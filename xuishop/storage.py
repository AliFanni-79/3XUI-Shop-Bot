import time
from .context import db


def _ensure_column(c, table, col, definition):
    exists = c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    if not exists:
        return
    cols = {r[1] for r in c.execute(f"PRAGMA table_info({table})").fetchall()}
    if col not in cols:
        c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")


def init_db():
    c = db()
    c.execute("PRAGMA journal_mode=WAL")
    now = int(time.time())
    c.execute("CREATE TABLE IF NOT EXISTS user_blocks(user_id INTEGER PRIMARY KEY,reason TEXT,active INTEGER NOT NULL DEFAULT 1,created_at INTEGER NOT NULL,created_by INTEGER NOT NULL,updated_at INTEGER NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS plan_categories(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL UNIQUE,active INTEGER NOT NULL DEFAULT 1,sort_order INTEGER NOT NULL DEFAULT 100,created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL)")
    _ensure_column(c, "plans", "category_id", "INTEGER")
    _ensure_column(c, "plans", "group_name", "TEXT")
    _ensure_column(c, "transactions", "sub_id", "TEXT")
    _ensure_column(c, "transactions", "custom_name", "TEXT")
    _ensure_column(c, "transactions", "promo_cashback_percent", "REAL NOT NULL DEFAULT 0")
    _ensure_column(c, "trial_services", "sub_id", "TEXT")
    _ensure_column(c, "discount_codes", "is_auto", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(c, "discount_codes", "title", "TEXT")
    _ensure_column(c, "discount_codes", "cashback_percent", "REAL NOT NULL DEFAULT 0")
    _ensure_column(c, "discount_codes", "steps_json", "TEXT")
    _ensure_column(c, "discount_codes", "description", "TEXT")
    _ensure_column(c, "gift_codes", "description", "TEXT")
    _ensure_column(c, "discount_redemptions", "cashback_percent", "REAL NOT NULL DEFAULT 0")
    _ensure_column(c, "discount_redemptions", "step_index", "INTEGER NOT NULL DEFAULT 1")
    c.execute("CREATE TABLE IF NOT EXISTS user_saved_discounts(user_id INTEGER NOT NULL, code TEXT NOT NULL, saved_at INTEGER NOT NULL, PRIMARY KEY(user_id, code))")
    c.execute("CREATE TABLE IF NOT EXISTS trial_overrides(user_id INTEGER PRIMARY KEY,volume_gb REAL NOT NULL DEFAULT 1,days INTEGER NOT NULL DEFAULT 1,ip_limit INTEGER NOT NULL DEFAULT 1,note TEXT,updated_at INTEGER NOT NULL,updated_by INTEGER NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS customer_feedback(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,rating INTEGER NOT NULL,comment TEXT,created_at INTEGER NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS audit_events(id INTEGER PRIMARY KEY AUTOINCREMENT,event_type TEXT NOT NULL,actor_id INTEGER,target_id TEXT,detail TEXT,created_at INTEGER NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS broadcast_history(id INTEGER PRIMARY KEY AUTOINCREMENT,admin_id INTEGER NOT NULL,audience TEXT NOT NULL,total INTEGER NOT NULL DEFAULT 0,sent INTEGER NOT NULL DEFAULT 0,failed INTEGER NOT NULL DEFAULT 0,created_at INTEGER NOT NULL)")
    r = c.execute("SELECT id FROM plan_categories ORDER BY id LIMIT 1").fetchone()
    if not r:
        cur = c.execute("INSERT INTO plan_categories(name,active,sort_order,created_at,updated_at) VALUES ('عمومی',1,10,?,?)", (now, now))
        cid = int(cur.lastrowid)
    else:
        cid = int(r[0])
    c.execute("UPDATE plans SET category_id=? WHERE category_id IS NULL", (cid,))
    defaults = {
        "operating_mode": "NORMAL",
        "sales_paused_message": "🛒 فروش و تمدید موقتاً متوقف شده است. حساب کاربری، راهنما و پشتیبانی همچنان در دسترس هستند.",
        "maintenance_message": "🛠 سرویس موقتاً در حال نگهداری است. حساب کاربری، راهنما و پشتیبانی همچنان در دسترس هستند.",
        "brand_name": "Shop",
        "menu_buy_visible": "1",
        "menu_account_visible": "1",
        "menu_trial_visible": "1",
        "menu_affiliate_visible": "1",
        "menu_guide_visible": "1",
        "menu_faq_visible": "1",
        "menu_rewards_visible": "1",
        "menu_support_visible": "1",
        "plan_categories_enabled": "1",
        "trial_overrides_enabled": "1",
        "trial_default_volume_gb": "0.3",
        "trial_default_days": "1",
        "trial_default_ip_limit": "0",
        "audit_enabled": "1",
        "audit_chat_id": "",
        "monitor_alert_after_failures": "3",
        "monitor_alert_cooldown_seconds": "21600",
        "monitor_recovery_notifications": "1",
        "update_notifications_enabled": "1",
        "update_check_interval_seconds": "21600",
        "last_update_notified_version": "",
        "ui_style_buy": "success",
        "ui_style_account": "primary",
        "ui_style_trial": "success",
        "ui_style_guide": "primary",
        "ui_style_support": "primary",
        "ui_style_admin": "primary",
        "builder_enabled": "1",
        "builder_month_price": "120000",
        "builder_dur_discount_3m": "5",
        "builder_dur_discount_6m": "10",
        "builder_dur_discount_12m": "20",
        "builder_gb_price": "1000",
        "builder_traffic_discount_50": "5",
        "builder_traffic_discount_100": "15",
        "builder_traffic_discount_300": "30",
        "builder_traffic_unlimited_price": "500000",
        "builder_traffic_unlimited_cap_gb": "1000",
        "builder_user_cost_1": "0",
        "builder_user_cost_2": "20000",
        "builder_user_cost_3": "35000",
        "builder_user_cost_4": "45000",
        "builder_user_cost_5": "50000",
        "builder_user_cost_unlimited": "65000",
        "builder_user_unlimited_safety_ip": "8",
        "gateway_zibal_enabled": "0",
        "gateway_zibal_merchant": "",
        "gateway_zibal_sandbox": "0",
        "gateway_zarinpal_enabled": "0",
        "gateway_zarinpal_merchant": "",
        "gateway_zarinpal_sandbox": "0",
        "webapp_url": "",
        "webapp_title": "Shop",
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES (?,?)", (k, v))

    # Synchronize brand_name and webapp_title into a single unified reference
    c.execute("UPDATE settings SET value='VizzPN Shop Bot' WHERE key='webapp_title' AND (value='SpeedyBot' OR value='speedybot' OR value='Shop' OR value='SpeedPing' OR value='SpeedPing Bot')")
    c.execute("UPDATE settings SET value='VizzPN Shop Bot' WHERE key='brand_name' AND (value='SpeedyBot' OR value='speedybot' OR value='Shop' OR value='SpeedPing' OR value='SpeedPing Bot')")
    r_brand = c.execute("SELECT value FROM settings WHERE key='brand_name'").fetchone()
    r_title = c.execute("SELECT value FROM settings WHERE key='webapp_title'").fetchone()
    b_val = str(r_brand[0]).strip() if r_brand and r_brand[0] else ""
    t_val = str(r_title[0]).strip() if r_title and r_title[0] else ""
    if b_val and b_val.lower() not in ("speedybot", "speedping") and (not t_val or t_val.lower() in ("", "speedybot", "speedping", "shop")):
        c.execute("UPDATE settings SET value=? WHERE key='webapp_title'", (b_val,))
    elif t_val and t_val.lower() not in ("speedybot", "speedping") and (not b_val or b_val.lower() in ("", "speedybot", "speedping", "shop")):
        c.execute("UPDATE settings SET value=? WHERE key='brand_name'", (t_val,))

    legacy_welcome = "سلام به ربات فروش خودکار **SpeedPing** خوش آمدید! 🚀\nاز منوی زیر اقدام به خرید یا مدیریت حساب خود کنید."
    legacy_welcome2 = "سلام به **Shop** خوش آمدید! 🚀\nاز منوی زیر اقدام به خرید یا مدیریت حساب خود کنید."
    legacy_welcome3 = "سلام به ربات فروش خودکار **SpeedyBot** خوش آمدید! 🚀\nاز منوی زیر اقدام به خرید یا مدیریت حساب خود کنید."
    neutral_welcome = "سلام به **VizzPN Shop Bot** خوش آمدید! 🚀\nاز منوی زیر اقدام به خرید یا مدیریت حساب خود کنید."
    legacy_faq = "📚 **راهنمای SpeedPing**\n\n• برای خرید از بخش پلان‌ها استفاده کنید.\n• لینک Subscription را همیشه نگه دارید و برای به‌روزرسانی کانفیگ‌ها Refresh کنید.\n• برای تمدید یا خرید حجم اضافه وارد حساب کاربری شوید.\n• در صورت مشکل از بخش پشتیبانی پیام بدهید."
    legacy_faq2 = "📚 **راهنمای Shop**\n\n• برای خرید از بخش پلان‌ها استفاده کنید.\n• لینک Subscription را همیشه نگه دارید و برای به‌روزرسانی کانفیگ‌ها Refresh کنید.\n• برای تمدید یا خرید حجم اضافه وارد حساب کاربری شوید.\n• در صورت مشکل از بخش پشتیبانی پیام بدهید."
    legacy_faq3 = "📚 **راهنمای SpeedyBot**\n\n• برای خرید از بخش پلان‌ها استفاده کنید.\n• لینک Subscription را همیشه نگه دارید و برای به‌روزرسانی کانفیگ‌ها Refresh کنید.\n• برای تمدید یا خرید حجم اضافه وارد حساب کاربری شوید.\n• در صورت مشکل از بخش پشتیبانی پیام بدهید."
    neutral_faq = "📚 **راهنمای VizzPN Shop Bot**\n\n• برای خرید از بخش پلان‌ها استفاده کنید.\n• لینک Subscription را همیشه نگه دارید و برای به‌روزرسانی کانفیگ‌ها Refresh کنید.\n• برای تمدید یا خرید حجم اضافه وارد حساب کاربری شوید.\n• در صورت مشکل از بخش پشتیبانی پیام بدهید."
    old_welcomes = (
        legacy_welcome,
        legacy_welcome2,
        legacy_welcome3,
        "سلام به **فروشگاه** خوش آمدید! 🚀\nاز منوی زیر اقدام به خرید یا مدیریت حساب خود کنید.",
    )
    c.execute(
        f"UPDATE settings SET value=? WHERE key='welcome_text' AND value IN ({','.join(['?']*len(old_welcomes))})",
        (neutral_welcome, *old_welcomes),
    )
    old_faqs = (
        legacy_faq,
        legacy_faq2,
        legacy_faq3,
        "📚 **راهنمای فروشگاه**\n\n• برای خرید از بخش پلان‌ها استفاده کنید.\n• لینک Subscription را همیشه نگه دارید و برای به‌روزرسانی کانفیگ‌ها Refresh کنید.\n• برای تمدید یا خرید حجم اضافه وارد حساب کاربری شوید.\n• در صورت مشکل از بخش پشتیبانی پیام بدهید.",
    )
    c.execute(
        f"UPDATE settings SET value=? WHERE key='faq_text' AND value IN ({','.join(['?']*len(old_faqs))})",
        (neutral_faq, *old_faqs),
    )

    c.commit()
    c.close()


def backfill_categories():
    c = db()
    r = c.execute("SELECT id FROM plan_categories WHERE active=1 ORDER BY sort_order,id LIMIT 1").fetchone()
    if r:
        c.execute(
            "UPDATE plans SET category_id=?,updated_at=COALESCE(updated_at,?) WHERE category_id IS NULL",
            (int(r[0]), int(time.time())),
        )
        c.commit()
    c.close()


def audiences(code):
    c = db()
    sql = {
        "all": "SELECT id FROM users WHERE is_active=1",
        "customers": "SELECT DISTINCT user_id FROM transactions WHERE status='APPROVED' AND kind='NEW'",
        "trial": "SELECT DISTINCT t.user_id FROM trial_services t WHERE NOT EXISTS(SELECT 1 FROM transactions x WHERE x.user_id=t.user_id AND x.status='APPROVED' AND x.kind='NEW')",
        "expired_trial": "SELECT DISTINCT t.user_id FROM trial_services t WHERE t.status='EXPIRED' AND NOT EXISTS(SELECT 1 FROM transactions x WHERE x.user_id=t.user_id AND x.status='APPROVED' AND x.kind='NEW')",
        "never_bought": "SELECT u.id FROM users u WHERE u.is_active=1 AND NOT EXISTS(SELECT 1 FROM transactions x WHERE x.user_id=u.id AND x.status='APPROVED' AND x.kind='NEW')",
    }.get(code)
    rows = c.execute(sql).fetchall() if sql else []
    c.close()
    return [int(r[0]) for r in rows]


def feedback_text():
    from html import escape

    c = db()
    total, avg = c.execute("SELECT COUNT(*),COALESCE(AVG(rating),0) FROM customer_feedback").fetchone()
    dist = {int(r[0]): int(r[1]) for r in c.execute("SELECT rating,COUNT(*) FROM customer_feedback GROUP BY rating")}
    recent = c.execute("SELECT user_id,rating,comment FROM customer_feedback ORDER BY id DESC LIMIT 8").fetchall()
    c.close()
    out = [
        "⭐ <b>بازخورد مشتریان</b>",
        "━━━━━━━━━━━━━━━━",
        f"📊 تعداد: <b>{int(total)}</b>",
        f"⭐ میانگین: <b>{float(avg):.2f}/5</b>",
        "",
    ]
    for n in range(5, 0, -1):
        out.append(f"{'⭐' * n}  {dist.get(n, 0)}")
    if recent:
        out += ["", "🕘 <b>آخرین بازخوردها</b>"]
        for r in recent:
            out.append(
                f"• <code>{r['user_id']}</code> — {r['rating']}/5"
                + (f" — {escape((r['comment'] or '')[:70])}" if r['comment'] else "")
            )
    return "\n".join(out)
