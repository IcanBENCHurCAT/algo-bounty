"""add treasury_altered to bounties

Revision ID: add_treasury_altered
Revises: init
Create Date: 2026-07-12 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "add_treasury_altered"
down_revision: Union[str, None] = "init"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add treasury_altered column to bounties table
    op.add_column(
        "bounties",
        sa.Column(
            "treasury_altered",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        )
    )


def downgrade() -> None:
    # Remove treasury_altered column from bounties table
    op.drop_column("bounties", "treasury_altered")
