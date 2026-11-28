#!/bin/bash
# AI TradePilot on Railway (free trial, no card).
# Runs migrations, then API + Celery worker + Celery beat in a single container.
set -e
alembic upgrade head
celery -A app.worker.celery_app worker --loglevel=info &
celery -A app.worker.celery_app beat --loglevel=info --schedule=/tmp/celerybeat-schedule &
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
