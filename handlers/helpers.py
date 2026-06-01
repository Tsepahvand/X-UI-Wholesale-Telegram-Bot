import html
from datetime import datetime
from typing import Optional

import database as db
from database import DealerConfig
from keyboards import send_qr
from panel_client import (
    PanelError,
    fix_link_fragment,
    format_bytes,
    format_expiry_ms,
    panel,
    parse_client_name_from_link,
    parse_config_link,
    sub_url,
    to_panel_email,
)


async def send_config_package(
    message,
    inbound_id: int,
    email: str,
    sub_id: str,
    title: str,
    client_name: str,
):
    """Send config link, sub link, and QR codes."""
    inbound_remark = panel.get_inbound_remark(inbound_id)
    config_links = panel.get_client_links(inbound_id, email)
    sub = sub_url(sub_id)

    config_link = config_links[0] if config_links else "—"
    if config_link != "—":
        config_link = fix_link_fragment(config_link, inbound_remark, client_name)

    text = (
        f"✅ {html.escape(title)}\n\n"
        f"🔗 لینک کانفیگ:\n<code>{html.escape(config_link)}</code>\n\n"
        f"📡 لینک ساب:\n<code>{html.escape(sub)}</code>"
    )
    await message.reply_text(text, parse_mode="HTML")

    try:
        if config_link != "—":
            await send_qr(message, config_link, "📱 QR کانفیگ")
        await send_qr(message, sub, "📱 QR ساب")
    except Exception:
        await message.reply_text("⚠️ QR ارسال نشد — لینک‌ها بالا موجود است.")


def get_traffic_stats(email: str) -> dict:
    empty = {"up": 0, "down": 0, "total": 0, "used": 0}
    try:
        t = panel.get_client_traffic(email)
        if not isinstance(t, dict):
            return empty
        up = int(t.get("up", 0) or 0)
        down = int(t.get("down", 0) or 0)
        total = int(t.get("total", 0) or 0)
        return {"up": up, "down": down, "total": total, "used": up + down}
    except PanelError:
        return empty


def _last_online_timestamp(data, email: str) -> Optional[int]:
    """Panel returns either {email: ts} dict or [{email, lastOnline}, ...] list."""
    if isinstance(data, dict):
        if email in data:
            return int(data[email] or 0)
        return None
    if isinstance(data, list):
        for row in data:
            if isinstance(row, dict) and row.get("email") == email:
                return int(row.get("lastOnline", 0) or 0)
    return None


def get_last_online_str(email: str) -> str:
    try:
        data = panel.get_last_online()
        ts = _last_online_timestamp(data, email)
        if ts is None:
            return "نامشخص"
        if not ts:
            return "هرگز"
        return datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M")
    except (PanelError, TypeError, ValueError):
        pass
    return "نامشخص"


def get_client_expiry_str(inbound_id: int, client_uuid: str) -> str:
    try:
        client = panel._find_client_in_inbound(inbound_id, client_uuid)
        if not client:
            return "نامشخص"
        return format_expiry_ms(int(client.get("expiryTime") or 0))
    except (PanelError, TypeError, ValueError):
        return "نامشخص"


def format_config_report(cfg: DealerConfig) -> str:
    stats = get_traffic_stats(cfg.client_email)
    used = stats["used"]
    total = stats["total"] or cfg.total_bytes
    remaining = max(0, total - used)
    last = get_last_online_str(cfg.client_email)
    expiry = get_client_expiry_str(cfg.inbound_id, cfg.client_uuid)
    status = "🟢 فعال" if cfg.enabled else "🔴 غیرفعال"
    name = html.escape(cfg.remark or cfg.client_email)

    return (
        f"📛 نام: <b>{name}</b>\n"
        f"📧 ایمیل: <code>{html.escape(cfg.client_email)}</code>\n"
        f"وضعیت: {status}\n\n"
        f"📊 حجم کل: {format_bytes(total)}\n"
        f"📥 مصرف شده: {format_bytes(used)}\n"
        f"📦 باقی‌مانده: {format_bytes(remaining)}\n"
        f"📅 انقضا: {html.escape(expiry)}\n"
        f"🕐 آخرین اتصال: {html.escape(last)}"
    )


def resolve_config_from_link(link: str, dealer_id: int) -> Optional[DealerConfig]:
    link = link.strip()
    uuid = parse_config_link(link)

    if uuid:
        cfg = db.get_config_by_uuid(uuid)
        if cfg and cfg.dealer_id == dealer_id:
            return cfg

        allowed = [ib.inbound_id for ib in db.get_dealer_inbounds(dealer_id)]
        found = panel.find_client_by_uuid(uuid, allowed)
        if found:
            client = found["client"]
            if not isinstance(client, dict):
                return None
            email = client.get("email", "")
            display = email.lstrip("-") if email.startswith("-") else email
            link_name = parse_client_name_from_link(
                link, found.get("inbound_remark", "")
            )
            if link_name:
                display = link_name
            cfg = db.get_config_by_email(email)
            if cfg and cfg.dealer_id == dealer_id:
                return cfg
            return DealerConfig(
                id=0,
                dealer_id=dealer_id,
                inbound_id=found["inbound_id"],
                client_email=email,
                client_uuid=uuid,
                sub_id=client.get("subId", display),
                remark=display,
                total_bytes=int(client.get("totalGB", 0) or 0),
                enabled=bool(client.get("enable", True)),
            )

    for ib in db.get_dealer_inbounds(dealer_id):
        name = parse_client_name_from_link(link, panel.get_inbound_remark(ib.inbound_id))
        if name:
            cfg = db.get_config_by_remark(dealer_id, name)
            if cfg:
                return cfg
            cfg = db.get_config_by_email(to_panel_email(name))
            if cfg and cfg.dealer_id == dealer_id:
                return cfg

    return None


async def disable_all_dealer_configs(dealer_id: int) -> int:
    count = 0
    for cfg in db.get_dealer_configs(dealer_id):
        try:
            panel.set_client_enabled(cfg.inbound_id, cfg.client_uuid, False)
            db.set_config_enabled(cfg.id, False)
            count += 1
        except PanelError:
            pass
    return count
