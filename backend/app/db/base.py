"""Declarative base + shared columns."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


def utcnow_col(nullable: bool = False):
    return DateTime(timezone=True), {"default": _utcnow, "nullable": nullable}
