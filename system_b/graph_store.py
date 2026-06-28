"""graph_store.py — charge l'ontologie publiée par A en un MultiDiGraph (singleton).

Ce module est le SEUL point de contact de B avec l'artefact de A. Il appelle le loader
`system_a.ontology_graph.load_ontology_graph` (désérialisation pure : aucune entity
resolution, aucun organigramme, aucun scoring n'est refait — la frontière §9 est donc
respectée). Le graphe est mis en cache au niveau module : un seul chargement par process.

Chemin configurable par la variable d'env `ONTOLOGY_PATH` (défaut
`outputs/ontology.agentic.json`), ce qui permet de tester B contre l'oracle déterministe
`outputs/ontology.json` sans toucher au code.
"""

from __future__ import annotations

import os
from pathlib import Path

import networkx as nx

from system_a.ontology_graph import load_ontology_graph

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ONTOLOGY = ROOT / "outputs" / "ontology.agentic.json"

_GRAPH: nx.MultiDiGraph | None = None
_LOADED_PATH: Path | None = None


def ontology_path() -> Path:
    """Chemin de l'ontologie à charger (env `ONTOLOGY_PATH` sinon défaut agentique)."""
    env = os.environ.get("ONTOLOGY_PATH")
    return Path(env) if env else DEFAULT_ONTOLOGY


def get_graph(force_reload: bool = False) -> nx.MultiDiGraph:
    """Renvoie le MultiDiGraph de l'ontologie, chargé une seule fois (cache module-level).

    `force_reload=True` recharge depuis le disque (utile pour les tests qui changent
    `ONTOLOGY_PATH`).
    """
    global _GRAPH, _LOADED_PATH
    path = ontology_path()
    if _GRAPH is None or force_reload or _LOADED_PATH != path:
        result = load_ontology_graph(path, policy="hybrid")
        _GRAPH = result.graph
        _LOADED_PATH = path
    return _GRAPH
