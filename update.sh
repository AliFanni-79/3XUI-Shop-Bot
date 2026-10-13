#!/usr/bin/env bash
set -Eeuo pipefail

# Re-execute from /tmp so replacing update.sh during deployment can never break
# the currently running updater process.
if [[ "${SPEEDYBOT_UPDATER_REEXEC:-0}" != "1" ]]; then
  SELF="$(mktemp /tmp/speedybot-updater.XXXXXX.sh)"
  cp -- "$0" "$SELF"
  chmod 700 "$SELF"
  exec env SPEEDYBOT_UPDATER_REEXEC=1 "$SELF" "$@"
fi

SERVICE_NAME="${SPEEDYBOT_SERVICE_NAME:-xui-bot.service}"
APP_DIR="${SPEEDYBOT_APP_DIR:-/root/SpeedyBot}"
REPO_URL="${SPEEDYBOT_REPO_URL:-https://github.com/AliFanni-79/SpeedyBot.git}"
BRANCH="${SPEEDYBOT_BRANCH:-main}"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$APP_DIR/backups/deploy-$STAMP"
CURRENT_COMMIT_FILE="$APP_DIR/.deployed_commit"
TMP_DIR=""
CHECK_ONLY=0
FORCE=0

info(){ printf '[INFO] %s\n' "$*" >&2; }
ok(){ printf '[OK] %s\n' "$*" >&2; }
warn(){ printf '[WARN] %s\n' "$*" >&2; }
fail(){ printf '[ERROR] %s\n' "$*" >&2; exit 1; }

trim(){
  local v="$*"
  v="${v#"${v%%[![:space:]]*}"}"
  v="${v%"${v##*[![:space:]]}"}"
  printf '%s' "$v"
}

prompt(){
  local prompt_text="$1"
  local default_value="${2:-}"
  local ans=""
  while true; do
    if [[ -n "$default_value" ]]; then
      read -r -p "$prompt_text [$default_value]: " ans
      ans="${ans:-$default_value}"
    else
      read -r -p "$prompt_text: " ans
    fi
    ans="$(trim "$ans")"
    if [[ -n "$ans" ]]; then
      printf '%s' "$ans"
      return 0
    fi
    warn "This value cannot be empty."
  done
}

prompt_optional(){
  local prompt_text="$1"
  local default_value="${2:-}"
  local ans=""
  if [[ -n "$default_value" ]]; then
    read -r -p "$prompt_text [$default_value]: " ans
    ans="${ans:-$default_value}"
  else
    read -r -p "$prompt_text: " ans
  fi
  printf '%s' "$(trim "$ans")"
}

confirm(){
  local prompt_text="$1"
  local default_choice="${2:-Y}"
  local ans=""
  while true; do
    if [[ "$default_choice" =~ ^[Yy]$ ]]; then
      read -r -p "$prompt_text [Y/n]: " ans
      ans="${ans:-Y}"
    else
      read -r -p "$prompt_text [y/N]: " ans
      ans="${ans:-N}"
    fi
    case "$ans" in
      [Yy]|[Yy][Ee][Ss]) return 0 ;;
      [Nn]|[Nn][Oo]) return 1 ;;
      *) printf "Please enter y or n.\n" ;;
    esac
  done
}

normalize_webapp_url(){
  local v; v="$(trim "$1")"
  [[ -z "$v" ]] && { printf ''; return; }
  if [[ "$v" =~ ^http:// ]]; then
    warn "Telegram Mini Apps require HTTPS. Converting http:// to https://" >&2
    v="https://${v#http://}"
  elif [[ ! "$v" =~ ^https:// ]]; then
    v="https://$v"
  fi
  v="${v%/}"
  printf '%s' "$v"
}

install_cloudflared(){
  if command -v cloudflared >/dev/null 2>&1; then
    ok "cloudflared is already installed."
    return 0
  fi
  info "Downloading cloudflared binary..."
  local arch; arch="$(uname -m)"
  local cf_arch="amd64"
  case "$arch" in
    x86_64) cf_arch="amd64" ;;
    aarch64|arm64) cf_arch="arm64" ;;
    armv7l|armhf) cf_arch="arm" ;;
    i386|i686) cf_arch="386" ;;
    *) cf_arch="amd64" ;;
  esac

  if curl -fsSL -m 35 "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${cf_arch}" -o /usr/local/bin/cloudflared; then
    chmod +x /usr/local/bin/cloudflared
    ok "cloudflared installed successfully."
    return 0
  else
    warn "Direct cloudflared download failed. Trying apt repository..."
    mkdir -p --mode=0755 /etc/apt/keyrings
    curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg 2>/dev/null | tee /etc/apt/keyrings/cloudflare-main.gpg >/dev/null || true
    echo "deb [signed-by=/etc/apt/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main" | tee /etc/apt/sources.list.d/cloudflared.list >/dev/null || true
    apt-get update -qq && apt-get install -y -qq cloudflared || { warn "Could not install cloudflared automatically."; return 1; }
    return 0
  fi
}

