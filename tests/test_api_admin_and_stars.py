import hashlib
import hmac
import json
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

import os
os.environ.setdefault("BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")

from fastapi.testclient import TestClient

from xuishop.api import app


class TestAdminEndpointsAndStars(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from xuishop import core, storage
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
        with patch("xuishop.api._get_bot_token", return_value=self.bot_token):
            with patch("xuishop.api._is_admin", return_value=True):
                init_data = self._generate_valid_init_data({"id": 111222, "first_name": "Admin"})
                response = self.client.get("/api/admin/server-status", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertIn("cpu_load", data)
                self.assertIn("ram", data)
                self.assertIn("disk", data)
                self.assertIn("xui", data)

    def test_admin_builder_defaults(self):
        with patch("xuishop.api._get_bot_token", return_value=self.bot_token):
            with patch("xuishop.api._is_admin", return_value=True):
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
        with patch("xuishop.api._get_bot_token", return_value=self.bot_token):
            with patch("xuishop.api._is_admin", return_value=True):
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
        with patch("xuishop.api._get_bot_token", return_value=self.bot_token):
            with patch("xuishop.api._is_admin", return_value=True):
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
        with patch("xuishop.api._get_bot_token", return_value=self.bot_token):
            with patch("xuishop.api._is_admin", return_value=True):
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
        with patch("xuishop.api._get_bot_token", return_value=self.bot_token):
            with patch("xuishop.api._is_admin", return_value=True):
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
        with patch("xuishop.api._get_bot_token", return_value=self.bot_token):
            with patch("xuishop.api._is_admin", return_value=True):
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
        with patch("xuishop.api._get_bot_token", return_value=self.bot_token):
            with patch("xuishop.api._is_admin", return_value=True):
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
        with patch("xuishop.api._get_bot_token", return_value=self.bot_token):
            with patch("xuishop.api._is_admin", return_value=True):
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
        with patch("xuishop.api._get_bot_token", return_value=self.bot_token):
            init_data = self._generate_valid_init_data({"id": 888777, "first_name": "Reza"})
            with patch("xuishop.core.bot.create_invoice_link", return_value="https://t.me/$invoice_test_link") as mock_invoice:
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
                self.assertEqual(data.get("invoice_link"), "https://t.me/$invoice_test_link")
                mock_invoice.assert_called_once()
    def test_admin_plans_group_name(self):
        with patch("xuishop.api._get_bot_token", return_value=self.bot_token):
            with patch("xuishop.api._is_admin", return_value=True):
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
        with patch("xuishop.api._get_bot_token", return_value=self.bot_token):
            with patch("xuishop.api._is_admin", return_value=True):
                init_data = self._generate_valid_init_data({"id": 111222, "first_name": "Admin"})
                with patch("xuishop.core._xui_list_groups", return_value=[{"id": 1, "name": "Customers"}, {"id": 2, "name": "Trial"}]):
                    res = self.client.get("/api/admin/xui/groups", headers={"X-Telegram-Init-Data": init_data})
                    self.assertEqual(res.status_code, 200)
                    self.assertEqual(res.json()["total"], 2)

                with patch("xuishop.core.reconcile_service_groups", return_value={"updated": 5, "errors": []}):
                    res = self.client.post("/api/admin/xui/groups/reconcile", headers={"X-Telegram-Init-Data": init_data})
                    self.assertEqual(res.status_code, 200)
                    self.assertEqual(res.json()["status"], "success")

                with patch("xuishop.core._run_xui_diagnostic", return_value="✅ Inbounds: OK"):
                    res = self.client.get("/api/admin/xui/test", headers={"X-Telegram-Init-Data": init_data})
                    self.assertEqual(res.status_code, 200)
                    self.assertIn("Inbounds", res.json()["result"])

    def test_admin_rewards_endpoints(self):
        with patch("xuishop.api._get_bot_token", return_value=self.bot_token):
            with patch("xuishop.api._is_admin", return_value=True):
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
        with patch("xuishop.api._get_bot_token", return_value=self.bot_token):
            with patch("xuishop.api._is_admin", return_value=True):
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


    def test_admin_version_and_stats(self):
        with patch("xuishop.api._get_bot_token", return_value=self.bot_token):
            with patch("xuishop.api._is_admin", return_value=True):
                init_data = self._generate_valid_init_data({"id": 111222, "first_name": "Admin"})
                # Version endpoint
                ver_res = self.client.get("/api/admin/version")
                self.assertEqual(ver_res.status_code, 200)
                self.assertEqual(ver_res.json()["version"], "26.1.0")

                # Stats endpoint contains app_version
                stats_res = self.client.get("/api/admin/stats", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(stats_res.status_code, 200)
                self.assertEqual(stats_res.json()["app_version"], "26.1.0")
                self.assertIn("brand_name", stats_res.json())

    def test_admin_trial_features(self):
        with patch("xuishop.api._get_bot_token", return_value=self.bot_token):
            with patch("xuishop.api._is_admin", return_value=True):
                init_data = self._generate_valid_init_data({"id": 111222, "first_name": "Admin"})
                # GET trial settings
                settings_res = self.client.get("/api/admin/trial/settings", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(settings_res.status_code, 200)
                data = settings_res.json()
                self.assertIn("enabled", data)
                self.assertIn("volume_gb", data)
                self.assertIn("days", data)
                self.assertIn("ip_limit", data)
                self.assertIn("stats", data)

                # POST trial settings
                save_res = self.client.post(
                    "/api/admin/trial/settings",
                    json={
                        "enabled": True,
                        "volume_gb": 1.5,
                        "days": 2,
                        "ip_limit": 1,
                        "cooldown_days": 30,
                        "followup_enabled": True,
                        "followup_delay_hours": 6
                    },
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(save_res.status_code, 200)

                # Inbounds toggle & reset for trial
                tog_res = self.client.post(
                    "/api/admin/trial/inbounds/toggle",
                    json={"inbound_id": 999},
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(tog_res.status_code, 200)
                rst_res = self.client.post("/api/admin/trial/inbounds/reset", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(rst_res.status_code, 200)

                # Overrides CRUD
                save_ov = self.client.post(
                    "/api/admin/trial/overrides",
                    json={"user_id": 98765432, "volume_gb": 5.0, "days": 7, "ip_limit": 2, "note": "VIP trial"},
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(save_ov.status_code, 200)

                get_ov = self.client.get("/api/admin/trial/overrides", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(get_ov.status_code, 200)
                self.assertTrue(any(o["user_id"] == 98765432 for o in get_ov.json()["overrides"]))

                del_ov = self.client.delete("/api/admin/trial/overrides/98765432", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(del_ov.status_code, 200)

    def test_admin_categories_and_volume_packs(self):
        with patch("xuishop.api._get_bot_token", return_value=self.bot_token):
            with patch("xuishop.api._is_admin", return_value=True):
                init_data = self._generate_valid_init_data({"id": 111222, "first_name": "Admin"})
                # Categories CRUD
                c_create = self.client.post(
                    "/api/admin/categories",
                    json={"name": "تست دسته‌بندی ویژه", "active": 1, "sort_order": 50},
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(c_create.status_code, 200)
                cat_id = c_create.json()["category_id"]

                c_list = self.client.get("/api/admin/categories", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(c_list.status_code, 200)
                self.assertTrue(any(c["id"] == cat_id for c in c_list.json()["categories"]))

                c_update = self.client.put(
                    f"/api/admin/categories/{cat_id}",
                    json={"name": "تست دسته‌بندی ویرایش شده", "sort_order": 55},
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(c_update.status_code, 200)

                c_del = self.client.delete(f"/api/admin/categories/{cat_id}", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(c_del.status_code, 200)

                # Volume Packs CRUD
                vp_create = self.client.post(
                    "/api/admin/volume-packs",
                    json={"name": "۱۰ گیگابایت اضافه", "volume_gb": 10.0, "price": 45000, "active": 1, "sort_order": 20},
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(vp_create.status_code, 200)
                pack_id = vp_create.json()["pack_id"]

                vp_list = self.client.get("/api/admin/volume-packs", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(vp_list.status_code, 200)
                self.assertTrue(any(p["id"] == pack_id for p in vp_list.json()["volume_packs"]))

                vp_tog = self.client.post(f"/api/admin/volume-packs/{pack_id}/toggle", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(vp_tog.status_code, 200)

                vp_del = self.client.delete(f"/api/admin/volume-packs/{pack_id}", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(vp_del.status_code, 200)

    def test_admin_crm_and_guides_and_audit(self):
        with patch("xuishop.api._get_bot_token", return_value=self.bot_token):
            with patch("xuishop.api._is_admin", return_value=True):
                init_data = self._generate_valid_init_data({"id": 111222, "first_name": "Admin"})
                # CRM
                crm_get = self.client.get("/api/admin/crm", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(crm_get.status_code, 200)
                self.assertIn("sources", crm_get.json())
                self.assertIn("claims", crm_get.json())

                crm_post = self.client.post(
                    "/api/admin/crm/settings",
                    json={"acquisition_survey_enabled": True, "custom_service_names_enabled": True, "existing_service_link_enabled": True},
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(crm_post.status_code, 200)

                # Guides
                g_get = self.client.get("/api/admin/guides", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(g_get.status_code, 200)

                g_create = self.client.post(
                    "/api/admin/guides",
                    json={"platform": "ANDROID", "media_type": "TEXT", "body": "راهنمای اتصال v2rayNG", "sort_order": 1},
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(g_create.status_code, 200)
                gid = g_create.json()["item_id"]

                g_del = self.client.delete(f"/api/admin/guides/{gid}", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(g_del.status_code, 200)

                g_tog = self.client.post("/api/admin/guides/toggle", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(g_tog.status_code, 200)

                # Audit
                audit_get = self.client.get("/api/admin/audit", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(audit_get.status_code, 200)

                audit_post = self.client.post(
                    "/api/admin/audit/settings",
                    json={"enabled": True, "chat_id": "-100123456789"},
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(audit_post.status_code, 200)

                # Notifications check now
                with patch("xuishop.core.check_service_notifications", return_value={"enabled": True, "tracked": 5, "sent": 0}):
                    notif_res = self.client.post("/api/admin/notifications/check-now", headers={"X-Telegram-Init-Data": init_data})
                    self.assertEqual(notif_res.status_code, 200)

    def test_admin_user_detail(self):
        with patch("xuishop.api._get_bot_token", return_value=self.bot_token):
            with patch("xuishop.api._is_admin", return_value=True):
                init_data = self._generate_valid_init_data({"id": 111222, "first_name": "Admin"})
                res = self.client.get("/api/admin/users/111222", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(res.status_code, 200)
                data = res.json()
                self.assertIn("user", data)
                self.assertIn("transactions", data)
                self.assertIn("services", data)
                self.assertEqual(data["user"]["id"], 111222)

    def test_customer_menu_toggles_and_keyboard(self):
        from xuishop import ui, context as C, core
        C.configure(core)
        with patch("xuishop.api._get_bot_token", return_value=self.bot_token):
            with patch("xuishop.api._is_admin", return_value=True):
                init_data = self._generate_valid_init_data({"id": 111222, "first_name": "Admin"})
                # Get branding
                b_get = self.client.get("/api/admin/branding", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(b_get.status_code, 200)
                self.assertIn("customer_menu", b_get.json())

                # Save branding with toggles
                b_post = self.client.post(
                    "/api/admin/branding",
                    json={
                        "webapp_title": "My Test Shop",
                        "customer_menu": {
                            "buy": True,
                            "account": True,
                            "support": False,
                            "faq": False
                        }
                    },
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(b_post.status_code, 200)
                menu_data = b_post.json()["customer_menu"]
                self.assertTrue(menu_data["buy"])
                self.assertFalse(menu_data["support"])

                # Verify bot reply keyboard respects settings
                kb = ui.main_menu()
                button_texts = []
                for row in kb.keyboard:
                    for b in row:
                        button_texts.append(b["text"] if isinstance(b, dict) else b.text)
                self.assertIn("🛍 مشاهده و خرید پلان‌ها", button_texts)
                self.assertNotIn("📞 پشتیبانی", button_texts)

                # Restore
                self.client.post(
                    "/api/admin/branding",
                    json={
                        "webapp_title": "Shop",
                        "customer_menu": {
                            "buy": True,
                            "account": True,
                            "support": True,
                            "faq": True
                        }
                    },
                    headers={"X-Telegram-Init-Data": init_data}
                )

    def test_guide_media_endpoint_and_urls(self):
        with patch("xuishop.api._get_bot_token", return_value=self.bot_token):
            with patch("xuishop.api._is_admin", return_value=True):
                init_data = self._generate_valid_init_data({"id": 111222, "first_name": "Admin"})
                # 1. External URL guide
                create_ext = self.client.post(
                    "/api/admin/guides",
                    json={
                        "platform": "android",
                        "media_type": "PHOTO",
                        "body": "Guide with external photo",
                        "media_file_id": "https://example.com/screenshot.jpg",
                    },
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(create_ext.status_code, 200)
                ext_id = create_ext.json()["item_id"]

                # Public media route redirects external URLs
                redir_res = self.client.get(f"/api/guides/{ext_id}/media", follow_redirects=False)
                self.assertEqual(redir_res.status_code, 307)
                self.assertEqual(redir_res.headers.get("location"), "https://example.com/screenshot.jpg")

                # 2. Telegram File ID guide
                create_tg = self.client.post(
                    "/api/admin/guides",
                    json={
                        "platform": "ios",
                        "app_name": "Streisand",
                        "media_type": "VIDEO",
                        "body": "Video tutorial",
                        "media_file_id": "BAACAgQAAxkBAAOwatS6V5gkd6jh34UdqgZ0Jc7i8UcAAGcfAAKEkKFsAbPye1xo8no9BA",
                    },
                    headers={"X-Telegram-Init-Data": init_data}
                )
                self.assertEqual(create_tg.status_code, 200)
                tg_id = create_tg.json()["item_id"]

                class MockFile:
                    file_path = "videos/guide_video.mp4"

                from xuishop import core
                with patch.object(core.bot, "get_file", return_value=MockFile()):
                    with patch.object(core.bot, "download_file", return_value=b"\x00\x00\x00\x18ftypmp42"):
                        media_res = self.client.get(f"/api/guides/{tg_id}/media")
                        self.assertEqual(media_res.status_code, 200)
                        self.assertEqual(media_res.headers.get("content-type"), "video/mp4")
                        self.assertEqual(media_res.content, b"\x00\x00\x00\x18ftypmp42")

                # 3. /api/guides public list includes media_url and app_name
                guides_res = self.client.get("/api/guides", headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(guides_res.status_code, 200)
                items = guides_res.json()["guides"]
                tg_guide = next(item for item in items if item["id"] == tg_id)
                self.assertEqual(tg_guide["media_url"], f"/api/guides/{tg_id}/media")
                self.assertEqual(tg_guide["app_name"], "Streisand")

                # 4. Prompt bot with explicit app_name
                with patch.object(core.bot, "send_message") as mock_send:
                    prompt_res = self.client.post("/api/admin/guides/prompt-bot?platform=android&app_name=V2RayNG", headers={"X-Telegram-Init-Data": init_data})
                    self.assertEqual(prompt_res.status_code, 200)
                    self.assertTrue(mock_send.called)
                    self.assertIn("V2RayNG", mock_send.call_args[0][1])

                # 5. Prompt bot without app_name (asks for app name first)
                with patch.object(core.bot, "send_message") as mock_send:
                    prompt_res2 = self.client.post("/api/admin/guides/prompt-bot?platform=android", headers={"X-Telegram-Init-Data": init_data})
                    self.assertEqual(prompt_res2.status_code, 200)
                    self.assertTrue(mock_send.called)
                    self.assertIn("نام نرم‌افزار", mock_send.call_args[0][1])

    def test_admin_broadcast(self):
        with patch("xuishop.api._get_bot_token", return_value=self.bot_token):
            with patch("xuishop.api._is_admin", return_value=True):
                init_data = self._generate_valid_init_data({"id": 111222, "first_name": "Admin"})
                with patch("xuishop.storage.audiences", return_value=[12345, 67890]):
                    with patch("xuishop.core.bot.send_message"):
                        res = self.client.post(
                            "/api/admin/broadcast",
                            json={"audience": "all", "message": "Test Announcement"},
                            headers={"X-Telegram-Init-Data": init_data},
                        )
                        self.assertEqual(res.status_code, 200)
                        data = res.json()
                        self.assertEqual(data.get("status"), "started")
                        self.assertEqual(data.get("total"), 2)

    def test_calc_discount_and_stars_checkout(self):
        from xuishop.api import _calc_discount
        import sqlite3
        conn = sqlite3.connect("app.db")
        conn.execute(
            "INSERT OR REPLACE INTO discount_codes (code, discount_type, value, min_purchase, max_uses, per_user_limit, expires_at, active, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("TEST50", "PERCENT", 50, 0, 100, 10, None, 1, 1000)
        )
        conn.commit()
        conn.close()

        disc = _calc_discount("TEST50", 100000, 888777)
        self.assertEqual(disc, 50000)

        with patch("xuishop.api._get_bot_token", return_value=self.bot_token):
            init_data = self._generate_valid_init_data({"id": 888777, "first_name": "Reza"})
            with patch("xuishop.core.bot.create_invoice_link", return_value="https://t.me/$invoice_test_link") as mock_invoice:
                payload = {
                    "custom_spec": {
                        "months": 1,
                        "volume_gb": 20,
                        "ip_limit": 1
                    },
                    "discount_code": "TEST50"
                }
                res = self.client.post("/api/orders/init-stars", json=payload, headers={"X-Telegram-Init-Data": init_data})
                self.assertEqual(res.status_code, 200)
                mock_invoice.assert_called_once()

    def test_core_logger_and_plan_alias(self):
        import logging
        from xuishop import core
        self.assertTrue(hasattr(core, "logger"))
        self.assertIsInstance(core.logger, logging.Logger)
        self.assertTrue(hasattr(core, "get_plan_by_id"))
        self.assertEqual(core.get_plan_by_id, core.get_plan)


if __name__ == "__main__":
    unittest.main()
