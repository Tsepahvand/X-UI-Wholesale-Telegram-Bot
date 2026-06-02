#!/usr/bin/env python3
"""3X-UI wholesale dealer Telegram bot."""

import logging
import sys
import time

from telegram import Update
from telegram.error import NetworkError, TimedOut
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
import config
import database as db
from telegram_http import configure_application_builder, log_proxy_mode
from handlers.admin import handle_admin_callback, handle_admin_message
from handlers.common import cancel, start
from handlers.dealer_ops import handle_dealer_callback, handle_dealer_message, handle_random_command
from panel_client import PanelError, panel
from requests.exceptions import RequestException

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_START_RETRIES = 15
TELEGRAM_START_DELAY = 5


def build_application() -> Application:
    log_proxy_mode()

    builder = configure_application_builder(
        Application.builder().token(config.BOT_TOKEN)
    )

    if config.TELEGRAM_API_BASE:
        base = config.TELEGRAM_API_BASE
        builder = builder.base_url(f"{base}/bot").base_file_url(f"{base}/file/bot")
        logger.info("Using custom Telegram API: %s", base)

    app = builder.build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("random", handle_random_command))
    app.add_handler(CallbackQueryHandler(route_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route_message))
    app.add_error_handler(error_handler)

    return app


async def route_message(update, context):
    if not update.message or not update.message.text:
        return

    if await handle_admin_message(update, context):
        return
    if await handle_dealer_message(update, context):
        return

    user = update.effective_user
    if db.is_admin(user.id):
        return
    dealer = db.get_dealer_by_telegram(user.id)
    if dealer and dealer.is_blocked:
        await update.message.reply_text("🚫 حساب شما temporary block شده است.")
        return
    if not dealer:
        inactive = db.get_dealer_by_telegram_any(user.id)
        if inactive and not inactive.is_active:
            await update.message.reply_text(
                "⛔ دسترسی wholesale شما revoke شده است.\n"
                "اگر Admin هستید، ID خود را در `.env` -> `ADMIN_ID` بگذارید و `/start` بزنید."
            )
        else:
            await update.message.reply_text("⛔ Access ندارید. شما مجاز به استفاده از bot نیستید.")


async def route_callback(update, context):
    if await handle_admin_callback(update, context):
        return
    await handle_dealer_callback(update, context)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    err = context.error
    if isinstance(err, (TimedOut, NetworkError)):
        logger.warning("Telegram network error: %s", err)
        return
    if isinstance(err, (PanelError, RequestException)):
        logger.warning("Panel/network error: %s", err)
        msg = str(err) if isinstance(err, PanelError) else "خطا در ارتباط با پنل."
        if update and isinstance(update, Update):
            try:
                if update.effective_message:
                    await update.effective_message.reply_text(f"❌ {msg}")
                elif update.callback_query:
                    await update.callback_query.message.reply_text(f"❌ {msg}")
            except Exception:
                pass
        return
    logger.exception("Unhandled error: %s", err)


def _print_telegram_help():
    print(
        "\n❌ Telegram connection failed (api.telegram.org).\n\n"
        "Set proxy in your .env:\n\n"
        "  # SOCKS5 without auth:\n"
        "  TELEGRAM_PROXY_ENABLED=true\n"
        "  TELEGRAM_PROXY_TYPE=socks5\n"
        "  TELEGRAM_PROXY_HOST=127.0.0.1\n"
        "  TELEGRAM_PROXY_PORT=1080\n\n"
        "  # SOCKS5 with username/password:\n"
        "  TELEGRAM_PROXY_ENABLED=true\n"
        "  TELEGRAM_PROXY_HOST=proxy.example.com\n"
        "  TELEGRAM_PROXY_PORT=1080\n"
        "  TELEGRAM_PROXY_USER=myuser\n"
        "  TELEGRAM_PROXY_PASS=mypassword\n\n"
        "  # Or full URL:\n"
        "  TELEGRAM_PROXY=socks5h://user:pass@host:1080\n\n"
        "  Tip: for restricted Telegram routes, use socks5h (default).\n"
        "  TELEGRAM_PROXY_REMOTE_DNS=false -> plain socks5\n\n"
        "Then run: ./run.sh\n"
    )


def run_polling_with_retry():
    """هر تلاش Application جدید — جلوگیری از Event loop is closed بعد از خطا."""
    for attempt in range(1, TELEGRAM_START_RETRIES + 1):
        try:
            logger.info("Connecting to Telegram (attempt %d/%d)...", attempt, TELEGRAM_START_RETRIES)
            app = build_application()
            app.run_polling(
                allowed_updates=["message", "callback_query"],
                drop_pending_updates=True,
                timeout=25,
                poll_interval=1.0,
                bootstrap_retries=5,
            )
            return
        except NetworkError as e:
            logger.warning("Telegram unreachable: %s", e)
            if attempt >= TELEGRAM_START_RETRIES:
                _print_telegram_help()
                sys.exit(1)
            time.sleep(TELEGRAM_START_DELAY)


def main():
    if not config.BOT_TOKEN:
        print("❌ BOT_TOKEN is not set in .env.")
        sys.exit(1)

    db.init_db()

    try:
        panel.login()
        logger.info("Panel login OK")
    except (PanelError, RequestException) as e:
        logger.warning("Panel login failed at startup: %s", e)

    logger.info(
        "Bot starting. Admin IDs: %s",
        ", ".join(str(i) for i in sorted(config.admin_ids())),
    )
    run_polling_with_retry()


if __name__ == "__main__":
    main()
