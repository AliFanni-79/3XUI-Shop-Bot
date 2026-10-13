# Changelog

## 5.0.0 — Telegram Mini App, Custom Plan Builder & Online Payment Gateways

### Added
- **Telegram Mini App (TMA)**:
  - Responsive SPA web application built with **Vue 3, Tailwind CSS, and Pinia** located in `webapp/`.
  - Cryptographic authentication with HMAC-SHA256 signature verification of Telegram `initData`.
  - High-performance **FastAPI** ASGI backend running concurrently in a daemon thread inside `main.py` on `WEBAPP_PORT` (default 8080).
  - Embedded customer views: Active Services (traffic usage, expiry, copyable links, QR code viewer), Platform Connection Guides (iOS, Android, Windows, macOS), Wallet management with deposit & transaction logs, and Referral partner link.
  - Web-based Admin Dashboard: live server stats, plan builder pricing configurations, and payment gateway controls.
- **Interactive Custom Plan Builder**:
  - Dynamic plan building directly within the Mini App storefront.
  - Duration picker: 1, 3, 6, or 12 months with duration discounts (3 months: 5%, 6 months: 10%, 12 months: 20%).
  - Traffic slider: customizable GB range (default 1,000 Tomans/GB with volume discounts for >50GB, >100GB, >300GB) or Unlimited traffic option (fair-use capped at 1,000 GB).
  - Device limits: 1 to 5 devices (with price tiers) or Unlimited devices.
  - Strict **Fair-Use Protection**: automatic validation preventing simultaneous unlimited traffic + unlimited users.
  - Real-time price breakdown displaying original strikethrough price and discounted final price.
  - Automated 3x-ui provisioning for custom plan purchases (`plan_id = 0`).
- **Online Payment Gateways (Zibal & Zarinpal)**:
  - Built-in integration for Iranian payment gateways **Zibal** and **Zarinpal** in `speedybot/gateways.py`.
  - Webhook callback handlers (`/api/payment/callback/zibal` and `/api/payment/callback/zarinpal`).
  - Automated client provisioning upon verified payment without manual admin receipt review.
  - Sandbox/testing mode toggles for development and testing.
  - Disabled by default out of the box; easily enabled with Merchant ID in Admin Dashboard.
- **Simplified Telegram Chat UI**:
  - Integrated Telegram Menu Button (`MenuButtonWebApp`) opening the Mini App directly.
  - Streamlined chat keyboard reduced to 3 primary actions: `📡 سرویس‌های فعال من` (My Active Services), `📚 راهنما و سوالات` (Guides & FAQ), and `📞 پشتیبانی` (Support).
- **Deployment & Script Updates**:
  - `install.sh`: Interactive prompts for `WEBAPP_PORT` (default: 8080) and `WEBAPP_URL`.
  - `update.sh`: Automatic `.env` migration appending webapp variables if missing; `node_modules` exclusions.
  - `.env.example`: Updated with Mini App environment variables.

### Removed
- Pruned deprecated legacy features to maximize performance and maintainability:
  - Doprax cloud deployment workflow.
  - Customer feedback star surveys and ratings dashboard.
  - Mandatory phone number verification and channel membership gating.
  - Telegram custom emoji styling and `/emojiid` helper.

### Fixed & Improved
- Fixed TeleBot initialization when `BOT_TOKEN` is unset or invalid in development/testing.
- Handled SQLite schema migrations automatically in `storage.init_db()`.
- Synchronized version reporting to 5.0.0 across `VERSION.txt`, `speedybot/__init__.py`, and CI workflows.


### Fixed
- Admin inline navigation now clears any stale `register_next_step_handler` state before starting another management action. This prevents an unfinished previous wizard (for example Plan Edit) from consuming the next admin input or making repeated button use feel stuck.
- Legacy admin menu callbacks that previously left Telegram's loading spinner active are now acknowledged immediately.
- Repeated use of the same admin action is now safe: clicking the button again cancels the old pending step and starts a fresh wizard.
- Internal runtime package version is synchronized with `VERSION.txt`; CI now verifies both values.

### Improved
- Admin input wizards now use readable Persian instructions instead of compact field-only strings.
- Plan Add/Edit/Toggle screens explain every field and show the current Plan IDs/values where useful.
- Discount, Gift Code, Trial, Category, Affiliate, Bank, Channel, Guide, Blacklist, Broadcast and deletion workflows now include concrete examples and safety notes.
- Every intercepted admin wizard includes an explicit **Cancel operation and return to admin panel** button.
- Starting another inline admin action automatically cancels the previous unfinished input step.

## 4.0.1 — Routing & Installer Reliability Patch

### Fixed
- Direct configs now prefer the real public 3x-ui subscription body, so manually delivered links match what a customer's subscription client receives. Plain and Base64 subscription bodies are supported; panel API-generated links remain a fallback.
- Trial/Plan Inbound selection now represents the effective state correctly: legacy empty selection means **all active Inbounds**, and the UI shows those Inbounds as selected instead of unchecked.
- Clicking a selected Inbound while in default-all mode now creates an explicit selection containing all other active Inbounds, so the clicked Inbound is actually excluded.
- Client Inbound synchronization now verifies the persisted `inboundIds` from 3x-ui after attach/detach and refuses to report success if the panel state differs from the configured selection.
- The installer now clearly explains that Bot/API token input is hidden, confirms receipt without displaying the secret, and retries invalid Telegram Bot Token input instead of exiting immediately.

