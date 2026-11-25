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
    """Upgrade to head creates contact_messages; downgrade one step removes it;
    upgrade again restores it. Runs on a scratch SQLite file, never the dev DB."""
    db_path = str(tmp_path / "scratch.db")
    _run_alembic(db_path, "upgrade", "head")
    con = sqlite3.connect(db_path)
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "contact_messages" in tables
    assert "users" in tables
    assert "market_signals" in tables
    con.close()
    _run_alembic(db_path, "downgrade", "-1")
    con = sqlite3.connect(db_path)
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    con.close()
    assert "contact_messages" not in tables
    assert "users" in tables  # only the newest revision was rolled back
    _run_alembic(db_path, "upgrade", "head")
    con = sqlite3.connect(db_path)
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    con.close()
    assert "contact_messages" in tables


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
