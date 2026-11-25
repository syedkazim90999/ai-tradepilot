"""In-app notifications."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification


async def notify(db: AsyncSession, user_id, type_: str, title: str, message: str, data: dict | None = None):
    n = Notification(user_id=user_id, type=type_, title=title, message=message, data=data)
    db.add(n)
    await db.commit()
    return n
