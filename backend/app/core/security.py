"""Security helpers: Argon2id passwords, JWT, Fernet encryption, TOTP."""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

_ph = PasswordHasher()  # Argon2id by default


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, password)
    except (VerifyMismatchError, Exception):
        return False


def create_access_token(subject: str, jti: str, expires_minutes: Optional[int] = None) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=expires_minutes or s.access_token_expire_minutes)
    payload = {"sub": subject, "jti": jti, "type": "access", "iat": now, "exp": exp}
    return jwt.encode(payload, s.secret_key, algorithm=s.jwt_algorithm)


def create_refresh_token(subject: str, jti: str) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(days=s.refresh_token_expire_days)
    payload = {"sub": subject, "jti": jti, "type": "refresh", "iat": now, "exp": exp}
    return jwt.encode(payload, s.secret_key, algorithm=s.jwt_algorithm)


def decode_token(token: str) -> dict:
    s = get_settings()
    return jwt.decode(token, s.secret_key, algorithms=[s.jwt_algorithm])


def new_jti() -> str:
    return secrets.token_hex(16)


def get_fernet() -> Fernet:
    key = get_settings().fernet_key
    if not key:
        raise RuntimeError("FERNET_KEY is not set — generate one with scripts/generate_fernet_key.py")
    return Fernet(key.encode())


def encrypt_secret(plaintext: str) -> str:
    return get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    try:
        return get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Could not decrypt stored secret") from exc


def mask_api_key(api_key: str) -> str:
    """Show only the last 4 characters of an API key."""
    if not api_key:
        return ""
    return "****" + api_key[-4:] if len(api_key) > 4 else "****"


# --- TOTP 2FA ---
def new_totp_secret() -> str:
    return pyotp.random_base32()


def totp_uri(secret: str, email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name="AI TradePilot")


def verify_totp(secret: str, code: str) -> bool:
    try:
        return pyotp.TOTP(secret).verify(code, valid_window=1)
    except Exception:
        return False
