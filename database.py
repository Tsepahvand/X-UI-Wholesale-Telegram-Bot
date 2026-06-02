import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional

import config


@dataclass
class Dealer:
    id: int
    telegram_id: int
    name: str
    is_blocked: bool
    is_active: bool


@dataclass
class DealerInbound:
    id: int
    dealer_id: int
    inbound_id: int
    display_name: str
    quota_bytes: int
    used_bytes: int
    config_days: int


@dataclass
class DealerConfig:
    id: int
    dealer_id: int
    inbound_id: int
    client_email: str
    client_uuid: str
    sub_id: str
    remark: str
    total_bytes: int
    enabled: bool


@contextmanager
def _conn():
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS dealers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                name TEXT NOT NULL,
                is_blocked INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS dealer_inbounds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dealer_id INTEGER NOT NULL,
                inbound_id INTEGER NOT NULL,
                display_name TEXT NOT NULL,
                quota_bytes INTEGER NOT NULL DEFAULT 0,
                used_bytes INTEGER NOT NULL DEFAULT 0,
                config_days INTEGER NOT NULL DEFAULT 0,
                UNIQUE(dealer_id, inbound_id),
                FOREIGN KEY (dealer_id) REFERENCES dealers(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS dealer_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dealer_id INTEGER NOT NULL,
                inbound_id INTEGER NOT NULL,
                client_email TEXT NOT NULL,
                client_uuid TEXT NOT NULL,
                sub_id TEXT NOT NULL,
                remark TEXT NOT NULL,
                total_bytes INTEGER NOT NULL,
                enabled INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dealer_id) REFERENCES dealers(id) ON DELETE CASCADE
            );
            """
        )
        _migrate_dealer_inbounds(conn)


def _migrate_dealer_inbounds(conn: sqlite3.Connection):
    cols = {row[1] for row in conn.execute("PRAGMA table_info(dealer_inbounds)").fetchall()}
    if "config_days" not in cols:
        conn.execute(
            "ALTER TABLE dealer_inbounds ADD COLUMN config_days INTEGER NOT NULL DEFAULT 0"
        )


def is_admin(telegram_id: int) -> bool:
    return telegram_id in config.admin_ids()


def get_dealer_by_telegram_any(telegram_id: int) -> Optional[Dealer]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM dealers WHERE telegram_id = ?",
            (telegram_id,),
        ).fetchone()
        if not row:
            return None
        return Dealer(
            id=row["id"],
            telegram_id=row["telegram_id"],
            name=row["name"],
            is_blocked=bool(row["is_blocked"]),
            is_active=bool(row["is_active"]),
        )


def get_dealer_by_telegram(telegram_id: int) -> Optional[Dealer]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM dealers WHERE telegram_id = ? AND is_active = 1",
            (telegram_id,),
        ).fetchone()
        if not row:
            return None
        return Dealer(
            id=row["id"],
            telegram_id=row["telegram_id"],
            name=row["name"],
            is_blocked=bool(row["is_blocked"]),
            is_active=bool(row["is_active"]),
        )


def get_dealer_by_id(dealer_id: int) -> Optional[Dealer]:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM dealers WHERE id = ?", (dealer_id,)).fetchone()
        if not row:
            return None
        return Dealer(
            id=row["id"],
            telegram_id=row["telegram_id"],
            name=row["name"],
            is_blocked=bool(row["is_blocked"]),
            is_active=bool(row["is_active"]),
        )


def create_dealer(telegram_id: int, name: str) -> Dealer:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT OR REPLACE INTO dealers (telegram_id, name, is_blocked, is_active) VALUES (?, ?, 0, 1)",
            (telegram_id, name),
        )
        dealer_id = cur.lastrowid
        if not dealer_id:
            row = conn.execute(
                "SELECT id FROM dealers WHERE telegram_id = ?", (telegram_id,)
            ).fetchone()
            dealer_id = row["id"]
            conn.execute(
                "UPDATE dealers SET name = ?, is_active = 1, is_blocked = 0 WHERE id = ?",
                (name, dealer_id),
            )
    return get_dealer_by_id(dealer_id)


def add_dealer_inbound(
    dealer_id: int,
    inbound_id: int,
    display_name: str,
    quota_bytes: int,
    config_days: int = 0,
) -> DealerInbound:
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO dealer_inbounds
                (dealer_id, inbound_id, display_name, quota_bytes, used_bytes, config_days)
            VALUES (?, ?, ?, ?, 0, ?)
            ON CONFLICT(dealer_id, inbound_id) DO UPDATE SET
                display_name = excluded.display_name,
                quota_bytes = excluded.quota_bytes,
                config_days = excluded.config_days
            """,
            (dealer_id, inbound_id, display_name, quota_bytes, config_days),
        )
    return get_dealer_inbound(dealer_id, inbound_id)


