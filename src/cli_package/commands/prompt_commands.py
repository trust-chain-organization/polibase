"""CLI commands for prompt version management"""

import click

from ..base import BaseCommand, with_error_handling


class PromptCommands(BaseCommand):
    """Commands for prompt version management"""

    @staticmethod
    @click.command()
    @click.option(
        "--prompt-key",
        type=str,
        help="プロンプトキー（例：minutes_divide, speaker_match）",
    )
    @click.option(
        "--limit",
        type=int,
        default=10,
        help="表示する最大バージョン数",
    )
    @with_error_handling
    @BaseCommand.async_command
    async def prompt_list(prompt_key: str | None, limit: int):
        """List prompt versions (プロンプトバージョン一覧)

        Examples:
        - polibase prompt-list                    # List all active prompts
        - polibase prompt-list --prompt-key minutes_divide  # List specific prompt
        - polibase prompt-list --limit 20         # Show more versions
        """
        from src.infrastructure.config.async_database import get_async_session
        from src.infrastructure.persistence.prompt_version_repository_impl import (
            PromptVersionRepositoryImpl,
        )

        PromptCommands.show_progress("Fetching prompt versions...")

        async with get_async_session() as session:
            repository = PromptVersionRepositoryImpl(session)

            if prompt_key:
                # Get versions for specific prompt
                versions = await repository.get_versions_by_key(prompt_key, limit)
                if not versions:
                    click.echo(f"⚠ No versions found for prompt: {prompt_key}")
                    return

                # Display versions
                click.echo(f"\nVersions for prompt '{prompt_key}':")
                click.echo("-" * 80)
                for v in versions:
                    active_mark = " [ACTIVE]" if v.is_active else ""
                    click.echo(f"\nVersion: {v.version}{active_mark}")
                    if v.description:
                        desc = (
                            v.description[:50] + "..."
                            if len(v.description) > 50
                            else v.description
                        )
                        click.echo(f"  Description: {desc}")
                    created = (
                        v.created_at.strftime("%Y-%m-%d %H:%M")
                        if v.created_at
                        else "Unknown"
                    )
                    click.echo(f"  Created: {created}")
                    click.echo(f"  Created By: {v.created_by or 'system'}")

            else:
                # Get all active versions
                versions = await repository.get_all_active_versions()
                if not versions:
                    click.echo("⚠ No active prompt versions found")
                    return

                # Display active versions
                click.echo("\nActive prompt versions:")
                click.echo("-" * 80)
                for v in versions:
                    click.echo(f"\n{v.prompt_key} (v{v.version})")
                    if v.variables:
                        click.echo(f"  Variables: {', '.join(v.variables)}")
                    created = (
                        v.created_at.strftime("%Y-%m-%d %H:%M")
                        if v.created_at
                        else "Unknown"
                    )
                    click.echo(f"  Created: {created}")
                    click.echo(f"  Created By: {v.created_by or 'system'}")

        PromptCommands.success(f"Found {len(versions)} prompt version(s)")

    @staticmethod
    @click.command()
    @click.argument("prompt_key", type=str)
    @click.argument("version", type=str)
    @with_error_handling
    @BaseCommand.async_command
    async def prompt_show(prompt_key: str, version: str):
        """Show a specific prompt version (特定バージョンの表示)

        Arguments:
        - PROMPT_KEY: Prompt key (e.g., minutes_divide, speaker_match)
        - VERSION: Version identifier (e.g., 1.0.0, latest for active version)

        Examples:
        - polibase prompt-show minutes_divide latest     # Show active version
        - polibase prompt-show speaker_match 1.0.0       # Show specific version
        """
        from src.infrastructure.config.async_database import get_async_session
        from src.infrastructure.persistence.prompt_version_repository_impl import (
            PromptVersionRepositoryImpl,
        )

        PromptCommands.show_progress(f"Fetching prompt {prompt_key}:{version}...")

        async with get_async_session() as session:
            repository = PromptVersionRepositoryImpl(session)

            if version == "latest":
                prompt = await repository.get_active_version(prompt_key)
                if not prompt:
                    PromptCommands.error(
                        f"No active version found for prompt: {prompt_key}"
                    )
                    return
            else:
                prompt = await repository.get_by_key_and_version(prompt_key, version)
                if not prompt:
                    PromptCommands.error(f"Version not found: {prompt_key}:{version}")
                    return

            # Display prompt details
            click.echo(f"\n{'=' * 60}")
            click.echo(f"Prompt: {prompt.prompt_key}")
            click.echo(f"Version: {prompt.version}")
            click.echo(f"Active: {'Yes' if prompt.is_active else 'No'}")
            created_time = (
                prompt.created_at.strftime("%Y-%m-%d %H:%M")
                if prompt.created_at
                else "Unknown"
            )
            click.echo(f"Created: {created_time}")
            click.echo(f"Created By: {prompt.created_by or 'system'}")

            if prompt.description:
                click.echo("\nDescription:")
                click.echo(prompt.description)

            if prompt.variables:
                click.echo(f"\nVariables: {', '.join(prompt.variables)}")

            if prompt.metadata:
                click.echo("\nMetadata:")
                for key, value in prompt.metadata.items():
                    click.echo(f"  {key}: {value}")

            click.echo(f"\n{'Template:':=^60}")
            click.echo(prompt.template)
            click.echo("=" * 60)

        PromptCommands.success("Prompt displayed successfully")

    @staticmethod
    @click.command()
    @click.argument("prompt_key", type=str)
    @click.argument("version", type=str)
    @with_error_handling
    @BaseCommand.async_command
    async def prompt_activate(prompt_key: str, version: str):
        """Activate a specific prompt version (バージョンの有効化)

        Arguments:
        - PROMPT_KEY: Prompt key (e.g., minutes_divide, speaker_match)
        - VERSION: Version to activate

        Examples:
        - polibase prompt-activate minutes_divide 2.0.0
        - polibase prompt-activate speaker_match 1.5.0
        """
        from src.infrastructure.config.async_database import get_async_session
        from src.infrastructure.persistence.prompt_version_repository_impl import (
            PromptVersionRepositoryImpl,
        )

        PromptCommands.show_progress(f"Activating prompt {prompt_key}:{version}...")

        async with get_async_session() as session:
            repository = PromptVersionRepositoryImpl(session)

            success = await repository.activate_version(prompt_key, version)
            if not success:
                PromptCommands.error(
                    f"Failed to activate version: {prompt_key}:{version}"
                )
                click.echo(
                    "ℹ Version may not exist. "
                    "Use 'prompt-list' to see available versions."
                )
                return

        PromptCommands.success(f"Successfully activated {prompt_key}:{version}")

    @staticmethod
    @click.command()
    @click.option(
        "--created-by",
        type=str,
        default="system",
        help="作成者の識別子",
    )
    @with_error_handling
    @BaseCommand.async_command
    async def prompt_migrate(created_by: str):
        """Migrate existing static prompts to versioned storage (静的プロンプトの移行)

        This command migrates all existing hardcoded prompts to the
        database-backed version management system.

        Examples:
        - polibase prompt-migrate                      # Migrate as 'system'
        - polibase prompt-migrate --created-by admin   # Migrate with custom creator
        """
        from src.infrastructure.config.async_database import get_async_session
        from src.infrastructure.persistence.prompt_version_repository_impl import (
            PromptVersionRepositoryImpl,
        )
        from src.services.versioned_prompt_manager import VersionedPromptManager

        PromptCommands.show_progress("Starting prompt migration...")

        async with get_async_session() as session:
            repository = PromptVersionRepositoryImpl(session)
            manager = VersionedPromptManager(repository=repository)

            # Check if prompts already exist
            existing = await repository.get_all_active_versions()
            if existing:
                click.echo(f"Found {len(existing)} existing prompt versions.")
                msg = "Skip existing and migrate only new prompts?"
                if not click.confirm(msg, default=True):
                    click.echo("ℹ Migration cancelled")
                    return

            # Perform migration
            count = await manager.migrate_existing_prompts(created_by=created_by)

        if count > 0:
            PromptCommands.success(f"Successfully migrated {count} prompts")
        else:
            click.echo("⚠ No prompts were migrated")

    @staticmethod
    @click.command()
    @click.argument("prompt_key", type=str)
    @click.option("--limit", type=int, default=10, help="比較するバージョン数")
    @with_error_handling
    @BaseCommand.async_command
    async def prompt_history(prompt_key: str, limit: int):
        """Show version history for a prompt (バージョン履歴表示)

        Arguments:
        - PROMPT_KEY: Prompt key to show history for

        Examples:
        - polibase prompt-history minutes_divide
        - polibase prompt-history speaker_match --limit 20
        """
        from src.infrastructure.config.async_database import get_async_session
        from src.infrastructure.persistence.prompt_version_repository_impl import (
            PromptVersionRepositoryImpl,
        )

        PromptCommands.show_progress(f"Fetching history for {prompt_key}...")

        async with get_async_session() as session:
            repository = PromptVersionRepositoryImpl(session)
            versions = await repository.get_versions_by_key(prompt_key, limit)

            if not versions:
                click.echo(f"⚠ No versions found for prompt: {prompt_key}")
                return

            click.echo(f"\nVersion history for '{prompt_key}':")
            click.echo("=" * 80)

            for i, version in enumerate(versions, 1):
                status = "ACTIVE" if version.is_active else ""
                click.echo(f"\n{i}. Version {version.version} {status}")
                created_str = (
                    version.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    if version.created_at
                    else "Unknown"
                )
                click.echo(f"   Created: {created_str}")
                click.echo(f"   By: {version.created_by or 'system'}")

                if version.description:
                    click.echo(f"   Description: {version.description}")

                if version.variables:
                    click.echo(f"   Variables: {', '.join(version.variables)}")

                # Show first 3 lines of template
                template_lines = version.template.split("\n")[:3]
                click.echo("   Template preview:")
                for line in template_lines:
                    if line.strip():
                        click.echo(f"     {line[:70]}...")
                        break

            click.echo("=" * 80)
            PromptCommands.success(f"Displayed {len(versions)} version(s)")


def get_prompt_commands():
    """Get all prompt version management commands"""
    return [
        PromptCommands.prompt_list,
        PromptCommands.prompt_show,
        PromptCommands.prompt_activate,
        PromptCommands.prompt_migrate,
        PromptCommands.prompt_history,
    ]
