"""Système B — l'agent conversationnel qui INTERROGE l'ontologie publiée par A.

Frontière A/B (CLAUDE §9) : A construit (json + graphe + carte), B exploite (queries).
B ne construit rien, ne dessine aucune carte, ne reconstruit pas l'ontologie : au démarrage
il recharge `outputs/ontology.agentic.json` via le loader de A (désérialisation pure) et
expose une famille d'OUTILS de requête NetworkX à un agent Claude.

Surface publique :
- `answer(question) -> dict` / `answer_async(question) -> dict` (agent.py) : le contrat UI.
- `get_graph()` (graph_store.py) : le MultiDiGraph chargé (singleton).
- le module `queries` : la couche de calcul pur Python, testable sans LLM.
"""

from __future__ import annotations

__all__ = ["answer", "answer_async", "get_graph", "queries"]


def __getattr__(name):  # import paresseux : exposer answer() sans tirer le SDK à l'import
    if name in {"answer", "answer_async"}:
        from . import agent

        return getattr(agent, name)
    if name == "get_graph":
        from .graph_store import get_graph

        return get_graph
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
# `queries` est un sous-module : `from system_b import queries` se résout nativement.
