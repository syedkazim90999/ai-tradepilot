#!/usr/bin/env bash
# AI TradePilot — local dev startup (SQLite fallback, no Docker/Postgres needed).
# Starts the FastAPI backend (venv + uvicorn) and the Next.js dev server.
# Usage: ./scripts/dev.sh   (Ctrl+C stops both)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

[ -d backend/venv ] || { echo "backend/venv missing — create it first:"; echo "  python3 -m venv backend/venv && backend/venv/bin/pip install -r backend/requirements.txt"; exit 1; }
[ -f backend/.env ] || echo "NOTE: backend/.env not found — defaults apply (SQLite dev DB, dev SECRET_KEY). Copy backend/.env.example to backend/.env for real values."
[ -d frontend/node_modules ] || { echo "Installing frontend dependencies..."; (cd frontend && npm install); }

# Apply migrations (SQLite dev DB by default).
(cd backend && ./venv/bin/alembic upgrade head)

echo "Starting backend on http://localhost:8000 ..."
(cd backend && ./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload) &
BACKEND_PID=$!
echo "Starting frontend on http://localhost:3000 ..."
(cd frontend && npm run dev) &
FRONTEND_PID=$!
trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true' INT TERM EXIT
wait
