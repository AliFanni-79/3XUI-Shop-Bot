import hashlib
import hmac
import json
import unittest
from unittest.mock import MagicMock, patch
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from speedybot.api import app, _verify_init_data, _VERIFIED_CACHE


class TestMiniAppApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
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
                "ip_limit": 1
            }
            with patch("speedybot.core._start_card_checkout") as mock_checkout:
                response = self.client.post("/api/orders/init-custom-card", json=payload, headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertEqual(data["status"], "awaiting_receipt")
                self.assertTrue(mock_checkout.called)


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
                    json={"webapp_title": "SpeedyBot"},
                    headers={"X-Telegram-Init-Data": init_data}
                )

    def test_spa_root_serves_html(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        # Should return html content with <!DOCTYPE html>
        self.assertIn("<!DOCTYPE html>", response.text)


if __name__ == "__main__":
    unittest.main()

