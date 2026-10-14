import hashlib
import hmac
import json
import unittest
from unittest.mock import MagicMock, patch
from urllib.parse import urlencode

import os
os.environ.setdefault("BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

from fastapi.testclient import TestClient

from speedybot.api import app, _verify_init_data, _VERIFIED_CACHE


class TestMiniAppApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from speedybot import core, storage
        core.init_db()
        storage.init_db()
        cls.client = TestClient(app)
        cls.bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"

    def _generate_valid_init_data(self, user_dict, bot_token=None):
        token = bot_token or self.bot_token
        secret_key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
        user_json = json.dumps(user_dict)
        data = {
            "auth_date": "1710000000",
            "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
            "user": user_json,
        }
        check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
        data_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
        data["hash"] = data_hash
        return urlencode(data)

    def test_verify_init_data_success(self):
        with patch("speedybot.api._get_bot_token", return_value=self.bot_token):
            init_data = self._generate_valid_init_data({"id": 999123, "first_name": "Ali"})
            verified = _verify_init_data(init_data)
            self.assertEqual(verified["id"], 999123)
            self.assertEqual(verified["first_name"], "Ali")

    def test_verify_init_data_tampered(self):
        with patch("speedybot.api._get_bot_token", return_value=self.bot_token):
            init_data = self._generate_valid_init_data({"id": 999123, "first_name": "Ali"})
            # Tamper with the string
            tampered = init_data.replace("999123", "999999")
            with self.assertRaises(Exception):
                _verify_init_data(tampered)

    def test_auth_me_endpoint_unauthorized_without_header(self):
        response = self.client.get("/api/auth/me")
        self.assertEqual(response.status_code, 401)

    def test_auth_me_endpoint_success(self):
        with patch("speedybot.api._get_bot_token", return_value=self.bot_token):
            init_data = self._generate_valid_init_data({"id": 888777, "first_name": "Reza"})
            response = self.client.get("/api/auth/me", headers={"X-Telegram-Init-Data": init_data})
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["id"], 888777)
            self.assertEqual(data["first_name"], "Reza")
            self.assertIn("balance", data)
            self.assertIn("is_admin", data)

    def test_builder_config_endpoint(self):
        with patch("speedybot.api._get_bot_token", return_value=self.bot_token):
            init_data = self._generate_valid_init_data({"id": 888777, "first_name": "Reza"})
            response = self.client.get("/api/builder/config", headers={"X-Telegram-Init-Data": init_data})
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["month_price"], 120000)
            self.assertEqual(data["dur_discounts"]["3"], 5)
            self.assertEqual(data["dur_discounts"]["6"], 10)
            self.assertEqual(data["dur_discounts"]["12"], 20)

    def test_builder_calculate_valid_plan(self):
        with patch("speedybot.api._get_bot_token", return_value=self.bot_token):
            init_data = self._generate_valid_init_data({"id": 888777, "first_name": "Reza"})
            payload = {
                "months": 3,
                "volume_gb": 100,
                "ip_limit": 2
            }
            response = self.client.post("/api/builder/calculate", json=payload, headers={"X-Telegram-Init-Data": init_data})
            self.assertEqual(response.status_code, 200)
            data = response.json()
            # 3 months: 360,000 - 5% = 342,000
            self.assertEqual(data["duration"]["final_price"], 342000)
            # 100 GB: 100,000 - 5% (>50GB discount) = 95,000
            self.assertEqual(data["traffic"]["final_price"], 95000)
            # 2 users: 20,000
            self.assertEqual(data["user_limit"]["cost"], 20000)
            # Total: 342000 + 95000 + 20000 = 457000
            self.assertEqual(data["total_price"], 457000)

    def test_builder_fair_use_unlimited_traffic_and_users_forbidden(self):
        with patch("speedybot.api._get_bot_token", return_value=self.bot_token):
            init_data = self._generate_valid_init_data({"id": 888777, "first_name": "Reza"})
            payload = {
                "months": 1,
                "volume_gb": 0,  # unlimited
                "ip_limit": 0    # unlimited
            }
            response = self.client.post("/api/builder/calculate", json=payload, headers={"X-Telegram-Init-Data": init_data})
            self.assertEqual(response.status_code, 400)
            self.assertIn("مصرف منصفانه", response.json()["detail"])

    def test_builder_init_custom_card_order(self):
        with patch("speedybot.api._get_bot_token", return_value=self.bot_token):
            init_data = self._generate_valid_init_data({"id": 888777, "first_name": "Reza"})
            payload = {
                "months": 1,
                "volume_gb": 20,
                "ip_limit": 1,
                "custom_name": "my_work_laptop"
            }
            with patch("speedybot.core._start_card_checkout") as mock_checkout:
                response = self.client.post("/api/orders/init-custom-card", json=payload, headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertEqual(data["status"], "awaiting_receipt")
                self.assertTrue(mock_checkout.called)
                self.assertEqual(mock_checkout.call_args[1].get("custom_name"), "my_work_laptop")


    def test_get_active_gateways(self):
        with patch("speedybot.api._get_bot_token", return_value=self.bot_token):
            init_data = self._generate_valid_init_data({"id": 888777, "first_name": "Reza"})
            response = self.client.get("/api/gateways/active", headers={"X-Telegram-Init-Data": init_data})
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data["card"])
            self.assertTrue(data["wallet"])
            self.assertFalse(data["zibal"])
            self.assertFalse(data["zarinpal"])

    def test_init_gateway_disabled_raises_400(self):
        with patch("speedybot.api._get_bot_token", return_value=self.bot_token):
            init_data = self._generate_valid_init_data({"id": 888777, "first_name": "Reza"})
            payload = {
                "gateway": "zibal",
                "months": 1,
                "volume_gb": 10,
                "ip_limit": 1
            }
            response = self.client.post("/api/orders/init-gateway", json=payload, headers={"X-Telegram-Init-Data": init_data})
            self.assertEqual(response.status_code, 400)
            self.assertIn("غیرفعال", response.json()["detail"])

    def test_admin_gateways_save_and_retrieve(self):
        with patch("speedybot.api._get_bot_token", return_value=self.bot_token):
            with patch("speedybot.api._is_admin", return_value=True):
                init_data = self._generate_valid_init_data({"id": 111222, "first_name": "Admin"})
                payload = {
                    "zibal_enabled": True,
                    "zibal_merchant": "zibal_test_key",
                    "zibal_sandbox": True,
                    "zarinpal_enabled": False,
                    "zarinpal_merchant": "",
                    "zarinpal_sandbox": False
                }
                save_res = self.client.post("/api/admin/gateways", json=payload, headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(save_res.status_code, 200)

                get_res = self.client.get("/api/admin/gateways", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(get_res.status_code, 200)
                gdata = get_res.json()
                self.assertTrue(gdata["zibal"]["enabled"])
                self.assertEqual(gdata["zibal"]["merchant"], "zibal_test_key")
                self.assertTrue(gdata["zibal"]["sandbox"])

                # Revert back to disabled
                payload["zibal_enabled"] = False
                payload["zibal_merchant"] = ""
                self.client.post("/api/admin/gateways", json=payload, headers={"X-Telegram-Init-Data": init_data})

    def test_app_config_endpoint(self):
        response = self.client.get("/api/app/config")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("webapp_title", data)

    def test_admin_branding_save_and_retrieve(self):
        with patch("speedybot.api._get_bot_token", return_value=self.bot_token):
            with patch("speedybot.api._is_admin", return_value=True):
                init_data = self._generate_valid_init_data({"id": 111222, "first_name": "Admin"})

                # Save new title
                save_res = self.client.post(
                    "/api/admin/branding",
                    json={"webapp_title": "فروشگاه تست جدید"},
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(save_res.status_code, 200)
                self.assertEqual(save_res.json()["webapp_title"], "فروشگاه تست جدید")

                # Retrieve via admin endpoint
                get_res = self.client.get("/api/admin/branding", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(get_res.status_code, 200)
                self.assertEqual(get_res.json()["webapp_title"], "فروشگاه تست جدید")

                # Check it reflects in /api/auth/me
                me_res = self.client.get("/api/auth/me", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(me_res.status_code, 200)
                self.assertEqual(me_res.json()["app_title"], "فروشگاه تست جدید")

                # Reset to default
                self.client.post(
                    "/api/admin/branding",
                    json={"webapp_title": "فروشگاه"},
                    headers={"X-Telegram-Init-Data": init_data}
                )

    def test_spa_root_serves_html(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        # Should return html content with <!DOCTYPE html>
        self.assertIn("<!DOCTYPE html>", response.text)

    def test_get_plans_includes_trial_info(self):
        with patch("speedybot.api._get_bot_token", return_value=self.bot_token):
            init_data = self._generate_valid_init_data({"id": 555666, "first_name": "TestUser"})
            with patch("speedybot.trial.get_trial_eligibility", return_value=(True, 0, 0, "NONE")):
                with patch("speedybot.trial.values", return_value=(0.3, 1, 0, False)):
                    response = self.client.get("/api/plans", headers={"X-Telegram-Init-Data": init_data})
                    self.assertEqual(response.status_code, 200)
                    data = response.json()
                    self.assertIn("categories", data)
                    self.assertIn("trial_info", data)
                    trial = data["trial_info"]
                    self.assertEqual(trial["volume_gb"], 0.3)
                    self.assertEqual(trial["days"], 1)
                    self.assertEqual(trial["ip_limit"], 0)
                    self.assertEqual(trial["price"], 0)
                    self.assertTrue(trial["eligible"])

    def test_get_trial_status_and_claim(self):
        with patch("speedybot.api._get_bot_token", return_value=self.bot_token):
            init_data = self._generate_valid_init_data({"id": 555666, "first_name": "TestUser"})
            with patch("speedybot.trial.get_trial_eligibility", return_value=(True, 0, 0, "NONE")):
                with patch("speedybot.trial.values", return_value=(0.3, 1, 0, False)):
                    status_res = self.client.get("/api/trial/status", headers={"X-Telegram-Init-Data": init_data})
                    self.assertEqual(status_res.status_code, 200)
                    status_data = status_res.json()
                    self.assertTrue(status_data["eligible"])
                    self.assertEqual(status_data["remaining_days"], 0)
                    self.assertEqual(status_data["volume_gb"], 0.3)

            # Test successful claim
            with patch("speedybot.trial.issue_trial_for_user", return_value={"success": True, "email": "vpn_trial_555", "sub_url": "https://sub.test/123"}):
                claim_res = self.client.post(
                    "/api/trial/claim",
                    json={"custom_name": "my_fast_vpn"},
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(claim_res.status_code, 200)
                claim_data = claim_res.json()
                self.assertTrue(claim_data["success"])
                self.assertEqual(claim_data["email"], "vpn_trial_555")

            # Test cooldown rejection (already claimed this month)
            with patch("speedybot.trial.issue_trial_for_user", return_value={"success": False, "error": "شما در این ماه از تست رایگان استفاده کرده‌اید. امکان دریافت مجدد تا ۲۵ روز دیگر وجود ندارد."}):
                cooldown_res = self.client.post(
                    "/api/trial/claim",
                    json={"custom_name": "my_fast_vpn"},
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(cooldown_res.status_code, 400)
                self.assertIn("۲۵ روز", cooldown_res.json()["detail"])

    def test_init_card_order_passes_custom_name(self):
        with patch("speedybot.api._get_bot_token", return_value=self.bot_token):
            init_data = self._generate_valid_init_data({"id": 555666, "first_name": "TestUser"})
            with patch("speedybot.api._get_plan", return_value={"id": 1, "name": "Plan 1", "price": 50000, "days": 30, "volume_gb": 10, "ip_limit": 1}):
                with patch("speedybot.core._start_card_checkout") as mock_card_checkout:
                    res = self.client.post(
                        "/api/orders/init-card",
                        json={"plan_id": 1, "custom_name": "home_pc"},
                        headers={"X-Telegram-Init-Data": init_data}
                    )
                    self.assertEqual(res.status_code, 200)
                    self.assertTrue(mock_card_checkout.called)
                    self.assertEqual(mock_card_checkout.call_args[1].get("custom_name"), "home_pc")

    def test_init_wallet_order_passes_custom_name(self):
        with patch("speedybot.api._get_bot_token", return_value=self.bot_token):
            init_data = self._generate_valid_init_data({"id": 555666, "first_name": "TestUser"})
            with patch("speedybot.api._get_plan", return_value={"id": 1, "name": "Plan 1", "price": 50000, "days": 30, "volume_gb": 10, "ip_limit": 1}):
                with patch("speedybot.core._create_checkout_transaction", return_value=({"tx_id": 101, "price": 50000}, None)) as mock_wallet_checkout:
                    with patch("speedybot.core.finalize_service_transaction", return_value=True):
                        res = self.client.post(
                            "/api/orders/init-wallet",
                            json={"plan_id": 1, "custom_name": "office_pc"},
                            headers={"X-Telegram-Init-Data": init_data}
                        )
                        self.assertEqual(res.status_code, 200)
                        self.assertTrue(mock_wallet_checkout.called)
                        self.assertEqual(mock_wallet_checkout.call_args[1].get("custom_name"), "office_pc")


if __name__ == "__main__":
    unittest.main()

