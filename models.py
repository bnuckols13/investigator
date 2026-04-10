"""Unified data models for the investigative toolkit."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SourceEnum(str, Enum):
    aleph = "aleph"
    opensanctions = "opensanctions"
    sec_edgar = "sec_edgar"
    openfec = "openfec"
    usaspending = "usaspending"
    courtlistener = "courtlistener"
    propublica = "propublica"


class EntityType(str, Enum):
    person = "person"
    company = "company"
    organization = "organization"
    vessel = "vessel"
    unknown = "unknown"


class Entity(BaseModel):
    """A person, company, or organization from any source."""

    id: str
    source: SourceEnum
    name: str
    entity_type: EntityType = EntityType.unknown
    aliases: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    properties: dict[str, list[str]] = Field(default_factory=dict)
    source_url: str | None = None
    last_seen: datetime | None = None
    flags: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict, exclude=True)


class EntityMatch(BaseModel):
    """An Entity with a similarity score from cross-source matching."""

    entity: Entity
    score: float = Field(ge=0, le=100)
    match_method: str = "exact"


class Connection(BaseModel):
    """A relationship between two entities."""

    source_entity_id: str
    target_entity_id: str
    relation_type: str  # ownership, directorship, contribution, contract, litigation, employment
    label: str = ""
    weight: float | None = None  # e.g. ownership percentage
    properties: dict[str, Any] = Field(default_factory=dict)
    source: SourceEnum = SourceEnum.aleph


class TimelineEvent(BaseModel):
    """A dated event from any source."""

    date: date
    event_type: str  # filing, sanction, incorporation, contribution, award, case
    description: str
    entity_ids: list[str] = Field(default_factory=list)
    source: SourceEnum = SourceEnum.aleph
    source_url: str | None = None
    amount: float | None = None


class LeadScore(BaseModel):
    """Investigative priority score for an entity."""

    entity_id: str
    entity_name: str
    total_score: float = 0
    components: dict[str, float] = Field(default_factory=dict)
    flags: list[str] = Field(default_factory=list)
    explanation: str = ""


class SearchResult(BaseModel):
    """Aggregated results from a multi-source investigation."""

    query: str
    entities: list[Entity] = Field(default_factory=list)
    resolved_groups: list[list[EntityMatch]] = Field(default_factory=list)
    connections: list[Connection] = Field(default_factory=list)
    events: list[TimelineEvent] = Field(default_factory=list)
    scores: list[LeadScore] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