setup_cf_quick_tunnel(){
  local port="$1"
  install_cloudflared || return 1
  info "Setting up Cloudflare Quick Tunnel service..."
  cat > /etc/systemd/system/speedybot-tunnel.service <<EOF
[Unit]
Description=SpeedyBot Cloudflare Tunnel (No Nginx)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/cloudflared tunnel --url http://127.0.0.1:${port} --no-autoupdate
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable speedybot-tunnel.service
  systemctl restart speedybot-tunnel.service
  info "Waiting for Cloudflare Quick Tunnel to allocate HTTPS URL..."
  sleep 4
  local cf_url=""
  for i in {1..8}; do
    cf_url="$(journalctl -u speedybot-tunnel.service -n 60 --no-pager 2>/dev/null | grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' | tail -n1 || true)"
    if [[ -n "$cf_url" ]]; then
      break
    fi
    sleep 2
  done
  if [[ -n "$cf_url" ]]; then
    ok "Cloudflare Quick Tunnel online: $cf_url"
    printf '%s' "$cf_url"
    return 0
  else
    warn "Tunnel started, but could not read URL immediately. Check: journalctl -u speedybot-tunnel.service"
    return 1
  fi
}

setup_cf_token_tunnel(){
  local token="$1"
  install_cloudflared || return 1
  info "Configuring Cloudflare Tunnel service with token..."
  cloudflared service install "$token" 2>/dev/null || true
  systemctl daemon-reload || true
  systemctl restart cloudflared 2>/dev/null || true
  ok "Cloudflare Tunnel service is active."
}

setup_caddy_proxy(){
  local domain="$1"
  local port="$2"
  info "Installing Caddy web server (automatic SSL without Nginx)..."
  apt-get update -qq
  apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https curl
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' 2>/dev/null | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg 2>/dev/null || true
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' 2>/dev/null | tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null || true
  apt-get update -qq
  apt-get install -y -qq caddy

  info "Configuring Caddy for $domain -> 127.0.0.1:$port..."
  cat > /etc/caddy/Caddyfile <<EOF
$domain {
    reverse_proxy 127.0.0.1:$port
}
EOF
  systemctl daemon-reload
  systemctl restart caddy
  ok "Caddy web server configured. Let's Encrypt SSL will be provisioned automatically."
}

set_env_var(){
  local key="$1"
  local val="$2"
  local file="$3"
  if grep -qE "^(export )?${key}=" "$file" 2>/dev/null; then
    sed -i -E "s|^(export )?${key}=.*|export ${key}=$(printf '%q' "$val")|" "$file"
  else
    printf "export %s=%q\n" "$key" "$val" >> "$file"
  fi
}

