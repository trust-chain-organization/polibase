"""Tests for User entity."""

from datetime import datetime
from uuid import uuid4

from src.domain.entities.user import User


def test_user_initialization():
    """Test user initialization with required fields."""
    email = "test@example.com"
    user = User(email=email)

    assert user.email == email
    assert user.name is None
    assert user.picture is None
    assert user.user_id is None
    assert user.created_at is None
    assert user.last_login_at is None


def test_user_initialization_with_all_fields():
    """Test user initialization with all fields."""
    user_id = uuid4()
    email = "test@example.com"
    name = "Test User"
    picture = "https://example.com/picture.jpg"
    created_at = datetime.now()
    last_login_at = datetime.now()

    user = User(
        user_id=user_id,
        email=email,
        name=name,
        picture=picture,
        created_at=created_at,
        last_login_at=last_login_at,
    )

    assert user.user_id == user_id
    assert user.email == email
    assert user.name == name
    assert user.picture == picture
    assert user.created_at == created_at
    assert user.last_login_at == last_login_at


def test_user_equality():
    """Test user equality based on email."""
    user1 = User(email="test@example.com", name="User 1")
    user2 = User(email="test@example.com", name="User 2")
    user3 = User(email="other@example.com", name="User 3")

    assert user1 == user2  # Same email
    assert user1 != user3  # Different email


def test_user_hash():
    """Test user hashing based on email."""
    user1 = User(email="test@example.com")
    user2 = User(email="test@example.com")
    user3 = User(email="other@example.com")

    assert hash(user1) == hash(user2)  # Same email
    assert hash(user1) != hash(user3)  # Different email


def test_user_str_representation():
    """Test user string representation."""
    user = User(email="test@example.com", name="Test User")
    str_repr = str(user)

    assert "test@example.com" in str_repr
    assert "Test User" in str_repr


def test_user_repr_representation():
    """Test user repr representation."""
    user_id = uuid4()
    user = User(
        user_id=user_id,
        email="test@example.com",
        name="Test User",
        picture="https://example.com/picture.jpg",
    )
    repr_str = repr(user)

    assert str(user_id) in repr_str
    assert "test@example.com" in repr_str
    assert "Test User" in repr_str
    assert "https://example.com/picture.jpg" in repr_str
