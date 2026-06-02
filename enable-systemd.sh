#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_NAME="xui-wholesale-bot"

echo "==> Migrating manual run to systemd mode"

if [[ ! -x "$ROOT_DIR/deploy/systemd/install-service.sh" ]]; then
  echo "❌ Missing installer: deploy/systemd/install-service.sh"
  exit 1
fi

echo "==> Stopping possible manual runners (run.sh/main.py/nohup)"
pkill -f "$ROOT_DIR/run.sh" 2>/dev/null || true
pkill -f "$ROOT_DIR/main.py" 2>/dev/null || true

if pgrep -f "$ROOT_DIR/main.py" >/dev/null 2>&1; then
  echo "⚠️ Some manual processes are still running. Stop them manually and retry:"
  echo "   pkill -f '$ROOT_DIR/main.py'"
  exit 1
fi

echo "==> Installing and enabling systemd service"
sudo "$ROOT_DIR/deploy/systemd/install-service.sh"

echo ""
echo "✅ Migration completed."
echo "Service: $SERVICE_NAME"
echo ""
echo "Status:"
echo "  sudo systemctl status $SERVICE_NAME --no-pager"
echo ""
echo "Logs:"
echo "  journalctl -u $SERVICE_NAME -f"
echo ""
