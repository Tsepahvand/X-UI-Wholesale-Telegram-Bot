#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="$ROOT_DIR/.update-backup"

echo "==> X-UI Wholesale Bot update started"

if [[ ! -d "$ROOT_DIR/.git" ]]; then
  echo "❌ This directory is not a git repository."
  exit 1
fi

mkdir -p "$BACKUP_DIR"

if [[ -f "$ROOT_DIR/.env" ]]; then
  cp "$ROOT_DIR/.env" "$BACKUP_DIR/.env.bak"
  echo "✓ Backed up .env"
fi

if [[ -f "$ROOT_DIR/bot.db" ]]; then
  cp "$ROOT_DIR/bot.db" "$BACKUP_DIR/bot.db.bak"
  echo "✓ Backed up bot.db"
fi

echo "==> Pulling latest changes from origin/main"
git -C "$ROOT_DIR" fetch origin
git -C "$ROOT_DIR" pull --ff-only origin main

if [[ -f "$BACKUP_DIR/.env.bak" ]]; then
  cp "$BACKUP_DIR/.env.bak" "$ROOT_DIR/.env"
  echo "✓ Restored .env"
fi

if [[ -f "$BACKUP_DIR/bot.db.bak" ]]; then
  cp "$BACKUP_DIR/bot.db.bak" "$ROOT_DIR/bot.db"
  echo "✓ Restored bot.db"
fi

if [[ -f "$ROOT_DIR/.env.example" && -f "$ROOT_DIR/.env" ]]; then
  echo "==> Merging missing keys from .env.example into .env"
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    if [[ "$line" == *"="* ]]; then
      key="${line%%=*}"
      if ! grep -Eq "^[[:space:]]*${key}=" "$ROOT_DIR/.env"; then
        printf "\n%s\n" "$line" >> "$ROOT_DIR/.env"
        echo "  + added $key"
      fi
    fi
  done < "$ROOT_DIR/.env.example"
fi

echo "==> Reinstalling dependencies"
bash "$ROOT_DIR/install.sh"

echo ""
echo "✅ Update finished."
echo "Next:"
echo "  - If using systemd: sudo systemctl restart xui-wholesale-bot"
echo "  - If running manually: ./run.sh"
