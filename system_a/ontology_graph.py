"""Resilient conversion of the published ontology JSON to a NetworkX graph.

The JSON document is the persistence contract between System A and System B.
System B uses the default hybrid policy: valid records are loaded and malformed
records are quarantined. System A and CI can use the strict policy before
publication.

Usage::

    python -m system_a.ontology_graph
    python -m system_a.ontology_graph --strict path/to/ontology.json
"""

from __future__ import annotations

import argparse
import copy
import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ONTOLOGY = ROOT / "outputs" / "ontology.json"
LoadPolicy = Literal["hybrid", "strict"]

ENTITY_ALIASES = {
    "id": ("entity_id",),
    "type": ("entity_type",),
    "name": ("label",),
}
RELATIONSHIP_ALIASES = {
    "source": ("source_id", "from"),
    "target": ("target_id", "to"),
    "type": ("relation_type", "predicate"),
}
TOP_LEVEL_ALIASES = {"entities": ("nodes",), "relationships": ("edges",)}
PROVENANCE_LIST_FIELDS = ("sources", "evidence", "open_questions")


@dataclass(frozen=True)
class ValidationIssue:
    """One normalization, validation, or fatal loading issue."""

    section: str
    index: int | None
    level: Literal["warning", "error", "fatal"]
    reason: str
    identifier: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "section": self.section,
            "index": self.index,
            "level": self.level,
            "reason": self.reason,
            "identifier": self.identifier,
        }


@dataclass
class OntologyValidationReport:
    """Quality report produced while converting an ontology document."""

    entities_received: int = 0
    entities_loaded: int = 0
    entities_normalized: int = 0
    entities_rejected: int = 0
    relationships_received: int = 0
    relationships_loaded: int = 0
    relationships_normalized: int = 0
    relationships_rejected: int = 0
    top_level_normalized: bool = False
    issues: list[ValidationIssue] = field(default_factory=list)
    quarantined_entities: list[dict[str, Any]] = field(default_factory=list)
    quarantined_relationships: list[dict[str, Any]] = field(default_factory=list)

    @property
    def entity_valid_ratio(self) -> float:
        return self.entities_loaded / self.entities_received if self.entities_received else 1.0

    @property
    def relationship_valid_ratio(self) -> float:
        return (
            self.relationships_loaded / self.relationships_received
            if self.relationships_received
            else 1.0
        )

    @property
    def has_fatal_errors(self) -> bool:
        return any(issue.level == "fatal" for issue in self.issues)

    @property
    def is_publishable(self) -> bool:
        return (
            not self.has_fatal_errors
            and self.entity_valid_ratio >= 0.95
            and self.relationship_valid_ratio >= 0.95
        )

    def add_issue(
        self,
        section: str,
        index: int | None,
        level: Literal["warning", "error", "fatal"],
        reason: str,
        identifier: str | None = None,
    ) -> None:
        self.issues.append(ValidationIssue(section, index, level, reason, identifier))

    def summary(self) -> dict[str, Any]:
        """Return a compact JSON-compatible report for graph-level metadata."""
        levels = Counter(issue.level for issue in self.issues)
        return {
            "entities": {
                "received": self.entities_received,
                "loaded": self.entities_loaded,
                "normalized": self.entities_normalized,
                "rejected": self.entities_rejected,
                "valid_ratio": round(self.entity_valid_ratio, 4),
            },
            "relationships": {
                "received": self.relationships_received,
                "loaded": self.relationships_loaded,
                "normalized": self.relationships_normalized,
                "rejected": self.relationships_rejected,
                "valid_ratio": round(self.relationship_valid_ratio, 4),
            },
            "top_level_normalized": self.top_level_normalized,
            "issues": {
                "warning": levels["warning"],
                "error": levels["error"],
                "fatal": levels["fatal"],
            },
            "is_publishable": self.is_publishable,
        }


@dataclass(frozen=True)
class OntologyLoadResult:
    """NetworkX graph plus the complete quality report for its source document."""

    graph: nx.MultiDiGraph
    report: OntologyValidationReport

    @property
    def is_publishable(self) -> bool:
        return self.report.is_publishable


class OntologyGraphError(ValueError):
    """Fatal ontology error, optionally carrying the accumulated quality report."""

    def __init__(self, message: str, report: OntologyValidationReport | None = None):
        super().__init__(message)
        self.report = report


def _validate_policy(policy: str) -> LoadPolicy:
    if policy not in {"hybrid", "strict"}:
        raise ValueError("policy must be 'hybrid' or 'strict'")
    return policy  # type: ignore[return-value]


def _identifier(record: Any, fields: tuple[str, ...]) -> str | None:
    if not isinstance(record, Mapping):
        return None
    for field_name in fields:
        value = record.get(field_name)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _normalize_aliases(
    record: Mapping[str, Any], aliases: Mapping[str, tuple[str, ...]]
) -> tuple[dict[str, Any], bool, list[str]]:
    normalized = copy.deepcopy(dict(record))
    changed = False
    conflicts: list[str] = []

    for canonical, alternatives in aliases.items():
        present = [(name, normalized[name]) for name in (canonical, *alternatives) if name in normalized]
        if not present:
            continue
        first_value = present[0][1]
        if any(value != first_value for _, value in present[1:]):
            conflicts.append(
                f"conflicting values for '{canonical}' across: "
                + ", ".join(name for name, _ in present)
            )
            continue
        if canonical not in normalized:
            normalized[canonical] = first_value
            changed = True
        for alternative in alternatives:
            if alternative in normalized:
                del normalized[alternative]
                changed = True

    return normalized, changed, conflicts


