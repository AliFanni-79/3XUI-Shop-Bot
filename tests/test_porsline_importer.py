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
            {"responder_id": 222, "responder_code": "codeB"},
            {"responder_id": 333, "responder_code": "codeA"},  # duplicate codeA
        ]

        # Mode: code
        codes = extract_identifiers(sample_responses, mode="code")
        self.assertEqual(len(codes), 2)
        self.assertEqual([c["code"] for c in codes], ["CODEA", "CODEB"])

        # Mode: id
        ids = extract_identifiers(sample_responses, mode="id")
        self.assertEqual(len(ids), 3)
        self.assertEqual([c["code"] for c in ids], ["111", "222", "333"])

        # Mode: both
        both = extract_identifiers(sample_responses, mode="both")
        self.assertEqual(len(both), 5)  # CODEA, 111, CODEB, 222, 333

    def test_build_stepped_discount_payload(self):
        payload = build_stepped_discount_payload("TEST_CODE", days=180, survey_id=2682416, responder_id=999)
        self.assertEqual(payload["code"], "TEST_CODE")
        self.assertEqual(payload["discount_type"], "PERCENT")
        self.assertEqual(payload["value"], 100.0)
        self.assertEqual(payload["max_uses"], 0)
        self.assertEqual(payload["per_user_limit"], 0)
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

    def test_save_to_db_and_evaluate_multi_step(self):
        payload = build_stepped_discount_payload("TEST_STEPPED", days=180, survey_id=2682416)
        saved = save_discounts_to_db([payload], db_path=self.db_path)
        self.assertEqual(saved, 1)

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

        row = conn.execute("SELECT * FROM discount_codes WHERE code = 'TEST_STEPPED'").fetchone()
        self.assertIsNotNone(row)

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
            "INSERT INTO discount_redemptions (code, user_id, tx_id, discount_amount, step_index, status, created_at) VALUES ('TEST_STEPPED', ?, 1, 200000, 1, 'APPLIED', ?)",
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
            "INSERT INTO discount_redemptions (code, user_id, tx_id, discount_amount, step_index, status, created_at) VALUES ('TEST_STEPPED', ?, 2, 100000, 2, 'APPLIED', ?)",
            (uid, now_ts)
        )
        conn.commit()

        # 3rd use: 2 prior redemptions -> 25% discount
        ev3 = core.evaluate_discount_row_for_user(conn, row, uid, base_price=base_price)
        self.assertTrue(ev3["eligible"])
        self.assertEqual(ev3["discount_value"], 25.0)
        self.assertEqual(ev3["discount_amount"], 50000)
        self.assertEqual(ev3["final_price"], 150000)

        # Record 3rd redemption
        conn.execute(
            "INSERT INTO discount_redemptions (code, user_id, tx_id, discount_amount, step_index, status, created_at) VALUES ('TEST_STEPPED', ?, 3, 50000, 3, 'APPLIED', ?)",
            (uid, now_ts)
        )
        conn.commit()

        # 4th use: 3 prior redemptions -> repeats 25% discount!
        ev4 = core.evaluate_discount_row_for_user(conn, row, uid, base_price=base_price)
        self.assertTrue(ev4["eligible"])
        self.assertEqual(ev4["discount_value"], 25.0)
        self.assertEqual(ev4["discount_amount"], 50000)
        self.assertEqual(ev4["final_price"], 150000)

        # 5th use: 4 prior redemptions -> still repeats 25% discount!
        conn.execute(
            "INSERT INTO discount_redemptions (code, user_id, tx_id, discount_amount, step_index, status, created_at) VALUES ('TEST_STEPPED', ?, 4, 50000, 3, 'APPLIED', ?)",
            (uid, now_ts)
        )
        conn.commit()

        ev5 = core.evaluate_discount_row_for_user(conn, row, uid, base_price=base_price)
        self.assertTrue(ev5["eligible"])
        self.assertEqual(ev5["discount_value"], 25.0)
        self.assertEqual(ev5["discount_amount"], 50000)
        self.assertEqual(ev5["final_price"], 150000)

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