configure_mini_app_exposure(){
  local current_url; current_url="$(grep -E '^(export )?WEBAPP_URL=' "$APP_DIR/.env" 2>/dev/null | head -n1 | cut -d'=' -f2- | tr -d "'\"" | xargs || true)"
  local port; port="$(grep -E '^(export )?WEBAPP_PORT=' "$APP_DIR/.env" 2>/dev/null | head -n1 | cut -d'=' -f2- | tr -d "'\"" | xargs || echo "8080")"
  
  set_env_var "WEBAPP_PORT" "$port" "$APP_DIR/.env"
  if ! grep -qE '^(export )?WEBAPP_HOST=' "$APP_DIR/.env"; then
    set_env_var "WEBAPP_HOST" "0.0.0.0" "$APP_DIR/.env"
  fi

  if [[ ! -t 0 ]]; then
    return 0
  fi

  local prompt_user=0
  if [[ -z "$current_url" ]]; then
    prompt_user=1
  else
    info "Telegram Mini App URL is currently: $current_url"
    if confirm "Do you want to reconfigure Mini App Internet exposure (No Nginx needed)" "N"; then
      prompt_user=1
    fi
  fi

  if [[ "$prompt_user" -eq 1 ]]; then
    printf '\n============================================================\n'
    printf ' Telegram Mini App Internet Setup (No Nginx Required)\n'
    printf '============================================================\n'
    printf 'Telegram Mini Apps require a public HTTPS URL.\n'
    printf 'Select how you want to run the Mini App on the Internet:\n\n'
    printf '  1) Cloudflare Quick Tunnel (Free, No Nginx, No domain, instant HTTPS)\n'
    printf '  2) Cloudflare Named Tunnel (Using your Cloudflare Zero Trust token & custom domain)\n'
    printf '  3) Caddy Web Server (Zero-config Let'\''s Encrypt SSL, No Nginx)\n'
    printf '  4) Custom Domain / Existing Reverse Proxy (Nginx, Traefik, HAProxy, etc.)\n'
    printf '  5) Skip for now (keep running locally on port %s)\n' "$port"
    
    local choice; choice="$(prompt "Select option (1-5)" "1")"
    local new_url=""
    
    case "$choice" in
      1)
        info "Setting up Cloudflare Quick Tunnel..."
        local q_url; q_url="$(setup_cf_quick_tunnel "$port" || true)"
        q_url="$(printf '%s\n' "$q_url" | grep -oE 'https://[a-zA-Z0-9.-]+\.trycloudflare\.com' | tail -n1 || true)"
        if [[ -n "$q_url" ]]; then
          new_url="$q_url"
        fi
        ;;
      2)
        local cf_token; cf_token="$(prompt "Cloudflare Tunnel Token (starts with eyJh...)")"
        local raw_url; raw_url="$(prompt "Public HTTPS hostname you routed in Cloudflare (e.g. https://shop.example.com)")"
        new_url="$(normalize_webapp_url "$raw_url")"
        setup_cf_token_tunnel "$cf_token" || true
        ;;
      3)
        local caddy_domain; caddy_domain="$(prompt "Your domain name pointing to this server IP (e.g. shop.example.com)")"
        caddy_domain="$(printf '%s' "$caddy_domain" | sed -E 's#^https?://##; s#/.*$##')"
        new_url="https://$caddy_domain"
        setup_caddy_proxy "$caddy_domain" "$port" || true
        ;;
      4)
        local raw_url; raw_url="$(prompt_optional "Public HTTPS URL (e.g. https://shop.example.com)" "")"
        new_url="$(normalize_webapp_url "$raw_url")"
        ;;
      *)
        info "Skipping internet tunnel configuration. Mini App runs locally on port $port."
        ;;
    esac

    if [[ -n "$new_url" ]]; then
      set_env_var "WEBAPP_URL" "$new_url" "$APP_DIR/.env"
      ok "Updated WEBAPP_URL in .env: $new_url"
      if [[ -f "$APP_DIR/speedping.db" ]]; then
        TARGET_URL="$new_url" TARGET_DB="$APP_DIR/speedping.db" "$APP_DIR/.venv/bin/python3" - <<'PY' || true
import os
import sqlite3
try:
    db_path = os.environ.get("TARGET_DB", "/root/SpeedyBot/speedping.db")
    target_url = os.environ.get("TARGET_URL", "").strip()
    conn = sqlite3.connect(db_path, timeout=15)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    c.execute("INSERT INTO settings(key, value) VALUES('webapp_url', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (target_url,))
    conn.commit()
    conn.close()
except Exception:
    pass
PY
      fi
    fi
  fi
}

