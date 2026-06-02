import os
from urllib.parse import quote

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")


def parse_admin_ids(raw: str) -> frozenset[int]:
    """Parse comma-separated admin IDs."""
    ids: set[int] = set()
    for part in raw.replace("،", ",").split(","):
        part = part.strip().strip('"').strip("'")
        if not part:
            continue
        try:
            ids.add(int(part))
        except ValueError:
            continue
    if not ids:
        ids.add(7156306196)
    return frozenset(ids)


def admin_ids() -> frozenset[int]:
    """Reload ADMIN_ID from .env each time."""
    load_dotenv(override=True)
    return parse_admin_ids(os.getenv("ADMIN_ID", "7156306196"))


ADMIN_IDS = admin_ids()
ADMIN_ID = next(iter(ADMIN_IDS))

PANEL_URL = os.getenv("PANEL_URL", "").rstrip("/")
PANEL_USER = os.getenv("PANEL_USER", "")
PANEL_PASS = os.getenv("PANEL_PASS", "")
SUB_BASE_URL = os.getenv("SUB_BASE_URL", "").rstrip("/")
if SUB_BASE_URL:
    SUB_BASE_URL += "/"
DATABASE_PATH = os.getenv("DATABASE_PATH", "bot.db")

TELEGRAM_API_BASE = os.getenv("TELEGRAM_API_BASE", "").strip().rstrip("/") or None

GB = 1073741824


def _env_bool(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _socks_remote_dns() -> bool:
    """Return whether SOCKS proxy should resolve DNS remotely."""
    return _env_bool("TELEGRAM_PROXY_REMOTE_DNS", True)


def _normalize_socks_scheme(url_or_scheme: str) -> str:
    """Convert socks5 to socks5h when remote DNS is enabled."""
    if not _socks_remote_dns():
        return url_or_scheme
    if url_or_scheme == "socks5":
        return "socks5h"
    if url_or_scheme.startswith("socks5://"):
        return "socks5h://" + url_or_scheme[len("socks5://") :]
    return url_or_scheme


def build_telegram_proxy() -> str | None:
    """Build Telegram proxy URL from direct URL or structured fields."""
    direct = os.getenv("TELEGRAM_PROXY", "").strip()
    if direct:
        return _normalize_socks_scheme(direct)

    if not _env_bool("TELEGRAM_PROXY_ENABLED"):
        return None

    host = os.getenv("TELEGRAM_PROXY_HOST", "127.0.0.1").strip()
    port = os.getenv("TELEGRAM_PROXY_PORT", "1080").strip()
    ptype = os.getenv("TELEGRAM_PROXY_TYPE", "socks5").strip().lower()
    ptype = _normalize_socks_scheme(ptype)
    user = os.getenv("TELEGRAM_PROXY_USER", "").strip()
    passwd = os.getenv("TELEGRAM_PROXY_PASS", "").strip()

    if not host or not port:
        return None

    if user and passwd:
        return f"{ptype}://{quote(user, safe='')}:{quote(passwd, safe='')}@{host}:{port}"
    return f"{ptype}://{host}:{port}"


TELEGRAM_PROXY = build_telegram_proxy()


def proxy_log_label(proxy_url: str | None) -> str:
    """Mask password in proxy URL for logs."""
    if not proxy_url:
        return "none"
    if "@" in proxy_url and "://" in proxy_url:
        scheme, rest = proxy_url.split("://", 1)
        if "@" in rest:
            creds, hostpart = rest.rsplit("@", 1)
            if ":" in creds:
                user = creds.split(":", 1)[0]
                return f"{scheme}://{user}:***@{hostpart}"
    return proxy_url
