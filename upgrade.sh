#!/usr/bin/env bash
set -Eeuo pipefail

# ==============================================================================
# VizzPN Shop Bot Upgrade Engine (Phase 2: Execution & Deployment)
# ==============================================================================
# This script executes the actual upgrade logic from the latest pulled code.
# It is launched by update.sh (Phase 1) after pulling the newest remote version.
# ==============================================================================

SERVICE_NAME="${SPEEDYBOT_SERVICE_NAME:-xui-bot.service}"
APP_DIR="${SPEEDYBOT_APP_DIR:-/root/SpeedyBot}"
export PYTHONPATH="$APP_DIR${PYTHONPATH:+:$PYTHONPATH}"
REPO_URL="${SPEEDYBOT_REPO_URL:-https://github.com/AliFanni-79/3XUI-Shop-Bot.git}"
BRANCH="${SPEEDYBOT_BRANCH:-main}"
SOURCE_DIR="${SPEEDYBOT_SOURCE_DIR:-}"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$APP_DIR/backups/deploy-$STAMP"
CURRENT_COMMIT_FILE="$APP_DIR/.deployed_commit"
CLEANUP_TMP_DIR="${SPEEDYBOT_TMP_DIR:-}"
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
  local cf_bin
  cf_bin="$(command -v cloudflared || echo '/usr/local/bin/cloudflared')"
  info "Setting up persistent Cloudflare Quick Tunnel service..."
  cat > /etc/systemd/system/speedybot-tunnel.service <<EOF
[Unit]
Description=X-UI Shop Bot Cloudflare Tunnel (No Nginx)
After=network-online.target xui-bot.service
Wants=network-online.target

[Service]
Type=simple
User=root
ExecStart=${cf_bin} tunnel --url http://127.0.0.1:${port} --protocol http2 --no-autoupdate
Restart=always
RestartSec=3
LimitNOFILE=65535
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF
  local start_time; start_time="$(date +'%Y-%m-%d %H:%M:%S')"
  systemctl daemon-reload
  systemctl enable speedybot-tunnel.service
  systemctl restart speedybot-tunnel.service
  info "Waiting for Cloudflare Quick Tunnel to allocate HTTPS URL..."
  local cf_url=""
  for i in {1..15}; do
    sleep 2
    cf_url="$(journalctl -u speedybot-tunnel.service --since "$start_time" -n 80 --no-pager 2>/dev/null | grep -oE 'https://[a-zA-Z0-9.-]+\.trycloudflare\.com' | tail -n1 || true)"
    if [[ -n "$cf_url" ]]; then
      break
    fi
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
      TARGET_URL="$new_url" PYTHONPATH="$APP_DIR" "$APP_DIR/.venv/bin/python3" - <<'PY' || true
import sys, os
sys.path.insert(0, os.environ.get("SPEEDYBOT_APP_DIR", "/root/SpeedyBot"))
try:
    from xuishop import db
    conn = db.get_connection(timeout=15)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    c.execute("INSERT INTO settings(key, value) VALUES('webapp_url', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (os.environ.get("TARGET_URL", "").strip(),))
    conn.commit()
    conn.close()
except Exception:
    pass
PY
    fi
  fi
}

write_runner(){
  cat > "$APP_DIR/run.sh" <<EOF
#!/usr/bin/env bash
set -Eeuo pipefail
cd "$APP_DIR"
export PYTHONPATH="$APP_DIR\${PYTHONPATH:+:\$PYTHONPATH}"
source "$APP_DIR/.env"
exec "$APP_DIR/.venv/bin/python3" "$APP_DIR/main.py"
EOF
  chmod 700 "$APP_DIR/run.sh"
}

cleanup(){
  [[ -z "${CLEANUP_TMP_DIR:-}" || ! -d "$CLEANUP_TMP_DIR" ]] || rm -rf "$CLEANUP_TMP_DIR"
}
trap cleanup EXIT

for arg in "$@"; do
  case "$arg" in
    --check) CHECK_ONLY=1 ;;
    --force) FORCE=1 ;;
    -h|--help)
      cat <<'EOF'
Usage: ./upgrade.sh [--check] [--force]
  --check  compare installed commit with GitHub without changing anything
  --force  deploy the current remote commit even if it matches installed state
EOF
      exit 0
      ;;
    *) fail "Unknown argument: $arg" ;;
  esac
done

[[ "$EUID" -eq 0 ]] || fail "Run upgrade.sh as root."
[[ -f "$APP_DIR/.env" ]] || fail "Existing installation not found at $APP_DIR (.env is missing)."

