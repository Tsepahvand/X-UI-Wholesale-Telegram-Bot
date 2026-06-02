# ربات عمده‌فروشی X-UI

این پروژه یک **Telegram Bot** برای مدیریت عمده‌فروش‌ها (Dealer) روی پنل‌های **X-UI** است؛ بدون اینکه دسترسی مستقیم به پنل بدهید.

---

## پنل‌های پشتیبانی‌شده

- **3X-UI** (پشتیبانی کامل)
- سایر forkهای X-UI در صورت سازگاری API

---

## کاربرد پروژه

### نقش ادمین
- افزودن Dealer
- تخصیص Inbound
- تعیین سهمیه حجم (GB)
- تعیین تعداد روز اعتبار هر کانفیگ
- بلاک/آنبلاک، مدیریت Inboundها، حذف کامل فروشنده

### نقش عمده‌فروش
- ساخت کانفیگ
- تمدید حجم
- بررسی وضعیت کانفیگ
- مشاهده حساب کاربری

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

## آپدیت به آخرین نسخه (بدون از دست دادن دیتا)

برای آپدیت پروژه و نگه‌داشتن `.env` و `bot.db`:

```bash
chmod +x update.sh
./update.sh
```

اگر نخواستید با git آپدیت کنید، با `curl` هم می‌توانید بدون حذف دایرکتوری پروژه آپدیت کنید:

```bash
cd /path/to/X-UI-Wholesale-Telegram-Bot
curl -fsSL https://raw.githubusercontent.com/Tsepahvand/X-UI-Wholesale-Telegram-Bot/main/remote-update.sh | bash -s -- main "$(pwd)"
```

این روش فایل‌های جدید را جایگزین می‌کند و `.env` و `bot.db` را نگه می‌دارد.

اگر با systemd اجرا می‌کنید:

```bash
sudo systemctl restart xui-wholesale-bot
```

---

## مهاجرت از اجرای دستی به systemd (با یک دستور)

اگر قبلاً با `./run.sh` یا `nohup` اجرا می‌کردید، یک بار این دستور را بزنید:

```bash
chmod +x enable-systemd.sh
./enable-systemd.sh
```

این اسکریپت:
- اجرای دستی را متوقف می‌کند
- سرویس systemd را نصب/فعال می‌کند
- ربات را با سرویس `xui-wholesale-bot` بالا می‌آورد

---

## تنظیمات اصلی `.env`

```env
BOT_TOKEN=...
ADMIN_ID=111111111
# ADMIN_ID=111,222,333
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

نکته:
- پروکسی فقط برای Telegram استفاده می‌شود.
- ارتباط با پنل مستقیم باقی می‌ماند.

---

## اجرای پایدار روی VPS (پیشنهادی)

برای جلوگیری از down شدن سرویس، از **systemd** استفاده کنید:

```bash
chmod +x deploy/systemd/install-service.sh
sudo ./deploy/systemd/install-service.sh
sudo systemctl status xui-wholesale-bot
```

لاگ زنده:

```bash
journalctl -u xui-wholesale-bot -f
```

ری‌استارت:

```bash
sudo systemctl restart xui-wholesale-bot
```

بررسی OOM / kill:

```bash
dmesg -T | rg -i "killed process|out of memory|oom"
```

---

## ویژگی‌های مهم

- پشتیبانی چند ادمین با `ADMIN_ID` (comma-separated)
- اعتبار روزانه هر کانفیگ (`0` = نامحدود)
- **Start After First Use** برای کانفیگ‌های محدود به روز
- مدیریت کامل Inboundهای هر Dealer
- حذف کامل فروشنده از دیتابیس ربات

---

## لایسنس

[MIT](LICENSE)
