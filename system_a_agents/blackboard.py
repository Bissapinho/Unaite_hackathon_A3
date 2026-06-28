"""blackboard.py — état partagé typé du pipeline agentique (Système A, étage 2).

Le Blackboard est la mémoire de travail du superviseur : chaque passe lit les
sections produites par les passes précédentes et écrit la sienne. Il est
sérialisable (dump_json / load_json) pour pouvoir rejouer une passe isolée
(`--passes p3`) sans relancer tout le pipeline.

Garde-fou (CLAUDE §9) : aucune section ne contient jamais de donnée tirée de
`canonical.py`, du manifest de scénario, ni de l'oracle `ontology.json`. Le
Blackboard ne porte que ce que les passes ont reconstruit depuis les sources
publiées (MCP + fichiers bruts).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, PrivateAttr


class JournalEvent(BaseModel):
    pass_id: str
    event: str
    detail: str = ""


class Blackboard(BaseModel):
    """Mémoire de travail partagée entre passes."""

    # P0 — inventaire déterministe (schémas / échantillons / comptes)
    raw: dict[str, Any] = Field(default_factory=dict)
    # P1 — profils de sources (Haiku)
    profiles: list[dict[str, Any]] = Field(default_factory=list)
    # P2 — entités proposées (format §4)
    entities_proposed: list[dict[str, Any]] = Field(default_factory=list)
    # P3 — relations proposées (format §4)
    relationships_proposed: list[dict[str, Any]] = Field(default_factory=list)
    # P4 — enrichissement attributs / finances (patches d'entités)
    attributes: dict[str, Any] = Field(default_factory=dict)
    # P5 — proposition assemblée au format §4 ({entities, relationships})
    ontology_draft: dict[str, Any] = Field(default_factory=dict)
    # P6 — constats du critic + corrections appliquées
    critic_findings: dict[str, Any] = Field(default_factory=dict)
    # P7 — résultat de validation déterministe
    validation: dict[str, Any] = Field(default_factory=dict)
    # Reprise : chunks (sous-requêtes) déjà aboutis par passe — permet à un run interrompu
    # (budget atteint) de NE PAS re-payer les chunks réussis quand on relance (cf. P2/P3).
    chunk_progress: dict[str, list[str]] = Field(default_factory=dict)
    # journal lisible des événements
    journal: list[JournalEvent] = Field(default_factory=list)

    # Chemin d'auto-sauvegarde (non sérialisé) : `checkpoint()` y persiste l'état après
    # chaque chunk, pour qu'une interruption garde le travail déjà fait.
    _autosave_path: Path | None = PrivateAttr(default=None)

    def set_autosave(self, path: str | Path | None) -> None:
        self._autosave_path = Path(path) if path is not None else None

    def checkpoint(self) -> None:
        """Persiste l'état courant si une cible d'auto-sauvegarde est configurée."""
        if self._autosave_path is not None:
            self.dump_json(self._autosave_path)

    def chunk_done(self, pass_id: str, label: str) -> bool:
        return label in self.chunk_progress.get(pass_id, [])

    def mark_chunk_done(self, pass_id: str, label: str) -> None:
        done = self.chunk_progress.setdefault(pass_id, [])
        if label not in done:
            done.append(label)

    def log(self, pass_id: str, event: str, detail: str = "") -> None:
        self.journal.append(JournalEvent(pass_id=pass_id, event=event, detail=detail))

    def dump_json(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(self.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load_json(cls, path: str | Path) -> "Blackboard":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(data)
