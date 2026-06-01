from enum import Enum

from telegram import Update
from telegram.ext import ContextTypes

import database as db
from keyboards import admin_menu, dealer_menu


class State(str, Enum):
    IDLE = "idle"

    ADM_ADD_TG = "adm_add_tg"
    ADM_ADD_NAME = "adm_add_name"
    ADM_ADD_INBOUND_ID = "adm_add_inbound_id"
    ADM_ADD_INBOUND_NAME = "adm_add_inbound_name"
    ADM_ADD_INBOUND_QUOTA = "adm_add_inbound_quota"
    ADM_ADD_MORE_INBOUND = "adm_add_more_inbound"

    ADM_FIND_TG = "adm_find_tg"
    ADM_QUOTA_INBOUND = "adm_quota_inbound"
    ADM_QUOTA_AMOUNT = "adm_quota_amount"

    CREATE_INBOUND = "create_inbound"
    CREATE_GB = "create_gb"
    CREATE_REMARK = "create_remark"

    RENEW_LINK = "renew_link"
    RENEW_GB = "renew_gb"

    CHECK_LINK = "check_link"


CANCEL_TEXT = "❌ انصراف"


def clear_state(context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("state", None)
    context.user_data.pop("draft", None)


def set_state(context: ContextTypes.DEFAULT_TYPE, state: State, **draft):
    context.user_data["state"] = state.value
    context.user_data.setdefault("draft", {}).update(draft)


def get_state(context: ContextTypes.DEFAULT_TYPE) -> State:
    val = context.user_data.get("state", State.IDLE.value)
    try:
        return State(val)
    except ValueError:
        return State.IDLE


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_state(context)
    user = update.effective_user
    if db.is_admin(user.id):
        await update.message.reply_text(
            "👋 سلام ادمین!\nاز منوی زیر مدیریت عمده‌فروشان را انجام دهید.",
            reply_markup=admin_menu(),
        )
        return

    dealer = db.get_dealer_by_telegram(user.id)
    if not dealer:
        await update.message.reply_text("⛔ شما دسترسی به این ربات ندارید.")
        return
    if dealer.is_blocked:
        await update.message.reply_text("🚫 حساب شما موقتاً مسدود شده است.")
        return

    await update.message.reply_text(
        f"👋 سلام {dealer.name}!\nاز منوی زیر استفاده کنید.",
        reply_markup=dealer_menu(),
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_state(context)
    user = update.effective_user
    if db.is_admin(user.id):
        await update.message.reply_text("انصراف.", reply_markup=admin_menu())
    else:
        await update.message.reply_text("انصراف.", reply_markup=dealer_menu())


def require_dealer(user_id: int):
    if db.is_admin(user_id):
        return None, "admin"
    dealer = db.get_dealer_by_telegram(user_id)
    if not dealer:
        return None, "no_access"
    if dealer.is_blocked:
        return None, "blocked"
    return dealer, "ok"
