# X-UI Wholesale Telegram Bot

یک Telegram bot برای مدیریت wholesale dealer روی پنل‌های X-UI، بدون دادن direct panel access.

For Persian explain click here: [README فارسی](README.fa.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## Supported Panels

| Panel | Status | Note |
|-----|--------|---------|
| [**3X-UI**](https://github.com/MHSanaei/3x-ui) | ✅ Full support | Compatible with standard `panel/api/inbounds` API |
| Other X-UI forks | ⚠️ Maybe works | If API behavior matches 3X-UI |

---

## Project Use Case

| Role | Access Scope |
|-----|--------|
| **Admin** | dealer management, inbound assignment, GB quota, day-limit, block/delete |
| **Dealer** | create / renew / check config, account status |

Data is stored in local SQLite (`bot.db`) and panel operations run through X-UI API.

---

## Quick Start

```bash
git clone https://github.com/Tsepahvand/X-UI-Wholesale-Telegram-Bot.git
cd X-UI-Wholesale-Telegram-Bot
chmod +x install.sh run.sh
./install.sh
nano .env
./run.sh
```

---

## Update to Latest Version

Updates keep your existing **`.env`** and **`bot.db`** (dealers, configs, quotas).

`update.sh` / `remote-update.sh` automatically run **`migrate_db.sh`** so SQLite gets new tables/columns (for example `bot_settings`) without manual SQL.

```bash
chmod +x update.sh migrate_db.sh
./update.sh
```

Manual migration only (optional):

```bash
./migrate_db.sh
```

For servers where git update is not preferred, use remote update with curl (no directory removal):

```bash
cd /path/to/X-UI-Wholesale-Telegram-Bot
curl -fsSL https://raw.githubusercontent.com/Tsepahvand/X-UI-Wholesale-Telegram-Bot/main/remote-update.sh | bash -s -- main "$(pwd)"
```

Then restart:

```bash
sudo systemctl restart xui-wholesale-bot
# or: ./run.sh
```

Dealers should send **`/start`** once after update so the reply keyboard matches new menu settings.

---

## Migrate Manual Run to systemd (One Command)

If you were running with `./run.sh` or `nohup`, use this command once:

```bash
chmod +x enable-systemd.sh
./enable-systemd.sh
```

This script:
- stops manual bot processes
- installs/enables systemd service
- starts bot under `xui-wholesale-bot`

---

## `.env` Configuration

Template: [`.env.example`](.env.example)

```env
BOT_TOKEN=...
ADMIN_ID=111111111              # single admin
# ADMIN_ID=111,222,333          # multiple admins
PANEL_URL=https://panel.example.com/secret-path
PANEL_USER=admin
PANEL_PASS=...
SUB_BASE_URL=https://panel.example.com/sub/
```

### Telegram Proxy (Optional)

```env
TELEGRAM_PROXY_ENABLED=true
TELEGRAM_PROXY_TYPE=socks5
TELEGRAM_PROXY_HOST=127.0.0.1
TELEGRAM_PROXY_PORT=1080
TELEGRAM_PROXY_REMOTE_DNS=true
```

Proxy is used only for Telegram API traffic; panel API always stays direct.

---

## Run Modes

| Command | Purpose |
|--------|--------|
| `./install.sh` | setup venv + deps + `.env` |
| `./update.sh` | pull latest code, keep `.env` + `bot.db`, run DB migration |
| `./remote-update.sh` | update from GitHub tarball, keep data, run DB migration |
| `./migrate_db.sh` | apply SQLite schema/migrations only (idempotent) |
| `./enable-systemd.sh` | migrate manual run to systemd mode |
| `./run.sh` | foreground run |
| `nohup ./run.sh > bot.log 2>&1 &` | background run |

Use only one instance at a time; multiple polling instances cause `409 Conflict`.

### Stable VPS Mode (Recommended)

Use systemd for auto-restart when process exits or gets killed:

```bash
chmod +x deploy/systemd/install-service.sh
sudo ./deploy/systemd/install-service.sh
sudo systemctl status xui-wholesale-bot
```

Live logs:

```bash
journalctl -u xui-wholesale-bot -f
```

Restart:

```bash
sudo systemctl restart xui-wholesale-bot
```

Check OOM/system kill:

```bash
dmesg -T | rg -i "killed process|out of memory|oom"
```

---

## Features

### Admin
- add dealer with inbound + GB quota + config day-limit
- dealer search & actions: block, disable all, quota +/- 
- inbound management: add/edit/remove assigned inbounds
- hard delete dealer from bot database
- multi-admin support via `ADMIN_ID`
- **⚙️ Bot Settings** (categorized panel):
  - **Menu buttons** — enable/disable: create, renew, check, account (hidden from dealer menu when off)
  - **Config actions** — enable/disable: on/off toggle and delete after check
  - **Create config** — client name mode (ask / auto-random / ask + `/random`), sub ID mode (same as name / random / name + random sub), random sub length 8–12+

### Dealer
- dynamic menu (only enabled sections from admin settings)
- create config — naming/sub rules follow admin settings
- renew config traffic
- check status (traffic, expiry, last online; optional toggle/delete per settings)
- account summary

### Expiry Logic
- assign `days` per inbound (`0` means unlimited)
- in panel, day-limited clients are created as **Start After First Use**
- changing day-limit affects only new clients

---

## Project Structure

```
├── main.py
├── config.py
├── database.py
├── bot_settings.py
├── panel_client.py
├── telegram_http.py
├── handlers/
│   ├── admin_settings.py
│   └── ...
├── deploy/systemd/
├── install.sh / update.sh / remote-update.sh / migrate_db.sh / enable-systemd.sh / run.sh
├── .env.example
└── requirements.txt
```

---

## Recent Updates

### v1.2 — Bot Settings & DB migration

**Added**
- Admin **⚙️ Bot Settings** with 3 categories: menu buttons, config actions, create/naming
- Toggle dealer menu items (create / renew / check / account)
- Toggle post-check actions (enable-disable / delete config)
- Client name modes: ask user, auto-random, ask + `/random`
- Sub ID modes: same as name, random (8–12+ chars), dealer name + random sub
- SQLite table `bot_settings` (defaults inserted on first run / migration)
- `migrate_db.sh` — safe idempotent migration; runs automatically in `update.sh` and `remote-update.sh`

**Database on update**
- Existing `bot.db` is kept; `init_db()` creates missing tables and adds missing columns
- New settings keys use `INSERT OR IGNORE` (won’t overwrite admin changes)

### Earlier releases

- per-inbound config day-limit (`0 = unlimited`)
- Start After First Use for day-limited clients
- inbound management in dealer profile
- hard delete dealer, multi-admin, systemd + `update.sh` / `remote-update.sh`
- Telegram-only proxy; panel stays direct

---

## License

[MIT](LICENSE) — Copyright (c) 2026 Taha Sepahvand
