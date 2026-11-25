"""Auth routes: register/login/logout/refresh, email verify, password reset,
first-run Super Admin setup, sessions, TOTP."""
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.deps import get_current_user, rate_limit
from app.core.security import (
    create_access_token, create_refresh_token, decode_token, hash_password,
    new_jti, new_totp_secret, totp_uri, verify_password, verify_totp,
)
from app.db.session import get_db
from app.models import SuperAdmin, User, UserSession
from app.schemas import (
    ChangePasswordRequest, ForgotPasswordRequest, LoginRequest, RefreshRequest,
    RegisterRequest, ResetPasswordRequest, SessionOut, SetupAdminRequest,
    TokenResponse, TwoFADisableRequest, TwoFAVerifyRequest,
    UpdateProfileRequest, UserOut, VerifyEmailRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])
log = logging.getLogger(__name__)


def _dev_verification_url(token: str) -> str:
    # Dev only: no real SMTP — the verification URL is logged and returned.
    return f"/api/v1/auth/verify-email?token={token}"


async def _issue_tokens(db: AsyncSession, user: User, request: Request) -> TokenResponse:
    access_jti, refresh_jti = new_jti(), new_jti()
    now = datetime.now(timezone.utc)
    db.add(UserSession(
        user_id=user.id, jti=refresh_jti, token_type="refresh",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        expires_at=now + timedelta(days=7),
    ))
    # Also record the access jti so it can be revoked.
    db.add(UserSession(
        user_id=user.id, jti=access_jti, token_type="access",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        expires_at=now + timedelta(minutes=30),
    ))
    await db.commit()
    return TokenResponse(
        access_token=create_access_token(str(user.id), access_jti),
        refresh_token=create_refresh_token(str(user.id), refresh_jti),
    )


