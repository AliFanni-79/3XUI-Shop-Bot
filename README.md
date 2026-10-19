# VizzPN Shop Bot v26.2.0

<p align="center">
  <strong>Telegram Mini App & Automated Sales Platform for 3x-ui / Sanaei</strong><br>
  Vue 3 Mini App • Custom Plan Builder • Zibal & Zarinpal Gateways • Automated Provisioning • Free Trial • Wallet • Control Center
</p>

<p align="center">
  <a href="README_FA.md">🇮🇷 راهنمای فارسی</a> ·
  <a href="SECURITY.md">Security</a> ·
  <a href="LICENSE">License</a>
</p>

> **Author / Maintainer:** **AliFanni-79**  
> Telegram: **@AliFanni_79**  
> Official repository: **https://github.com/AliFanni-79/SpeedyBot**

VizzPN Shop Bot turns Telegram into a high-performance storefront, self-service customer portal, and operations console for **3x-ui / Sanaei**. Built as a hybrid application combining a modern **Telegram Mini App (Vue 3 + Tailwind CSS)** and a streamlined Telegram bot, it provides automatic client provisioning, an interactive custom plan builder, online payment gateway integrations (Zibal & Zarinpal), wallet checkouts, and a Telegram-first administrative dashboard.

## Architecture

VizzPN Shop Bot runs as a unified single-process application:

```text
main.py
  ├── TeleBot Polling (Telegram user & admin command handlers)
  └── Uvicorn Daemon Thread (FastAPI REST API + static Vue 3 Mini App on port 8080)
```

The application package is located in `xuishop/` and the compiled single-page frontend is served from `webapp/dist/`.

---

## Table of contents

