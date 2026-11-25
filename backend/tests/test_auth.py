"""Authentication tests: register/login, wrong password, Argon2id hashing,
session revocation, expired/invalid JWT, rate limiting."""
import time
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, new_jti, verify_password
from tests.conftest import admin_token, auth_headers, get_user, register_and_login, unique_email


def test_register_returns_201_and_no_password_leak(client):
    email = unique_email()
    r = client.post("/api/v1/auth/register", json={"email": email, "password": "TestPass123!", "full_name": "Alice"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["user"]["email"] == email
    assert "password" not in body["user"]
    assert "password_hash" not in str(body)


def test_register_duplicate_email_409(client):
    email = unique_email()
    assert client.post("/api/v1/auth/register", json={"email": email, "password": "TestPass123!"}).status_code == 201
    r = client.post("/api/v1/auth/register", json={"email": email, "password": "TestPass123!"})
    assert r.status_code == 409


def test_register_short_password_rejected(client):
    r = client.post("/api/v1/auth/register", json={"email": unique_email(), "password": "short"})
    assert r.status_code == 422


def test_login_wrong_password_401(client):
    email, pw, _, _ = register_and_login(client)
    r = client.post("/api/v1/auth/login", json={"email": email, "password": "WrongPass999!"})
    assert r.status_code == 401


def test_login_unknown_email_401(client):
    r = client.post("/api/v1/auth/login", json={"email": unique_email(), "password": "Whatever123!"})
    assert r.status_code == 401


def test_password_hash_is_argon2id_not_plaintext(client):
    email, pw, _, _ = register_and_login(client)
    user = get_user(email)
    assert user.password_hash != pw
    assert user.password_hash.startswith("$argon2id$")
    assert verify_password(pw, user.password_hash)
    assert not verify_password("WrongPass999!", user.password_hash)
    # Argon2id helper itself
    h = hash_password("AnotherPass123!")
    assert h.startswith("$argon2id$")


def test_me_requires_auth(client):
    assert client.get("/api/v1/auth/me").status_code in (401, 403)


def test_invalid_jwt_rejected(client):
    r = client.get("/api/v1/auth/me", headers=auth_headers("not.a.real.token"))
    assert r.status_code == 401


def test_expired_jwt_rejected(client):
    email, _, token, _ = register_and_login(client)
    # Forge an expired access token with a valid signature (same secret).
    now = datetime.now(timezone.utc)
    payload = {"sub": str(get_user(email).id), "jti": new_jti(), "type": "access",
               "iat": now - timedelta(hours=1), "exp": now - timedelta(minutes=1)}
    expired = jwt.encode(payload, get_settings().secret_key, algorithm="HS256")
    r = client.get("/api/v1/auth/me", headers=auth_headers(expired))
    assert r.status_code == 401
    assert "expired" in r.json()["detail"].lower()


def test_refresh_token_cannot_be_used_as_access(client):
    _, _, _, refresh = register_and_login(client)
    r = client.get("/api/v1/auth/me", headers=auth_headers(refresh))
    assert r.status_code == 401


def test_logout_revokes_all_sessions(client):
    _, _, token, _ = register_and_login(client)
    r = client.post("/api/v1/auth/logout", headers=auth_headers(token))
    assert r.status_code == 200
    r = client.get("/api/v1/auth/me", headers=auth_headers(token))
    assert r.status_code == 401


def test_revoke_single_session(client):
    email, _, token, _ = register_and_login(client)
    sessions = client.get("/api/v1/auth/sessions", headers=auth_headers(token)).json()
    assert len(sessions) >= 1
    # Revoke the refresh session; access token must keep working only if its
    # own session is untouched — revoke the ACCESS session instead.
    access_sessions = [s for s in sessions if s["token_type"] == "access"]
    assert access_sessions
    r = client.delete(f"/api/v1/auth/sessions/{access_sessions[0]['id']}", headers=auth_headers(token))
    assert r.status_code == 200
    assert client.get("/api/v1/auth/me", headers=auth_headers(token)).status_code == 401


def test_revoke_other_users_session_404(client):
    _, _, token_a, _ = register_and_login(client)
    _, _, token_b, _ = register_and_login(client)
    sessions_b = client.get("/api/v1/auth/sessions", headers=auth_headers(token_b)).json()
    r = client.delete(f"/api/v1/auth/sessions/{sessions_b[0]['id']}", headers=auth_headers(token_a))
    assert r.status_code == 404


def test_refresh_rotates_and_old_refresh_is_dead(client):
    _, _, _, refresh = register_and_login(client)
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200
    r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r2.status_code == 401


def test_login_rate_limit_429(client):
    email = unique_email()
    client.post("/api/v1/auth/register", json={"email": email, "password": "TestPass123!"})
    statuses = []
    for _ in range(12):
        r = client.post("/api/v1/auth/login", json={"email": email, "password": "WrongPass999!"})
        statuses.append(r.status_code)
    assert 429 in statuses, f"expected a 429 among login attempts, got {statuses}"


def test_suspended_user_cannot_login(client):
    email, pw, token, _ = register_and_login(client)
    adm = admin_token(client)
    user = get_user(email)
    r = client.post(f"/api/v1/admin/users/{user.id}/suspend", headers=auth_headers(adm))
    assert r.status_code == 200
    r = client.post("/api/v1/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 403


def test_change_password_flow(client):
    email, pw, token, _ = register_and_login(client)
    r = client.post("/api/v1/auth/change-password", headers=auth_headers(token),
                    json={"current_password": "WrongPass999!", "new_password": "NewPass12345!"})
    assert r.status_code == 400
    r = client.post("/api/v1/auth/change-password", headers=auth_headers(token),
                    json={"current_password": pw, "new_password": "NewPass12345!"})
    assert r.status_code == 200
    r = client.post("/api/v1/auth/login", json={"email": email, "password": "NewPass12345!"})
    assert r.status_code == 200
    r = client.post("/api/v1/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 401


def test_update_profile(client):
    _, _, token, _ = register_and_login(client)
    r = client.put("/api/v1/auth/me", headers=auth_headers(token), json={"full_name": "New Name"})
    assert r.status_code == 200, r.text
    assert r.json()["full_name"] == "New Name"


def test_2fa_setup_verify_disable_flow(client):
    import pyotp
    _, _, token, _ = register_and_login(client)
    r = client.post("/api/v1/auth/2fa/setup", headers=auth_headers(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["otpauth_uri"].startswith("otpauth://totp/")
    assert "secret" in body
    # Secret is stored but not yet enabled; login without code still works.
    code = pyotp.TOTP(body["secret"]).now()
    r = client.post("/api/v1/auth/2fa/verify", headers=auth_headers(token), json={"code": "000000"})
    assert r.status_code == 400
    r = client.post("/api/v1/auth/2fa/verify", headers=auth_headers(token), json={"code": code})
    assert r.status_code == 200
    me = client.get("/api/v1/auth/me", headers=auth_headers(token)).json()
    assert me["totp_enabled"] is True
    # Login now requires a valid TOTP code.
    email = me["email"]
    r = client.post("/api/v1/auth/login", json={"email": email, "password": "TestPass123!"})
    assert r.status_code == 401
    r = client.post("/api/v1/auth/login", json={"email": email, "password": "TestPass123!",
                                                "totp_code": pyotp.TOTP(body["secret"]).now()})
    assert r.status_code == 200
    # Disable with wrong password fails; with correct password succeeds.
    r = client.post("/api/v1/auth/2fa/disable", headers=auth_headers(token),
                    json={"current_password": "WrongPass999!"})
    assert r.status_code == 400
    r = client.post("/api/v1/auth/2fa/disable", headers=auth_headers(token),
                    json={"current_password": "TestPass123!"})
    assert r.status_code == 200
    assert client.get("/api/v1/auth/me", headers=auth_headers(token)).json()["totp_enabled"] is False
