import io
from typing import Optional

import qrcode
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from database import DealerInbound


def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["➕ افزودن عمده‌فروش", "🔍 جستجوی عمده‌فروش"],
            ["📋 لیست عمده‌فروشان"],
        ],
        resize_keyboard=True,
    )


def dealer_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["🆕 ساخت", "♻️ تمدید"], ["🔎 بررسی", "👤 حساب من"]],
        resize_keyboard=True,
    )


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


def config_actions(config_id: int, enabled: bool) -> InlineKeyboardMarkup:
    toggle = "🔴 خاموش کردن" if enabled else "🟢 روشن کردن"
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(toggle, callback_data=f"cfg_toggle:{config_id}")],
            [InlineKeyboardButton("🗑 حذف کانفیگ", callback_data=f"cfg_del:{config_id}")],
            [InlineKeyboardButton("◀️ بازگشت", callback_data="cancel")],
        ]
    )


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
