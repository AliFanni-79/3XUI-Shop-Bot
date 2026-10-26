#!/usr/bin/env python3
"""
Import Porsline survey respondents as stepped discount codes.

Porsline API endpoint:
https://survey.porsline.ir/api/v2/surveys/{survey_id}/responses/results-table/

Discount rules applied:
- Step 1 (1st use): 100% discount
- Step 2 (2nd use): 50% discount
- Step 3+ (3rd use onwards): 25% discount (repeat_after = True, up to max_uses)
- Validity / Expiration: 6 months (180 days)
- Max uses: 10 maximum (max_uses = 10, per_user_limit = 10)
- Identifier: responder_code (e.g. CqyRa)
- Target: Direct DB query (least overhead)
"""

import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Set, Tuple

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

DEFAULT_PORSLINE_TOKEN = "5bf19a2541c51e30c8a2fb88009f50f235ae3c01"
DEFAULT_SURVEY_ID = 2682416
DEFAULT_DB_PATH = "app.db"
DEFAULT_DAYS = 180  # 6 months
DEFAULT_MAX_USES = 10  # 10 maximum uses (no unlimited usage)


def fetch_porsline_responses(
    survey_id: int = DEFAULT_SURVEY_ID,
    api_token: str = DEFAULT_PORSLINE_TOKEN,
    page_size: int = 1000,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Fetch all respondent rows from Porsline results table API without requiring

    a professional subscription.
    """
    base_url = f"https://survey.porsline.ir/api/v2/surveys/{survey_id}/responses/results-table/"
    headers = {
        "Authorization": f"API-Key {api_token.strip()}",
        "User-Agent": "XUIShop-Porsline-Importer/1.0",
        "Accept": "application/json",
    }

    all_bodies: List[Dict[str, Any]] = []
    meta_info: Dict[str, Any] = {}
    page = 1

    while True:
        url = f"{base_url}?page_size={page_size}&page={page}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"HTTP Error {resp.status} fetching page {page} from Porsline")
                content = resp.read().decode("utf-8")
                data = json.loads(content)
        except urllib.error.HTTPError as err:
            err_msg = err.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Porsline API HTTP {err.code}: {err_msg}") from err
        except Exception as exc:
            raise RuntimeError(f"Failed to connect to Porsline API: {exc}") from exc

        if not meta_info:
            meta_info = {
                "responders_count": data.get("responders_count", 0),
                "invisible_responders_count": data.get("invisible_responders_count", 0),
                "headers": data.get("header", []),
            }

        body = data.get("body", [])
        if not body:
            break

        all_bodies.extend(body)

        total_expected = meta_info.get("responders_count", 0)
        if total_expected and len(all_bodies) >= total_expected:
            break

        if len(body) < page_size:
            break

        page += 1

    return all_bodies, meta_info


def extract_identifiers(
    responses: List[Dict[str, Any]],
    mode: str = "code",
) -> List[Dict[str, Any]]:
    """Extract responder codes, IDs, or both from response body items.

    mode:
      - 'code': extract responder_code (e.g. CqyRa) [default]
      - 'id': extract responder_id (e.g. 566319380)
      - 'both': extract both as separate discount codes
    """
    records: List[Dict[str, Any]] = []
    seen_codes: Set[str] = set()

    for item in responses:
        r_code = str(item.get("responder_code") or "").strip()
        r_id = item.get("responder_id")

        if mode in ("code", "both") and r_code:
            norm_code = r_code.upper()
            if norm_code not in seen_codes:
                seen_codes.add(norm_code)
                records.append({
                    "code": norm_code,
                    "raw_code": r_code,
                    "responder_id": r_id,
                    "kind": "responder_code",
                })

        if mode in ("id", "both") and r_id is not None:
            norm_id = str(r_id).strip()
            if norm_id and norm_id not in seen_codes:
                seen_codes.add(norm_id)
                records.append({
                    "code": norm_id,
                    "raw_code": r_code,
                    "responder_id": r_id,
                    "kind": "responder_id",
                })

    return records


def build_stepped_discount_payload(
    code: str,
    days: int = DEFAULT_DAYS,
    max_uses: int = DEFAULT_MAX_USES,
    survey_id: int = DEFAULT_SURVEY_ID,
    responder_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Build record payload for stepped discount:

    - Step 1: 100% discount
    - Step 2: 50% discount
    - Step 3+: 25% discount (repeat_after = True, up to max_uses)
    - 6-month validity (days * 86400)
    - 10 maximum uses (max_uses = 10, per_user_limit = 10)
    """
    now_ts = int(time.time())
    expires_at = now_ts + (days * 86400)

    steps = [
        {
            "step": 1,
            "discount_type": "PERCENT",
            "discount_value": 100.0,
            "cashback_percent": 0.0,
            "repeat_after": False,
            "label": "بار اول: ۱۰۰٪ تخفیف رایگان",
        },
        {
            "step": 2,
            "discount_type": "PERCENT",
            "discount_value": 50.0,
            "cashback_percent": 0.0,
            "repeat_after": False,
            "label": "بار دوم: ۵۰٪ تخفیف",
        },
        {
            "step": 3,
            "discount_type": "PERCENT",
            "discount_value": 25.0,
            "cashback_percent": 0.0,
            "repeat_after": True,
            "label": "بار سوم به بعد: ۲۵٪ تخفیف",
        },
    ]

    limit_val = max(0, int(max_uses))
    extra_info = f" (شناسه پاسخ: {responder_id})" if responder_id else ""
    desc = f"تخفیف پله‌ای ویژه پاسخ‌دهنده پرسلاین{extra_info} - پرسشنامه #{survey_id} (۱۰۰٪، ۵۰٪، ۲۵٪ - حداکثر {limit_val} بار)"

    return {
        "code": code.strip().upper(),
        "discount_type": "PERCENT",
        "value": 100.0,
        "min_purchase": 0,
        "max_uses": limit_val,
        "per_user_limit": limit_val,
        "expires_at": expires_at,
        "active": 1,
        "created_at": now_ts,
        "is_auto": 0,
        "title": "جشنواره پاسخ‌دهندگان پرسلاین",
        "cashback_percent": 0.0,
        "steps_json": json.dumps(steps, ensure_ascii=False),
        "description": desc,
    }


def ensure_db_schema(conn: sqlite3.Connection) -> None:
    """Ensure discount_codes table exists and has all extended columns."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS discount_codes (
            code TEXT PRIMARY KEY,
            discount_type TEXT NOT NULL,
            value REAL NOT NULL,
            min_purchase INTEGER NOT NULL DEFAULT 0,
            max_uses INTEGER NOT NULL DEFAULT 0,
            per_user_limit INTEGER NOT NULL DEFAULT 1,
            expires_at INTEGER,
            active INTEGER NOT NULL DEFAULT 1,
            created_at INTEGER NOT NULL
        )
        """
    )
    cols = {r[1] for r in conn.execute("PRAGMA table_info(discount_codes)").fetchall()}
    if "is_auto" not in cols:
        conn.execute("ALTER TABLE discount_codes ADD COLUMN is_auto INTEGER NOT NULL DEFAULT 0")
    if "title" not in cols:
        conn.execute("ALTER TABLE discount_codes ADD COLUMN title TEXT")
    if "cashback_percent" not in cols:
        conn.execute("ALTER TABLE discount_codes ADD COLUMN cashback_percent REAL NOT NULL DEFAULT 0")
    if "steps_json" not in cols:
        conn.execute("ALTER TABLE discount_codes ADD COLUMN steps_json TEXT")
    if "description" not in cols:
        conn.execute("ALTER TABLE discount_codes ADD COLUMN description TEXT")
    conn.commit()


