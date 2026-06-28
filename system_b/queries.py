"""queries.py — la couche d'outils de requête de B. PUR PYTHON, AUCUN LLM.

Fonctions GÉNÉRIQUES sur le MultiDiGraph publié par A (voisins, chemins, sous-graphe,
impact, scoring, centralité). Chacune renvoie des structures sérialisables (dicts/listes),
jamais des objets NetworkX, et expose `evidence` / `sources` / `confidence` pour que l'agent
puisse CITER ses preuves.

Garde-fous (CLAUDE §9, prompt étape B) :
- B fait un VRAI calcul : `score_delayed_shipments` SCORE les candidats et fait émerger le
  point chaud par les chiffres. Aucun champ `is_hot` n'est lu — il n'existe pas dans le
  graphe (vérifié : SH-2049 a les mêmes types de relations que les autres shipments).
- Ces fonctions CALCULENT et renvoient des faits + scores transparents ; elles ne formulent
  aucune réponse en langage naturel (c'est le rôle de l'agent).

Le graphe est un `nx.MultiDiGraph` DIRIGÉ : plusieurs arêtes possibles entre deux nœuds, le
sens porte du sens. Les arêtes sont indexées par leur `type` de relation (clé du multigraphe).
"""

from __future__ import annotations

from typing import Any

import networkx as nx

from .graph_store import get_graph

# Provenance portée par chaque nœud/arête — toujours renvoyée pour la citation.
_PROVENANCE = ("confidence", "evidence", "sources", "open_questions")


# --------------------------------------------------------------------------- #
# Sérialisation — nœuds & arêtes -> dicts citables
# --------------------------------------------------------------------------- #
def _node_payload(graph: nx.MultiDiGraph, node_id: str, *, full: bool = True) -> dict[str, Any]:
    """Représentation sérialisable d'un nœud (id + name + type + layer + provenance)."""
    data = graph.nodes[node_id]
    payload: dict[str, Any] = {
        "id": node_id,
        "name": data.get("name", node_id),
        "type": data.get("type"),
        "layer": data.get("layer"),
        "attributes": data.get("attributes", {}),
    }
    if full:
        for field in _PROVENANCE:
            payload[field] = data.get(field, [] if field != "confidence" else None)
    return payload


def _edge_payload(source: str, target: str, rel_type: str, data: dict[str, Any]) -> dict[str, Any]:
    """Représentation sérialisable d'une arête (type + sens + provenance)."""
    return {
        "type": rel_type,
        "source": source,
        "target": target,
        "confidence": data.get("confidence"),
        "evidence": data.get("evidence", []),
        "sources": data.get("sources", []),
        "open_questions": data.get("open_questions", []),
    }


# --------------------------------------------------------------------------- #
# Traversée bas niveau (réutilisée par compute_impact / score)
# --------------------------------------------------------------------------- #
def _out(graph: nx.MultiDiGraph, node_id: str, rel_type: str | None = None) -> list[tuple[str, str, dict]]:
    """Arêtes sortantes (node -> voisin). Renvoie (voisin, type, data)."""
    if node_id not in graph:
        return []
    return [
        (v, k, d)
        for _, v, k, d in graph.out_edges(node_id, keys=True, data=True)
        if rel_type is None or k == rel_type
    ]


def _in(graph: nx.MultiDiGraph, node_id: str, rel_type: str | None = None) -> list[tuple[str, str, dict]]:
    """Arêtes entrantes (voisin -> node). Renvoie (voisin, type, data)."""
    if node_id not in graph:
        return []
    return [
        (u, k, d)
        for u, _, k, d in graph.in_edges(node_id, keys=True, data=True)
        if rel_type is None or k == rel_type
    ]


def _first_in(graph: nx.MultiDiGraph, node_id: str, rel_type: str) -> str | None:
    """Premier voisin source d'une arête entrante de type donné (ou None)."""
    hits = _in(graph, node_id, rel_type)
    return hits[0][0] if hits else None


