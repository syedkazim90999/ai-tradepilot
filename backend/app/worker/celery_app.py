"""Celery configuration for deployment (requires Redis).
Local dev without Redis uses the in-app asyncio worker in main.py lifespan."""
import os

from celery import Celery

celery_app = Celery(
    "tradepilot",
    broker=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "scanner-every-5-min": {
            "task": "app.worker.tasks.run_scanner",
            "schedule": 300.0,
        },
        "reconcile-positions-every-15-min": {
            "task": "app.worker.tasks.reconcile_positions",
            "schedule": 900.0,
        },
    },
)
