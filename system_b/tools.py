"""tools.py — wrappers @tool SDK (LECTURE SEULE) autour de queries.py.

Chaque outil enrobe une fonction de `queries.py` au format SDK (mêmes conventions que
`system_a_agents/tools/readers.py` : `@tool(nom, desc, schema)`, retour via `_ok(payload)`).
Tous les outils sont génériques (voisins, chemins, sous-graphe, impact, scoring, structure)
et n'ont AUCUN effet de bord : B interroge, il n'écrit ni n'exécute rien (CLAUDE §9).

Regroupés dans un serveur MCP en-process `system_b_query` exposé à l'agent.
"""

from __future__ import annotations

import json

from claude_agent_sdk import create_sdk_mcp_server, tool

from . import queries


def _ok(payload) -> dict:
    """Emballe une charge utile au format de retour attendu par le SDK."""
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, indent=2)
    return {"content": [{"type": "text", "text": text}]}


SERVER_NAME = "system_b_query"


@tool(
    "find_nodes",
    "Filtre les nœuds de l'ontologie par type, couche et/ou égalité d'attribut. "
    "Params (tous optionnels) : node_type (str, ex. 'Shipment'), layer (str ∈ "
    "operational|hr|financial), attr_equals (objet, ex. {\"status\":\"Delayed\"}). "
    "Renvoie id+name+type+layer+attributes.",
    {"node_type": str, "layer": str, "attr_equals": dict},
)
async def find_nodes(args) -> dict:
    a = args or {}
    return _ok(
        queries.find_nodes(
            node_type=a.get("node_type") or None,
            layer=a.get("layer") or None,
            attr_equals=a.get("attr_equals") or None,
        )
    )


@tool(
    "get_node",
    "Nœud complet (attributs + provenance : confidence, evidence, sources, open_questions). "
    "Param : node_id (str, ex. 'shipment:sh-2049').",
    {"node_id": str},
)
async def get_node(args) -> dict:
    return _ok(queries.get_node((args or {}).get("node_id", "")))


@tool(
    "get_neighbors",
    "Voisinage direct d'un nœud : pour chaque voisin, l'arête (type, sens, evidence, "
    "confidence) + le nœud voisin. Params : node_id (str), direction (str ∈ in|out|both, "
    "défaut both), rel_type (str optionnel, ex. 'governed_by').",
    {"node_id": str, "direction": str, "rel_type": str},
)
async def get_neighbors(args) -> dict:
    a = args or {}
    return _ok(
        queries.get_neighbors(
            a.get("node_id", ""),
            direction=a.get("direction") or "both",
            rel_type=a.get("rel_type") or None,
        )
    )


@tool(
    "shortest_path",
    "Plus court chemin entre deux nœuds, avec les arêtes traversées et leur evidence "
    "(essaie le sens dirigé, retombe sur le non-dirigé sinon). Params : source_id (str), "
    "target_id (str).",
    {"source_id": str, "target_id": str},
)
async def shortest_path(args) -> dict:
    a = args or {}
    return _ok(queries.shortest_path(a.get("source_id", ""), a.get("target_id", "")))


@tool(
    "get_subgraph",
    "Sous-graphe (nœuds + arêtes + liste node_ids pour le surlignage UI) autour d'un nœud "
    "jusqu'à une profondeur. Params : node_id (str), depth (int, défaut 1).",
    {"node_id": str, "depth": int},
)
async def get_subgraph(args) -> dict:
    a = args or {}
    return _ok(queries.get_subgraph(a.get("node_id", ""), depth=int(a.get("depth", 1) or 1)))


@tool(
    "compute_impact",
    "Calcule l'impact d'un shipment par TRAVERSÉE du graphe : produit & cold-chain, client "
    "(tier, strategic_value, account_manager), contrat (pénalité/h, deadline SLA, escalade), "
    "facture liée (montant, statut), et la pénalité (delay_h × pénalité/h). Renvoie l'evidence "
    "de chaque pièce. Param : shipment_id (str).",
    {"shipment_id": str},
)
async def compute_impact(args) -> dict:
    return _ok(queries.compute_impact((args or {}).get("shipment_id", "")))


@tool(
    "score_delayed_shipments",
    "Récupère TOUS les shipments en retard, calcule leur impact, et les SCORE sur un barème "
    "transparent (cold-chain, tier client, pénalité/h, facture en cours, retard). Renvoie la "
    "liste triée par criticité décroissante avec le détail du score — c'est ce calcul qui "
    "fait émerger le point chaud. Aucun paramètre.",
    {},
)
async def score_delayed_shipments(args) -> dict:
    return _ok(queries.score_delayed_shipments())


@tool(
    "articulation_points",
    "Points d'articulation du graphe (nœuds dont le retrait fragmente la structure) : "
    "hommes-clés, clients/transporteurs critiques. Renvoie type+name+layer. Aucun paramètre.",
    {},
)
async def articulation_points(args) -> dict:
    return _ok(queries.articulation_points())


@tool(
    "centrality",
    "Top-N nœuds par centralité (les plus connectés) : approxime de qui/quoi dépend le plus "
    "la boîte (concentration, hommes-clés). Param : top (int, défaut 10).",
    {"top": int},
)
async def centrality(args) -> dict:
    return _ok(queries.centrality(top=int((args or {}).get("top", 10) or 10)))


ALL_TOOLS = [
    find_nodes,
    get_node,
    get_neighbors,
    shortest_path,
    get_subgraph,
    compute_impact,
    score_delayed_shipments,
    articulation_points,
    centrality,
]

# Noms qualifiés exposés à l'agent (namespace SDK = mcp__<server>__<tool>).
TOOL_NAMES = [f"mcp__{SERVER_NAME}__{t.name}" for t in ALL_TOOLS]


def query_server():
    """Serveur MCP en-process exposant les outils de requête (lecture seule) de B."""
    return create_sdk_mcp_server(SERVER_NAME, "1.0.0", tools=ALL_TOOLS)
