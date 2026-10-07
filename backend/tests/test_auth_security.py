import os
import unittest
from datetime import timedelta
from uuid import uuid4

os.environ.setdefault("DISABLE_SQLALCHEMY_CEXT", "1")

from pydantic import ValidationError

from app.core.config import Settings
from app.core.security import (
    InvalidAccessTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


class PasswordSecurityTests(unittest.TestCase):
    def test_argon2_hash_verifies_without_retaining_plaintext(self) -> None:
        password = "correct-horse-battery-staple-42"
        encoded = hash_password(password)
        self.assertNotIn(password, encoded)
        self.assertTrue(encoded.startswith("$argon2id$"))
        self.assertTrue(verify_password(password, encoded))
        self.assertFalse(verify_password("incorrect-password", encoded))


class AccessTokenTests(unittest.TestCase):
    def test_valid_access_token_returns_subject(self) -> None:
        user_id = uuid4()
        token = create_access_token(user_id)
        self.assertEqual(decode_access_token(token), user_id)

    def test_expired_access_token_is_rejected(self) -> None:
        token = create_access_token(uuid4(), expires_delta=timedelta(seconds=-1))
        with self.assertRaises(InvalidAccessTokenError):
            decode_access_token(token)

    def test_wrong_token_purpose_is_rejected(self) -> None:
        import jwt

        from app.core.config import settings
        from app.core.security import ACCESS_TOKEN_ISSUER

        now = __import__("datetime").datetime.now(__import__("datetime").UTC)
        token = jwt.encode(
            {
                "sub": str(uuid4()),
                "type": "refresh",
                "iss": ACCESS_TOKEN_ISSUER,
                "iat": now,
                "exp": now + timedelta(minutes=5),
                "jti": str(uuid4()),
            },
            settings.signing_key,
            algorithm="HS256",
        )
        with self.assertRaises(InvalidAccessTokenError):
            decode_access_token(token)


class ConfigurationSecurityTests(unittest.TestCase):
    def test_production_requires_a_secret(self) -> None:
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, environment="production", secret_key=None)

    def test_production_rejects_a_weak_secret(self) -> None:
        with self.assertRaises(ValidationError):
            Settings(_env_file=None, environment="production", secret_key="short")


if __name__ == "__main__":
    unittest.main()