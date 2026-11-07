"""In-chat interactive HTML5 widget (HTMLBubble) and companion service portal.

Provides an interactive in-chat card with state machine:
- Multi-service list view with pagination (Next/Prev)
- Detail view with visual progress bar, usage stats, days left, IP limits
- QR code display with instant switch and back buttons
- 5-second cooldown live refresh button
- Empty state with trial claim and store shortcuts
- Smart fallback for older Telegram clients (Compact WebApp / Inline rich message)
"""
from __future__ import annotations

import base64
import html
import json
import os
import time
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import requests

from telebot import types

from . import context as C

try:
    import qrcode
except ImportError:
    qrcode = None


def generate_qr_data_uri(text: str) -> str:
    """Generate a base64-encoded PNG data URI for a QR code."""
    if not text or not qrcode:
        return ""
    try:
        img = qrcode.make(text)
        buf = BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return ""


def build_services_payload(user_id: int) -> Dict[str, Any]:
    """Gather all service data, live 3x-ui statistics, and trial eligibility for user_id."""
    uid = int(user_id)
    conn = C.db()
    
    # 1. Fetch user balance & brand info
    user_row = conn.execute("SELECT balance FROM users WHERE id=?", (uid,)).fetchone()
    balance = int(user_row["balance"] or 0) if user_row else 0
    brand_name = C.brand_name() or "SpeedyBot"
    
    # 2. Check trial eligibility
    trial_eligible = False
    try:
        from . import trial
        eligible, _, _, _ = trial.get_trial_eligibility(uid, conn)
        trial_eligible = bool(eligible)
    except Exception:
        trial_eligible = False
        
    # 3. Query approved transactions
    paid_rows = conn.execute(
        """SELECT id, service_email, plan_name_snapshot, sub_id 
           FROM transactions 
           WHERE user_id=? AND UPPER(status)='APPROVED' 
             AND (kind IS NULL OR UPPER(kind) IN ('NEW','CUSTOM','SERVICE','')) 
           ORDER BY id DESC""",
        (uid,)
    ).fetchall()
    
    # 4. Query trial service
    trial_row = conn.execute(
        "SELECT user_id, email, status, sub_id FROM trial_services WHERE user_id=? ORDER BY created_at DESC LIMIT 1",
        (uid,)
    ).fetchone()
    
    # 5. Query linked services
    linked_rows = conn.execute(
        "SELECT id, email FROM linked_services WHERE user_id=? ORDER BY id DESC",
        (uid,)
    ).fetchall()
    conn.close()

    # 6. Resolve sub format & headers
    headers = C.CORE._xui_headers() if hasattr(C.CORE, "_xui_headers") else {}
    proxies = C.CORE._xui_proxies() if hasattr(C.CORE, "_xui_proxies") else None
    dev_mode = getattr(C.CORE, "DEVELOPMENT_MODE", False)
    
    services: List[Dict[str, Any]] = []

    def fetch_live_data(email: str, tx_id: Optional[int] = None, sub_id: Optional[str] = None, title: str = "", kind: str = "paid"):
        if not email:
            return
        client_data: Dict[str, Any] = {}
        traffic_data: Dict[str, Any] = {}
        try:
            c_url = C.CORE._xui_url(f"panel/api/clients/get/{quote(str(email), safe='')}")
            res = requests.get(c_url, headers=headers, proxies=proxies, timeout=5, verify=not dev_mode)
            if res.status_code == 200 and res.json().get("success"):
                client_data = res.json().get("obj", {}) or {}
                
            t_url = C.CORE._xui_url(f"panel/api/clients/traffic/{quote(str(email), safe='')}")
            res_t = requests.get(t_url, headers=headers, proxies=proxies, timeout=5, verify=not dev_mode)
            if res_t.status_code == 200 and res_t.json().get("success"):
                traffic_data = res_t.json().get("obj", {}) or {}
        except Exception:
            pass

        data = {**client_data, **traffic_data}
        
        # Calculate usage
        up_bytes = int(data.get("up", 0) or 0)
        down_bytes = int(data.get("down", 0) or 0)
        total_used_gb = round((up_bytes + down_bytes) / (1024 ** 3), 2)
        
        total_bytes = int(data.get("total", 0) or data.get("totalGB", 0) or 0)
        is_unlimited = (total_bytes == 0)
        total_gb = round(total_bytes / (1024 ** 3), 2) if not is_unlimited else 0.0
        
        usage_pct = 0
        if not is_unlimited and total_gb > 0:
            usage_pct = min(100, int(round((total_used_gb / total_gb) * 100)))
            
        remaining_gb = max(0.0, round(total_gb - total_used_gb, 2)) if not is_unlimited else 0.0
        
        # Calculate expiry
        expiry_ms = int(data.get("expiryTime", 0) or 0)
        now_ms = int(time.time() * 1000)
        is_expired = False
        time_left_str = "بدون محدودیتزمانی"
        days_left = 999
        
        if expiry_ms > 0:
            if expiry_ms < now_ms:
                is_expired = True
                days_left = 0
                time_left_str = "منقضی شده"
            else:
                diff_sec = (expiry_ms - now_ms) / 1000
                days_left = int(diff_sec // 86400)
                hours_left = int((diff_sec % 86400) // 3600)
                time_left_str = f"{days_left} روز و {hours_left} ساعت"
                
        # Resolve subscription URLs
        sub_info = C.CORE.get_client_sub_urls(email, sub_id) if hasattr(C.CORE, "get_client_sub_urls") else {}
        active_sub_url = sub_info.get("active_url") or ""
        sub_format = sub_info.get("format") or "normal"
        
        qr_uri = generate_qr_data_uri(active_sub_url) if active_sub_url else ""
        
        ip_limit = int(data.get("limitIp", 0) or data.get("limit_ip", 0) or 0)
        is_active = bool(data.get("enable", True)) and not is_expired

        services.append({
            "id": tx_id or email,
            "tx_id": tx_id,
            "title": title or email,
            "email": email,
            "kind": kind,
            "is_active": is_active,
            "is_expired": is_expired,
            "is_unlimited": is_unlimited,
            "used_gb": total_used_gb,
            "total_gb": total_gb,
            "remaining_gb": remaining_gb,
            "usage_pct": usage_pct,
            "days_left": days_left,
            "time_left_str": time_left_str,
            "ip_limit": ip_limit,
            "sub_url": active_sub_url,
            "sub_format": sub_format,
            "qr_data_uri": qr_uri,
        })

    # Collect from paid transactions
    for r in paid_rows:
        tx_id = r["id"]
        email = r["service_email"] or f"{C.CORE.get_brand_slug()}_{uid}_{tx_id}"
        title = r["plan_name_snapshot"] or f"سرویس #{tx_id}"
        fetch_live_data(email, tx_id=tx_id, sub_id=r["sub_id"], title=title, kind="paid")

    # Collect from trial if active
    if trial_row and str(trial_row["status"]).upper() in ("ACTIVE", "TRIAL_ACTIVE"):
        fetch_live_data(trial_row["email"], tx_id=None, sub_id=trial_row["sub_id"], title="🎁 تست رایگان", kind="trial")

    # Collect from linked services
    for r in linked_rows:
        fetch_live_data(r["email"], tx_id=None, sub_id=None, title=f"🔗 {r['email']}", kind="linked")

    webapp_url = os.getenv("WEBAPP_URL", "").strip() or C.setting("webapp_url", "").strip()

    return {
        "user_id": uid,
        "brand_name": brand_name,
        "balance": balance,
        "trial_eligible": trial_eligible,
        "services_count": len(services),
        "services": services,
        "webapp_url": webapp_url,
        "updated_at": int(time.time()),
    }


def render_services_widget_html(payload: Dict[str, Any]) -> str:
    """Render self-contained, lightweight HTML/CSS/JS widget string (< 25 KB)."""
    payload_json = json.dumps(payload, ensure_ascii=False)
    
    html_template = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>سرویس‌های من</title>
<style>
:root {{
  --bg-color: var(--tg-theme-bg-color, #1e1e24);
  --text-color: var(--tg-theme-text-color, #f3f4f6);
  --hint-color: var(--tg-theme-hint-color, #9ca3af);
  --btn-color: var(--tg-theme-button-color, #3b82f6);
  --btn-text: var(--tg-theme-button-text-color, #ffffff);
  --card-bg: var(--tg-theme-secondary-bg-color, #282830);
  --border-color: rgba(255,255,255,0.08);
  --success-color: #10b981;
  --warn-color: #f59e0b;
  --danger-color: #ef4444;
}}
* {{
  box-sizing: border-box;
  margin: 0;
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "IRANSans", Tahoma, sans-serif;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}}
body {{
  background-color: var(--bg-color);
  color: var(--text-color);
  padding: 12px;
  font-size: 14px;
  line-height: 1.5;
}}
.widget-card {{
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 16px;
  position: relative;
  box-shadow: 0 4px 14px rgba(0,0,0,0.2);
}}
.header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 10px;
}}
.header h3 {{
  font-size: 16px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 6px;
}}
.badge {{
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 20px;
  font-weight: 600;
}}
.badge-active {{ background: rgba(16,185,129,0.15); color: var(--success-color); border: 1px solid rgba(16,185,129,0.3); }}
.badge-expired {{ background: rgba(239,68,68,0.15); color: var(--danger-color); border: 1px solid rgba(239,68,68,0.3); }}
.badge-sub {{ background: rgba(59,130,246,0.15); color: var(--btn-color); border: 1px solid rgba(59,130,246,0.3); }}

/* Progress Bar */
.progress-container {{
  margin: 12px 0;
}}
.progress-labels {{
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  margin-bottom: 5px;
}}
.progress-bg {{
  background: rgba(255,255,255,0.08);
  height: 10px;
  border-radius: 10px;
  overflow: hidden;
  position: relative;
}}
.progress-fill {{
  height: 100%;
  border-radius: 10px;
  background: linear-gradient(90deg, #3b82f6, #60a5fa);
  transition: width 0.5s ease-in-out;
}}
.progress-fill.warn {{ background: linear-gradient(90deg, #f59e0b, #fbbf24); }}
.progress-fill.danger {{ background: linear-gradient(90deg, #ef4444, #f87171); }}

/* Stats Grid */
.stats-grid {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin: 14px 0;
}}
.stat-box {{
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 8px 10px;
}}
.stat-box .stat-label {{
  font-size: 11px;
  color: var(--hint-color);
}}
.stat-box .stat-value {{
  font-size: 13px;
  font-weight: 600;
  margin-top: 2px;
}}

/* Buttons */
.btn-group {{
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 14px;
}}
.btn {{
  background: var(--btn-color);
  color: var(--btn-text);
  border: none;
  padding: 10px 14px;
  border-radius: 10px;
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.2s ease;
}}
.btn:active {{ transform: scale(0.98); opacity: 0.9; }}
.btn-secondary {{
  background: rgba(255,255,255,0.07);
  color: var(--text-color);
}}
.btn-secondary:hover {{ background: rgba(255,255,255,0.12); }}
.btn-outline {{
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-color);
}}
.btn:disabled {{
  opacity: 0.5;
  cursor: not-allowed;
}}

/* Service list items */
.service-item {{
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 12px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: background 0.2s ease;
}}
.service-item:hover {{ background: rgba(255,255,255,0.06); }}
.service-item-header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
}}
.pagination {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--border-color);
}}

/* QR Code */
.qr-card {{
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 14px 0;
}}
.qr-frame {{
  background: #ffffff;
  padding: 12px;
  border-radius: 14px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.4);
  display: inline-block;
  margin-bottom: 12px;
}}
.qr-frame img {{
  display: block;
  width: 180px;
  height: 180px;
}}

/* Toast */
.toast {{
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: #10b981;
  color: #fff;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.3s ease;
  z-index: 100;
}}
.toast.show {{ opacity: 1; }}

/* Animations */
.spin {{
  display: inline-block;
  animation: rotate 1s linear infinite;
}}
@keyframes rotate {{
  100% {{ transform: rotate(360deg); }}
}}
.empty-box {{
  text-align: center;
  padding: 24px 8px;
}}
.empty-icon {{
  font-size: 42px;
  margin-bottom: 10px;
}}
</style>
</head>
<body>

<div class="widget-card" id="widgetApp">
  <!-- Dynamic views rendered via JS -->
</div>

<div id="toast" class="toast">کپی شد! ✅</div>

<script>
const DATA = {payload_json};
let currentView = DATA.services.length === 1 ? 'detail' : (DATA.services.length === 0 ? 'empty' : 'list');
let selectedIndex = 0;
let listPage = 0;
const PAGE_SIZE = 2;
let isCooldown = false;
let cooldownInterval = null;

function showToast(msg) {{
  const t = document.getElementById('toast');
  t.innerText = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2000);
}}

function copyText(str) {{
  if (!str) return;
  if (navigator.clipboard && navigator.clipboard.writeText) {{
    navigator.clipboard.writeText(str).then(() => showToast('لینک کپی شد! ✅'));
  }} else {{
    const el = document.createElement('textarea');
    el.value = str;
    document.body.appendChild(el);
    el.select();
    document.execCommand('copy');
    document.body.removeChild(el);
    showToast('لینک کپی شد! ✅');
  }}
}}

function triggerRefresh() {{
  if (isCooldown) return;
  isCooldown = true;
  
  const btn = document.getElementById('btnRefresh');
  const icon = document.getElementById('refreshIcon');
  const txt = document.getElementById('refreshTxt');
  
  if (btn) btn.disabled = true;
  if (icon) icon.classList.add('spin');
  
  let left = 5;
  if (txt) txt.innerText = left + 's...';
  
  // Call Telegram host bridge or fallback
  if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.sendData) {{
    try {{
      window.Telegram.WebApp.sendData(JSON.stringify({{ action: 'refresh', index: selectedIndex }}));
    }} catch(e) {{}}
  }}
  
  cooldownInterval = setInterval(() => {{
    left--;
    if (left > 0) {{
      if (txt) txt.innerText = left + 's...';
    }} else {{
      clearInterval(cooldownInterval);
      isCooldown = false;
      if (btn) btn.disabled = false;
      if (icon) icon.classList.remove('spin');
      if (txt) txt.innerText = 'بروزرسانی زنده';
    }}
  }}, 1000);
}}

function openStore() {{
  if (DATA.webapp_url) {{
    if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.openLink) {{
      window.Telegram.WebApp.openLink(DATA.webapp_url + '#/store');
      return;
    }}
    window.location.href = DATA.webapp_url + '#/store';
  }} else {{
    showToast('لطفاً از دکمه «خرید پلان» منوی ربات استفاده کنید.');
  }}
}}

function claimTrial() {{
  if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.sendData) {{
    window.Telegram.WebApp.sendData(JSON.stringify({{ action: 'claim_trial' }}));
    showToast('درخواست تست رایگان ارسال شد... ⏳');
  }} else {{
    showToast('دکمه دریافت تست رایگان در کیبورد ربات را بزنید.');
  }}
}}

function render() {{
  const app = document.getElementById('widgetApp');
  
  // 1. EMPTY STATE
  if (currentView === 'empty' || DATA.services.length === 0) {{
    let trialBtnHtml = '';
    if (DATA.trial_eligible) {{
      trialBtnHtml = '<button class="btn btn-secondary" onclick="claimTrial()">🎁 دریافت تست رایگان</button>';
    }}
    app.innerHTML = `
      <div class="header">
        <h3>📦 سرویس‌های فعال</h3>
        <span class="badge badge-expired">۰ سرویس</span>
      </div>
      <div class="empty-box">
        <div class="empty-icon">📡</div>
        <p style="font-weight: 600; margin-bottom: 6px;">در حال حاضر هیچ سرویس فعالی ندارید.</p>
        <p style="font-size: 12px; color: var(--hint-color); margin-bottom: 16px;">برای استفاده از اینترنت پرسرعت، اشتراک جدید تهیه کنید.</p>
        <div class="btn-group">
          ${{trialBtnHtml}}
          <button class="btn" onclick="openStore()">🛍 مشاهده و خرید پلان‌ها</button>
        </div>
      </div>
    `;
    return;
  }}
  
  // 2. LIST VIEW
  if (currentView === 'list') {{
    const start = listPage * PAGE_SIZE;
    const end = Math.min(start + PAGE_SIZE, DATA.services.length);
    const pageServices = DATA.services.slice(start, end);
    const totalPages = Math.ceil(DATA.services.length / PAGE_SIZE);
    
    let itemsHtml = '';
    pageServices.forEach((s, idx) => {{
      const realIdx = start + idx;
      const statusBadge = s.is_active ? '<span class="badge badge-active">🟢 فعال</span>' : '<span class="badge badge-expired">🔴 غیرفعال</span>';
      itemsHtml += `
        <div class="service-item" onclick="selectService(${{realIdx}})">
          <div class="service-item-header">
            <strong>${{s.title}}</strong>
            ${{statusBadge}}
          </div>
          <div style="font-size: 11px; color: var(--hint-color); margin: 4px 0;">${{s.email}}</div>
          <div class="progress-labels" style="margin-top: 6px;">
            <span>مصرف: ${{s.used_gb}} GB</span>
            <span>کل: ${{s.is_unlimited ? 'نامحدود' : s.total_gb + ' GB'}}</span>
          </div>
        </div>
      `;
    }});
    
    app.innerHTML = `
      <div class="header">
        <h3>📡 سرویس‌های فعال من</h3>
        <span class="badge badge-sub">${{DATA.services.length}} سرویس</span>
      </div>
      <div>${{itemsHtml}}</div>
      <div class="pagination">
        <button class="btn btn-outline" style="padding: 6px 12px;" onclick="prevPage()" ${{listPage === 0 ? 'disabled' : ''}}>◀️ قبلی</button>
        <span style="font-size: 12px; color: var(--hint-color);">صفحه ${{listPage + 1}} از ${{totalPages}}</span>
        <button class="btn btn-outline" style="padding: 6px 12px;" onclick="nextPage()" ${{listPage >= totalPages - 1 ? 'disabled' : ''}}>بعدی ▶️</button>
      </div>
    `;
    return;
  }}
  
  // 3. DETAIL VIEW
  if (currentView === 'detail') {{
    const s = DATA.services[selectedIndex];
    const statusBadge = s.is_active ? '<span class="badge badge-active">🟢 فعال</span>' : '<span class="badge badge-expired">🔴 غیرفعال</span>';
    
    let progressClass = '';
    if (s.usage_pct > 85) progressClass = 'danger';
    else if (s.usage_pct > 65) progressClass = 'warn';
    
    const backBtn = DATA.services.length > 1 ? '<button class="btn btn-outline" onclick="currentView=\\'list\\'; render();">🔙 بازگشت به لیست</button>' : '';
    
    app.innerHTML = `
      <div class="header">
        <h3>${{s.title}}</h3>
        ${{statusBadge}}
      </div>
      
      <div style="font-size: 11px; color: var(--hint-color); margin-bottom: 8px;">شناسه: <code>${{s.email}}</code></div>
      
      <div class="progress-container">
        <div class="progress-labels">
          <span>حجم باقیمانده: ${{s.is_unlimited ? 'نامحدود' : s.remaining_gb + ' GB'}}</span>
          <span>${{s.usage_pct}}%</span>
        </div>
        <div class="progress-bg">
          <div class="progress-fill ${{progressClass}}" style="width: ${{s.is_unlimited ? 100 : s.usage_pct}}%;"></div>
        </div>
      </div>
      
      <div class="stats-grid">
        <div class="stat-box">
          <div class="stat-label">📥 مصرف شده</div>
          <div class="stat-value">${{s.used_gb}} GB</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">📤 حجم کل</div>
          <div class="stat-value">${{s.is_unlimited ? 'نامحدود' : s.total_gb + ' GB'}}</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">⏳ مهلت اعتبار</div>
          <div class="stat-value" style="font-size: 12px;">${{s.time_left_str}}</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">👥 سقف کاربر</div>
          <div class="stat-value">${{s.ip_limit > 0 ? s.ip_limit + ' دستگاه' : 'نامحدود'}}</div>
        </div>
      </div>
      
      <div class="btn-group">
        <button class="btn" onclick="copyText('${{s.sub_url}}')">
          <span>📋</span> کپی لینک سابسکریپشن
        </button>
        <button class="btn btn-secondary" onclick="currentView=\\'qr\\'; render();">
          <span>📷</span> نمایش QR Code
        </button>
        <button id="btnRefresh" class="btn btn-outline" onclick="triggerRefresh()">
          <span id="refreshIcon">🔄</span> <span id="refreshTxt">بروزرسانی زنده</span>
        </button>
        ${{backBtn}}
      </div>
    `;
    return;
  }}
  
  // 4. QR CODE VIEW
  if (currentView === 'qr') {{
    const s = DATA.services[selectedIndex];
    app.innerHTML = `
      <div class="header">
        <h3>📷 بارکد اتصال</h3>
        <span class="badge badge-sub">${{s.sub_format.toUpperCase()}}</span>
      </div>
      <div class="qr-card">
        <div class="qr-frame">
          <img src="${{s.qr_data_uri}}" alt="QR Code" />
        </div>
        <p style="font-size: 12px; color: var(--hint-color); text-align: center; margin-bottom: 12px;">
          جهت اتصال با v2rayNG ،Hiddify یا Streisand این بارکد را اسکن کنید.
        </p>
      </div>
      <div class="btn-group">
        <button class="btn" onclick="copyText('${{s.sub_url}}')">📋 کپی لینک</button>
        <button class="btn btn-secondary" onclick="currentView=\\'detail\\'; render();">🔙 بازگشت به جزئیات سرویس</button>
      </div>
    `;
    return;
  }}
}}

function selectService(idx) {{
  selectedIndex = idx;
  currentView = 'detail';
  render();
}}

function nextPage() {{
  const totalPages = Math.ceil(DATA.services.length / PAGE_SIZE);
  if (listPage < totalPages - 1) {{
    listPage++;
    render();
  }}
}}

function prevPage() {{
  if (listPage > 0) {{
    listPage--;
    render();
  }}
}}

render();
</script>
</body>
</html>"""
    return html_template


def fallback_send_services_message(bot, chat_id: int, user_id: int, payload: Dict[str, Any]):
    """Deliver a rich fallback message when in-chat HTML widget is unsupported by client/API."""
    services = payload.get("services", [])
    brand = payload.get("brand_name", "Shop")
    webapp_url = payload.get("webapp_url", "")
    widget_url = f"{webapp_url.rstrip('/')}/widget/services?user_id={user_id}" if webapp_url else ""
    
    if not services:
        msg = f"📡 <b>سرویس‌های من | {html.escape(brand)}</b>\n\n❌ در حال حاضر هیچ سرویس فعالی ندارید."
        m = types.InlineKeyboardMarkup()
        if widget_url:
            m.add(types.InlineKeyboardButton("📡 باز کردن کارت تعاملی", web_app=types.WebAppInfo(url=widget_url)))
        if payload.get("trial_eligible"):
            m.add(types.InlineKeyboardButton("🎁 دریافت تست رایگان", callback_data="view:trial"))
        if webapp_url:
            m.add(types.InlineKeyboardButton("🛍 مشاهده و خرید پلان‌ها", web_app=types.WebAppInfo(url=f"{webapp_url.rstrip('/')}#/store")))
        return bot.send_message(chat_id, msg, parse_mode="HTML", reply_markup=m)

    m = types.InlineKeyboardMarkup(row_width=1)
    
    # Place prominent WebApp launcher at the top to open the HTML5 widget directly!
    if widget_url:
        m.add(types.InlineKeyboardButton("📡 مشاهده سرویس‌ها (ویجت تعاملی)", web_app=types.WebAppInfo(url=widget_url)))
    elif webapp_url:
        services_app_url = f"{webapp_url.rstrip('/')}#/services"
        m.add(types.InlineKeyboardButton("🌐 باز کردن نمای کارتی (Mini App)", web_app=types.WebAppInfo(url=services_app_url)))

    # Add quick access buttons for each service
    for s in services:
        tx_id = s.get("tx_id")
        cb_data = f"view:status:{tx_id}" if tx_id else (f"view:linked:{s['id']}" if s["kind"] == "linked" else "view:trial")
        status_dot = "🟢" if s.get("is_active") else "🔴"
        m.add(types.InlineKeyboardButton(f"{status_dot} {s['title'][:32]}", callback_data=cb_data))

    msg = f"📡 <b>سرویس‌های فعال شما | {html.escape(brand)}</b>\n" \
          f"تعداد سرویس‌های فعال: <b>{len(services)}</b>\n\n" \
          f"👇 برای مشاهده مشخصات زنده، نوار مصرف و بارکد اتصال، سرویس خود را انتخاب کنید:"
          
    return bot.send_message(chat_id, msg, parse_mode="HTML", reply_markup=m)


def send_active_services_widget(bot, chat_id: int, user_id: int):
    """Build payload and send in-chat HTML widget with graceful fallback."""
    payload = build_services_payload(user_id)
    widget_html = render_services_widget_html(payload)
    
    # Attempt to send via Telegram Widget API
    try:
        # Experimental sendWidget call
        res = bot.api_request(
            "sendWidget",
            method="post",
            params={
                "chat_id": chat_id,
                "widget": widget_html,
            }
        )
        if res and res.get("ok"):
            return res
    except Exception:
        pass
        
    # Standard graceful fallback
    return fallback_send_services_message(bot, chat_id, user_id, payload)
