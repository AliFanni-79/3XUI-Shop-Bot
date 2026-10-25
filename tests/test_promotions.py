import json
import os
import sqlite3
import tempfile
import time
import unittest

os.environ.setdefault("BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
from speedybot import core, storage, context as C


class TieredPromotionsTest(unittest.TestCase):
    def setUp(self):
        self.old_cwd = os.getcwd()
        self.tmp = tempfile.TemporaryDirectory()
        os.chdir(self.tmp.name)
        sqlite3.connect("app.db").close()
        core.init_db()
        C.configure(core)
        storage.init_db()

        conn = core._db_connect()
        now_ts = int(time.time())
        conn.execute(
            "INSERT OR REPLACE INTO users (id, balance, created_at, last_seen_at, is_active) VALUES (1001, 500000, ?, ?, 1)",
            (now_ts, now_ts),
        )
        conn.execute(
            "INSERT OR REPLACE INTO users (id, balance, created_at, last_seen_at, is_active) VALUES (1002, 500000, ?, ?, 1)",
            (now_ts, now_ts),
        )
        conn.execute(
            "INSERT OR REPLACE INTO plans (id, name, price, volume_gb, days, ip_limit, active, sort_order, created_at, updated_at) "
            "VALUES (10, 'پلن تست ماهانه', 200000, 50, 30, 2, 1, 10, ?, ?)",
            (now_ts, now_ts),
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        os.chdir(self.old_cwd)
        try:
            self.tmp.cleanup()
        except Exception:
            pass

    def _create_campaign(self, code, steps, is_auto=1, days=10, title="جشنواره پلکانی"):
        now_ts = int(time.time())
        expires_at = now_ts + days * 86400 if days is not None else None
        per_user_limit = 0 if steps[-1].get("repeat_after") else len(steps)
        conn = core._db_connect()
        conn.execute(
            """INSERT OR REPLACE INTO discount_codes
               (code, discount_type, value, min_purchase, max_uses, per_user_limit, expires_at, active, created_at, is_auto, title, cashback_percent, steps_json)
               VALUES (?, ?, ?, 0, 0, ?, ?, 1, ?, ?, ?, ?, ?)""",
            (
                code,
                steps[0].get("discount_type", "PERCENT"),
                float(steps[0].get("discount_value", 0)),
                per_user_limit,
                expires_at,
                now_ts,
                int(is_auto),
                title,
                float(steps[0].get("cashback_percent", 0)),
                json.dumps(steps, ensure_ascii=False),
            ),
        )
        conn.commit()
        conn.close()

    def test_pattern_100_50_25_repeating(self):
        # 1st time 100%, 2nd time 50%, 3rd+ time 25%
        steps = [
            {"discount_type": "PERCENT", "discount_value": 100, "cashback_percent": 0, "repeat_after": False},
            {"discount_type": "PERCENT", "discount_value": 50, "cashback_percent": 0, "repeat_after": False},
            {"discount_type": "PERCENT", "discount_value": 25, "cashback_percent": 0, "repeat_after": True},
        ]
        self._create_campaign("CAMP_100_50_25", steps, is_auto=1)
        plan = core.get_plan(10)

        # 1st purchase -> 100% discount (price = 0)
        res1, err1 = core._create_checkout_transaction(1001, plan, "WALLET", "NEW")
        self.assertIsNone(err1)
        self.assertEqual(res1["discount"], 200000)
        self.assertEqual(res1["price"], 0)
        self.assertEqual(res1["step_index"], 1)
        core._finish_discount(res1["tx_id"], applied=True)

        # 2nd purchase -> 50% discount (price = 100,000)
        res2, err2 = core._create_checkout_transaction(1001, plan, "WALLET", "RENEWAL", target_service_email="sub_1")
        self.assertIsNone(err2)
        self.assertEqual(res2["discount"], 100000)
        self.assertEqual(res2["price"], 100000)
        self.assertEqual(res2["step_index"], 2)
        core._finish_discount(res2["tx_id"], applied=True)

        # 3rd purchase -> 25% discount (price = 150,000)
        res3, err3 = core._create_checkout_transaction(1001, plan, "WALLET", "NEW")
        self.assertIsNone(err3)
        self.assertEqual(res3["discount"], 50000)
        self.assertEqual(res3["price"], 150000)
        self.assertEqual(res3["step_index"], 3)
        core._finish_discount(res3["tx_id"], applied=True)

        # 4th purchase -> still 25% discount because repeat_after=True
        res4, err4 = core._create_checkout_transaction(1001, plan, "WALLET", "NEW")
        self.assertIsNone(err4)
        self.assertEqual(res4["discount"], 50000)
        self.assertEqual(res4["price"], 150000)
        self.assertEqual(res4["step_index"], 3)

    def test_pattern_25x2_35x2_50_repeating(self):
        # 1st & 2nd: 25%, 3rd & 4th: 35%, 5th+: 50%
        steps = [
            {"discount_type": "PERCENT", "discount_value": 25, "cashback_percent": 0, "repeat_after": False},
            {"discount_type": "PERCENT", "discount_value": 25, "cashback_percent": 0, "repeat_after": False},
            {"discount_type": "PERCENT", "discount_value": 35, "cashback_percent": 0, "repeat_after": False},
            {"discount_type": "PERCENT", "discount_value": 35, "cashback_percent": 0, "repeat_after": False},
            {"discount_type": "PERCENT", "discount_value": 50, "cashback_percent": 0, "repeat_after": True},
        ]
        self._create_campaign("LOYAL5", steps, is_auto=1)
        plan = core.get_plan(10)

        expected_discounts = [50000, 50000, 70000, 70000, 100000, 100000]
        for expected_disc in expected_discounts:
            res, err = core._create_checkout_transaction(1001, plan, "CARD", "NEW")
            self.assertIsNone(err)
            self.assertEqual(res["discount"], expected_disc)
            core._finish_discount(res["tx_id"], applied=True)

    def test_pattern_non_repeating_stops_after_last_step(self):
        # 1st: 25%, 2nd: 50%, no repeat
        steps = [
            {"discount_type": "PERCENT", "discount_value": 25, "cashback_percent": 0, "repeat_after": False},
            {"discount_type": "PERCENT", "discount_value": 50, "cashback_percent": 0, "repeat_after": False},
        ]
        self._create_campaign("TWO_STEP", steps, is_auto=0)
        plan = core.get_plan(10)

        # 1st use with code
        res1, err1 = core._create_checkout_transaction(1001, plan, "CARD", "NEW", explicit_code="TWO_STEP")
        self.assertIsNone(err1)
        self.assertEqual(res1["discount"], 50000)
        core._finish_discount(res1["tx_id"], applied=True)

        # 2nd use with code
        res2, err2 = core._create_checkout_transaction(1001, plan, "CARD", "NEW", explicit_code="TWO_STEP")
        self.assertIsNone(err2)
        self.assertEqual(res2["discount"], 100000)
        core._finish_discount(res2["tx_id"], applied=True)

        # 3rd use -> exhausted, no discount applied
        ok, msg = core.set_pending_discount(1001, "TWO_STEP")
        self.assertFalse(ok)
        res3, err3 = core._create_checkout_transaction(1001, plan, "CARD", "NEW", explicit_code="TWO_STEP")
        self.assertIsNone(err3)
        self.assertEqual(res3["discount"], 0)
        self.assertEqual(res3["price"], 200000)

    def test_combined_discount_and_cashback_and_stepped_cashback(self):
        # 1st time: 10% discount + 0% cashback; 2nd time: 0% discount + 10% cashback
        steps = [
            {"discount_type": "PERCENT", "discount_value": 10, "cashback_percent": 0, "repeat_after": False},
            {"discount_type": "PERCENT", "discount_value": 0, "cashback_percent": 10, "repeat_after": True},
        ]
        self._create_campaign("STEP_CB", steps, is_auto=1)
        plan = core.get_plan(10)

        # 1st purchase -> 10% discount (20,000 off -> 180,000), 0% cashback
        res1, err1 = core._create_checkout_transaction(1002, plan, "WALLET", "NEW")
        self.assertIsNone(err1)
        self.assertEqual(res1["discount"], 20000)
        self.assertEqual(res1["price"], 180000)
        self.assertEqual(res1["cashback_percent"], 0.0)
        conn = core._db_connect()
        conn.execute("UPDATE transactions SET status='APPROVED' WHERE id=?", (res1["tx_id"],))
        conn.commit()
        conn.close()
        core._finish_discount(res1["tx_id"], applied=True)
        cb1 = core.credit_cashback(res1["tx_id"])
        self.assertIsNone(cb1)

        # 2nd purchase -> 0% discount (200,000), 10% cashback (20,000 credited to wallet!)
        res2, err2 = core._create_checkout_transaction(1002, plan, "WALLET", "NEW")
        self.assertIsNone(err2)
        self.assertEqual(res2["discount"], 0)
        self.assertEqual(res2["price"], 200000)
        self.assertEqual(res2["cashback_percent"], 10.0)
        conn = core._db_connect()
        conn.execute("UPDATE transactions SET status='APPROVED' WHERE id=?", (res2["tx_id"],))
        conn.commit()
        conn.close()
        core._finish_discount(res2["tx_id"], applied=True)
        cb2 = core.credit_cashback(res2["tx_id"])
        self.assertIsNotNone(cb2)
        self.assertEqual(cb2["amount"], 20000)

    def test_volume_purchase_ignores_promotions_and_expired_campaign_ignored(self):
        steps = [
            {"discount_type": "PERCENT", "discount_value": 50, "cashback_percent": 20, "repeat_after": True},
        ]
        self._create_campaign("ACTIVE_50", steps, is_auto=1, days=5)
        plan = core.get_plan(10)

        # VOLUME purchase should NOT receive discount or promo cashback
        res_vol, err_vol = core._create_checkout_transaction(
            1001, {"id": 0, "name": "حجم اضافه", "price": 100000, "days": 0, "volume": 10, "ip_limit": 0},
            "CARD", "VOLUME", target_service_email="sub_1", extra_volume_gb=10
        )
        self.assertIsNone(err_vol)
        self.assertEqual(res_vol["discount"], 0)
        self.assertEqual(res_vol["price"], 100000)
        self.assertEqual(res_vol["cashback_percent"], 0.0)

        # Expire the campaign
        conn = core._db_connect()
        conn.execute("UPDATE discount_codes SET expires_at = ? WHERE code = 'ACTIVE_50'", (int(time.time()) - 10,))
        conn.commit()
        conn.close()

        res_exp, err_exp = core._create_checkout_transaction(1001, plan, "CARD", "NEW")
        self.assertIsNone(err_exp)
        self.assertEqual(res_exp["discount"], 0)
        self.assertEqual(res_exp["price"], 200000)

    def test_100_percent_discount_card_checkout_instant_activation(self):
        steps = [{"discount_type": "PERCENT", "discount_value": 100, "cashback_percent": 0, "repeat_after": False}]
        self._create_campaign("FREE100", steps, is_auto=0)
        plan = core.get_plan(10)

        # Mock finalize_service_transaction and bot messages
        finalized_tx = []
        sent_messages = []
        original_finalize = core.finalize_service_transaction
        original_send = core.bot.send_message
        try:
            core.finalize_service_transaction = lambda tx_id: finalized_tx.append(tx_id)
            core.bot.send_message = lambda cid, text, **kw: sent_messages.append((cid, text))

            core._start_card_checkout(1001, 1001, plan, explicit_code="FREE100")
            self.assertEqual(len(finalized_tx), 1)
            tx_id = finalized_tx[0]

            conn = core._db_connect()
            tx = conn.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,)).fetchone()
            conn.close()
            self.assertEqual(tx["price"], 0)
            self.assertEqual(tx["status"], "PROCESSING")
            self.assertTrue(any("رایگان" in msg[1] for msg in sent_messages))
        finally:
            core.finalize_service_transaction = original_finalize
            core.bot.send_message = original_send

    def test_discount_and_gift_descriptions(self):
        conn = core._db_connect()
        now_ts = int(time.time())
        conn.execute(
            """INSERT INTO discount_codes
               (code, discount_type, value, min_purchase, max_uses, per_user_limit, expires_at, active, created_at, is_auto, title, cashback_percent, description)
               VALUES ('DESC_OFF', 'PERCENT', 30, 0, 5, 2, ?, 1, ?, 0, 'تخفیف همراه با توضیح', 0, 'توضیحات اختصاصی تخفیف')""",
            (now_ts + 86400 * 5, now_ts)
        )
        conn.execute(
            """INSERT INTO gift_codes (code, amount, max_uses, expires_at, active, created_at, description)
               VALUES ('DESC_GIFT', 25000, 1, ?, 1, ?, 'توضیحات کارت هدیه')""",
            (now_ts + 86400 * 3, now_ts)
        )
        conn.commit()
        conn.close()

        ok, msg, ev = core.save_user_discount(1001, "DESC_OFF")
        self.assertTrue(ok)
        self.assertEqual(ev["description"], "توضیحات اختصاصی تخفیف")
        self.assertEqual(ev["remaining_days"], 5)
        self.assertEqual(ev["remaining_uses"], 2)

        # Check user saved discounts inquiry
        saved = core.get_user_saved_discounts(1001)
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["code"], "DESC_OFF")
        self.assertEqual(saved[0]["description"], "توضیحات اختصاصی تخفیف")

    def test_saved_discount_cleanup_when_expired_or_exhausted(self):
        conn = core._db_connect()
        now_ts = int(time.time())
        conn.execute(
            """INSERT INTO discount_codes
               (code, discount_type, value, min_purchase, max_uses, per_user_limit, expires_at, active, created_at, is_auto, title, cashback_percent, description)
               VALUES ('EXP_CODE', 'PERCENT', 20, 0, 1, 1, ?, 1, ?, 0, 'تخفیف موقت', 0, 'توضیح')""",
            (now_ts + 3600, now_ts)
        )
        conn.commit()
        conn.close()

        # User saves the discount
        ok, msg, ev = core.save_user_discount(1001, "EXP_CODE")
        self.assertTrue(ok)
        self.assertEqual(len(core.get_user_saved_discounts(1001)), 1)

        # Case 1: Expire by time
        conn = core._db_connect()
        conn.execute("UPDATE discount_codes SET expires_at = ? WHERE code = 'EXP_CODE'", (now_ts - 100,))
        conn.commit()
        conn.close()

        # Querying saved discounts cleans it up and returns empty
        active_saved = core.get_user_saved_discounts(1001)
        self.assertEqual(len(active_saved), 0)

        # Also deleted from discount_codes
        conn = core._db_connect()
        row = conn.execute("SELECT 1 FROM discount_codes WHERE code = 'EXP_CODE'").fetchone()
        conn.close()
        self.assertIsNone(row)

    def test_wallet_api_endpoints(self):
        from fastapi.testclient import TestClient
        from speedybot.api import app, get_current_user

        # Override user auth dependency for user 1001
        app.dependency_overrides[get_current_user] = lambda: {"id": 1001, "balance": 500000}
        client = TestClient(app)

        conn = core._db_connect()
        now_ts = int(time.time())
        conn.execute(
            """INSERT INTO gift_codes (code, amount, max_uses, expires_at, active, created_at, description)
               VALUES ('API_GIFT', 50000, 1, ?, 1, ?, 'هدیه تست')""",
            (now_ts + 86400, now_ts)
        )
        conn.execute(
            """INSERT INTO discount_codes (code, discount_type, value, min_purchase, max_uses, per_user_limit, expires_at, active, created_at, is_auto, title, cashback_percent, description)
               VALUES ('API_OFF', 'PERCENT', 100, 0, 5, 2, ?, 1, ?, 0, 'تخفیف کامل', 0, 'توضیحات تست')""",
            (now_ts + 86400 * 3, now_ts)
        )
        conn.commit()
        conn.close()

        # 1. Redeem gift code via wallet endpoint
        res_g = client.post("/api/wallet/code/redeem", json={"code": "API_GIFT"})
        self.assertEqual(res_g.status_code, 200)
        self.assertEqual(res_g.json()["type"], "GIFT")
        self.assertEqual(res_g.json()["amount"], 50000)

        # 2. Redeem discount code via wallet endpoint
        res_d = client.post("/api/wallet/code/redeem", json={"code": "API_OFF"})
        self.assertEqual(res_d.status_code, 200)
        self.assertEqual(res_d.json()["type"], "DISCOUNT")
        self.assertEqual(res_d.json()["discount"]["description"], "توضیحات تست")

        # 3. Get saved wallet discounts
        res_list = client.get("/api/wallet/discounts")
        self.assertEqual(res_list.status_code, 200)
        discounts = res_list.json()["discounts"]
        self.assertEqual(len(discounts), 1)
        self.assertEqual(discounts[0]["code"], "API_OFF")
        self.assertEqual(discounts[0]["remaining_days"], 3)

        # 4. Attempt to pay with Telegram Stars when 100% discount
        res_stars = client.post("/api/orders/init-stars", json={"plan_id": 10, "discount_code": "API_OFF"})
        self.assertEqual(res_stars.status_code, 400)
        self.assertIn("صفر است", res_stars.json()["detail"])

        app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()