def get_dealer_inbounds(dealer_id: int) -> list[DealerInbound]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM dealer_inbounds WHERE dealer_id = ? ORDER BY id",
            (dealer_id,),
        ).fetchall()
    return [_row_to_inbound(r) for r in rows]


def get_dealer_inbound(dealer_id: int, inbound_id: int) -> Optional[DealerInbound]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM dealer_inbounds WHERE dealer_id = ? AND inbound_id = ?",
            (dealer_id, inbound_id),
        ).fetchone()
    return _row_to_inbound(row) if row else None


def update_dealer_inbound(
    dealer_id: int,
    inbound_id: int,
    *,
    display_name: Optional[str] = None,
    quota_bytes: Optional[int] = None,
    config_days: Optional[int] = None,
) -> Optional[DealerInbound]:
    ib = get_dealer_inbound(dealer_id, inbound_id)
    if not ib:
        return None
    if display_name is not None:
        ib = DealerInbound(
            id=ib.id,
            dealer_id=ib.dealer_id,
            inbound_id=ib.inbound_id,
            display_name=display_name,
            quota_bytes=ib.quota_bytes,
            used_bytes=ib.used_bytes,
            config_days=ib.config_days,
        )
    if quota_bytes is not None:
        ib = DealerInbound(
            id=ib.id,
            dealer_id=ib.dealer_id,
            inbound_id=ib.inbound_id,
            display_name=ib.display_name,
            quota_bytes=quota_bytes,
            used_bytes=ib.used_bytes,
            config_days=ib.config_days,
        )
    if config_days is not None:
        ib = DealerInbound(
            id=ib.id,
            dealer_id=ib.dealer_id,
            inbound_id=ib.inbound_id,
            display_name=ib.display_name,
            quota_bytes=ib.quota_bytes,
            used_bytes=ib.used_bytes,
            config_days=config_days,
        )
    with _conn() as conn:
        conn.execute(
            """
            UPDATE dealer_inbounds
            SET display_name = ?, quota_bytes = ?, config_days = ?
            WHERE dealer_id = ? AND inbound_id = ?
            """,
            (ib.display_name, ib.quota_bytes, ib.config_days, dealer_id, inbound_id),
        )
    return get_dealer_inbound(dealer_id, inbound_id)


def set_dealer_inbound_quota(
    dealer_id: int, inbound_id: int, quota_bytes: int
) -> tuple[bool, str]:
    """Set total quota and keep it >= used_bytes."""
    ib = get_dealer_inbound(dealer_id, inbound_id)
    if not ib:
        return False, "اینباند یافت نشد."
    if quota_bytes < ib.used_bytes:
        return False, "سقف نمی‌تواند کمتر از حجم تخصیص‌یافته باشد."
    update_dealer_inbound(dealer_id, inbound_id, quota_bytes=quota_bytes)
    return True, ""


def remove_dealer_inbound(dealer_id: int, inbound_id: int) -> bool:
    with _conn() as conn:
        cur = conn.execute(
            "DELETE FROM dealer_inbounds WHERE dealer_id = ? AND inbound_id = ?",
            (dealer_id, inbound_id),
        )
        return cur.rowcount > 0


def count_configs_on_inbound(dealer_id: int, inbound_id: int) -> int:
    with _conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM dealer_configs WHERE dealer_id = ? AND inbound_id = ?",
            (dealer_id, inbound_id),
        ).fetchone()
    return int(row["c"]) if row else 0


def adjust_inbound_quota(dealer_id: int, inbound_id: int, delta_bytes: int):
    with _conn() as conn:
        conn.execute(
            "UPDATE dealer_inbounds SET quota_bytes = quota_bytes + ? WHERE dealer_id = ? AND inbound_id = ?",
            (delta_bytes, dealer_id, inbound_id),
        )


def reserve_quota(dealer_id: int, inbound_id: int, bytes_amount: int) -> bool:
    with _conn() as conn:
        row = conn.execute(
            "SELECT quota_bytes, used_bytes FROM dealer_inbounds WHERE dealer_id = ? AND inbound_id = ?",
            (dealer_id, inbound_id),
        ).fetchone()
        if not row:
            return False
        available = row["quota_bytes"] - row["used_bytes"]
        if bytes_amount > available:
            return False
        conn.execute(
            "UPDATE dealer_inbounds SET used_bytes = used_bytes + ? WHERE dealer_id = ? AND inbound_id = ?",
            (bytes_amount, dealer_id, inbound_id),
        )
        return True


