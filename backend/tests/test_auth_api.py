import os
import unittest
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

os.environ.setdefault("DISABLE_SQLALCHEMY_CEXT", "1")

from fastapi.testclient import TestClient
from fastapi import Response
from sqlalchemy import delete, select

from app.api.auth import (
    REFRESH_COOKIE_NAME,
    _clear_refresh_cookie,
    _set_refresh_cookie,
)
from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.auth import hash_refresh_token


class AuthenticationAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.user_ids: list[uuid.UUID] = []
        self.email = f"{uuid.uuid4()}@example.com"
        self.password = "EcoTrack-account-password-7"

    def tearDown(self) -> None:
        with SessionLocal() as session:
            if self.user_ids:
                session.execute(delete(User).where(User.id.in_(self.user_ids)))
                session.commit()
        self.client.close()

    def _register(self, email: str | None = None) -> dict[str, object]:
        response = self.client.post(
            "/auth/register",
            json={
                "email": email or self.email,
                "password": self.password,
                "first_name": "Test",
                "last_name": "Member",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.user_ids.append(uuid.UUID(body["id"]))
        return body

    def _login(self) -> dict[str, object]:
        response = self.client.post(
            "/auth/login", json={"email": self.email, "password": self.password}
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_refresh_cookie_uses_configured_path_for_same_origin_proxy(self) -> None:
        response = Response()
        with patch("app.api.auth.settings.refresh_cookie_path", "/api/backend/auth"):
            _set_refresh_cookie(response, "refresh-token")
            set_cookie = response.headers["set-cookie"].lower()
            self.assertIn("path=/api/backend/auth", set_cookie)

            _clear_refresh_cookie(response)
            cleared_cookie = response.headers.getlist("set-cookie")[-1].lower()
            self.assertIn("path=/api/backend/auth", cleared_cookie)

    def test_registration_hashes_password_and_never_returns_hash(self) -> None:
        body = self._register()
        self.assertEqual(body["email"], self.email.lower())
        self.assertNotIn("password_hash", body)
        with SessionLocal() as session:
            user = session.get(User, uuid.UUID(body["id"]))
            self.assertNotEqual(user.password_hash, self.password)
            self.assertTrue(user.password_hash.startswith("$argon2id$"))

    def test_duplicate_email_is_rejected_case_insensitively(self) -> None:
        self._register()
        duplicate = self.client.post(
            "/auth/register",
            json={
                "email": self.email.upper(),
                "password": self.password,
                "first_name": "Other",
                "last_name": "Member",
            },
        )
        self.assertEqual(duplicate.status_code, 409)

    def test_invalid_email_and_weak_password_are_rejected(self) -> None:
        invalid_email = self.client.post(
            "/auth/register",
            json={
                "email": "not-an-email",
                "password": self.password,
                "first_name": "Test",
                "last_name": "Member",
            },
        )
        self.assertEqual(invalid_email.status_code, 422)

        weak_password = self.client.post(
            "/auth/register",
            json={
                "email": self.email,
                "password": "short",
                "first_name": "Test",
                "last_name": "Member",
            },
        )
        self.assertEqual(weak_password.status_code, 422)

    def test_login_and_current_user(self) -> None:
        registered = self._register()
        response = self.client.post(
            "/auth/login", json={"email": self.email, "password": self.password}
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["user"]["id"], registered["id"])
        self.assertNotIn("password_hash", body["user"])
        self.assertNotIn("refresh_token", body)
        self.assertIn("httponly", response.headers["set-cookie"].lower())
        self.assertIn("path=/auth", response.headers["set-cookie"].lower())
        current = self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {body['access_token']}"},
        )
        self.assertEqual(current.status_code, 200)
        self.assertEqual(current.json()["id"], registered["id"])

    def test_invalid_credentials_and_inactive_account_are_rejected(self) -> None:
        self._register()
        invalid = self.client.post(
            "/auth/login", json={"email": self.email, "password": "wrong-password"}
        )
        self.assertEqual(invalid.status_code, 401)

        user_id = self.user_ids[0]
        with SessionLocal() as session:
            session.get(User, user_id).is_active = False
            session.commit()
        inactive = self.client.post(
            "/auth/login", json={"email": self.email, "password": self.password}
        )
        self.assertEqual(inactive.status_code, 401)
        token = create_access_token(user_id)
        self.assertEqual(
            self.client.get(
                "/auth/me", headers={"Authorization": f"Bearer {token}"}
            ).status_code,
            401,
        )

    def test_missing_invalid_expired_and_header_only_access_are_rejected(self) -> None:
        self._register()
        self.assertEqual(self.client.get("/auth/me").status_code, 401)
        self.assertEqual(
            self.client.get(
                "/activities", headers={"X-Dev-User-Id": str(self.user_ids[0])}
            ).status_code,
            401,
        )
        self.assertEqual(
            self.client.get(
                "/auth/me", headers={"Authorization": "Bearer invalid-token"}
            ).status_code,
            401,
        )
        expired = create_access_token(
            self.user_ids[0], expires_delta=timedelta(seconds=-1)
        )
        self.assertEqual(
            self.client.get(
                "/auth/me", headers={"Authorization": f"Bearer {expired}"}
            ).status_code,
            401,
        )

    def test_refresh_rotation_stores_only_hash_and_rejects_reuse(self) -> None:
        self._register()
        login_body = self._login()
        old_refresh = self.client.cookies.get(REFRESH_COOKIE_NAME)
        self.assertIsNotNone(old_refresh)
        refreshed = self.client.post("/auth/refresh")
        self.assertEqual(refreshed.status_code, 200, refreshed.text)
        new_refresh = self.client.cookies.get(REFRESH_COOKIE_NAME)
        self.assertNotEqual(old_refresh, new_refresh)
        self.assertNotEqual(refreshed.json()["access_token"], login_body["access_token"])

        with SessionLocal() as session:
            old_record = session.scalar(
                select(RefreshToken).where(
                    RefreshToken.token_hash == hash_refresh_token(old_refresh)
                )
            )
            self.assertIsNotNone(old_record.revoked_at)
            self.assertNotEqual(old_record.token_hash, old_refresh)

        replay_client = TestClient(app)
        replay_client.cookies.set(REFRESH_COOKIE_NAME, old_refresh)
        replay = replay_client.post("/auth/refresh")
        self.assertEqual(replay.status_code, 401)
        replay_client.close()

    def test_expired_refresh_token_is_rejected(self) -> None:
        self._register()
        self._login()
        raw_token = self.client.cookies.get(REFRESH_COOKIE_NAME)
        with SessionLocal() as session:
            token = session.scalar(
                select(RefreshToken).where(
                    RefreshToken.token_hash == hash_refresh_token(raw_token)
                )
            )
            token.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            session.commit()
        self.assertEqual(self.client.post("/auth/refresh").status_code, 401)

    def test_logout_revokes_refresh_token_and_clears_cookie(self) -> None:
        self._register()
        self._login()
        raw_token = self.client.cookies.get(REFRESH_COOKIE_NAME)
        response = self.client.post("/auth/logout")
        self.assertEqual(response.status_code, 204)
        with SessionLocal() as session:
            token = session.scalar(
                select(RefreshToken).where(
                    RefreshToken.token_hash == hash_refresh_token(raw_token)
                )
            )
            self.assertIsNotNone(token.revoked_at)
        replay_client = TestClient(app)
        replay_client.cookies.set(REFRESH_COOKIE_NAME, raw_token)
        self.assertEqual(replay_client.post("/auth/refresh").status_code, 401)
        replay_client.close()


if __name__ == "__main__":
    unittest.main()