def save_discounts_to_db(
    discounts: List[Dict[str, Any]],
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    """Insert or update discount codes in SQLite database via direct batch DB query.
    Direct DB query provides the lowest overhead (no network latency or HTTP overhead).
    """
    conn = sqlite3.connect(db_path)
    try:
        ensure_db_schema(conn)
        cursor = conn.cursor()
        sql = """
            INSERT INTO discount_codes (
                code, discount_type, value, min_purchase, max_uses, per_user_limit,
                expires_at, active, created_at, is_auto, title, cashback_percent,
                steps_json, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                discount_type = excluded.discount_type,
                value = excluded.value,
                min_purchase = excluded.min_purchase,
                max_uses = excluded.max_uses,
                per_user_limit = excluded.per_user_limit,
                expires_at = excluded.expires_at,
                active = excluded.active,
                is_auto = excluded.is_auto,
                title = excluded.title,
                cashback_percent = excluded.cashback_percent,
                steps_json = excluded.steps_json,
                description = excluded.description
        """
        rows = [
            (
                d["code"],
                d["discount_type"],
                d["value"],
                d["min_purchase"],
                d["max_uses"],
                d["per_user_limit"],
                d["expires_at"],
                d["active"],
                d["created_at"],
                d["is_auto"],
                d["title"],
                d["cashback_percent"],
                d["steps_json"],
                d["description"],
            )
            for d in discounts
        ]
        cursor.executemany(sql, rows)
        conn.commit()
        return len(rows)
    finally:
        conn.close()


def save_discounts_via_api(
    discounts: List[Dict[str, Any]],
    api_url: str = "http://127.0.0.1:8000",
    admin_token: str = "",
) -> int:
    """Save discount codes via SpeedyBot Admin HTTP API.
    Note: Has higher overhead than direct DB query due to HTTP round-trips and JWT auth.
    """
    if not admin_token:
        raise ValueError("Admin token (--api-token) is required when using API mode")
    headers = {
        "Authorization": f"Bearer {admin_token.strip()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    endpoint = f"{api_url.rstrip('/')}/api/admin/rewards/discounts"
    saved = 0
    for d in discounts:
        steps = json.loads(d.get("steps_json") or "[]")
        payload = {
            "code": d["code"],
            "discount_type": d["discount_type"],
            "value": d["value"],
            "min_purchase": d["min_purchase"],
            "max_uses": d["max_uses"],
            "per_user_limit": d["per_user_limit"],
            "days": max(1, (d["expires_at"] - d["created_at"]) // 86400) if d.get("expires_at") else 0,
            "is_auto": bool(d.get("is_auto")),
            "title": d.get("title") or "",
            "description": d.get("description") or "",
            "cashback_percent": d.get("cashback_percent") or 0.0,
            "steps": steps,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status in (200, 201):
                    saved += 1
        except Exception as exc:
            raise RuntimeError(f"API request failed for code {d['code']}: {exc}") from exc
    return saved


def main():
    parser = argparse.ArgumentParser(
        description="Extract Porsline survey respondents and import them as stepped discount codes."
    )
    parser.add_argument(
        "--token",
        default=os.getenv("PORSLINE_API_TOKEN", DEFAULT_PORSLINE_TOKEN),
        help="Porsline API token",
    )
    parser.add_argument(
        "--survey-id",
        type=int,
        default=int(os.getenv("PORSLINE_SURVEY_ID", DEFAULT_SURVEY_ID)),
        help="Porsline Survey ID",
    )
    parser.add_argument(
        "--mode",
        choices=["code", "id", "both"],
        default="code",
        help="Identifier type to import: 'code' (responder_code e.g. CqyRa) [default], 'id' (numeric responder_id), or 'both'",
    )
    parser.add_argument(
        "--max-uses",
        type=int,
        default=DEFAULT_MAX_USES,
        help="Maximum uses allowed per discount code (default: 10, no unlimited usage)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_DAYS,
        help="Discount code validity in days (default: 180 = 6 months)",
    )
    parser.add_argument(
        "--target",
        choices=["db", "api"],
        default="db",
        help="Import destination: 'db' for direct SQLite query (least overhead) [default], or 'api' for SpeedyBot Admin REST API",
    )
    parser.add_argument(
        "--db-path",
        default=os.getenv("DATABASE_PATH", DEFAULT_DB_PATH),
        help="Path to SQLite database for direct DB query (default: app.db)",
    )
    parser.add_argument(
        "--api-url",
        default=os.getenv("SPEEDYBOT_API_URL", "http://127.0.0.1:8000"),
        help="SpeedyBot API base URL (used when --target=api, default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--api-token",
        default=os.getenv("SPEEDYBOT_ADMIN_TOKEN", ""),
        help="Admin JWT token for SpeedyBot API (required when --target=api)",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Only display fetched respondent identifiers without writing to database",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate database import without making persistent changes",
    )

    args = parser.parse_args()

    print("================================================================")
    print(" 🚀 استخراج شناسه‌های پاسخ‌دهندگان پرسلاین و تبدیل به کد تخفیف پله‌ای")
    print("================================================================")
    print(f"📌 شماره پرسشنامه (Survey ID): {args.survey_id}")
    print(f"🔑 توکن ارتباطی: {args.token[:8]}...{args.token[-6:]}")
    print(f"⚙️ حالت شناسه‌ها (Mode): {args.mode} (فقط responder_code)")
    print(f"⏳ مهلت استفاده: {args.days} روز (۶ ماه)")
    print(f"🔢 حداکثر دفعات استفاده: {args.max_uses} بار (بدون استفاده نامحدود)")
    if args.target == "db":
        print(f"🗄 روش ذخیره‌سازی: Direct DB Query با کمترین سربار (مسیر: {args.db_path})")
    else:
        print(f"🌐 روش ذخیره‌سازی: HTTP Admin API (آدرس: {args.api_url})")
    print("----------------------------------------------------------------")

    # 1. Fetch from Porsline
    print("📡 در حال دریافت پاسخ‌ها از API پرسلاین بدون نیاز به اشتراک حرفه‌ای...")
    try:
        responses, meta = fetch_porsline_responses(survey_id=args.survey_id, api_token=args.token)
    except Exception as exc:
        print(f"❌ خطا در اتصال به پرسلاین: {exc}", file=sys.stderr)
        sys.exit(1)

    total_responders = meta.get("responders_count", len(responses))
    print(f"✅ با موفقیت {len(responses)} پاسخ از مجموع {total_responders} پاسخ‌دهنده دریافت شد.")

    # 2. Extract identifiers
    identifiers = extract_identifiers(responses, mode=args.mode)
    print(f"📋 تعداد کل شناسه‌های استخراج‌شده برای ایجاد کد تخفیف: {len(identifiers)}")
    print("\n🔍 نمونه شناسه‌های استخراج‌شده:")
    for i, it in enumerate(identifiers[:10], 1):
        print(f"  {i}. کد تخفیف: {it['code']} (نوع: {it['kind']} | کد اصلی: {it['raw_code']} | شناسه عددی: {it['responder_id']})")
    if len(identifiers) > 10:
        print(f"  ... و {len(identifiers) - 10} شناسه دیگر.")

    if args.list_only:
        print("\n🏁 عملیات بر اساس گزینه --list-only خاتمه یافت (هیچ تغییری در دیتابیس ثبت نشد).")
        return

    # 3. Build discount payloads
    discounts = [
        build_stepped_discount_payload(
            code=it["code"],
            days=args.days,
            max_uses=args.max_uses,
            survey_id=args.survey_id,
            responder_id=it.get("responder_id"),
        )
        for it in identifiers
    ]

    print("\n📊 ساختار تخفیف پلکانی تنظیم‌شده:")
    print("  • مرحله ۱ (خرید اول): ۱۰۰٪ تخفیف رایگان")
    print("  • مرحله ۲ (خرید دوم): ۵۰٪ تخفیف")
    print("  • مرحله ۳ به بعد (خرید سوم و دفعات بعد): ۲۵٪ تخفیف")
    print(f"  • مهلت استفاده: {args.days} روز")
    print(f"  • محدودیت سقف استفاده: حداکثر {args.max_uses} بار")

    # 4. Save to Database or API
    if args.dry_run:
        print(f"\n⚠️ حالت آزمایشی (--dry-run): {len(discounts)} رکورد آماده ثبت بود اما در دیتابیس ذخیره نشد.")
    else:
        if args.target == "db":
            print(f"\n💾 در حال درج/بروزرسانی مستقیم {len(discounts)} کد تخفیف در دیتابیس '{args.db_path}' (Direct DB Query - کمترین سربار)...")
            saved_count = save_discounts_to_db(discounts, db_path=args.db_path)
            print(f"🎉 عملیات با موفقیت انجام شد! {saved_count} کد تخفیف پلکانی در دیتابیس ذخیره گردید.")
        else:
            print(f"\n🌐 در حال ارسال {len(discounts)} کد تخفیف از طریق API به '{args.api_url}'...")
            saved_count = save_discounts_via_api(discounts, api_url=args.api_url, admin_token=args.api_token)
            print(f"🎉 عملیات با موفقیت انجام شد! {saved_count} کد تخفیف پلکانی از طریق API ثبت گردید.")

    print("================================================================")


if __name__ == "__main__":
    main()
