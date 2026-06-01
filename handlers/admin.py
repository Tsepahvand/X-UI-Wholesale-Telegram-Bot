from telegram import Update
from telegram.ext import ContextTypes

import config
import database as db
from handlers.common import CANCEL_TEXT, State, clear_state, set_state
from handlers.helpers import disable_all_dealer_configs
from keyboards import admin_dealer_actions, admin_menu, cancel_kb, confirm_kb
from panel_client import PanelError, format_bytes, gb_to_bytes, panel


async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Return True if message was handled."""
    if not db.is_admin(update.effective_user.id):
        return False

    text = (update.message.text or "").strip()
    state_val = context.user_data.get("state")

    if text == CANCEL_TEXT:
        clear_state(context)
        await update.message.reply_text("انصراف شد.", reply_markup=admin_menu())
        return True

    if text == "➕ افزودن عمده‌فروش":
        clear_state(context)
        set_state(context, State.ADM_ADD_TG)
        await update.message.reply_text(
            "🆔 آیدی عددی تلگرام عمده‌فروش را بفرستید:",
            reply_markup=cancel_kb(),
        )
        return True

    if text == "🔍 جستجوی عمده‌فروش":
        clear_state(context)
        set_state(context, State.ADM_FIND_TG)
        await update.message.reply_text(
            "🆔 آیدی عددی تلگرام را بفرستید:",
            reply_markup=cancel_kb(),
        )
        return True

    if text == "📋 لیست عمده‌فروشان":
        dealers = db.list_dealers()
        if not dealers:
            await update.message.reply_text("لیست خالی است.")
            return True
        lines = []
        for d in dealers:
            st = "🚫 بلاک" if d.is_blocked else "✅ فعال"
            lines.append(f"• {d.name} — ID: `{d.telegram_id}` — {st}")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return True

    if state_val == State.ADM_ADD_TG.value:
        return await _adm_add_tg(update, context, text)
    if state_val == State.ADM_ADD_NAME.value:
        return await _adm_add_name(update, context, text)
    if state_val == State.ADM_ADD_INBOUND_ID.value:
        return await _adm_add_inbound_id(update, context, text)
    if state_val == State.ADM_ADD_INBOUND_NAME.value:
        return await _adm_add_inbound_name(update, context, text)
    if state_val == State.ADM_ADD_INBOUND_QUOTA.value:
        return await _adm_add_inbound_quota(update, context, text)
    if state_val == State.ADM_ADD_MORE_INBOUND.value:
        return await _adm_add_more(update, context, text)
    if state_val == State.ADM_FIND_TG.value:
        return await _adm_find_tg(update, context, text)
    if state_val == State.ADM_QUOTA_INBOUND.value:
        return await _adm_quota_inbound(update, context, text)
    if state_val == State.ADM_QUOTA_AMOUNT.value:
        return await _adm_quota_amount(update, context, text)

    return False


async def _adm_add_tg(update, context, text):
    try:
        tg_id = int(text)
    except ValueError:
        await update.message.reply_text("❌ فقط عدد بفرستید.")
        return True
    set_state(context, State.ADM_ADD_NAME, telegram_id=tg_id)
    await update.message.reply_text("📝 نام عمده‌فروش را وارد کنید:")
    return True


async def _adm_add_name(update, context, text):
    draft = context.user_data["draft"]
    dealer = db.create_dealer(draft["telegram_id"], text)
    draft["dealer_id"] = dealer.id
    draft["dealer_name"] = text
    draft["inbounds_added"] = []
    set_state(context, State.ADM_ADD_INBOUND_ID)
    await _send_panel_inbounds(update)
    return True


async def _send_panel_inbounds(update):
    try:
        inbounds = panel.list_inbounds()
        lines = ["📡 اینباندهای پنل — یک ID انتخاب کنید:\n"]
        for ib in inbounds:
            lines.append(f"• ID `{ib['id']}` — {ib.get('remark', '?')} ({ib.get('protocol', '')}:{ib.get('port', '')})")
        lines.append("\nیا `done` برای پایان (اگر حداقل یک اینباند اضافه کردید)")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        await update.message.reply_text("🔢 شماره inbound را بفرستید:")
    except PanelError as e:
        await update.message.reply_text(f"❌ خطای پنل: {e}")


async def _adm_add_inbound_id(update, context, text):
    draft = context.user_data["draft"]
    if text.lower() == "done":
        if not draft.get("inbounds_added"):
            await update.message.reply_text("❌ حداقل یک اینباند لازم است.")
            return True
        clear_state(context)
        await update.message.reply_text(
            f"✅ عمده‌فروش ثبت شد.\nآیدی: `{draft['telegram_id']}`\nنام: {draft.get('dealer_name', '')}",
            parse_mode="Markdown",
            reply_markup=admin_menu(),
        )
        return True

    try:
        inbound_id = int(text)
    except ValueError:
        await update.message.reply_text("❌ عدد معتبر بفرستید یا done")
        return True

    draft["pending_inbound_id"] = inbound_id
    set_state(context, State.ADM_ADD_INBOUND_NAME)
    await update.message.reply_text("🏷 نام نمایشی این اینباند برای عمده‌فروش:")
    return True


async def _adm_add_inbound_name(update, context, text):
    draft = context.user_data["draft"]
    draft["pending_display_name"] = text
    set_state(context, State.ADM_ADD_INBOUND_QUOTA)
    await update.message.reply_text("📦 سقف حجم مجاز (گیگابایت) برای ساخت/تمدید روی این اینباند:")
    return True


async def _adm_add_inbound_quota(update, context, text):
    try:
        gb = float(text.replace(",", "."))
        if gb <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ عدد مثبت وارد کنید.")
        return True

    draft = context.user_data["draft"]
    db.add_dealer_inbound(
        draft["dealer_id"],
        draft["pending_inbound_id"],
        draft["pending_display_name"],
        gb_to_bytes(gb),
    )
    draft.setdefault("inbounds_added", []).append(draft["pending_inbound_id"])
    set_state(context, State.ADM_ADD_MORE_INBOUND)
    await update.message.reply_text(
        "✅ اینباند اضافه شد.\n`yes` برای اینباند دیگر / `no` برای پایان",
        parse_mode="Markdown",
    )
    return True


async def _adm_add_more(update, context, text):
    if text.lower() in ("no", "نه", "خیر"):
        draft = context.user_data["draft"]
        clear_state(context)
        await update.message.reply_text(
            f"✅ عمده‌فروش آماده است.\nتلگرام: `{draft['telegram_id']}`",
            parse_mode="Markdown",
            reply_markup=admin_menu(),
        )
        return True
    if text.lower() in ("yes", "بله", "آره"):
        set_state(context, State.ADM_ADD_INBOUND_ID)
        await _send_panel_inbounds(update)
        return True
    await update.message.reply_text("yes یا no")
    return True


async def _adm_find_tg(update, context, text):
    try:
        tg_id = int(text)
    except ValueError:
        await update.message.reply_text("❌ عدد معتبر بفرستید.")
        return True

    dealer = db.get_dealer_by_telegram_any(tg_id)
    clear_state(context)
    if not dealer or not dealer.is_active:
        await update.message.reply_text("❌ یافت نشد.", reply_markup=admin_menu())
        return True

    await _show_dealer_profile(update, dealer.id)
    return True


async def _show_dealer_profile(update, dealer_id: int):
    dealer = db.get_dealer_by_id(dealer_id)
    inbounds = db.get_dealer_inbounds(dealer_id)
    configs = db.get_dealer_configs(dealer_id)

    lines = [
        f"👤 {dealer.name}",
        f"🆔 تلگرام: `{dealer.telegram_id}`",
        f"وضعیت: {'🚫 بلاک' if dealer.is_blocked else '✅ فعال'}",
        f"📦 کانفیگ‌ها: {len(configs)}",
        "",
        "📡 اینباندها:",
    ]
    for ib in inbounds:
        avail = ib.quota_bytes - ib.used_bytes
        lines.append(
            f"• {ib.display_name} (id={ib.inbound_id})\n"
            f"  کل: {format_bytes(ib.quota_bytes)} | مصرف شده از سهمیه: {format_bytes(ib.used_bytes)} | باقی: {format_bytes(avail)}"
        )

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=admin_dealer_actions(dealer_id, dealer.is_blocked),
    )


async def _adm_quota_inbound(update, context, text):
    try:
        inbound_id = int(text)
    except ValueError:
        await update.message.reply_text("❌ عدد inbound")
        return True
    draft = context.user_data["draft"]
    if not db.get_dealer_inbound(draft["dealer_id"], inbound_id):
        await update.message.reply_text("❌ این inbound به این فروشنده تعلق ندارد.")
        return True
    draft["quota_inbound_id"] = inbound_id
    set_state(context, State.ADM_QUOTA_AMOUNT)
    sign = "+" if draft.get("quota_sign") == "add" else "-"
    await update.message.reply_text(f"📦 مقدار گیگابایت برای {sign}:")
    return True


async def _adm_quota_amount(update, context, text):
    try:
        gb = float(text.replace(",", "."))
        if gb <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ عدد مثبت")
        return True

    draft = context.user_data["draft"]
    delta = gb_to_bytes(gb)
    if draft.get("quota_sign") == "sub":
        delta = -delta
    db.adjust_inbound_quota(draft["dealer_id"], draft["quota_inbound_id"], delta)
    clear_state(context)
    await update.message.reply_text("✅ سهمیه به‌روز شد.", reply_markup=admin_menu())
    return True


async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    query = update.callback_query
    if not db.is_admin(query.from_user.id):
        return False

    await query.answer()
    data = query.data

    if data == "cancel":
        clear_state(context)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("انصراف.", reply_markup=admin_menu())
        return True

    if data.startswith("adm_block:"):
        dealer_id = int(data.split(":")[1])
        dealer = db.get_dealer_by_id(dealer_id)
        db.set_dealer_blocked(dealer_id, not dealer.is_blocked)
        await query.message.reply_text(
            "✅ وضعیت بلاک تغییر کرد.",
            reply_markup=admin_dealer_actions(dealer_id, not dealer.is_blocked),
        )
        return True

    if data.startswith("adm_disable_all:"):
        dealer_id = int(data.split(":")[1])
        n = await disable_all_dealer_configs(dealer_id)
        await query.message.reply_text(f"✅ {n} کانفیگ خاموش شد.")
        return True

    if data.startswith("adm_quota_add:"):
        dealer_id = int(data.split(":")[1])
        set_state(context, State.ADM_QUOTA_INBOUND, dealer_id=dealer_id, quota_sign="add")
        await query.message.reply_text("🔢 inbound id برای افزایش حجم:", reply_markup=cancel_kb())
        return True

    if data.startswith("adm_quota_sub:"):
        dealer_id = int(data.split(":")[1])
        set_state(context, State.ADM_QUOTA_INBOUND, dealer_id=dealer_id, quota_sign="sub")
        await query.message.reply_text("🔢 inbound id برای کاهش حجم:", reply_markup=cancel_kb())
        return True

    if data.startswith("adm_revoke:"):
        dealer_id = int(data.split(":")[1])
        await query.message.reply_text(
            "⚠️ قطع دسترسی؟",
            reply_markup=confirm_kb("revoke", dealer_id),
        )
        return True

    if data.startswith("confirm:revoke:"):
        dealer_id = int(data.split(":")[2])
        db.revoke_dealer(dealer_id)
        clear_state(context)
        await query.edit_message_text("✅ دسترسی قطع شد.")
        return True

    return False