- [Features](#features)
- [What's New in v26.2.0](#whats-new-in-v2620)
- [Default plans](#default-plans)
- [Telegram Mini App Setup](#telegram-mini-app-setup)
- [Online Payment Gateways](#online-payment-gateways)
- [Custom Plan Builder](#custom-plan-builder)
- [Requirements](#requirements)
- [Before installation](#before-installation)
- [Step-by-step installation](#step-by-step-installation)
- [First-run checklist](#first-run-checklist)
- [Admin Control Center](#admin-control-center)
- [Operating modes](#operating-modes)
- [Plan categories](#plan-categories)
- [Free Trial and inbound routing](#free-trial-and-inbound-routing)
- [Per-user Trial overrides](#per-user-trial-overrides)
- [Connection guides](#connection-guides)
- [Existing services and custom names](#existing-services-and-custom-names)
- [Payments, wallet and marketing](#payments-wallet-and-marketing)
- [Renewals](#renewals)
- [Targeted broadcasts](#targeted-broadcasts)
- [Audit log](#audit-log)
- [Notifications](#notifications)
- [Diagnostics](#diagnostics)
- [Updating](#updating)
- [Upgrading and Maintenance](#upgrading-and-maintenance)
- [Backups and rollback](#backups-and-rollback)
- [Troubleshooting](#troubleshooting)
- [Project layout](#project-layout)
- [Security](#security)
- [License and author](#license-and-author)

---

## Features

### Sales and provisioning

- **Telegram Mini App (TMA)**: Clean, reactive Vue 3 web interface embedded right inside Telegram.
- **Interactive Custom Plan Builder**: Build tailor-made plans (custom durations, GB slider, device limits) with volume & duration discounts.
- **Fair-Use Protection**: Enforces security policies to prevent multi-user reselling abuse.
- **Online Payment Gateways**: Built-in support for **Zibal** and **Zarinpal** with automated instant callbacks and auto-provisioning.
- **Manual Card Transfer**: Receipt upload with admin approval flow.
- **Wallet Checkout**: Instant zero-click purchase using internal wallet balance.
- **Automatic 3x-ui Client Creation**: Instant client generation upon payment verification.
- **Free Trial**: Default 1 GB / 1 day / 1 IP test service.
- **Subscription & Direct Config Delivery**: Immediate delivery of sub links, raw configs, and QR codes.
- **Service Renewal**: Seamless renewal keeping existing client credentials and UUID.

### Customer portal (Mini App + Bot)

- Live traffic remaining and expiry monitoring.
- One-tap copying of subscription URLs and direct proxy links.
- Interactive QR code viewer.
- Full wallet balance management and transaction history.
- Referral / affiliate program with reward links and cashback.
- Discount codes and gift card redemption.
- Step-by-step connection guides for iOS, Android, Windows, and macOS.
- Streamlined Telegram chat keyboard (Active Services, Guides, Support).

### Administration

From `/sudoadmin` or the Mini App Admin Dashboard:

- Plan catalog and interactive builder pricing rules.
- Plan categories and volume packs.
- Payment gateway credentials and toggle switches (Zibal, Zarinpal).
- Free Trial configuration and per-user overrides.
- Inbound selection and routing.
- Operating mode (`NORMAL`, `SALES_PAUSED`, `MAINTENANCE`).
- Targeted user broadcasts.
- Comprehensive audit log.
- Automated backup creation and safe restoration.

---

## What's New in v26.2.0

### 1. Customer Service Management & Interactive Controls
- Complete management modal directly in the Customer Details profile inside the Web Admin Dashboard.
- **Traffic Quota Management**: Edit quota (`totalGB`), reset downloaded/uploaded bytes with one click, or set traffic to unlimited.
- **Concurrent IP Limiter**: Edit and enforce `limitIp` directly in 3x-ui.
- **Expiry Date & Quick Extension**: View formatted expiration date and remaining days; extend by +7, +30, +60, +90 days, set to unlimited, or choose an exact date.
- **Per-Service Inbound Routing**: Selectively map or exclude inbounds for specific customer services with one-click toggles.
- **Instant Client Deletion**: Safely delete clients from the 3x-ui panel (`del/{email}?keepTraffic=0`) while revoking all linked transaction and trial records.

### 2. Plan Inbound Routing Bugfix
- Fixed a bug where inbounds in the Plans list displayed "No inbound available in the panel".
- Both backend and frontend now consistently process inbound tags, remarks, protocols, ports, and selection states.

### 3. Telegram API Rate-Limiting Protection (HTTP 429)
- Implemented an intelligent rate-limit exception handler in `TeleBot.infinity_polling`.
- When Telegram API returns HTTP 429 ("Too Many Requests: retry after X"), polling automatically pauses for `retry_after + 2` seconds instead of busy-spinning every 250ms.

### 4. Resilient Background Services
- Added exception catching and detailed logging for the Uvicorn daemon thread in `main.py`.

---

## What's New in v26.1.0

### 1. CalVer Release & Rebranding
- Formal adoption of **v26.1.0** CalVer versioning scheme.
- Full rebranding to **VizzPN Shop Bot** under **AliFanni-79** (`@AliFanni_79`).
- Complete overhaul of project documentation, license terms, and repository metadata.

### 2. Multi-App Connection Guides with Direct Telegram Intake
- Guides organized by both operating system (Android, iOS, Windows, macOS, Linux, TV) and specific client application (V2RayNG, Streisand, v2rayN, Hiddify, etc.).
- **Direct Telegram Intake Flow**: Admins can submit formatted guides, high-definition photos, and video tutorials directly via Telegram chat without manually handling `file_id` strings or web input limits.
- Interactive Web Admin interface with application name suggestions, media previews, and live editing.
- Responsive client guide portal in the Mini App with tabbed application navigation.

### 3. Telegram Mini App (TMA) Architecture
- Modern SPA built with **Vue 3, Tailwind CSS, and Pinia**.
- Deep integration via Telegram WebApp SDK (`window.Telegram.WebApp`).
- Cryptographically verified HMAC-SHA256 signature validation of Telegram `initData`.
- Embedded FastAPI server running asynchronously in a background thread inside `main.py`.

### 4. Interactive Custom Plan Builder
- Users are no longer limited to fixed plans; they can customize:
  1. **Duration**: 1, 3, 6, or 12 months with duration tier discounts (e.g., 5%, 10%, 20%).
  2. **Traffic**: Custom GB slider (default 1,000 Tomans/GB, volume discounts for >50GB, >100GB, >300GB) or Unlimited traffic (capped at 1,000 GB for fair use).
  3. **User Limit**: 1 to 5 devices or Unlimited.
  4. **Fair-Use Safeguard**: Prohibits simultaneous unlimited traffic + unlimited users to prevent reselling abuse.
  5. **Instant Price Calculation**: Transparent breakdown showing original vs discounted price.

### 5. Online Payment Gateways (Zibal & Zarinpal)
- Native integration with Iranian payment gateways (Zibal and Zarinpal).
- Support for sandbox/testing mode and live merchant IDs.
- Automated web callback handlers (`/api/payment/callback/zibal` and `zarinpal`).
- Instant automated provisioning upon verified payment without requiring manual receipt checks.
- Manual card-to-card transfer with receipt photo verification workflow.
- Internal wallet balance support for instant zero-click renewals and purchases.

### 6. Administrative Console & Operations Automation
- Centralized Admin Dashboard covering live orders, user CRM, trial policies, inbound routing, and audit logs.
- Interactive diagnostic tools: `/xuidiag` (API verification), `/groupsdiag` (client group reconciliation), and `/notifydiag` (service health monitor).
- Non-destructive automated backups (`restore.sh`, `restore.py`) and atomic source updates (`update.sh`, `upgrade.sh`).

---

## Default plans

Fresh databases receive these seed plans:

| Plan | Duration | Traffic | IP limit | Default price |
|---|---:|---:|---:|---:|
| Unlimited - 1 user | 30 days | Unlimited | 1 | 250,000 Toman |
| Unlimited - 2 users | 30 days | Unlimited | 2 | 300,000 Toman |
| Unlimited - 3 users | 30 days | Unlimited | 3 | 350,000 Toman |

In addition to preset plans, users can build custom plans dynamically through the Telegram Mini App.

---

## Telegram Mini App Setup

VizzPN Shop Bot embeds a high-performance Vue 3 Single Page Application directly inside Telegram.

### Configuration
In `/root/SpeedyBot/.env`:
```bash
export WEBAPP_PORT='8080'
export WEBAPP_HOST='0.0.0.0'
export WEBAPP_URL='https://bot.yourdomain.com'
```

### Internet Exposure (No Nginx Required)

Telegram Mini Apps strictly require a public **HTTPS** URL. VizzPN Shop Bot supports multiple zero-Nginx options out of the box during both `install.sh` and `update.sh`:

1. **Option 1: Cloudflare Quick Tunnel (Recommended — No Nginx, No Domain, No Open Ports)**
   - Automatically installs `cloudflared` and runs a background systemd service (`speedybot-tunnel.service`).
   - Instantly provisions a free, public `https://*.trycloudflare.com` URL with valid Cloudflare SSL.
   - Zero open firewall ports, zero DNS setup, and zero web server configuration needed.

2. **Option 2: Cloudflare Zero Trust Named Tunnel (Custom Domain, No Open Ports)**
   - Connects to your Cloudflare Zero Trust account via tunnel token (`eyJh...`).
   - Routes your custom domain (e.g., `https://shop.yourdomain.com`) directly to `127.0.0.1:8080`.
   - High security with complete end-to-end encryption and zero inbound open ports.

3. **Option 3: Caddy Web Server (Zero-Config Automatic Let's Encrypt SSL, No Nginx)**
   - Automatically installs Caddy and provisions `/etc/caddy/Caddyfile`.
   - Obtains and automatically renews free Let's Encrypt SSL certificates for your domain in a single command.

4. **Option 4: Traditional Reverse Proxy (Nginx, Traefik, HAProxy, etc.)**
   - Point your existing reverse proxy to `http://127.0.0.1:8080`.
   - Example Nginx block:
     ```nginx
     location / {
         proxy_pass http://127.0.0.1:8080;
         proxy_set_header Host $host;
         proxy_set_header X-Real-IP $remote_addr;
     }
     ```

### Configure `@BotFather`
- Send `/setmenubutton` to `@BotFather`.
- Select your bot.
- Enter your public Mini App URL (e.g., `https://xxxx.trycloudflare.com` or `https://shop.yourdomain.com`).
- Set the button title to `🚀 باز کردن فروشگاه` or your preference.
- The Menu button next to the chat bar in Telegram will now open your Mini App directly.

### Authentication & Security
- The Mini App uses Telegram's `initData` passed automatically by Telegram WebApp client.
- The backend verifies HMAC-SHA256 signatures against `BOT_TOKEN` so no passwords or tokens are stored in local storage.
- Administrative tabs in the Mini App are accessible exclusively to authenticated `ADMIN_ID` accounts.

---

## Online Payment Gateways & Telegram Stars

VizzPN Shop Bot natively supports automated online payment gateways, Telegram Stars, manual card-to-card receipts, and internal wallet payments:

1. **Telegram Stars (`XTR`)**
   - Native in-app payment directly inside Telegram using Stars.
   - **No external merchant setup required**: All Stars paid by users are directly credited to the bot owner's balance in Telegram / `@BotFather`.
   - Configurable exchange rate (Tomans per Star, default: 1,500 Tomans/Star).
   - Native invoice checkout modal via `window.Telegram.WebApp.openInvoice`.
   - Automated instant service provisioning upon successful payment.

2. **Zibal (`zibal.ir`)**
   - Instant Iranian payment gateway with callback verification.
   - Admin config: Merchant ID, Sandbox Mode (on/off), Active (on/off).

3. **Zarinpal (`zarinpal.com`)**
   - Standard merchant payment gateway.
   - Admin config: Merchant ID, Sandbox Mode (on/off), Active (on/off).

4. **Card-to-Card Transfer**
   - Manual bank card transfer with receipt upload and admin review.

### Enabling Gateways & Stars
- Open the Mini App as Admin (or navigate to `/sudoadmin`) → **روش‌های پرداخت**.
- Enable Telegram Stars, set your desired Tomans-per-Star exchange rate, or configure Zibal/Zarinpal credentials.
- Customers in the Mini App checkout modal can choose their preferred payment method for instant automated activation.

---

## Mini App Admin Control Center

The Mini App Admin Panel provides a comprehensive, touch-friendly operations dashboard matching all `/sudoadmin` bot commands:

- **🖥️ Server Hardware & Panel Status**: Live monitoring of CPU load averages, RAM memory usage, Disk storage, OS uptime, Python runtime, and 3x-ui API connection health with real-time latency ping.
- **💳 Payment Methods & Stars**: Configure card-to-card details, Zibal & Zarinpal credentials, and Telegram Stars toggles with custom exchange rates.
- **🛠️ Custom Plan Builder Defaults**: Fine-tune base monthly pricing, duration tier discounts (3m, 6m, 12m), GB traffic pricing, traffic volume discounts, and multi-user device limits.
- **📦 Preset Plans Management (CRUD)**: Create new preset plans, edit pricing, days, traffic GB, or device limits, toggle active/inactive status, and reorder catalog display order.
- **👥 User Directory & Balance Control**: Search users by Telegram ID, view profiles and creation dates, adjust wallet balance with automated user notification and audit notes, or toggle account access.
- **🚫 Blacklist Management**: Inspect blocked users, add blocks with detailed administrative reasons, or unblock accounts.
- **👮 Admin Permissions**: Manage co-admins with strict Owner protection (Owner cannot be removed).
- **💾 Hot SQLite Database Backups**: Create instantaneous, zero-downtime hot SQLite database snapshots stored safely in `backups/`.
- **⚙️ Operating Modes**: Switch between `NORMAL`, `SALES_PAUSED` (with customizable pause notice), and `MAINTENANCE`.
- **📢 Targeted Broadcasts**: Dispatch announcements to users directly from the web interface.
- **🎨 Custom Branding**: Customize web app header and browser tab titles on the fly.

---

## Custom Plan Builder

Customers can build their own custom subscriptions inside the Mini App:

1. **Duration**: 1, 3, 6, or 12 months with duration discounts (3 months: 5%, 6 months: 10%, 12 months: 20%).
2. **Traffic**: Custom GB slider (default 1,000 Tomans/GB, volume discounts for >50GB: 5%, >100GB: 15%, >300GB: 30%) or Unlimited (capped at 1,000 GB for fair use).
3. **User Limit**: 1 to 5 devices (defaults: 1 device free, 2: 20k, 3: 35k, 4: 45k, 5: 50k) or Unlimited (65k).
4. **Anti-Abuse Fair Use**: Prohibits choosing Unlimited Traffic and Unlimited Users simultaneously to protect server resources and prevent unauthorized resale.
5. **Real-time Price Preview**: Shows full pricing calculations and applied discounts dynamically before purchase.

---

## Requirements

Recommended production setup:

- Ubuntu **24.04 LTS**.
- Python 3.12.
- Current 3x-ui / Sanaei with `/panel/api/*` API.
- Bearer API Token from 3x-ui.
- Telegram Bot Token from `@BotFather`.
- Numeric Telegram ID for the Owner.
- Working Subscription service if Subscription URLs are used.
- Outbound connectivity from the VPS to Telegram and the panel.

VizzPN Shop Bot uses Long Polling, so no Telegram webhook port is required.

---

## Before installation

### 1. Create the Telegram bot

In `@BotFather`:

1. Send `/newbot`.
2. Choose a display name.
3. Choose a username ending in `bot`.
4. Copy and securely store the Bot Token.

Never publish the token in a GitHub Issue, screenshot, README, log or commit.

### 2. Find the Owner Telegram ID

You need the **numeric Telegram user ID**, not the username. This becomes the initial `ADMIN_ID` and Owner account.

### 3. Create a 3x-ui Bearer API token

Inside 3x-ui:

```text
Settings → Security → API Token
```

Create a token and save the **plaintext Token value**.

The following are not the Bearer Token:

- Token display name.
- Panel password.
- Hidden web path.

### 4. API URL vs Base Path

If the panel opens at:

```text
https://panel.example.com:2053/secret-panel/
```

Installer values should normally be:

```text
X-UI API base URL: https://panel.example.com:2053
X-UI security base path: /secret-panel
```

If there is no hidden path:

```text
X-UI security base path: /
```

Do not duplicate the hidden path inside the base URL.

### 5. Subscription settings

If a real user Subscription URL looks like:

```text
https://sub.example.com:2096/sub/ABC123
```

enter:

```text
Subscription server base URL: https://sub.example.com:2096
Subscription URI path: /sub/
```

Use the actual path configured in your 3x-ui installation.

---

## Step-by-step installation

Log in as `root`:

```bash
apt update
apt install -y git

git clone https://github.com/AliFanni-79/SpeedyBot.git /root/SpeedyBot
cd /root/SpeedyBot
chmod +x install.sh update.sh
./install.sh
```

The Installer asks for:

1. Telegram Bot Token.
2. Telegram Admin numeric ID.
3. X-UI API base URL.
4. X-UI security base path.
5. Panel Bearer API Token.
6. Subscription server base URL.
7. Subscription URI path.
8. Telegram Mini App port (default: 8080).
9. Telegram Mini App Internet exposure method (Cloudflare Quick/Named Tunnel, Caddy, Custom Domain, or Local).

Before systemd is enabled, Installer performs a **read-only 3x-ui API preflight**. Authentication/base-path mistakes are caught before the bot is considered installed.

### Runtime files

Important mutable runtime state:

```text
/root/SpeedyBot/.env
/root/SpeedyBot/.venv/
/root/SpeedyBot/speedping.db
/root/SpeedyBot/speedping.db-wal
/root/SpeedyBot/speedping.db-shm
/root/SpeedyBot/run.sh
/root/SpeedyBot/backups/
```

The systemd service is:

```text
xui-bot.service
```

The runner executes:

```text
/root/SpeedyBot/main.py
```

### Service status

```bash
systemctl status xui-bot.service --no-pager -l
```

### Live logs

```bash
journalctl -u xui-bot.service -f
```

### Restart

```bash
systemctl restart xui-bot.service
```

---

## First-run checklist

From the Owner account:

```text
/start
/sudoadmin
```

Before accepting real customers:

1. Replace example payment/card data.
2. Verify plan prices, duration, traffic and IP limits.
3. Create/review plan categories.
4. Review Trial & Inbounds.
5. Enable/disable Trial as required.
6. Select inbounds for Trial and each plan.
7. Reconcile `Customers` and `Trial` groups.
8. Create Android/iOS/Windows/macOS/Linux/TV connection guides.
9. Review CRM and Trial follow-up.
10. Configure verification/channel membership if required.
11. Confirm operating mode is `NORMAL`.
12. Review button styles.
13. Configure Audit Chat only if needed.
14. Run `/xuidiag`.
15. Run `/groupsdiag`.
16. Run `/notifydiag`.
17. Test one real Trial.
18. Test one complete purchase flow before heavy production use.

---

## Admin Control Center

Main command:

```text
/sudoadmin
```

Useful diagnostics:

```text
/xuidiag
/groupsdiag
/notifydiag
```

- `/xuidiag` — read-only panel API diagnostics.
- `/groupsdiag` — live Client Group counts.
- `/notifydiag` — run the service monitor once.

---

## Operating modes

### NORMAL

All configured functions are available.

### SALES_PAUSED

New purchase, renewal and volume-add actions are blocked while Account, Guide and Support remain available.

### MAINTENANCE

New purchase and Trial issuance are blocked while existing-account visibility, Guide and Support remain available.

---

## Plan categories

Create categories from `/sudoadmin`, then move Plan IDs to the appropriate category. Existing uncategorized plans are assigned to `عمومی` during migration.

---

## Free Trial and inbound routing

From:

```text
/sudoadmin → Trial & Inbounds
```

admins can:

- Enable/disable Trial.
- Select exact Trial inbounds.
- Select exact inbounds independently for each plan.
- Reset a scope to all active inbounds.

If a scope has no explicit inbound rows, VizzPN Shop Bot uses **all active inbounds** for backward compatibility.

### Direct config vs Subscription

Direct proxy links are kept separate from Subscription URLs.

Direct-link schemes can include:

```text
vless://
vmess://
trojan://
ss://
hysteria://
hysteria2://
hy2://
```

HTTP/HTTPS Subscription URLs are shown only as Subscription links.

If a Direct Address is wrong, compare it with 3x-ui **Copy URL**. If both contain the same wrong host, fix the Inbound Share Address/Public Host in 3x-ui.

---

## Per-user Trial overrides

Before a user's first Trial, an admin can enter:

```text
TelegramID | VolumeGB | Days | IPLimit | Optional note
```

Example:

```text
123456789 | 5 | 3 | 2 | VIP lead
```

The normal Trial Inbound selection still applies.

---

## Connection guides

VizzPN Shop Bot features an advanced, multi-platform connection guide system tailored for both administrators and end users:

### Supported Platforms & Applications
Admins can publish guides organized by platform and specific client application:
- **Android**: V2RayNG, Hiddify, Streisand, etc.
- **iPhone / iOS**: Streisand, FoXray, V2Box, etc.
- **Windows**: v2rayN, Hiddify, Nekoray, etc.
- **macOS**: V2Box, FoXray, etc.
- **Linux**: Command line, GUI clients.
- **Android TV / TV Box**: TV-compatible clients.

### Guide Content Types
Each guide can contain:
- Formatted text instructions and direct download links.
- High-definition photos with descriptive captions.
- Video tutorials with step-by-step captions.

### Effortless Direct Telegram Bot Submission
Instead of manually typing long guides or copying Telegram `file_id` strings into a web form:
1. In the Web Admin Dashboard, click **ارسال درخواست ثبت راهنما به تلگرام من**.
2. The bot sends an interactive prompt directly to the admin in Telegram chat.
3. The admin sends or forwards the guide message directly in Telegram — including long formatted text, photos, or video tutorials with captions.
4. The bot automatically extracts the content and Telegram `file_id`, saving the guide under the designated platform and app immediately.

### User Experience
- Customers can access step-by-step guides from either the Telegram chat keyboard (`📚 راهنما و سوالات`) or the Mini App (`📲 راهنمای اتصال`).
- Customers can filter guides by operating system and preferred client app with one-tap configuration copying.

---

## CRM and Trial follow-up

### Acquisition survey

After the first successful paid purchase, VizzPN Shop Bot can ask how the user found the service. Default choices include friend recommendation, Telegram search, channel ads, Instagram, web/search, returning customer and other.

### Trial follow-up

After Trial expiry/exhaustion, the bot can wait for the configured delay, check whether the user already purchased, and only follow up non-buyers.

Reasons can include quality, price, setup difficulty, buying later, no current need, ready to buy, or other. Responses can lead to purchase/support CTAs.

This CRM path can operate independently from normal expiry-warning messages.

---

## Existing services and custom names

### Custom Client name

When enabled, buyers can choose a custom Client name.

Rules:

- 3–40 characters.
- ASCII letters/numbers plus `.`, `_`, `-`.
- Checked against local VizzPN Shop Bot data.
- Checked against the connected 3x-ui panel before checkout.

### Link a previously purchased service

A user can enter an existing 3x-ui Client email/name from Account.

Ownership rules:

- Matching panel `tgId` → automatic claim.
- Non-matching `tgId` → admin approval required.
- One panel Client can be linked to only one VizzPN Shop Bot account.

---

## Payments, wallet and marketing

### Manual/card payment

The bot shows configured payment data, receives a receipt and waits for admin approval before provisioning.

### Wallet

- Balance.
- Ledger/history.
- Admin credit/debit.
- Wallet checkout.

### Affiliate

- Permanent Telegram referral link.
- Referrer stored on first registration.
- Commission after qualifying approved/provisioned purchase.
- Exactly-once commission protection.

### Cashback / Discount / Gift

Admins can configure cashback, percentage/fixed discount codes, minimum purchase, expiry/usage limits and wallet-credit Gift Codes.

---

## Renewals

Renewal keeps the same service identity and:

- Preserves remaining time on early renewal.
- Updates quota/IP limit for the selected plan.
- Re-enables the Client.
- Resets traffic for the new period.
- Synchronizes the Client to the renewal plan's configured inbounds.

---

## Groups

Default mapping:

```text
Paid service → Customers
Free Trial   → Trial
```

Live check:

```text
/groupsdiag
```

---

## Targeted broadcasts

Available audiences include all active users, paying customers, Trial leads, expired-Trial leads and never-purchased users.

Telegram `copy_message` is used so text/photo/video/document messages can be reused. Always test a small audience before sending to everyone.

---

## Audit log

Important operations are stored in SQLite. An optional private Telegram Chat ID can receive mirrored events if the bot has permission to post there.

---

## Panel snapshot

A read-only JSON export can be generated from the connected 3x-ui panel. Snapshot files contain sensitive service data and must not be posted publicly.

---

## Notifications

The service monitor can send one-time events for:

- Traffic warning near 90%.
- Paid-service expiry warning.
- Trial expiry warning.
- Traffic exhausted.
- Time expired.

Notification claims are stored in SQLite so restarts do not intentionally duplicate the same event.

---

## Diagnostics

### Bot does not respond

```bash
systemctl status xui-bot.service --no-pager -l
journalctl -u xui-bot.service -n 200 --no-pager
```

### 401 / 403

Verify the **plaintext Bearer API Token**. Do not use the Token name or panel password.

### 404

Verify:

- API Base URL.
- Hidden Base Path.
- Reverse-proxy routing.
- Panel API availability/version.

Example:

```text
Panel: https://panel.example.com:2053/secret/
XUI_API_URL=https://panel.example.com:2053
XUI_BASE_PATH=/secret
```

### Duplicate bot processes

```bash
systemctl show xui-bot.service -p NRestarts
pgrep -af 'python.*main.py'
```

Only the systemd-managed process should normally use the production Bot Token.

---

## Updating

The updater synchronizes the **complete repository**, not a hand-maintained list of files.

### Check

```bash
cd /root/SpeedyBot
./update.sh --check
```

### Update

```bash
./update.sh
```

### Force redeploy

```bash
./update.sh --force
```

### What the updater does

1. Re-executes itself from `/tmp` so it can safely replace its own file.
2. Resolves the current GitHub branch commit.
3. Clones the complete repository into a temporary directory.
4. Validates `main.py`, every `xuishop/*.py`, `install.sh` and `update.sh`.
5. Installs dependencies before downtime.
6. Stops the systemd service.
7. Creates a complete rollback copy of the deployed application.
8. Backs up `.env` and SQLite DB/WAL/SHM.
9. Uses `rsync --delete` to make `/root/SpeedyBot` match the published repository.
10. Preserves `.env`, `.venv/`, SQLite runtime files, `backups/`, `run.sh` and `.deployed_commit`.
11. Rewrites `run.sh` to execute `main.py`.
12. Restarts systemd and checks service health / immediate restart loops.
13. Restores the previous complete application if deployment fails.

Because `--delete` is used for source synchronization, old version-specific files are removed automatically when they no longer exist in GitHub.

---

## Upgrading and Maintenance

To check for updates or upgrade your production installation:

```bash
cd /root/SpeedyBot
./update.sh --check
./update.sh
```

After an upgrade completes, verify the runtime:

```bash
cat VERSION.txt
cat run.sh
systemctl status xui-bot.service --no-pager -l
journalctl -u xui-bot.service -n 150 --no-pager
```

Expected active version:

```text
26.2.0
```

Runner target:

```text
/root/SpeedyBot/main.py
```

All updates are atomic and non-destructive:
- Database schema migrations run automatically and preserve all customer, order, wallet, and service records.
- Complete rollback snapshots are created before changes are applied in `/root/SpeedyBot/backups/`.
- If a deployment failure occurs, the previous release is automatically restored without downtime.

---

## Backups and rollback

Deployment backups are stored under:

```text
/root/SpeedyBot/backups/deploy-YYYYMMDD-HHMMSS/
```

Important runtime state:

```text
/root/SpeedyBot/.env
/root/SpeedyBot/speedping.db
/root/SpeedyBot/speedping.db-wal
/root/SpeedyBot/speedping.db-shm
/root/SpeedyBot/backups/
```

For real production, periodically copy backups to another machine/storage provider.

---

## Project layout

```text
SpeedyBot/
├── main.py                    # Unified production entrypoint (TeleBot + FastAPI daemon)
├── xuishop/                 # Core application backend package
│   ├── __init__.py            # Package init & version declaration
│   ├── core.py                # Sales and provisioning business core
│   ├── api.py                 # FastAPI REST API endpoints for Mini App & webhooks
│   ├── context.py             # Global execution context and bot state
│   ├── storage.py             # SQLite data access and schema migrations
│   ├── db.py                  # Database connection helpers
│   ├── ui.py                  # Telegram keyboards and message formatters
│   ├── user_handlers.py       # Telegram user commands and callbacks
│   ├── admin_handlers.py      # Admin panel and command handlers
│   ├── admin_tools.py         # Administrative actions and utilities
│   ├── admin_ux.py            # Admin UX interactive workflows
│   ├── trial.py               # Free trial issuance and policy enforcement
│   ├── gateways.py            # Zibal, Zarinpal and payment gateway handlers
│   ├── linked_services.py     # Existing customer subscription linking
│   ├── customization.py       # Visual styles and button layouts
│   ├── backup_manager.py      # Automated snapshot and backup manager
│   ├── env_manager.py         # Dynamic .env configuration manager
│   ├── updates.py             # Version checking and auto-update logic
│   ├── corepatch.py           # Core monkeypatches and proxy overrides
│   ├── ops.py                 # System health and operational checks
│   └── handlers.py            # Unified event router
├── webapp/                    # Telegram Mini App (Vue 3 + Vite + Tailwind CSS)
│   ├── src/
│   │   ├── api/               # API client calling FastAPI endpoints
│   │   ├── stores/            # Pinia state stores (auth, etc.)
│   │   ├── views/             # StoreView, ServicesView, WalletView, GuidesView, AdminDashboard
│   │   ├── App.vue
│   │   └── main.js
│   ├── dist/                  # Production-compiled assets served by FastAPI
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.js
├── tests/                     # Automated unittest suite
│   ├── test_admin_ux.py
│   ├── test_api.py
│   ├── test_api_admin_and_stars.py
│   ├── test_backup_and_restore.py
│   ├── test_storage.py
│   └── test_xui_and_card.py
├── install.sh                 # One-click Ubuntu deployment installer
├── update.sh                  # One-click application updater
├── upgrade.sh                 # Automated database and environment upgrader
├── restore.sh / restore.py    # Backup restoration scripts
├── requirements.txt           # Python production dependencies
├── VERSION.txt                # Single source of truth for semantic version
├── README.md                  # English documentation
├── README_FA.md               # Persian documentation
├── SECURITY.md                # Security policy
├── LICENSE                    # MIT License
├── .env.example               # Template environment configuration
└── .github/                   # CI/CD workflows and issue templates
```

No release-numbered application folder is used.

---

## Security

- Never commit `.env`.
- Never publish Telegram Bot Tokens or 3x-ui API Tokens.
- Treat Subscription URLs, Direct Configs and QR codes as credentials.
- Treat Panel Snapshot files as sensitive.
- Keep Ubuntu, SSH and 3x-ui updated.
- Use TLS for externally exposed panel/subscription endpoints.
- Existing-service claims require matching `tgId` or explicit admin approval.
- Redact secrets before posting logs in Issues.

See [SECURITY.md](SECURITY.md).

---

## License and author

Licensed under the **MIT License**.

Created and maintained by **AliFanni-79**.

- Telegram: **@AliFanni_79**
- Repository: **https://github.com/AliFanni-79/SpeedyBot**

If you redistribute or build on VizzPN Shop Bot, keeping a link to the original repository helps users find maintained documentation, security updates and future releases.
