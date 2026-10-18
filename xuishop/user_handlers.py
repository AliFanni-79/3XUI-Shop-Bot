from html import escape
from . import context as C
from . import ui


def _shop(message):
    blocked,reason=C.blocked(message.from_user.id)
    if blocked:
        C.BOT.send_message(message.chat.id,'🚫 امکان خرید برای حساب شما غیرفعال است.'+(f'\nدلیل: {reason}' if reason else ''),reply_markup=ui.main_menu()); return
    current_mode=C.mode()
    if current_mode=='SALES_PAUSED':
        C.BOT.send_message(message.chat.id,C.setting('sales_paused_message','🛒 فروش و تمدید موقتاً متوقف شده است.'),reply_markup=ui.main_menu()); return
    if current_mode=='MAINTENANCE':
        C.BOT.send_message(message.chat.id,C.setting('maintenance_message','🛠 سرویس موقتاً در حال نگهداری است.'),reply_markup=ui.main_menu()); return
    if C.setting('plan_categories_enabled','1')!='1': return C.CORE.show_plans(message)
    m,rows=ui.categories_markup()
    if not rows: return C.CORE.show_plans(message)
    C.BOT.send_message(message.chat.id,f'🛍 <b>{escape(C.brand_name())}</b>\n━━━━━━━━━━━━━━━━\nدسته موردنظر را انتخاب کنید:',parse_mode='HTML',reply_markup=m)


def _account(message):
    uid=int(message.from_user.id); c=C.db()
    user=c.execute('SELECT balance FROM users WHERE id=?',(uid,)).fetchone()
    paid=c.execute("SELECT id,service_email,plan_name_snapshot FROM transactions WHERE user_id=? AND status='APPROVED' AND kind='NEW' ORDER BY id DESC",(uid,)).fetchall()
    trial=c.execute("SELECT email,status FROM trial_services WHERE user_id=? ORDER BY created_at DESC LIMIT 1",(uid,)).fetchone()
    linked=c.execute('SELECT id,email FROM linked_services WHERE user_id=? ORDER BY id DESC',(uid,)).fetchall(); c.close()
    balance=int(user['balance'] or 0) if user else 0
    lines=['👤 <b>حساب کاربری</b>','━━━━━━━━━━━━━━━━',f'🆔 <code>{uid}</code>',f'👛 موجودی: <b>{balance:,} تومان</b>',f'📦 سرویس‌های خریداری‌شده: <b>{len(paid)}</b>',f'🔗 سرویس‌های متصل‌شده: <b>{len(linked)}</b>']
    if trial: lines.append(f"🎁 وضعیت تست: <b>{escape(str(trial['status']))}</b>")
    blocked,reason=C.blocked(uid)
    if blocked: lines += ['','🚫 <b>خرید برای این حساب محدود شده است.</b>'+(f'\n{escape(reason)}' if reason else '')]
    lines += ['','👇 برای مدیریت هر سرویس، دکمه مربوط به آن را انتخاب کنید.']
    m=C.CORE.types.InlineKeyboardMarkup(row_width=1)
    if trial and trial['status']=='ACTIVE': m.add(C.inline('🎁 وضعیت تست رایگان',callback_data='view:trial',style_name='primary'))
    for r in paid:
        label=(r['plan_name_snapshot'] or r['service_email'] or f"سرویس #{r['id']}")[:42]
        m.add(C.inline(f'📦 {label}',callback_data=f"view:status:{r['id']}",style_name='primary'))
    for r in linked: m.add(C.inline(f"🔗 {r['email'][:42]}",callback_data=f"view:linked:{r['id']}"))
    m.row(C.inline('🧾 تاریخچه خرید',callback_data='account:purchases'),C.inline('📜 کیف پول',callback_data='ref:wallet_history'))
    if C.CORE.existing_service_link_enabled(): m.add(C.inline('➕ افزودن سرویس قبلی',callback_data='account:link_existing',style_name='success'))
    if C.menu_visible('guide') and C.CORE.connection_guides_enabled(): m.add(C.inline('📲 راهنمای اتصال',callback_data='guide:menu',style_name='primary',emoji_key='guide'))
    C.BOT.send_message(uid,'\n'.join(lines),parse_mode='HTML',reply_markup=m)


def public_callback(call):
    parts=(call.data or '').split(':'); action=parts[1] if len(parts)>1 else ''
    if action=='shop':
        C.BOT.answer_callback_query(call.id); m,_=ui.categories_markup(); C.BOT.send_message(call.from_user.id,'🛍 <b>دسته‌بندی پلان‌ها</b>\nدسته موردنظر را انتخاب کنید:',parse_mode='HTML',reply_markup=m); return True
    if action=='shopcat': C.BOT.answer_callback_query(call.id); ui.send_category(call.from_user.id,call.from_user.id,int(parts[2])); return True
    return False


def register():
    C.BOT.message_handler(func=lambda m: m.text == '🛍 مشاهده و خرید پلان‌ها')(_shop); C.promote_message()
    C.BOT.message_handler(func=lambda m: m.text in ('👤 حساب کاربری', '📡 سرویس‌های فعال من'))(_account); C.promote_message()
