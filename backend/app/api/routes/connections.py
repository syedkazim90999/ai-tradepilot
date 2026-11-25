"""Binance connections (encrypted keys, masked display, permission validation)."""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.security import decrypt_secret, encrypt_secret, mask_api_key
from app.db.session import get_db
from app.models import ExchangeConnection, User
from app.schemas import ConnectionCreate, ConnectionOut
from app.services.binance_client import BinanceClient, BinanceError

router = APIRouter(prefix="/connections", tags=["connections"])


def _out(conn: ExchangeConnection) -> ConnectionOut:
    return ConnectionOut(
        id=conn.id, exchange=conn.exchange, environment=conn.environment,
        api_key_masked="****" + conn.api_key_last4, label=conn.label,
        is_active=conn.is_active, can_trade=conn.can_trade, can_read=conn.can_read,
        permissions=conn.permissions, last_validated_at=conn.last_validated_at,
        created_at=conn.created_at,
    )


@router.get("", response_model=list[ConnectionOut])
async def list_connections(current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(ExchangeConnection).where(ExchangeConnection.user_id == current.id))).scalars().all()
    return [_out(r) for r in rows]


@router.post("", response_model=ConnectionOut, status_code=201)
async def create_connection(body: ConnectionCreate, current: User = Depends(get_current_user),
                            db: AsyncSession = Depends(get_db)):
    conn = ExchangeConnection(
        user_id=current.id, environment=body.environment, label=body.label,
        api_key_encrypted=encrypt_secret(body.api_key),
        api_secret_encrypted=encrypt_secret(body.api_secret),
        api_key_last4=body.api_key[-4:],
    )
    db.add(conn)
    await db.commit()
    await db.refresh(conn)
    return _out(conn)


async def _validate_with_binance(conn: ExchangeConnection) -> dict:
    api_key = decrypt_secret(conn.api_key_encrypted)
    api_secret = decrypt_secret(conn.api_secret_encrypted)
    async with BinanceClient(api_key, api_secret, testnet=(conn.environment == "testnet")) as client:
        await client.sync_time()
        info = await client.account_info()
        perms = info.get("permissions", [])
        return {
            "can_trade": bool(info.get("canTrade")),
            "can_read": True,
            "permissions": perms,
            "no_withdrawal": "WITHDRAW" not in perms,
        }


@router.post("/{conn_id}/validate", response_model=ConnectionOut)
async def validate_connection(conn_id: uuid.UUID, current: User = Depends(get_current_user),
                              db: AsyncSession = Depends(get_db)):
    conn = (await db.execute(
        select(ExchangeConnection).where(ExchangeConnection.id == conn_id,
                                        ExchangeConnection.user_id == current.id))).scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    try:
        result = await _validate_with_binance(conn)
    except BinanceError as exc:
        conn.last_error = str(exc)
        conn.is_active = False
        await db.commit()
        raise HTTPException(status_code=400, detail=f"Binance validation failed: {exc}")
    if not result["no_withdrawal"]:
        raise HTTPException(status_code=400, detail="API key has withdrawal permission — refused")
    from datetime import datetime, timezone
    conn.can_trade = result["can_trade"]
    conn.can_read = result["can_read"]
    conn.permissions = result["permissions"]
    conn.last_validated_at = datetime.now(timezone.utc)
    conn.last_error = None
    conn.is_active = True
    await db.commit()
    return _out(conn)


@router.delete("/{conn_id}")
async def delete_connection(conn_id: uuid.UUID, current: User = Depends(get_current_user),
                            db: AsyncSession = Depends(get_db)):
    conn = (await db.execute(
        select(ExchangeConnection).where(ExchangeConnection.id == conn_id,
                                        ExchangeConnection.user_id == current.id))).scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    await db.delete(conn)
    await db.commit()
    return {"detail": "Connection deleted"}
