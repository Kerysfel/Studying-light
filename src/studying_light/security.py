"""Security helpers for password and token handling."""

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from jwt import InvalidTokenError

JWT_SECRET_ENV = "JWT_SECRET"
JWT_ALGORITHM_ENV = "JWT_ALGORITHM"
JWT_ACCESS_TOKEN_EXPIRES_MINUTES_ENV = "JWT_ACCESS_TOKEN_EXPIRES_MINUTES"
DEFAULT_JWT_SECRET = "local-dev-jwt-secret-change-me-32-bytes"
DEFAULT_JWT_ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_EXPIRES_MINUTES = 60

_password_hasher = PasswordHasher()


class TokenValidationError(ValueError):
    """Raised when an access token is invalid."""


def _jwt_secret() -> str:
    return os.getenv(JWT_SECRET_ENV, DEFAULT_JWT_SECRET)


def _jwt_algorithm() -> str:
    return os.getenv(JWT_ALGORITHM_ENV, DEFAULT_JWT_ALGORITHM)


def access_token_ttl_minutes() -> int:
    """Return access token lifetime in minutes."""
    raw_value = (os.getenv(JWT_ACCESS_TOKEN_EXPIRES_MINUTES_ENV) or "").strip()
    if not raw_value:
        return DEFAULT_ACCESS_TOKEN_EXPIRES_MINUTES
    try:
        parsed = int(raw_value)
    except ValueError:
        return DEFAULT_ACCESS_TOKEN_EXPIRES_MINUTES
    if parsed <= 0:
        return DEFAULT_ACCESS_TOKEN_EXPIRES_MINUTES
    return parsed


def hash_password(password: str) -> str:
    """Hash password using Argon2."""
    return _password_hasher.hash(password)


def is_legacy_sha256_hash(password_hash: str) -> bool:
    """Return whether hash is legacy sha256 format."""
    return password_hash.startswith("sha256$")


def _verify_legacy_sha256(password: str, password_hash: str) -> bool:
    try:
        scheme, salt, digest = password_hash.split("$", 2)
    except ValueError:
        return False
    if scheme != "sha256":
        return False
    computed = hashlib.sha256(f"{salt}{password}".encode("utf-8")).hexdigest()
    return hmac.compare_digest(computed, digest)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against stored hash."""
    if is_legacy_sha256_hash(password_hash):
        return _verify_legacy_sha256(password, password_hash)
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def create_access_token(user_id: UUID) -> str:
    """Create a JWT access token for a user id."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=access_token_ttl_minutes()),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=_jwt_algorithm())


def decode_access_token(token: str) -> UUID:
    """Decode JWT access token and return user id."""
    try:
        payload = jwt.decode(
            token,
            _jwt_secret(),
            algorithms=[_jwt_algorithm()],
        )
    except InvalidTokenError as exc:
        raise TokenValidationError("Invalid access token") from exc

    if payload.get("type") != "access":
        raise TokenValidationError("Invalid access token")

    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise TokenValidationError("Invalid access token")

    try:
        return UUID(subject)
    except ValueError as exc:
        raise TokenValidationError("Invalid access token") from exc
