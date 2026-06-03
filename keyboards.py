import io
from typing import Optional

import qrcode
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

import bot_settings as bs
from database import DealerInbound


def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["➕ افزودن عمده‌فروش", "🔍 جستجوی عمده‌فروش"],
            ["📋 لیست عمده‌فروشان", "⚙️ تنظیمات ربات"],
        ],
        resize_keyboard=True,
    )


def dealer_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(bs.dealer_menu_rows(), resize_keyboard=True)


def _bset_on(key: str) -> str:
    return "✅" if bs.is_enabled(key) else "❌"


def _bset_back_home() -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton("◀️ بازگشت به تنظیمات", callback_data="bset:home")]


def admin_bot_settings_home_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📱 دکمه‌های منو", callback_data="bset:sec:menu")],
            [InlineKeyboardButton("🔧 عملیات کانفیگ", callback_data="bset:sec:config")],
            [InlineKeyboardButton("🆕 ساخت کانفیگ", callback_data="bset:sec:create")],
            [InlineKeyboardButton("🔄 بروزرسانی خلاصه", callback_data="bset:home")],
        ]
    )


def admin_bot_settings_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"{_bset_on(bs.FEAT_CREATE)} ساخت کانفیگ", callback_data="bset:fc"
                ),
            ],
            [
                InlineKeyboardButton(
                    f"{_bset_on(bs.FEAT_RENEW)} تمدید", callback_data="bset:fr"
                ),
            ],
            [
                InlineKeyboardButton(
                    f"{_bset_on(bs.FEAT_CHECK)} بررسی", callback_data="bset:fch"
                ),
            ],
            [
                InlineKeyboardButton(
                    f"{_bset_on(bs.FEAT_ACCOUNT)} حساب من", callback_data="bset:fa"
                ),
            ],
            _bset_back_home(),
        ]
    )


def admin_bot_settings_config_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"{_bset_on(bs.FEAT_CONFIG_TOGGLE)} خاموش / روشن",
                    callback_data="bset:fct",
                ),
            ],
            [
                InlineKeyboardButton(
                    f"{_bset_on(bs.FEAT_CONFIG_DELETE)} حذف کانفیگ",
                    callback_data="bset:fcd",
                ),
            ],
            _bset_back_home(),
        ]
    )


def admin_bot_settings_create_kb() -> InlineKeyboardMarkup:
    cn = bs.CLIENT_NAME_LABELS[bs.get_client_name_mode()]
    sub = bs.SUB_ID_LABELS[bs.get_sub_id_mode()]
    lo, hi = bs.get_sub_random_bounds()
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"📛 نام: {cn[:28]}", callback_data="bset:cn")],
            [InlineKeyboardButton(f"🔗 ساب: {sub[:28]}", callback_data="bset:sub")],
            [
                InlineKeyboardButton(
                    f"📏 طول ساب تصادفی: {lo}–{hi}", callback_data="bset:slen"
                ),
            ],
            _bset_back_home(),
        ]
    )


def admin_bot_settings_kb(section: str = "home") -> InlineKeyboardMarkup:
    if section == "menu":
        return admin_bot_settings_menu_kb()
    if section == "config":
        return admin_bot_settings_config_kb()
    if section == "create":
        return admin_bot_settings_create_kb()
    return admin_bot_settings_home_kb()


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([["❌ انصراف"]], resize_keyboard=True)


def inbound_choice(inbounds: list[DealerInbound]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                f"{ib.display_name} ({_avail_label(ib)})",
                callback_data=f"inbound:{ib.inbound_id}",
            )
        ]
        for ib in inbounds
    ]
    rows.append([InlineKeyboardButton("❌ انصراف", callback_data="cancel")])
    return InlineKeyboardMarkup(rows)


