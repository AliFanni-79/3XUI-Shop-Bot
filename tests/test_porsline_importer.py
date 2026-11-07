import json
import os
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

from scripts.import_porsline_discounts import (
    build_stepped_discount_payload,
    ensure_db_schema,
    extract_identifiers,
    fetch_porsline_responses,
    save_discounts_to_db,
)
from xuishop import core


class TestPorslineImporter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "test_app.db")
        conn = sqlite3.connect(self.db_path)
        ensure_db_schema(conn)
        conn.close()

    def tearDown(self):
        try:
            self.tmp.cleanup()
        except Exception:
            pass

    def test_extract_identifiers(self):
        sample_responses = [
            {"responder_id": 111, "responder_code": "codeA"},
            {"responder_id": 222, "responder_code": "CqyRa"},
            {"responder_id": 333, "responder_code": "codeA"},  # duplicate codeA
        ]

        # Default mode: code (exact case preserved from Porsline)
        default_codes = extract_identifiers(sample_responses)
        self.assertEqual(len(default_codes), 2)
        self.assertEqual([c["code"] for c in default_codes], ["codeA", "CqyRa"])

        # Explicit mode: code
        codes = extract_identifiers(sample_responses, mode="code")
        self.assertEqual(len(codes), 2)
        self.assertEqual([c["code"] for c in codes], ["codeA", "CqyRa"])

        # Mode: id
        ids = extract_identifiers(sample_responses, mode="id")
        self.assertEqual(len(ids), 3)
        self.assertEqual([c["code"] for c in ids], ["111", "222", "333"])

        # Mode: both
        both = extract_identifiers(sample_responses, mode="both")
        self.assertEqual(len(both), 5)  # codeA, 111, CqyRa, 222, 333
        self.assertEqual([c["code"] for c in both], ["codeA", "111", "CqyRa", "222", "333"])

    def test_build_stepped_discount_payload(self):
        payload = build_stepped_discount_payload("CqyRa", days=180, max_uses=10, survey_id=2682416, responder_id=999)
        self.assertEqual(payload["code"], "CqyRa")
        self.assertEqual(payload["discount_type"], "PERCENT")
        self.assertEqual(payload["value"], 100.0)
        self.assertEqual(payload["max_uses"], 10)
        self.assertEqual(payload["per_user_limit"], 10)
        self.assertEqual(payload["active"], 1)

        now = int(time.time())
        self.assertTrue(now + 179 * 86400 <= payload["expires_at"] <= now + 181 * 86400)

        steps = json.loads(payload["steps_json"])
        self.assertEqual(len(steps), 3)
        self.assertEqual(steps[0]["step"], 1)
        self.assertEqual(steps[0]["discount_value"], 100.0)
        self.assertFalse(steps[0]["repeat_after"])

        self.assertEqual(steps[1]["step"], 2)
        self.assertEqual(steps[1]["discount_value"], 50.0)
        self.assertFalse(steps[1]["repeat_after"])

        self.assertEqual(steps[2]["step"], 3)
        self.assertEqual(steps[2]["discount_value"], 25.0)
        self.assertTrue(steps[2]["repeat_after"])
        self.assertEqual(steps[2]["label"], "بار سوم به بعد: ۲۵٪ تخفیف")
        self.assertNotIn("همیشگی", steps[2]["label"])

    def test_save_to_db_and_evaluate_multi_step(self):
        payload = build_stepped_discount_payload("Test_Stepped", days=180, max_uses=10, survey_id=2682416)
        saved = save_discounts_to_db([payload], db_path=self.db_path)
        self.assertEqual(saved, 1)
        self.assertEqual(saved.inserted, 1)
        self.assertEqual(saved.skipped, 0)

        # Attempt to save the same code again: must be skipped (not re-added or overwritten)
        saved_again = save_discounts_to_db([payload], db_path=self.db_path)
        self.assertEqual(saved_again, 0)
        self.assertEqual(saved_again.inserted, 0)
        self.assertEqual(saved_again.skipped, 1)

        # Attempt to save a mix of existing and new: only new is added
        payload2 = build_stepped_discount_payload("New_Code_2", days=180, max_uses=10)
        saved_mix = save_discounts_to_db([payload, payload2], db_path=self.db_path)
        self.assertEqual(saved_mix, 1)
        self.assertEqual(saved_mix.inserted, 1)
        self.assertEqual(saved_mix.skipped, 1)

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # Create discount_redemptions table for testing usage history
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS discount_redemptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                tx_id INTEGER NOT NULL,
                discount_amount INTEGER NOT NULL DEFAULT 0,
                cashback_percent REAL NOT NULL DEFAULT 0,
                step_index INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'RESERVED',
                created_at INTEGER NOT NULL
            )
            """
        )
        conn.commit()

        row = conn.execute("SELECT * FROM discount_codes WHERE code = 'Test_Stepped'").fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["code"], "Test_Stepped")  # exact case preserved

        uid = 5001
        base_price = 200000

        # 1st use: 0 prior redemptions -> 100% discount
        ev1 = core.evaluate_discount_row_for_user(conn, row, uid, base_price=base_price)
        self.assertTrue(ev1["eligible"])
        self.assertEqual(ev1["discount_value"], 100.0)
        self.assertEqual(ev1["discount_amount"], 200000)
        self.assertEqual(ev1["final_price"], 0)

        # Record 1st redemption
        now_ts = int(time.time())
        conn.execute(
            "INSERT INTO discount_redemptions (code, user_id, tx_id, discount_amount, step_index, status, created_at) VALUES ('Test_Stepped', ?, 1, 200000, 1, 'APPLIED', ?)",
            (uid, now_ts)
        )
        conn.commit()

        # 2nd use: 1 prior redemption -> 50% discount
        ev2 = core.evaluate_discount_row_for_user(conn, row, uid, base_price=base_price)
        self.assertTrue(ev2["eligible"])
        self.assertEqual(ev2["discount_value"], 50.0)
        self.assertEqual(ev2["discount_amount"], 100000)
        self.assertEqual(ev2["final_price"], 100000)

        # Record 2nd redemption
        conn.execute(
            "INSERT INTO discount_redemptions (code, user_id, tx_id, discount_amount, step_index, status, created_at) VALUES ('Test_Stepped', ?, 2, 100000, 2, 'APPLIED', ?)",
            (uid, now_ts)
        )
        conn.commit()

        # 3rd use to 10th use: repeat step 3 (25% discount)
        for use_num in range(3, 11):
            ev = core.evaluate_discount_row_for_user(conn, row, uid, base_price=base_price)
            self.assertTrue(ev["eligible"], f"Use {use_num} should be eligible")
            self.assertEqual(ev["discount_value"], 25.0)
            self.assertEqual(ev["discount_amount"], 50000)
            self.assertEqual(ev["final_price"], 150000)
            conn.execute(
                "INSERT INTO discount_redemptions (code, user_id, tx_id, discount_amount, step_index, status, created_at) VALUES ('Test_Stepped', ?, ?, 50000, 3, 'APPLIED', ?)",
                (uid, use_num, now_ts)
            )
            conn.commit()

        # 11th use: max 10 uses reached -> NOT eligible!
        ev11 = core.evaluate_discount_row_for_user(conn, row, uid, base_price=base_price)
        self.assertFalse(ev11["eligible"])
        self.assertTrue(
            "سقف مجاز" in ev11["reason"] or "ظرفیت کل" in ev11["reason"],
            f"Expected limit error, got: {ev11['reason']}"
        )

        # Another user also blocked because total max_uses=10 reached
        ev_other = core.evaluate_discount_row_for_user(conn, row, 9999, base_price=base_price)
        self.assertFalse(ev_other["eligible"])
        self.assertIn("ظرفیت کل", ev_other["reason"])

        conn.close()

    def test_live_api_fetch(self):
        """Test live fetch from Porsline survey 2682416 with the user's token."""
        responses, meta = fetch_porsline_responses(
            survey_id=2682416,
            api_token="5bf19a2541c51e30c8a2fb88009f50f235ae3c01",
            page_size=1000
        )
        self.assertGreater(len(responses), 0)
        self.assertGreaterEqual(meta.get("responders_count", 0), 180)
        first = responses[0]
        self.assertIn("responder_code", first)
        self.assertIn("responder_id", first)


if __name__ == "__main__":
    unittest.main()
