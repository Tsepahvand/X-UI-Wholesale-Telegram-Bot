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

Use this command to update code while keeping old `.env` and `bot.db`:

```bash
chmod +x update.sh
./update.sh
```

If you run with systemd:

```bash
sudo systemctl restart xui-wholesale-bot
```

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
| `./update.sh` | update to latest version and keep `.env` + `bot.db` |
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

### Dealer
- create config (size + name or `/random`) with QR/config/sub links
- renew config traffic
- check status (traffic, expiry, last online, enable/disable/delete)
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
├── panel_client.py
├── telegram_http.py
├── handlers/
├── deploy/systemd/
├── install.sh / update.sh / enable-systemd.sh / run.sh / setup.sh
├── .env.example
└── requirements.txt
```

---

## Recent Updates

### Added
- per-inbound config day-limit (`0 = unlimited`)
- Start After First Use support for day-limited clients
- inbound management UI in dealer search flow
- hard delete dealer from `bot.db`
- dynamic multi-admin reload from `.env`
- systemd deployment with auto-restart

### Fixed
- panel calls accidentally going through global proxy
- `getUpdates` proxy path instability
- dealer revoke/admin-id edge cases
- `lastOnline` parsing compatibility for dict format

---

## License

[MIT](LICENSE) — Copyright (c) 2026 Taha Sepahvand
