import html
import time
from typing import Any, Dict, Optional, Tuple

from . import context as C

MONTH_SECONDS = 30 * 86400  # Each user can receive trial once every 30 days (once a month)


def override(uid: int):
    if C.setting("trial_overrides_enabled", "1") != "1":
        return None
    c = C.db()
    row = c.execute("SELECT * FROM trial_overrides WHERE user_id=?", (int(uid),)).fetchone()
    c.close()
    return row


def default_values() -> Tuple[float, int, int]:
    try:
        gb = max(0.05, min(1024.0, float(C.setting("trial_default_volume_gb", "0.3"))))
    except Exception:
        gb = 0.3
    try:
        days = max(1, min(365, int(float(C.setting("trial_default_days", "1")))))
    except Exception:
        days = 1
    try:
        ip = max(0, min(50, int(float(C.setting("trial_default_ip_limit", "0")))))
    except Exception:
        ip = 0
    return gb, days, ip


def values(uid: int) -> Tuple[float, int, int, bool]:
    ov = override(uid)
    if ov:
        return (
            max(0.05, min(1024.0, float(ov["volume_gb"]))),
            max(1, min(365, int(ov["days"]))),
            max(0, min(50, int(ov["ip_limit"]))),
            True,
        )
    gb, days, ip = default_values()
    return gb, days, ip, False


