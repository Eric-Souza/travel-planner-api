#!/usr/bin/env bash
# One-time local setup for travel-planner-api
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> travel-planner-api setup"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
else
  echo ".env already exists — skipping"
fi

mkdir -p data/uploads

echo "==> Installing Python dependencies..."
python -m pip install -e ".[dev]"

echo "==> Seeding demo data..."
python scripts/seed_demo.py

echo "==> Running tests..."
python -m pytest tests/ -q

echo ""
echo "Setup complete. Start the API with:"
echo "  python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
