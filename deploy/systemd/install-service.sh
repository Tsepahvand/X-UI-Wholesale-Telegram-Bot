#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
SERVICE_NAME="xui-wholesale-bot"
UNIT_TEMPLATE="$ROOT_DIR/deploy/systemd/${SERVICE_NAME}.service"
UNIT_TARGET="/etc/systemd/system/${SERVICE_NAME}.service"
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
ENTRYPOINT="$ROOT_DIR/main.py"

if [[ $EUID -ne 0 ]]; then
  echo "❌ Please run with sudo:"
  echo "   sudo $0"
  exit 1
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "❌ Python venv not found: $PYTHON_BIN"
  echo "   Run first: ./install.sh"
  exit 1
fi

if [[ ! -f "$ROOT_DIR/.env" ]]; then
  echo "❌ .env file not found."
  echo "   cp .env.example .env && nano .env"
  exit 1
fi

if [[ ! -f "$UNIT_TEMPLATE" ]]; then
  echo "❌ Service template not found: $UNIT_TEMPLATE"
  exit 1
fi

tmp_unit="$(mktemp)"
trap 'rm -f "$tmp_unit"' EXIT

sed \
  -e "s|__WORKDIR__|$ROOT_DIR|g" \
  -e "s|__PYTHON__|$PYTHON_BIN|g" \
  -e "s|__ENTRYPOINT__|$ENTRYPOINT|g" \
  "$UNIT_TEMPLATE" > "$tmp_unit"

install -m 0644 "$tmp_unit" "$UNIT_TARGET"

systemctl daemon-reload
systemctl enable --now "$SERVICE_NAME"

echo ""
echo "✅ systemd service enabled: $SERVICE_NAME"
echo ""
echo "Status:"
echo "  systemctl status $SERVICE_NAME --no-pager"
echo ""
echo "Live logs:"
echo "  journalctl -u $SERVICE_NAME -f"
echo ""
echo "Restart:"
echo "  systemctl restart $SERVICE_NAME"
echo ""