def _first_out(graph: nx.MultiDiGraph, node_id: str, rel_type: str) -> str | None:
    """Premier voisin cible d'une arête sortante de type donné (ou None)."""
    hits = _out(graph, node_id, rel_type)
    return hits[0][0] if hits else None


# --------------------------------------------------------------------------- #
# Outils génériques
# --------------------------------------------------------------------------- #
def find_nodes(
    node_type: str | None = None,
    layer: str | None = None,
    attr_equals: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Filtre les nœuds par `type`, `layer` et/ou égalité d'attribut.

    Ex. `find_nodes("Shipment", attr_equals={"status": "Delayed"})`. Le filtre d'attribut
    est appliqué sur `node["attributes"]`. Renvoie une vue compacte (sans provenance lourde)
    pour rester digeste ; utiliser `get_node` pour le détail complet d'un nœud.
    """
    graph = get_graph()
    out: list[dict[str, Any]] = []
    for node_id, data in graph.nodes(data=True):
        if node_type is not None and data.get("type") != node_type:
            continue
        if layer is not None and data.get("layer") != layer:
            continue
        if attr_equals:
            attrs = data.get("attributes", {})
            if any(attrs.get(key) != value for key, value in attr_equals.items()):
                continue
        out.append(_node_payload(graph, node_id, full=False))
    return out


def get_node(node_id: str) -> dict[str, Any]:
    """Nœud complet : attributs + provenance (confidence, evidence, sources, open_questions)."""
    graph = get_graph()
    if node_id not in graph:
        return {"error": "node not found", "node_id": node_id}
    return _node_payload(graph, node_id, full=True)


def get_neighbors(
    node_id: str,
    direction: str = "both",
    rel_type: str | None = None,
) -> list[dict[str, Any]]:
    """Voisinage direct d'un nœud.

    `direction` ∈ `in|out|both`. Filtre optionnel par `rel_type`. Pour chaque voisin :
    l'arête (type, sens, evidence, confidence) + le nœud voisin (vue compacte).
    """
    graph = get_graph()
    if node_id not in graph:
        return [{"error": "node not found", "node_id": node_id}]
    out: list[dict[str, Any]] = []
    if direction in ("out", "both"):
        for neighbor, rtype, data in _out(graph, node_id, rel_type):
            out.append(
                {
                    "edge": _edge_payload(node_id, neighbor, rtype, data),
                    "neighbor": _node_payload(graph, neighbor, full=False),
                }
            )
    if direction in ("in", "both"):
        for neighbor, rtype, data in _in(graph, node_id, rel_type):
            out.append(
                {
                    "edge": _edge_payload(neighbor, node_id, rtype, data),
                    "neighbor": _node_payload(graph, neighbor, full=False),
                }
            )
    return out


def shortest_path(source_id: str, target_id: str) -> dict[str, Any]:
    """Plus court chemin source -> target, avec les arêtes traversées et leur evidence.

    Sur ce graphe DIRIGÉ : on essaie d'abord le sens dirigé ; si aucun chemin, on retombe
    sur la version non dirigée (en le signalant via `directed=false`).
    """
    graph = get_graph()
    if source_id not in graph or target_id not in graph:
        return {"error": "node not found", "source": source_id, "target": target_id, "path": []}

    directed = True
    try:
        node_path = nx.shortest_path(graph, source_id, target_id)
    except nx.NetworkXNoPath:
        node_path = None
    except nx.NodeNotFound:
        node_path = None

    if node_path is None:
        undirected = graph.to_undirected(as_view=True)
        try:
            node_path = nx.shortest_path(undirected, source_id, target_id)
            directed = False
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return {
                "error": "no path",
                "source": source_id,
                "target": target_id,
                "path": [],
            }

    nodes = [_node_payload(graph, n, full=False) for n in node_path]
    edges: list[dict[str, Any]] = []
    for a, b in zip(node_path, node_path[1:]):
        edges.append(_edge_between(graph, a, b))
    return {
        "source": source_id,
        "target": target_id,
        "directed": directed,
        "length": len(node_path) - 1,
        "nodes": nodes,
        "edges": edges,
    }


def _edge_between(graph: nx.MultiDiGraph, a: str, b: str) -> dict[str, Any]:
    """Une arête entre a et b dans l'un ou l'autre sens (pour reconstituer un chemin)."""
    if graph.has_edge(a, b):
        rtype, data = next(iter(graph.get_edge_data(a, b).items()))
        return _edge_payload(a, b, rtype, data)
    if graph.has_edge(b, a):
        rtype, data = next(iter(graph.get_edge_data(b, a).items()))
        return _edge_payload(b, a, rtype, data)
    return {"type": "?", "source": a, "target": b, "evidence": [], "sources": []}


def get_subgraph(node_id: str, depth: int = 1) -> dict[str, Any]:
    """Sous-graphe (nœuds + arêtes) autour d'un nœud jusqu'à `depth` (sens ignoré).

    Renvoie aussi `node_ids` à plat — c'est ce que l'UI utilise pour surligner le voisinage
    sur la carte (vis.js focus/selectNodes).
    """
    graph = get_graph()
    if node_id not in graph:
        return {"error": "node not found", "node_id": node_id, "node_ids": []}
    undirected = graph.to_undirected(as_view=True)
    within = nx.ego_graph(undirected, node_id, radius=max(0, depth))
    node_ids = list(within.nodes())
    nodes = [_node_payload(graph, n, full=False) for n in node_ids]
    edges: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for n in node_ids:
        for v, rtype, data in _out(graph, n):
            if v in within and (n, v, rtype) not in seen:
                edges.append(_edge_payload(n, v, rtype, data))
                seen.add((n, v, rtype))
    return {"center": node_id, "depth": depth, "node_ids": node_ids, "nodes": nodes, "edges": edges}


# --------------------------------------------------------------------------- #
# compute_impact — le calcul clé de la question phare
# --------------------------------------------------------------------------- #
def compute_impact(shipment_id: str) -> dict[str, Any]:
    """Assemble l'impact d'un shipment par TRAVERSÉE du graphe (aucune arête directe supposée).

    Chaîne réelle de l'ontologie :
      shipment <-[fulfilled_by]- order <-[creates]- po <-[places]- customer
      customer -[governed_by]-> contract
      order   <-[bills]- invoice
      shipment -[contains]-> product
    La cold-chain est lue sur le shipment lui-même (`temperature_controlled`).

    Pénalité : si `delay_hours` connu -> `delay_hours * late_penalty_per_hour` (nombre) ;
    sinon une FORMULE texte `"<penalty>/h × heures de retard"`. Chaque pièce porte son
    evidence pour la citation.
    """
    graph = get_graph()
    if shipment_id not in graph:
        return {"error": "node not found", "shipment_id": shipment_id}

    ship = graph.nodes[shipment_id]
    sattrs = ship.get("attributes", {})
    result: dict[str, Any] = {
        "shipment": _node_payload(graph, shipment_id, full=True),
        "cold_chain": {
            "temperature_controlled": sattrs.get("temperature_controlled"),
            "temperature_min": sattrs.get("temperature_min"),
            "temperature_max": sattrs.get("temperature_max"),
            "battery_autonomy_h": sattrs.get("battery_autonomy_h"),
        },
        "delay_hours": sattrs.get("delay_hours"),
        "product": None,
        "order": None,
        "customer": None,
        "contract": None,
        "invoice": None,
        "penalty": None,
        "evidence": list(ship.get("evidence", [])),
    }

    # produit transporté
    product_id = _first_out(graph, shipment_id, "contains")
    if product_id:
        result["product"] = _node_payload(graph, product_id, full=True)

    # remontée order -> po -> customer
    order_id = _first_in(graph, shipment_id, "fulfilled_by")
    customer_id = None
    if order_id:
        result["order"] = _node_payload(graph, order_id, full=False)
        po_id = _first_in(graph, order_id, "creates")
        if po_id:
            customer_id = _first_in(graph, po_id, "places")
        # facture liée à l'order
        invoice_id = _first_in(graph, order_id, "bills")
        if invoice_id:
            inv = graph.nodes[invoice_id]
            result["invoice"] = {
                **_node_payload(graph, invoice_id, full=True),
                "amount": inv.get("attributes", {}).get("amount"),
                "status": inv.get("attributes", {}).get("status"),
            }

    if customer_id:
        cust = graph.nodes[customer_id]
        cattrs = cust.get("attributes", {})
        result["customer"] = {
            **_node_payload(graph, customer_id, full=True),
            "priority_tier": cattrs.get("priority_tier"),
            "strategic_value": cattrs.get("strategic_value"),
            "account_manager": cattrs.get("account_manager"),
        }
        # contrat du client
        contract_id = _first_out(graph, customer_id, "governed_by")
        if contract_id:
            con = graph.nodes[contract_id]
            conattrs = con.get("attributes", {})
            result["contract"] = {
                **_node_payload(graph, contract_id, full=True),
                "late_penalty_per_hour": conattrs.get("late_penalty_per_hour"),
                "sla_deadline": conattrs.get("sla_deadline"),
                "escalation_to_account_manager": conattrs.get("escalation_to_account_manager"),
            }

    # pénalité
    penalty_per_h = None
    if result["contract"]:
        penalty_per_h = result["contract"].get("late_penalty_per_hour")
    delay = result["delay_hours"]
    if penalty_per_h is not None and isinstance(delay, (int, float)):
        result["penalty"] = {
            "amount": delay * penalty_per_h,
            "formula": f"{delay} h × {penalty_per_h} €/h",
            "delay_hours": delay,
            "penalty_per_hour": penalty_per_h,
        }
    elif penalty_per_h is not None:
        result["penalty"] = {
            "amount": None,
            "formula": f"{penalty_per_h} €/h × heures de retard",
            "delay_hours": None,
            "penalty_per_hour": penalty_per_h,
        }
    return result


# --------------------------------------------------------------------------- #
# score_delayed_shipments — la désignation du point chaud, PAR LES CHIFFRES
# --------------------------------------------------------------------------- #
# Tiers client (échelle ordinale) : Platinum > Gold > Silver > Bronze > (inconnu).
_TIER_RANK = {"Platinum": 4, "Gold": 3, "Silver": 2, "Bronze": 1}


def _score_components(impact: dict[str, Any]) -> dict[str, Any]:
    """Composantes de criticité TRANSPARENTES d'un shipment (toutes normalisées 0..1).

    Score = somme pondérée de cinq signaux, indépendants et explicables :
      - cold_chain   (poids 25) : transport sous température contrôlée (bool) ;
      - client_tier  (poids 20) : rang du tier client (Platinum=1.0 … Bronze=0.25) ;
      - penalty      (poids 25) : pénalité/h du contrat, normalisée sur 10 000 €/h ;
      - invoice      (poids 15) : montant de la facture EN COURS (Pending), /200 000 € ;
      - delay        (poids 15) : retard mesuré en heures, normalisé sur 12 h.
    Aucun de ces signaux n'est un drapeau : ils sont tous lus/calculés depuis le graphe.
    """
    cold = 1.0 if impact.get("cold_chain", {}).get("temperature_controlled") else 0.0

    tier = (impact.get("customer") or {}).get("priority_tier")
    tier_score = _TIER_RANK.get(tier, 0) / 4.0

    penalty_per_h = (impact.get("contract") or {}).get("late_penalty_per_hour") or 0
    penalty_score = min(penalty_per_h / 10000.0, 1.0)

    invoice = impact.get("invoice") or {}
    pending = str(invoice.get("status", "")).lower() in {"pending", "not_paid", "unpaid"}
    amount = invoice.get("amount") or 0
    invoice_score = min(amount / 200000.0, 1.0) if pending else 0.0

    delay = impact.get("delay_hours")
    delay_score = min(delay / 12.0, 1.0) if isinstance(delay, (int, float)) else 0.0

    weights = {"cold_chain": 25, "client_tier": 20, "penalty": 25, "invoice": 15, "delay": 15}
    raw = {
        "cold_chain": cold,
        "client_tier": tier_score,
        "penalty": penalty_score,
        "invoice": invoice_score,
        "delay": delay_score,
    }
    weighted = {k: round(raw[k] * weights[k], 2) for k in weights}
    total = round(sum(weighted.values()), 2)
    return {
        "total": total,
        "weights": weights,
        "normalized": {k: round(v, 4) for k, v in raw.items()},
        "weighted": weighted,
        "facts": {
            "cold_chain": bool(cold),
            "priority_tier": tier,
            "penalty_per_hour": penalty_per_h or None,
            "invoice_amount_pending": amount if pending else None,
            "delay_hours": delay,
        },
    }


def score_delayed_shipments() -> list[dict[str, Any]]:
    """Récupère TOUS les shipments `Delayed`, calcule leur impact, les SCORE et les trie.

    C'est ce score (transparent, documenté dans `_score_components`) qui fait émerger le
    point chaud — pas un champ pré-mâché. Renvoie la liste triée par score décroissant, avec
    le DÉTAIL de chaque composante pour que l'agent explique POURQUOI le 1er gagne.
    """
    delayed = find_nodes("Shipment", attr_equals={"status": "Delayed"})
    scored: list[dict[str, Any]] = []
    for node in delayed:
        impact = compute_impact(node["id"])
        components = _score_components(impact)
        scored.append(
            {
                "shipment_id": node["id"],
                "name": node["name"],
                "score": components["total"],
                "score_detail": components,
                "customer": (impact.get("customer") or {}).get("name"),
                "penalty": impact.get("penalty"),
                "invoice": (
                    {
                        "id": impact["invoice"]["id"],
                        "amount": impact["invoice"].get("amount"),
                        "status": impact["invoice"].get("status"),
                    }
                    if impact.get("invoice")
                    else None
                ),
            }
        )
    scored.sort(key=lambda s: s["score"], reverse=True)
    return scored


# --------------------------------------------------------------------------- #
# Fragilité structurelle — questions de structure
# --------------------------------------------------------------------------- #
def articulation_points() -> list[dict[str, Any]]:
    """Points d'articulation (sur la version non dirigée) : retirer ce nœud fragmente le graphe.

    Sert aux questions de structure (« qui sont les hommes-clés ? », « de quoi dépend la
    boîte ? »). Renvoie chaque nœud avec type/name/layer pour que l'agent l'interprète.
    """
    graph = get_graph()
    undirected = nx.Graph(graph.to_undirected(as_view=True))
    points = list(nx.articulation_points(undirected))
    out = [_node_payload(graph, n, full=False) for n in points]
    out.sort(key=lambda n: (n.get("type") or "", n.get("name") or ""))
    return out


def centrality(top: int = 10) -> list[dict[str, Any]]:
    """Top-N nœuds par centralité de degré (version non dirigée) : les plus connectés.

    Approxime « de qui/quoi dépend le plus la boîte » (concentration, hommes-clés). Renvoie
    type/name + le score de centralité pour que l'agent l'interprète et le source.
    """
    graph = get_graph()
    undirected = graph.to_undirected(as_view=True)
    scores = nx.degree_centrality(undirected)
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[: max(0, top)]
    out: list[dict[str, Any]] = []
    for node_id, score in ranked:
        payload = _node_payload(graph, node_id, full=False)
        payload["centrality"] = round(score, 4)
        payload["degree"] = undirected.degree(node_id)
        out.append(payload)
    return out
