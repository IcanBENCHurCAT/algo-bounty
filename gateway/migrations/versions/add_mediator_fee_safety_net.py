"""add platform_fee and treasury_address to bounties

Revision ID: add_mediator_fee_safety_net
Revises: add_webhook_delivery
Create Date: 2026-07-18 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_mediator_fee_safety_net"
down_revision: Union[str, None] = "add_webhook_delivery"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bounties",
        sa.Column(
            "platform_fee",
            sa.Integer(),
            nullable=False,
            server_default="200",
        )
    )
    op.add_column(
        "bounties",
        sa.Column(
            "treasury_address",
            sa.String(length=58),
            nullable=False,
            server_default="RTCed54abc91f37d8d2d2cb2cf69ce60b0021fd67e5",
        )
    )


def downgrade() -> None:
    op.drop_column("bounties", "platform_fee")
    op.drop_column("bounties", "treasury_address")