def _extract_sections(
    ontology: Mapping[str, Any], report: OntologyValidationReport
) -> tuple[list[Any], list[Any]]:
    normalized, changed, conflicts = _normalize_aliases(ontology, TOP_LEVEL_ALIASES)
    report.top_level_normalized = changed
    for conflict in conflicts:
        report.add_issue("ontology", None, "fatal", conflict)

    entities = normalized.get("entities")
    relationships = normalized.get("relationships")
    if conflicts or not isinstance(entities, list) or not isinstance(relationships, list):
        report.add_issue(
            "ontology",
            None,
            "fatal",
            "unrecognized structure: expected entity and relationship lists",
        )
        raise OntologyGraphError("unrecognized ontology structure", report)
    if changed:
        report.add_issue("ontology", None, "warning", "normalized top-level aliases")
    return entities, relationships


def _non_empty_string(record: Mapping[str, Any], field_name: str) -> str | None:
    value = record.get(field_name)
    return value if isinstance(value, str) and value.strip() else None


def _quarantine(
    report: OntologyValidationReport,
    section: Literal["entities", "relationships"],
    index: int,
    record: Any,
    reasons: list[str],
    identifier: str | None,
) -> None:
    for reason in reasons:
        report.add_issue(section, index, "error", reason, identifier)
    entry = {"index": index, "identifier": identifier, "reasons": reasons, "record": copy.deepcopy(record)}
    if section == "entities":
        report.entities_rejected += 1
        report.quarantined_entities.append(entry)
    else:
        report.relationships_rejected += 1
        report.quarantined_relationships.append(entry)


