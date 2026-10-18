"""Payment Gateway Adapter — Zibal and Zarinpal.

Supports:
- Zibal (v1 REST API)
- Zarinpal (v4 REST JSON API)
Both adapters can operate in live or sandbox mode and are disabled by default.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple
import requests

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Zibal Gateway
# ---------------------------------------------------------------------------

class ZibalGateway:
    REQUEST_URL = "https://gateway.zibal.ir/v1/request"
    VERIFY_URL = "https://gateway.zibal.ir/v1/verify"
    START_URL = "https://gateway.zibal.ir/start/{track_id}"

    @classmethod
    def request_payment(
        cls,
        merchant: str,
        amount_tomans: int,
        callback_url: str,
        order_id: int,
        description: str = "خرید اشتراک VPN",
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Request payment token from Zibal.

        Returns: (payment_url, track_id, error_message)
        """
        if not merchant:
            return None, None, "مرچنت کد زیبال تنظیم نشده است."

        # Zibal expects amount in Rials (1 Toman = 10 Rials)
        payload = {
            "merchant": merchant,
            "amount": int(amount_tomans) * 10,
            "callbackUrl": callback_url,
            "description": description,
            "orderId": str(order_id),
        }

        try:
            res = requests.post(cls.REQUEST_URL, json=payload, timeout=12)
            data = res.json()
            if data.get("result") == 100:
                track_id = str(data["trackId"])
                payment_url = cls.START_URL.format(track_id=track_id)
                return payment_url, track_id, None
            return None, None, f"خطای زیبال: کد {data.get('result')} - {data.get('message')}"
        except Exception as exc:
            logger.error(f"Zibal request exception: {exc}")
            return None, None, f"خطا در اتصال به زیبال: {exc}"

    @classmethod
    def verify_payment(
        cls,
        merchant: str,
        track_id: str,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Verify payment with Zibal.

        Returns: (is_success, ref_number, error_message)
        """
        payload = {
            "merchant": merchant,
            "trackId": int(track_id),
        }
        try:
            res = requests.post(cls.VERIFY_URL, json=payload, timeout=12)
            data = res.json()
            # result 100 = success, 201 = already verified
            if data.get("result") in (100, 201):
                ref_num = str(data.get("refNumber") or track_id)
                return True, ref_num, None
            return False, None, f"تراکنش زیبال تایید نشد (کد {data.get('result')}: {data.get('message')})"
        except Exception as exc:
            logger.error(f"Zibal verify exception: {exc}")
            return False, None, f"خطا در تایید زیبال: {exc}"


# ---------------------------------------------------------------------------
# Zarinpal Gateway
# ---------------------------------------------------------------------------

class ZarinpalGateway:
    LIVE_BASE = "https://payment.zarinpal.com/pg"
    SANDBOX_BASE = "https://sandbox.zarinpal.com/pg"

    @classmethod
    def _base(cls, sandbox: bool = False) -> str:
        return cls.SANDBOX_BASE if sandbox else cls.LIVE_BASE

    @classmethod
    def request_payment(
        cls,
        merchant: str,
        amount_tomans: int,
        callback_url: str,
        order_id: int,
        description: str = "خرید اشتراک VPN",
        sandbox: bool = False,
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Request payment authority from Zarinpal.

        Returns: (payment_url, authority, error_message)
        """
        if not merchant:
            return None, None, "مرچنت کد زرین‌پال تنظیم نشده است."

        base = cls._base(sandbox)
        url = f"{base}/v4/payment/request.json"
        payload = {
            "merchant_id": merchant,
            "amount": int(amount_tomans),
            "callback_url": callback_url,
            "description": description,
            "metadata": {"order_id": str(order_id)},
        }

        try:
            res = requests.post(url, json=payload, timeout=12)
            data = res.json()
            code = data.get("data", {}).get("code")
            if code == 100:
                authority = data["data"]["authority"]
                payment_url = f"{base}/StartPay/{authority}"
                return payment_url, authority, None
            errors = data.get("errors", [])
            err_msg = str(errors) if errors else f"کد خطا: {code}"
            return None, None, f"خطای زرین‌پال: {err_msg}"
        except Exception as exc:
            logger.error(f"Zarinpal request exception: {exc}")
            return None, None, f"خطا در اتصال به زرین‌پال: {exc}"

    @classmethod
    def verify_payment(
        cls,
        merchant: str,
        amount_tomans: int,
        authority: str,
        sandbox: bool = False,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Verify payment with Zarinpal.

        Returns: (is_success, ref_id, error_message)
        """
        base = cls._base(sandbox)
        url = f"{base}/v4/payment/verify.json"
        payload = {
            "merchant_id": merchant,
            "amount": int(amount_tomans),
            "authority": authority,
        }

        try:
            res = requests.post(url, json=payload, timeout=12)
            data = res.json()
            code = data.get("data", {}).get("code")
            # 100 = success, 101 = verified before
            if code in (100, 101):
                ref_id = str(data.get("data", {}).get("ref_id") or authority)
                return True, ref_id, None
            errors = data.get("errors", [])
            err_msg = str(errors) if errors else f"کد خطا: {code}"
            return False, None, f"تراکنش زرین‌پال تایید نشد: {err_msg}"
        except Exception as exc:
            logger.error(f"Zarinpal verify exception: {exc}")
            return False, None, f"خطا در تایید زرین‌پال: {exc}"
