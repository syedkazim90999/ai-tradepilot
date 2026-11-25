"""Smoke tests: health, auth flow, auth rejection, signal generation on fixtures."""
import os
import sys

import pandas as pd
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app  # noqa: E402
from app.services.signals import generate_signal, klines_to_df  # noqa: E402

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["database"] == "ok"
    assert "exchange_reachable" in body


def test_auth_required():
    r = client.get("/api/v1/auth/me")
    assert r.status_code in (401, 403)


def test_register_login_flow():
    email = "smoke@example.com"
    r = client.post("/api/v1/auth/register", json={
        "email": email, "password": "SmokePass123!", "full_name": "Smoke Test"})
    assert r.status_code in (201, 409), r.text
    r = client.post("/api/v1/auth/login", json={"email": email, "password": "SmokePass123!"})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == email
    r = client.get("/api/v1/dashboard/overview", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["total_trades"] == 0


def _fixture_klines(n=250, start=60000.0, drift=30.0):
    """Deterministic rising klines: [open_time, open, high, low, close, volume, ...]"""
    rows = []
    price = start
    for i in range(n):
        o = price
        c = price + drift
        rows.append([i * 60000, str(o), str(c + 50), str(o - 50), str(c),
                     "100", i * 60000, "6000000", "10", "50", "3000000", "0"])
        price = c
    return rows


def test_signal_generation_on_fixture():
    df = klines_to_df(_fixture_klines())
    assert len(df) == 250
    sig = generate_signal("BTCUSDT", df, timeframe="1h")
    assert sig["symbol"] == "BTCUSDT"
    assert sig["direction"] in ("LONG", "SHORT", "WAIT")
    assert sig["entry_price"] > 0
    assert sig["stop_loss"] > 0 and sig["take_profit"] > 0
    assert "rsi_14" in sig["indicators"]
    assert "atr_14" in sig["indicators"]


def test_setup_admin_first_run_only():
    r = client.post("/api/v1/auth/setup-admin", json={
        "email": "admin@example.com", "password": "AdminPass123456"})
    assert r.status_code in (201, 409), r.text
    r2 = client.post("/api/v1/auth/setup-admin", json={
        "email": "admin2@example.com", "password": "AdminPass123456"})
    assert r2.status_code == 409
