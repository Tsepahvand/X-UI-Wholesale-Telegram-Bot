# X-UI Wholesale Telegram Bot

ربات تلگرامی برای مدیریت **عمده‌فروشان** پنل‌های **X-UI** — بدون دادن دسترسی مستقیم به پنل.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## پنل‌های پشتیبانی‌شده

| پنل | وضعیت | یادداشت |
|-----|--------|---------|
| [**3X-UI**](https://github.com/MHSanaei/3x-ui) | ✅ پشتیبانی کامل | نسخه‌های 2.x / 3.x با API استاندارد `panel/api/inbounds` |
| سایر فورک‌های X-UI | ⚠️ ممکن است کار کند | در صورت سازگاری API با 3X-UI |

> در حال حاضر توسعه و تست روی **3X-UI** انجام شده است. اگر پنل شما API مشابه دارد، احتمالاً بدون تغییر کار می‌کند.

---

## این پروژه برای چیست؟

اگر چند **عمده‌فروش / نماینده** دارید که باید کانفیگ بسازند، تمدید کنند و مصرف را ببینند، ولی **نمی‌خواهید** به آن‌ها یوزر/پسورد پنل بدهید — این ربات لایهٔ میانی است:

| نقش | دسترسی |
|-----|--------|
| **ادمین** | افزودن فروشنده، تعیین اینباند و سهمیه GB، بلاک، قطع دسترسی |
| **عمده‌فروش** | ساخت کانفیگ، تمدید، بررسی، حساب من |

ربات از **API پنل X-UI** استفاده می‌کند و دادهٔ فروشندگان/سهمیه‌ها را در **SQLite** (`bot.db`) نگه می‌دارد.

---

## نصب سریع

```bash
git clone https://github.com/Tsepahvand/X-UI-Wholesale-Telegram-Bot.git
cd X-UI-Wholesale-Telegram-Bot

chmod +x install.sh run.sh
./install.sh
```

سپس `.env` را ویرایش کنید و ربات را اجرا کنید:

```bash
nano .env
./run.sh
```

---

## تنظیمات `.env`

فایل نمونه: [`.env.example`](.env.example)

### الزامی

```env
BOT_TOKEN=123456:ABC...          # از @BotFather
ADMIN_ID=7156306196              # یک ادمین
# ADMIN_ID=111,222,333           # چند ادمین با کاما
PANEL_URL=https://panel.example.com/XhzfnPpVrHRzzzh
PANEL_USER=admin
PANEL_PASS=admin
SUB_BASE_URL=https://panel.example.com/sub/
```

### پروکسی تلگرام (اختیاری)

روی سرورهایی که `api.telegram.org` فیلتر است، یکی از حالت‌های زیر را در `.env` فعال کنید.

#### حالت ۱ — SOCKS5 بدون یوزر/پس (مثلاً Clash/v2ray محلی)

```env
TELEGRAM_PROXY_ENABLED=true
TELEGRAM_PROXY_TYPE=socks5
TELEGRAM_PROXY_HOST=127.0.0.1
TELEGRAM_PROXY_PORT=1080
```

#### حالت ۲ — SOCKS5 با یوزر/پس (پروکسی ریموت)

```env
TELEGRAM_PROXY_ENABLED=true
TELEGRAM_PROXY_TYPE=socks5
TELEGRAM_PROXY_HOST=proxy.example.com
TELEGRAM_PROXY_PORT=1080
TELEGRAM_PROXY_USER=myuser
TELEGRAM_PROXY_PASS=mypassword
TELEGRAM_PROXY_REMOTE_DNS=true
```

#### حالت ۳ — URL کامل

```env
TELEGRAM_PROXY=socks5h://user:pass@proxy.example.com:1080
```

> برای SOCKS5، `install.sh` به‌صورت خودکار `httpx[socks]` نصب می‌کند.

> **مهم:** پروکسی **فقط** برای تلگرام است. اتصال به **پنل X-UI** همیشه مستقیم است (بدون پروکسی).

---

## اجرا

| دستور | کاربرد |
|--------|--------|
| `./install.sh` | نصب یک‌بار (venv + pip + ساخت `.env`) |
| `./run.sh` | اجرای ربات |
| `nohup ./run.sh > bot.log 2>&1 &` | اجرا در پس‌زمینه |

> فقط **یک** نمونه از ربات را همزمان اجرا کنید؛ دو instance باعث خطای `409 Conflict` در `getUpdates` می‌شود.

---

## امکانات

### ادمین
- ➕ افزودن عمده‌فروش (آیدی تلگرام + اینباندها + سقف GB)
- 🔍 جستجو و مدیریت (بلاک، خاموش کردن همه، افزایش/کاهش سهمیه، قطع دسترسی)
- 📋 لیست فروشندگان

### عمده‌فروش
- 🆕 **ساخت** — حجم → نام (`/random` برای تصادفی) → QR + لینک کانفیگ و ساب
- ♻️ **تمدید** — ارسال لینک → افزودن حجم
- 🔎 **بررسی** — حجم، آخرین اتصال، خاموش/حذف
- 👤 **حساب من** — وضعیت سهمیه هر اینباند

### نام کانفیگ
- نام نمایشی در لینک: `#TamTunnel-Ali`
- در پنل با پیشوند `-` ثبت می‌شود: `-Ali`
- تکراری بودن فقط بین کانفیگ‌های همان فروشنده در ربات چک می‌شود

---

## ساختار پروژه

```
X-UI-Wholesale-Telegram-Bot/
├── main.py              # نقطه ورود
├── config.py            # خواندن .env + ساخت URL پروکسی
├── database.py          # SQLite
├── panel_client.py      # کلاینت API پنل
├── telegram_http.py     # پروکسی فقط برای تلگرام
├── handlers/            # هندلرهای تلگرام
├── install.sh / run.sh
├── .env.example
└── requirements.txt
```

---

## فایل‌های Git

| commit می‌شود | commit **نمی‌شود** (`.gitignore`) |
|---------------|-----------------------------------|
| کد منبع، `README.md`, `.env.example`, `install.sh`, `run.sh` | `.env`, `bot.db`, `.venv/` |

---

## English

**X-UI Wholesale Telegram Bot** — manage resellers without giving them panel access.

- **Supported panel:** [3X-UI](https://github.com/MHSanaei/3x-ui) (other X-UI forks may work if API-compatible)
- Admin: dealers, inbounds, GB quotas
- Dealers: create / renew / check configs via Telegram
- Telegram SOCKS5 proxy optional; panel API always connects directly

```bash
git clone https://github.com/Tsepahvand/X-UI-Wholesale-Telegram-Bot.git
cd X-UI-Wholesale-Telegram-Bot
./install.sh && nano .env && ./run.sh
```

---

## License

[MIT](LICENSE) — Copyright (c) 2026 Taha Sepahvand
