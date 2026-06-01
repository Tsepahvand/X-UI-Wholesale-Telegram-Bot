"""تنظیم HTTP تلگرام: پروکسی فقط برای Bot API (نه پنل)."""

import os
from typing import TYPE_CHECKING

import httpx
from telegram.request import HTTPXRequest

import config
from config import proxy_log_label

if TYPE_CHECKING:
    from telegram.ext import ApplicationBuilder


def _telegram_timeouts() -> dict[str, float]:
    return {
        "connect": float(os.getenv("TELEGRAM_CONNECT_TIMEOUT", "60")),
        "read": float(os.getenv("TELEGRAM_READ_TIMEOUT", "90")),
        "write": float(os.getenv("TELEGRAM_WRITE_TIMEOUT", "60")),
        "pool": float(os.getenv("TELEGRAM_POOL_TIMEOUT", "60")),
    }


def configure_application_builder(builder: "ApplicationBuilder") -> "ApplicationBuilder":
    """
    پروکسی و timeout روی هر دو request و get_updates_request (polling).
    از .request() سفارشی استفاده نمی‌کنیم تا getUpdates بدون پروکسی نماند.
    """
    t = _telegram_timeouts()
    builder = (
        builder.connect_timeout(t["connect"])
        .read_timeout(t["read"])
        .write_timeout(t["write"])
        .pool_timeout(t["pool"])
        .get_updates_connect_timeout(t["connect"])
        .get_updates_read_timeout(t["read"])
        .get_updates_write_timeout(t["write"])
        .get_updates_pool_timeout(t["pool"])
    )
    proxy = config.TELEGRAM_PROXY
    if proxy:
        builder = (
            builder.proxy(proxy)
            .get_updates_proxy(proxy)
            .connection_pool_size(4)
            .get_updates_connection_pool_size(1)
        )
    return builder


def build_telegram_request(*, for_updates: bool = False) -> HTTPXRequest:
    """برای تست یا استفاده دستی — همان تنظیمات builder."""
    t = _telegram_timeouts()
    proxy = config.TELEGRAM_PROXY
    pool = 1 if for_updates else 4
    limits = httpx.Limits(max_connections=pool, max_keepalive_connections=0)
    return HTTPXRequest(
        connection_pool_size=pool,
        connect_timeout=t["connect"],
        read_timeout=t["read"],
        write_timeout=t["write"],
        pool_timeout=t["pool"],
        proxy=proxy,
        httpx_kwargs={"limits": limits, "trust_env": False},
    )


def log_proxy_mode():
    if config.TELEGRAM_PROXY:
        import logging

        logging.getLogger(__name__).info(
            "Telegram-only proxy: %s (panel API direct, REMOTE_DNS=%s)",
            proxy_log_label(config.TELEGRAM_PROXY),
            config._socks_remote_dns(),
        )
