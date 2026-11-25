"""Public contact form: stores a message for the admin team. No auth required;
rate-limited. Never accept passwords or API secrets here (schema has no
such field)."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import rate_limit
from app.db.session import get_db
from app.models import ContactMessage
from app.schemas import ContactCreate, ContactOut

router = APIRouter(prefix="/contact", tags=["contact"])


@router.post("", response_model=ContactOut, status_code=201,
             dependencies=[Depends(rate_limit(5, 60))])
async def submit_contact(body: ContactCreate, db: AsyncSession = Depends(get_db)):
    msg = ContactMessage(name=body.name, email=body.email, message=body.message)
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg
