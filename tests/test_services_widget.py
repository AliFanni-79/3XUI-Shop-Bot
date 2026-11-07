import os
import unittest
from unittest.mock import MagicMock, patch

from xuishop import widget_services


class TestServicesWidget(unittest.TestCase):
    def setUp(self):
        self.mock_payload_empty = {
            "user_id": 123456,
            "brand_name": "TestShop",
            "balance": 50000,
            "trial_eligible": True,
            "services_count": 0,
            "services": [],
            "webapp_url": "https://test.shop",
            "updated_at": 1700000000,
        }

        self.mock_payload_single = {
            "user_id": 123456,
            "brand_name": "TestShop",
            "balance": 50000,
            "trial_eligible": False,
            "services_count": 1,
            "services": [
                {
                    "id": 101,
                    "tx_id": 101,
                    "title": "VIP 1 Month",
                    "email": "test_user_101",
                    "kind": "paid",
                    "is_active": True,
                    "is_expired": False,
                    "is_unlimited": False,
                    "used_gb": 12.5,
                    "total_gb": 50.0,
                    "remaining_gb": 37.5,
                    "usage_pct": 25,
                    "days_left": 20,
                    "time_left_str": "20 روز و 5 ساعت",
                    "ip_limit": 2,
                    "sub_url": "https://sub.test.shop/sub/xyz123",
                    "sub_format": "normal",
                    "qr_data_uri": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==",
                }
            ],
            "webapp_url": "https://test.shop",
            "updated_at": 1700000000,
        }

        self.mock_payload_multiple = {
            "user_id": 123456,
            "brand_name": "TestShop",
            "balance": 50000,
            "trial_eligible": False,
            "services_count": 3,
            "services": [
                {
                    "id": 101,
                    "tx_id": 101,
                    "title": "VIP 1 Month",
                    "email": "test_user_101",
                    "kind": "paid",
                    "is_active": True,
                    "is_expired": False,
                    "is_unlimited": False,
                    "used_gb": 12.5,
                    "total_gb": 50.0,
                    "remaining_gb": 37.5,
                    "usage_pct": 25,
                    "days_left": 20,
                    "time_left_str": "20 روز",
                    "ip_limit": 2,
                    "sub_url": "https://sub.test.shop/sub/xyz101",
                    "sub_format": "normal",
                    "qr_data_uri": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==",
                },
                {
                    "id": 102,
                    "tx_id": 102,
                    "title": "Pro 3 Months",
                    "email": "test_user_102",
                    "kind": "paid",
                    "is_active": True,
                    "is_expired": False,
                    "is_unlimited": False,
                    "used_gb": 45.0,
                    "total_gb": 100.0,
                    "remaining_gb": 55.0,
                    "usage_pct": 45,
                    "days_left": 75,
                    "time_left_str": "75 روز",
                    "ip_limit": 3,
                    "sub_url": "https://sub.test.shop/sub/xyz102",
                    "sub_format": "normal",
                    "qr_data_uri": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==",
                },
                {
                    "id": "trial_user",
                    "tx_id": None,
                    "title": "🎁 تست رایگان",
                    "email": "trial_user",
                    "kind": "trial",
                    "is_active": True,
                    "is_expired": False,
                    "is_unlimited": False,
                    "used_gb": 0.2,
                    "total_gb": 1.0,
                    "remaining_gb": 0.8,
                    "usage_pct": 20,
                    "days_left": 1,
                    "time_left_str": "1 روز",
                    "ip_limit": 1,
                    "sub_url": "https://sub.test.shop/sub/trial",
                    "sub_format": "normal",
                    "qr_data_uri": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==",
                },
            ],
            "webapp_url": "https://test.shop",
            "updated_at": 1700000000,
        }

    def test_widget_html_size_under_telegram_limit(self):
        """Telegram HTMLBubbles must remain strictly under 32 KB uncompressed."""
        html_empty = widget_services.render_services_widget_html(self.mock_payload_empty)
        html_single = widget_services.render_services_widget_html(self.mock_payload_single)
        html_multi = widget_services.render_services_widget_html(self.mock_payload_multiple)

        self.assertLess(len(html_empty.encode("utf-8")), 32 * 1024)
        self.assertLess(len(html_single.encode("utf-8")), 32 * 1024)
        self.assertLess(len(html_multi.encode("utf-8")), 32 * 1024)

    def test_qr_generation(self):
        """Ensure QR code data URI generation works correctly."""
        uri = widget_services.generate_qr_data_uri("vless://test-uuid@domain.com:443")
        self.assertTrue(uri.startswith("data:image/png;base64,"))
        self.assertGreater(len(uri), 50)

    def test_empty_state_rendering(self):
        """Ensure empty state contains trial button if eligible."""
        html = widget_services.render_services_widget_html(self.mock_payload_empty)
        self.assertIn("دریافت تست رایگان", html)
        self.assertIn("مشاهده و خرید پلان‌ها", html)
        self.assertIn("در حال حاضر هیچ سرویس فعالی ندارید", html)

    def test_single_service_jump_to_detail(self):
        """Single service skips list and defaults directly to detail view."""
        html = widget_services.render_services_widget_html(self.mock_payload_single)
        self.assertIn("currentView = DATA.services.length === 1 ? 'detail'", html)
        self.assertIn("بروزرسانی زنده", html)
        self.assertIn("کپی لینک سابسکریپشن", html)
        self.assertIn("نمایش QR Code", html)

    def test_multiple_services_list_and_pagination(self):
        """Multiple services render list view with pagination support."""
        html = widget_services.render_services_widget_html(self.mock_payload_multiple)
        self.assertIn("nextPage()", html)
        self.assertIn("prevPage()", html)
        self.assertIn("PAGE_SIZE = 2", html)

    def test_cooldown_timer_in_html(self):
        """Check 5-second cooldown refresh script in widget."""
        html = widget_services.render_services_widget_html(self.mock_payload_single)
        self.assertIn("let left = 5;", html)
        self.assertIn("isCooldown = true;", html)
        self.assertIn("triggerRefresh()", html)


if __name__ == "__main__":
    unittest.main()
