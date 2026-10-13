import base64
import os
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import MagicMock

from speedybot import context as C, corepatch, linked_services, storage, updates


class FakeTypes:
    class InlineKeyboardButton:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class KeyboardButton:
        def __init__(self, **kwargs):
            self.kwargs = kwargs


class FakeBot:
    def send_message(self, *args, **kwargs):
        return None


class FakeCore:
    types = FakeTypes
    bot = FakeBot()

    def get_db_setting(self, key, default=""):
        con = sqlite3.connect("app.db")
        try:
            row = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            return row[0] if row else default
        finally:
            con.close()

    def update_db_setting(self, key, value):
        con = sqlite3.connect("app.db")
        con.execute(
            "INSERT INTO settings(key,value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )
        con.commit()
        con.close()

    def is_admin(self, uid):
        return int(uid) == 1


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.old = os.getcwd()
        self.tmp = tempfile.TemporaryDirectory()
        os.chdir(self.tmp.name)
        con = sqlite3.connect("app.db")
        con.execute("CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT)")
        con.execute(
            "CREATE TABLE plans(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,price INTEGER,"
            "volume_gb REAL,days INTEGER,ip_limit INTEGER,active INTEGER,sort_order INTEGER,"
            "created_at INTEGER,updated_at INTEGER)"
        )
        con.execute(
            "INSERT INTO plans(name,price,volume_gb,days,ip_limit,active,sort_order,created_at,updated_at) "
            "VALUES ('Plan A',100,0,30,1,1,10,1,1)"
        )
        con.execute("CREATE TABLE users(id INTEGER PRIMARY KEY,is_active INTEGER,balance INTEGER)")
        con.execute("CREATE TABLE transactions(id INTEGER PRIMARY KEY,user_id INTEGER,plan_id INTEGER,status TEXT,kind TEXT,service_email TEXT)")
        con.execute("CREATE TABLE trial_services(user_id INTEGER,status TEXT,email TEXT,created_at INTEGER,activated_at INTEGER)")
        con.execute(
            "CREATE TABLE linked_services(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,email TEXT NOT NULL UNIQUE,linked_at INTEGER NOT NULL,source TEXT,approved_by INTEGER)"
        )
        con.executemany("INSERT INTO users(id,is_active,balance) VALUES (?,?,0)", [(10, 1), (20, 1), (30, 1)])
        con.execute("INSERT INTO transactions(id,user_id,plan_id,status,kind) VALUES (1,10,1,'APPROVED','NEW')")
        con.execute("INSERT INTO trial_services(user_id,status) VALUES (20,'EXPIRED')")
        con.execute("INSERT INTO linked_services(user_id,email,linked_at,source) VALUES (10,'legacy@example.com',1,'CLAIM')")
        con.commit()
        con.close()
        C.configure(FakeCore())
        storage.init_db()

    def tearDown(self):
        os.chdir(self.old)
        try:
            self.tmp.cleanup()
        except Exception:
            pass

    def test_migration_and_category_backfill(self):
        con = sqlite3.connect("app.db")
        con.row_factory = sqlite3.Row
        category = con.execute("SELECT id,name FROM plan_categories").fetchone()
        plan = con.execute("SELECT category_id FROM plans WHERE id=1").fetchone()
        con.close()
        self.assertEqual(category["name"], "عمومی")
        self.assertEqual(plan["category_id"], category["id"])

    def test_global_trial_defaults_are_seeded(self):
        self.assertEqual(C.setting("trial_default_volume_gb", ""), "0.3")
        self.assertEqual(C.setting("trial_default_days", ""), "1")
        self.assertEqual(C.setting("trial_default_ip_limit", ""), "0")

    def test_brand_and_customer_menu_defaults_are_seeded(self):
        self.assertEqual(C.brand_name(), "فروشگاه")
        for key in C.CUSTOMER_MENU_KEYS:
            self.assertTrue(C.menu_visible(key), key)
        C.set_setting("menu_guide_visible", "0")
        self.assertFalse(C.menu_visible("guide"))

    def test_monitor_and_update_defaults_are_seeded(self):
        self.assertEqual(C.setting("monitor_alert_after_failures", ""), "3")
        self.assertEqual(C.setting("monitor_alert_cooldown_seconds", ""), "21600")
        self.assertEqual(C.setting("update_notifications_enabled", ""), "1")
        self.assertEqual(C.setting("update_check_interval_seconds", ""), "21600")

    def test_legacy_default_copy_is_white_labeled_on_upgrade(self):
        legacy_welcome = "سلام به ربات فروش خودکار **SpeedPing** خوش آمدید! 🚀\nاز منوی زیر اقدام به خرید یا مدیریت حساب خود کنید."
        legacy_faq = "📚 **راهنمای SpeedPing**\n\n• برای خرید از بخش پلان‌ها استفاده کنید.\n• لینک Subscription را همیشه نگه دارید و برای به‌روزرسانی کانفیگ‌ها Refresh کنید.\n• برای تمدید یا خرید حجم اضافه وارد حساب کاربری شوید.\n• در صورت مشکل از بخش پشتیبانی پیام بدهید."
        C.set_setting("welcome_text", legacy_welcome)
        C.set_setting("faq_text", legacy_faq)
        storage.init_db()
        self.assertNotIn("SpeedPing", C.setting("welcome_text", ""))
        self.assertNotIn("SpeedPing", C.setting("faq_text", ""))
        self.assertIn("فروشگاه", C.setting("welcome_text", ""))

    def test_custom_welcome_copy_is_preserved_on_upgrade(self):
        custom = "متن اختصاصی فروشنده بدون قالب پیش‌فرض"
        C.set_setting("welcome_text", custom)
        storage.init_db()
        self.assertEqual(C.setting("welcome_text", ""), custom)

    def test_blacklist_lookup(self):
        con = sqlite3.connect("app.db")
        con.execute(
            "INSERT INTO user_blocks(user_id,reason,active,created_at,created_by,updated_at) "
            "VALUES (20,'abuse',1,1,1,1)"
        )
        con.commit()
        con.close()
        self.assertEqual(C.blocked(20), (True, "abuse"))
        self.assertEqual(C.blocked(30), (False, ""))

    def test_audience_segments(self):
        self.assertEqual(storage.audiences("customers"), [10])
        self.assertEqual(storage.audiences("expired_trial"), [20])
        self.assertEqual(set(storage.audiences("never_bought")), {20, 30})

    def test_style_payload(self):
        C.set_setting("ui_style_buy", "success")
        button = C.inline("Buy", callback_data="x", emoji_key="buy")
        self.assertEqual(button.kwargs["style"], "success")

    def test_linked_service_ownership_lookup(self):
        row = linked_services._owned_linked_service(10, 1)
        self.assertEqual(row["email"], "legacy@example.com")
        self.assertIsNone(linked_services._owned_linked_service(20, 1))

    def test_update_version_comparison(self):
        self.assertTrue(updates.is_newer("4.1.1", "4.1.0"))
        self.assertTrue(updates.is_newer("5.0.0", "4.9.9"))
        self.assertFalse(updates.is_newer("4.1.0", "4.1.0"))
        self.assertFalse(updates.is_newer("not-a-version", "4.1.0"))

    def test_monitor_dns_error_is_summarized(self):
        text = corepatch._monitor_error_summary(
            Exception("NameResolutionError: Temporary failure in name resolution")
        )
        self.assertIn("DNS", text)
        self.assertIn("Resolve", text)

    def test_subscription_direct_links_plain_and_base64(self):
        raw = "vless://one\nvmess://two\nhttps://subscription.example/sub/x"
        self.assertEqual(corepatch._decode_subscription_text(raw), ["vless://one", "vmess://two"])
        encoded = base64.b64encode(raw.encode()).decode()
        self.assertEqual(corepatch._decode_subscription_text(encoded), ["vless://one", "vmess://two"])

    def test_default_all_inbound_click_removes_clicked(self):
        stored, selected, changed = corepatch._toggle_effective([1, 2, 3], [], 2)
        self.assertTrue(changed)
        self.assertFalse(selected)
        self.assertEqual(stored, [1, 3])

    def test_explicit_selection_can_return_to_default_all(self):
        stored, selected, changed = corepatch._toggle_effective([1, 2, 3], [1, 3], 2)
        self.assertTrue(changed)
        self.assertTrue(selected)
        self.assertEqual(stored, [])

    def test_at_least_one_inbound_is_kept(self):
        stored, selected, changed = corepatch._toggle_effective([1, 2], [2], 2)
        self.assertFalse(changed)
        self.assertTrue(selected)
        self.assertEqual(stored, [2])

    def test_resolve_unique_service_email_sanitization_and_increment(self):
        from speedybot.db import resolve_unique_service_email
        con = sqlite3.connect("app.db")
        con.execute("CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY, service_email TEXT)")
        con.execute("CREATE TABLE IF NOT EXISTS trial_services (service_email TEXT)")
        con.execute("CREATE TABLE IF NOT EXISTS linked_services (email TEXT)")

        # Case 1: Desired name is free
        name1 = resolve_unique_service_email("my-vpn", user_id=123, tx_id=1, conn=con)
        self.assertEqual(name1, "my-vpn")

        # Reserve it
        con.execute("INSERT INTO transactions (id, service_email) VALUES (101, 'my-vpn')")

        # Case 2: Desired name collision increments to _2
        name2 = resolve_unique_service_email("my-vpn", user_id=123, tx_id=2, conn=con)
        self.assertEqual(name2, "my-vpn_2")

        # Reserve _2
        con.execute("INSERT INTO transactions (id, service_email) VALUES (102, 'my-vpn_2')")

        # Case 3: Next collision increments to _3
        name3 = resolve_unique_service_email("my-vpn", user_id=123, tx_id=3, conn=con)
        self.assertEqual(name3, "my-vpn_3")

        # Case 4: No desired name provided falls back to brand_user_tx
        name4 = resolve_unique_service_email(None, user_id=123, tx_id=4, conn=con)
        self.assertTrue(name4.endswith("_123_4"))

        # Case 5: Special characters sanitized
        name5 = resolve_unique_service_email("special @#$ name!", user_id=123, tx_id=5, conn=con)
        self.assertEqual(name5, "special_____name")

        con.close()

    def test_brand_name_and_slug_resolution(self):
        from speedybot.db import get_brand_name, get_brand_slug
        con = sqlite3.connect("app.db")
        # Reset brand settings
        con.execute("DELETE FROM settings WHERE key IN ('webapp_title', 'brand_name')")
        con.commit()
        self.assertEqual(get_brand_name(conn=con), "SpeedyBot")

        # Brand name set
        con.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('brand_name', 'VizzPN')")
        con.commit()
        self.assertEqual(get_brand_name(conn=con), "VizzPN")
        self.assertEqual(get_brand_slug(conn=con), "vizzpn")

        # Webapp title set
        con.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('webapp_title', 'SuperVPN')")
        con.commit()
        self.assertEqual(get_brand_name(conn=con), "SuperVPN")
        self.assertEqual(get_brand_slug(conn=con), "supervpn")

        con.close()

    def test_legacy_speedping_db_migration(self):
        from speedybot.db import get_db_path
        with tempfile.TemporaryDirectory() as td:
            old_cwd = os.getcwd()
            try:
                os.chdir(td)
                # Create a legacy speedping.db with -wal and -shm
                legacy_file = os.path.join(td, "speedping.db")
                with open(legacy_file, "w") as f:
                    f.write("legacy_db_content")
                with open(f"{legacy_file}-wal", "w") as f:
                    f.write("wal_content")
                with open(f"{legacy_file}-shm", "w") as f:
                    f.write("shm_content")

                # Resolving path should automatically migrate to app.db
                resolved = get_db_path()
                self.assertTrue(resolved.endswith("app.db"))
                self.assertTrue(os.path.exists("app.db"))
                self.assertTrue(os.path.exists("app.db-wal"))
                self.assertTrue(os.path.exists("app.db-shm"))
                self.assertFalse(os.path.exists("speedping.db"))
                self.assertFalse(os.path.exists("speedping.db-wal"))
                self.assertFalse(os.path.exists("speedping.db-shm"))

                # Verify content preserved
                with open("app.db", "r") as f:
                    self.assertEqual(f.read(), "legacy_db_content")
            finally:
                os.chdir(old_cwd)

    def test_corepatch_checkout_accepts_custom_name(self):
        from speedybot import corepatch, context as C
        # Mock ORIGINALS checkout
        received = {}
        def fake_orig_checkout(uid, plan, payment_method, kind="NEW", target_service_email=None, extra_volume_gb=0, custom_name=None, **kwargs):
            received["uid"] = uid
            received["custom_name"] = custom_name
            return {"tx_id": 999}, None

        fake_core = type(
            "Core",
            (),
            {
                "_create_checkout_transaction": staticmethod(fake_orig_checkout),
                "purchase_gate": lambda u: True,
                "trial_enabled": lambda: True,
                "generate_trial_xui_config": lambda *a: None,
                "notify_admins": lambda *a, **k: None,
                "_get_delivery_links": lambda *a: [],
                "_configured_inbound_ids": lambda *a: [],
                "_set_inbound_toggle": lambda *a: None,
                "_sync_client_inbounds": lambda *a: None,
                "_service_monitor_loop": lambda *a: None,
                "get_db_setting": lambda self, k, d="": d,
            },
        )()
        C.CORE = fake_core
        corepatch.apply()

        # Calling core._create_checkout_transaction with custom_name must not raise TypeError
        res, err = fake_core._create_checkout_transaction(
            123, {"plan_id": 1}, "WALLET", custom_name="laptop"
        )
        self.assertIsNone(err)
        self.assertEqual(received["custom_name"], "laptop")
        self.assertEqual(received["uid"], 123)

    def test_trial_monthly_eligibility_and_defaults(self):
        from speedybot import trial
        con = sqlite3.connect("app.db")
        con.execute("CREATE TABLE IF NOT EXISTS trial_services (user_id INTEGER PRIMARY KEY, status TEXT, created_at INTEGER, activated_at INTEGER)")
        con.execute("DELETE FROM trial_services")
        con.commit()

        # 1. New user is eligible
        eligible, rem, _, status = trial.get_trial_eligibility(1001, conn=con)
        self.assertTrue(eligible)
        self.assertEqual(rem, 0)

        # 2. User activated trial 10 days ago (within 30 days cooldown) -> Not eligible
        now = int(time.time())
        ten_days_ago = now - (10 * 86400)
        con.execute("INSERT INTO trial_services (user_id, status, created_at, activated_at) VALUES (1002, 'ACTIVE', ?, ?)", (ten_days_ago, ten_days_ago))
        con.commit()

        eligible, rem, _, status = trial.get_trial_eligibility(1002, conn=con)
        self.assertFalse(eligible)
        self.assertEqual(rem, 20)  # 20 days remaining

        # 3. User activated trial 31 days ago -> Eligible again for monthly test!
        thirty_one_days_ago = now - (31 * 86400)
        con.execute("INSERT INTO trial_services (user_id, status, created_at, activated_at) VALUES (1003, 'EXPIRED', ?, ?)", (thirty_one_days_ago, thirty_one_days_ago))
        con.commit()

        eligible, rem, _, status = trial.get_trial_eligibility(1003, conn=con)
        self.assertTrue(eligible)
        self.assertEqual(rem, 0)

        # 4. Check defaults: 300MB (0.3 GB), 1 day, unlimited users (0)
        gb, days, ip = trial.default_values()
        self.assertEqual(gb, 0.3)
        self.assertEqual(days, 1)
        self.assertEqual(ip, 0)

        con.close()

    def test_trial_override_precedence(self):
        from speedybot import trial, context as C
        con = sqlite3.connect("app.db")
        con.execute("CREATE TABLE IF NOT EXISTS trial_overrides (user_id INTEGER PRIMARY KEY, volume_gb REAL, days INTEGER, ip_limit INTEGER, note TEXT, updated_at INTEGER, updated_by INTEGER)")
        con.execute("DELETE FROM trial_overrides")
        con.commit()

        # Without override -> defaults
        gb, days, ip, is_ov = trial.values(9901)
        self.assertFalse(is_ov)
        self.assertEqual(gb, 0.3)
        self.assertEqual(days, 1)
        self.assertEqual(ip, 0)

        # With override
        con.execute(
            "INSERT INTO trial_overrides (user_id, volume_gb, days, ip_limit, updated_at, updated_by) VALUES (9901, 5.0, 7, 3, 1000, 1)"
        )
        con.commit()
        con.close()

        gb, days, ip, is_ov = trial.values(9901)
        self.assertTrue(is_ov)
        self.assertEqual(gb, 5.0)
        self.assertEqual(days, 7)
        self.assertEqual(ip, 3)

    def test_trial_issue_flow_records_email_and_custom_name(self):
        from speedybot import trial, context as C
        con = sqlite3.connect("app.db")
        con.execute("CREATE TABLE IF NOT EXISTS trial_services (user_id INTEGER PRIMARY KEY, email TEXT, status TEXT, last_error TEXT, sub_id TEXT, created_at INTEGER, activated_at INTEGER)")
        con.execute("DELETE FROM trial_services")
        con.commit()

        # Mock XUI calls in fake core
        class FakeCore:
            DEVELOPMENT_MODE = False
            requests = MagicMock()
            @staticmethod
            def trial_enabled(): return True
            @staticmethod
            def purchase_gate(uid): return True
            @staticmethod
            def get_db_setting(key, default=""): return default
            @staticmethod
            def _xui_headers(): return {}
            @staticmethod
            def _xui_proxies(): return {}
            @staticmethod
            def _xui_url(p): return f"http://xui.test/{p}"
            @staticmethod
            def _selected_inbound_ids_for(*a): return [1]
            @staticmethod
            def _get_client_data(*a): return None
            @staticmethod
            def _safe_json(*a): return {"success": True}
            @staticmethod
            def _sync_client_inbounds(*a): pass
            @staticmethod
            def _get_client_subscription_id(*a): return "sub_trial_uuid_123"
            @staticmethod
            def _get_delivery_links(*a): return ["vless://testlink"]
            @staticmethod
            def _subscription_url(sub): return f"http://sub.test/{sub}"
            @staticmethod
            def _subscription_markup(*a, **k): return None
            @staticmethod
            def _xui_assign_group(*a): pass
            @staticmethod
            def _mark_trial(uid, status, err=None):
                c = sqlite3.connect("app.db")
                c.execute("UPDATE trial_services SET status=?, activated_at=? WHERE user_id=?", (status, int(time.time()), uid))
                c.commit()
                c.close()
            @staticmethod
            def notify_admins(*a, **k): pass
            @staticmethod
            def main_menu(): return None

        fake_resp = MagicMock()
        fake_resp.status_code = 200
        FakeCore.requests.post.return_value = fake_resp

        C.CORE = FakeCore()

        res = trial.issue_trial_for_user(7788, custom_name="my_trial_box")
        self.assertTrue(res["success"])
        self.assertEqual(res["sub_id"], "sub_trial_uuid_123")
        self.assertIn("my_trial_box", res["email"])

        row = con.execute("SELECT status, email, sub_id FROM trial_services WHERE user_id=7788").fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "ACTIVE")
        self.assertIn("my_trial_box", row[1])
        self.assertEqual(row[2], "sub_trial_uuid_123")
        con.close()


if __name__ == "__main__":
    unittest.main()