def ontology_to_graph(
    ontology: Mapping[str, Any], policy: LoadPolicy = "hybrid"
) -> OntologyLoadResult:
    """Convert an ontology mapping into a resilient directed attributed graph.

    Hybrid mode returns a partial graph and report when individual records are
    invalid. Strict mode raises :class:`OntologyGraphError` if any warning or error
    was observed. Both modes raise for fatal document-level failures.
    """
    selected_policy = _validate_policy(policy)
    report = OntologyValidationReport()
    if not isinstance(ontology, Mapping):
        report.add_issue("ontology", None, "fatal", "ontology must be a JSON object")
        raise OntologyGraphError("ontology must be a JSON object", report)

    entities, relationships = _extract_sections(ontology, report)
    report.entities_received = len(entities)
    report.relationships_received = len(relationships)

    graph = nx.MultiDiGraph(source_format="ontology.json")

    for index, raw_entity in enumerate(entities):
        raw_identifier = _identifier(raw_entity, ("id", "entity_id"))
        if not isinstance(raw_entity, Mapping):
            _quarantine(report, "entities", index, raw_entity, ["entity must be an object"], None)
            continue

        entity, normalized, conflicts = _normalize_aliases(raw_entity, ENTITY_ALIASES)
        if normalized:
            report.add_issue(
                "entities", index, "warning", "normalized entity field aliases", raw_identifier
            )
        entity_id = _non_empty_string(entity, "id")
        entity_type = _non_empty_string(entity, "type")
        reasons = list(conflicts)
        if entity_id is None:
            reasons.append("'id' must be a non-empty string")
        if entity_type is None:
            reasons.append("'type' must be a non-empty string")
        if entity_id is not None and graph.has_node(entity_id):
            reasons.append(f"duplicate entity id '{entity_id}'")
        if reasons:
            _quarantine(report, "entities", index, raw_entity, reasons, entity_id or raw_identifier)
            continue

        assert entity_id is not None
        if _non_empty_string(entity, "name") is None:
            entity["name"] = entity_id
            normalized = True
            report.add_issue("entities", index, "warning", "missing name; used entity id", entity_id)
        if _non_empty_string(entity, "layer") is None:
            entity["layer"] = "unknown"
            normalized = True
            report.add_issue("entities", index, "warning", "missing layer; used 'unknown'", entity_id)

        invalid_lists = [
            field_name
            for field_name in PROVENANCE_LIST_FIELDS
            if field_name in entity and entity[field_name] is not None and not isinstance(entity[field_name], list)
        ]
        if invalid_lists:
            _quarantine(
                report,
                "entities",
                index,
                raw_entity,
                [f"'{field_name}' must be a list when present" for field_name in invalid_lists],
                entity_id,
            )
            continue
        for field_name in PROVENANCE_LIST_FIELDS:
            if entity.get(field_name) is None:
                entity[field_name] = []
                normalized = True
                report.add_issue(
                    "entities", index, "warning", f"missing {field_name}; used empty list", entity_id
                )

        node_attributes = {key: value for key, value in entity.items() if key != "id"}
        graph.add_node(entity_id, **node_attributes)
        report.entities_loaded += 1
        if normalized:
            report.entities_normalized += 1

    if graph.number_of_nodes() == 0:
        report.add_issue("entities", None, "fatal", "ontology contains zero valid entities")
        raise OntologyGraphError("ontology contains zero valid entities", report)

    seen_relationships: set[tuple[str, str, str]] = set()
    for index, raw_relationship in enumerate(relationships):
        raw_identifier = _identifier(raw_relationship, ("type", "relation_type", "predicate"))
        if not isinstance(raw_relationship, Mapping):
            _quarantine(
                report, "relationships", index, raw_relationship, ["relationship must be an object"], None
            )
            continue

        relationship, normalized, conflicts = _normalize_aliases(
            raw_relationship, RELATIONSHIP_ALIASES
        )
        if normalized:
            report.add_issue(
                "relationships",
                index,
                "warning",
                "normalized relationship field aliases",
                raw_identifier,
            )
        source = _non_empty_string(relationship, "source")
        target = _non_empty_string(relationship, "target")
        relationship_type = _non_empty_string(relationship, "type")
        reasons = list(conflicts)
        if source is None:
            reasons.append("'source' must be a non-empty string")
        if target is None:
            reasons.append("'target' must be a non-empty string")
        if relationship_type is None:
            reasons.append("'type' must be a non-empty string")
        missing = [node_id for node_id in (source, target) if node_id is not None and node_id not in graph]
        if missing:
            reasons.append("relationship references missing entity/entities: " + ", ".join(missing))
        identity = (
            (source, target, relationship_type)
            if source is not None and target is not None and relationship_type is not None
            else None
        )
        if identity is not None and identity in seen_relationships:
            reasons.append(
                f"duplicate relationship {source!r} -[{relationship_type}]-> {target!r}"
            )
        if reasons:
            _quarantine(
                report,
                "relationships",
                index,
                raw_relationship,
                reasons,
                relationship_type or raw_identifier,
            )
            continue

        assert source is not None and target is not None and relationship_type is not None
        for field_name in ("evidence", "open_questions"):
            if field_name in relationship and relationship[field_name] is not None and not isinstance(
                relationship[field_name], list
            ):
                reasons.append(f"'{field_name}' must be a list when present")
        if reasons:
            _quarantine(
                report, "relationships", index, raw_relationship, reasons, relationship_type
            )
            continue
        for field_name in ("evidence", "open_questions"):
            if relationship.get(field_name) is None:
                relationship[field_name] = []
                normalized = True
                report.add_issue(
                    "relationships",
                    index,
                    "warning",
                    f"missing {field_name}; used empty list",
                    relationship_type,
                )

        seen_relationships.add(identity)
        edge_attributes = {
            key: value for key, value in relationship.items() if key not in {"source", "target"}
        }
        graph.add_edge(source, target, key=relationship_type, **edge_attributes)
        report.relationships_loaded += 1
        if normalized:
            report.relationships_normalized += 1

    graph.graph.update(
        {
            "entity_count": graph.number_of_nodes(),
            "relationship_count": graph.number_of_edges(),
            "validation": report.summary(),
        }
    )
    result = OntologyLoadResult(graph=graph, report=report)
    if selected_policy == "strict" and report.issues:
        raise OntologyGraphError(
            f"strict ontology validation failed with {len(report.issues)} issue(s)", report
        )
    return result


def load_ontology_graph(
    path: str | Path = DEFAULT_ONTOLOGY, policy: LoadPolicy = "hybrid"
) -> OntologyLoadResult:
    """Load an ontology JSON file and reconstruct its NetworkX graph."""
    selected_policy = _validate_policy(policy)
    ontology_path = Path(path)
    try:
        ontology = json.loads(ontology_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        report = OntologyValidationReport()
        report.add_issue("ontology", None, "fatal", f"ontology file not found: {ontology_path}")
        raise OntologyGraphError(f"ontology file not found: {ontology_path}", report) from exc
    except json.JSONDecodeError as exc:
        report = OntologyValidationReport()
        reason = f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        report.add_issue("ontology", None, "fatal", reason)
        raise OntologyGraphError(f"invalid JSON in {ontology_path}: {reason}", report) from exc
    return ontology_to_graph(ontology, policy=selected_policy)


def main() -> int:
    parser = argparse.ArgumentParser(description="Load ontology.json into a NetworkX MultiDiGraph")
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_ONTOLOGY)
    parser.add_argument("--strict", action="store_true", help="fail on any normalization or rejection")
    args = parser.parse_args()

    try:
        result = load_ontology_graph(args.path, policy="strict" if args.strict else "hybrid")
    except OntologyGraphError as exc:
        print(f"ERROR: {exc}")
        if exc.report is not None:
            print(json.dumps(exc.report.summary(), ensure_ascii=False, indent=2))
        return 2

    print(f"Loaded {args.path}")
    print(
        f"NetworkX graph: {result.graph.number_of_nodes()} nodes, "
        f"{result.graph.number_of_edges()} edges"
    )
    print(json.dumps(result.report.summary(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