cleanup(){
  [[ -z "${TMP_DIR:-}" || ! -d "$TMP_DIR" ]] || rm -rf "$TMP_DIR"
  [[ "$0" != /tmp/speedybot-updater.*.sh ]] || rm -f "$0" 2>/dev/null || true
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

write_runner(){
  cat > "$APP_DIR/run.sh" <<EOF
#!/usr/bin/env bash
set -Eeuo pipefail
source "$APP_DIR/.env"
exec "$APP_DIR/.venv/bin/python3" "$APP_DIR/main.py"
EOF
  chmod 700 "$APP_DIR/run.sh"
}

# Runtime state is never copied from GitHub and never removed by --delete.
RSYNC_EXCLUDES=(
  --exclude '.git/'
  --exclude '.env'
  --exclude '.venv/'
  --exclude 'speedping.db'
  --exclude 'speedping.db-wal'
  --exclude 'speedping.db-shm'
  --exclude 'backups/'
  --exclude 'run.sh'
  --exclude '.deployed_commit'
  --exclude 'node_modules/'
  --exclude 'webapp/node_modules/'
)

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
info "Cloning complete repository..."
git clone --quiet --depth 1 --branch "$BRANCH" "$REPO_URL" "$SOURCE_DIR" || fail "git clone failed."
CLONED_COMMIT="$(git -C "$SOURCE_DIR" rev-parse HEAD)"

if [[ "$FORCE" -ne 1 && -f "$APP_DIR/VERSION.txt" && -f "$SOURCE_DIR/VERSION.txt" ]]; then
  LOCAL_VERSION="$(grep -oE '^[0-9]+(\.[0-9]+){1,2}' "$APP_DIR/VERSION.txt" | head -1 || true)"
  REMOTE_VERSION="$(grep -oE '^[0-9]+(\.[0-9]+){1,2}' "$SOURCE_DIR/VERSION.txt" | head -1 || true)"
  if [[ -n "$LOCAL_VERSION" && -n "$REMOTE_VERSION" ]]; then
    LOWEST="$(printf '%s\n%s\n' "$LOCAL_VERSION" "$REMOTE_VERSION" | sort -V | head -1)"
    if [[ "$LOWEST" == "$REMOTE_VERSION" && "$LOCAL_VERSION" != "$REMOTE_VERSION" ]]; then
      fail "GitHub version $REMOTE_VERSION is older than installed $LOCAL_VERSION. Use --force only for an intentional downgrade."
    fi
  fi
fi

[[ -f "$SOURCE_DIR/main.py" ]] || fail "main.py is missing from the repository."
[[ -d "$SOURCE_DIR/speedybot" ]] || fail "speedybot application package is missing from the repository."

info "Validating downloaded project before downtime..."
python3 -m py_compile "$SOURCE_DIR/main.py" "$SOURCE_DIR"/speedybot/*.py || fail "Python syntax validation failed."
bash -n "$SOURCE_DIR/update.sh" || fail "update.sh syntax validation failed."
[[ ! -f "$SOURCE_DIR/install.sh" ]] || bash -n "$SOURCE_DIR/install.sh" || fail "install.sh syntax validation failed."

if [[ ! -x "$APP_DIR/.venv/bin/python3" ]]; then
  apt-get update
  apt-get install -y python3 python3-pip python3-venv
  python3 -m venv "$APP_DIR/.venv"
fi

info "Installing Python dependencies before downtime..."
"$APP_DIR/.venv/bin/python3" -m pip install --upgrade pip >/dev/null
if [[ -f "$SOURCE_DIR/requirements.txt" ]]; then
  "$APP_DIR/.venv/bin/python3" -m pip install -r "$SOURCE_DIR/requirements.txt" || fail "Dependency installation failed."
fi

mkdir -p "$BACKUP_DIR/app"
info "Stopping bot and creating a complete rollback backup..."
systemctl stop "$SERVICE_NAME" 2>/dev/null || true

# Consistent runtime backup.
for f in .env speedping.db speedping.db-wal speedping.db-shm .deployed_commit run.sh; do
  [[ ! -f "$APP_DIR/$f" ]] || cp -a "$APP_DIR/$f" "$BACKUP_DIR/$f"
done

# Backup the complete deployed repository while excluding mutable runtime data.
rsync -a --delete "${RSYNC_EXCLUDES[@]}" "$APP_DIR/" "$BACKUP_DIR/app/"

rollback(){
  warn "Deployment failed; restoring the previous complete application..."
  systemctl stop "$SERVICE_NAME" 2>/dev/null || true

  rsync -a --delete "${RSYNC_EXCLUDES[@]}" "$BACKUP_DIR/app/" "$APP_DIR/" || true
  for f in .env speedping.db speedping.db-wal speedping.db-shm .deployed_commit; do
    if [[ -f "$BACKUP_DIR/$f" ]]; then
      cp -a "$BACKUP_DIR/$f" "$APP_DIR/$f"
    elif [[ "$f" != "speedping.db" && "$f" != ".env" ]]; then
      rm -f "$APP_DIR/$f"
    fi
  done
  write_runner
  chmod +x "$APP_DIR/install.sh" "$APP_DIR/update.sh" 2>/dev/null || true
  systemctl daemon-reload || true
  systemctl restart "$SERVICE_NAME" || true
  sleep 2
  journalctl -u "$SERVICE_NAME" -n 100 --no-pager || true
  fail "Rollback completed. Backup: $BACKUP_DIR"
}

info "Synchronizing the complete repository to $APP_DIR..."
rsync -a --delete "${RSYNC_EXCLUDES[@]}" "$SOURCE_DIR/" "$APP_DIR/" || rollback

chmod +x "$APP_DIR/install.sh" "$APP_DIR/update.sh" 2>/dev/null || true
printf '%s\n' "$CLONED_COMMIT" > "$CURRENT_COMMIT_FILE"
write_runner

configure_mini_app_exposure

info "Validating deployed application..."
"$APP_DIR/.venv/bin/python3" -m py_compile "$APP_DIR/main.py" "$APP_DIR"/speedybot/*.py || rollback
bash -n "$APP_DIR/update.sh" || rollback
[[ ! -f "$APP_DIR/install.sh" ]] || bash -n "$APP_DIR/install.sh" || rollback

systemctl daemon-reload || rollback
systemctl restart "$SERVICE_NAME" || rollback
sleep 5
systemctl is-active --quiet "$SERVICE_NAME" || rollback

if systemctl list-unit-files speedybot-tunnel.service 2>/dev/null | grep -q 'speedybot-tunnel.service'; then
  systemctl restart speedybot-tunnel.service 2>/dev/null || true
fi
if systemctl is-active --quiet caddy 2>/dev/null; then
  systemctl reload caddy 2>/dev/null || systemctl restart caddy 2>/dev/null || true
fi

# Catch immediate crash loops, not just a single successful start.
sleep 3
systemctl is-active --quiet "$SERVICE_NAME" || rollback
RESTARTS="$(systemctl show "$SERVICE_NAME" -p NRestarts --value 2>/dev/null || echo 0)"
if [[ "$RESTARTS" =~ ^[0-9]+$ && "$RESTARTS" -ge 3 ]]; then
  warn "Service restarted $RESTARTS times immediately after deployment."
  rollback
fi

ok "SpeedyBot complete-project update finished successfully."
ok "Commit: $CLONED_COMMIT"
ok ".env, SQLite runtime data, virtualenv and backups were preserved."
info "Rollback backup: $BACKUP_DIR"

FINAL_WEBAPP_URL="$(grep -E '^(export )?WEBAPP_URL=' "$APP_DIR/.env" 2>/dev/null | head -n1 | cut -d'=' -f2- | tr -d "'\"" | xargs || true)"
if [[ -n "$FINAL_WEBAPP_URL" ]]; then
  printf '\n🌐 Telegram Mini App is accessible at:\n'
  printf '   %s\n' "$FINAL_WEBAPP_URL"
  if systemctl is-active --quiet speedybot-tunnel.service 2>/dev/null; then
    printf '   • Cloudflare Quick Tunnel service: speedybot-tunnel.service\n'
  elif systemctl is-active --quiet cloudflared 2>/dev/null; then
    printf '   • Cloudflare Tunnel service: cloudflared.service\n'
  elif systemctl is-active --quiet caddy 2>/dev/null; then
    printf '   • Caddy web server: caddy.service\n'
  fi
  printf '\n📱 Remember to set this URL in @BotFather via /setmenubutton\n\n'
fi

systemctl --no-pager --full status "$SERVICE_NAME" || true
