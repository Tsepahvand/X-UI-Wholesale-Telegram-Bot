#!/bin/bash
# Run bot — Usage: ./run.sh
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "❌ Please run installer first: ./install.sh"
  exit 1
fi

if [ ! -f ".env" ]; then
  echo "❌ .env file not found."
  echo "   cp .env.example .env  &&  nano .env"
  exit 1
fi

source .venv/bin/activate
exec python main.py
