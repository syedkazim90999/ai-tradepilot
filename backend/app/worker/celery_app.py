"""Celery configuration for deployment (requires Redis).
Local dev without Redis uses the in-app asyncio worker in main.py lifespan."""
import os

from celery import Celery


def _celery_redis_url() -> str:
    url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    # Kombu requires ssl_cert_reqs to be set explicitly for rediss:// URLs
    # (Upstash Redis uses TLS). Without it the worker dies with:
    # "a rediss:// URL must have parameter ssl_cert_reqs set to CERT_REQUIRED".
    if url.startswith("rediss://") and "ssl_cert_reqs" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}ssl_cert_reqs=CERT_REQUIRED"
    return url


celery_app = Celery(
    "tradepilot",
    broker=_celery_redis_url(),
    backend=_celery_redis_url(),
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
