"""Runtime bot settings (DB-backed) for features and config naming."""

from __future__ import annotations

import database as db
from panel_client import random_client_name, random_sub_id_in_range

# Feature flags (stored as "0" / "1")
FEAT_CREATE = "feat_create"
FEAT_RENEW = "feat_renew"
FEAT_CHECK = "feat_check"
FEAT_ACCOUNT = "feat_account"
FEAT_CONFIG_TOGGLE = "feat_config_toggle"
FEAT_CONFIG_DELETE = "feat_config_delete"

# Naming
CLIENT_NAME_MODE = "client_name_mode"  # ask | random | ask_or_random
SUB_ID_MODE = "sub_id_mode"  # same_as_name | random | name_random_sub
SUB_RANDOM_MIN = "sub_random_min_len"
SUB_RANDOM_MAX = "sub_random_max_len"

DEFAULTS: dict[str, str] = {
    FEAT_CREATE: "1",
    FEAT_RENEW: "1",
    FEAT_CHECK: "1",
    FEAT_ACCOUNT: "1",
    FEAT_CONFIG_TOGGLE: "1",
    FEAT_CONFIG_DELETE: "1",
    CLIENT_NAME_MODE: "ask_or_random",
    SUB_ID_MODE: "same_as_name",
    SUB_RANDOM_MIN: "8",
    SUB_RANDOM_MAX: "12",
}

CLIENT_NAME_MODES = ("ask", "random", "ask_or_random")
SUB_ID_MODES = ("same_as_name", "random", "name_random_sub")

CLIENT_NAME_LABELS = {
    "ask": "نام از کاربر (بدون /random)",
    "random": "نام تصادفی خودکار",
    "ask_or_random": "نام از کاربر + /random",
}

SUB_ID_LABELS = {
    "same_as_name": "ساب = همان نام کانفیگ",
    "random": "ساب تصادفی (۸–۱۲ کاراکتر)",
    "name_random_sub": "نام از فروشنده، ساب تصادفی",
}


def is_enabled(key: str) -> bool:
    return db.get_setting(key, DEFAULTS.get(key, "1")) == "1"


def get_client_name_mode() -> str:
    val = db.get_setting(CLIENT_NAME_MODE, DEFAULTS[CLIENT_NAME_MODE])
    return val if val in CLIENT_NAME_MODES else "ask_or_random"


def get_sub_id_mode() -> str:
    val = db.get_setting(SUB_ID_MODE, DEFAULTS[SUB_ID_MODE])
    return val if val in SUB_ID_MODES else "same_as_name"


def get_sub_random_bounds() -> tuple[int, int]:
    try:
        lo = int(db.get_setting(SUB_RANDOM_MIN, "8"))
        hi = int(db.get_setting(SUB_RANDOM_MAX, "12"))
    except ValueError:
        lo, hi = 8, 12
    lo = max(4, min(lo, 32))
    hi = max(lo, min(hi, 32))
    return lo, hi


def cycle_client_name_mode() -> str:
    modes = CLIENT_NAME_MODES
    cur = get_client_name_mode()
    nxt = modes[(modes.index(cur) + 1) % len(modes)]
    db.set_setting(CLIENT_NAME_MODE, nxt)
    return nxt


def cycle_sub_id_mode() -> str:
    modes = SUB_ID_MODES
    cur = get_sub_id_mode()
    nxt = modes[(modes.index(cur) + 1) % len(modes)]
    db.set_setting(SUB_ID_MODE, nxt)
    return nxt


def toggle_feature(key: str) -> bool:
    new_val = "0" if is_enabled(key) else "1"
    db.set_setting(key, new_val)
    return new_val == "1"


def dealer_menu_rows() -> list[list[str]]:
    rows: list[list[str]] = []
    r1: list[str] = []
    if is_enabled(FEAT_CREATE):
        r1.append("🆕 ساخت")
    if is_enabled(FEAT_RENEW):
        r1.append("♻️ تمدید")
    if r1:
        rows.append(r1)
    r2: list[str] = []
    if is_enabled(FEAT_CHECK):
        r2.append("🔎 بررسی")
    if is_enabled(FEAT_ACCOUNT):
        r2.append("👤 حساب من")
    if r2:
        rows.append(r2)
    if not rows:
        rows = [["ℹ️ بخشی فعال نیست"]]
    return rows


def _flag(enabled: bool) -> str:
    return "✅" if enabled else "❌"


