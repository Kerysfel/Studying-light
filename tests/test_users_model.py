"""User model tests."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from studying_light.db.models.user import User


def test_create_user(session: Session) -> None:
    """User can be created with defaults."""
    user = User(
        email="user@example.com",
        password_hash="hashed",
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    assert user.id is not None
    assert user.created_at is not None
    assert user.is_active is False
    assert user.is_admin is False
    assert user.must_change_password is False


def test_user_email_unique(session: Session) -> None:
    """Email must be unique."""
    session.add(User(email="dup@example.com", password_hash="hash1"))
    session.commit()

    session.add(User(email="dup@example.com", password_hash="hash2"))
    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()
