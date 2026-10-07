import os
import unittest
import uuid

os.environ.setdefault("DISABLE_SQLALCHEMY_CEXT", "1")

from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import configure_mappers

from app.db.session import engine
from app.models import Activity, Category, EmissionFactor, Goal, RefreshToken, User


class DatabaseSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        configure_mappers()
        cls.inspector = inspect(engine)

    def test_tables_and_required_indexes_exist(self) -> None:
        expected_tables = {
            "users",
            "categories",
            "emission_factors",
            "activities",
            "goals",
            "refresh_tokens",
        }
        self.assertTrue(expected_tables.issubset(set(self.inspector.get_table_names())))

        expected_indexes = {
            ("users", "ix_users_email"),
            ("activities", "ix_activities_user_id"),
            ("activities", "ix_activities_activity_date"),
            ("activities", "ix_activities_category_id"),
            ("activities", "ix_activities_emission_factor_id"),
            ("goals", "ix_goals_user_id"),
            ("refresh_tokens", "ix_refresh_tokens_user_id"),
        }
        actual_indexes = {
            (table, index["name"])
            for table in expected_tables
            for index in self.inspector.get_indexes(table)
        }
        self.assertTrue(expected_indexes.issubset(actual_indexes))
        unique_constraints = {
            constraint["name"]
            for constraint in self.inspector.get_unique_constraints("users")
        }
        self.assertIn("uq_users_email", unique_constraints)

    def test_active_factors_have_real_sources_and_are_not_placeholders(self) -> None:
        with engine.connect() as connection:
            categories = set(
                connection.execute(text("SELECT name FROM categories")).scalars()
            )
            factors = connection.execute(
                text(
                    "SELECT source_name, region, factor_value FROM emission_factors "
                    "WHERE is_active IS TRUE"
                )
            ).all()

        self.assertEqual(
            categories,
            {"Transport", "Energy", "Food", "Travel", "Waste", "Purchases"},
        )
        self.assertGreaterEqual(len(factors), 15)
        for source_name, region, _factor_value in factors:
            self.assertNotIn("DEV ONLY", source_name)
            self.assertTrue(region)
        self.assertGreater(len({factor_value for _, _, factor_value in factors}), 3)

    def test_relationships_and_cascade_foreign_keys(self) -> None:
        self.assertEqual(set(inspect(User).relationships.keys()), {
            "activities", "goals", "refresh_tokens"
        })
        self.assertEqual(set(inspect(Activity).relationships.keys()), {
            "user", "category", "emission_factor"
        })
        self.assertIn("activities", inspect(Category).relationships)
        self.assertIn("activities", inspect(EmissionFactor).relationships)
        self.assertIn("user", inspect(Goal).relationships)
        self.assertIn("user", inspect(RefreshToken).relationships)

        for table in ("activities", "goals", "refresh_tokens"):
            user_foreign_key = next(
                foreign_key
                for foreign_key in self.inspector.get_foreign_keys(table)
                if foreign_key["referred_table"] == "users"
            )
            self.assertEqual(user_foreign_key["options"].get("ondelete"), "CASCADE")

    def test_database_cascades_user_deletion(self) -> None:
        user_id = uuid.uuid4()
        with engine.begin() as connection:
            category_id = connection.execute(
                text("SELECT id FROM categories WHERE name = 'Transport'")
            ).scalar_one()
            factor_id = connection.execute(
                text(
                    "SELECT id FROM emission_factors "
                    "WHERE activity_type = 'car_petrol' "
                    "AND factor_unit = 'kg_co2e_per_L' AND is_active IS TRUE"
                )
            ).scalar_one()
            connection.execute(
                text(
                    "INSERT INTO users (id, email, password_hash, first_name, last_name) "
                    "VALUES (:id, :email, :password_hash, :first_name, :last_name)"
                ),
                {
                    "id": user_id,
                    "email": f"{user_id}@test.invalid",
                    "password_hash": "test-only-hash",
                    "first_name": "Test",
                    "last_name": "Account",
                },
            )
            connection.execute(
                text(
                    "INSERT INTO activities "
                    "(user_id, category_id, activity_type, quantity, unit, activity_date, "
                    "emission_factor_id, calculated_co2e) "
                    "VALUES (:user_id, :category_id, 'car_petrol', 1, 'L', "
                    "CURRENT_DATE, :factor_id, 1)"
                ),
                {"user_id": user_id, "category_id": category_id, "factor_id": factor_id},
            )
            connection.execute(
                text(
                    "INSERT INTO goals "
                    "(user_id, name, target_type, baseline_co2e, target_co2e, start_date, end_date) "
                    "VALUES (:user_id, 'Test goal', 'Annual reduction', 10, 5, CURRENT_DATE, CURRENT_DATE)"
                ),
                {"user_id": user_id},
            )
            connection.execute(
                text(
                    "INSERT INTO refresh_tokens (user_id, token_hash, expires_at) "
                    "VALUES (:user_id, 'test-only-hash', CURRENT_TIMESTAMP + INTERVAL '1 day')"
                ),
                {"user_id": user_id},
            )
            connection.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})

            for table in ("activities", "goals", "refresh_tokens"):
                count = connection.execute(
                    text(f"SELECT count(*) FROM {table} WHERE user_id = :user_id"),
                    {"user_id": user_id},
                ).scalar_one()
                self.assertEqual(count, 0)

    def test_non_negative_checks_and_factor_immutability(self) -> None:
        activity_checks = {
            check["name"] for check in self.inspector.get_check_constraints("activities")
        }
        factor_checks = {
            check["name"]
            for check in self.inspector.get_check_constraints("emission_factors")
        }
        self.assertIn("ck_activities_non_negative_quantity", activity_checks)
        self.assertIn("ck_activities_non_negative_calculated_co2e", activity_checks)
        self.assertIn("ck_emission_factors_non_negative_value", factor_checks)

        with engine.connect() as connection:
            factor_id = connection.execute(
                text("SELECT id FROM emission_factors LIMIT 1")
            ).scalar_one()
            with self.assertRaises(DBAPIError):
                connection.execute(
                    text("UPDATE emission_factors SET factor_value = 2 WHERE id = :id"),
                    {"id": factor_id},
                )
            connection.rollback()


if __name__ == "__main__":
    unittest.main()