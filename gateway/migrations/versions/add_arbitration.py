"""add arbitration tables

Revision ID: add_arbitration
Revises: add_treasury_altered
Create Date: 2026-07-13 22:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_arbitration"
down_revision: Union[str, None] = "add_treasury_altered"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create arbitrators table
    op.create_table(
        "arbitrators",
        sa.Column("address", sa.String(), primary_key=True, index=True),
        sa.Column("status", sa.String(), server_default="active", nullable=False),
        sa.Column("registered_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    # Create dispute_arbitrators table
    op.create_table(
        "dispute_arbitrators",
        sa.Column("id", sa.Integer(), primary_key=True, index=True, autoincrement=True),
        sa.Column("bounty_id", sa.String(), sa.ForeignKey("bounties.bounty_id", ondelete="CASCADE"), nullable=False),
        sa.Column("arbitrator_address", sa.String(), sa.ForeignKey("arbitrators.address", ondelete="CASCADE"), nullable=False),
        sa.Column("vote", sa.String(), nullable=True),
        sa.Column("voted_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("bounty_id", "arbitrator_address", name="uq_bounty_arbitrator"),
    )
    # Create indexes
    op.create_index("idx_dispute_arbitrators_bounty_id", "dispute_arbitrators", ["bounty_id"])
    op.create_index("idx_dispute_arbitrators_arbitrator", "dispute_arbitrators", ["arbitrator_address"])


def downgrade() -> None:
    op.drop_index("idx_dispute_arbitrators_arbitrator", table_name="dispute_arbitrators")
    op.drop_index("idx_dispute_arbitrators_bounty_id", table_name="dispute_arbitrators")
    op.drop_table("dispute_arbitrators")
    op.drop_table("arbitrators")