def format_settings_home() -> str:
    lo, hi = get_sub_random_bounds()
    return "\n".join(
        [
            "⚙️ <b>تنظیمات ربات</b>",
            "",
            "یک دسته را انتخاب کنید:",
            "",
            "📱 <b>دکمه‌های منو</b> — نمایش بخش‌ها در منوی فروشنده",
            "🔧 <b>عملیات کانفیگ</b> — خاموش/روشن و حذف بعد از بررسی",
            "🆕 <b>ساخت کانفیگ</b> — نام، ساب‌آیدی و طول تصادفی",
            "",
            "<i>خلاصه وضعیت فعلی:</i>",
            f"منو: {_flag(is_enabled(FEAT_CREATE))} ساخت · {_flag(is_enabled(FEAT_RENEW))} تمدید · "
            f"{_flag(is_enabled(FEAT_CHECK))} بررسی · {_flag(is_enabled(FEAT_ACCOUNT))} حساب",
            f"عملیات: {_flag(is_enabled(FEAT_CONFIG_TOGGLE))} خاموش/روشن · "
            f"{_flag(is_enabled(FEAT_CONFIG_DELETE))} حذف",
            f"ساخت: {CLIENT_NAME_LABELS[get_client_name_mode()]} | "
            f"{SUB_ID_LABELS[get_sub_id_mode()]} ({lo}–{hi})",
        ]
    )


def format_settings_menu_section() -> str:
    return "\n".join(
        [
            "📱 <b>تنظیمات دکمه‌های منو</b>",
            "",
            "بخش‌های غیرفعال از منوی عمده‌فروش حذف می‌شوند.",
            "فروشنده باید <code>/start</code> بزند تا منو به‌روز شود.",
            "",
            f"{_flag(is_enabled(FEAT_CREATE))} <b>ساخت کانفیگ</b>",
            f"{_flag(is_enabled(FEAT_RENEW))} <b>تمدید</b>",
            f"{_flag(is_enabled(FEAT_CHECK))} <b>بررسی کانفیگ</b>",
            f"{_flag(is_enabled(FEAT_ACCOUNT))} <b>حساب من</b>",
        ]
    )


def format_settings_config_section() -> str:
    return "\n".join(
        [
            "🔧 <b>تنظیمات عملیات کانفیگ</b>",
            "",
            "پس از ارسال لینک در بخش «بررسی»، دکمه‌های زیر نمایش داده می‌شوند.",
            "(اگر «بررسی» در منو خاموش باشد، این بخش در دسترس نیست.)",
            "",
            f"{_flag(is_enabled(FEAT_CONFIG_TOGGLE))} <b>خاموش / روشن کردن</b>",
            f"{_flag(is_enabled(FEAT_CONFIG_DELETE))} <b>حذف کانفیگ</b>",
        ]
    )


def format_settings_create_section() -> str:
    lo, hi = get_sub_random_bounds()
    return "\n".join(
        [
            "🆕 <b>تنظیمات ساخت کانفیگ</b>",
            "",
            "<b>نام کانفیگ (remark)</b>",
            f"• {CLIENT_NAME_LABELS[get_client_name_mode()]}",
            "",
            "<b>ساب‌آیدی (Subscription)</b>",
            f"• {SUB_ID_LABELS[get_sub_id_mode()]}",
            f"• طول تصادفی: <b>{lo}–{hi}</b> کاراکتر",
        ]
    )


def format_settings_section(section: str) -> str:
    if section == "menu":
        return format_settings_menu_section()
    if section == "config":
        return format_settings_config_section()
    if section == "create":
        return format_settings_create_section()
    return format_settings_home()


def unique_random_sub_for_dealer(dealer_id: int) -> str:
    lo, hi = get_sub_random_bounds()
    for _ in range(30):
        sid = random_sub_id_in_range(lo, hi)
        if not db.dealer_sub_id_exists(dealer_id, sid):
            return sid
    raise RuntimeError("نتوانست ساب‌آیدی یکتا ساخت.")


def resolve_sub_id(dealer_id: int, display_name: str) -> str:
    mode = get_sub_id_mode()
    if mode == "same_as_name":
        return display_name
    return unique_random_sub_for_dealer(dealer_id)


def should_skip_name_prompt() -> bool:
    return get_client_name_mode() == "random"


def create_remark_prompt() -> str:
    mode = get_client_name_mode()
    sub = SUB_ID_LABELS[get_sub_id_mode()]
    if mode == "ask":
        return (
            "📛 نام کانفیگ را وارد کنید:\n"
            f"• نحوه ساب: {sub}\n"
            "• تکراری بودن فقط بین کانفیگ‌های خودتان چک می‌شود"
        )
    return (
        "📛 نام کانفیگ را وارد کنید:\n"
        f"• نحوه ساب: {sub}\n"
        "• تکراری بودن فقط بین کانفیگ‌های خودتان چک می‌شود\n"
        "• برای نام تصادفی: /random"
    )


def random_display_name_for_dealer(dealer_id: int) -> str:
    for _ in range(30):
        name = random_client_name()
        if not db.dealer_config_name_exists(dealer_id, name):
            return name
    raise RuntimeError("نتوانست نام یکتا ساخت.")
