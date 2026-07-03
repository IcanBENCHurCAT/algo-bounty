"""provision postgres and initial tables

Revision ID: init
Revises:
Create Date: 2026-07-01 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "init"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("address", sa.String(), primary_key=True, nullable=False),
        sa.Column("karma", sa.Integer(), server_default="25"),
        sa.Column("completed_bounties", sa.Integer(), server_default="0"),
        sa.Column("disputes_lost", sa.Integer(), server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Index("ix_agents_address", "address"),
    )

    op.create_table(
        "bounties",
        sa.Column("bounty_id", sa.String(), primary_key=True, nullable=False),
        sa.Column("app_id", sa.Integer(), unique=True, nullable=True),
        sa.Column("status", sa.String(), server_default="open"),
        sa.Column("creator", sa.String(), nullable=False),
        sa.Column("worker", sa.String(), nullable=True),
        sa.Column("amount", sa.BigInteger()),
        sa.Column("asset_id", sa.Integer(), server_default="0"),
        sa.Column("is_hitm", sa.Boolean(), server_default="false"),
        sa.Column("description", sa.String()),
        sa.Column("repo_url", sa.String(), nullable=False),
        sa.Column("karma_requirement", sa.Integer(), server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deadline_round", sa.Integer(), nullable=True),
        sa.Column("hitm_review_days", sa.Integer(), server_default="7"),
        sa.Column("rejection_count", sa.Integer(), server_default="0"),
        sa.Column("payout_type", sa.String(), nullable=True),
        sa.Index("ix_bounties_bounty_id", "bounty_id"),
        sa.Index("ix_bounties_creator", "creator"),
        sa.Index("ix_bounties_repo_url", "repo_url"),
        sa.Index("ix_bounties_app_id", "app_id", unique=True),
        sa.Index("ix_bounties_worker", "worker"),
    )

    op.create_table(
        "github_prs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("pr_number", sa.Integer(), nullable=False),
        sa.Column("repo_url", sa.String(), nullable=False),
        sa.Column(
            "bounty_id",
            sa.String(),
            sa.ForeignKey("bounties.bounty_id"),
            nullable=False,
        ),
        sa.Column("state", sa.String(), server_default="open"),
        sa.Column("author", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Index("ix_github_prs_id", "id"),
        sa.Index("ix_github_prs_pr_number", "pr_number"),
        sa.Index("ix_github_prs_repo_url", "repo_url"),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("recipient", sa.String(), nullable=False),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column("read", sa.Boolean(), server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Index("ix_notifications_id", "id"),
        sa.Index("ix_notifications_recipient", "recipient"),
    )


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("github_prs")
    op.drop_table("bounties")
    op.drop_table("agents")