def config_actions(config_id: int, enabled: bool) -> Optional[InlineKeyboardMarkup]:
    rows = []
    if bs.is_enabled(bs.FEAT_CONFIG_TOGGLE):
        toggle = "🔴 خاموش کردن" if enabled else "🟢 روشن کردن"
        rows.append(
            [InlineKeyboardButton(toggle, callback_data=f"cfg_toggle:{config_id}")]
        )
    if bs.is_enabled(bs.FEAT_CONFIG_DELETE):
        rows.append(
            [InlineKeyboardButton("🗑 حذف کانفیگ", callback_data=f"cfg_del:{config_id}")]
        )
    if not rows:
        return None
    rows.append([InlineKeyboardButton("◀️ بازگشت", callback_data="cancel")])
    return InlineKeyboardMarkup(rows)


def admin_dealer_actions(dealer_id: int, blocked: bool) -> InlineKeyboardMarkup:
    block_label = "✅ رفع بلاک" if blocked else "🚫 بلاک موقت"
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📡 مدیریت اینباندها",
                    callback_data=f"adm_ibm:{dealer_id}",
                )
            ],
            [InlineKeyboardButton(block_label, callback_data=f"adm_block:{dealer_id}")],
            [
                InlineKeyboardButton(
                    "🔌 خاموش کردن همه کانفیگ‌ها",
                    callback_data=f"adm_disable_all:{dealer_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "➕ افزایش حجم اینباند", callback_data=f"adm_quota_add:{dealer_id}"
                ),
                InlineKeyboardButton(
                    "➖ کاهش حجم اینباند", callback_data=f"adm_quota_sub:{dealer_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    "🗑 حذف فروشنده", callback_data=f"adm_revoke:{dealer_id}"
                )
            ],
        ]
    )


def admin_inbounds_menu(dealer_id: int, inbounds: list[DealerInbound]) -> InlineKeyboardMarkup:
    rows = []
    for ib in inbounds:
        rows.append(
            [
                InlineKeyboardButton(
                    f"✏️ {ib.display_name} (id={ib.inbound_id})",
                    callback_data=f"adm_ibe:{dealer_id}:{ib.inbound_id}",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                "➕ افزودن اینباند",
                callback_data=f"adm_iba:{dealer_id}",
            )
        ]
    )
    rows.append(
        [InlineKeyboardButton("◀️ بازگشت به پروفایل", callback_data=f"adm_ibp:{dealer_id}")]
    )
    return InlineKeyboardMarkup(rows)


def admin_inbound_edit_menu(
    dealer_id: int, inbound_id: int, display_name: str
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🏷 نام نمایشی",
                    callback_data=f"adm_iben:{dealer_id}:{inbound_id}",
                ),
                InlineKeyboardButton(
                    "📦 سقف حجم (GB)",
                    callback_data=f"adm_ibeq:{dealer_id}:{inbound_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "📅 روز اعتبار کانفیگ",
                    callback_data=f"adm_ibed:{dealer_id}:{inbound_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🗑 حذف اینباند",
                    callback_data=f"adm_ibr:{dealer_id}:{inbound_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "◀️ بازگشت",
                    callback_data=f"adm_ibm:{dealer_id}",
                )
            ],
        ]
    )


def confirm_kb(action: str, entity_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ بله", callback_data=f"confirm:{action}:{entity_id}"),
                InlineKeyboardButton("❌ خیر", callback_data="cancel"),
            ]
        ]
    )


def _avail_label(ib: DealerInbound) -> str:
    from panel_client import format_bytes

    avail = ib.quota_bytes - ib.used_bytes
    return f"باقی: {format_bytes(avail)}"


async def send_qr(update_or_query, text: str, caption: str):
    """Send QR code as photo. Works with Message or CallbackQuery."""
    buf = io.BytesIO()
    qr = qrcode.make(text)
    qr.save(buf, format="PNG")
    buf.seek(0)
    buf.name = "qr.png"

    if hasattr(update_or_query, "message") and update_or_query.message:
        await update_or_query.message.reply_photo(buf, caption=caption)
    else:
        await update_or_query.reply_photo(buf, caption=caption)
