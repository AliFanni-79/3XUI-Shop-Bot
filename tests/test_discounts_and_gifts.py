import hashlib
import hmac
import json
import time
import unittest
from unittest.mock import patch
from urllib.parse import urlencode
import os

os.environ.setdefault("BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

from fastapi.testclient import TestClient
from xuishop.api import app, _db
from xuishop import core, storage


class TestDiscountsAndGifts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        core.init_db()
        storage.init_db()
        cls.client = TestClient(app)
        cls.bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"

    def _generate_init_data(self, user_dict):
        secret_key = hmac.new(b"WebAppData", self.bot_token.encode(), hashlib.sha256).digest()
        user_json = json.dumps(user_dict)
        data = {
            "auth_date": str(int(time.time())),
            "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
            "user": user_json,
        }
        check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
        data_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
        data["hash"] = data_hash
        return urlencode(data)

    def test_apply_gift_code(self):
        uid = 998811
        init_data = self._generate_init_data({"id": uid, "first_name": "GiftUser"})

        conn = _db()
        now_ts = int(time.time())
        conn.execute("DELETE FROM users WHERE id = ?", (uid,))
        conn.execute("DELETE FROM gift_redemptions WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM wallet_transactions WHERE user_id = ?", (uid,))
        conn.execute("INSERT OR REPLACE INTO users (id, balance, created_at) VALUES (?, 0, ?)", (uid, now_ts))
        conn.execute(
            "INSERT OR REPLACE INTO gift_codes (code, amount, max_uses, expires_at, active, created_at) VALUES ('GIFT_TEST_50', 50000, 10, NULL, 1, ?)",
            (now_ts,)
        )
        conn.commit()
        conn.close()

        with patch("xuishop.api._get_bot_token", return_value=self.bot_token), \
             patch("xuishop.api._is_admin", return_value=True):
            # 1. Apply gift code
            res = self.client.post(
                "/api/codes/apply",
                headers={"X-Telegram-Init-Data": init_data},
                json={"code": "GIFT_TEST_50"}
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["type"], "gift")
            self.assertEqual(data["amount"], 50000)
            self.assertEqual(data["new_balance"], 50000)

            # Check DB balance and wallet_transactions
            conn = _db()
            u = conn.execute("SELECT balance FROM users WHERE id = ?", (uid,)).fetchone()
            self.assertEqual(int(u["balance"]), 50000)
            wt = conn.execute("SELECT * FROM wallet_transactions WHERE user_id = ? AND type = 'GIFT_CODE'", (uid,)).fetchone()
            self.assertIsNotNone(wt)
            self.assertEqual(int(wt["amount"]), 50000)
            conn.close()

            # 2. Re-applying the same gift code should fail
            res_repeat = self.client.post(
                "/api/codes/apply",
                headers={"X-Telegram-Init-Data": init_data},
                json={"code": "GIFT_TEST_50"}
            )
            self.assertEqual(res_repeat.status_code, 400)
            self.assertIn("قبلاً", res_repeat.json()["detail"])

    def test_apply_discount_code_wallet_vs_buy(self):
        uid = 998822
        init_data = self._generate_init_data({"id": uid, "first_name": "DiscUser"})

        conn = _db()
        now_ts = int(time.time())
        conn.execute("DELETE FROM users WHERE id = ?", (uid,))
        conn.execute("DELETE FROM transactions WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM discount_redemptions WHERE code = 'SINGLE_USE_CODE'")
        conn.execute("INSERT OR REPLACE INTO users (id, balance, created_at) VALUES (?, 0, ?)", (uid, now_ts))
        conn.execute(
            """INSERT OR REPLACE INTO discount_codes
               (code, discount_type, value, min_purchase, max_uses, per_user_limit, expires_at, active, created_at)
               VALUES ('OFF_PERCENT_20', 'PERCENT', 20, 50000, 10, 1, NULL, 1, ?)""",
            (now_ts,)
        )
        conn.commit()
        conn.close()

        with patch("xuishop.api._get_bot_token", return_value=self.bot_token), \
             patch("xuishop.api._is_admin", return_value=True):
            # 1. Calling in Wallet view (price=None): tells user it's a discount code and to use on purchases
            res_wallet = self.client.post(
                "/api/codes/apply",
                headers={"X-Telegram-Init-Data": init_data},
                json={"code": "OFF_PERCENT_20"}
            )
            self.assertEqual(res_wallet.status_code, 200)
            d_wallet = res_wallet.json()
            self.assertEqual(d_wallet["type"], "discount")
            self.assertTrue(d_wallet.get("is_discount_only"))
            self.assertIn("منوی خرید", d_wallet["message"])

            # 2. Calling in Buy menu below min_purchase: returns 400
            res_below_min = self.client.post(
                "/api/codes/apply",
                headers={"X-Telegram-Init-Data": init_data},
                json={"code": "OFF_PERCENT_20", "price": 30000}
            )
            self.assertEqual(res_below_min.status_code, 400)
            self.assertIn("حداقل مبلغ خرید", res_below_min.json()["detail"])

            # 3. Calling in Buy menu with valid price: calculates discount
            res_buy = self.client.post(
                "/api/codes/apply",
                headers={"X-Telegram-Init-Data": init_data},
                json={"code": "OFF_PERCENT_20", "price": 100000}
            )
            self.assertEqual(res_buy.status_code, 200)
            d_buy = res_buy.json()
            self.assertEqual(d_buy["type"], "discount")
            self.assertEqual(d_buy["discount_amount"], 20000)
            self.assertEqual(d_buy["final_price"], 80000)

    def test_discount_release_on_order_rejection(self):
        uid = 998833
        admin_id = 998800
        admin_init = self._generate_init_data({"id": admin_id, "first_name": "Admin"})
        user_init = self._generate_init_data({"id": uid, "first_name": "Buyer"})

        conn = _db()
        now_ts = int(time.time())
        conn.execute("DELETE FROM users WHERE id = ?", (uid,))
        conn.execute("DELETE FROM transactions WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM discount_redemptions WHERE code = 'SINGLE_USE_CODE'")
        conn.execute("INSERT OR REPLACE INTO users (id, balance, created_at) VALUES (?, 0, ?)", (uid, now_ts))
        conn.execute("INSERT OR REPLACE INTO users (id, balance, created_at) VALUES (?, 0, ?)", (admin_id, now_ts))
        conn.execute("INSERT OR REPLACE INTO admins (user_id, created_at) VALUES (?, ?)", (admin_id, now_ts))
        conn.execute(
            """INSERT OR REPLACE INTO plans (id, name, price, days, volume_gb, ip_limit, active, sort_order, created_at, updated_at)
               VALUES (950, 'Plan 950', 100000, 30, 50, 1, 1, 0, ?, ?)""",
            (now_ts, now_ts)
        )
        conn.execute(
            """INSERT OR REPLACE INTO discount_codes
               (code, discount_type, value, min_purchase, max_uses, per_user_limit, expires_at, active, created_at)
               VALUES ('SINGLE_USE_CODE', 'FIXED', 25000, 0, 1, 1, NULL, 1, ?)""",
            (now_ts,)
        )
        conn.commit()
        conn.close()

        with patch("xuishop.api._get_bot_token", return_value=self.bot_token), \
             patch("xuishop.api._is_admin", return_value=True), \
             patch("xuishop.core.bot.send_message"):
            # 1. User initiates card order with discount code
            res_ord = self.client.post(
                "/api/orders/init-card",
                headers={"X-Telegram-Init-Data": user_init},
                json={"plan_id": 950, "discount_code": "SINGLE_USE_CODE"}
            )
            self.assertEqual(res_ord.status_code, 200)

            # Check that discount redemption is RESERVED and price is reduced
            conn = _db()
            tx = conn.execute("SELECT * FROM transactions WHERE user_id = ? ORDER BY id DESC LIMIT 1", (uid,)).fetchone()
            self.assertEqual(int(tx["price"]), 75000)
            self.assertEqual(int(tx["discount_amount"]), 25000)
            self.assertEqual(tx["discount_code"], "SINGLE_USE_CODE")
            order_id = tx["id"]

            redemption = conn.execute("SELECT * FROM discount_redemptions WHERE tx_id = ?", (order_id,)).fetchone()
            self.assertIsNotNone(redemption)
            self.assertEqual(redemption["status"], "RESERVED")
            conn.close()

            # 2. Admin rejects the order
            res_rej = self.client.post(
                f"/api/admin/orders/{order_id}/reject",
                headers={"X-Telegram-Init-Data": admin_init},
                json={"reason": "Fake receipt"}
            )
            self.assertEqual(res_rej.status_code, 200)

            # Check that discount redemption was RELEASED
            conn = _db()
            redemption_after = conn.execute("SELECT * FROM discount_redemptions WHERE tx_id = ?", (order_id,)).fetchone()
            self.assertEqual(redemption_after["status"], "RELEASED")

            # 3. Code can be checked/applied again because it was released!
            res_check_again = self.client.post(
                "/api/codes/apply",
                headers={"X-Telegram-Init-Data": user_init},
                json={"code": "SINGLE_USE_CODE", "price": 100000}
            )
            self.assertEqual(res_check_again.status_code, 200)
            self.assertEqual(res_check_again.json()["discount_amount"], 25000)
            conn.close()

    def test_admin_user_detail_includes_discounts_and_wallet_transactions(self):
        uid = 998844
        admin_id = 998800
        admin_init = self._generate_init_data({"id": admin_id, "first_name": "Admin"})

        conn = _db()
        now_ts = int(time.time())
        conn.execute("INSERT OR REPLACE INTO users (id, balance, created_at) VALUES (?, 10000, ?)", (uid, now_ts))
        conn.execute(
            """INSERT INTO transactions
               (user_id, plan_id, status, price, payment_method, wallet_used, cash_amount, created_at,
                plan_name_snapshot, plan_days_snapshot, plan_volume_gb_snapshot, plan_ip_limit_snapshot,
                discount_code, discount_amount, kind)
               VALUES (?, 950, 'APPROVED', 80000, 'CARD', 0, 80000, ?, 'Gold Plan', 30, 50, 1, 'OFF20K', 20000, 'NEW')""",
            (uid, now_ts)
        )
        conn.execute(
            """INSERT INTO wallet_transactions
               (user_id, amount, balance_after, type, description, created_at)
               VALUES (?, 50000, 60000, 'GIFT_CODE', 'کد هدیه GIFT50', ?)""",
            (uid, now_ts)
        )
        conn.commit()
        conn.close()

        with patch("xuishop.api._get_bot_token", return_value=self.bot_token), \
             patch("xuishop.api._is_admin", return_value=True):
            res = self.client.get(
                f"/api/admin/users/{uid}",
                headers={"X-Telegram-Init-Data": admin_init}
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            # Transactions must have discount info
            self.assertIn("transactions", data)
            self.assertTrue(len(data["transactions"]) >= 1)
            t = next(tx for tx in data["transactions"] if tx["plan"] == "Gold Plan")
            self.assertEqual(t["discount_code"], "OFF20K")
            self.assertEqual(t["discount_amount"], 20000)

            # Wallet transactions must include gift code
            self.assertIn("wallet_transactions", data)
            self.assertTrue(len(data["wallet_transactions"]) >= 1)
            wt = next(w for w in data["wallet_transactions"] if w["type"] == "GIFT_CODE")
            self.assertEqual(wt["amount"], 50000)
            self.assertIn("GIFT50", wt["description"])

    def test_bot_process_user_code_discount_not_saved_as_pending(self):
        uid = 998855
        conn = _db()
        now_ts = int(time.time())
        conn.execute("INSERT OR REPLACE INTO users (id, balance, pending_discount_code, created_at) VALUES (?, 0, NULL, ?)", (uid, now_ts))
        conn.execute(
            """INSERT OR REPLACE INTO discount_codes
               (code, discount_type, value, min_purchase, max_uses, per_user_limit, expires_at, active, created_at)
               VALUES ('BOT_DISC_CODE', 'PERCENT', 15, 0, 10, 1, NULL, 1, ?)""",
            (now_ts,)
        )
        conn.commit()
        conn.close()

        class FakeMessage:
            def __init__(self, uid, text):
                self.chat = type("Chat", (), {"id": uid})()
                self.from_user = type("User", (), {"id": uid})()
                self.text = text

        sent_messages = []
        with patch.object(core.bot, "send_message", side_effect=lambda cid, text, **kw: sent_messages.append(text)):
            core.USER_STATES[uid] = 'CODE_ENTRY'
            core.process_user_code(FakeMessage(uid, "BOT_DISC_CODE"))

        # Check response message warns that discount codes can only be used on purchase menu
        self.assertTrue(any("کد تخفیف" in m and "منوی خرید" in m for m in sent_messages))

        # Check that pending_discount_code in users table remained NULL
        conn = _db()
        u = conn.execute("SELECT pending_discount_code FROM users WHERE id = ?", (uid,)).fetchone()
        conn.close()
        self.assertIsNone(u["pending_discount_code"])


if __name__ == "__main__":
    unittest.main()
