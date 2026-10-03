"""add cold-start support: collateral deposits and co-signing vouches

Revision ID: add_collateral_vouch
Revises: c326801a9571
Create Date: 2026-09-29 11:00:00.000000

Implements two cold-start bootstrapping mechanisms (Karma #175):
- Collateral deposits: newcomers lock ALGO as temporary reputation
- Co-signing vouches: Elite agents vouch for newcomers by co-signing their first bounty
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_collateral_vouch"
down_revision: Union[str, None] = "c326801a9571"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── Collateral deposits table ─────────────────────────────────────
    op.create_table(
        "collateral_deposits",
        sa.Column("id", sa.Integer(), primary_key=True, index=True, autoincrement=True),
        sa.Column(
            "agent_address", sa.String(), sa.ForeignKey("agents.address", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("amount_microalgo", sa.BigInteger(), nullable=False),
        sa.Column("bounty_id", sa.String(), sa.ForeignKey("bounties.bounty_id", ondelete="CASCADE"), nullable=True),
        sa.Column("status", sa.String(), server_default="locked", nullable=False),
        # locked = held while bounty is active
        # slashed = lost due to bounty failure
        # released = returned after successful completion
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("released_at", sa.DateTime(), nullable=True),
        sa.Index("ix_collateral_agent", "agent_address"),
        sa.Index("ix_collateral_bounty", "bounty_id"),
        sa.Index("ix_collateral_status", "status"),
    )

    # ─── Co-signing vouches table ──────────────────────────────────────
    op.create_table(
        "vouches",
        sa.Column("id", sa.Integer(), primary_key=True, index=True, autoincrement=True),
        sa.Column(
            "vouching_agent", sa.String(), sa.ForeignKey("agents.address", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "vouched_agent", sa.String(), sa.ForeignKey("agents.address", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("bounty_id", sa.String(), sa.ForeignKey("bounties.bounty_id", ondelete="SET NULL"), nullable=True),
        sa.Column("amount_at_stake", sa.BigInteger(), server_default="0", nullable=False),
        # How much of the vouching agent's "reputation capital" is at risk
        sa.Column("status", sa.String(), server_default="active", nullable=False),
        # active, resolved, slashed, expired
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("vouching_agent", "vouched_agent", "bounty_id", name="uq_vouch_triple"),
        sa.Index("ix_vouch_vouched", "vouched_agent"),
        sa.Index("ix_vouch_vouching", "vouching_agent"),
        sa.Index("ix_vouch_bounty", "bounty_id"),
        sa.Index("ix_vouch_status", "status"),
    )

    # ─── Agent cold-start flags ────────────────────────────────────────
    op.add_column(
        "agents",
        sa.Column("has_collateral", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "agents",
        sa.Column("vouched_by_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "agents",
        sa.Column("cold_start_eligible", sa.Boolean(), server_default="true", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("agents", "cold_start_eligible")
    op.drop_column("agents", "vouched_by_count")
    op.drop_column("agents", "has_collateral")
    op.drop_index("ix_vouch_status", table_name="vouches")
    op.drop_index("ix_vouch_bounty", table_name="vouches")
    op.drop_index("ix_vouch_vouching", table_name="vouches")
    op.drop_index("ix_vouch_vouched", table_name="vouches")
    op.drop_table("vouches")
    op.drop_index("ix_collateral_status", table_name="collateral_deposits")
    op.drop_index("ix_collateral_bounty", table_name="collateral_deposits")
    op.drop_index("ix_collateral_agent", table_name="collateral_deposits")
    op.drop_table("collateral_deposits")
