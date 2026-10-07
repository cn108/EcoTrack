"""Replace placeholder factors with activity-specific units and sourced values.

Revision ID: 2a1f6d8c4e90
Revises: 8313b7d8ba8a
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2a1f6d8c4e90"
down_revision: Union[str, Sequence[str], None] = "8313b7d8ba8a"
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
    connection = op.get_bind()
    connection.execute(
        emission_factors.update()
        .where(
            emission_factors.c.source_name.like("EcoTrack DEV ONLY%"),
            emission_factors.c.is_active.is_(True),
        )
        .values(is_active=False)
    )

    op.bulk_insert(
        emission_factors,
        [
            {
                "category": "Transport",
                "activity_type": "car_petrol",
                "factor_value": "2.286",
                "factor_unit": "kg_co2e_per_L",
                "co2e_unit": "kg_co2e",
                "source_name": "IPCC 2006 Guidelines, motor gasoline (direct combustion)",
                "source_url": "https://www.ipcc-nggip.iges.or.jp/public/2006gl/vol2.html",
                "source_year": 2006,
                "region": "Fuel combustion default; tailpipe only",
                "is_active": True,
            },
            {
                "category": "Transport",
                "activity_type": "car_diesel",
                "factor_value": "2.642",
                "factor_unit": "kg_co2e_per_L",
                "co2e_unit": "kg_co2e",
                "source_name": "IPCC 2006 Guidelines, gas/diesel oil (direct combustion)",
                "source_url": "https://www.ipcc-nggip.iges.or.jp/public/2006gl/vol2.html",
                "source_year": 2006,
                "region": "Fuel combustion default; tailpipe only",
                "is_active": True,
            },
            {
                "category": "Energy",
                "activity_type": "electricity",
                "factor_value": "0.54413214",
                "factor_unit": "kg_co2e_per_kWh",
                "co2e_unit": "kg_co2e",
                "source_name": "Ember electricity data via Our World in Data (Africa regional proxy)",
                "source_url": "https://ourworldindata.org/grapher/electricity-mix.csv?frequency=annual&metric=carbon_intensity&source=total",
                "source_year": 2024,
                "region": "Africa average proxy; not Nigeria-specific",
                "is_active": True,
            },
            {
                "category": "Food",
                "activity_type": "beef",
                "factor_value": "99.4774",
                "factor_unit": "kg_co2e_per_kg",
                "co2e_unit": "kg_co2e",
                "source_name": "Poore & Nemecek (2018), via Our World in Data (global supply-chain average)",
                "source_url": "https://ourworldindata.org/grapher/food-emissions-supply-chain.csv",
                "source_year": 2018,
                "region": "Global average; beef from beef herd",
                "is_active": True,
            },
            {
                "category": "Food",
                "activity_type": "beef_dairy",
                "factor_value": "33.3014",
                "factor_unit": "kg_co2e_per_kg",
                "co2e_unit": "kg_co2e",
                "source_name": "Poore & Nemecek (2018), via Our World in Data (global supply-chain average)",
                "source_url": "https://ourworldindata.org/grapher/food-emissions-supply-chain.csv",
                "source_year": 2018,
                "region": "Global average; beef from dairy herd",
                "is_active": True,
            },
            {
                "category": "Food",
                "activity_type": "lamb_mutton",
                "factor_value": "39.7223",
                "factor_unit": "kg_co2e_per_kg",
                "co2e_unit": "kg_co2e",
                "source_name": "Poore & Nemecek (2018), via Our World in Data (global supply-chain average)",
                "source_url": "https://ourworldindata.org/grapher/food-emissions-supply-chain.csv",
                "source_year": 2018,
                "region": "Global average",
                "is_active": True,
            },
            {
                "category": "Food",
                "activity_type": "pork",
                "factor_value": "12.3057",
                "factor_unit": "kg_co2e_per_kg",
                "co2e_unit": "kg_co2e",
                "source_name": "Poore & Nemecek (2018), via Our World in Data (global supply-chain average)",
                "source_url": "https://ourworldindata.org/grapher/food-emissions-supply-chain.csv",
                "source_year": 2018,
                "region": "Global average",
                "is_active": True,
            },
            {
                "category": "Food",
                "activity_type": "poultry",
                "factor_value": "9.8658",
                "factor_unit": "kg_co2e_per_kg",
                "co2e_unit": "kg_co2e",
                "source_name": "Poore & Nemecek (2018), via Our World in Data (global supply-chain average)",
                "source_url": "https://ourworldindata.org/grapher/food-emissions-supply-chain.csv",
                "source_year": 2018,
                "region": "Global average",
                "is_active": True,
            },
            {
                "category": "Food",
                "activity_type": "farmed_fish",
                "factor_value": "13.6324",
                "factor_unit": "kg_co2e_per_kg",
                "co2e_unit": "kg_co2e",
                "source_name": "Poore & Nemecek (2018), via Our World in Data (global supply-chain average)",
                "source_url": "https://ourworldindata.org/grapher/food-emissions-supply-chain.csv",
                "source_year": 2018,
                "region": "Global average; farmed fish",
                "is_active": True,
            },
            {
                "category": "Food",
                "activity_type": "milk",
                "factor_value": "3.1517",
                "factor_unit": "kg_co2e_per_kg",
                "co2e_unit": "kg_co2e",
                "source_name": "Poore & Nemecek (2018), via Our World in Data (global supply-chain average)",
                "source_url": "https://ourworldindata.org/grapher/food-emissions-supply-chain.csv",
                "source_year": 2018,
                "region": "Global average",
                "is_active": True,
            },
            {
                "category": "Food",
                "activity_type": "rice",
                "factor_value": "4.4516",
                "factor_unit": "kg_co2e_per_kg",
                "co2e_unit": "kg_co2e",
                "source_name": "Poore & Nemecek (2018), via Our World in Data (global supply-chain average)",
                "source_url": "https://ourworldindata.org/grapher/food-emissions-supply-chain.csv",
                "source_year": 2018,
                "region": "Global average",
                "is_active": True,
            },
            {
                "category": "Food",
                "activity_type": "maize",
                "factor_value": "1.7015",
                "factor_unit": "kg_co2e_per_kg",
                "co2e_unit": "kg_co2e",
                "source_name": "Poore & Nemecek (2018), via Our World in Data (global supply-chain average)",
                "source_url": "https://ourworldindata.org/grapher/food-emissions-supply-chain.csv",
                "source_year": 2018,
                "region": "Global average",
                "is_active": True,
            },
            {
                "category": "Food",
                "activity_type": "cassava",
                "factor_value": "1.3157",
                "factor_unit": "kg_co2e_per_kg",
                "co2e_unit": "kg_co2e",
                "source_name": "Poore & Nemecek (2018), via Our World in Data (global supply-chain average)",
                "source_url": "https://ourworldindata.org/grapher/food-emissions-supply-chain.csv",
                "source_year": 2018,
                "region": "Global average",
                "is_active": True,
            },
            {
                "category": "Food",
                "activity_type": "pulses",
                "factor_value": "1.7864",
                "factor_unit": "kg_co2e_per_kg",
                "co2e_unit": "kg_co2e",
                "source_name": "Poore & Nemecek (2018), via Our World in Data (global supply-chain average)",
                "source_url": "https://ourworldindata.org/grapher/food-emissions-supply-chain.csv",
                "source_year": 2018,
                "region": "Global average; other pulses",
                "is_active": True,
            },
            {
                "category": "Food",
                "activity_type": "tofu",
                "factor_value": "3.1617",
                "factor_unit": "kg_co2e_per_kg",
                "co2e_unit": "kg_co2e",
                "source_name": "Poore & Nemecek (2018), via Our World in Data (global supply-chain average)",
                "source_url": "https://ourworldindata.org/grapher/food-emissions-supply-chain.csv",
                "source_year": 2018,
                "region": "Global average",
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    emission_factors = sa.table(
        "emission_factors",
        sa.column("source_name", sa.String(length=255)),
        sa.column("is_active", sa.Boolean()),
    )
    connection = op.get_bind()
    connection.execute(
        emission_factors.update()
        .where(
            emission_factors.c.source_name.in_(
                [
                    "IPCC 2006 Guidelines, motor gasoline (direct combustion)",
                    "IPCC 2006 Guidelines, gas/diesel oil (direct combustion)",
                    "Ember electricity data via Our World in Data (Africa regional proxy)",
                    "Poore & Nemecek (2018), via Our World in Data (global supply-chain average)",
                ]
            ),
            emission_factors.c.is_active.is_(True),
        )
        .values(is_active=False)
    )
    connection.execute(
        emission_factors.update()
        .where(emission_factors.c.source_name.like("EcoTrack DEV ONLY%"))
        .values(is_active=True)
    )