# If SOURCE_DIR not provided via environment, determine or clone it
if [[ -z "$SOURCE_DIR" || ! -d "$SOURCE_DIR" ]]; then
  LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [[ -f "$LOCAL_DIR/main.py" && -d "$LOCAL_DIR/xuishop" && "$LOCAL_DIR" != "$APP_DIR" ]]; then
    SOURCE_DIR="$LOCAL_DIR"
  else
    info "Source directory not specified; pulling latest from GitHub..."
    CLEANUP_TMP_DIR="$(mktemp -d /tmp/speedybot-upgrade.XXXXXX)"
    SOURCE_DIR="$CLEANUP_TMP_DIR/repo"
    git clone --quiet --depth 1 --branch "$BRANCH" "$REPO_URL" "$SOURCE_DIR" || fail "git clone failed."
  fi
fi

CLONED_COMMIT="$(git -C "$SOURCE_DIR" rev-parse HEAD 2>/dev/null || cat "$SOURCE_DIR/.deployed_commit" 2>/dev/null || echo "unknown")"
CURRENT_COMMIT=""
[[ -f "$CURRENT_COMMIT_FILE" ]] && CURRENT_COMMIT="$(tr -d '[:space:]' < "$CURRENT_COMMIT_FILE")"

info "Executing Phase 2 deployment..."
info "Installed: ${CURRENT_COMMIT:-unknown}"
info "Target:    $CLONED_COMMIT"

if [[ "$CHECK_ONLY" -eq 1 ]]; then
  [[ "$CURRENT_COMMIT" == "$CLONED_COMMIT" ]] && ok "Already up to date." || warn "A newer/different commit is available."
  exit 0
fi

if [[ "$FORCE" -ne 1 && -n "$CURRENT_COMMIT" && "$CURRENT_COMMIT" == "$CLONED_COMMIT" ]]; then
  ok "Already on latest version."
  exit 0
fi

if [[ "$FORCE" -ne 1 && -f "$APP_DIR/VERSION.txt" && -f "$SOURCE_DIR/VERSION.txt" ]]; then
  LOCAL_VERSION="$(grep -oE '^[0-9]+(\.[0-9]+){1,2}' "$APP_DIR/VERSION.txt" | head -1 || true)"
  REMOTE_VERSION="$(grep -oE '^[0-9]+(\.[0-9]+){1,2}' "$SOURCE_DIR/VERSION.txt" | head -1 || true)"
  if [[ -n "$LOCAL_VERSION" && -n "$REMOTE_VERSION" ]]; then
    LOWEST="$(printf '%s\n%s\n' "$LOCAL_VERSION" "$REMOTE_VERSION" | sort -V | head -1)"
    if [[ "$LOWEST" == "$REMOTE_VERSION" && "$LOCAL_VERSION" != "$REMOTE_VERSION" ]]; then
      fail "Target version $REMOTE_VERSION is older than installed $LOCAL_VERSION. Use --force for intentional downgrade."
    fi
  fi
fi

[[ -f "$SOURCE_DIR/main.py" ]] || fail "main.py is missing from target repository."
[[ -d "$SOURCE_DIR/xuishop" ]] || fail "xuishop application package is missing from target repository."

