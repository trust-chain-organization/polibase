"""Prompt version entity."""

from typing import Any

from src.domain.entities.base import BaseEntity


class PromptVersion(BaseEntity):
    """Entity to track versions of prompts used in LLM operations."""

    def __init__(
        self,
        prompt_key: str,
        template: str,
        version: str,
        is_active: bool = True,
        description: str | None = None,
        variables: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        created_by: str | None = None,
        id: int | None = None,
    ) -> None:
        """Initialize prompt version.

        Args:
            prompt_key: Unique key identifying the prompt (e.g., "minutes_divide")
            template: The prompt template content
            version: Version identifier (e.g., "1.0.0", "2023-12-01-001")
            is_active: Whether this version is currently active
            description: Human-readable description of the prompt version
            variables: List of variable names expected in the template
            metadata: Additional metadata (e.g., performance metrics, usage notes)
            created_by: User or system that created this version
            id: Entity ID
        """
        super().__init__(id)
        self.prompt_key = prompt_key
        self.template = template
        self.version = version
        self.is_active = is_active
        self.description = description
        self.variables = variables or []
        self.metadata = metadata or {}
        self.created_by = created_by

    @property
    def is_valid_template(self) -> bool:
        """Check if template is valid with all declared variables."""
        if not self.variables:
            return True

        # Check if all declared variables are present in the template
        for var in self.variables:
            if f"{{{var}}}" not in self.template:
                return False
        return True

    def extract_variables(self) -> list[str]:
        """Extract variable names from the template."""
        import re

        # Match {variable_name} pattern
        pattern = r"\{([^}]+)\}"
        matches = re.findall(pattern, self.template)
        return list(set(matches))

    def validate_variables(
        self, provided_variables: dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """Validate that all required variables are provided.

        Args:
            provided_variables: Dictionary of variable names and values

        Returns:
            Tuple of (is_valid, missing_variables)
        """
        required_vars = set(self.extract_variables())
        provided_vars = set(provided_variables.keys())
        missing_vars = list(required_vars - provided_vars)

        return len(missing_vars) == 0, missing_vars

    def format_template(self, variables: dict[str, Any]) -> str:
        """Format the template with provided variables.

        Args:
            variables: Dictionary of variable names and values

        Returns:
            Formatted prompt string

        Raises:
            ValueError: If required variables are missing
        """
        is_valid, missing = self.validate_variables(variables)
        if not is_valid:
            raise ValueError(f"Missing required variables: {missing}")

        return self.template.format(**variables)

    def __str__(self) -> str:
        return (
            f"PromptVersion(key={self.prompt_key}, "
            f"version={self.version}, active={self.is_active})"
        )
