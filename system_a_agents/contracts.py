"""contracts.py — schémas Pydantic d'I/O de chaque passe.

Le superviseur VALIDE la sortie d'une passe contre son contrat AVANT de l'écrire
au Blackboard (CLAUDE §3 : propose → valide → critic → publie). En cas d'échec de
validation, le superviseur rejoue la passe une fois avec le message d'erreur, puis
s'arrête proprement.

Ces contrats matérialisent le format §4 (entités/relations avec provenance :
sources + confidence + evidence + open_questions).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

LAYERS = ("operational", "hr", "financial")


# --------------------------------------------------------------------------- #
# P1 — Source Profiler
# --------------------------------------------------------------------------- #
class SourceProfile(BaseModel):
    source: str
    likely_entities: list[str] = Field(default_factory=list)
    key_fields: list[str] = Field(default_factory=list)
    quality_notes: str = ""


class ProfilerOutput(BaseModel):
    profiles: list[SourceProfile]


# --------------------------------------------------------------------------- #
# P2 / P5 — Entités (format §4)
# --------------------------------------------------------------------------- #
class EntityProposal(BaseModel):
    id: str
    type: str
    name: str
    layer: Literal["operational", "hr", "financial"]
    attributes: dict[str, Any] = Field(default_factory=dict)
    sources: list[str] = Field(default_factory=list)
    confidence: float
    evidence: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)

    @field_validator("confidence")
    @classmethod
    def _conf_range(cls, v: float) -> float:
        if not (0.0 < v <= 1.0):
            raise ValueError(f"confidence hors ]0,1] : {v}")
        return v


class EntitiesOutput(BaseModel):
    entities: list[EntityProposal]


# --------------------------------------------------------------------------- #
# P3 — Relations (format §4)
# --------------------------------------------------------------------------- #
class RelationshipProposal(BaseModel):
    source: str
    target: str
    type: str
    confidence: float
    evidence: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("confidence")
    @classmethod
    def _conf_range(cls, v: float) -> float:
        if not (0.0 < v <= 1.0):
            raise ValueError(f"confidence hors ]0,1] : {v}")
        return v


class RelationshipsOutput(BaseModel):
    relationships: list[RelationshipProposal]


# --------------------------------------------------------------------------- #
# P4 — Attribut / finances : patches d'attributs par id d'entité
# --------------------------------------------------------------------------- #
class AttributePatch(BaseModel):
    id: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    layer: Literal["operational", "hr", "financial"] | None = None


class AttributesOutput(BaseModel):
    patches: list[AttributePatch] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# P5 — Ontologie assemblée
# --------------------------------------------------------------------------- #
class OntologyDraft(BaseModel):
    entities: list[EntityProposal]
    relationships: list[RelationshipProposal]


# --------------------------------------------------------------------------- #
# P6 — Critic
# --------------------------------------------------------------------------- #
class CriticFinding(BaseModel):
    severity: Literal["blocker", "major", "minor"]
    kind: str
    detail: str
    target_ids: list[str] = Field(default_factory=list)


class ArchitectOutput(BaseModel):
    """P5 — actions correctives de cohérence (pas de re-sérialisation du graphe)."""
    notes: str = ""
    actions: list[dict[str, Any]] = Field(default_factory=list)


class CriticReview(BaseModel):
    """P6 — constats + actions correctives."""
    findings: list[CriticFinding] = Field(default_factory=list)
    actions: list[dict[str, Any]] = Field(default_factory=list)
