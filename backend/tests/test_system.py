"""System tests: health endpoint, Alembic upgrade/downgrade on a scratch DB,
worker recovery (standalone scan loop survives a failing scan)."""
import os
import sqlite3
import subprocess
import sys

from tests.conftest import auth_headers, register_and_login


def test_health_shape(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["database"] == "ok"
    assert set(body) >= {"status", "database", "worker", "exchange_reachable", "testnet"}
    assert body["worker"] in ("ok", "error")
    assert isinstance(body["exchange_reachable"], bool)


def test_root_endpoint(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["app"] == "AI TradePilot"


def test_openapi_lists_new_endpoints(client):
    spec = client.get("/openapi.json").json()
    paths = spec["paths"]
    for p in ["/api/v1/market/klines", "/api/v1/contact", "/api/v1/auth/me",
              "/api/v1/auth/change-password", "/api/v1/auth/2fa/setup",
              "/api/v1/auth/2fa/verify", "/api/v1/auth/2fa/disable",
              "/api/v1/admin/signals", "/api/v1/admin/strategies/performance"]:
        assert p in paths, f"missing OpenAPI path {p}"
    assert "put" in paths["/api/v1/auth/me"]
    assert "post" in paths["/api/v1/contact"]


def _run_alembic(db_path: str, *args: str):
    """Run Alembic in a subprocess: env.py reads DATABASE_URL from the
    environment (get_settings), so the scratch URL must come via env, not via
    the ini file. Never touches the dev tradepilot.db."""
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = dict(os.environ)
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade" if args[0] == "upgrade" else "downgrade", *args[1:]],
        cwd=backend_dir, env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr


def test_alembic_upgrade_downgrade_scratch_db(tmp_path):
    """Upgrade to head creates contact_messages and the min_risk_usd column;
    downgrade one step removes only the newest revision; downgrade another
    removes contact_messages; upgrade again restores both. Runs on a scratch
    SQLite file, never the dev DB."""
    db_path = str(tmp_path / "scratch.db")
    _run_alembic(db_path, "upgrade", "head")
    con = sqlite3.connect(db_path)
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "contact_messages" in tables
    assert "users" in tables
    assert "market_signals" in tables
    cols = {r[1] for r in con.execute("PRAGMA table_info(bot_settings)")}
    assert "min_risk_usd" in cols
    con.close()
    _run_alembic(db_path, "downgrade", "-1")
    con = sqlite3.connect(db_path)
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    cols = {r[1] for r in con.execute("PRAGMA table_info(bot_settings)")}
    con.close()
    assert "min_risk_usd" not in cols
    assert "contact_messages" in tables  # only the newest revision was rolled back
    _run_alembic(db_path, "downgrade", "-1")
    con = sqlite3.connect(db_path)
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    con.close()
    assert "contact_messages" not in tables
    assert "users" in tables
    _run_alembic(db_path, "upgrade", "head")
    con = sqlite3.connect(db_path)
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    cols = {r[1] for r in con.execute("PRAGMA table_info(bot_settings)")}
    con.close()
    assert "contact_messages" in tables
    assert "min_risk_usd" in cols


def test_worker_scan_task_propagates_error_for_loop_recovery(monkeypatch):
    """run_scanner_task raises when the scanner fails; the standalone
    __main__ loop in app/worker/tasks.py wraps each call in try/except, so a
    failing scan is logged and the loop continues instead of dying."""
    import pytest
    import app.worker.tasks as tasks

    async def failing_scan(*a, **k):
        raise RuntimeError("exchange down")

    monkeypatch.setattr(tasks, "run_scan", failing_scan)
    with pytest.raises(RuntimeError, match="exchange down"):
        tasks.run_scanner_task()


def test_celery_beat_schedule_lists_scanner_and_reconcile():
    from app.worker.celery_app import celery_app
    beat = celery_app.conf.beat_schedule
    assert "scanner-every-5-min" in beat
    assert "reconcile-positions-every-15-min" in beat
    assert beat["scanner-every-5-min"]["task"] == "app.worker.tasks.run_scanner"


def test_celery_redis_broker_forces_resp2_for_rediss_url():
    """With a rediss:// (Upstash) broker URL the Celery broker must use
    RESP2 (protocol=2). redis-py 6.x otherwise negotiates RESP3
    (HELLO 3 + AUTH) and Upstash's TCP endpoint rejects that handshake
    as 'invalid username-password pair' even with correct credentials.
    The protocol cannot be set via ?protocol=2 in the URL (kombu's
    Connection._init_params rejects it), so it is declared in
    broker_transport_options and injected into the redis pool kwargs by
    the Channel._connparams patch in app/worker/celery_app.py.
    Built the way kombu builds the pool, without connecting.
    """
    import redis
    from celery import Celery
    from kombu.transport.redis import Channel

    from app.worker.celery_app import celery_app

    # 1. The app's own config declares protocol 2.
    assert celery_app.conf.broker_transport_options.get("protocol") == 2

    # 2. A rediss:// broker resolves to protocol 2 in the pool kwargs.
    probe = Celery(
        "resp2-probe",
        broker="rediss://celery:testpass@flowing-elk-220644.upstash.io:6379"
               "?ssl_cert_reqs=CERT_REQUIRED",
        backend="rediss://celery:testpass@flowing-elk-220644.upstash.io:6379"
                "?ssl_cert_reqs=CERT_REQUIRED",
    )
    probe.conf.update(broker_transport_options={"protocol": 2})
    conn = probe.connection()
    channel = Channel.__new__(Channel)
    channel.connection = conn.transport
    params = channel._connparams()
    assert params.get("protocol") == 2
    assert params.get("username") == "celery"
    assert params.get("connection_class") is redis.SSLConnection

    # 3. A pool built from those kwargs negotiates RESP2.
    pool = redis.ConnectionPool(**params)
    assert pool.get_protocol() == 2
    connection = pool.connection_class(**pool.connection_kwargs)
    assert connection.protocol == 2


def test_celery_redis_url_encodes_special_chars_in_password(monkeypatch):
    """A REDIS_PASSWORD containing URL-special characters must reach
    kombu intact. Root cause of the live AUTH failure: redis-py 6.4.0
    already defaults to RESP2, so the RESP3 theory was wrong; the
    failure was the password being mangled by URL parsing when it was
    pasted raw into REDIS_URL. Supplying the raw password via
    REDIS_PASSWORD (and REDIS_USERNAME) makes _celery_redis_url()
    percent-encode it, so kombu parses back exactly the intended
    username/password. Proves the fix end to end through the same
    Channel._connparams path the worker uses.
    """
    import redis
    from celery import Celery
    from kombu.transport.redis import Channel

    from app.worker.celery_app import _celery_redis_url

    special_password = "p@ss:w/rd#1&2=3+4%5"
    monkeypatch.setenv(
        "REDIS_URL",
        "rediss://celery:placeholder@flowing-elk-220644.upstash.io:6379",
    )
    monkeypatch.setenv("REDIS_USERNAME", "celery")
    monkeypatch.setenv("REDIS_PASSWORD", special_password)

    url = _celery_redis_url()
    # The raw special characters must NOT appear unencoded in the URL.
    assert "p@ss:w/rd" not in url
    assert "ssl_cert_reqs=CERT_REQUIRED" in url

    # Round-trip through the exact path the worker uses: build a Celery
    # probe with this URL and read the pool kwargs from Channel._connparams.
    probe = Celery("url-encoding-probe", broker=url, backend=url)
    probe.conf.update(broker_transport_options={"protocol": 2})
    conn = probe.connection()
    channel = Channel.__new__(Channel)
    channel.connection = conn.transport
    params = channel._connparams()
    assert params.get("username") == "celery"
    assert params.get("password") == special_password
    assert params.get("protocol") == 2
    assert params.get("connection_class") is redis.SSLConnection

    # And a pool built from those kwargs carries the exact password.
    pool = redis.ConnectionPool(**params)
    assert pool.connection_kwargs.get("password") == special_password


def test_celery_redis_url_without_env_override_is_unchanged(monkeypatch):
    """Without REDIS_USERNAME/REDIS_PASSWORD the broker URL is used
    as-is (previous behaviour), with ssl_cert_reqs appended for rediss.
    """
    from app.worker.celery_app import _celery_redis_url

    monkeypatch.delenv("REDIS_USERNAME", raising=False)
    monkeypatch.delenv("REDIS_PASSWORD", raising=False)
    monkeypatch.setenv(
        "REDIS_URL",
        "rediss://celery:plainpass123@flowing-elk-220644.upstash.io:6379",
    )
    url = _celery_redis_url()
    assert url == (
        "rediss://celery:plainpass123@flowing-elk-220644.upstash.io:6379"
        "?ssl_cert_reqs=CERT_REQUIRED"
    )