def release_quota(dealer_id: int, inbound_id: int, bytes_amount: int):
    with _conn() as conn:
        conn.execute(
            """
            UPDATE dealer_inbounds SET used_bytes = MAX(0, used_bytes - ?)
            WHERE dealer_id = ? AND inbound_id = ?
            """,
            (bytes_amount, dealer_id, inbound_id),
        )


def add_config(cfg: DealerConfig) -> int:
    with _conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO dealer_configs
            (dealer_id, inbound_id, client_email, client_uuid, sub_id, remark, total_bytes, enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cfg.dealer_id,
                cfg.inbound_id,
                cfg.client_email,
                cfg.client_uuid,
                cfg.sub_id,
                cfg.remark,
                cfg.total_bytes,
                int(cfg.enabled),
            ),
        )
        return cur.lastrowid


def get_config_by_uuid(client_uuid: str) -> Optional[DealerConfig]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM dealer_configs WHERE client_uuid = ?", (client_uuid,)
        ).fetchone()
    return _row_to_config(row) if row else None


def get_config_by_id(config_id: int) -> Optional[DealerConfig]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM dealer_configs WHERE id = ?", (config_id,)
        ).fetchone()
    return _row_to_config(row) if row else None


def get_config_by_email(email: str) -> Optional[DealerConfig]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM dealer_configs WHERE client_email = ?", (email,)
        ).fetchone()
    return _row_to_config(row) if row else None


def dealer_config_name_exists(dealer_id: int, display_name: str) -> bool:
    """True if this dealer already has a bot-created config with the same display name."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM dealer_configs WHERE dealer_id = ? AND remark = ? LIMIT 1",
            (dealer_id, display_name),
        ).fetchone()
        return row is not None


def get_config_by_remark(dealer_id: int, remark: str) -> Optional[DealerConfig]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM dealer_configs WHERE dealer_id = ? AND remark = ? LIMIT 1",
            (dealer_id, remark),
        ).fetchone()
    return _row_to_config(row) if row else None


def get_dealer_configs(dealer_id: int) -> list[DealerConfig]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM dealer_configs WHERE dealer_id = ? ORDER BY id DESC",
            (dealer_id,),
        ).fetchall()
    return [_row_to_config(r) for r in rows]


def update_config_total(config_id: int, new_total: int):
    with _conn() as conn:
        conn.execute(
            "UPDATE dealer_configs SET total_bytes = ? WHERE id = ?",
            (new_total, config_id),
        )


def set_config_enabled(config_id: int, enabled: bool):
    with _conn() as conn:
        conn.execute(
            "UPDATE dealer_configs SET enabled = ? WHERE id = ?",
            (int(enabled), config_id),
        )


def delete_config(config_id: int):
    with _conn() as conn:
        conn.execute("DELETE FROM dealer_configs WHERE id = ?", (config_id,))


def set_dealer_blocked(dealer_id: int, blocked: bool):
    with _conn() as conn:
        conn.execute(
            "UPDATE dealers SET is_blocked = ? WHERE id = ?", (int(blocked), dealer_id)
        )


def revoke_dealer(dealer_id: int):
    with _conn() as conn:
        conn.execute("UPDATE dealers SET is_active = 0 WHERE id = ?", (dealer_id,))


def delete_dealer(dealer_id: int) -> bool:
    with _conn() as conn:
        cur = conn.execute("DELETE FROM dealers WHERE id = ?", (dealer_id,))
        return cur.rowcount > 0


def list_dealers() -> list[Dealer]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM dealers WHERE is_active = 1 ORDER BY id DESC"
        ).fetchall()
    return [
        Dealer(
            id=r["id"],
            telegram_id=r["telegram_id"],
            name=r["name"],
            is_blocked=bool(r["is_blocked"]),
            is_active=bool(r["is_active"]),
        )
        for r in rows
    ]


def _row_to_inbound(row) -> DealerInbound:
    keys = row.keys()
    config_days = int(row["config_days"]) if "config_days" in keys else 0
    return DealerInbound(
        id=row["id"],
        dealer_id=row["dealer_id"],
        inbound_id=row["inbound_id"],
        display_name=row["display_name"],
        quota_bytes=row["quota_bytes"],
        used_bytes=row["used_bytes"],
        config_days=config_days,
    )


def format_config_days_label(days: int) -> str:
    if days <= 0:
        return "نامحدود"
    return f"{days} روز"


def _row_to_config(row) -> DealerConfig:
    return DealerConfig(
        id=row["id"],
        dealer_id=row["dealer_id"],
        inbound_id=row["inbound_id"],
        client_email=row["client_email"],
        client_uuid=row["client_uuid"],
        sub_id=row["sub_id"],
        remark=row["remark"],
        total_bytes=row["total_bytes"],
        enabled=bool(row["enabled"]),
    )