@router.post("/register", status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    token = secrets.token_urlsafe(32)
    user = User(email=body.email, password_hash=hash_password(body.password),
                full_name=body.full_name, email_verification_token=token)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    url = _dev_verification_url(token)
    log.info("Verification URL for %s: %s", body.email, url)
    # Dev response includes the token (no real SMTP in dev). Never do this in prod.
    return {"user": UserOut.model_validate(user), "verification_token": token,
            "verification_url": url, "note": "Dev only: token returned because no SMTP is configured."}


@router.post("/verify-email")
async def verify_email(body: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(
        select(User).where(User.email_verification_token == body.token))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification token")
    user.is_email_verified = True
    user.email_verification_token = None
    await db.commit()
    return {"detail": "Email verified"}


@router.post("/login", response_model=TokenResponse,
             dependencies=[Depends(rate_limit(10, 60))])
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.is_suspended:
        raise HTTPException(status_code=403, detail="Account suspended")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    if user.totp_enabled:
        if not body.totp_code or not user.totp_secret or not verify_totp(user.totp_secret, body.totp_code):
            raise HTTPException(status_code=401, detail="Invalid or missing 2FA code")
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    return await _issue_tokens(db, user, request)


@router.post("/logout")
async def logout(current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Revoke all sessions for this user.
    sessions = (await db.execute(
        select(UserSession).where(UserSession.user_id == current.id,
                                 UserSession.is_revoked == False))).scalars().all()  # noqa: E712
    for s in sessions:
        s.is_revoked = True
    await db.commit()
    return {"detail": "Logged out"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    session = (await db.execute(
        select(UserSession).where(UserSession.jti == payload["jti"],
                                 UserSession.is_revoked == False))).scalar_one_or_none()  # noqa: E712
    if session is None:
        raise HTTPException(status_code=401, detail="Session revoked")
    session.is_revoked = True  # rotate
    user = (await db.execute(select(User).where(User.id == uuid.UUID(payload["sub"])))).scalar_one_or_none()
    if not user or not user.is_active or user.is_suspended:
        raise HTTPException(status_code=401, detail="User unavailable")
    return await _issue_tokens(db, user, request)


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    # Always return success to avoid email enumeration.
    if user:
        token = secrets.token_urlsafe(32)
        user.password_reset_token = token
        user.password_reset_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        await db.commit()
        log.info("Password reset token for %s: %s", body.email, token)
        return {"detail": "If the email exists, a reset link was sent", "dev_reset_token": token}
    return {"detail": "If the email exists, a reset link was sent"}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(
        select(User).where(User.password_reset_token == body.token))).scalar_one_or_none()
    if not user or not user.password_reset_expires_at or \
            user.password_reset_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    user.password_hash = hash_password(body.new_password)
    user.password_reset_token = None
    user.password_reset_expires_at = None
    await db.commit()
    return {"detail": "Password reset"}


@router.post("/setup-admin", status_code=201)
async def setup_admin(body: SetupAdminRequest, db: AsyncSession = Depends(get_db)):
    """First-run Super Admin setup. Fails with 409 once an admin exists."""
    existing = (await db.execute(select(SuperAdmin))).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Super Admin already exists")
    admin = SuperAdmin(email=body.email, password_hash=hash_password(body.password),
                       full_name=body.full_name)
    db.add(admin)
    await db.commit()
    return {"detail": "Super Admin created", "email": admin.email}


@router.get("/me", response_model=UserOut)
async def me(current: User = Depends(get_current_user)):
    return current


@router.put("/me", response_model=UserOut)
async def update_me(body: UpdateProfileRequest, current: User = Depends(get_current_user),
                    db: AsyncSession = Depends(get_db)):
    if body.full_name is not None:
        current.full_name = body.full_name.strip() or None
    await db.commit()
    await db.refresh(current)
    return current


@router.post("/change-password")
async def change_password(body: ChangePasswordRequest, current: User = Depends(get_current_user),
                          db: AsyncSession = Depends(get_db)):
    if not verify_password(body.current_password, current.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if body.new_password == body.current_password:
        raise HTTPException(status_code=400, detail="New password must differ from the current password")
    current.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"detail": "Password changed"}


@router.post("/2fa/setup")
async def twofa_setup(current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Generate a fresh TOTP secret and store it (unverified). The caller must
    verify it with POST /2fa/verify before 2FA becomes active. The secret is
    returned once in this response and never logged."""
    if current.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled")
    secret = new_totp_secret()
    current.totp_secret = secret
    await db.commit()
    return {"otpauth_uri": totp_uri(secret, current.email), "secret": secret,
            "detail": "Scan the otpauth URI (or enter the secret manually) in your authenticator app, then verify with POST /api/v1/auth/2fa/verify."}


@router.post("/2fa/verify")
async def twofa_verify(body: TwoFAVerifyRequest, current: User = Depends(get_current_user),
                       db: AsyncSession = Depends(get_db)):
    if not current.totp_secret or not verify_totp(current.totp_secret, body.code):
        raise HTTPException(status_code=400, detail="Invalid 2FA code")
    current.totp_enabled = True
    await db.commit()
    return {"detail": "2FA enabled", "totp_enabled": True}


@router.post("/2fa/disable")
async def twofa_disable(body: TwoFADisableRequest, current: User = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):
    if not current.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled")
    if not verify_password(body.current_password, current.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if body.code and not verify_totp(current.totp_secret or "", body.code):
        raise HTTPException(status_code=400, detail="Invalid 2FA code")
    current.totp_enabled = False
    current.totp_secret = None
    await db.commit()
    return {"detail": "2FA disabled", "totp_enabled": False}


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    sessions = (await db.execute(
        select(UserSession).where(UserSession.user_id == current.id).order_by(UserSession.created_at.desc())
    )).scalars().all()
    return sessions


@router.delete("/sessions/{session_id}")
async def revoke_session(session_id: uuid.UUID, current: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    session = (await db.execute(
        select(UserSession).where(UserSession.id == session_id,
                                 UserSession.user_id == current.id))).scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.is_revoked = True
    await db.commit()
    return {"detail": "Session revoked"}
