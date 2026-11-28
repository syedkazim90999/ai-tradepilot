"""Celery configuration for deployment (requires Redis).
Local dev without Redis uses the in-app asyncio worker in main.py lifespan."""
import logging
import os
from urllib.parse import quote, urlsplit, urlunsplit

from celery import Celery

logger = logging.getLogger(__name__)


def _celery_redis_url() -> str:
    """Build the Celery broker/result-backend URL.

    Credentials must survive URL parsing intact. Upstash auto-generated
    ACL passwords can contain characters that are special in a URL
    (@ : / # ? & = + %). If such a password is pasted raw into
    REDIS_URL, the URL parser splits the password at the special
    character and kombu sends a mangled password to AUTH, so Upstash
    rejects it as "invalid username-password pair" even though the
    password itself is correct. (Verified: redis-py 6.4.0 already
    defaults to RESP2/protocol=2, so the AUTH failure is not a RESP3
    handshake problem, and the default-user REST token in
    .env.production is all-alphanumeric, so the failure is not the
    password value itself -- it is how the password travels through
    the URL.)

    To avoid that, the password may be supplied separately via the
    REDIS_PASSWORD env var (raw, no URL-encoding needed) and the
    username via REDIS_USERNAME. When set, they override whatever
    credentials are embedded in REDIS_URL, and the password is
    percent-encoded here before being placed in the URL, so kombu
    parses back exactly the intended username/password. The URL
    itself is only used for scheme/host/port/path/query in that case.
    Without REDIS_PASSWORD/REDIS_USERNAME the URL is used as-is
    (previous behaviour).
    """
    url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    username = os.environ.get("REDIS_USERNAME")
    password = os.environ.get("REDIS_PASSWORD")
    if username is not None or password is not None:
        parts = urlsplit(url)
        if username is None:
            username = parts.username or "default"
        if password is None:
            password = parts.password or ""
        host = parts.hostname or "localhost"
        netloc = host
        if parts.port:
            netloc += f":{parts.port}"
        auth = quote(username, safe="") + ":" + quote(password, safe="")
        url = urlunsplit(
            (parts.scheme, f"{auth}@{netloc}", parts.path, parts.query, "")
        )
        logger.info(
            "Celery broker credentials supplied via REDIS_USERNAME/REDIS_PASSWORD "
            "env vars (username=%s, host=%s); password percent-encoded into URL.",
            username,
            host,
        )
    # Kombu requires ssl_cert_reqs to be set explicitly for rediss:// URLs
    # (Upstash Redis uses TLS). Without it the worker dies with:
    # "a rediss:// URL must have parameter ssl_cert_reqs set to CERT_REQUIRED".
    if url.startswith("rediss://") and "ssl_cert_reqs" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}ssl_cert_reqs=CERT_REQUIRED"
    return url


def _force_resp2_for_redis_broker() -> None:
    """Force RESP2 (protocol=2) on the Redis broker connection.

    NOTE (2026-11-28 investigation): redis-py 6.4.0 already defaults
    to protocol=2 (RESP2) in both Connection.__init__ and Redis.__init__,
    so this patch is belt-and-braces -- it does NOT by itself explain or
    fix an "invalid username-password pair" AUTH failure, because the
    worker was already speaking RESP2 before this patch. The AUTH
    failure with correct credentials is a credential-transport problem
    (see _celery_redis_url: a password containing URL-special characters
    is mangled by URL parsing), not a RESP3 handshake problem. This
    patch is kept so the resolved pool kwargs provably carry protocol=2.

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
    # Register the worker tasks. Without this the worker starts with an
    # EMPTY [tasks] list: beat dispatches "app.worker.tasks.run_scanner"
    # every 5 min and the worker discards it as an unregistered task
    # ("Received unregistered task of type ..."). The beat schedule alone
    # does not register tasks -- the module must be imported. Celery
    # imports `include` lazily (on finalize / worker start), so there is
    # no circular import with app.worker.tasks, which imports celery_app.
    include=["app.worker.tasks"],
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
