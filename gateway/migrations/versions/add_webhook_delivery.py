"""add webhook_delivery_records table

Revision ID: add_webhook_delivery
Revises: add_arbitration
Create Date: 2026-07-15 21:28:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_webhook_delivery"
down_revision: Union[str, None] = "add_arbitration"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create webhook_delivery_records table for X-GitHub-Delivery idempotency
    op.create_table(
        "webhook_delivery_records",
        sa.Column("id", sa.Integer(), primary_key=True, index=True, autoincrement=True),
        sa.Column("delivery_id", sa.String(), nullable=False, unique=True),
        sa.Column("processed_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("status", sa.String(), server_default="success", nullable=False),
    )
    op.create_index(
        "idx_webhook_delivery_delivery_id",
        "webhook_delivery_records",
        ["delivery_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("idx_webhook_delivery_delivery_id", table_name="webhook_delivery_records")
    op.drop_table("webhook_delivery_records")
