"""Add Nigeria-relevant household fuel activities.

Revision ID: 4d8a2f6c1b90
Revises: 2a1f6d8c4e90
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4d8a2f6c1b90"
down_revision: Union[str, Sequence[str], None] = "2a1f6d8c4e90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    emission_factors = sa.table(
        "emission_factors",
        sa.column("category", sa.String(length=100)),
        sa.column("activity_type", sa.String(length=100)),
        sa.column("factor_value", sa.Numeric(precision=20, scale=10)),
        sa.column("factor_unit", sa.String(length=100)),
        sa.column("co2e_unit", sa.String(length=32)),
        sa.column("source_name", sa.String(length=255)),
        sa.column("source_url", sa.String(length=2048)),
        sa.column("source_year", sa.Integer()),
        sa.column("region", sa.String(length=100)),
        sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(
        emission_factors,
        [
            {
                "category": "Energy",
                "activity_type": "generator_petrol",
                "factor_value": "2.286",
                "factor_unit": "kg_co2e_per_L",
                "co2e_unit": "kg_co2e",
                "source_name": "IPCC 2006 Guidelines, motor gasoline (direct combustion)",
                "source_url": "https://www.ipcc-nggip.iges.or.jp/public/2006gl/vol2.html",
                "source_year": 2006,
                "region": "Nigeria household activity; global fuel default; direct combustion only",
                "is_active": True,
            },
            {
                "category": "Energy",
                "activity_type": "generator_diesel",
                "factor_value": "2.642",
                "factor_unit": "kg_co2e_per_L",
                "co2e_unit": "kg_co2e",
                "source_name": "IPCC 2006 Guidelines, gas/diesel oil (direct combustion)",
                "source_url": "https://www.ipcc-nggip.iges.or.jp/public/2006gl/vol2.html",
                "source_year": 2006,
                "region": "Nigeria household activity; global fuel default; direct combustion only",
                "is_active": True,
            },
            {
                "category": "Energy",
                "activity_type": "cooking_lpg",
                "factor_value": "2.9846",
                "factor_unit": "kg_co2e_per_kg",
                "co2e_unit": "kg_co2e",
                "source_name": "IPCC 2006 Guidelines, LPG default factor converted by net calorific value",
                "source_url": "https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_2_Ch2_Stationary_Combustion.pdf",
                "source_year": 2006,
                "region": "Nigeria household activity; global fuel default; direct combustion only",
                "is_active": True,
            },
            {
                "category": "Energy",
                "activity_type": "cooking_kerosene",
                "factor_value": "2.519",
                "factor_unit": "kg_co2e_per_L",
                "co2e_unit": "kg_co2e",
                "source_name": "IPCC 2006 Guidelines, kerosene default factor converted by net calorific value",
                "source_url": "https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_2_Ch2_Stationary_Combustion.pdf",
                "source_year": 2006,
                "region": "Nigeria household activity; global fuel default; direct combustion only",
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    emission_factors = sa.table(
        "emission_factors",
        sa.column("source_name", sa.String(length=255)),
        sa.column("activity_type", sa.String(length=100)),
        sa.column("is_active", sa.Boolean()),
    )
    op.get_bind().execute(
        emission_factors.update()
        .where(
            emission_factors.c.activity_type.in_(
                (
                    "generator_petrol",
                    "generator_diesel",
                    "cooking_lpg",
                    "cooking_kerosene",
                )
            ),
            emission_factors.c.is_active.is_(True),
        )
        .values(is_active=False)
    )
