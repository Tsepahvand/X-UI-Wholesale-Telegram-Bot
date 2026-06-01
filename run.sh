#!/bin/bash
# اجرای ربات — Usage: ./run.sh
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "❌ ابتدا نصب کنید:  ./install.sh"
  exit 1
fi

if [ ! -f ".env" ]; then
  echo "❌ فایل .env وجود ندارد."
  echo "   cp .env.example .env  &&  nano .env"
  exit 1
fi

source .venv/bin/activate
exec python main.py
