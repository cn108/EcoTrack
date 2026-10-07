from __future__ import annotations

import unittest
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.goal import Goal
from app.models.user import User


class GoalPersistenceAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.user_id = uuid.uuid4()
        with SessionLocal() as session:
            session.add(
                User(
                    id=self.user_id,
                    email=f"{self.user_id}@example.com",
                    password_hash="test-hash",
                    first_name="Test",
                    last_name="Member",
                )
            )
            session.commit()
        self.client.headers.update(
            {"Authorization": f"Bearer {create_access_token(self.user_id)}"}
        )

    def tearDown(self) -> None:
        with SessionLocal() as session:
            session.execute(delete(User).where(User.id == self.user_id))
            session.commit()
        self.client.close()

    def test_goal_create_update_and_delete_are_persisted(self) -> None:
        created = self.client.post(
            "/goals",
            json={
                "name": "Reduce footprint",
                "target_type": "Reduction goal",
                "baseline_co2e": "100",
                "target_co2e": "50",
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        goal_id = uuid.UUID(created.json()["id"])

        with SessionLocal() as session:
            stored = session.get(Goal, goal_id)
            self.assertIsNotNone(stored)
            self.assertEqual(stored.name, "Reduce footprint")

        updated = self.client.put(
            f"/goals/{goal_id}",
            json={"name": "Updated footprint goal", "target_co2e": "40"},
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        with SessionLocal() as session:
            stored = session.get(Goal, goal_id)
            self.assertEqual(stored.name, "Updated footprint goal")
            self.assertEqual(str(stored.target_co2e), "40.000000")

        deleted = self.client.delete(f"/goals/{goal_id}")
        self.assertEqual(deleted.status_code, 204, deleted.text)
        with SessionLocal() as session:
            self.assertIsNone(session.get(Goal, goal_id))


if __name__ == "__main__":
    unittest.main()
