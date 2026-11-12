"""add sanctions screening fields to bounties

Revision ID: add_sanctions_screening
Revises: add_collateral_vouch
Create Date: 2026-11-12 14:00:00.000000

Implements OFAC/sanctions screening at point of entry via KYA integration (Issue #180):
- screening_status: status of KYA screening ('pending', 'passed', 'flagged', 'blocked')
- screened_at: timestamp when screening occurred
- screening_hash: SHA256 audit hash
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_sanctions_screening"
down_revision: Union[str, None] = "add_collateral_vouch"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bounties",
        sa.Column("screening_status", sa.String(), server_default="pending", nullable=False),
    )
    op.add_column(
        "bounties",
        sa.Column("screened_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "bounties",
        sa.Column("screening_hash", sa.String(), nullable=True),
    )
    op.create_index(
        "idx_bounties_screening_status",
        "bounties",
        ["screening_status"],
    )


def downgrade() -> None:
    op.drop_index("idx_bounties_screening_status", table_name="bounties")
    op.drop_column("bounties", "screening_hash")
    op.drop_column("bounties", "screened_at")
    op.drop_column("bounties", "screening_status")
