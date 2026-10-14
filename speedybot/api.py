"""FastAPI application — SpeedyBot Mini App REST layer.

Endpoints:
  GET  /api/auth/me                  → validate initData, return profile + is_admin
  GET  /api/plans                    → active plans grouped by category
  GET  /api/services                 → user's VPN services (paid + trial + linked)
  GET  /api/wallet                   → balance + transaction history
  GET  /api/referral                 → referral code + commission stats
  GET  /api/guides                   → connection guides
  POST /api/orders/init-card         → create order, trigger bot message for receipt
  POST /api/orders/init-wallet       → instant wallet purchase
  GET  /api/admin/stats              → (admin) summary stats
  GET  /api/admin/orders             → (admin) pending orders
  POST /api/admin/orders/{id}/approve → (admin) approve order
  POST /api/admin/orders/{id}/reject  → (admin) reject order
  GET  /api/admin/users              → (admin) user list
  GET  /api/admin/plans              → (admin) all plans including inactive
  POST /api/admin/broadcast          → (admin) send broadcast message

Static files at /  → served from webapp/dist (built Vue SPA)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qsl, unquote

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------

app = FastAPI(title="SpeedyBot Mini App API", version="1.0.0", docs_url="/api/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production by listing your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Telegram initData HMAC verification
# ---------------------------------------------------------------------------

_VERIFIED_CACHE: Dict[str, Dict[str, Any]] = {}  # simple in-process cache


def _get_bot_token() -> str:
    """Resolve bot token at call-time so it works even after late import."""
    # Try context module first (set after bot starts), fall back to env.
    try:
        from . import context as C  # noqa: PLC0415
        if C.CORE is not None:
            return C.CORE.BOT_TOKEN  # type: ignore[attr-defined]
    except Exception:
        pass
    token = os.getenv("BOT_TOKEN", "")
    if not token:
        raise RuntimeError("BOT_TOKEN not set")
    return token


def _verify_init_data(init_data_raw: str) -> Dict[str, Any]:
    """Parse and HMAC-verify Telegram WebApp initData string.

    Returns the parsed user dict (with 'id' as int) on success.
    Raises HTTPException 401 on any failure.
    """
    if not init_data_raw:
        raise HTTPException(status_code=401, detail="Missing initData")

    # Cache hit
    cached = _VERIFIED_CACHE.get(init_data_raw)
    if cached and cached.get("_expires_at", 0) > time.time():
        return cached

    try:
        params = dict(parse_qsl(init_data_raw, keep_blank_values=True))
    except Exception:
        raise HTTPException(status_code=401, detail="Malformed initData")

    received_hash = params.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=401, detail="Missing hash in initData")

    # Build data-check-string: sorted key=value pairs (excluding hash)
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))

    try:
        bot_token = _get_bot_token()
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        expected = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Token resolution error: {exc}")

    if not hmac.compare_digest(expected, received_hash):
        raise HTTPException(status_code=401, detail="Invalid initData signature")

    # Parse the user JSON field
    raw_user = params.get("user", "{}")
    try:
        user_data = json.loads(unquote(raw_user))
    except Exception:
        raise HTTPException(status_code=401, detail="Malformed user field in initData")

    if "id" not in user_data:
        raise HTTPException(status_code=401, detail="Missing user.id in initData")

    result: Dict[str, Any] = {
        "id": int(user_data["id"]),
        "first_name": user_data.get("first_name", ""),
        "last_name": user_data.get("last_name", ""),
        "username": user_data.get("username", ""),
        "language_code": user_data.get("language_code", ""),
        "_expires_at": time.time() + 300,  # cache for 5 minutes
    }
    _VERIFIED_CACHE[init_data_raw] = result
    return result


from .db import get_connection, get_db_path
_DB_PATH = get_db_path()
_SCHEMA_INITIALIZED = False


def _ensure_schema():
    global _SCHEMA_INITIALIZED
    if _SCHEMA_INITIALIZED:
        return
    try:
        from . import core as _core, storage as _storage  # noqa: PLC0415
        _core.init_db()
        _storage.init_db()
        _SCHEMA_INITIALIZED = True
    except Exception:
        pass


def _db():
    if not _SCHEMA_INITIALIZED:
        _ensure_schema()
    return get_connection(timeout=30)


def _get_plan(plan_id: int) -> Optional[Dict[str, Any]]:
    conn = _db()
    try:
        plan_row = conn.execute(
            "SELECT * FROM plans WHERE id = ? AND active = 1", (plan_id,)
        ).fetchone()
        if not plan_row:
            return None
        return {
            "id": plan_row["id"],
            "name": plan_row["name"],
            "price": int(plan_row["price"]),
            "days": int(plan_row["days"]),
            "volume_gb": float(plan_row["volume_gb"] or 0),
            "ip_limit": int(plan_row["ip_limit"] or 0),
            "volume": float(plan_row["volume_gb"] or 0),
            "sort_order": int(plan_row["sort_order"] or 100),
            "group_name": plan_row["group_name"] if "group_name" in plan_row.keys() and plan_row["group_name"] else "",
            "active": True,
        }
    finally:
        conn.close()


def _setting(key: str, default: str = "") -> str:
    conn = _db()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return str(row[0]) if row else default


def _brand_name() -> str:
    try:
        from .db import get_brand_name  # noqa: PLC0415
        return get_brand_name(default="Shop")
    except Exception:
        return _setting("webapp_title", "").strip() or _setting("brand_name", "").strip() or "Shop"


def _update_setting(key: str, value: Any):
    conn = _db()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()


def _is_admin(uid: int) -> bool:
    try:
        from . import context as C  # noqa: PLC0415
        return C.is_admin(int(uid))
    except Exception:
        pass
    # Fallback: direct DB check
    try:
        admin_id = int(os.getenv("ADMIN_ID", "0"))
        if uid == admin_id:
            return True
        conn = _db()
        row = conn.execute("SELECT 1 FROM admins WHERE user_id = ?", (int(uid),)).fetchone()
        conn.close()
        return bool(row)
    except Exception:
        return False


def _ensure_user(uid: int):
    """Insert user row if not present (first Mini App visit before any bot message)."""
    conn = _db()
    now_ts = int(time.time())
    conn.execute(
        "INSERT OR IGNORE INTO users (id, balance, created_at, last_seen_at, is_active) VALUES (?, 0, ?, ?, 1)",
        (uid, now_ts, now_ts),
    )
    conn.execute("UPDATE users SET last_seen_at = ? WHERE id = ?", (now_ts, uid))
    conn.commit()
    conn.close()


def _get_init_data_header(request: Request) -> str:
    """Extract X-Telegram-Init-Data header."""
    hdr = request.headers.get("X-Telegram-Init-Data", "")
    if not hdr:
        # Also accept query param for easy browser testing
        hdr = request.query_params.get("initData", "")
    return hdr


async def get_current_user(request: Request) -> Dict[str, Any]:
    """FastAPI dependency: verify initData, return user dict with is_admin."""
    raw = _get_init_data_header(request)
    user = _verify_init_data(raw)
    _ensure_user(user["id"])
    user["is_admin"] = _is_admin(user["id"])
    return user


async def get_admin_user(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """FastAPI dependency: same as get_current_user but requires admin."""
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Forbidden")
    return user


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class InitCardOrderRequest(BaseModel):
    plan_id: int
    discount_code: Optional[str] = None
    custom_name: Optional[str] = None


class InitWalletOrderRequest(BaseModel):
    plan_id: int
    discount_code: Optional[str] = None
    custom_name: Optional[str] = None


class BroadcastRequest(BaseModel):
    message: str
    audience: str = "all"  # all | customers | trial | expired_trial | never_bought


class RejectOrderRequest(BaseModel):
    reason: Optional[str] = None


class BuilderCalculateRequest(BaseModel):
    months: int
    volume_gb: int
    ip_limit: int
    discount_code: Optional[str] = None


class InitCustomCardOrderRequest(BaseModel):
    months: int
    volume_gb: int
    ip_limit: int
    discount_code: Optional[str] = None
    custom_name: Optional[str] = None


class InitCustomWalletOrderRequest(BaseModel):
    months: int
    volume_gb: int
    ip_limit: int
    discount_code: Optional[str] = None
    custom_name: Optional[str] = None


class InitGatewayOrderRequest(BaseModel):
    gateway: str  # 'zibal' | 'zarinpal'
    plan_id: Optional[int] = None
    months: Optional[int] = None
    volume_gb: Optional[int] = None
    ip_limit: Optional[int] = None
    discount_code: Optional[str] = None
    custom_name: Optional[str] = None


class AdminGatewaySettingsRequest(BaseModel):
    zibal_enabled: bool
    zibal_merchant: str
    zibal_sandbox: bool
    zarinpal_enabled: bool
    zarinpal_merchant: str
    zarinpal_sandbox: bool


class BrandingRequest(BaseModel):
    webapp_title: str


class InitStarsOrderRequest(BaseModel):
    plan_id: Optional[int] = None
    custom_spec: Optional[dict] = None
    discount_code: Optional[str] = None
    custom_name: Optional[str] = None


class TrialClaimRequest(BaseModel):
    custom_name: Optional[str] = None


class AdminPlanCreateRequest(BaseModel):
    name: str
    price: int
    volume_gb: float = 0
    days: int = 30
    ip_limit: int = 1
    active: int = 1
    sort_order: int = 100
    group_name: Optional[str] = None


class AdminPlanUpdateRequest(BaseModel):
    name: Optional[str] = None
    price: Optional[int] = None
    volume_gb: Optional[float] = None
    days: Optional[int] = None
    ip_limit: Optional[int] = None
    active: Optional[int] = None
    sort_order: Optional[int] = None
    group_name: Optional[str] = None


class ReplaceDomainRequest(BaseModel):
    old_domain: str
    new_domain: str


class DeleteClientRequest(BaseModel):
    email: str


class CreateDiscountRequest(BaseModel):
    code: str
    discount_type: str = "PERCENT"  # "PERCENT" or "FIXED"
    value: float
    min_purchase: int = 0
    max_uses: int = 0
    per_user_limit: int = 1
    expires_at: Optional[int] = None


class CreateGiftRequest(BaseModel):
    code: str
    amount: int
    max_uses: int = 1
    expires_at: Optional[int] = None


class CashbackUpdateRequest(BaseModel):
    percent: float


class AffiliateSettingsRequest(BaseModel):
    enabled: Optional[bool] = None
    percent: Optional[float] = None


class ContentSecurityRequest(BaseModel):
    welcome_text: Optional[str] = None
    faq_text: Optional[str] = None
    phone_verification_required: Optional[bool] = None
    membership_required: Optional[bool] = None
    required_channel: Optional[str] = None
    required_channel_url: Optional[str] = None
    service_notifications_enabled: Optional[bool] = None
    service_volume_warning_percent: Optional[int] = None
    service_expiry_warning_hours: Optional[int] = None


class AdminBuilderDefaultsRequest(BaseModel):
    month_price: Optional[int] = None
    gb_price: Optional[int] = None
    discount_3m: Optional[int] = None
    discount_6m: Optional[int] = None
    discount_12m: Optional[int] = None
    traffic_discount_50: Optional[int] = None
    traffic_discount_100: Optional[int] = None
    traffic_discount_300: Optional[int] = None
    traffic_unlimited_price: Optional[int] = None
    traffic_unlimited_cap_gb: Optional[int] = None
    user_cost_1: Optional[int] = None
    user_cost_2: Optional[int] = None
    user_cost_3: Optional[int] = None
    user_cost_4: Optional[int] = None
    user_cost_5: Optional[int] = None
    user_cost_unlimited: Optional[int] = None


class AdminAdjustBalanceRequest(BaseModel):
    amount: int
    reason: Optional[str] = "Admin manual adjustment"


class AdminBlacklistAddRequest(BaseModel):
    user_id: int
    reason: Optional[str] = "Blocked by admin"


class AdminAddRequest(BaseModel):
    user_id: int
    role: Optional[str] = "ADMIN"


class AdminOperatingModeRequest(BaseModel):
    mode: str  # NORMAL, SALES_PAUSED, MAINTENANCE


class AdminPaymentsSettingsRequest(BaseModel):
    card_number: Optional[str] = None
    card_holder: Optional[str] = None
    bank_name: Optional[str] = None
    zibal_enabled: Optional[bool] = None
    zibal_merchant: Optional[str] = None
    zibal_sandbox: Optional[bool] = None
    zarinpal_enabled: Optional[bool] = None
    zarinpal_merchant: Optional[str] = None
    zarinpal_sandbox: Optional[bool] = None
    stars_enabled: Optional[bool] = None
    stars_rate: Optional[int] = None


# ---------------------------------------------------------------------------
# App Config & Auth endpoints
# ---------------------------------------------------------------------------

@app.get("/api/app/config")
async def get_app_config():
    """Public webapp configuration (title, branding)."""
    app_title = _brand_name()
    return {
        "webapp_title": app_title,
    }


@app.get("/api/auth/me")
async def auth_me(user: Dict[str, Any] = Depends(get_current_user)):
    """Return authenticated user profile."""
    uid = user["id"]
    conn = _db()
    row = conn.execute(
        "SELECT balance, referred_by, created_at FROM users WHERE id = ?", (uid,)
    ).fetchone()
    conn.close()
    app_title = _brand_name()
    return {
        "id": uid,
        "first_name": user.get("first_name", ""),
        "last_name": user.get("last_name", ""),
        "username": user.get("username", ""),
        "balance": int(row["balance"] or 0) if row else 0,
        "is_admin": user.get("is_admin", False),
        "app_title": app_title,
        "webapp_title": app_title,
    }


# ---------------------------------------------------------------------------
# Plans
# ---------------------------------------------------------------------------

@app.get("/api/plans")
async def get_plans(user: Dict[str, Any] = Depends(get_current_user)):
    """Return active plans grouped by category and trial info."""
    conn = _db()
    cats = conn.execute(
        "SELECT id, name FROM plan_categories WHERE active = 1 ORDER BY sort_order, id"
    ).fetchall()
    plans = conn.execute(
        """SELECT p.id, p.name, p.price, p.volume_gb, p.days, p.ip_limit, p.sort_order,
                  p.category_id, COALESCE(pc.name, 'عمومی') AS category_name
           FROM plans p
           LEFT JOIN plan_categories pc ON pc.id = p.category_id
           WHERE p.active = 1
           ORDER BY p.sort_order, p.id"""
    ).fetchall()
    conn.close()

    grouped: Dict[int, Dict] = {}
    for cat in cats:
        grouped[cat["id"]] = {"id": cat["id"], "name": cat["name"], "plans": []}

    for p in plans:
        cid = p["category_id"] or 0
        if cid not in grouped:
            grouped[cid] = {"id": cid, "name": p["category_name"] or "عمومی", "plans": []}
        grouped[cid]["plans"].append({
            "id": p["id"],
            "name": p["name"],
            "price": p["price"],
            "volume_gb": float(p["volume_gb"] or 0),
            "days": p["days"],
            "ip_limit": p["ip_limit"],
        })

    from . import core as _core, trial as _trial  # noqa: PLC0415
    uid = user["id"]
    eligible, rem_days, last_ts, trial_status = _trial.get_trial_eligibility(uid)
    gb, days, ip, _ = _trial.values(uid)

    trial_info = {
        "enabled": _core.trial_enabled(),
        "eligible": eligible,
        "remaining_days": rem_days,
        "status": trial_status,
        "last_activated_at": last_ts,
        "name": "تست رایگان ۱ روزه",
        "volume_gb": gb,
        "volume_display": "300 مگابایت" if abs(gb - 0.3) < 0.05 else f"{gb:g} GB",
        "days": days,
        "ip_limit": ip,
        "price": 0,
        "is_free": True,
    }

    return {
        "categories": [v for v in grouped.values() if v["plans"]],
        "trial_info": trial_info,
    }


@app.get("/api/trial/status")
async def get_trial_status(user: Dict[str, Any] = Depends(get_current_user)):
    """Return whether user is eligible for monthly free trial and trial plan specs."""
    from . import core as _core, trial as _trial  # noqa: PLC0415
    uid = user["id"]
    eligible, rem_days, last_ts, trial_status = _trial.get_trial_eligibility(uid)
    gb, days, ip, _ = _trial.values(uid)
    return {
        "enabled": _core.trial_enabled(),
        "eligible": eligible,
        "remaining_days": rem_days,
        "status": trial_status,
        "last_activated_at": last_ts,
        "name": "تست رایگان ۱ روزه",
        "volume_gb": gb,
        "volume_display": "300 مگابایت" if abs(gb - 0.3) < 0.05 else f"{gb:g} GB",
        "days": days,
        "ip_limit": ip,
        "price": 0,
        "is_free": True,
    }


@app.post("/api/trial/claim")
async def claim_trial(
    body: TrialClaimRequest = TrialClaimRequest(),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Claim monthly free trial (1 day, 300MB, unlimited users)."""
    uid = user["id"]
    from . import trial as _trial
    res = _trial.issue_trial_for_user(uid, custom_name=body.custom_name)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "خطا در صدور تست رایگان"))
    return res


