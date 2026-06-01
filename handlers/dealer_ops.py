from telegram import Update
from telegram.ext import ContextTypes

import database as db
from database import DealerConfig
from handlers.common import CANCEL_TEXT, State, clear_state, require_dealer, set_state
from handlers.helpers import (
    format_config_report,
    get_traffic_stats,
    resolve_config_from_link,
    send_config_package,
)
from keyboards import (
    cancel_kb,
    config_actions,
    confirm_kb,
    dealer_menu,
    inbound_choice,
)
from panel_client import (
    PanelError,
    format_bytes,
    gb_to_bytes,
    is_duplicate_error,
    normalize_client_name,
    panel,
    random_client_name,
    to_panel_email,
)


async def handle_random_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /random during config name step."""
    dealer, status = require_dealer(update.effective_user.id)
    if status != "ok":
        return
    if context.user_data.get("state") != State.CREATE_REMARK.value:
        await update.message.reply_text("ℹ️ /random فقط هنگام ساخت کانفیگ کار می‌کند.")
        return
    await _create_remark(update, context, dealer, "/random")


async def handle_dealer_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    dealer, status = require_dealer(update.effective_user.id)
    if status in ("no_access", "blocked"):
        return False
    if status == "admin":
        return False

    text = (update.message.text or "").strip()
    state_val = context.user_data.get("state")

    if text == CANCEL_TEXT:
        clear_state(context)
        await update.message.reply_text("انصراف.", reply_markup=dealer_menu())
        return True

    if state_val is None and text in ("🆕 ساخت", "♻️ تمدید", "🔎 بررسی", "👤 حساب من"):
        if text == "🆕 ساخت":
            return await _start_create(update, context, dealer)
        if text == "♻️ تمدید":
            return await _start_renew(update, context)
        if text == "🔎 بررسی":
            return await _start_check(update, context)
        if text == "👤 حساب من":
            return await _show_account(update, dealer)
        return True

    if state_val == State.CREATE_GB.value:
        return await _create_gb(update, context, dealer, text)
    if state_val == State.CREATE_REMARK.value:
        return await _create_remark(update, context, dealer, text)
    if state_val == State.RENEW_LINK.value:
        return await _renew_link(update, context, dealer, text)
    if state_val == State.RENEW_GB.value:
        return await _renew_gb(update, context, dealer, text)
    if state_val == State.CHECK_LINK.value:
        return await _check_link(update, context, dealer, text)

    return False


async def _start_create(update, context, dealer):
    inbounds = db.get_dealer_inbounds(dealer.id)
    if not inbounds:
        await update.message.reply_text("❌ اینباندی برای شما تعریف نشده. با ادمین تماس بگیرید.")
        return True

    if len(inbounds) == 1:
        ib = inbounds[0]
        avail = ib.quota_bytes - ib.used_bytes
        if avail <= 0:
            await update.message.reply_text("❌ سهمیه این اینباند تمام شده.")
            return True
        set_state(context, State.CREATE_GB, inbound_id=ib.inbound_id, display_name=ib.display_name)
        await update.message.reply_text(
            f"📡 اینباند: {ib.display_name}\n📦 حجم باقی‌مانده سهمیه: {format_bytes(avail)}\n\n"
            "حجم کانفیگ را به گیگابایت وارد کنید:",
            reply_markup=cancel_kb(),
        )
        return True

    set_state(context, State.CREATE_INBOUND)
    await update.message.reply_text(
        "📡 روی کدام اینباند می‌خواهید بسازید؟",
        reply_markup=inbound_choice(inbounds),
    )
    return True


async def _create_gb(update, context, dealer, text):
    try:
        gb = float(text.replace(",", "."))
        if gb <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ عدد مثبت وارد کنید.")
        return True

    draft = context.user_data["draft"]
    inbound_id = draft["inbound_id"]
    ib = db.get_dealer_inbound(dealer.id, inbound_id)
    bytes_needed = gb_to_bytes(gb)
    avail = ib.quota_bytes - ib.used_bytes
    if bytes_needed > avail:
        await update.message.reply_text(
            f"❌ سهمیه کافی نیست. باقی‌مانده: {format_bytes(avail)}"
        )
        return True

    draft["gb"] = gb
    draft["bytes"] = bytes_needed
    set_state(context, State.CREATE_REMARK)
    await update.message.reply_text(
        "📛 نام کانفیگ را وارد کنید:\n"
        "• همین نام در لینک نمایش داده می‌شود\n"
        "• تکراری بودن فقط بین کانفیگ‌های خودتان چک می‌شود\n"
        "• برای نام تصادفی: /random"
    )
    return True


async def _create_remark(update, context, dealer, text):
    draft = context.user_data["draft"]
    inbound_id = draft["inbound_id"]
    bytes_needed = draft["bytes"]

    if text.strip().lower() == "/random":
        display_name = random_client_name()
    else:
        display_name = normalize_client_name(text)
        if not display_name:
            await update.message.reply_text(
                "❌ نام نامعتبر. فقط حروف، عدد، . _ - مجاز است.\n"
                "یا /random بزنید."
            )
            return True

    if db.dealer_config_name_exists(dealer.id, display_name):
        await update.message.reply_text(
            f"❌ نام «{display_name}» را قبلاً ساخته‌اید.\n"
            "نام دیگری وارد کنید یا /random بزنید."
        )
        return True

    panel_email = to_panel_email(display_name)
    if not panel_email:
        await update.message.reply_text("❌ نام نامعتبر.")
        return True

    if not db.reserve_quota(dealer.id, inbound_id, bytes_needed):
        await update.message.reply_text("❌ سهمیه کافی نیست.")
        clear_state(context)
        await update.message.reply_text("منو", reply_markup=dealer_menu())
        return True

    try:
        uuid = panel.new_uuid()
        sub_id = display_name
        panel.add_client(inbound_id, panel_email, uuid, sub_id, bytes_needed)

        cfg = DealerConfig(
            id=0,
            dealer_id=dealer.id,
            inbound_id=inbound_id,
            client_email=panel_email,
            client_uuid=uuid,
            sub_id=sub_id,
            remark=display_name,
            total_bytes=bytes_needed,
            enabled=True,
        )
        db.add_config(cfg)

        clear_state(context)
        await update.message.reply_text(
            f"✅ کانفیگ «{display_name}» ساخته شد — در حال ارسال لینک‌ها...",
            reply_markup=dealer_menu(),
        )
        try:
            await send_config_package(
                update.message,
                inbound_id,
                panel_email,
                sub_id,
                f"کانفیگ {display_name}",
                display_name,
            )
        except Exception:
            await update.message.reply_text(
                "⚠️ کانفیگ ساخته شد ولی ارسال QR/لینک با تأخیر مواجه شد. از بخش بررسی امتحان کنید."
            )

    except PanelError as e:
        db.release_quota(dealer.id, inbound_id, bytes_needed)
        if is_duplicate_error(str(e)):
            set_state(context, State.CREATE_REMARK)
            await update.message.reply_text(
                "❌ این نام در پنل هم تکراری است. نام دیگری بفرستید یا /random"
            )
        else:
            clear_state(context)
            await update.message.reply_text(f"❌ {e}", reply_markup=dealer_menu())

    except Exception as e:
        db.release_quota(dealer.id, inbound_id, bytes_needed)
        clear_state(context)
        await update.message.reply_text(
            f"❌ خطای غیرمنتظره: {e}\nاگر سهمیه کم شد با ادمین تماس بگیرید.",
            reply_markup=dealer_menu(),
        )

    return True


async def _start_renew(update, context):
    set_state(context, State.RENEW_LINK)
    await update.message.reply_text(
        "🔗 لینک کانفیگ را بفرستید:",
        reply_markup=cancel_kb(),
    )
    return True


async def _renew_link(update, context, dealer, text):
    cfg = resolve_config_from_link(text, dealer.id)
    if not cfg:
        await update.message.reply_text("❌ کانفیگ یافت نشد یا متعلق به شما نیست.")
        return True

    set_state(context, State.RENEW_GB, config_id=cfg.id)
    await update.message.reply_text(
        f"📛 کانفیگ: <b>{cfg.remark}</b>\n\n"
        "قصد دارید چه مقدار حجم (گیگابایت) به این کانفیگ اضافه کنید؟",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )
    return True


async def _renew_gb(update, context, dealer, text):
    try:
        gb = float(text.replace(",", "."))
        if gb <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ عدد مثبت")
        return True

    draft = context.user_data["draft"]
    cfg = db.get_config_by_id(draft["config_id"])
    if not cfg:
        clear_state(context)
        await update.message.reply_text("❌ کانفیگ", reply_markup=dealer_menu())
        return True

    ib = db.get_dealer_inbound(dealer.id, cfg.inbound_id)
    add_bytes = gb_to_bytes(gb)
    avail = ib.quota_bytes - ib.used_bytes
    if add_bytes > avail:
        await update.message.reply_text(f"❌ سهمیه کافی نیست. باقی: {format_bytes(avail)}")
        return True

    if not db.reserve_quota(dealer.id, cfg.inbound_id, add_bytes):
        await update.message.reply_text("❌ سهمیه کافی نیست.")
        return True

    try:
        new_total = cfg.total_bytes + add_bytes
        panel.update_client_total(cfg.inbound_id, cfg.client_uuid, new_total)
        db.update_config_total(cfg.id, new_total)

        clear_state(context)
        await update.message.reply_text(
            f"✅ {format_bytes(add_bytes)} به «{cfg.remark}» اضافه شد.\n"
            f"حجم کل جدید: {format_bytes(new_total)}",
            reply_markup=dealer_menu(),
        )
    except PanelError as e:
        db.release_quota(dealer.id, cfg.inbound_id, add_bytes)
        await update.message.reply_text(f"❌ {e}")

    return True


async def _start_check(update, context):
    set_state(context, State.CHECK_LINK)
    await update.message.reply_text(
        "🔗 لینک کانفیگ را برای بررسی بفرستید:",
        reply_markup=cancel_kb(),
    )
    return True


async def _check_link(update, context, dealer, text):
    try:
        cfg = resolve_config_from_link(text, dealer.id)
    except PanelError as e:
        await update.message.reply_text(f"❌ خطای پنل: {e}", reply_markup=dealer_menu())
        return True

    clear_state(context)
    if not cfg:
        await update.message.reply_text(
            "❌ کانفیگ یافت نشد.\n"
            "لینک کامل vless://... را بفرستید.",
            reply_markup=dealer_menu(),
        )
        return True

    try:
        report = format_config_report(cfg)
        kb = config_actions(cfg.id, cfg.enabled) if cfg.id else None
        await update.message.reply_text(report, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        await update.message.reply_text(
            f"❌ خطا در نمایش اطلاعات: {e}",
            reply_markup=dealer_menu(),
        )
    return True


async def _show_account(update, dealer):
    inbounds = db.get_dealer_inbounds(dealer.id)
    configs = db.get_dealer_configs(dealer.id)
    lines = [f"👤 حساب من — {dealer.name}", f"📦 تعداد کانفیگ: {len(configs)}", ""]
    for ib in inbounds:
        avail = ib.quota_bytes - ib.used_bytes
        lines.append(
            f"📡 {ib.display_name}\n"
            f"   سهمیه کل: {format_bytes(ib.quota_bytes)}\n"
            f"   تخصیص‌یافته: {format_bytes(ib.used_bytes)}\n"
            f"   قابل استفاده: {format_bytes(avail)}"
        )
    await update.message.reply_text("\n".join(lines), reply_markup=dealer_menu())
    return True


async def handle_dealer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    query = update.callback_query
    dealer, status = require_dealer(query.from_user.id)
    if status != "ok":
        return False

    await query.answer()
    data = query.data

    if data == "cancel":
        clear_state(context)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("انصراف.", reply_markup=dealer_menu())
        return True

    if data.startswith("inbound:"):
        inbound_id = int(data.split(":")[1])
        ib = db.get_dealer_inbound(dealer.id, inbound_id)
        if not ib:
            await query.message.reply_text("❌ دسترسی ندارید.")
            return True
        avail = ib.quota_bytes - ib.used_bytes
        if avail <= 0:
            await query.message.reply_text("❌ سهمیه تمام شده.")
            return True
        set_state(
            context,
            State.CREATE_GB,
            inbound_id=inbound_id,
            display_name=ib.display_name,
        )
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            f"📡 {ib.display_name} — باقی: {format_bytes(avail)}\nحجم (GB):",
            reply_markup=cancel_kb(),
        )
        return True

    if data.startswith("cfg_toggle:"):
        config_id = int(data.split(":")[1])
        return await _toggle_config(query, dealer, config_id)

    if data.startswith("cfg_del:"):
        config_id = int(data.split(":")[1])
        await query.message.reply_text(
            "⚠️ حذف کانفیگ؟ حجم باقی‌مانده به سهمیه برمی‌گردد.",
            reply_markup=confirm_kb("del_cfg", config_id),
        )
        return True

    if data.startswith("confirm:del_cfg:"):
        config_id = int(data.split(":")[2])
        return await _delete_config(query, dealer, config_id)

    return False


async def _toggle_config(query, dealer, config_id: int) -> bool:
    cfg = db.get_config_by_id(config_id)
    if not cfg or cfg.dealer_id != dealer.id:
        await query.message.reply_text("❌ یافت نشد.")
        return True
    new_enabled = not cfg.enabled
    try:
        panel.set_client_enabled(cfg.inbound_id, cfg.client_uuid, new_enabled)
        db.set_config_enabled(cfg.id, new_enabled)
        cfg.enabled = new_enabled
        await query.message.reply_text(
            format_config_report(cfg),
            parse_mode="HTML",
            reply_markup=config_actions(cfg.id, cfg.enabled),
        )
    except PanelError as e:
        await query.message.reply_text(f"❌ {e}")
    return True


async def _delete_config(query, dealer, config_id: int) -> bool:
    cfg = db.get_config_by_id(config_id)
    if not cfg or cfg.dealer_id != dealer.id:
        await query.edit_message_text("❌ یافت نشد.")
        return True

    stats = get_traffic_stats(cfg.client_email)
    remaining = max(0, cfg.total_bytes - stats["used"])

    try:
        panel.delete_client(cfg.inbound_id, cfg.client_uuid)
        if remaining > 0:
            db.release_quota(dealer.id, cfg.inbound_id, remaining)
        db.delete_config(cfg.id)
        await query.edit_message_text(
            f"✅ کانفیگ «{cfg.remark}» حذف شد.\n"
            f"↩️ {format_bytes(remaining)} به سهمیه برگشت."
        )
    except PanelError as e:
        await query.message.reply_text(f"❌ {e}")
    return True
