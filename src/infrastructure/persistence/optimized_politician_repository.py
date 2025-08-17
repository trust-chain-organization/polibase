"""Optimized politician repository with caching and batch loading."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.domain.entities.politician import Politician
from src.infrastructure.persistence.optimized_repository_mixin import (
    OptimizedRepositoryMixin,
)
from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianRepositoryImpl,
)
from src.models import PoliticianModel


class OptimizedPoliticianRepository(PoliticianRepositoryImpl, OptimizedRepositoryMixin):
    """Optimized politician repository with caching and batch operations."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize with caching support."""
        super().__init__(*args, **kwargs)
        # Cache for frequently accessed politicians
        self._politician_cache: dict[int, Politician] = {}
        self._cache_loaded = False

    async def get_all_cached(self) -> list[Politician]:
        """Get all politicians with caching for LLM matching.

        This method loads all politicians once and caches them for subsequent calls.
        Used in LLM matching scenarios where the same data is accessed repeatedly.
        """
        if not self._cache_loaded and self.async_session:
            # Load all politicians with party relationships
            query = select(PoliticianModel).options(
                selectinload(PoliticianModel.political_party),
                selectinload(PoliticianModel.speaker),
            )
            result = await self.async_session.execute(query)
            models = result.scalars().unique().all()

            # Cache the results
            politicians = []
            for model in models:
                politician = self._to_entity(model)
                if politician.id:
                    self._politician_cache[politician.id] = politician
                politicians.append(politician)

            self._cache_loaded = True
            return politicians
        elif self._cache_loaded:
            return list(self._politician_cache.values())
        else:
            # Fallback to regular get_all
            return await self.get_all()

    async def batch_search_by_names(
        self, names: list[str]
    ) -> dict[str, list[Politician]]:
        """Batch search for politicians by multiple names.

        Args:
            names: List of names to search for

        Returns:
            Dictionary mapping names to matching politicians
        """
        if not names or not self.async_session:
            return {}

        # Normalize names for searching
        normalized_names = [name.replace(" ", "").replace("　", "") for name in names]

        # Build query with ILIKE for all names
        from sqlalchemy import or_

        conditions = []
        for name in normalized_names:
            conditions.append(PoliticianModel.name.ilike(f"%{name}%"))

        query = (
            select(PoliticianModel)
            .where(or_(*conditions))
            .options(
                selectinload(PoliticianModel.political_party),
                selectinload(PoliticianModel.speaker),
            )
        )

        result = await self.async_session.execute(query)
        models = result.scalars().unique().all()

        # Group results by matching names
        results: dict[str, list[Politician]] = {name: [] for name in names}

        for model in models:
            politician = self._to_entity(model)
            # Match back to original names
            for orig_name, norm_name in zip(names, normalized_names, strict=False):
                if norm_name.lower() in politician.name.lower().replace(
                    " ", ""
                ).replace("　", ""):
                    results[orig_name].append(politician)

        return results

    async def get_by_party_with_relations(self, party_id: int) -> list[Politician]:
        """Get politicians by party with all relations loaded.

        Args:
            party_id: Political party ID

        Returns:
            List of politicians with relations loaded
        """
        if not self.async_session:
            return await self.get_by_party(party_id)

        query = (
            select(PoliticianModel)
            .where(PoliticianModel.political_party_id == party_id)
            .options(
                selectinload(PoliticianModel.political_party),
                selectinload(PoliticianModel.speaker),
            )
        )

        result = await self.async_session.execute(query)
        models = result.scalars().unique().all()

        return [self._to_entity(model) for model in models]

    async def invalidate_cache(self) -> None:
        """Invalidate the politician cache.

        Call this when politicians are added or updated.
        """
        self._politician_cache.clear()
        self._cache_loaded = False

    async def warm_cache(self) -> None:
        """Pre-load the cache for better performance."""
        await self.get_all_cached()
