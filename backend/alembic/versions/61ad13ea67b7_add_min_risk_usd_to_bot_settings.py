"""add min_risk_usd to bot_settings

Revision ID: 61ad13ea67b7
Revises: 7f3a9c1d2e4b
Create Date: 2026-11-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '61ad13ea67b7'
down_revision: Union[str, None] = '7f3a9c1d2e4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('bot_settings',
        sa.Column('min_risk_usd', sa.Numeric(precision=10, scale=2),
                  nullable=False, server_default='2.00'))


def downgrade() -> None:
    op.drop_column('bot_settings', 'min_risk_usd')
