"""Admin panel: bot-wide settings (categorized)."""

from telegram import Update
from telegram.ext import ContextTypes

import bot_settings as bs
import database as db
from keyboards import admin_bot_settings_kb

# Which subsection to reopen after a toggle/change
_CALLBACK_SECTION = {
    "bset:home": "home",
    "bset:sec:menu": "menu",
    "bset:sec:config": "config",
    "bset:sec:create": "create",
    "bset:fc": "menu",
    "bset:fr": "menu",
    "bset:fch": "menu",
    "bset:fa": "menu",
    "bset:fct": "config",
    "bset:fcd": "config",
    "bset:cn": "create",
    "bset:sub": "create",
    "bset:slen": "create",
}

_TOGGLE_MAP = {
    "bset:fc": bs.FEAT_CREATE,
    "bset:fr": bs.FEAT_RENEW,
    "bset:fch": bs.FEAT_CHECK,
    "bset:fa": bs.FEAT_ACCOUNT,
    "bset:fct": bs.FEAT_CONFIG_TOGGLE,
    "bset:fcd": bs.FEAT_CONFIG_DELETE,
}


async def show_bot_settings(update: Update, section: str = "home"):
    text = bs.format_settings_section(section)
    kb = admin_bot_settings_kb(section)
    if update.message:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)
    elif update.callback_query:
        q = update.callback_query
        try:
            await q.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            await q.message.reply_text(text, parse_mode="HTML", reply_markup=kb)


async def handle_admin_settings_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not db.is_admin(update.effective_user.id):
        return False
    text = (update.message.text or "").strip()
    if text != "⚙️ تنظیمات ربات":
        return False
    await show_bot_settings(update, "home")
    return True


async def handle_admin_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    query = update.callback_query
    if not db.is_admin(query.from_user.id):
        return False
    data = query.data or ""
    if not data.startswith("bset:"):
        return False

    await query.answer()

    section = _CALLBACK_SECTION.get(data, "home")

    if data in _TOGGLE_MAP:
        bs.toggle_feature(_TOGGLE_MAP[data])
        await show_bot_settings(update, section)
        return True

    if data == "bset:cn":
        bs.cycle_client_name_mode()
        await show_bot_settings(update, "create")
        return True

    if data == "bset:sub":
        bs.cycle_sub_id_mode()
        await show_bot_settings(update, "create")
        return True

    if data == "bset:slen":
        lo, hi = bs.get_sub_random_bounds()
        if hi < 16:
            db.set_setting(bs.SUB_RANDOM_MIN, str(lo))
            db.set_setting(bs.SUB_RANDOM_MAX, str(min(hi + 2, 24)))
        else:
            db.set_setting(bs.SUB_RANDOM_MIN, "8")
            db.set_setting(bs.SUB_RANDOM_MAX, "12")
        await show_bot_settings(update, "create")
        return True

    if data in ("bset:home", "bset:sec:menu", "bset:sec:config", "bset:sec:create"):
        await show_bot_settings(update, section)
        return True

    return False