info "Validating source code before service downtime..."
python3 -m py_compile "$SOURCE_DIR/main.py" "$SOURCE_DIR"/xuishop/*.py || fail "Python syntax validation failed."
bash -n "$SOURCE_DIR/update.sh" 2>/dev/null || fail "update.sh syntax validation failed."
bash -n "$SOURCE_DIR/upgrade.sh" 2>/dev/null || fail "upgrade.sh syntax validation failed."
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

# Runtime state is never copied from GitHub and never removed by --delete.
RSYNC_EXCLUDES=(
  --exclude '.git/'
  --exclude '.env'
  --exclude '.venv/'
  --exclude 'app.db'
  --exclude 'app.db-wal'
  --exclude 'app.db-shm'
  --exclude 'speedping.db'
  --exclude 'speedping.db-wal'
  --exclude 'speedping.db-shm'
  --exclude 'backups/'
  --exclude 'run.sh'
  --exclude '.deployed_commit'
  --exclude 'node_modules/'
  --exclude 'webapp/node_modules/'
)

mkdir -p "$BACKUP_DIR/app"
info "Stopping bot service for atomic upgrade..."
systemctl stop "$SERVICE_NAME" 2>/dev/null || true

# ------------------------------------------------------------------------------
# Database Migration: speedping.db -> app.db
# ------------------------------------------------------------------------------
if [[ -f "$APP_DIR/speedping.db" && ! -f "$APP_DIR/app.db" ]]; then
  info "Migrating legacy database speedping.db to app.db..."
  mv "$APP_DIR/speedping.db" "$APP_DIR/app.db"
  [[ ! -f "$APP_DIR/speedping.db-wal" ]] || mv "$APP_DIR/speedping.db-wal" "$APP_DIR/app.db-wal"
  [[ ! -f "$APP_DIR/speedping.db-shm" ]] || mv "$APP_DIR/speedping.db-shm" "$APP_DIR/app.db-shm"
  ok "Database file successfully migrated to app.db."
fi

# Consistent runtime backup
for f in .env app.db app.db-wal app.db-shm speedping.db speedping.db-wal speedping.db-shm .deployed_commit run.sh; do
  [[ ! -f "$APP_DIR/$f" ]] || cp -a "$APP_DIR/$f" "$BACKUP_DIR/$f"
done

# Backup complete deployed repository while excluding mutable runtime data
rsync -a --delete "${RSYNC_EXCLUDES[@]}" "$APP_DIR/" "$BACKUP_DIR/app/"

rollback(){
  warn "Deployment failed; restoring the previous complete application..."
  systemctl stop "$SERVICE_NAME" 2>/dev/null || true

  rsync -a --delete "${RSYNC_EXCLUDES[@]}" "$BACKUP_DIR/app/" "$APP_DIR/" || true
  for f in .env app.db app.db-wal app.db-shm speedping.db speedping.db-wal speedping.db-shm .deployed_commit; do
    if [[ -f "$BACKUP_DIR/$f" ]]; then
      cp -a "$BACKUP_DIR/$f" "$APP_DIR/$f"
    elif [[ "$f" != "app.db" && "$f" != "speedping.db" && "$f" != ".env" ]]; then
      rm -f "$APP_DIR/$f"
    fi
  done
  write_runner
  chmod +x "$APP_DIR/install.sh" "$APP_DIR/update.sh" "$APP_DIR/upgrade.sh" "$APP_DIR/restore.sh" 2>/dev/null || true
  systemctl daemon-reload || true
  systemctl restart "$SERVICE_NAME" || true
  sleep 2
  journalctl -u "$SERVICE_NAME" -n 100 --no-pager || true
  fail "Rollback completed. Backup: $BACKUP_DIR"
}

info "Synchronizing repository to $APP_DIR..."
rsync -a --delete "${RSYNC_EXCLUDES[@]}" "$SOURCE_DIR/" "$APP_DIR/" || rollback

chmod +x "$APP_DIR/install.sh" "$APP_DIR/update.sh" "$APP_DIR/upgrade.sh" "$APP_DIR/restore.sh" 2>/dev/null || true
printf '%s\n' "$CLONED_COMMIT" > "$CURRENT_COMMIT_FILE"
write_runner

info "Running database schema migrations..."
PYTHONPATH="$APP_DIR" "$APP_DIR/.venv/bin/python3" -c "import sys; sys.path.insert(0, '$APP_DIR'); from xuishop import storage, db; storage.init_db()" || rollback

info "Validating deployed application..."
PYTHONPATH="$APP_DIR" "$APP_DIR/.venv/bin/python3" -m py_compile "$APP_DIR/main.py" "$APP_DIR"/xuishop/*.py || rollback
bash -n "$APP_DIR/update.sh" || rollback
bash -n "$APP_DIR/upgrade.sh" || rollback
[[ ! -f "$APP_DIR/install.sh" ]] || bash -n "$APP_DIR/install.sh" || rollback

systemctl daemon-reload || rollback
systemctl restart "$SERVICE_NAME" || rollback
sleep 5
systemctl is-active --quiet "$SERVICE_NAME" || rollback

# Check for immediate crash loops
sleep 3
systemctl is-active --quiet "$SERVICE_NAME" || rollback
RESTARTS="$(systemctl show "$SERVICE_NAME" -p NRestarts --value 2>/dev/null || echo 0)"
if [[ "$RESTARTS" =~ ^[0-9]+$ && "$RESTARTS" -ge 3 ]]; then
  warn "Service restarted $RESTARTS times immediately after deployment."
  rollback
fi

configure_mini_app_exposure

if systemctl is-active --quiet caddy 2>/dev/null; then
  systemctl reload caddy 2>/dev/null || systemctl restart caddy 2>/dev/null || true
fi

ok "VizzPN Shop Bot upgrade finished successfully."
ok "Commit: $CLONED_COMMIT"
ok ".env, SQLite database (app.db), virtualenv and backups were preserved."
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
