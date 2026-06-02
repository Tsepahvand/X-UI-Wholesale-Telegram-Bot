#!/usr/bin/env bash
set -euo pipefail

REPO_OWNER="Tsepahvand"
REPO_NAME="X-UI-Wholesale-Telegram-Bot"
BRANCH="${1:-main}"
TARGET_DIR="${2:-$(pwd)}"
ARCHIVE_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}/archive/refs/heads/${BRANCH}.tar.gz"
WORK_DIR="$(mktemp -d)"
BACKUP_DIR="$TARGET_DIR/.remote-update-backup"

cleanup() {
  rm -rf "$WORK_DIR"
}
trap cleanup EXIT

echo "==> Remote update from ${REPO_OWNER}/${REPO_NAME}:${BRANCH}"
echo "==> Target directory: $TARGET_DIR"

if [[ ! -d "$TARGET_DIR" ]]; then
  echo "❌ Target directory not found: $TARGET_DIR"
  exit 1
fi

mkdir -p "$BACKUP_DIR"

if [[ -f "$TARGET_DIR/.env" ]]; then
  cp "$TARGET_DIR/.env" "$BACKUP_DIR/.env.bak"
  echo "✓ Backed up .env"
fi

if [[ -f "$TARGET_DIR/bot.db" ]]; then
  cp "$TARGET_DIR/bot.db" "$BACKUP_DIR/bot.db.bak"
  echo "✓ Backed up bot.db"
fi

echo "==> Downloading latest source archive"
curl -fsSL "$ARCHIVE_URL" -o "$WORK_DIR/repo.tar.gz"
tar -xzf "$WORK_DIR/repo.tar.gz" -C "$WORK_DIR"

SRC_DIR="$WORK_DIR/${REPO_NAME}-${BRANCH}"
if [[ ! -d "$SRC_DIR" ]]; then
  echo "❌ Extracted source directory not found."
  exit 1
fi

echo "==> Replacing project files (preserving .env, bot.db, .git)"
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete \
    --exclude ".git/" \
    --exclude ".env" \
    --exclude "bot.db" \
    "$SRC_DIR/" "$TARGET_DIR/"
else
  echo "⚠️ rsync not found; using cp fallback."
  cp -a "$SRC_DIR/." "$TARGET_DIR/"
fi

if [[ -f "$BACKUP_DIR/.env.bak" ]]; then
  cp "$BACKUP_DIR/.env.bak" "$TARGET_DIR/.env"
  echo "✓ Restored .env"
fi

if [[ -f "$BACKUP_DIR/bot.db.bak" ]]; then
  cp "$BACKUP_DIR/bot.db.bak" "$TARGET_DIR/bot.db"
  echo "✓ Restored bot.db"
fi

if [[ -f "$TARGET_DIR/.env.example" && -f "$TARGET_DIR/.env" ]]; then
  echo "==> Merging missing keys from .env.example into .env"
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    if [[ "$line" == *"="* ]]; then
      key="${line%%=*}"
      if ! grep -Eq "^[[:space:]]*${key}=" "$TARGET_DIR/.env"; then
        printf "\n%s\n" "$line" >> "$TARGET_DIR/.env"
        echo "  + added $key"
      fi
    fi
  done < "$TARGET_DIR/.env.example"
fi

echo "==> Installing/updating dependencies"
bash "$TARGET_DIR/install.sh"

echo ""
echo "✅ Remote update finished."
echo "Next:"
echo "  - If using systemd: sudo systemctl restart xui-wholesale-bot"
echo "  - If manual: ./run.sh"
echo ""
