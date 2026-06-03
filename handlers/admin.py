from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import config
import database as db
from handlers.admin_settings import handle_admin_settings_message
from handlers.common import CANCEL_TEXT, State, clear_state, set_state
from handlers.helpers import disable_all_dealer_configs
from keyboards import (
    admin_dealer_actions,
    admin_inbound_edit_menu,
    admin_inbounds_menu,
    admin_menu,
    cancel_kb,
    confirm_kb,
)
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

    if await handle_admin_settings_message(update, context):
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
    if state_val == State.ADM_ADD_INBOUND_DAYS.value:
        return await _adm_add_inbound_days(update, context, text)
    if state_val == State.ADM_ADD_MORE_INBOUND.value:
        return await _adm_add_more(update, context, text)
    if state_val == State.ADM_FIND_TG.value:
        return await _adm_find_tg(update, context, text)
    if state_val == State.ADM_QUOTA_INBOUND.value:
        return await _adm_quota_inbound(update, context, text)
    if state_val == State.ADM_QUOTA_AMOUNT.value:
        return await _adm_quota_amount(update, context, text)
    if state_val == State.ADM_MGMT_ADD_INBOUND_ID.value:
        return await _adm_mgmt_add_inbound_id(update, context, text)
    if state_val == State.ADM_MGMT_ADD_INBOUND_NAME.value:
        return await _adm_mgmt_add_inbound_name(update, context, text)
    if state_val == State.ADM_MGMT_ADD_INBOUND_QUOTA.value:
        return await _adm_mgmt_add_inbound_quota(update, context, text)
    if state_val == State.ADM_MGMT_ADD_INBOUND_DAYS.value:
        return await _adm_mgmt_add_inbound_days(update, context, text)
    if state_val == State.ADM_MGMT_EDIT_NAME.value:
        return await _adm_mgmt_edit_name(update, context, text)
    if state_val == State.ADM_MGMT_EDIT_QUOTA.value:
        return await _adm_mgmt_edit_quota(update, context, text)
    if state_val == State.ADM_MGMT_EDIT_DAYS.value:
        return await _adm_mgmt_edit_days(update, context, text)

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
    draft["pending_quota_bytes"] = gb_to_bytes(gb)
    set_state(context, State.ADM_ADD_INBOUND_DAYS)
    await update.message.reply_text(
        "📅 مدت اعتبار هر کانفیگ (روز):\n"
        "• مثلاً `30` → هر کانفیگ ۳۰ روز\n"
        "• `0` → نامحدود",
        parse_mode="Markdown",
    )
    return True


async def _adm_add_inbound_days(update, context, text):
    try:
        days = int(text.strip())
        if days < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ عدد صحیح ≥ ۰ بفرستید (۰ = نامحدود).")
        return True

    draft = context.user_data["draft"]
    db.add_dealer_inbound(
        draft["dealer_id"],
        draft["pending_inbound_id"],
        draft["pending_display_name"],
        draft["pending_quota_bytes"],
        config_days=days,
    )
    draft.setdefault("inbounds_added", []).append(draft["pending_inbound_id"])
    days_label = db.format_config_days_label(days)
    set_state(context, State.ADM_ADD_MORE_INBOUND)
    await update.message.reply_text(
        f"✅ اینباند اضافه شد (اعتبار هر کانفیگ: {days_label}).\n"
        "`yes` برای اینباند دیگر / `no` برای پایان",
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


async def _reply_or_edit_profile(target, dealer_id: int):
    """Send profile to Message or CallbackQuery.message."""
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
    if not inbounds:
        lines.append("  (هیچ اینباندی تخصیص داده نشده)")
    for ib in inbounds:
        avail = ib.quota_bytes - ib.used_bytes
        days_label = db.format_config_days_label(ib.config_days)
        lines.append(
            f"• {ib.display_name} (id={ib.inbound_id})\n"
            f"  کل: {format_bytes(ib.quota_bytes)} | تخصیص: {format_bytes(ib.used_bytes)} | باقی: {format_bytes(avail)}\n"
            f"  اعتبار هر کانفیگ: {days_label}"
        )

    text = "\n".join(lines)
    markup = admin_dealer_actions(dealer_id, dealer.is_blocked)
    msg = getattr(target, "message", None) or target
    await msg.reply_text(text, parse_mode="Markdown", reply_markup=markup)


async def _show_inbounds_menu(query_or_update, dealer_id: int):
    inbounds = db.get_dealer_inbounds(dealer_id)
    dealer = db.get_dealer_by_id(dealer_id)
    lines = [
        f"📡 مدیریت اینباندها — {dealer.name}",
        "",
        "یک اینباند را برای ویرایش انتخاب کنید یا اینباند جدید اضافه کنید.",
    ]
    if inbounds:
        lines.append("")
        for ib in inbounds:
            days_label = db.format_config_days_label(ib.config_days)
            lines.append(
                f"• `{ib.inbound_id}` — {ib.display_name}\n"
                f"  سقف: {format_bytes(ib.quota_bytes)} | اعتبار: {days_label}"
            )
    msg = getattr(query_or_update, "message", None) or query_or_update
    await msg.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=admin_inbounds_menu(dealer_id, inbounds),
    )


