#!/usr/bin/env bash
set -Eeuo pipefail

# ==============================================================================
# VizzPN Shop Bot Updater (Phase 1: Fetch Latest Remote Version)
# ==============================================================================
# This launcher fetches the newest version from GitHub and delegates execution
# to upgrade.sh from the freshly fetched code. This ensures that any improvements,
# migrations, or fixes in the updater logic itself are executed.
# ==============================================================================

SERVICE_NAME="${SPEEDYBOT_SERVICE_NAME:-xui-bot.service}"
APP_DIR="${SPEEDYBOT_APP_DIR:-/root/SpeedyBot}"
REPO_URL="${SPEEDYBOT_REPO_URL:-https://github.com/AliFanni-79/3XUI-Shop-Bot.git}"
BRANCH="${SPEEDYBOT_BRANCH:-main}"
CURRENT_COMMIT_FILE="$APP_DIR/.deployed_commit"
CHECK_ONLY=0
FORCE=0
TMP_DIR=""

info(){ printf '[INFO] %s\n' "$*" >&2; }
ok(){ printf '[OK] %s\n' "$*" >&2; }
warn(){ printf '[WARN] %s\n' "$*" >&2; }
fail(){ printf '[ERROR] %s\n' "$*" >&2; exit 1; }

cleanup(){
  [[ -z "${TMP_DIR:-}" || ! -d "$TMP_DIR" ]] || rm -rf "$TMP_DIR"
}
trap cleanup EXIT

for arg in "$@"; do
  case "$arg" in
    --check) CHECK_ONLY=1 ;;
    --force) FORCE=1 ;;
    -h|--help)
      cat <<'EOF'
Usage: ./update.sh [--check] [--force]
  --check  compare installed commit with GitHub without changing anything
  --force  deploy the current remote commit even if it matches installed state
EOF
      exit 0
      ;;
    *) fail "Unknown argument: $arg" ;;
  esac
done

[[ "$EUID" -eq 0 ]] || fail "Run update.sh as root."
[[ -f "$APP_DIR/.env" ]] || fail "Existing installation not found at $APP_DIR (.env is missing)."

if ! command -v git >/dev/null 2>&1 || ! command -v rsync >/dev/null 2>&1; then
  apt-get update
  apt-get install -y git ca-certificates rsync
fi

info "Checking GitHub repository: $REPO_URL ($BRANCH)"
REMOTE_LINE="$(git ls-remote "$REPO_URL" "refs/heads/$BRANCH" 2>&1)" || fail "Cannot reach GitHub: $REMOTE_LINE"
REMOTE_COMMIT="$(awk 'NR==1{print $1}' <<<"$REMOTE_LINE")"
[[ "$REMOTE_COMMIT" =~ ^[0-9a-fA-F]{40}$ ]] || fail "Could not resolve branch $BRANCH."
CURRENT_COMMIT=""
[[ -f "$CURRENT_COMMIT_FILE" ]] && CURRENT_COMMIT="$(tr -d '[:space:]' < "$CURRENT_COMMIT_FILE")"

info "Installed: ${CURRENT_COMMIT:-unknown}"
info "GitHub:    $REMOTE_COMMIT"

if [[ "$CHECK_ONLY" -eq 1 ]]; then
  [[ "$CURRENT_COMMIT" == "$REMOTE_COMMIT" ]] && ok "Already up to date." || warn "A newer/different GitHub commit is available."
  exit 0
fi

if [[ "$FORCE" -ne 1 && -n "$CURRENT_COMMIT" && "$CURRENT_COMMIT" == "$REMOTE_COMMIT" ]]; then
  ok "Already on latest version."
  exit 0
fi

TMP_DIR="$(mktemp -d /tmp/speedybot-update.XXXXXX)"
SOURCE_DIR="$TMP_DIR/repo"

info "Pulling latest version from remote repository into temporary workspace..."
git clone --quiet --depth 1 --branch "$BRANCH" "$REPO_URL" "$SOURCE_DIR" || fail "git clone failed."

UPGRADE_SCRIPT="$SOURCE_DIR/upgrade.sh"
[[ -f "$UPGRADE_SCRIPT" ]] || fail "upgrade.sh is missing from remote repository."
chmod +x "$UPGRADE_SCRIPT"

info "Phase 1 complete. Launching Phase 2 (upgrade.sh from freshly pulled version)..."
# Disarm Phase 1 cleanup trap so TMP_DIR remains intact for upgrade.sh (which manages its own cleanup)
trap - EXIT

exec env \
  SPEEDYBOT_SOURCE_DIR="$SOURCE_DIR" \
  SPEEDYBOT_TMP_DIR="$TMP_DIR" \
  SPEEDYBOT_APP_DIR="$APP_DIR" \
  SPEEDYBOT_REPO_URL="$REPO_URL" \
  SPEEDYBOT_BRANCH="$BRANCH" \
  SPEEDYBOT_SERVICE_NAME="$SERVICE_NAME" \
  PYTHONPATH="$APP_DIR${PYTHONPATH:+:$PYTHONPATH}" \
  bash "$UPGRADE_SCRIPT" "$@"
