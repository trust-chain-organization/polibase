"""Persistence layer package."""

from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl
from src.infrastructure.persistence.speaker_repository_impl import (
    SpeakerRepositoryImpl,
)

__all__ = [
    "BaseRepositoryImpl",
    "SpeakerRepositoryImpl",
]