async def _show_dealer_profile(update, dealer_id: int):
    await _reply_or_edit_profile(update, dealer_id)


async def _adm_mgmt_add_inbound_id(update, context, text):
    try:
        inbound_id = int(text)
    except ValueError:
        await update.message.reply_text("❌ عدد inbound معتبر بفرستید.")
        return True

    draft = context.user_data["draft"]
    dealer_id = draft["dealer_id"]
    if db.get_dealer_inbound(dealer_id, inbound_id):
        await update.message.reply_text("❌ این inbound قبلاً به این فروشنده داده شده.")
        return True

    draft["pending_inbound_id"] = inbound_id
    set_state(context, State.ADM_MGMT_ADD_INBOUND_NAME, dealer_id=dealer_id)
    await update.message.reply_text("🏷 نام نمایشی این اینباند برای عمده‌فروش:")
    return True


async def _adm_mgmt_add_inbound_name(update, context, text):
    context.user_data["draft"]["pending_display_name"] = text
    set_state(context, State.ADM_MGMT_ADD_INBOUND_QUOTA)
    await update.message.reply_text("📦 سقف حجم مجاز (گیگابایت):")
    return True


async def _adm_mgmt_add_inbound_quota(update, context, text):
    try:
        gb = float(text.replace(",", "."))
        if gb <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ عدد مثبت وارد کنید.")
        return True

    context.user_data["draft"]["pending_quota_bytes"] = gb_to_bytes(gb)
    set_state(context, State.ADM_MGMT_ADD_INBOUND_DAYS)
    await update.message.reply_text(
        "📅 مدت اعتبار هر کانفیگ (روز):\n`0` = نامحدود",
        parse_mode="Markdown",
    )
    return True


async def _adm_mgmt_add_inbound_days(update, context, text):
    try:
        days = int(text.strip())
        if days < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ عدد صحیح ≥ ۰.")
        return True

    draft = context.user_data["draft"]
    dealer_id = draft["dealer_id"]
    db.add_dealer_inbound(
        dealer_id,
        draft["pending_inbound_id"],
        draft["pending_display_name"],
        draft["pending_quota_bytes"],
        config_days=days,
    )
    clear_state(context)
    await update.message.reply_text(
        f"✅ اینباند اضافه شد ({db.format_config_days_label(days)}).",
        reply_markup=admin_menu(),
    )
    await _show_inbounds_menu(update, dealer_id)
    return True


async def _adm_mgmt_edit_name(update, context, text):
    draft = context.user_data["draft"]
    db.update_dealer_inbound(
        draft["dealer_id"],
        draft["edit_inbound_id"],
        display_name=text.strip(),
    )
    clear_state(context)
    await update.message.reply_text("✅ نام نمایشی به‌روز شد.", reply_markup=admin_menu())
    await _show_inbound_edit_menu_msg(update, draft["dealer_id"], draft["edit_inbound_id"])
    return True


async def _adm_mgmt_edit_quota(update, context, text):
    try:
        gb = float(text.replace(",", "."))
        if gb <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ عدد مثبت (گیگابایت) بفرستید.")
        return True

    draft = context.user_data["draft"]
    ok, err = db.set_dealer_inbound_quota(
        draft["dealer_id"], draft["edit_inbound_id"], gb_to_bytes(gb)
    )
    if not ok:
        await update.message.reply_text(f"❌ {err}")
        return True

    clear_state(context)
    await update.message.reply_text("✅ سقف حجم به‌روز شد.", reply_markup=admin_menu())
    await _show_inbound_edit_menu_msg(update, draft["dealer_id"], draft["edit_inbound_id"])
    return True