def get_trial_eligibility(uid: int, conn=None) -> Tuple[bool, int, int, str]:
    """Check if user can claim monthly free trial.

    Returns:
        (eligible: bool, remaining_days: int, last_activated_ts: int, status: str)
    """
    close_after = False
    if conn is None:
        conn = C.db()
        close_after = True
    try:
        row = conn.execute(
            "SELECT status, created_at, activated_at FROM trial_services WHERE user_id=?",
            (int(uid),)
        ).fetchone()
        if not row:
            return True, 0, 0, "NONE"
        status = row["status"] if hasattr(row, "keys") else row[0]
        if status == "FAILED":
            return True, 0, 0, "FAILED"
        if status == "CREATING":
            return False, 0, int((row["created_at"] if hasattr(row, "keys") else row[1]) or 0), "CREATING"

        created_at = int((row["created_at"] if hasattr(row, "keys") else row[1]) or 0)
        activated_at = int((row["activated_at"] if hasattr(row, "keys") else row[2]) or 0)
        last_ts = activated_at or created_at or 0
        now = int(time.time())
        diff = now - last_ts
        if diff >= MONTH_SECONDS:
            return True, 0, last_ts, status

        rem_days = max(1, int((MONTH_SECONDS - diff + 86399) // 86400))
        return False, rem_days, last_ts, status
    finally:
        if close_after and conn:
            conn.close()


def generate(uid: int, email: str, custom_name: Optional[str] = None) -> Dict[str, Any]:
    gb, days, ip, is_override = values(uid)
    headers = C.CORE._xui_headers()
    proxies = C.CORE._xui_proxies()
    try:
        desired = C.CORE._selected_inbound_ids_for("trial", None, headers, proxies)
        client = C.CORE._get_client_data(email, headers, proxies)
        if not client:
            payload = {
                "client": {
                    "email": email,
                    "totalGB": int(gb * 1024**3),
                    "expiryTime": int((time.time() + days * 86400) * 1000),
                    "tgId": int(uid),
                    "limitIp": ip,
                    "enable": True,
                },
                "inboundIds": desired,
            }
            response = C.CORE.requests.post(
                C.CORE._xui_url("panel/api/clients/add"),
                json=payload,
                headers=headers,
                proxies=proxies,
                timeout=15,
                verify=not C.CORE.DEVELOPMENT_MODE,
            )
            data = C.CORE._safe_json(response)
            if response.status_code != 200 or not data.get("success"):
                raise RuntimeError(C.CORE._xui_response_error(response, "پنل ساخت تست رایگان را رد کرد"))
            time.sleep(1)
            client = C.CORE._get_client_data(email, headers, proxies)

        if client:
            # If client was already present on 3x-ui, reset consumed traffic & renew expiry
            try:
                C.CORE.requests.post(
                    C.CORE._xui_url(f"panel/api/clients/resetTraffic/{email}"),
                    headers=headers,
                    proxies=proxies,
                    timeout=10,
                    verify=not C.CORE.DEVELOPMENT_MODE,
                )
            except Exception:
                pass

            update_payload = {
                "client": {
                    "email": email,
                    "totalGB": int(gb * 1024**3),
                    "expiryTime": int((time.time() + days * 86400) * 1000),
                    "tgId": int(uid),
                    "limitIp": ip,
                    "enable": True,
                },
                "inboundIds": desired,
            }
            try:
                C.CORE.requests.post(
                    C.CORE._xui_url(f"panel/api/clients/update/{email}"),
                    json=update_payload,
                    headers=headers,
                    proxies=proxies,
                    timeout=15,
                    verify=not C.CORE.DEVELOPMENT_MODE,
                )
            except Exception:
                pass

            C.CORE._sync_client_inbounds(email, desired)
            client = C.CORE._get_client_data(email, headers, proxies) or client

        sub = C.CORE._get_client_subscription_id(email, headers, proxies, client)
        links = C.CORE._get_delivery_links(email, sub, headers, proxies)
        if not sub and not links:
            raise RuntimeError("هیچ لینک تحویلی از پنل برنگشت.")

        try:
            C.CORE._xui_assign_group(email, C.setting("xui_trial_group", "Trial") or "Trial")
        except Exception as group_error:
            C.CORE.notify_admins(
                f"⚠️ تست {email} ساخته شد اما عضویت Group Trial خطا داد: {str(group_error)[:350]}"
            )

        C.CORE._mark_trial(uid, "ACTIVE")
        # Store sub_id into trial_services
        try:
            c = C.db()
            c.execute("UPDATE trial_services SET sub_id=? WHERE user_id=?", (sub or "", uid))
            c.commit()
            c.close()
        except Exception:
            pass

    except Exception as exc:
        C.CORE._mark_trial(uid, "FAILED", exc)
        try:
            C.BOT.send_message(
                uid,
                "❌ صدور تست رایگان خطا داد؛ درخواست مصرف‌شده حساب نشد و می‌توانید دوباره تلاش کنید.",
                reply_markup=C.CORE.main_menu(),
            )
        except Exception:
            pass
        C.CORE.notify_admins(f"🚨 خطا در صدور تست {uid}: {str(exc)[:700]}")
        return {"success": False, "error": str(exc)}

    vol_label = "300 مگابایت" if abs(gb - 0.3) < 0.05 else f"{gb:g} GB"
    ip_label = "نامحدود" if not ip else f"{ip} کاربر"
    title = "تست اختصاصی" if is_override else "تست رایگان ۱ روزه"
    text = (
        f"🎁 <b>{title} فعال شد</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        f"📦 حجم: <b>{vol_label}</b>\n"
        f"⏱ اعتبار: <b>{days} روز</b>\n"
        f"👥 کاربر: <b>{ip_label}</b>\n"
    )
    if sub:
        text += f"\n🌐 <b>Subscription</b>\n<code>{html.escape(C.CORE._subscription_url(sub))}</code>\n"
    if links:
        text += "\n🔑 <b>Direct configs</b>\n" + "\n".join(
            f"<code>{html.escape(link)}</code>" for link in links
        )
    try:
        C.BOT.send_message(uid, text, parse_mode="HTML", reply_markup=C.CORE.main_menu())
        C.CORE._send_guide_cta(uid)
    except Exception:
        pass
    C.audit(
        "TRIAL_ISSUED",
        uid,
        email,
        f"{gb:g}GB/{days}d/ip={ip}/override={1 if is_override else 0}",
    )
    return {
        "success": True,
        "email": email,
        "sub_id": sub,
        "sub_url": C.CORE._subscription_url(sub) if sub else None,
        "links": links or [],
        "days": days,
        "volume_gb": gb,
        "ip_limit": ip,
    }


def issue_trial_for_user(uid: int, custom_name: Optional[str] = None) -> Dict[str, Any]:
    """Issue or renew monthly free trial (1 day, 300MB, unlimited users)."""
    if not C.CORE.trial_enabled():
        return {"success": False, "error": "دریافت تست رایگان در حال حاضر توسط مدیریت غیرفعال شده است."}
    if not C.CORE.purchase_gate(uid):
        return {"success": False, "error": "دسترسی این حساب برای دریافت خدمات محدود شده است."}

    eligible, rem_days, _, status = get_trial_eligibility(uid)
    if not eligible:
        if status == "CREATING":
            return {"success": False, "error": "درخواست تست شما قبلاً ثبت شده و در حال صدور است."}
        return {
            "success": False,
            "error": f"شما در این ماه از تست رایگان استفاده کرده‌اید. امکان دریافت مجدد تا {rem_days} روز دیگر وجود ندارد."
        }

    from .db import resolve_unique_service_email, get_brand_slug
    c = C.db()
    try:
        c.execute("BEGIN IMMEDIATE")
        row = c.execute("SELECT status, email FROM trial_services WHERE user_id=?", (uid,)).fetchone()
        desired = custom_name.strip() if custom_name and custom_name.strip() else None
        service_email = resolve_unique_service_email(desired or f"{get_brand_slug()}_trial_{uid}", user_id=uid, conn=c)
        now = int(time.time())
        if row:
            c.execute(
                "UPDATE trial_services SET email=?, status='CREATING', last_error=NULL, created_at=? WHERE user_id=?",
                (service_email, now, uid)
            )
        else:
            c.execute(
                "INSERT INTO trial_services(user_id, email, status, created_at) VALUES (?, ?, 'CREATING', ?)",
                (uid, service_email, now)
            )
        c.commit()
    except Exception as exc:
        c.rollback()
        return {"success": False, "error": f"خطا در ثبت درخواست تست رایگان: {exc}"}
    finally:
        c.close()

    return generate(uid, service_email, custom_name=custom_name)


def request(message):
    """Handle the Trial button with dynamic global/per-user settings."""
    try:
        C.CORE.USER_STATES[message.chat.id] = None
    except Exception:
        pass
    uid = int(message.from_user.id)
    if not C.CORE.trial_enabled():
        C.BOT.send_message(
            message.chat.id,
            "⛔️ دریافت تست رایگان در حال حاضر توسط مدیریت غیرفعال شده است.",
            reply_markup=C.CORE.main_menu(),
        )
        return
    if not C.CORE.purchase_gate(uid):
        return

    eligible, rem_days, _, status = get_trial_eligibility(uid)
    if not eligible:
        if status == "CREATING":
            text = "⏳ درخواست تست شما قبلاً ثبت شده و در حال صدور است."
        else:
            text = f"🎁 هر کاربر می‌تواند هر ۳۰ روز (یک‌بار در ماه) تست رایگان دریافت کند.\n⏱ زمان باقی‌مانده تا دریافت بعدی: **{rem_days} روز**"
        C.BOT.send_message(message.chat.id, text, reply_markup=C.CORE.main_menu(), parse_mode="Markdown")
        return

    gb, days, ip, is_override = values(uid)
    vol_label = "300 مگابایت" if abs(gb - 0.3) < 0.05 else f"{gb:g} GB"
    ip_label = "نامحدود" if not ip else f"{ip} کاربر"
    label = "تنظیم اختصاصی شما" if is_override else "تست رایگان ماهانه"
    C.BOT.send_message(
        message.chat.id,
        "⚡️ در حال ساخت تست رایگان شما هستم...\n\n"
        f"📦 حجم: <b>{vol_label}</b>\n"
        f"⏱ اعتبار: <b>{days} روز</b>\n"
        f"👥 کاربر: <b>{ip_label}</b>\n"
        f"⚙️ {label}",
        parse_mode="HTML",
        reply_markup=C.CORE.main_menu(),
    )
    issue_trial_for_user(uid)


def register():
    C.BOT.message_handler(func=lambda m: m.text == "🎁 دریافت تست رایگان")(request)
    C.promote_message()