### Added
- Global Free Trial settings for traffic, duration and IP limit. Per-user Trial overrides still take priority.
- A refreshed Trial/Inbound admin screen with live checkmarks and immediate state refresh after every toggle.
- Safe Plan deletion for unused plans. Plans referenced by transaction history cannot be hard-deleted and should be deactivated instead.
- Safe Category deletion; plans inside a deleted category are moved to another category before deletion.
- Unit tests for plain/Base64 subscription parsing and default-all/explicit Inbound toggle semantics.

## 4.0.0 — Control Center & Growth Suite

### Added
- Redesigned customer account, categorized storefront and reorganized Telegram admin Control Center.
- Official Telegram button style support (`primary`, `success`, `danger`, default) for key user/admin actions.
- Optional Custom/Premium Emoji IDs for important buttons, `/emojiid` helper and live eligibility testing.
- Operating modes: `NORMAL`, `SALES_PAUSED`, `MAINTENANCE`.
- User purchase/trial restriction (blacklist) with reason and audit events.
- Plan categories with automatic migration of existing plans to a default category.
- Per-user Trial overrides for traffic, days and IP limit while preserving Trial inbound routing.
- Customer feedback: 1–5 stars, optional comment, distribution and average-rating dashboard.
- Targeted broadcasts for active users, customers, Trial leads, expired-Trial leads and users who never purchased.
- SQLite Audit Log with optional Telegram audit channel.
- Read-only emergency 3x-ui client snapshot export.
- Unit tests for migrations, categories, blacklist, audience segmentation, feedback and button payloads.

### Architecture
- v4 is now the **integrated SpeedyBot application**, not a versioned overlay.
- Root `main.py` is the single official production entrypoint.
- Business logic and Control Center modules live in the permanent `speedybot/` package.
- The former `app.py` entrypoint and `speedybot_v4/` directory were removed.
- The previous monolithic business core was moved without functional rewriting to `speedybot/core.py` and is loaded by the integrated entrypoint.
- Tests were renamed from `test_v4_storage.py` to the version-independent `test_storage.py`.

### Installer / updater
- `install.sh` installs the complete repository layout and always runs `main.py`.
- `update.sh` re-executes from a temporary copy before self-update.
- Updates now synchronize the **entire GitHub repository** with `rsync --delete`, rather than maintaining a fragile manual file list.
- Mutable runtime state is excluded from synchronization: `.env`, `.venv/`, SQLite DB/WAL/SHM, `backups/`, `run.sh` and `.deployed_commit`.
- A complete application + runtime rollback backup is created before synchronization.
- Obsolete files/directories are automatically removed during upgrade because the deployed application mirrors the current repository.
- The updater performs Python/shell validation, dependency installation, systemd restart, health checks and automatic rollback on failure.
- GitHub Actions validates the integrated `main.py`, all `speedybot/*.py`, unit tests, shell scripts and repository layout.

### UX
- Admin/user messages and navigation were reorganized for faster scanning and less dense menus.
- Shop and account screens now use the categorized v4 experience.
- Official Telegram button styling and optional Custom Emoji remain backward-safe with normal-text/emoji fallback.

### Security / safety
- Panel Snapshot is intentionally read-only; no destructive one-click restore was added.
- Existing runtime secrets remain in `.env`; v4 introduces no new required secret.
- Blacklisted users retain support/account visibility rather than being silently locked out of help.
- Complete-project updates never overwrite runtime secrets or the production SQLite database from GitHub.

## 3.1.0 — Trial delivery, inbound routing & lightweight CRM

### Fixed
- Corrected free-Trial direct-link delivery using 3x-ui client-link APIs instead of mislabeling subscription URLs.
- Filtered direct links to actual proxy URI schemes.
- Re-synchronized configured Trial/Plan inbounds during idempotent retries.

### Added
- Per-plan and Trial inbound routing.
- Trial on/off switch.
- Admin-managed platform connection guides with text/photo/video.
- Acquisition-source survey and Trial-expiry sales follow-up.
- Custom service names with local/panel duplicate checks.
- Secure existing-service claims via matching `tgId` or admin approval.

## 3.0.0 — Sales & management suite

- Added Sanaei Client Groups (`Customers` / `Trial`).
- Replaced hard-coded plans with SQLite-backed plan management.
- Added 1/2/3-user default monthly unlimited plans and dynamic IP limits.
- Added renewals, optional extra-volume packs and subscription QR codes.
- Added discount codes, gift-wallet codes, cashback, phone verification, membership gating and multiple admins.
- Added automatic backups, expanded analytics and safer GitHub-based updates.

## 2.2.0 — Service notifications

- Added background quota/expiry monitoring, warnings and one-time exhaustion/expiry notices.
- Added persistent notification de-duplication and `/notifydiag`.

## 2.1.0 — Sanaei API compatibility & diagnostics

- Aligned calls with current `/panel/api/*` Bearer-token API.
- Added base-path-safe URL joining, `/xuidiag`, detailed HTTP diagnostics and installer API preflight.
- Corrected Subscription ID handling and configurable subscription path.

## 2.0.0 — Affiliate & Wallet

- Added referral/affiliate links, exactly-once commissions, wallet ledger and wallet checkout.
- Added idempotent provisioning, retry/recovery flows and soft user deactivation.
