import unittest
from datetime import date

from pydantic import ValidationError

from app.schemas.goals import GoalCreate, GoalUpdate


class GoalDateSchemaTests(unittest.TestCase):
    @staticmethod
    def goal_payload(start_date: str, end_date: str) -> dict[str, object]:
        return {
            "name": "Long-range goal",
            "target_type": "Emissions reduction",
            "baseline_co2e": "100",
            "target_co2e": "50",
            "start_date": start_date,
            "end_date": end_date,
        }

    def test_create_accepts_valid_historical_and_far_future_dates(self) -> None:
        goal = GoalCreate.model_validate(
            self.goal_payload("0001-01-01", "9999-12-31")
        )

        self.assertEqual(goal.start_date, date(1, 1, 1))
        self.assertEqual(goal.end_date, date(9999, 12, 31))

    def test_create_rejects_invalid_dates_and_reversed_ranges(self) -> None:
        for start_date, end_date in (
            ("2026-02-30", "2027-01-01"),
            ("10/05/2026", "2027-01-01"),
            ("2027-01-01", "2026-12-31"),
        ):
            with self.subTest(start_date=start_date, end_date=end_date):
                with self.assertRaises(ValidationError):
                    GoalCreate.model_validate(self.goal_payload(start_date, end_date))

    def test_update_accepts_iso_dates_and_rejects_invalid_or_reversed_ranges(self) -> None:
        self.assertEqual(
            GoalUpdate.model_validate({"start_date": "0001-01-01"}).start_date,
            date(1, 1, 1),
        )
        for payload in (
            {"start_date": "2026-02-30"},
            {"end_date": "10/05/2026"},
            {"start_date": "2027-01-01", "end_date": "2026-12-31"},
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(ValidationError):
                    GoalUpdate.model_validate(payload)


if __name__ == "__main__":
    unittest.main()
