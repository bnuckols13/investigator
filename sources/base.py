"""Abstract base class for all OSINT data sources."""

from __future__ import annotations

from abc import ABC, abstractmethod

from models import Connection, Entity, SourceEnum, TimelineEvent


class BaseSource(ABC):
    """Interface that every source adapter implements."""

    name: str
    source_enum: SourceEnum

    @abstractmethod
    async def search_entity(
        self, query: str, entity_type: str | None = None, limit: int = 25
    ) -> list[Entity]:
        """Search for entities matching the query string."""
        ...

    @abstractmethod
    async def get_entity(self, entity_id: str) -> Entity | None:
        """Fetch a single entity by its source-specific ID."""
        ...

    async def get_connections(self, entity_id: str) -> list[Connection]:
        """Get relationships for an entity. Override in sources that support it."""
        return []

    async def get_events(self, entity_id: str) -> list[TimelineEvent]:
        """Get timeline events for an entity. Override in sources that support it."""
        return []

    async def health_check(self) -> bool:
        """Check if the source API is reachable."""
        return True