async def _adm_mgmt_edit_days(update, context, text):
    try:
        days = int(text.strip())
        if days < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ عدد صحیح ≥ ۰ (۰ = نامحدود).")
        return True

    draft = context.user_data["draft"]
    db.update_dealer_inbound(
        draft["dealer_id"],
        draft["edit_inbound_id"],
        config_days=days,
    )
    clear_state(context)
    await update.message.reply_text(
        f"✅ اعتبار کانفیگ‌های جدید: {db.format_config_days_label(days)}\n"
        "(کانفیگ‌های قبلی در پنل تغییر نمی‌کند.)",
        reply_markup=admin_menu(),
    )
    await _show_inbound_edit_menu_msg(update, draft["dealer_id"], draft["edit_inbound_id"])
    return True


async def _show_inbound_edit_menu_msg(update, dealer_id: int, inbound_id: int):
    ib = db.get_dealer_inbound(dealer_id, inbound_id)
    if not ib:
        return
    avail = ib.quota_bytes - ib.used_bytes
    n_cfg = db.count_configs_on_inbound(dealer_id, inbound_id)
    text = (
        f"✏️ ویرایش — {ib.display_name} (id={inbound_id})\n\n"
        f"سقف: {format_bytes(ib.quota_bytes)}\n"
        f"تخصیص‌شده: {format_bytes(ib.used_bytes)}\n"
        f"باقی‌مانده: {format_bytes(avail)}\n"
        f"اعتبار هر کانفیگ: {db.format_config_days_label(ib.config_days)}\n"
        f"تعداد کانفیگ ربات: {n_cfg}"
    )
    await update.message.reply_text(
        text,
        reply_markup=admin_inbound_edit_menu(dealer_id, inbound_id, ib.display_name),
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
        dealer = db.get_dealer_by_id(dealer_id)
        n_cfg = len(db.get_dealer_configs(dealer_id))
        await query.message.reply_text(
            f"⚠️ حذف کامل «{dealer.name}»؟\n"
            f"آیدی تلگرام: `{dealer.telegram_id}`\n"
            f"از دیتابیس ربات پاک می‌شود ({n_cfg} کانفیگ ثبت‌شده).\n"
            f"کانفیگ‌های پنل دست نخورده می‌مانند.",
            parse_mode="Markdown",
            reply_markup=confirm_kb("revoke", dealer_id),
        )
        return True

    if data.startswith("confirm:revoke:"):
        dealer_id = int(data.split(":")[2])
        dealer = db.get_dealer_by_id(dealer_id)
        tg_id = dealer.telegram_id if dealer else None
        if db.delete_dealer(dealer_id):
            clear_state(context)
            extra = ""
            if tg_id and db.is_admin(tg_id):
                extra = "\n\nℹ️ این آیدی در ADMIN_ID هم هست — می‌تواند به‌عنوان ادمین وارد شود."
            await query.edit_message_text(f"✅ فروشنده از دیتابیس حذف شد.{extra}")
        else:
            await query.edit_message_text("❌ حذف انجام نشد.")
        return True

    if data.startswith("adm_ibm:"):
        dealer_id = int(data.split(":")[1])
        clear_state(context)
        await _show_inbounds_menu(query, dealer_id)
        return True

    if data.startswith("adm_ibp:"):
        dealer_id = int(data.split(":")[1])
        clear_state(context)
        await _reply_or_edit_profile(query, dealer_id)
        return True

    if data.startswith("adm_iba:"):
        dealer_id = int(data.split(":")[1])
        set_state(context, State.ADM_MGMT_ADD_INBOUND_ID, dealer_id=dealer_id)
        await query.message.reply_text(
            "🔢 شماره inbound پنل را بفرستید:",
            reply_markup=cancel_kb(),
        )
        try:
            inbounds = panel.list_inbounds()
            lines = ["📡 اینباندهای پنل:\n"]
            assigned = {ib.inbound_id for ib in db.get_dealer_inbounds(dealer_id)}
            for ib in inbounds:
                mark = " ✅" if ib["id"] in assigned else ""
                lines.append(
                    f"• ID `{ib['id']}` — {ib.get('remark', '?')}{mark}"
                )
            await query.message.reply_text("\n".join(lines), parse_mode="Markdown")
        except PanelError as e:
            await query.message.reply_text(f"❌ {e}")
        return True

    if data.startswith("adm_ibe:"):
        parts = data.split(":")
        dealer_id, inbound_id = int(parts[1]), int(parts[2])
        ib = db.get_dealer_inbound(dealer_id, inbound_id)
        if not ib:
            await query.message.reply_text("❌ اینباند یافت نشد.")
            return True
        avail = ib.quota_bytes - ib.used_bytes
        n_cfg = db.count_configs_on_inbound(dealer_id, inbound_id)
        await query.message.reply_text(
            f"✏️ {ib.display_name} (id={inbound_id})\n\n"
            f"سقف: {format_bytes(ib.quota_bytes)}\n"
            f"تخصیص: {format_bytes(ib.used_bytes)} | باقی: {format_bytes(avail)}\n"
            f"اعتبار کانفیگ: {db.format_config_days_label(ib.config_days)}\n"
            f"کانفیگ‌های ثبت‌شده: {n_cfg}",
            reply_markup=admin_inbound_edit_menu(dealer_id, inbound_id, ib.display_name),
        )
        return True

    if data.startswith("adm_iben:"):
        parts = data.split(":")
        dealer_id, inbound_id = int(parts[1]), int(parts[2])
        set_state(
            context,
            State.ADM_MGMT_EDIT_NAME,
            dealer_id=dealer_id,
            edit_inbound_id=inbound_id,
        )
        ib = db.get_dealer_inbound(dealer_id, inbound_id)
        await query.message.reply_text(
            f"🏷 نام جدید (فعلی: {ib.display_name}):",
            reply_markup=cancel_kb(),
        )
        return True

    if data.startswith("adm_ibeq:"):
        parts = data.split(":")
        dealer_id, inbound_id = int(parts[1]), int(parts[2])
        set_state(
            context,
            State.ADM_MGMT_EDIT_QUOTA,
            dealer_id=dealer_id,
            edit_inbound_id=inbound_id,
        )
        ib = db.get_dealer_inbound(dealer_id, inbound_id)
        await query.message.reply_text(
            f"📦 سقف کل جدید (گیگابایت)\n"
            f"فعلی: {format_bytes(ib.quota_bytes)} | حداقل: {format_bytes(ib.used_bytes)}",
            reply_markup=cancel_kb(),
        )
        return True

    if data.startswith("adm_ibed:"):
        parts = data.split(":")
        dealer_id, inbound_id = int(parts[1]), int(parts[2])
        set_state(
            context,
            State.ADM_MGMT_EDIT_DAYS,
            dealer_id=dealer_id,
            edit_inbound_id=inbound_id,
        )
        ib = db.get_dealer_inbound(dealer_id, inbound_id)
        await query.message.reply_text(
            f"📅 روز اعتبار هر کانفیگ جدید\n"
            f"فعلی: {db.format_config_days_label(ib.config_days)}\n"
            f"`0` = نامحدود",
            parse_mode="Markdown",
            reply_markup=cancel_kb(),
        )
        return True

    if data.startswith("adm_ibr:"):
        parts = data.split(":")
        dealer_id, inbound_id = int(parts[1]), int(parts[2])
        n = db.count_configs_on_inbound(dealer_id, inbound_id)
        extra = f"\n⚠️ {n} کانفیگ روی این اینباند ثبت است." if n else ""
        await query.message.reply_text(
            f"حذف دسترسی به inbound {inbound_id}؟{extra}",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "✅ بله",
                            callback_data=f"confirm:ibr:{dealer_id}:{inbound_id}",
                        ),
                        InlineKeyboardButton("❌ خیر", callback_data="cancel"),
                    ]
                ]
            ),
        )
        return True

    if data.startswith("confirm:ibr:"):
        parts = data.split(":")
        dealer_id, inbound_id = int(parts[2]), int(parts[3])
        if db.remove_dealer_inbound(dealer_id, inbound_id):
            clear_state(context)
            await query.edit_message_text("✅ اینباند از دسترسی فروشنده حذف شد.")
            await _show_inbounds_menu(query, dealer_id)
        else:
            await query.answer("خطا در حذف", show_alert=True)
        return True

    return False
