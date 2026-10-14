import hashlib
import hmac
import json
import unittest
from unittest.mock import patch, MagicMock
from urllib.parse import urlencode

import os
os.environ.setdefault("BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

from fastapi.testclient import TestClient

from speedybot.api import app


class TestAdminEndpointsAndStars(unittest.TestCase):
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

    def test_admin_server_status(self):
        with patch("speedybot.api._get_bot_token", return_value=self.bot_token):
            with patch("speedybot.api._is_admin", return_value=True):
                init_data = self._generate_valid_init_data({"id": 111222, "first_name": "Admin"})
                response = self.client.get("/api/admin/server-status", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertIn("cpu_load", data)
                self.assertIn("ram", data)
                self.assertIn("disk", data)
                self.assertIn("xui", data)

    def test_admin_builder_defaults(self):
        with patch("speedybot.api._get_bot_token", return_value=self.bot_token):
            with patch("speedybot.api._is_admin", return_value=True):
                init_data = self._generate_valid_init_data({"id": 111222, "first_name": "Admin"})
                # GET
                get_res = self.client.get("/api/admin/builder/defaults", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(get_res.status_code, 200)
                bdata = get_res.json()
                self.assertIn("month_price", bdata)

                # POST
                try:
                    post_res = self.client.post(
                        "/api/admin/builder/defaults",
                        json={
                            "month_price": 130000,
                            "gb_price": 1100,
                            "traffic_unlimited_price": 550000
                        },
                        headers={"X-Telegram-Init-Data": init_data}
                    )
                    self.assertEqual(post_res.status_code, 200)
                    self.assertIn(post_res.json()["status"], ["ok", "saved"])
                finally:
                    # Reset to original values
                    self.client.post(
                        "/api/admin/builder/defaults",
                        json={
                            "month_price": 120000,
                            "gb_price": 1000,
                            "traffic_unlimited_price": 500000
                        },
                        headers={"X-Telegram-Init-Data": init_data}
                    )

    def test_admin_payments_settings(self):
        with patch("speedybot.api._get_bot_token", return_value=self.bot_token):
            with patch("speedybot.api._is_admin", return_value=True):
                init_data = self._generate_valid_init_data({"id": 111222, "first_name": "Admin"})
                get_res = self.client.get("/api/admin/payments", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(get_res.status_code, 200)
                pdata = get_res.json()
                self.assertIn("stars", pdata)
                self.assertIn("rate", pdata["stars"])

                post_res = self.client.post(
                    "/api/admin/payments",
                    json={
                        "card_enabled": True,
                        "card_number": "6037997100000000",
                        "card_holder": "تست دارنده",
                        "stars_enabled": True,
                        "stars_rate": 1600
                    },
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(post_res.status_code, 200)
                self.assertIn(post_res.json()["status"], ["ok", "saved"])

    def test_admin_plans_crud(self):
        with patch("speedybot.api._get_bot_token", return_value=self.bot_token):
            with patch("speedybot.api._is_admin", return_value=True):
                init_data = self._generate_valid_init_data({"id": 111222, "first_name": "Admin"})

                # Create plan
                create_res = self.client.post(
                    "/api/admin/plans",
                    json={
                        "name": "پلن تستی ادمین",
                        "price": 99000,
                        "traffic_gb": 30,
                        "duration_days": 30,
                        "category_id": 1,
                        "description": "توضیح تستی"
                    },
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(create_res.status_code, 200)
                plan_id = create_res.json()["plan_id"]

                # Toggle
                toggle_res = self.client.post(f"/api/admin/plans/{plan_id}/toggle", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(toggle_res.status_code, 200)

                # Update
                update_res = self.client.put(
                    f"/api/admin/plans/{plan_id}",
                    json={"name": "پلن ویرایش شده", "price": 105000},
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(update_res.status_code, 200)

                # Delete
                del_res = self.client.delete(f"/api/admin/plans/{plan_id}", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(del_res.status_code, 200)

    def test_admin_users_and_balance(self):
        with patch("speedybot.api._get_bot_token", return_value=self.bot_token):
            with patch("speedybot.api._is_admin", return_value=True):
                init_data = self._generate_valid_init_data({"id": 111222, "first_name": "Admin"})
                # Get users
                res = self.client.get("/api/admin/users", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(res.status_code, 200)
                users = res.json()["users"]
                self.assertIsInstance(users, list)

                # Adjust balance for a test user
                adj_res = self.client.post(
                    "/api/admin/users/111222/balance",
                    json={"amount": 50000, "description": "شارژ هدیه تست"},
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(adj_res.status_code, 200)

    def test_admin_blacklist(self):
        with patch("speedybot.api._get_bot_token", return_value=self.bot_token):
            with patch("speedybot.api._is_admin", return_value=True):
                init_data = self._generate_valid_init_data({"id": 111222, "first_name": "Admin"})
                # Add to blacklist
                add_res = self.client.post(
                    "/api/admin/blacklist/add",
                    json={"user_id": 999888777, "reason": "اسپم"},
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(add_res.status_code, 200)

                # List blacklist
                list_res = self.client.get("/api/admin/blacklist", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(list_res.status_code, 200)
                self.assertTrue(any(u["user_id"] == 999888777 for u in list_res.json()["blacklist"]))

                # Remove from blacklist
                rem_res = self.client.post(
                    "/api/admin/blacklist/remove",
                    json={"user_id": 999888777},
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(rem_res.status_code, 200)

    def test_admin_admins_management(self):
        with patch("speedybot.api._get_bot_token", return_value=self.bot_token):
            with patch("speedybot.api._is_admin", return_value=True):
                init_data = self._generate_valid_init_data({"id": 111222, "first_name": "Admin"})
                # Add admin
                add_res = self.client.post(
                    "/api/admin/admins/add",
                    json={"user_id": 555444333},
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(add_res.status_code, 200)

                # List
                list_res = self.client.get("/api/admin/admins", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(list_res.status_code, 200)
                self.assertTrue(any(a["user_id"] == 555444333 for a in list_res.json()["admins"]))

                # Remove
                rem_res = self.client.post(
                    "/api/admin/admins/remove",
                    json={"user_id": 555444333},
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(rem_res.status_code, 200)

    def test_admin_backups(self):
        with patch("speedybot.api._get_bot_token", return_value=self.bot_token):
            with patch("speedybot.api._is_admin", return_value=True):
                init_data = self._generate_valid_init_data({"id": 111222, "first_name": "Admin"})
                # Create backup
                create_res = self.client.post("/api/admin/backups/create", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(create_res.status_code, 200)
                self.assertEqual(create_res.json()["status"], "ok")

                # List backups
                list_res = self.client.get("/api/admin/backups", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(list_res.status_code, 200)
                self.assertIsInstance(list_res.json()["backups"], list)

    def test_admin_ops_mode(self):
        with patch("speedybot.api._get_bot_token", return_value=self.bot_token):
            with patch("speedybot.api._is_admin", return_value=True):
                init_data = self._generate_valid_init_data({"id": 111222, "first_name": "Admin"})
                post_res = self.client.post(
                    "/api/admin/ops/mode",
                    json={"mode": "SALES_PAUSED", "reason": "به‌روزرسانی سرور"},
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(post_res.status_code, 200)

                get_res = self.client.get("/api/admin/ops/mode", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(get_res.status_code, 200)
                self.assertEqual(get_res.json()["mode"], "SALES_PAUSED")

                # Revert to NORMAL
                self.client.post(
                    "/api/admin/ops/mode",
                    json={"mode": "NORMAL", "reason": ""},
                    headers={"X-Telegram-Init-Data": init_data}
                )

    def test_init_stars_order(self):
        with patch("speedybot.api._get_bot_token", return_value=self.bot_token):
            init_data = self._generate_valid_init_data({"id": 888777, "first_name": "Reza"})
            with patch("speedybot.core.bot.create_invoice_link", return_value="https://t.me/$invoice_test_link") as mock_invoice:
                payload = {
                    "custom_spec": {
                        "months": 1,
                        "volume_gb": 20,
                        "ip_limit": 1
                    }
                }
                res = self.client.post("/api/orders/init-stars", json=payload, headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(res.status_code, 200)
                data = res.json()
    def test_admin_plans_group_name(self):
        with patch("speedybot.api._get_bot_token", return_value=self.bot_token):
            with patch("speedybot.api._is_admin", return_value=True):
                init_data = self._generate_valid_init_data({"id": 111222, "first_name": "Admin"})
                # Create with group_name
                create_res = self.client.post(
                    "/api/admin/plans",
                    json={
                        "name": "پلن VIP تست",
                        "price": 120000,
                        "volume_gb": 30,
                        "days": 30,
                        "ip_limit": 2,
                        "group_name": "VIP_Clients"
                    },
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(create_res.status_code, 200)
                plan_id = create_res.json()["plan_id"]

                # Verify in list
                list_res = self.client.get("/api/admin/plans", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(list_res.status_code, 200)
                plans = list_res.json()["plans"]
                created_plan = next((p for p in plans if p["id"] == plan_id), None)
                self.assertIsNotNone(created_plan)
                self.assertEqual(created_plan["group_name"], "VIP_Clients")

                # Update group_name
                update_res = self.client.put(
                    f"/api/admin/plans/{plan_id}",
                    json={"group_name": "Super_VIP"},
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(update_res.status_code, 200)

                # Verify update
                list_res2 = self.client.get("/api/admin/plans", headers={"X-Telegram-Init-Data": init_data})
                updated_plan = next((p for p in list_res2.json()["plans"] if p["id"] == plan_id), None)
                self.assertEqual(updated_plan["group_name"], "Super_VIP")

                # Cleanup
                self.client.delete(f"/api/admin/plans/{plan_id}", headers={"X-Telegram-Init-Data": init_data})

    def test_admin_xui_endpoints(self):
        with patch("speedybot.api._get_bot_token", return_value=self.bot_token):
            with patch("speedybot.api._is_admin", return_value=True):
                init_data = self._generate_valid_init_data({"id": 111222, "first_name": "Admin"})
                with patch("speedybot.core._xui_list_groups", return_value=[{"id": 1, "name": "Customers"}, {"id": 2, "name": "Trial"}]):
                    res = self.client.get("/api/admin/xui/groups", headers={"X-Telegram-Init-Data": init_data})
                    self.assertEqual(res.status_code, 200)
                    self.assertEqual(res.json()["total"], 2)

                with patch("speedybot.core.reconcile_service_groups", return_value={"updated": 5, "errors": []}):
                    res = self.client.post("/api/admin/xui/groups/reconcile", headers={"X-Telegram-Init-Data": init_data})
                    self.assertEqual(res.status_code, 200)
                    self.assertEqual(res.json()["status"], "success")

                with patch("speedybot.core._run_xui_diagnostic", return_value="✅ Inbounds: OK"):
                    res = self.client.get("/api/admin/xui/test", headers={"X-Telegram-Init-Data": init_data})
                    self.assertEqual(res.status_code, 200)
                    self.assertIn("Inbounds", res.json()["result"])

    def test_admin_rewards_endpoints(self):
        with patch("speedybot.api._get_bot_token", return_value=self.bot_token):
            with patch("speedybot.api._is_admin", return_value=True):
                init_data = self._generate_valid_init_data({"id": 111222, "first_name": "Admin"})
                # Cashback
                cb_res = self.client.post("/api/admin/rewards/cashback", json={"percent": 5.5}, headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(cb_res.status_code, 200)

                # Create Discount Code
                disc_res = self.client.post(
                    "/api/admin/rewards/discounts",
                    json={
                        "code": "TEST50",
                        "discount_type": "PERCENT",
                        "value": 50,
                        "min_purchase": 50000,
                        "max_uses": 10
                    },
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(disc_res.status_code, 200)

                # Create Gift Code
                gift_res = self.client.post(
                    "/api/admin/rewards/gifts",
                    json={"code": "GIFT20K", "amount": 20000, "max_uses": 5},
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(gift_res.status_code, 200)

                # Get Rewards
                get_rewards = self.client.get("/api/admin/rewards", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(get_rewards.status_code, 200)
                data = get_rewards.json()
                self.assertEqual(data["cashback_percent"], 5.5)
                self.assertTrue(any(d["code"] == "TEST50" for d in data["discount_codes"]))
                self.assertTrue(any(g["code"] == "GIFT20K" for g in data["gift_codes"]))

                # Delete Codes
                del_d = self.client.delete("/api/admin/rewards/discounts/TEST50", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(del_d.status_code, 200)
                del_g = self.client.delete("/api/admin/rewards/gifts/GIFT20K", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(del_g.status_code, 200)

    def test_admin_affiliate_and_content_security(self):
        with patch("speedybot.api._get_bot_token", return_value=self.bot_token):
            with patch("speedybot.api._is_admin", return_value=True):
                init_data = self._generate_valid_init_data({"id": 111222, "first_name": "Admin"})
                # Affiliate GET & POST
                aff_get = self.client.get("/api/admin/affiliate", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(aff_get.status_code, 200)
                aff_post = self.client.post(
                    "/api/admin/affiliate/settings",
                    json={"enabled": True, "percent": 12.5},
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(aff_post.status_code, 200)

                # Content & Security GET & POST
                sec_get = self.client.get("/api/admin/content-security", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(sec_get.status_code, 200)
                sec_post = self.client.post(
                    "/api/admin/content-security",
                    json={
                        "welcome_text": "خوش آمدید تستی",
                        "phone_verification_required": False,
                        "membership_required": False
                    },
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(sec_post.status_code, 200)


if __name__ == "__main__":
    unittest.main()
