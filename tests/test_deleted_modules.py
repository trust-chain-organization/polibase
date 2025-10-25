"""Tests to verify deprecated modules have been deleted.

This test suite ensures that modules deleted as part of the Clean Architecture
migration cannot be imported, preventing accidental reintroduction of deprecated code.

Related to Issue #621 and PR #626.
"""

import pytest


class TestDeletedModules:
    """Test that deprecated modules have been properly deleted."""

    def test_deprecated_cli_cannot_be_imported(self):
        """Verify old src.cli module no longer exists.

        The CLI has been migrated to src.interfaces.cli.cli as part of
        the Clean Architecture migration.
        """
        with pytest.raises(ModuleNotFoundError, match="No module named 'src.cli'"):
            import src.cli  # noqa: F401

    def test_deprecated_party_tools_cannot_be_imported(self):
        """Verify old party_member_extractor tools module no longer exists.

        The tools have been migrated to src.infrastructure.external.langgraph_tools
        as part of the Clean Architecture migration.
        """
        with pytest.raises(
            ModuleNotFoundError,
            match="No module named 'src.party_member_extractor.tools'",
        ):
            from src.party_member_extractor.tools import __init__  # noqa: F401

    def test_deprecated_exceptions_module_cannot_be_imported(self):
        """Verify old src.exceptions module no longer exists.

        Exceptions have been migrated to layer-specific modules:
        - src.domain.exceptions
        - src.application.exceptions
        - src.infrastructure.exceptions
        """
        with pytest.raises(
            ModuleNotFoundError, match="No module named 'src.exceptions'"
        ):
            import src.exceptions  # noqa: F401

    def test_deprecated_test_speaker_matching_service_deleted(self):
        """Verify legacy test file has been deleted.

        tests/test_speaker_matching_service.py contained legacy tests
        for pre-Clean Architecture API and has been removed.
        """
        import os

        test_file = "tests/test_speaker_matching_service.py"
        assert not os.path.exists(test_file), (
            f"Deprecated test file should not exist: {test_file}"
        )


class TestNewModulesExist:
    """Test that new Clean Architecture modules exist and can be imported."""

    def test_new_cli_module_can_be_imported(self):
        """Verify new CLI module at src.interfaces.cli.cli can be imported."""
        from src.interfaces.cli import cli

        assert cli is not None
        assert hasattr(cli, "cli"), "CLI module should have 'cli' function"

    def test_layer_specific_exceptions_can_be_imported(self):
        """Verify layer-specific exception modules can be imported."""
        # Domain layer
        from src.domain.exceptions import PolibaseError

        assert PolibaseError is not None

        # Application layer
        from src.application.exceptions import ConfigurationError, PDFProcessingError

        assert ConfigurationError is not None
        assert PDFProcessingError is not None

        # Infrastructure layer
        from src.infrastructure.exceptions import DatabaseError, LLMError

        assert DatabaseError is not None
        assert LLMError is not None

    def test_exceptions_available_from_src_init(self):
        """Verify exceptions are re-exported from src.__init__ for convenience."""
        # Import from src package (backward compatibility)
        from src import (
            APIKeyError,
            ConfigurationError,
            DatabaseError,
            LLMError,
            PDFProcessingError,
            PolibaseError,
        )

        # Verify they are the correct types
        assert APIKeyError is not None
        assert ConfigurationError is not None
        assert DatabaseError is not None
        assert LLMError is not None
        assert PDFProcessingError is not None
        assert PolibaseError is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
