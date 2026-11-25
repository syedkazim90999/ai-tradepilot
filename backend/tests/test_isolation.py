"""Authorization / isolation: user A cannot read user B's data; admin never
sees secrets (no password hashes, no encrypted API keys)."""
from tests.conftest import (
    admin_token, auth_headers, get_user, make_closed_trade, register_and_login,
    seed_rows, unique_email,
)


def _two_users(client):
    email_a, _, tok_a, _ = register_and_login(client)
    email_b, _, tok_b, _ = register_and_login(client)
    return (get_user(email_a), tok_a), (get_user(email_b), tok_b)


def test_user_cannot_read_other_users_trade(client):
    (ua, tok_a), (ub, tok_b) = _two_users(client)
    seed_rows([make_closed_trade(ub.id, pnl="100")])
    trades_b = client.get("/api/v1/trades", headers=auth_headers(tok_b)).json()
    assert len(trades_b) == 1
    trade_id = trades_b[0]["id"]
    assert client.get(f"/api/v1/trades/{trade_id}", headers=auth_headers(tok_a)).status_code == 404
    assert client.get("/api/v1/trades", headers=auth_headers(tok_a)).json() == []


def test_user_cannot_read_other_users_positions_orders_notifications(client):
    from app.models import Notification, Order, Position
    from decimal import Decimal
    (ua, tok_a), (ub, tok_b) = _two_users(client)
    seed_rows([
        Position(user_id=ub.id, symbol="BTCUSDT", side="LONG", quantity=Decimal("0.1"),
                 entry_price=Decimal("60000")),
        Order(user_id=ub.id, symbol="BTCUSDT", client_order_id="TP-TEST-ISOLATION-1",
              side="BUY", order_type="MARKET", quantity=Decimal("0.1")),
        Notification(user_id=ub.id, type="info", title="hi", message="hello"),
    ])
    assert client.get("/api/v1/positions", headers=auth_headers(tok_a)).json() == []
    assert client.get("/api/v1/orders", headers=auth_headers(tok_a)).json() == []
    assert client.get("/api/v1/notifications", headers=auth_headers(tok_a)).json() == []
    assert len(client.get("/api/v1/positions", headers=auth_headers(tok_b)).json()) == 1
    # Marking another user's notification as read must 404.
    notifs_b = client.get("/api/v1/notifications", headers=auth_headers(tok_b)).json()
    r = client.post(f"/api/v1/notifications/{notifs_b[0]['id']}/read", headers=auth_headers(tok_a))
    assert r.status_code == 404


def test_user_cannot_read_or_delete_other_users_connection(client):
    (ua, tok_a), (ub, tok_b) = _two_users(client)
    r = client.post("/api/v1/connections", headers=auth_headers(tok_b),
                    json={"api_key": "KEY12345678", "api_secret": "SECRET12345678",
                          "environment": "testnet", "label": "mine"})
    assert r.status_code == 201, r.text
    conn_id = r.json()["id"]
    assert client.get("/api/v1/connections", headers=auth_headers(tok_a)).json() == []
    assert client.delete(f"/api/v1/connections/{conn_id}", headers=auth_headers(tok_a)).status_code == 404
    assert client.get("/api/v1/connections", headers=auth_headers(tok_b)).json()[0]["id"] == conn_id


def test_user_cannot_change_other_users_bot_settings(client):
    (ua, tok_a), (ub, tok_b) = _two_users(client)
    client.put("/api/v1/bot/settings", headers=auth_headers(tok_b),
               json={"risk_per_trade_pct": 1.5, "max_positions": 5})
    mine = client.get("/api/v1/bot/settings", headers=auth_headers(tok_a)).json()
    assert float(mine["risk_per_trade_pct"]) == 0.5
    assert mine["max_positions"] == 2


def test_connection_response_masks_key_and_never_leaks_secret(client):
    _, _, tok, _ = register_and_login(client)
    r = client.post("/api/v1/connections", headers=auth_headers(tok),
                    json={"api_key": "ABCDEFGH1234", "api_secret": "SUPERSECRETVALUE",
                          "environment": "testnet"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["api_key_masked"] == "****1234"
    assert "SUPERSECRETVALUE" not in str(body)
    assert "ABCDEFGH1234" not in str(body)
    assert "api_key_encrypted" not in body and "api_secret_encrypted" not in body


def test_admin_users_list_contains_no_password_hash_or_secret(client):
    email, _, tok, _ = register_and_login(client)
    client.post("/api/v1/connections", headers=auth_headers(tok),
                json={"api_key": "ABCDEFGH1234", "api_secret": "SUPERSECRETVALUE", "environment": "testnet"})
    adm = admin_token(client)
    body = client.get("/api/v1/admin/users", headers=auth_headers(adm)).json()
    assert any(u["email"] == email for u in body)
    assert "password_hash" not in str(body)
    assert "SUPERSECRETVALUE" not in str(body)
    assert "api_key_encrypted" not in str(body)


def test_non_admin_cannot_access_admin_endpoints(client):
    _, _, tok, _ = register_and_login(client)
    for path in ["/api/v1/admin/overview", "/api/v1/admin/users", "/api/v1/admin/signals",
                 "/api/v1/admin/strategies/performance", "/api/v1/admin/audit-logs"]:
        r = client.get(path, headers=auth_headers(tok))
        assert r.status_code in (401, 403), (path, r.status_code)


def test_user_token_cannot_use_admin_login_token_paths(client):
    # A user JWT (type "access") must not pass the admin guard.
    _, _, tok, _ = register_and_login(client)
    r = client.get("/api/v1/admin/overview", headers=auth_headers(tok))
    assert r.status_code == 403
