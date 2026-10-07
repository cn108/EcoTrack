"""Add optional user-entered fuel costs to activities.

Revision ID: 9c3e1a7b5d42
Revises: 4d8a2f6c1b90
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9c3e1a7b5d42"
down_revision: Union[str, Sequence[str], None] = "4d8a2f6c1b90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "activities",
        sa.Column("unit_cost_ngn", sa.Numeric(20, 6), nullable=True),
    )
    op.create_check_constraint(
        "ck_activities_non_negative_unit_cost_ngn",
        "activities",
        "unit_cost_ngn IS NULL OR unit_cost_ngn >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_activities_non_negative_unit_cost_ngn",
        "activities",
        type_="check",
    )
    op.drop_column("activities", "unit_cost_ngn")
