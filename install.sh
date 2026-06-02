#!/bin/bash
# ===============================================================
#  X-UI Wholesale Telegram Bot — Installer
#  Usage: chmod +x install.sh && ./install.sh
# ===============================================================
set -e

cd "$(dirname "$0")"
ROOT="$(pwd)"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   X-UI Wholesale Bot — Installer         ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── Python ─────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  echo "❌ python3 not found. Please install Python 3.10+ first."
  exit 1
fi

PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✓ Python $PY_VER"

# ── venv ───────────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
  echo "📦 Creating virtualenv..."
  python3 -m venv .venv
else
  echo "✓ virtualenv already exists"
fi

source .venv/bin/activate

echo "📥 Installing dependencies..."
pip install -U pip -q
pip install -r requirements.txt -q

# SOCKS support for Telegram proxy
pip install 'httpx[socks]' -q 2>/dev/null || true

# ── .env ───────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "✅ .env created from .env.example"
  echo ""
  echo "⚠️  Before running, update these fields in .env:"
  echo "   • BOT_TOKEN        (from @BotFather)"
  echo "   • PANEL_URL / PANEL_USER / PANEL_PASS"
  echo "   • SUB_BASE_URL"
  echo ""
  echo "   If api.telegram.org is restricted:"
  echo "   • TELEGRAM_PROXY_ENABLED=true"
  echo "   • TELEGRAM_PROXY_HOST / PORT (+ USER/PASS if needed)"
else
  echo "✓ .env already exists"
fi

# ── executable scripts ─────────────────────────────────────────
chmod +x run.sh 2>/dev/null || true
chmod +x deploy/systemd/install-service.sh 2>/dev/null || true

echo ""
echo "════════════════════════════════════════════"
echo "✅ Installation completed successfully."
echo ""
echo "Next steps:"
echo "  1) Edit .env"
echo "  2) Run:"
echo "       ./run.sh"
echo ""
echo "Stable deployment (recommended on VPS):"
echo "  sudo ./deploy/systemd/install-service.sh"
echo ""
echo "Background run (optional):"
echo "  nohup ./run.sh > bot.log 2>&1 &"
echo "════════════════════════════════════════════"
echo ""
