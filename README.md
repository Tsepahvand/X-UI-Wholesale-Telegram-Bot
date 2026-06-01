# X-UI Wholesale Telegram Bot

ربات تلگرامی برای مدیریت **عمده‌فروشان** پنل‌های **X-UI** — بدون دادن دسترسی مستقیم به پنل.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## پنل‌های پشتیبانی‌شده

| پنل | وضعیت | یادداشت |
|-----|--------|---------|
| [**3X-UI**](https://github.com/MHSanaei/3x-ui) | ✅ پشتیبانی کامل | نسخه‌های 2.x / 3.x با API استاندارد `panel/api/inbounds` |
| سایر فورک‌های X-UI | ⚠️ ممکن است کار کند | در صورت سازگاری API با 3X-UI |

---

## این پروژه برای چیست؟

| نقش | دسترسی |
|-----|--------|
| **ادمین** | فروشندگان، اینباندها، سهمیه GB، روز اعتبار، بلاک، حذف |
| **عمده‌فروش** | ساخت / تمدید / بررسی کانفیگ، حساب من |

ربات از **API پنل X-UI** استفاده می‌کند؛ سهمیه‌ها و فروشندگان در **SQLite** (`bot.db`) ذخیره می‌شوند.

---

## نصب سریع

```bash
git clone https://github.com/Tsepahvand/X-UI-Wholesale-Telegram-Bot.git
cd X-UI-Wholesale-Telegram-Bot

chmod +x install.sh run.sh
./install.sh
nano .env
./run.sh
```

---

## تنظیمات `.env`

نمونه: [`.env.example`](.env.example)

```env
BOT_TOKEN=...
ADMIN_ID=111111111              # یک ادمین
# ADMIN_ID=111,222,333          # چند ادمین با کاما
PANEL_URL=https://panel.example.com/secret-path
PANEL_USER=admin
PANEL_PASS=...
SUB_BASE_URL=https://panel.example.com/sub/
```

### پروکسی تلگرام (اختیاری)

```env
TELEGRAM_PROXY_ENABLED=true
TELEGRAM_PROXY_TYPE=socks5
TELEGRAM_PROXY_HOST=127.0.0.1
TELEGRAM_PROXY_PORT=1080
TELEGRAM_PROXY_REMOTE_DNS=true
```

> پروکسی **فقط برای تلگرام** است؛ اتصال **پنل** همیشه مستقیم است.  
> `getUpdates` و `sendMessage` هر دو از همان پروکسی استفاده می‌کنند.

---

## اجرا

| دستور | کاربرد |
|--------|--------|
| `./install.sh` | نصب (venv + وابستگی‌ها + `.env`) |
| `./run.sh` | اجرای ربات |
| `nohup ./run.sh > bot.log 2>&1 &` | اجرا در پس‌زمینه |

> فقط **یک** instance همزمان — دو بار اجرا → خطای `409 Conflict`.

---

## امکانات

### ادمین
- ➕ افزودن عمده‌فروش (اینباند + سقف GB + **روز اعتبار هر کانفیگ**)
- 🔍 جستجو: بلاک، خاموش کردن همه، ± سهمیه حجم
- 📡 **مدیریت اینباندها** (افزودن / ویرایش نام، سقف، روز / حذف)
- 🗑 **حذف کامل فروشنده** از دیتابیس ربات
- 📋 لیست فروشندگان
- چند ادمین با `ADMIN_ID` (با کاما)

### عمده‌فروش
- 🆕 ساخت کانفیگ (حجم، نام، `/random`) → QR + لینک + ساب
- ♻️ تمدید حجم
- 🔎 بررسی (حجم، انقضا، آخرین اتصال، خاموش/حذف)
- 👤 حساب من

### اعتبار زمانی کانفیگ
- هنگام دادن اینباند: تعداد **روز** (مثلاً `30`) یا `0` = نامحدود
- در پنل: **Start After First Use** (با `expiryTime` منفی)
- ویرایش روز فقط روی **کانفیگ‌های جدید** اثر دارد

### نام کانفیگ
- در لینک: `#InboundRemark-Name`
- در پنل: email با پیشوند `-`

---

## ساختار پروژه

```
├── main.py
├── config.py
├── database.py
├── panel_client.py
├── telegram_http.py
├── handlers/
├── install.sh / run.sh / setup.sh
├── .env.example
└── requirements.txt
```

---

## به‌روزرسانی‌ها

### نسخه اخیر

**امکانات جدید**
- روز اعتبار هر کانفیگ هنگام تخصیص اینباند (`0` = نامحدود)
- فعال‌سازی **Start After First Use** در پنل برای کانفیگ‌های محدود به روز
- منوی **مدیریت اینباندها** در جستجوی فروشنده (افزودن / ویرایش / حذف)
- حذف کامل فروشنده از `bot.db` (نه فقط غیرفعال‌سازی)
- چند ادمین در `ADMIN_ID`
- پروکسی SOCKS فقط برای تلگرام؛ پنل مستقیم

**رفع باگ‌ها**
- پروکسی سراسری باعث HTML به‌جای JSON پنل می‌شد → جدا شد
- `getUpdates` بدون پروکسی قطع می‌شد → `get_updates_proxy` اضافه شد
- قطع دسترسی فروشنده ولی رکورد در DB + ادمین `.env` کار نمی‌کرد → حذف واقعی + خواندن زنده `ADMIN_ID`
- `lastOnline` پنل به‌صورت dict — نمایش آخرین اتصال اصلاح شد

---

## English

Telegram bot for X-UI wholesale resellers. Admin manages dealers, inbounds, GB quota, and per-config day limits. Optional SOCKS5 for Telegram only; panel API stays direct.

```bash
git clone https://github.com/Tsepahvand/X-UI-Wholesale-Telegram-Bot.git
cd X-UI-Wholesale-Telegram-Bot && ./install.sh && nano .env && ./run.sh
```

---

## License

[MIT](LICENSE) — Copyright (c) 2026 Taha Sepahvand
