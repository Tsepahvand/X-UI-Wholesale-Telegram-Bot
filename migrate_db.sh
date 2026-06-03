#!/usr/bin/env bash
# Apply SQLite schema + migrations (safe to run multiple times).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [[ ! -d "$ROOT_DIR/.venv" ]]; then
  echo "❌ .venv not found. Run ./install.sh first."
  exit 1
fi

"$ROOT_DIR/.venv/bin/python" - <<'PY'
import database as db

db.init_db()
print("✓ Database migrated: tables and settings are up to date")
PY
