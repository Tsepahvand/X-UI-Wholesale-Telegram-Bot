#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  3X-UI Wholesale Telegram Bot — نصب
#  Usage:  chmod +x install.sh && ./install.sh
# ═══════════════════════════════════════════════════════════════
set -e

cd "$(dirname "$0")"
ROOT="$(pwd)"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   3X-UI Wholesale Bot — Installer        ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── Python ─────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  echo "❌ python3 یافت نشد. ابتدا Python 3.10+ نصب کنید."
  exit 1
fi

PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✓ Python $PY_VER"

# ── venv ───────────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
  echo "📦 ساخت virtualenv..."
  python3 -m venv .venv
else
  echo "✓ virtualenv موجود است"
fi

source .venv/bin/activate

echo "📥 نصب وابستگی‌ها..."
pip install -U pip -q
pip install -r requirements.txt -q

# SOCKS support for Telegram proxy
pip install 'httpx[socks]' -q 2>/dev/null || true

# ── .env ───────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "✅ فایل .env ساخته شد از .env.example"
  echo ""
  echo "⚠️  قبل از اجرا این موارد را در .env پر کنید:"
  echo "   • BOT_TOKEN        (از @BotFather)"
  echo "   • PANEL_URL / PANEL_USER / PANEL_PASS"
  echo "   • SUB_BASE_URL"
  echo ""
  echo "   اگر سرور فیلتر است:"
  echo "   • TELEGRAM_PROXY_ENABLED=true"
  echo "   • TELEGRAM_PROXY_HOST / PORT (+ USER/PASS در صورت نیاز)"
else
  echo "✓ فایل .env از قبل وجود دارد"
fi

# ── executable scripts ─────────────────────────────────────────
chmod +x run.sh 2>/dev/null || true

echo ""
echo "════════════════════════════════════════════"
echo "✅ نصب با موفقیت انجام شد."
echo ""
echo "مرحله بعد:"
echo "  1) ویرایش .env"
echo "  2) اجرا:"
echo "       ./run.sh"
echo ""
echo "اجرای پس‌زمینه (اختیاری):"
echo "  nohup ./run.sh > bot.log 2>&1 &"
echo "════════════════════════════════════════════"
echo ""