# ---------------------------------------------------------------------------
# Custom Plan Builder
# ---------------------------------------------------------------------------

def _get_builder_config() -> Dict[str, Any]:
    return {
        "enabled": _setting("builder_enabled", "1") == "1",
        "month_price": int(_setting("builder_month_price", "120000")),
        "dur_discounts": {
            1: 0,
            3: int(_setting("builder_dur_discount_3m", "5")),
            6: int(_setting("builder_dur_discount_6m", "10")),
            12: int(_setting("builder_dur_discount_12m", "20")),
        },
        "gb_price": int(_setting("builder_gb_price", "1000")),
        "traffic_discounts": [
            {"min_gb": 300, "percent": int(_setting("builder_traffic_discount_300", "30"))},
            {"min_gb": 100, "percent": int(_setting("builder_traffic_discount_100", "15"))},
            {"min_gb": 50, "percent": int(_setting("builder_traffic_discount_50", "5"))},
        ],
        "traffic_unlimited_price": int(_setting("builder_traffic_unlimited_price", "500000")),
        "traffic_unlimited_cap_gb": int(_setting("builder_traffic_unlimited_cap_gb", "1000")),
        "user_costs": {
            1: int(_setting("builder_user_cost_1", "0")),
            2: int(_setting("builder_user_cost_2", "20000")),
            3: int(_setting("builder_user_cost_3", "35000")),
            4: int(_setting("builder_user_cost_4", "45000")),
            5: int(_setting("builder_user_cost_5", "50000")),
            0: int(_setting("builder_user_cost_unlimited", "65000")),
        },
        "user_unlimited_safety_ip": int(_setting("builder_user_unlimited_safety_ip", "8")),
    }


def _calculate_builder_plan(
    months: int,
    volume_gb: int,
    ip_limit: int,
    discount_code: Optional[str] = None,
    user_id: Optional[int] = None
) -> Dict[str, Any]:
    cfg = _get_builder_config()

    if months not in (1, 3, 6, 12):
        raise HTTPException(status_code=400, detail="مدت زمان پلن باید یکی از مقادیر ۱، ۳، ۶ یا ۱۲ ماه باشد.")
    if volume_gb < 0 or volume_gb > 500:
        raise HTTPException(status_code=400, detail="حجم انتخابی باید بین ۱ تا ۵۰۰ گیگابایت یا ۰ (نامحدود) باشد.")
    if ip_limit not in (0, 1, 2, 3, 4, 5):
        raise HTTPException(status_code=400, detail="تعداد کاربر باید بین ۱ تا ۵ یا ۰ (نامحدود) باشد.")

    # Fair use rule: unlimited traffic + unlimited users is strictly forbidden!
    if volume_gb == 0 and ip_limit == 0:
        raise HTTPException(
            status_code=400,
            detail="در صورت انتخاب حجم نامحدود، امکان انتخاب کاربر نامحدود به دلیل رعایت مصرف منصفانه (Fair Use) وجود ندارد."
        )

    # 1. Duration calculation
    month_price = cfg["month_price"]
    duration_base = months * month_price
    dur_disc_pct = cfg["dur_discounts"].get(months, 0)
    dur_disc_amount = int(round(duration_base * dur_disc_pct / 100.0))
    duration_price = max(0, duration_base - dur_disc_amount)

    # 2. Traffic calculation
    if volume_gb == 0:
        traffic_base = cfg["traffic_unlimited_price"]
        traffic_disc_pct = 0
        traffic_disc_amount = 0
        traffic_price = traffic_base
        effective_gb = cfg["traffic_unlimited_cap_gb"]
        traffic_label = "نامحدود"
    else:
        traffic_base = volume_gb * cfg["gb_price"]
        traffic_disc_pct = 0
        for td in cfg["traffic_discounts"]:
            if volume_gb > td["min_gb"]:
                traffic_disc_pct = td["percent"]
                break
        traffic_disc_amount = int(round(traffic_base * traffic_disc_pct / 100.0))
        traffic_price = max(0, traffic_base - traffic_disc_amount)
        effective_gb = volume_gb
        traffic_label = f"{volume_gb} گیگ"

    # 3. User limit calculation
    user_cost = cfg["user_costs"].get(ip_limit, 0)
    user_label = "نامحدود" if ip_limit == 0 else f"{ip_limit} کاربر"
    effective_ip = cfg["user_unlimited_safety_ip"] if ip_limit == 0 else ip_limit

    subtotal = duration_price + traffic_price + user_cost

    # 4. Optional discount code check
    code_discount = 0
    valid_code = None
    if discount_code and user_id:
        conn = _db()
        from . import core as _core
        valid_code, code_discount, _ = _core._calculate_pending_discount(conn, user_id, subtotal)
        conn.close()

    final_price = max(0, subtotal - code_discount)
    plan_name = f"پلن اختصاصی | {months} ماهه - {traffic_label} - {user_label}"

    return {
        "months": months,
        "days": months * 30,
        "volume_gb": volume_gb,
        "effective_volume_gb": effective_gb,
        "ip_limit": ip_limit,
        "effective_ip_limit": effective_ip,
        "plan_name": plan_name,
        "duration": {
            "months": months,
            "base_price": duration_base,
            "discount_percent": dur_disc_pct,
            "discount_amount": dur_disc_amount,
            "final_price": duration_price,
        },
        "traffic": {
            "volume_gb": volume_gb,
            "is_unlimited": volume_gb == 0,
            "base_price": traffic_base,
            "discount_percent": traffic_disc_pct,
            "discount_amount": traffic_disc_amount,
            "final_price": traffic_price,
        },
        "user_limit": {
            "ip_limit": ip_limit,
            "is_unlimited": ip_limit == 0,
            "cost": user_cost,
        },
        "subtotal": subtotal,
        "discount_code": valid_code,
        "discount_code_amount": code_discount,
        "total_price": final_price,
    }


@app.get("/api/builder/config")
async def get_builder_config(_user: Dict[str, Any] = Depends(get_current_user)):
    """Return pricing settings and presets for custom plan builder."""
    return _get_builder_config()


