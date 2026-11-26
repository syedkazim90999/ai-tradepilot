#!/bin/bash
# AI TradePilot on Replit (free Starter tier, no card).
# Starts the API + Celery worker + Celery beat in a single Repl.
set -e
cd "$(dirname "$0")/backend"
pip install -q -r requirements.txt
alembic upgrade head
celery -A app.worker.celery_app worker --loglevel=info &
celery -A app.worker.celery_app beat --loglevel=info &
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
