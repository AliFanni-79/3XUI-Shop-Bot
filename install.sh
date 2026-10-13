#!/usr/bin/env bash
set -Eeuo pipefail

SERVICE_NAME="xui-bot.service"
APP_DIR="/root/SpeedyBot"
ENV_FILE="$APP_DIR/.env"
RUNNER_FILE="$APP_DIR/run.sh"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED="\033[0;31m"; GREEN="\033[0;32m"; YELLOW="\033[1;33m"; BLUE="\033[0;34m"; NC="\033[0m"
info(){ printf "${BLUE}[INFO]${NC} %s\n" "$*"; }
ok(){ printf "${GREEN}[OK]${NC} %s\n" "$*"; }
warn(){ printf "${YELLOW}[WARN]${NC} %s\n" "$*" >&2; }
fail(){ printf "${RED}[ERROR]${NC} %s\n" "$*" >&2; exit 1; }
trap 'printf "${RED}[ERROR]${NC} Installation failed at line %s.\n" "$LINENO" >&2' ERR

trim(){ local v="$1"; v="${v#"${v%%[![:space:]]*}"}"; v="${v%"${v##*[![:space:]]}"}"; printf '%s' "$v"; }
prompt(){ local p="$1" d="${2-}" v=""; while true; do if [[ -n "$d" ]]; then read -r -p "$p [$d]: " v || true; v="$(trim "${v:-$d}")"; else read -r -p "$p: " v || true; v="$(trim "${v:-}")"; fi; [[ -n "$v" ]] && { printf '%s' "$v"; return; }; warn "Value cannot be empty."; done; }
prompt_optional(){ local p="$1" d="${2-}" v=""; read -r -p "$p${d:+ [$d]}: " v || true; v="$(trim "${v:-$d}")"; printf '%s' "$v"; }
secret(){
  local p="$1" v=""
  while true; do
    printf '%s [input hidden — paste/type, then press Enter]: ' "$p" >&2
    IFS= read -r -s v || true
    printf '\n' >&2
    v="$(printf '%s' "$v" | tr -d '\n\r\t')"
    if [[ -n "$v" ]]; then
      printf "${GREEN}[OK]${NC} Secret received (%d characters).\n" "${#v}" >&2
      printf '%s' "$v"
      return
    fi
    warn "Nothing was received. Paste/type the value even though it is not shown, then press Enter."
  done
}
confirm(){ local a=""; read -r -p "$1 [y/N]: " a || true; [[ "${a,,}" =~ ^(y|yes)$ ]]; }
normalize_base_path(){ local v; v="$(trim "$1")"; [[ -z "$v" ]] && v="/"; [[ "$v" != /* ]] && v="/$v"; [[ "$v" != "/" ]] && v="${v%/}"; printf '%s' "$v"; }
normalize_sub_path(){ local v; v="$(trim "$1")"; [[ -z "$v" ]] && v="/sub/"; [[ "$v" != /* ]] && v="/$v"; [[ "$v" != */ ]] && v="$v/"; printf '%s' "$v"; }

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

check_port_in_use(){
  local p="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -tulpn 2>/dev/null | grep -qE ":$p\b" && return 0
  elif command -v netstat >/dev/null 2>&1; then
    netstat -tulpn 2>/dev/null | grep -qE ":$p\b" && return 0
  elif command -v lsof >/dev/null 2>&1; then
    lsof -i ":$p" >/dev/null 2>&1 && return 0
  fi
  return 1
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

write_runner(){
  cat > "$RUNNER_FILE" <<EOF
#!/usr/bin/env bash
set -Eeuo pipefail
source "$ENV_FILE"
exec "$APP_DIR/.venv/bin/python3" "$APP_DIR/main.py"
EOF
  chmod 700 "$RUNNER_FILE"
}

[[ "$EUID" -eq 0 ]] || fail "Run install.sh as root."
command -v apt-get >/dev/null 2>&1 || fail "apt-get was not found. Ubuntu/Debian is required."
[[ -f "$SOURCE_DIR/main.py" ]] || fail "main.py is missing next to install.sh."
[[ -d "$SOURCE_DIR/speedybot" ]] || fail "speedybot application package is missing."

printf '\n============================================================\n SpeedyBot v5.0.0 Installer\n Telegram Mini App + 3x-ui / Sanaei Automation\n============================================================\n\n'

# --- System Prerequisites Check ---
info "Checking system prerequisites..."
TOTAL_MEM_KB="$(grep MemTotal /proc/meminfo 2>/dev/null | awk '{print $2}' || echo 0)"
if [[ "$TOTAL_MEM_KB" -gt 0 && "$TOTAL_MEM_KB" -lt 500000 ]]; then
  warn "Total server RAM is under 512MB ($((TOTAL_MEM_KB/1024))MB). Ensure swap is configured."
else
  ok "Server RAM: $((TOTAL_MEM_KB/1024)) MB"
fi

if command -v python3 >/dev/null 2>&1; then
  PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "0.0")"
  info "Detected Python: $PY_VER"
fi
printf '\n'

# --- 1. Telegram Bot & Admin ---
info "1. Telegram Bot Configuration"
printf 'Note: Bot/API tokens are intentionally hidden while typing. Your paste still works; press Enter after pasting.\n\n'
while true; do
  BOT_TOKEN="$(secret "Telegram Bot token (@BotFather)")"
  if [[ "$BOT_TOKEN" =~ ^[0-9]+:[A-Za-z0-9_-]{20,}$ ]]; then
    info "Verifying Bot token with Telegram API..."
    set +e
    BOT_TEST="$(curl -s -m 8 "https://api.telegram.org/bot${BOT_TOKEN}/getMe" 2>/dev/null || true)"
    set -e
    if [[ "$BOT_TEST" =~ \"ok\":true ]]; then
      BOT_UNAME="$(printf '%s' "$BOT_TEST" | grep -o '"username":"[^"]*"' | cut -d'"' -f4 || true)"
      ok "Telegram Bot verified: @${BOT_UNAME}"
      break
    else
      warn "Telegram API did not verify the token (HTTP test failed or invalid token)."
      if confirm "Use this token anyway"; then
        break
      fi
    fi
  else
    warn "Telegram bot token format looks invalid. Copy the full token from @BotFather and try again."
  fi
done

ADMIN_ID="$(prompt "Telegram Admin numeric ID (Owner)")"
[[ "$ADMIN_ID" =~ ^[0-9]+$ && "$ADMIN_ID" != "0" ]] || fail "Admin ID must be numeric."
printf '\n'

# --- 2. 3x-ui Panel Configuration ---
info "2. 3x-ui / Sanaei Panel Configuration"
XUI_API_URL="$(prompt "X-UI API base URL (scheme + host + port only)" "http://127.0.0.1:2053")"
XUI_API_URL="${XUI_API_URL%/}"
[[ "$XUI_API_URL" =~ ^https?://[^[:space:]/?#]+(:[0-9]{1,5})?$ ]] || fail "Invalid X-UI API base URL."

XUI_BASE_PATH="$(normalize_base_path "$(prompt "X-UI security base path" "/")")"
XUI_BEARER_TOKEN="$(secret "Panel Bearer API Token (plaintext value)")"

XUI_SUB_SERVER_URL="$(prompt "Subscription server base URL" "https://sub.example.com:2096")"
XUI_SUB_SERVER_URL="${XUI_SUB_SERVER_URL%/}"
[[ "$XUI_SUB_SERVER_URL" =~ ^https?://[^[:space:]/?#]+(:[0-9]{1,5})?$ ]] || fail "Invalid subscription base URL."

XUI_SUB_PATH="$(normalize_sub_path "$(prompt "Subscription URI path" "/sub/")")"
printf '\n'

# --- 3. Telegram Mini App & Internet Exposure ---
info "3. Telegram Mini App (TMA) & Internet Access"
while true; do
  WEBAPP_PORT="$(prompt "Mini App internal HTTP port" "8080")"
  if [[ "$WEBAPP_PORT" =~ ^[0-9]+$ ]] && [[ "$WEBAPP_PORT" -ge 1 ]] && [[ "$WEBAPP_PORT" -le 65535 ]]; then
    if check_port_in_use "$WEBAPP_PORT"; then
      warn "Port $WEBAPP_PORT is currently in use on this server!"
      if ! confirm "Use port $WEBAPP_PORT anyway"; then
        continue
      fi
    fi
    break
  else
    warn "Port must be a number between 1 and 65535."
  fi
done

printf "\nHow would you like to run the Web App through the Internet (HTTPS)?\n"
printf "  1) Cloudflare Tunnel (No Nginx, No Open Ports, Automatic Free SSL)\n"
printf "  2) Custom Domain / Existing Reverse Proxy (Nginx, Caddy, Traefik, Apache)\n"
printf "  3) Caddy Web Server (Zero-config Let's Encrypt SSL, No Nginx)\n"
printf "  4) Skip / Local only for now (Configure later)\n"
EXPOSE_METHOD="$(prompt "Select option (1-4)" "1")"

WEBAPP_URL=""
CF_TUNNEL_MODE=""
CF_TUNNEL_TOKEN=""
CADDY_DOMAIN=""

case "$EXPOSE_METHOD" in
  1)
    info "Cloudflare Tunnel Setup (No Nginx needed)"
    if confirm "Do you have a Cloudflare Tunnel Token (from Zero Trust dashboard)"; then
      CF_TUNNEL_MODE="token"
      CF_TUNNEL_TOKEN="$(prompt "Cloudflare Tunnel Token (starts with eyJh...)")"
      RAW_URL="$(prompt "Public HTTPS hostname you routed in Cloudflare (e.g. https://shop.example.com)")"
      WEBAPP_URL="$(normalize_webapp_url "$RAW_URL")"
    else
      CF_TUNNEL_MODE="quick"
      info "A free Cloudflare Quick Tunnel will be launched automatically during installation."
      info "It provides a public https://*.trycloudflare.com URL without needing a domain or Nginx."
    fi
    ;;
  2)
    info "Custom Domain / Existing Reverse Proxy"
    printf "Enter your public HTTPS URL (e.g. https://shop.example.com):\n"
    RAW_URL="$(prompt_optional "Public HTTPS URL" "")"
    WEBAPP_URL="$(normalize_webapp_url "$RAW_URL")"
    ;;
  3)
    info "Caddy Web Server Setup (Automatic SSL, No Nginx)"
    CADDY_DOMAIN="$(prompt "Your domain name pointing to this server IP (e.g. shop.example.com)")"
    CADDY_DOMAIN="$(printf '%s' "$CADDY_DOMAIN" | sed -E 's#^https?://##; s#/.*$##')"
    WEBAPP_URL="https://$CADDY_DOMAIN"
    ;;
  *)
    info "Skipping internet tunnel configuration. Mini App will run on port $WEBAPP_PORT locally."
    WEBAPP_URL=""
    ;;
esac
printf '\n'

# --- 4. Store Branding & Support ---
info "4. Store Branding & Support"
BRAND_NAME="$(prompt "Store / Brand display name" "فروشگاه")"
SUPPORT_CONTACT="$(prompt_optional "Support Telegram username or link (optional, e.g. @MySupport)" "")"
printf '\n'

# --- 5. Payment Methods Configuration ---
info "5. Payment Methods Configuration"
printf "Enter Card-to-Card payment info for manual receipts (press Enter to keep defaults):\n"
CARD_NUMBER="$(prompt_optional "Card Number (شماره کارت بانکی)" "")"
CARD_HOLDER="$(prompt_optional "Card Holder Name (نام صاحب حساب)" "")"

printf "\nDo you want to configure an Online Payment Gateway now?\n"
printf "  1) None / Skip (use manual card payments or configure later in admin panel)\n"
printf "  2) Zibal (درگاه زیبال)\n"
printf "  3) Zarinpal (درگاه زرین‌پال)\n"
GATEWAY_CHOICE="$(prompt "Select option (1-3)" "1")"

ZIBAL_MERCHANT=""
ZIBAL_SANDBOX="0"
ZARINPAL_MERCHANT=""
ZARINPAL_SANDBOX="0"

if [[ "$GATEWAY_CHOICE" == "2" ]]; then
  info "Configuring Zibal..."
  ZIBAL_MERCHANT="$(prompt "Zibal Merchant ID (use 'zibal' for test)" "zibal")"
  if confirm "Enable Zibal Sandbox (test) mode"; then
    ZIBAL_SANDBOX="1"
  fi
elif [[ "$GATEWAY_CHOICE" == "3" ]]; then
  info "Configuring Zarinpal..."
  ZARINPAL_MERCHANT="$(prompt "Zarinpal Merchant ID (36-character UUID)" "")"
  if confirm "Enable Zarinpal Sandbox (test) mode"; then
    ZARINPAL_SANDBOX="1"
  fi
fi

# --- Summary ---
printf '\n============================================================\n Configuration Summary:\n============================================================\n'
printf '  Admin ID:            %s\n' "$ADMIN_ID"
printf '  X-UI API URL:        %s\n' "$XUI_API_URL"
printf '  X-UI Base Path:      %s\n' "$XUI_BASE_PATH"
printf '  Subscription:        %s%s\n' "$XUI_SUB_SERVER_URL" "$XUI_SUB_PATH"
printf '  Mini App Port:       %s\n' "$WEBAPP_PORT"
if [[ "$CF_TUNNEL_MODE" == "quick" ]]; then
  printf '  Internet Exposure:   Cloudflare Quick Tunnel (auto-allocated)\n'
elif [[ "$CF_TUNNEL_MODE" == "token" ]]; then
  printf '  Internet Exposure:   Cloudflare Tunnel Token -> %s\n' "$WEBAPP_URL"
elif [[ "$EXPOSE_METHOD" == "3" ]]; then
  printf '  Internet Exposure:   Caddy Web Server -> https://%s\n' "$CADDY_DOMAIN"
else
  printf '  Mini App Public URL: %s\n' "${WEBAPP_URL:-not set (local only)}"
fi
printf '  Brand Name:          %s\n' "$BRAND_NAME"
[[ -z "$SUPPORT_CONTACT" ]] || printf '  Support Contact:     %s\n' "$SUPPORT_CONTACT"
[[ -z "$CARD_NUMBER" ]] || printf '  Card Number:         %s (%s)\n' "$CARD_NUMBER" "${CARD_HOLDER:-N/A}"
[[ -z "$ZIBAL_MERCHANT" ]] || printf '  Gateway:             Zibal (Merchant: %s, Sandbox: %s)\n' "$ZIBAL_MERCHANT" "$ZIBAL_SANDBOX"
[[ -z "$ZARINPAL_MERCHANT" ]] || printf '  Gateway:             Zarinpal (Merchant: %s, Sandbox: %s)\n' "$ZARINPAL_MERCHANT" "$ZARINPAL_SANDBOX"
printf '  Installation Dir:    %s\n' "$APP_DIR"
printf '============================================================\n\n'
confirm "Continue installation" || { warn "Installation cancelled."; exit 0; }

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3 python3-pip python3-venv curl git ca-certificates rsync
mkdir -p "$APP_DIR"

if [[ "$SOURCE_DIR" != "$APP_DIR" ]]; then
  info "Installing the complete SpeedyBot repository..."
  rsync -a --delete \
    --exclude '.git/' \
    --exclude '.env' \
    --exclude '.venv/' \
    --exclude 'speedping.db' \
    --exclude 'speedping.db-wal' \
    --exclude 'speedping.db-shm' \
    --exclude 'backups/' \
    --exclude 'run.sh' \
    --exclude '.deployed_commit' \
    --exclude 'node_modules/' \
    --exclude 'webapp/node_modules/' \
    "$SOURCE_DIR/" "$APP_DIR/"
else
  info "Source is already $APP_DIR; using the repository in place."
fi
cd "$APP_DIR"

python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip setuptools wheel >/dev/null
if [[ -f requirements.txt ]]; then
  ./.venv/bin/python -m pip install -r requirements.txt
else
  ./.venv/bin/python -m pip install pyTelegramBotAPI requests 'qrcode[pil]' fastapi uvicorn python-multipart
fi
./.venv/bin/python -m py_compile main.py speedybot/*.py
bash -n install.sh
[[ ! -f update.sh ]] || bash -n update.sh

# --- Configure Internet Tunnel / Reverse Proxy ---
if [[ "$CF_TUNNEL_MODE" == "quick" ]]; then
  info "Launching Cloudflare Quick Tunnel..."
  CF_URL="$(setup_cf_quick_tunnel "$WEBAPP_PORT" || true)"
  if [[ -n "$CF_URL" ]]; then
    WEBAPP_URL="$CF_URL"
  fi
elif [[ "$CF_TUNNEL_MODE" == "token" ]]; then
  info "Configuring Cloudflare Tunnel service..."
  setup_cf_token_tunnel "$CF_TUNNEL_TOKEN" || true
elif [[ "$EXPOSE_METHOD" == "3" && -n "$CADDY_DOMAIN" ]]; then
  info "Configuring Caddy web server..."
  setup_caddy_proxy "$CADDY_DOMAIN" "$WEBAPP_PORT" || true
fi

cat > "$ENV_FILE" <<EOF
export BOT_TOKEN=$(printf '%q' "$BOT_TOKEN")
export ADMIN_ID=$(printf '%q' "$ADMIN_ID")
export XUI_API_URL=$(printf '%q' "$XUI_API_URL")
export XUI_BASE_PATH=$(printf '%q' "$XUI_BASE_PATH")
export XUI_BEARER_TOKEN=$(printf '%q' "$XUI_BEARER_TOKEN")
export XUI_SUB_SERVER_URL=$(printf '%q' "$XUI_SUB_SERVER_URL")
export XUI_SUB_PATH=$(printf '%q' "$XUI_SUB_PATH")
export WEBAPP_PORT=$(printf '%q' "${WEBAPP_PORT:-8080}")
export WEBAPP_HOST='0.0.0.0'
export WEBAPP_URL=$(printf '%q' "${WEBAPP_URL:-}")
EOF
chmod 600 "$ENV_FILE"

info "Testing 3x-ui API authentication (read-only)..."
set +e
PREFLIGHT="$(XUI_API_URL="$XUI_API_URL" XUI_BASE_PATH="$XUI_BASE_PATH" XUI_BEARER_TOKEN="$XUI_BEARER_TOKEN" "$APP_DIR/.venv/bin/python3" - <<'PY'
import os, requests, sys
base=os.environ['XUI_API_URL'].rstrip('/'); path=os.environ.get('XUI_BASE_PATH','').strip(); prefix='' if path in ('','/') else '/'+path.strip('/'); url=f"{base}{prefix}/panel/api/inbounds/list"
try: r=requests.get(url,headers={'Authorization':'Bearer '+os.environ['XUI_BEARER_TOKEN'],'Accept':'application/json'},timeout=15)
except Exception as e: print(f"NETWORK|{type(e).__name__}: {e}"); sys.exit(20)
print(f"HTTP_{r.status_code}|{url}|{(r.text or '').replace(chr(10),' ')[:400]}")
try: ok=r.status_code==200 and bool(r.json().get('success'))
except Exception: ok=False
if ok: sys.exit(0)
if r.status_code in (401,403): sys.exit(21)
if r.status_code==404: sys.exit(22)
sys.exit(23)
PY
)"; CODE=$?; set -e
[[ "$CODE" -eq 0 ]] || fail "3x-ui API preflight failed: $PREFLIGHT"
ok "3x-ui API preflight passed."

info "Initializing database and saving configuration..."
set +e
"$APP_DIR/.venv/bin/python3" - <<PY
import sqlite3

try:
    from speedybot import storage
    storage.init_db()

    conn = sqlite3.connect("$APP_DIR/speedping.db", timeout=15)
    cur = conn.cursor()

    def set_kv(key, val):
        cur.execute("INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(val)))

    if "$WEBAPP_URL":
        set_kv("webapp_url", "$WEBAPP_URL")
    if "$BRAND_NAME":
        set_kv("brand_name", "$BRAND_NAME")
        set_kv("webapp_title", "$BRAND_NAME")
    if "$CARD_NUMBER":
        set_kv("card_number", "$CARD_NUMBER")
    if "$CARD_HOLDER":
        set_kv("card_holder", "$CARD_HOLDER")
    if "$SUPPORT_CONTACT":
        set_kv("support_contact", "$SUPPORT_CONTACT")

    if "$GATEWAY_CHOICE" == "2" and "$ZIBAL_MERCHANT":
        set_kv("gateway_zibal_enabled", "1")
        set_kv("gateway_zibal_merchant", "$ZIBAL_MERCHANT")
        set_kv("gateway_zibal_sandbox", "$ZIBAL_SANDBOX")
    elif "$GATEWAY_CHOICE" == "3" and "$ZARINPAL_MERCHANT":
        set_kv("gateway_zarinpal_enabled", "1")
        set_kv("gateway_zarinpal_merchant", "$ZARINPAL_MERCHANT")
        set_kv("gateway_zarinpal_sandbox", "$ZARINPAL_SANDBOX")

    conn.commit()
    conn.close()
    print("Database settings updated successfully.")
except Exception as e:
    print(f"Notice during db configuration: {e}")
PY
set -e

write_runner
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=SpeedyBot Telegram Bot
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
ExecStart=$RUNNER_FILE
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"
sleep 4
if systemctl is-active --quiet "$SERVICE_NAME"; then
  ok "Installation completed successfully."
  systemctl --no-pager --full status "$SERVICE_NAME" || true
else
  journalctl -u "$SERVICE_NAME" -n 80 --no-pager || true
  fail "Service failed to start."
fi

printf '\n============================================================\n'
printf ' ✅ SpeedyBot v5.0.0 is running!\n'
printf '============================================================\n'

if [[ -n "$WEBAPP_URL" ]]; then
  printf '\n🌐 Telegram Mini App is accessible at:\n'
  printf '   %s\n' "$WEBAPP_URL"

  if [[ "$CF_TUNNEL_MODE" == "quick" ]]; then
    printf '\n   [Cloudflare Quick Tunnel Active]\n'
    printf '   • Service: speedybot-tunnel.service\n'
    printf '   • No Nginx or open ports needed!\n'
  elif [[ "$CF_TUNNEL_MODE" == "token" ]]; then
    printf '\n   [Cloudflare Tunnel Active]\n'
    printf '   • Service: cloudflared.service\n'
  elif [[ "$EXPOSE_METHOD" == "3" ]]; then
    printf '\n   [Caddy Web Server Active]\n'
    printf '   • Service: caddy.service (Auto Let'\''s Encrypt SSL active)\n'
  fi

  printf '\n📱 Configure Telegram Menu Button in @BotFather:\n'
  printf '   1. Open @BotFather in Telegram\n'
  printf '   2. Send /setmenubutton -> pick your bot\n'
  printf '   3. Enter URL: %s\n' "$WEBAPP_URL"
  printf '   4. Button Title: 🚀 ورود به اپلیکیشن\n\n'
else
  printf '\n💡 To run the Mini App through the Internet without Nginx:\n'
  printf '   • Free Cloudflare Quick Tunnel: Run "cloudflared tunnel --url http://localhost:%s"\n' "$WEBAPP_PORT"
  printf '   • Zero-install Pinggy tunnel:   Run "ssh -p 443 -R0:localhost:%s a.pinggy.io"\n' "$WEBAPP_PORT"
  printf '   • Or add WEBAPP_URL="https://your-url" to %s/.env and restart.\n\n' "$APP_DIR"
fi

printf 'Useful commands:\n'
printf '  • Check logs:    journalctl -u %s -f\n' "$SERVICE_NAME"
printf '  • Restart bot:   systemctl restart %s\n' "$SERVICE_NAME"
printf '  • Manage bot:    send /sudoadmin to the bot from Telegram\n'
printf '============================================================\n\n'
