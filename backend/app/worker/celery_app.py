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


def _force_resp2_for_redis_broker() -> None:
    """Force RESP2 (protocol=2) on the Redis broker connection.

    redis-py 6.x can negotiate RESP3 (HELLO 3 + AUTH) and Upstash's TCP
    endpoint rejects that handshake as "invalid username-password pair"
    even with correct credentials (the password was proven not to be the
    cause: five credential forms, including a brand-new ACL user, all
    failed identically).

    The protocol cannot be set via the REDIS_URL query string:
    ``?protocol=2`` is rejected by kombu's ``Connection._init_params``
    (fixed signature, no ``protocol`` parameter). Kombu's redis Channel
    also does not read ``protocol`` from ``broker_transport_options`` on
    its own, so we inject it into the connection-pool kwargs that kombu
    builds in ``Channel._connparams``. The value is read from the
    connection's ``broker_transport_options`` (set to 2 below),
    defaulting to 2. The pool then creates every connection with
    ``protocol=2``, so AUTH is sent as a plain ``AUTH`` command (RESP2)
    instead of ``HELLO 3 AUTH`` (RESP3).

    This applies to the worker, beat, and the result backend, which all
    share the same broker URL / Channel class. It does not change
    REDIS_URL, the broker host, or any credential. The patch is
    idempotent (safe if this module is reloaded).
    """
    try:
        from kombu.transport.redis import Channel as RedisChannel
    except Exception:
        return
    if getattr(RedisChannel._connparams, "_resp2_patched", False):
        return
    _orig_connparams = RedisChannel._connparams

    def _connparams_resp2(self, asynchronous=False):
        params = _orig_connparams(self, asynchronous=asynchronous)
        try:
            protocol = self.connection.client.transport_options.get("protocol", 2)
        except Exception:
            protocol = 2
        params["protocol"] = int(protocol)
        return params

    _connparams_resp2._resp2_patched = True
    RedisChannel._connparams = _connparams_resp2


_force_resp2_for_redis_broker()

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
    # Force RESP2 for the Redis broker (see _force_resp2_for_redis_broker).
    # redis-py 6.x otherwise negotiates RESP3 and Upstash rejects the
    # HELLO 3 + AUTH handshake. Declared here so the resolved config
    # carries protocol=2; the _connparams patch above is what actually
    # injects it into the redis connection-pool kwargs.
    broker_transport_options={"protocol": 2},
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