@app.post("/api/builder/calculate")
async def calculate_builder_price(
    body: BuilderCalculateRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Calculate and return price breakdown for custom plan configuration."""
    return _calculate_builder_plan(
        months=body.months,
        volume_gb=body.volume_gb,
        ip_limit=body.ip_limit,
        discount_code=body.discount_code,
        user_id=user["id"]
    )


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------

def _format_service(row) -> Dict[str, Any]:
    from . import core as _core
    email = row["email"] if "email" in row.keys() else row.get("service_email", "")
    sub_id = row.get("sub_id")
    sub_url = _core.get_client_sub_url(email, sub_id)
    return {
        "email": email,
        "custom_name": row.get("custom_name") or email,
        "sub_url": sub_url,
        "kind": row.get("kind", "PAID"),
        "status": row.get("status", ""),
        "plan_name": row.get("plan_name_snapshot") or row.get("name") or "",
        "days": int(row.get("plan_days_snapshot") or row.get("days") or 0),
        "volume_gb": float(row.get("plan_volume_gb_snapshot") or row.get("volume_gb") or 0),
        "ip_limit": int(row.get("plan_ip_limit_snapshot") or row.get("ip_limit") or 0),
        "approved_at": row.get("approved_at"),
        "tx_id": row.get("id"),
    }


@app.get("/api/services")
async def get_services(user: Dict[str, Any] = Depends(get_current_user)):
    """Return all user's VPN services: paid, trial, and linked."""
    from . import core as _core
    uid = user["id"]
    conn = _db()

    paid = conn.execute(
        """SELECT id, service_email AS email, sub_id, custom_name, kind, status, plan_name_snapshot,
                  plan_days_snapshot, plan_volume_gb_snapshot, plan_ip_limit_snapshot, approved_at
           FROM transactions
           WHERE user_id = ? AND status = 'APPROVED' AND kind = 'NEW'
           ORDER BY id DESC""",
        (uid,),
    ).fetchall()

    trial = conn.execute(
        "SELECT user_id, email, sub_id, status, created_at, activated_at FROM trial_services WHERE user_id = ?",
        (uid,),
    ).fetchone()

    linked = conn.execute(
        "SELECT id, email, linked_at, source FROM linked_services WHERE user_id = ? ORDER BY id DESC",
        (uid,),
    ).fetchall()

    conn.close()

    services = []
    for row in paid:
        svc = _format_service(dict(row))
        svc["kind"] = "PAID"
        services.append(svc)

    if trial:
        status_val = trial["status"]
        if status_val in ("ACTIVE", "CREATING", "EXPIRED"):
            svc = {
                "email": trial["email"],
                "sub_url": _core.get_client_sub_url(trial["email"], trial["sub_id"]),
                "kind": "TRIAL",
                "status": status_val,
                "plan_name": "تست رایگان",
                "days": int(_setting("trial_default_days", "1")),
                "volume_gb": float(_setting("trial_default_volume_gb", "1")),
                "ip_limit": int(_setting("trial_default_ip_limit", "1")),
                "approved_at": trial.get("activated_at"),
                "tx_id": None,
            }
            services.append(svc)

    for row in linked:
        services.append({
            "email": row["email"],
            "sub_url": _core.get_client_sub_url(row["email"], None),
            "kind": "LINKED",
            "status": "ACTIVE",
            "plan_name": "سرویس لینک‌شده",
            "days": 0,
            "volume_gb": 0,
            "ip_limit": 0,
            "approved_at": row.get("linked_at"),
            "tx_id": row["id"],
        })

    return {"services": services}


# ---------------------------------------------------------------------------
# Wallet
# ---------------------------------------------------------------------------

@app.get("/api/wallet")
async def get_wallet(user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    conn = _db()
    u_row = conn.execute("SELECT balance FROM users WHERE id = ?", (uid,)).fetchone()
    balance = int(u_row["balance"] or 0) if u_row else 0

    txns = conn.execute(
        """SELECT id, amount, balance_after, type, description, created_at
           FROM wallet_transactions WHERE user_id = ?
           ORDER BY id DESC LIMIT 50""",
        (uid,),
    ).fetchall()
    conn.close()

    return {
        "balance": balance,
        "transactions": [
            {
                "id": r["id"],
                "amount": r["amount"],
                "balance_after": r["balance_after"],
                "type": r["type"],
                "description": r["description"] or "",
                "created_at": r["created_at"],
            }
            for r in txns
        ],
    }


# ---------------------------------------------------------------------------
# Referral
# ---------------------------------------------------------------------------

@app.get("/api/referral")
async def get_referral(user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    conn = _db()

    ref_row = conn.execute(
        "SELECT code, created_at FROM referral_codes WHERE user_id = ?", (uid,)
    ).fetchone()

    # Auto-generate a referral code if missing
    if not ref_row:
        import secrets as _secrets
        code = _secrets.token_urlsafe(8).upper()
        now_ts = int(time.time())
        try:
            conn.execute(
                "INSERT OR IGNORE INTO referral_codes (user_id, code, created_at) VALUES (?, ?, ?)",
                (uid, code, now_ts),
            )
            conn.commit()
            ref_row = conn.execute(
                "SELECT code, created_at FROM referral_codes WHERE user_id = ?", (uid,)
            ).fetchone()
        except Exception:
            pass

    commissions = conn.execute(
        """SELECT SUM(commission_amount) AS total_earned,
                  COUNT(*) AS total_referrals
           FROM referral_commissions WHERE referrer_id = ?""",
        (uid,),
    ).fetchone()

    referred_count = conn.execute(
        "SELECT COUNT(*) AS c FROM users WHERE referred_by = ?", (uid,)
    ).fetchone()

    conn.close()

    # Build deep link
    try:
        from . import core as _core  # noqa: PLC0415
        bot_username = _core.bot.get_me().username if _core.bot else None
    except Exception:
        bot_username = None

    ref_link = f"https://t.me/{bot_username}?start=ref_{ref_row['code']}" if (ref_row and bot_username) else None

    return {
        "referral_enabled": _setting("referral_enabled", "1") == "1",
        "code": ref_row["code"] if ref_row else None,
        "link": ref_link,
        "total_earned": int(commissions["total_earned"] or 0) if commissions else 0,
        "total_referrals": int(referred_count["c"] or 0) if referred_count else 0,
        "commission_percent": float(_setting("referral_commission_percent", "10") or 10),
    }


# ---------------------------------------------------------------------------
# Guides
# ---------------------------------------------------------------------------

@app.get("/api/guides")
async def get_guides(_user: Dict[str, Any] = Depends(get_current_user)):
    conn = _db()
    rows = conn.execute(
        "SELECT id, platform, media_type, body, file_id, sort_order FROM guide_items WHERE active = 1 ORDER BY sort_order, id"
    ).fetchall()
    conn.close()
    return {
        "guides": [
            {
                "id": r["id"],
                "platform": r["platform"],
                "media_type": r["media_type"],
                "body": r["body"] or "",
                "file_id": r["file_id"],
            }
            for r in rows
        ]
    }


# ---------------------------------------------------------------------------
# Orders — card-to-card checkout handoff
# ---------------------------------------------------------------------------

@app.post("/api/orders/init-card")
async def init_card_order(
    body: InitCardOrderRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Create a card-to-card order and trigger the bot to send payment instructions
    directly to the user's Telegram chat, where they upload the receipt photo."""
    uid = user["id"]

    # Resolve plan
    plan = _get_plan(body.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found or inactive")

    # Optionally pre-load a discount code
    if body.discount_code:
        from . import core as _core  # noqa: PLC0415
        _core.set_pending_discount(uid, body.discount_code)

    # Use existing core function to create the transaction and trigger the bot message
    try:
        from . import core as _core  # noqa: PLC0415
        _core._start_card_checkout(uid, uid, plan, custom_name=body.custom_name)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to initiate checkout: {exc}")

    return {"status": "awaiting_receipt", "message": "پیام پرداخت در تلگرام ارسال شد"}


# ---------------------------------------------------------------------------
# Orders — wallet checkout
# ---------------------------------------------------------------------------

@app.post("/api/orders/init-wallet")
async def init_wallet_order(
    body: InitWalletOrderRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Deduct wallet balance and immediately provision the service."""
    uid = user["id"]

    plan = _get_plan(body.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found or inactive")

    if body.discount_code:
        from . import core as _core  # noqa: PLC0415
        _core.set_pending_discount(uid, body.discount_code)

    from . import core as _core  # noqa: PLC0415
    result, error = _core._create_checkout_transaction(uid, plan, "WALLET", custom_name=body.custom_name)
    if not result:
        raise HTTPException(status_code=400, detail=error or "موجودی ناکافی")

    tx_id = result["tx_id"]
    _core.finalize_service_transaction(tx_id)

    return {
        "status": "processing",
        "tx_id": tx_id,
        "price": result.get("price", plan.get("price", 0)),
        "message": "خرید از کیف پول ثبت شد",
    }


@app.post("/api/orders/init-custom-card")
async def init_custom_card_order(
    body: InitCustomCardOrderRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Initiate a card-to-card order for a custom builder plan."""
    uid = user["id"]
    calc = _calculate_builder_plan(
        months=body.months,
        volume_gb=body.volume_gb,
        ip_limit=body.ip_limit,
        discount_code=body.discount_code,
        user_id=uid
    )

    custom_plan = {
        "id": 0,
        "name": calc["plan_name"],
        "price": calc["total_price"],
        "days": calc["days"],
        "volume_gb": calc["effective_volume_gb"],
        "volume": calc["effective_volume_gb"],
        "ip_limit": calc["effective_ip_limit"],
        "sort_order": 0,
        "active": True,
    }

    if body.discount_code:
        from . import core as _core  # noqa: PLC0415
        _core.set_pending_discount(uid, body.discount_code)

    try:
        from . import core as _core  # noqa: PLC0415
        _core._start_card_checkout(uid, uid, custom_plan, custom_name=body.custom_name)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to initiate checkout: {exc}")

    return {
        "status": "awaiting_receipt",
        "plan_name": calc["plan_name"],
        "price": calc["total_price"],
        "message": "پیام پرداخت در تلگرام ارسال شد"
    }


@app.post("/api/orders/init-custom-wallet")
async def init_custom_wallet_order(
    body: InitCustomWalletOrderRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Deduct wallet balance and provision a custom builder plan immediately."""
    uid = user["id"]
    calc = _calculate_builder_plan(
        months=body.months,
        volume_gb=body.volume_gb,
        ip_limit=body.ip_limit,
        discount_code=body.discount_code,
        user_id=uid
    )

    custom_plan = {
        "id": 0,
        "name": calc["plan_name"],
        "price": calc["total_price"],
        "days": calc["days"],
        "volume_gb": calc["effective_volume_gb"],
        "volume": calc["effective_volume_gb"],
        "ip_limit": calc["effective_ip_limit"],
        "sort_order": 0,
        "active": True,
    }

    if body.discount_code:
        from . import core as _core  # noqa: PLC0415
        _core.set_pending_discount(uid, body.discount_code)

    from . import core as _core  # noqa: PLC0415
    result, error = _core._create_checkout_transaction(uid, custom_plan, "WALLET", custom_name=body.custom_name)
    if not result:
        raise HTTPException(status_code=400, detail=error or "موجودی کیف پول ناکافی است")

    tx_id = result["tx_id"]
    _core.finalize_service_transaction(tx_id)

    return {
        "status": "processing",
        "tx_id": tx_id,
        "price": result["price"],
        "plan_name": calc["plan_name"],
        "message": "خرید پلن اختصاصی از کیف پول با موفقیت ثبت شد",
    }


# ---------------------------------------------------------------------------
# Payment Gateways (Zibal & Zarinpal)
# ---------------------------------------------------------------------------

@app.get("/api/gateways/active")
async def get_active_gateways(_user: Dict[str, Any] = Depends(get_current_user)):
    """Return enabled payment methods available for checkout."""
    stars_enabled = _setting("gateway_stars_enabled", "1") == "1"
    stars_rate = int(_setting("gateway_stars_rate", "1500") or 1500)
    return {
        "card": True,
        "wallet": True,
        "zibal": _setting("gateway_zibal_enabled", "0") == "1",
        "zarinpal": _setting("gateway_zarinpal_enabled", "0") == "1",
        "stars": stars_enabled,
        "stars_rate": stars_rate,
    }


@app.post("/api/orders/init-stars")
async def init_stars_order(
    body: InitStarsOrderRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Initiate payment via Telegram Stars (XTR). Generates native invoice link."""
    uid = user["id"]
    stars_enabled = _setting("gateway_stars_enabled", "1") == "1"
    if not stars_enabled:
        raise HTTPException(status_code=400, detail="پرداخت با تلگرام استارز در حال حاضر غیرفعال است.")

    stars_rate = int(_setting("gateway_stars_rate", "1500") or 1500)
    if stars_rate <= 0:
        stars_rate = 1500

    import math  # noqa: PLC0415
    plan_name = "سرویس"
    price = 0
    plan_id = None
    custom_spec = None

    if body.plan_id:
        conn = _db()
        p = conn.execute("SELECT * FROM plans WHERE id = ? AND active = 1", (body.plan_id,)).fetchone()
        conn.close()
        if not p:
            raise HTTPException(status_code=404, detail="پلن انتخابی یافت نشد.")
        plan_id = int(p["id"])
        plan_name = p["name"]
        price = int(p["price"])
    elif body.custom_spec:
        calc = _calculate_builder_plan(
            months=int(body.custom_spec.get("months", 1)),
            volume_gb=int(body.custom_spec.get("volume_gb", 0)),
            ip_limit=int(body.custom_spec.get("ip_limit", 1)),
        )
        plan_name = calc["plan_name"]
        price = calc.get("total_price", calc.get("final_price", 0))
        custom_spec = calc
    else:
        raise HTTPException(status_code=400, detail="مشخصات پلن یا پلن انتخابی الزامی است.")

    discount_amount = 0
    if body.discount_code:
        d = _calc_discount(body.discount_code.strip(), price, uid)
        if d > 0:
            discount_amount = d
            price = max(1000, price - discount_amount)

    stars_amount = max(1, math.ceil(price / stars_rate))
    now = int(time.time())

    conn = _db()
    try:
        from .db import resolve_unique_service_email, get_brand_name
        service_email = resolve_unique_service_email(body.custom_name, user_id=uid, tx_id=0, conn=conn)
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO transactions (
                user_id, photo_id, plan_id, status, price, payment_method, wallet_used, cash_amount, created_at,
                service_email, custom_name, kind, plan_name_snapshot, plan_days_snapshot, plan_volume_gb_snapshot,
                plan_ip_limit_snapshot, discount_code, discount_amount, extra_volume_gb
            ) VALUES (?, 'stars', ?, 'PENDING', ?, 'STARS', 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                uid,
                plan_id or 0,
                price,
                price,
                now,
                service_email,
                body.custom_name or service_email,
                "CUSTOM" if custom_spec else "NEW",
                plan_name,
                int(custom_spec.get("days", 30)) if custom_spec else 30,
                float(custom_spec.get("volume_gb", 0)) if custom_spec else 0.0,
                int(custom_spec.get("ip_limit", 1)) if custom_spec else 1,
                body.discount_code,
                discount_amount,
            ),
        )
        tx_id = c.lastrowid
        conn.commit()
    finally:
        conn.close()

    from . import core as _core  # noqa: PLC0415
    from telebot import types as _tele_types  # noqa: PLC0415

    try:
        invoice_link = _core.bot.create_invoice_link(
            title=f"خرید {plan_name}",
            description=f"سفارش شماره #{tx_id} در {get_brand_name()} - فعال‌سازی آنی",
            payload=f"stars_order_{tx_id}",
            provider_token="",  # ALWAYS empty for Telegram Stars (XTR)
            currency="XTR",
            prices=[_tele_types.LabeledPrice(label=plan_name, amount=stars_amount)],
        )
    except Exception as e:
        logger.error("Failed to generate Telegram Stars invoice: %s", e)
        raise HTTPException(status_code=500, detail=f"خطا در ایجاد فاکتور تلگرام استارز: {e}")

    return {
        "status": "invoice_created",
        "order_id": tx_id,
        "invoice_link": invoice_link,
        "stars": stars_amount,
        "stars_amount": stars_amount,
        "price_tomans": price,
        "currency": "XTR",
    }


@app.post("/api/orders/init-gateway")
async def init_gateway_order(
    request: Request,
    body: InitGatewayOrderRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Initiate an online payment via Zibal or Zarinpal."""
    uid = user["id"]
    gateway = body.gateway.lower().strip()
    if gateway not in ("zibal", "zarinpal"):
        raise HTTPException(status_code=400, detail="درگاه پرداخت انتخابی معتبر نیست.")

    enabled = _setting(f"gateway_{gateway}_enabled", "0") == "1"
    if not enabled:
        raise HTTPException(status_code=400, detail=f"درگاه {gateway} در حال حاضر غیرفعال است.")

    # 1. Resolve plan
    if body.plan_id:
        conn = _db()
        plan_row = conn.execute("SELECT * FROM plans WHERE id = ? AND active = 1", (body.plan_id,)).fetchone()
        conn.close()
        if not plan_row:
            raise HTTPException(status_code=404, detail="پلن انتخابی یافت نشد.")
        plan = {
            "id": plan_row["id"],
            "name": plan_row["name"],
            "price": int(plan_row["price"]),
            "days": int(plan_row["days"]),
            "volume_gb": float(plan_row["volume_gb"] or 0),
            "volume": float(plan_row["volume_gb"] or 0),
            "ip_limit": int(plan_row["ip_limit"] or 0),
            "sort_order": int(plan_row["sort_order"] or 100),
            "active": True,
        }
    elif body.months:
        calc = _calculate_builder_plan(
            months=body.months,
            volume_gb=body.volume_gb or 0,
            ip_limit=body.ip_limit if body.ip_limit is not None else 1,
            discount_code=body.discount_code,
            user_id=uid
        )
        plan = {
            "id": 0,
            "name": calc["plan_name"],
            "price": calc["total_price"],
            "days": calc["days"],
            "volume_gb": calc["effective_volume_gb"],
            "volume": calc["effective_volume_gb"],
            "ip_limit": calc["effective_ip_limit"],
            "sort_order": 0,
            "active": True,
        }
    else:
        raise HTTPException(status_code=400, detail="مشخصات پلن ارسال نشده است.")

    if body.discount_code:
        from . import core as _core  # noqa: PLC0415
        _core.set_pending_discount(uid, body.discount_code)

    # 2. Create pending transaction
    from . import core as _core  # noqa: PLC0415
    result, error = _core._create_checkout_transaction(uid, plan, gateway.upper(), custom_name=body.custom_name)
    if not result:
        raise HTTPException(status_code=400, detail=error or "خطا در ایجاد تراکنش درگاه")

    tx_id = result["tx_id"]
    final_price = result["price"]

    # 3. Determine base URL for callback
    base_url = str(request.base_url).rstrip("/")
    configured_url = _setting("webapp_url", "").strip() or os.getenv("WEBAPP_URL", "").strip()
    if configured_url:
        base_url = configured_url.rstrip("/")

    callback_url = f"{base_url}/api/payment/callback/{gateway}?order_id={tx_id}"

    # 4. Request payment from gateway adapter
    from .gateways import ZibalGateway, ZarinpalGateway  # noqa: PLC0415

    if gateway == "zibal":
        merchant = _setting("gateway_zibal_merchant", "zibal").strip() or "zibal"
        payment_url, track_id, err = ZibalGateway.request_payment(
            merchant=merchant,
            amount_tomans=final_price,
            callback_url=callback_url,
            order_id=tx_id,
            description=f"خرید اشتراک VPN #{tx_id}",
        )
    else:  # zarinpal
        merchant = _setting("gateway_zarinpal_merchant", "").strip() or "sandbox"
        sandbox = _setting("gateway_zarinpal_sandbox", "0") == "1" or merchant.lower() == "sandbox"
        payment_url, authority, err = ZarinpalGateway.request_payment(
            merchant=merchant,
            amount_tomans=final_price,
            callback_url=callback_url,
            order_id=tx_id,
            description=f"خرید اشتراک VPN #{tx_id}",
            sandbox=sandbox,
        )

    if err or not payment_url:
        conn = _db()
        conn.execute("UPDATE transactions SET status='FAILED', last_error=? WHERE id=?", (err or "Gateway error", tx_id))
        conn.commit()
        conn.close()
        raise HTTPException(status_code=500, detail=err or "خطا در برقراری ارتباط با درگاه پرداخت")

    return {
        "status": "redirect",
        "payment_url": payment_url,
        "tx_id": tx_id,
        "price": final_price,
    }


def _render_gateway_result_html(success: bool, order_id: int, title: str, message: str, ref_id: str = "") -> str:
    icon = "✓" if success else "✕"
    color = "#10b981" if success else "#ef4444"
    bg_badge = "rgba(16, 185, 129, 0.15)" if success else "rgba(239, 68, 68, 0.15)"
    ref_row = f"<p style='margin: 8px 0; font-size: 13px; color: #94a3b8;'>کد پیگیری: <b style='color:#f8fafc;'>{ref_id}</b></p>" if ref_id else ""

    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        body {{
            background-color: #0f172a;
            color: #f8fafc;
            font-family: 'Vazirmatn', sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            padding: 16px;
            box-sizing: border-box;
        }}
        .card {{
            background: #1e293b;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 24px;
            max-width: 420px;
            width: 100%;
            padding: 28px 20px;
            text-align: center;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
        }}
        .icon-circle {{
            width: 64px;
            height: 64px;
            border-radius: 50%;
            background: {bg_badge};
            color: {color};
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 16px;
        }}
        .btn {{
            display: block;
            width: 100%;
            background: #2563eb;
            color: #ffffff;
            text-decoration: none;
            padding: 14px;
            border-radius: 14px;
            font-weight: 600;
            font-size: 14px;
            margin-top: 24px;
            box-sizing: border-box;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon-circle">{icon}</div>
        <h2 style="margin: 0 0 10px; font-size: 18px; color: {color};">{title}</h2>
        <p style="margin: 0 0 14px; font-size: 13px; line-height: 1.6; color: #cbd5e1;">{message}</p>
        <p style="margin: 4px 0; font-size: 13px; color: #94a3b8;">شماره سفارش: <b style='color:#f8fafc;'>#{order_id}</b></p>
        {ref_row}
        <a href="https://t.me" class="btn" onclick="if(window.Telegram?.WebApp) {{ Telegram.WebApp.close(); return false; }}">بازگشت به تلگرام</a>
    </div>
</body>
</html>"""


@app.get("/api/payment/callback/zibal", response_class=HTMLResponse)
async def payment_callback_zibal(
    order_id: int,
    trackId: Optional[str] = None,
    success: Optional[str] = None,
    status: Optional[str] = None,
):
    """Handle return callback from Zibal payment gateway."""
    conn = _db()
    tx = conn.execute("SELECT * FROM transactions WHERE id = ?", (int(order_id),)).fetchone()
    conn.close()

    if not tx:
        return HTMLResponse(
            _render_gateway_result_html(False, order_id, "سفارش نامعتبر", "سفارش مورد نظر در سیستم یافت نشد."),
            status_code=404,
        )

    # Check if already processed
    if tx["status"] == "APPROVED":
        return HTMLResponse(
            _render_gateway_result_html(True, order_id, "پرداخت قبلاً تایید شده", "این سفارش قبلاً با موفقیت تایید و تحویل شده است.")
        )

    from .gateways import ZibalGateway  # noqa: PLC0415
    merchant = _setting("gateway_zibal_merchant", "zibal").strip() or "zibal"

    target_track = trackId or str(tx.get("photo_id") or "")
    if not target_track:
        return HTMLResponse(
            _render_gateway_result_html(False, order_id, "پرداخت ناموفق", "شناسه پیگیری تراکنش زیبال یافت نشد.")
        )

    is_verified, ref_num, err = ZibalGateway.verify_payment(merchant=merchant, track_id=target_track)

    if not is_verified:
        conn = _db()
        conn.execute("UPDATE transactions SET status='CANCELLED', last_error=? WHERE id=?", (err or "Zibal verify failed", int(order_id)))
        conn.commit()
        conn.close()
        return HTMLResponse(
            _render_gateway_result_html(False, order_id, "پرداخت ناموفق یا لغو شده", err or "تراکنش توسط بانک یا کاربر لغو شد.")
        )

    # Success! Finalize and provision service
    from . import core as _core  # noqa: PLC0415
    _core.finalize_service_transaction(order_id)

    # Send delivery message to user in Telegram
    try:
        _core.bot.send_message(
            tx["user_id"],
            f"🎉 <b>پرداخت آنلاین شما با موفقیت تایید شد!</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🆔 کد سفارش: <code>#{order_id}</code>\n"
            f"🧾 شماره پیگیری زیبال: <code>{ref_num}</code>\n"
            f"⚡️ سرویس شما فعال شد و اطلاعات آن در ادامه ارسال گردید.",
            parse_mode="HTML"
        )
    except Exception:
        pass

    return HTMLResponse(
        _render_gateway_result_html(
            True,
            order_id,
            "پرداخت با موفقیت انجام شد!",
            "سرویس شما به صورت خودکار فعال شد و اطلاعات اشتراک در چت تلگرام برای شما ارسال گردید.",
            ref_id=ref_num or ""
        )
    )


@app.get("/api/payment/callback/zarinpal", response_class=HTMLResponse)
async def payment_callback_zarinpal(
    order_id: int,
    Authority: Optional[str] = None,
    Status: Optional[str] = None,
):
    """Handle return callback from Zarinpal payment gateway."""
    conn = _db()
    tx = conn.execute("SELECT * FROM transactions WHERE id = ?", (int(order_id),)).fetchone()
    conn.close()

    if not tx:
        return HTMLResponse(
            _render_gateway_result_html(False, order_id, "سفارش نامعتبر", "سفارش مورد نظر در سیستم یافت نشد."),
            status_code=404,
        )

    if tx["status"] == "APPROVED":
        return HTMLResponse(
            _render_gateway_result_html(True, order_id, "پرداخت قبلاً تایید شده", "این سفارش قبلاً با موفقیت تایید و تحویل شده است.")
        )

    if str(Status).upper() != "OK" or not Authority:
        conn = _db()
        conn.execute("UPDATE transactions SET status='CANCELLED', last_error='Zarinpal cancelled by user' WHERE id=?", (int(order_id),))
        conn.commit()
        conn.close()
        return HTMLResponse(
            _render_gateway_result_html(False, order_id, "پرداخت لغو شد", "تراکنش بانکی توسط کاربر لغو شد یا ناموفق بود.")
        )

    from .gateways import ZarinpalGateway  # noqa: PLC0415
    merchant = _setting("gateway_zarinpal_merchant", "").strip() or "sandbox"
    sandbox = _setting("gateway_zarinpal_sandbox", "0") == "1" or merchant.lower() == "sandbox"

    is_verified, ref_id, err = ZarinpalGateway.verify_payment(
        merchant=merchant,
        amount_tomans=int(tx["price"]),
        authority=Authority,
        sandbox=sandbox,
    )

    if not is_verified:
        conn = _db()
        conn.execute("UPDATE transactions SET status='CANCELLED', last_error=? WHERE id=?", (err or "Zarinpal verify failed", int(order_id)))
        conn.commit()
        conn.close()
        return HTMLResponse(
            _render_gateway_result_html(False, order_id, "تایید تراکنش ناموفق", err or "تراکنش بانکی مورد تایید قرار نگرفت.")
        )

    # Success! Finalize and provision service
    from . import core as _core  # noqa: PLC0415
    _core.finalize_service_transaction(order_id)

    try:
        _core.bot.send_message(
            tx["user_id"],
            f"🎉 <b>پرداخت آنلاین شما با موفقیت تایید شد!</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🆔 کد سفارش: <code>#{order_id}</code>\n"
            f"🧾 شماره پیگیری زرین‌پال: <code>{ref_id}</code>\n"
            f"⚡️ سرویس شما فعال شد و اطلاعات آن در ادامه ارسال گردید.",
            parse_mode="HTML"
        )
    except Exception:
        pass

    return HTMLResponse(
        _render_gateway_result_html(
            True,
            order_id,
            "پرداخت با موفقیت انجام شد!",
            "سرویس شما به صورت خودکار فعال شد و اطلاعات اشتراک در چت تلگرام برای شما ارسال گردید.",
            ref_id=ref_id or ""
        )
    )


# ---------------------------------------------------------------------------
# Admin — Payment Gateways Configuration
# ---------------------------------------------------------------------------

@app.get("/api/admin/gateways")
async def admin_get_gateways(_admin: Dict[str, Any] = Depends(get_admin_user)):
    """Return gateway configurations for admin panel."""
    return {
        "zibal": {
            "enabled": _setting("gateway_zibal_enabled", "0") == "1",
            "merchant": _setting("gateway_zibal_merchant", ""),
            "sandbox": _setting("gateway_zibal_sandbox", "0") == "1",
        },
        "zarinpal": {
            "enabled": _setting("gateway_zarinpal_enabled", "0") == "1",
            "merchant": _setting("gateway_zarinpal_merchant", ""),
            "sandbox": _setting("gateway_zarinpal_sandbox", "0") == "1",
        },
    }


@app.post("/api/admin/gateways")
async def admin_save_gateways(
    body: AdminGatewaySettingsRequest,
    _admin: Dict[str, Any] = Depends(get_admin_user),
):
    """Save gateway settings from admin panel."""
    _update_setting("gateway_zibal_enabled", "1" if body.zibal_enabled else "0")
    _update_setting("gateway_zibal_merchant", body.zibal_merchant.strip())
    _update_setting("gateway_zibal_sandbox", "1" if body.zibal_sandbox else "0")

    _update_setting("gateway_zarinpal_enabled", "1" if body.zarinpal_enabled else "0")
    _update_setting("gateway_zarinpal_merchant", body.zarinpal_merchant.strip())
    _update_setting("gateway_zarinpal_sandbox", "1" if body.zarinpal_sandbox else "0")

    return {"status": "saved", "message": "تنظیمات درگاه‌های پرداخت با موفقیت ذخیره شد."}


# ---------------------------------------------------------------------------
# Admin — Branding / UI Title
# ---------------------------------------------------------------------------

@app.get("/api/admin/branding")
async def get_admin_branding(_admin: Dict[str, Any] = Depends(get_admin_user)):
    """Return current webapp branding / title."""
    app_title = _brand_name()
    return {
        "webapp_title": app_title,
    }


@app.post("/api/admin/branding")
async def save_admin_branding(
    body: BrandingRequest,
    _admin: Dict[str, Any] = Depends(get_admin_user),
):
    """Save webapp UI title."""
    title = body.webapp_title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="عنوان وب‌اپ نمی‌تواند خالی باشد.")
    if len(title) > 64:
        raise HTTPException(status_code=400, detail="عنوان نباید بیشتر از ۶۴ کاراکتر باشد.")

    _update_setting("webapp_title", title)
    _update_setting("brand_name", title)
    return {
        "success": True,
        "webapp_title": title,
        "message": "عنوان و نام وب‌اپ با موفقیت ذخیره شد.",
    }


# ---------------------------------------------------------------------------
# Admin — Stats
# ---------------------------------------------------------------------------

@app.get("/api/admin/stats")
async def admin_stats(_admin: Dict[str, Any] = Depends(get_admin_user)):
    conn = _db()
    total_users = conn.execute("SELECT COUNT(*) FROM users WHERE is_active=1").fetchone()[0]
    total_orders = conn.execute("SELECT COUNT(*) FROM transactions WHERE status='APPROVED' AND kind='NEW'").fetchone()[0]
    total_revenue = conn.execute(
        "SELECT COALESCE(SUM(price),0) FROM transactions WHERE status='APPROVED' AND kind='NEW' AND payment_method='CARD'"
    ).fetchone()[0]
    pending_orders = conn.execute("SELECT COUNT(*) FROM transactions WHERE status='PENDING'").fetchone()[0]
    today_ts = int(time.time()) - 86400
    new_users_today = conn.execute(
        "SELECT COUNT(*) FROM users WHERE created_at >= ?", (today_ts,)
    ).fetchone()[0]
    conn.close()
    return {
        "total_users": total_users,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "pending_orders": pending_orders,
        "new_users_today": new_users_today,
    }


# ---------------------------------------------------------------------------
# Admin — Pending orders
# ---------------------------------------------------------------------------

@app.get("/api/admin/orders")
async def admin_orders(
    status_filter: str = "PENDING",
    limit: int = 50,
    _admin: Dict[str, Any] = Depends(get_admin_user),
):
    allowed = {"PENDING", "AWAITING_RECEIPT", "APPROVED", "REJECTED", "CANCELLED", "PROCESSING"}
    if status_filter not in allowed:
        raise HTTPException(status_code=400, detail="Invalid status filter")
    conn = _db()
    rows = conn.execute(
        """SELECT id, user_id, plan_name_snapshot, price, payment_method,
                  status, photo_id, created_at, approved_at, service_email,
                  kind, discount_amount
           FROM transactions
           WHERE status = ?
           ORDER BY id DESC LIMIT ?""",
        (status_filter, limit),
    ).fetchall()
    conn.close()
    return {
        "orders": [
            {
                "id": r["id"],
                "user_id": r["user_id"],
                "plan": r["plan_name_snapshot"] or "",
                "price": int(r["price"] or 0),
                "method": r["payment_method"],
                "status": r["status"],
                "has_photo": bool(r["photo_id"]),
                "photo_id": r["photo_id"],
                "created_at": r["created_at"],
                "approved_at": r["approved_at"],
                "service_email": r["service_email"],
                "kind": r["kind"],
                "discount": int(r["discount_amount"] or 0),
            }
            for r in rows
        ]
    }


# ---------------------------------------------------------------------------
# Admin — Approve / Reject order
# ---------------------------------------------------------------------------

@app.post("/api/admin/orders/{order_id}/approve")
async def admin_approve_order(order_id: int, admin: Dict[str, Any] = Depends(get_admin_user)):
    """Approve a pending order and trigger service provisioning."""
    try:
        from . import core as _core  # noqa: PLC0415
        _core.finalize_service_transaction(order_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # Notify user via bot
    conn = _db()
    tx = conn.execute("SELECT user_id FROM transactions WHERE id = ?", (order_id,)).fetchone()
    conn.close()
    if tx:
        try:
            from . import core as _core  # noqa: PLC0415
            _core.bot.send_message(
                tx["user_id"],
                f"✅ پرداخت شما تأیید شد و سرویس در حال راه‌اندازی است.\n🆔 تراکنش: `{order_id}`",
                parse_mode="Markdown",
            )
        except Exception:
            pass

    return {"status": "approved", "order_id": order_id}


@app.post("/api/admin/orders/{order_id}/reject")
async def admin_reject_order(
    order_id: int,
    body: RejectOrderRequest,
    _admin: Dict[str, Any] = Depends(get_admin_user),
):
    conn = _db()
    tx = conn.execute("SELECT user_id, status FROM transactions WHERE id = ?", (order_id,)).fetchone()
    if not tx:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")
    if tx["status"] not in ("PENDING", "AWAITING_RECEIPT"):
        conn.close()
        raise HTTPException(status_code=400, detail=f"Cannot reject order in status {tx['status']}")

    conn.execute("UPDATE transactions SET status='REJECTED' WHERE id=?", (order_id,))
    conn.execute("UPDATE discount_redemptions SET status='RELEASED' WHERE tx_id=? AND status='RESERVED'", (order_id,))
    conn.commit()
    user_id = tx["user_id"]
    conn.close()

    reason_text = f"\n📝 دلیل: {body.reason}" if body.reason else ""
    try:
        from . import core as _core  # noqa: PLC0415
        _core.bot.send_message(
            user_id,
            f"❌ متأسفانه پرداخت شما رد شد.{reason_text}\n🆔 تراکنش: `{order_id}`",
            parse_mode="Markdown",
        )
    except Exception:
        pass

    return {"status": "rejected", "order_id": order_id}


# ---------------------------------------------------------------------------
# Admin — Server Status
# ---------------------------------------------------------------------------

def _get_server_status() -> Dict[str, Any]:
    import shutil
    import sys

    # Disk
    try:
        du = shutil.disk_usage("/")
        disk_total = du.total
        disk_used = du.used
        disk_percent = round((du.used / du.total) * 100, 1)
    except Exception:
        disk_total = disk_used = disk_percent = 0

    # RAM
    ram_total = ram_used = ram_percent = 0
    try:
        with open("/proc/meminfo", "r") as f:
            lines = f.readlines()
        mem = {}
        for line in lines:
            parts = line.split(":")
            if len(parts) == 2:
                mem[parts[0].strip()] = int(parts[1].split()[0])
        total_kb = mem.get("MemTotal", 0)
        avail_kb = mem.get("MemAvailable", mem.get("MemFree", 0))
        used_kb = total_kb - avail_kb
        ram_total = total_kb * 1024
        ram_used = used_kb * 1024
        ram_percent = round((used_kb / total_kb) * 100, 1) if total_kb else 0
    except Exception:
        pass

    # CPU load
    load_1 = 0.0
    try:
        load_1, _, _ = os.getloadavg()
    except Exception:
        pass

    # Uptime
    uptime_seconds = 0
    try:
        with open("/proc/uptime", "r") as f:
            uptime_seconds = int(float(f.readline().split()[0]))
    except Exception:
        pass

    # 3x-ui connection status
    xui_ok = False
    xui_latency_ms = None
    try:
        from . import core as _core  # noqa: PLC0415
        import requests  # noqa: PLC0415
        t0 = time.time()
        url = _core._xui_url("panel/api/inbounds/list")
        r = requests.get(url, headers=_core._xui_headers(), proxies=_core._xui_proxies(), timeout=5)
        xui_latency_ms = round((time.time() - t0) * 1000)
        xui_ok = r.status_code == 200 and bool(r.json().get("success"))
    except Exception:
        xui_ok = False

    return {
        "cpu_load": f"{load_1:.2f}",
        "ram": {
            "used_mb": round(ram_used / (1024 * 1024)),
            "total_mb": round(ram_total / (1024 * 1024)),
            "percent": ram_percent,
        },
        "disk": {
            "used_gb": round(disk_used / (1024 * 1024 * 1024), 1),
            "total_gb": round(disk_total / (1024 * 1024 * 1024), 1),
            "percent": disk_percent,
        },
        "uptime_hours": round(uptime_seconds / 3600, 1),
        "python_version": sys.version.split()[0],
        "xui": {
            "connected": xui_ok,
            "latency_ms": xui_latency_ms,
        },
    }


@app.get("/api/admin/server-status")
async def admin_server_status_get(_admin: Dict[str, Any] = Depends(get_admin_user)):
    return _get_server_status()


# ---------------------------------------------------------------------------
# Admin — Custom Plan Builder Defaults
# ---------------------------------------------------------------------------

@app.get("/api/admin/builder/defaults")
async def admin_builder_defaults_get(_admin: Dict[str, Any] = Depends(get_admin_user)):
    return {
        "month_price": int(_setting("builder_month_price", "120000") or 120000),
        "gb_price": int(_setting("builder_gb_price", "1000") or 1000),
        "discount_3m": int(_setting("builder_dur_discount_3m", "5") or 5),
        "discount_6m": int(_setting("builder_dur_discount_6m", "10") or 10),
        "discount_12m": int(_setting("builder_dur_discount_12m", "20") or 20),
        "traffic_discount_50": int(_setting("builder_traffic_discount_50", "5") or 5),
        "traffic_discount_100": int(_setting("builder_traffic_discount_100", "15") or 15),
        "traffic_discount_300": int(_setting("builder_traffic_discount_300", "30") or 30),
        "traffic_unlimited_price": int(_setting("builder_traffic_unlimited_price", "500000") or 500000),
        "traffic_unlimited_cap_gb": int(_setting("builder_traffic_unlimited_cap_gb", "1000") or 1000),
        "user_cost_1": int(_setting("builder_user_cost_1", "0") or 0),
        "user_cost_2": int(_setting("builder_user_cost_2", "20000") or 20000),
        "user_cost_3": int(_setting("builder_user_cost_3", "35000") or 35000),
        "user_cost_4": int(_setting("builder_user_cost_4", "45000") or 45000),
        "user_cost_5": int(_setting("builder_user_cost_5", "50000") or 50000),
        "user_cost_unlimited": int(_setting("builder_user_cost_unlimited", "65000") or 65000),
    }


@app.post("/api/admin/builder/defaults")
async def admin_builder_defaults_post(
    body: AdminBuilderDefaultsRequest,
    _admin: Dict[str, Any] = Depends(get_admin_user),
):
    mapping = {
        "month_price": "builder_month_price",
        "gb_price": "builder_gb_price",
        "discount_3m": "builder_dur_discount_3m",
        "discount_6m": "builder_dur_discount_6m",
        "discount_12m": "builder_dur_discount_12m",
        "traffic_discount_50": "builder_traffic_discount_50",
        "traffic_discount_100": "builder_traffic_discount_100",
        "traffic_discount_300": "builder_traffic_discount_300",
        "traffic_unlimited_price": "builder_traffic_unlimited_price",
        "traffic_unlimited_cap_gb": "builder_traffic_unlimited_cap_gb",
        "user_cost_1": "builder_user_cost_1",
        "user_cost_2": "builder_user_cost_2",
        "user_cost_3": "builder_user_cost_3",
        "user_cost_4": "builder_user_cost_4",
        "user_cost_5": "builder_user_cost_5",
        "user_cost_unlimited": "builder_user_cost_unlimited",
    }
    for attr, key in mapping.items():
        val = getattr(body, attr, None)
        if val is not None:
            _update_setting(key, str(val))
    return {"status": "saved", "message": "پیش‌فرض‌های پلن‌ساز با موفقیت ذخیره شد."}


# ---------------------------------------------------------------------------
# Admin — Payments & Gateways (Card, Zibal, Zarinpal, Stars)
# ---------------------------------------------------------------------------

@app.get("/api/admin/payments")
async def admin_get_payments(_admin: Dict[str, Any] = Depends(get_admin_user)):
    return {
        "card": {
            "card_number": _setting("card_number", ""),
            "card_holder": _setting("card_holder", ""),
            "bank_name": _setting("bank_name", ""),
        },
        "zibal": {
            "enabled": _setting("gateway_zibal_enabled", "0") == "1",
            "merchant": _setting("gateway_zibal_merchant", ""),
            "sandbox": _setting("gateway_zibal_sandbox", "0") == "1",
        },
        "zarinpal": {
            "enabled": _setting("gateway_zarinpal_enabled", "0") == "1",
            "merchant": _setting("gateway_zarinpal_merchant", ""),
            "sandbox": _setting("gateway_zarinpal_sandbox", "0") == "1",
        },
        "stars": {
            "enabled": _setting("gateway_stars_enabled", "1") == "1",
            "rate": int(_setting("gateway_stars_rate", "1500") or 1500),
        },
    }


@app.post("/api/admin/payments")
async def admin_save_payments(
    body: AdminPaymentsSettingsRequest,
    _admin: Dict[str, Any] = Depends(get_admin_user),
):
    if body.card_number is not None:
        _update_setting("card_number", body.card_number.strip())
    if body.card_holder is not None:
        _update_setting("card_holder", body.card_holder.strip())
    if body.bank_name is not None:
        _update_setting("bank_name", body.bank_name.strip())

    if body.zibal_enabled is not None:
        _update_setting("gateway_zibal_enabled", "1" if body.zibal_enabled else "0")
    if body.zibal_merchant is not None:
        _update_setting("gateway_zibal_merchant", body.zibal_merchant.strip())
    if body.zibal_sandbox is not None:
        _update_setting("gateway_zibal_sandbox", "1" if body.zibal_sandbox else "0")

    if body.zarinpal_enabled is not None:
        _update_setting("gateway_zarinpal_enabled", "1" if body.zarinpal_enabled else "0")
    if body.zarinpal_merchant is not None:
        _update_setting("gateway_zarinpal_merchant", body.zarinpal_merchant.strip())
    if body.zarinpal_sandbox is not None:
        _update_setting("gateway_zarinpal_sandbox", "1" if body.zarinpal_sandbox else "0")

    if body.stars_enabled is not None:
        _update_setting("gateway_stars_enabled", "1" if body.stars_enabled else "0")
    if body.stars_rate is not None and body.stars_rate > 0:
        _update_setting("gateway_stars_rate", str(body.stars_rate))

    return {"status": "saved", "message": "تنظیمات روش‌های پرداخت با موفقیت ذخیره شد."}


# ---------------------------------------------------------------------------
# Admin — User list & Management
# ---------------------------------------------------------------------------

@app.get("/api/admin/users")
async def admin_users(
    limit: int = 100,
    offset: int = 0,
    q: Optional[str] = None,
    _admin: Dict[str, Any] = Depends(get_admin_user),
):
    conn = _db()
    if q and q.strip():
        search = f"%{q.strip()}%"
        rows = conn.execute(
            """
            SELECT id, balance, created_at, last_seen_at, is_active
            FROM users
            WHERE CAST(id AS TEXT) LIKE ?
            ORDER BY id DESC LIMIT ? OFFSET ?
            """,
            (search, limit, offset),
        ).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) FROM users WHERE CAST(id AS TEXT) LIKE ?",
            (search,),
        ).fetchone()[0]
    else:
        rows = conn.execute(
            "SELECT id, balance, created_at, last_seen_at, is_active FROM users ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    return {
        "total": total,
        "users": [
            {
                "id": r["id"],
                "balance": int(r["balance"] or 0),
                "created_at": r["created_at"],
                "last_seen_at": r["last_seen_at"],
                "is_active": bool(r["is_active"]),
            }
            for r in rows
        ],
    }


@app.get("/api/admin/users/{user_id}")
async def admin_user_detail(user_id: int, _admin: Dict[str, Any] = Depends(get_admin_user)):
    conn = _db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="کاربر یافت نشد.")

    transactions = conn.execute(
        """
        SELECT id, plan_name_snapshot, price, status, payment_method, created_at, approved_at
        FROM transactions WHERE user_id = ? ORDER BY id DESC LIMIT 20
        """,
        (user_id,),
    ).fetchall()

    services = conn.execute(
        """
        SELECT id, sub_id, plan_id, status, created_at, expires_at
        FROM linked_services WHERE user_id = ? ORDER BY id DESC LIMIT 10
        """,
        (user_id,),
    ).fetchall()
    conn.close()

    return {
        "user": {
            "id": user["id"],
            "balance": int(user["balance"] or 0),
            "created_at": user["created_at"],
            "last_seen_at": user["last_seen_at"],
            "is_active": bool(user["is_active"]),
        },
        "transactions": [
            {
                "id": t["id"],
                "plan": t["plan_name_snapshot"] or "سرویس",
                "price": int(t["price"] or 0),
                "status": t["status"],
                "method": t["payment_method"],
                "created_at": t["created_at"],
                "approved_at": t["approved_at"],
            }
            for t in transactions
        ],
        "services": [
            {
                "id": s["id"],
                "sub_id": s["sub_id"],
                "plan_id": s["plan_id"],
                "status": s["status"],
                "created_at": s["created_at"],
                "expires_at": s["expires_at"],
            }
            for s in services
        ],
    }


@app.post("/api/admin/users/{user_id}/balance")
async def admin_adjust_user_balance(
    user_id: int,
    body: AdminAdjustBalanceRequest,
    admin: Dict[str, Any] = Depends(get_admin_user),
):
    conn = _db()
    try:
        user = conn.execute("SELECT balance FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="کاربر یافت نشد.")

        current_balance = int(user["balance"] or 0)
        new_balance = max(0, current_balance + body.amount)
        now = int(time.time())

        conn.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, user_id))
        conn.execute(
            """
            INSERT INTO wallet_transactions (user_id, amount, balance_after, type, description, created_at)
            VALUES (?, ?, ?, 'MANUAL_ADMIN', ?, ?)
            """,
            (user_id, body.amount, new_balance, body.reason or "تغییر موجودی توسط مدیریت", now),
        )
        conn.commit()
    finally:
        conn.close()

    try:
        from . import core as _core  # noqa: PLC0415
        diff_str = f"+{body.amount:,}" if body.amount > 0 else f"{body.amount:,}"
        _core.bot.send_message(
            user_id,
            f"💼 <b>موجودی کیف پول شما توسط مدیریت تغییر یافت:</b>\n"
            f"تغییر: <code>{diff_str}</code> تومان\n"
            f"موجودی جدید: <b>{new_balance:,}</b> تومان\n"
            f"توضیحات: {body.reason}",
            parse_mode="HTML",
        )
    except Exception:
        pass

    return {"status": "updated", "new_balance": new_balance}


@app.post("/api/admin/users/{user_id}/toggle-status")
async def admin_toggle_user_status(user_id: int, _admin: Dict[str, Any] = Depends(get_admin_user)):
    conn = _db()
    user = conn.execute("SELECT is_active FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="کاربر یافت نشد.")
    new_status = 0 if user["is_active"] else 1
    conn.execute("UPDATE users SET is_active = ? WHERE id = ?", (new_status, user_id))
    conn.commit()
    conn.close()
    return {"status": "updated", "is_active": bool(new_status)}


# ---------------------------------------------------------------------------
# Admin — Plans CRUD
# ---------------------------------------------------------------------------

@app.get("/api/admin/plans")
async def admin_plans(_admin: Dict[str, Any] = Depends(get_admin_user)):
    conn = _db()
    rows = conn.execute(
        "SELECT id, name, price, volume_gb, days, ip_limit, active, sort_order, group_name FROM plans ORDER BY sort_order, id"
    ).fetchall()
    conn.close()
    return {
        "plans": [
            {
                "id": r["id"],
                "name": r["name"],
                "price": r["price"],
                "volume_gb": float(r["volume_gb"] or 0),
                "days": r["days"],
                "ip_limit": r["ip_limit"],
                "active": bool(r["active"]),
                "sort_order": r["sort_order"],
                "group_name": r["group_name"] or "",
            }
            for r in rows
        ]
    }


@app.post("/api/admin/plans")
async def admin_create_plan(body: AdminPlanCreateRequest, _admin: Dict[str, Any] = Depends(get_admin_user)):
    now = int(time.time())
    conn = _db()
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO plans (name, price, volume_gb, days, ip_limit, active, sort_order, group_name, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (body.name.strip(), body.price, body.volume_gb, body.days, body.ip_limit, body.active, body.sort_order, (body.group_name or "").strip() or None, now, now),
    )
    plan_id = c.lastrowid
    conn.commit()
    conn.close()
    return {"status": "created", "plan_id": plan_id, "message": "پلن جدید با موفقیت اضافه شد."}


@app.put("/api/admin/plans/{plan_id}")
async def admin_update_plan(plan_id: int, body: AdminPlanUpdateRequest, _admin: Dict[str, Any] = Depends(get_admin_user)):
    conn = _db()
    plan = conn.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
    if not plan:
        conn.close()
        raise HTTPException(status_code=404, detail="پلن یافت نشد.")

    now = int(time.time())
    name = body.name.strip() if body.name is not None else plan["name"]
    price = body.price if body.price is not None else plan["price"]
    volume_gb = body.volume_gb if body.volume_gb is not None else plan["volume_gb"]
    days = body.days if body.days is not None else plan["days"]
    ip_limit = body.ip_limit if body.ip_limit is not None else plan["ip_limit"]
    active = body.active if body.active is not None else plan["active"]
    sort_order = body.sort_order if body.sort_order is not None else plan["sort_order"]
    group_name = body.group_name.strip() if body.group_name is not None else (plan["group_name"] if "group_name" in plan.keys() else None)

    conn.execute(
        """
        UPDATE plans
        SET name = ?, price = ?, volume_gb = ?, days = ?, ip_limit = ?, active = ?, sort_order = ?, group_name = ?, updated_at = ?
        WHERE id = ?
        """,
        (name, price, volume_gb, days, ip_limit, active, sort_order, (group_name or "").strip() or None, now, plan_id),
    )
    conn.commit()
    conn.close()
    return {"status": "updated", "message": "پلن با موفقیت ویرایش شد."}


@app.delete("/api/admin/plans/{plan_id}")
async def admin_delete_plan(plan_id: int, _admin: Dict[str, Any] = Depends(get_admin_user)):
    conn = _db()
    conn.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted", "message": "پلن با موفقیت حذف شد."}


@app.post("/api/admin/plans/{plan_id}/toggle")
async def admin_toggle_plan(plan_id: int, _admin: Dict[str, Any] = Depends(get_admin_user)):
    conn = _db()
    plan = conn.execute("SELECT active FROM plans WHERE id = ?", (plan_id,)).fetchone()
    if not plan:
        conn.close()
        raise HTTPException(status_code=404, detail="پلن یافت نشد.")
    new_state = 0 if plan["active"] else 1
    conn.execute("UPDATE plans SET active = ?, updated_at = ? WHERE id = ?", (new_state, int(time.time()), plan_id))
    conn.commit()
    conn.close()
    return {"status": "toggled", "active": bool(new_state)}


# ---------------------------------------------------------------------------
# Admin — Blacklist Management
# ---------------------------------------------------------------------------

@app.get("/api/admin/blacklist")
async def admin_blacklist_get(_admin: Dict[str, Any] = Depends(get_admin_user)):
    conn = _db()
    rows = conn.execute(
        """
        SELECT user_id, reason, created_at, created_by
        FROM user_blocks
        WHERE active = 1
        ORDER BY created_at DESC
        """
    ).fetchall()
    conn.close()
    return {
        "blacklist": [
            {
                "user_id": r["user_id"],
                "reason": r["reason"] or "مسدود توسط ادمین",
                "created_at": r["created_at"],
                "created_by": r["created_by"],
            }
            for r in rows
        ]
    }


@app.post("/api/admin/blacklist/add")
async def admin_blacklist_add(
    body: AdminBlacklistAddRequest,
    admin: Dict[str, Any] = Depends(get_admin_user),
):
    now = int(time.time())
    admin_id = admin["id"]
    conn = _db()
    conn.execute(
        """
        INSERT INTO user_blocks (user_id, reason, active, created_at, created_by, updated_at)
        VALUES (?, ?, 1, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET active = 1, reason = excluded.reason, updated_at = excluded.updated_at
        """,
        (body.user_id, body.reason, now, admin_id, now),
    )
    conn.execute("UPDATE users SET is_active = 0 WHERE id = ?", (body.user_id,))
    conn.commit()
    conn.close()
    return {"status": "blocked", "user_id": body.user_id, "message": "کاربر با موفقیت مسدود شد."}


@app.post("/api/admin/blacklist/remove")
async def admin_blacklist_remove(
    body: AdminBlacklistAddRequest,
    _admin: Dict[str, Any] = Depends(get_admin_user),
):
    conn = _db()
    conn.execute("UPDATE user_blocks SET active = 0 WHERE user_id = ?", (body.user_id,))
    conn.execute("UPDATE users SET is_active = 1 WHERE id = ?", (body.user_id,))
    conn.commit()
    conn.close()
    return {"status": "unblocked", "user_id": body.user_id, "message": "مسدودیت کاربر لغو شد."}


# ---------------------------------------------------------------------------
# Admin — Other Admins Management
# ---------------------------------------------------------------------------

@app.get("/api/admin/admins")
async def admin_admins_get(_admin: Dict[str, Any] = Depends(get_admin_user)):
    owner_id = int(os.environ.get("ADMIN_ID", "0") or 0)
    conn = _db()
    rows = conn.execute("SELECT user_id, role, added_by, created_at FROM admins ORDER BY created_at DESC").fetchall()
    conn.close()
    admins_list = [
        {
            "user_id": owner_id,
            "role": "OWNER",
            "is_owner": True,
            "created_at": 0,
        }
    ]
    for r in rows:
        if r["user_id"] != owner_id:
            admins_list.append({
                "user_id": r["user_id"],
                "role": r["role"],
                "is_owner": False,
                "added_by": r["added_by"],
                "created_at": r["created_at"],
            })
    return {"admins": admins_list, "owner_id": owner_id}


@app.post("/api/admin/admins/add")
async def admin_admins_add(
    body: AdminAddRequest,
    admin: Dict[str, Any] = Depends(get_admin_user),
):
    owner_id = int(os.environ.get("ADMIN_ID", "0") or 0)
    if body.user_id == owner_id:
        return {"status": "exists", "message": "این کاربر مالک اصلی سیستم است."}

    now = int(time.time())
    conn = _db()
    conn.execute(
        """
        INSERT INTO admins (user_id, role, added_by, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET role = excluded.role
        """,
        (body.user_id, body.role or "ADMIN", admin["id"], now),
    )
    conn.commit()
    conn.close()
    return {"status": "added", "user_id": body.user_id, "message": "مدیر جدید با موفقیت اضافه شد."}


@app.post("/api/admin/admins/remove")
async def admin_admins_remove(
    body: AdminAddRequest,
    _admin: Dict[str, Any] = Depends(get_admin_user),
):
    owner_id = int(os.environ.get("ADMIN_ID", "0") or 0)
    if body.user_id == owner_id:
        raise HTTPException(status_code=400, detail="مالک اصلی سیستم قابل حذف نیست.")

    conn = _db()
    conn.execute("DELETE FROM admins WHERE user_id = ?", (body.user_id,))
    conn.commit()
    conn.close()
    return {"status": "removed", "user_id": body.user_id, "message": "دسترسی مدیریت کاربر حذف شد."}


# ---------------------------------------------------------------------------
# Admin — Backups & Operating Mode
# ---------------------------------------------------------------------------

@app.get("/api/admin/backups")
async def admin_backups_get(_admin: Dict[str, Any] = Depends(get_admin_user)):
    backup_dir = os.path.join(os.path.dirname(_DB_PATH), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    backups = []
    try:
        for entry in os.scandir(backup_dir):
            if entry.is_file() and entry.name.endswith(".db"):
                st = entry.stat()
                backups.append({
                    "name": entry.name,
                    "size_kb": round(st.st_size / 1024, 1),
                    "created_at": int(st.st_mtime),
                })
    except Exception:
        pass
    backups.sort(key=lambda x: x["created_at"], reverse=True)
    return {"backups": backups}


@app.post("/api/admin/backups/create")
async def admin_backups_create(_admin: Dict[str, Any] = Depends(get_admin_user)):
    import sqlite3
    backup_dir = os.path.join(os.path.dirname(_DB_PATH), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    from datetime import datetime
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"manual_{stamp}.db"
    dest_path = os.path.join(backup_dir, backup_filename)

    src_conn = sqlite3.connect(_DB_PATH)
    dest_conn = sqlite3.connect(dest_path)
    src_conn.backup(dest_conn)
    dest_conn.close()
    src_conn.close()

    return {"status": "ok", "filename": backup_filename, "message": f"بکاپ {backup_filename} با موفقیت ایجاد شد."}


@app.get("/api/admin/ops/mode")
async def admin_ops_mode_get(_admin: Dict[str, Any] = Depends(get_admin_user)):
    return {
        "mode": _setting("operating_mode", "NORMAL"),
        "sales_paused_message": _setting("sales_paused_message", ""),
        "maintenance_message": _setting("maintenance_message", ""),
    }


@app.post("/api/admin/ops/mode")
async def admin_ops_mode_post(
    body: AdminOperatingModeRequest,
    _admin: Dict[str, Any] = Depends(get_admin_user),
):
    valid_modes = {"NORMAL", "SALES_PAUSED", "MAINTENANCE"}
    if body.mode not in valid_modes:
        raise HTTPException(status_code=400, detail="حالت کاری نامعتبر است.")
    _update_setting("operating_mode", body.mode)
    return {"status": "saved", "mode": body.mode, "message": f"حالت کاری به {body.mode} تغییر یافت."}


# ---------------------------------------------------------------------------
# Admin — Broadcast
# ---------------------------------------------------------------------------

@app.post("/api/admin/broadcast")
async def admin_broadcast(
    body: BroadcastRequest,
    admin: Dict[str, Any] = Depends(get_admin_user),
):
    import threading
    from . import storage as _storage  # noqa: PLC0415
    from . import core as _core  # noqa: PLC0415

    audience_ids = _storage.audiences(body.audience)
    if not audience_ids:
        return {"status": "no_recipients", "total": 0}

    text = body.message[:4096]  # Telegram limit

    def _send():
        sent = failed = 0
        for uid in audience_ids:
            try:
                _core.bot.send_message(uid, text, parse_mode="HTML")
                sent += 1
            except Exception:
                failed += 1

# ---------------------------------------------------------------------------
# Admin — Sanaei 3x-ui & Groups Management
# ---------------------------------------------------------------------------

@app.get("/api/admin/xui/groups")
async def admin_xui_groups(_admin: Dict[str, Any] = Depends(get_admin_user)):
    """Fetch live groups list from Sanaei 3x-ui panel."""
    try:
        from . import core as _core
        raw_groups = _core._xui_list_groups()
        groups = []
        for g in raw_groups:
            if isinstance(g, dict):
                groups.append({
                    "id": g.get("id"),
                    "name": g.get("name", "")
                })
            elif isinstance(g, str):
                groups.append({"id": None, "name": g})
        return {"groups": groups, "total": len(groups)}
    except Exception as e:
        return {"groups": [], "total": 0, "error": str(e)}


@app.post("/api/admin/xui/groups/reconcile")
async def admin_xui_groups_reconcile(_admin: Dict[str, Any] = Depends(get_admin_user)):
    """Reconcile clients and ensure groups exist on Sanaei 3x-ui."""
    try:
        from . import core as _core
        res = _core.reconcile_service_groups()
        return {"status": "success", "result": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در همگام‌سازی گروه‌ها: {e}")


@app.get("/api/admin/xui/test")
async def admin_xui_test(_admin: Dict[str, Any] = Depends(get_admin_user)):
    """Run diagnostic checks against 3x-ui API."""
    try:
        from . import core as _core
        output = _core._run_xui_diagnostic()
        return {"result": output}
    except Exception as e:
        return {"result": f"❌ خطا: {e}"}


@app.post("/api/admin/xui/replace-domain")
async def admin_xui_replace_domain(body: ReplaceDomainRequest, _admin: Dict[str, Any] = Depends(get_admin_user)):
    """Replace domain string across DB settings and .env."""
    try:
        from . import core as _core
        ok, msg = _core.replace_domain_in_all_configs(body.old_domain, body.new_domain)
        if not ok:
            raise HTTPException(status_code=400, detail=msg)
        return {"status": "success", "message": msg}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/xui/delete-client")
async def admin_xui_delete_client(body: DeleteClientRequest, _admin: Dict[str, Any] = Depends(get_admin_user)):
    """Delete a client subscription directly from Sanaei panel."""
    from urllib.parse import quote
    import requests
    email = body.email.strip()
    if not email:
        raise HTTPException(status_code=400, detail="ایمیل کلاینت الزامی است.")
    try:
        from . import core as _core
        del_url = _core._xui_url(f"panel/api/clients/del/{quote(str(email), safe='')}") + "?keepTraffic=0"
        res = requests.post(
            del_url,
            headers=_core._xui_headers(),
            proxies=_core._xui_proxies(),
            timeout=15,
            verify=not _core.DEVELOPMENT_MODE
        )
        data = _core._safe_json(res)
        if res.status_code == 200 and data.get("success"):
            return {"status": "success", "message": f"اشتراک {email} با موفقیت از پنل حذف شد."}
        else:
            raise HTTPException(status_code=400, detail=data.get("msg") or res.text or "خطای پنل")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Admin — Rewards (Cashback, Discounts, Gifts)
# ---------------------------------------------------------------------------

@app.get("/api/admin/rewards")
async def admin_get_rewards(_admin: Dict[str, Any] = Depends(get_admin_user)):
    conn = _db()
    cashback = float(_setting("cashback_percent", "0") or 0)
    discounts = conn.execute("SELECT * FROM discount_codes ORDER BY created_at DESC").fetchall()
    gifts = conn.execute("SELECT * FROM gift_codes ORDER BY created_at DESC").fetchall()
    conn.close()
    return {
        "cashback_percent": cashback,
        "discount_codes": [
            {
                "code": d["code"],
                "discount_type": d["discount_type"],
                "value": float(d["value"]),
                "min_purchase": int(d["min_purchase"] or 0),
                "max_uses": int(d["max_uses"] or 0),
                "per_user_limit": int(d["per_user_limit"] or 1),
                "expires_at": d["expires_at"],
                "active": bool(d["active"]),
                "created_at": d["created_at"],
            }
            for d in discounts
        ],
        "gift_codes": [
            {
                "code": g["code"],
                "amount": int(g["amount"]),
                "max_uses": int(g["max_uses"] or 1),
                "expires_at": g["expires_at"],
                "active": bool(g["active"]),
                "created_at": g["created_at"],
            }
            for g in gifts
        ]
    }


@app.post("/api/admin/rewards/cashback")
async def admin_set_cashback(body: CashbackUpdateRequest, _admin: Dict[str, Any] = Depends(get_admin_user)):
    _update_setting("cashback_percent", f"{body.percent:g}")
    return {"status": "saved", "cashback_percent": body.percent}


@app.post("/api/admin/rewards/discounts")
async def admin_create_discount(body: CreateDiscountRequest, _admin: Dict[str, Any] = Depends(get_admin_user)):
    code = body.code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="کد تخفیف الزامی است.")
    dtype = body.discount_type.upper()
    if dtype not in ("PERCENT", "FIXED"):
        raise HTTPException(status_code=400, detail="نوع تخفیف باید PERCENT یا FIXED باشد.")
    now = int(time.time())
    conn = _db()
    conn.execute(
        """
        INSERT OR REPLACE INTO discount_codes (code, discount_type, value, min_purchase, max_uses, per_user_limit, expires_at, active, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
        """,
        (code, dtype, body.value, body.min_purchase, body.max_uses, body.per_user_limit, body.expires_at, now)
    )
    conn.commit()
    conn.close()
    return {"status": "created", "code": code}


@app.delete("/api/admin/rewards/discounts/{code}")
async def admin_delete_discount(code: str, _admin: Dict[str, Any] = Depends(get_admin_user)):
    conn = _db()
    conn.execute("DELETE FROM discount_codes WHERE code = ? COLLATE NOCASE", (code.strip(),))
    conn.commit()
    conn.close()
    return {"status": "deleted", "code": code}


@app.post("/api/admin/rewards/gifts")
async def admin_create_gift(body: CreateGiftRequest, _admin: Dict[str, Any] = Depends(get_admin_user)):
    code = body.code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="کد هدیه الزامی است.")
    now = int(time.time())
    conn = _db()
    conn.execute(
        """
        INSERT OR REPLACE INTO gift_codes (code, amount, max_uses, expires_at, active, created_at)
        VALUES (?, ?, ?, ?, 1, ?)
        """,
        (code, body.amount, body.max_uses, body.expires_at, now)
    )
    conn.commit()
    conn.close()
    return {"status": "created", "code": code}


@app.delete("/api/admin/rewards/gifts/{code}")
async def admin_delete_gift(code: str, _admin: Dict[str, Any] = Depends(get_admin_user)):
    conn = _db()
    conn.execute("DELETE FROM gift_codes WHERE code = ? COLLATE NOCASE", (code.strip(),))
    conn.commit()
    conn.close()
    return {"status": "deleted", "code": code}


# ---------------------------------------------------------------------------
# Admin — Affiliate & Referrals
# ---------------------------------------------------------------------------

@app.get("/api/admin/affiliate")
async def admin_get_affiliate(_admin: Dict[str, Any] = Depends(get_admin_user)):
    conn = _db()
    enabled = _setting("referral_enabled", "1") == "1"
    percent = float(_setting("referral_commission_percent", "10") or 10)
    referrals_count = conn.execute("SELECT COUNT(*) AS c FROM users WHERE referred_by IS NOT NULL").fetchone()["c"]
    commissions_count = conn.execute("SELECT COUNT(*) AS c FROM referral_commissions").fetchone()["c"]
    commissions_sum = conn.execute("SELECT COALESCE(SUM(commission_amount),0) AS s FROM referral_commissions").fetchone()["s"]
    wallet_total = conn.execute("SELECT COALESCE(SUM(balance),0) AS s FROM users").fetchone()["s"]
    top_rows = conn.execute(
        """SELECT referrer_id, COUNT(DISTINCT referred_id) AS buyers, SUM(commission_amount) AS earned
           FROM referral_commissions GROUP BY referrer_id ORDER BY earned DESC LIMIT 10"""
    ).fetchall()
    conn.close()
    return {
        "enabled": enabled,
        "percent": percent,
        "total_referrals": int(referrals_count),
        "total_commissions_count": int(commissions_count),
        "total_commissions_amount": int(commissions_sum),
        "total_wallet_balance": int(wallet_total),
        "top_referrers": [
            {
                "referrer_id": r["referrer_id"],
                "buyers": int(r["buyers"]),
                "earned": int(r["earned"] or 0)
            }
            for r in top_rows
        ]
    }


@app.post("/api/admin/affiliate/settings")
async def admin_save_affiliate(body: AffiliateSettingsRequest, _admin: Dict[str, Any] = Depends(get_admin_user)):
    if body.enabled is not None:
        _update_setting("referral_enabled", "1" if body.enabled else "0")
    if body.percent is not None:
        _update_setting("referral_commission_percent", f"{body.percent:g}")
    return {"status": "saved"}


# ---------------------------------------------------------------------------
# Admin — Content, Security & Notifications
# ---------------------------------------------------------------------------

@app.get("/api/admin/content-security")
async def admin_get_content_security(_admin: Dict[str, Any] = Depends(get_admin_user)):
    return {
        "welcome_text": _setting("welcome_text", ""),
        "faq_text": _setting("faq_text", ""),
        "phone_verification_required": _setting("phone_verification_required", "0") == "1",
        "membership_required": _setting("membership_required", "0") == "1",
        "required_channel": _setting("required_channel", ""),
        "required_channel_url": _setting("required_channel_url", ""),
        "service_notifications_enabled": _setting("service_notifications_enabled", "1") == "1",
        "service_volume_warning_percent": int(_setting("service_volume_warning_percent", "90") or 90),
        "service_expiry_warning_hours": int(_setting("service_expiry_warning_hours", "24") or 24),
    }


@app.post("/api/admin/content-security")
async def admin_save_content_security(body: ContentSecurityRequest, _admin: Dict[str, Any] = Depends(get_admin_user)):
    if body.welcome_text is not None:
        _update_setting("welcome_text", body.welcome_text.strip())
    if body.faq_text is not None:
        _update_setting("faq_text", body.faq_text.strip())
    if body.phone_verification_required is not None:
        _update_setting("phone_verification_required", "1" if body.phone_verification_required else "0")
    if body.membership_required is not None:
        _update_setting("membership_required", "1" if body.membership_required else "0")
    if body.required_channel is not None:
        _update_setting("required_channel", body.required_channel.strip())
    if body.required_channel_url is not None:
        _update_setting("required_channel_url", body.required_channel_url.strip())
    if body.service_notifications_enabled is not None:
        _update_setting("service_notifications_enabled", "1" if body.service_notifications_enabled else "0")
    if body.service_volume_warning_percent is not None:
        _update_setting("service_volume_warning_percent", str(body.service_volume_warning_percent))
    if body.service_expiry_warning_hours is not None:
        _update_setting("service_expiry_warning_hours", str(body.service_expiry_warning_hours))
    return {"status": "saved"}


# ---------------------------------------------------------------------------
# Static file serving (Vue SPA)
# ---------------------------------------------------------------------------

_WEBAPP_DIST = os.path.join(os.path.dirname(os.path.dirname(__file__)), "webapp", "dist")


def _mount_static():
    """Mount static assets and handle SPA client-side routing."""
    assets_dir = os.path.join(_WEBAPP_DIST, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/", include_in_schema=False)
    async def spa_root():
        index_file = os.path.join(_WEBAPP_DIST, "index.html")
        if os.path.isfile(index_file):
            return FileResponse(index_file)
        return JSONResponse({"message": "Mini App API is running. Build the webapp to serve the Mini App."})

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        # API routes are handled by FastAPI routers above
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        fp = os.path.join(_WEBAPP_DIST, full_path)
        if os.path.isfile(fp):
            return FileResponse(fp)
        index_file = os.path.join(_WEBAPP_DIST, "index.html")
        if os.path.isfile(index_file):
            return FileResponse(index_file)
        return JSONResponse({"message": "Mini App API is running. Build the webapp to serve the Mini App."})


_mount_static()
