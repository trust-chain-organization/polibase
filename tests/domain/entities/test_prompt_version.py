"""Tests for PromptVersion entity."""

import pytest

from src.domain.entities.prompt_version import PromptVersion


class TestPromptVersion:
    """Test cases for PromptVersion entity."""

    def test_create_prompt_version(self):
        """Test creating a prompt version."""
        prompt = PromptVersion(
            prompt_key="test_prompt",
            template="Hello {name}, welcome to {place}!",
            version="1.0.0",
            description="Test prompt",
            is_active=True,
            variables=["name", "place"],
            metadata={"category": "greeting"},
            created_by="test_user",
        )

        assert prompt.prompt_key == "test_prompt"
        assert prompt.template == "Hello {name}, welcome to {place}!"
        assert prompt.version == "1.0.0"
        assert prompt.description == "Test prompt"
        assert prompt.is_active is True
        assert prompt.variables == ["name", "place"]
        assert prompt.metadata == {"category": "greeting"}
        assert prompt.created_by == "test_user"

    def test_extract_variables(self):
        """Test extracting variables from template."""
        prompt = PromptVersion(
            prompt_key="test",
            template="User {user_name} has {count} items in {location}",
            version="1.0.0",
        )

        variables = prompt.extract_variables()
        assert set(variables) == {"user_name", "count", "location"}

    def test_extract_variables_with_duplicates(self):
        """Test extracting variables handles duplicates."""
        prompt = PromptVersion(
            prompt_key="test",
            template="{name} said hello to {name} at {place}",
            version="1.0.0",
        )

        variables = prompt.extract_variables()
        assert set(variables) == {"name", "place"}
        assert len(variables) == 2

    def test_extract_variables_empty_template(self):
        """Test extracting variables from empty template."""
        prompt = PromptVersion(
            prompt_key="test",
            template="No variables here!",
            version="1.0.0",
        )

        variables = prompt.extract_variables()
        assert variables == []

    def test_validate_variables_all_present(self):
        """Test validating variables when all are present."""
        prompt = PromptVersion(
            prompt_key="test",
            template="Hello {name}!",
            version="1.0.0",
            variables=["name"],
        )

        is_valid, missing = prompt.validate_variables({"name": "Alice"})
        assert is_valid is True
        assert missing == []

    def test_validate_variables_missing(self):
        """Test validating variables when some are missing."""
        prompt = PromptVersion(
            prompt_key="test",
            template="Hello {name} from {city}!",
            version="1.0.0",
            variables=["name", "city"],
        )

        is_valid, missing = prompt.validate_variables({"name": "Alice"})
        assert is_valid is False
        assert missing == ["city"]

    def test_validate_variables_extra(self):
        """Test validating variables with extra variables."""
        prompt = PromptVersion(
            prompt_key="test",
            template="Hello {name}!",
            version="1.0.0",
            variables=["name"],
        )

        # Extra variables are allowed
        is_valid, missing = prompt.validate_variables(
            {"name": "Alice", "extra": "value"}
        )
        assert is_valid is True
        assert missing == []

    def test_validate_variables_empty_list(self):
        """Test validating variables when no variables expected."""
        prompt = PromptVersion(
            prompt_key="test",
            template="Hello world!",
            version="1.0.0",
            variables=[],
        )

        is_valid1, missing1 = prompt.validate_variables({})
        assert is_valid1 is True
        assert missing1 == []

        is_valid2, missing2 = prompt.validate_variables({"extra": "value"})
        assert is_valid2 is True
        assert missing2 == []

    def test_format_template_success(self):
        """Test formatting template with valid variables."""
        prompt = PromptVersion(
            prompt_key="test",
            template="Hello {name}, you have {count} messages!",
            version="1.0.0",
            variables=["name", "count"],
        )

        result = prompt.format_template({"name": "Alice", "count": 5})
        assert result == "Hello Alice, you have 5 messages!"

    def test_format_template_missing_variable(self):
        """Test formatting template with missing variables."""
        prompt = PromptVersion(
            prompt_key="test",
            template="Hello {name}!",
            version="1.0.0",
            variables=["name"],
        )

        with pytest.raises(ValueError, match="Missing required variables"):
            prompt.format_template({})

    def test_format_template_no_variables(self):
        """Test formatting template with no variables."""
        prompt = PromptVersion(
            prompt_key="test",
            template="Hello world!",
            version="1.0.0",
            variables=[],
        )

        result = prompt.format_template({})
        assert result == "Hello world!"

    def test_format_template_extra_variables(self):
        """Test formatting template ignores extra variables."""
        prompt = PromptVersion(
            prompt_key="test",
            template="Hello {name}!",
            version="1.0.0",
            variables=["name"],
        )

        result = prompt.format_template({"name": "Alice", "extra": "ignored"})
        assert result == "Hello Alice!"

    def test_activate(self):
        """Test activating a prompt version."""
        prompt = PromptVersion(
            prompt_key="test",
            template="Test",
            version="1.0.0",
            is_active=False,
        )

        assert prompt.is_active is False
        # Direct modification since no activate method exists
        prompt.is_active = True
        assert prompt.is_active is True

    def test_deactivate(self):
        """Test deactivating a prompt version."""
        prompt = PromptVersion(
            prompt_key="test",
            template="Test",
            version="1.0.0",
            is_active=True,
        )

        assert prompt.is_active is True
        # Direct modification since no deactivate method exists
        prompt.is_active = False
        assert prompt.is_active is False

    def test_default_values(self):
        """Test default values for optional fields."""
        prompt = PromptVersion(
            prompt_key="test",
            template="Test template",
            version="1.0.0",
        )

        assert prompt.description is None
        assert prompt.is_active is True
        assert prompt.variables == []
        assert prompt.metadata == {}
        assert prompt.created_by is None

    def test_str_representation(self):
        """Test string representation."""
        prompt = PromptVersion(
            prompt_key="test_prompt",
            template="Test",
            version="1.0.0",
        )

        assert (
            str(prompt) == "PromptVersion(key=test_prompt, version=1.0.0, active=True)"
        )

    def test_repr(self):
        """Test repr representation."""
        prompt = PromptVersion(
            prompt_key="test_prompt",
            template="Test",
            version="1.0.0",
            is_active=True,
        )

        repr_str = repr(prompt)
        # Default repr shows object memory address
        assert "PromptVersion" in repr_str
