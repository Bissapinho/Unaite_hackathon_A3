"""test_queries.py — l'ORACLE de B : prouve que le raisonnement-clé tient SANS LLM.

Teste `queries.py` en pur Python sur `outputs/ontology.agentic.json` réel. Si ces tests
passent, le calcul (impact, scoring, chemins, centralité) est correct AVANT qu'on branche
l'agent par-dessus (CLAUDE §8 : déterministe d'abord).

Lancement :  .venv/bin/python -m pytest system_b/tests -q
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
# B teste contre l'ontologie agentique publiée (le défaut), sauf override explicite.
os.environ.setdefault("ONTOLOGY_PATH", str(ROOT / "outputs" / "ontology.agentic.json"))

from system_b import queries  # noqa: E402
from system_b.graph_store import get_graph  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_graph():
    get_graph(force_reload=True)
    yield


def test_graph_loads():
    g = get_graph()
    assert g.number_of_nodes() > 100
    assert g.number_of_edges() > 100


def test_delayed_shipments_are_several():
    """Le statut ne suffit pas : SH-2049 est Delayed PARMI d'autres (le point du scoring)."""
    delayed = queries.find_nodes("Shipment", attr_equals={"status": "Delayed"})
    ids = {d["id"] for d in delayed}
    assert "shipment:sh-2049" in ids
    assert len(delayed) > 1, "il doit y avoir plusieurs Delayed sinon le scoring est trivial"


def test_no_is_hot_flag_exists():
    """Anti-triche : aucun shipment ne porte de drapeau pré-mâché type is_hot/risk/priority."""
    g = get_graph()
    for _, data in g.nodes(data=True):
        if data.get("type") == "Shipment":
            attrs = {k.lower() for k in data.get("attributes", {})}
            assert not (attrs & {"is_hot", "is_critical", "risk", "priority_score", "hot"})


def test_compute_impact_sh2049():
    impact = queries.compute_impact("shipment:sh-2049")
    # cold-chain
    assert impact["cold_chain"]["temperature_controlled"] is True
    # client MedPharma Platinum, strategic_value max
    assert impact["customer"] is not None
    assert impact["customer"]["name"] == "MedPharma"
    assert impact["customer"]["priority_tier"] == "Platinum"
    assert impact["customer"]["strategic_value"] == 1200000
    # contrat CT-001, pénalité 7000/h
    assert impact["contract"] is not None
    assert impact["contract"]["late_penalty_per_hour"] == 7000
    # facture INV-7742, 186 000 €, en cours
    assert impact["invoice"] is not None
    assert impact["invoice"]["id"] == "invoice:inv-7742"
    assert impact["invoice"]["amount"] == 186000
    assert str(impact["invoice"]["status"]).lower() in {"pending", "not_paid"}
    # délai présent -> pénalité = 6 * 7000 = 42 000
    assert impact["delay_hours"] == 6
    assert impact["penalty"]["amount"] == 42000


def test_score_designates_sh2049_first():
    scored = queries.score_delayed_shipments()
    assert scored, "score_delayed_shipments ne doit pas être vide"
    top = scored[0]
    assert top["shipment_id"] == "shipment:sh-2049"
    # strictement en tête (pas ex aequo) : il SORT par les chiffres
    if len(scored) > 1:
        assert top["score"] > scored[1]["score"]
    # le détail du score est exposé (pour que l'agent explique pourquoi)
    facts = top["score_detail"]["facts"]
    assert facts["cold_chain"] is True
    assert facts["priority_tier"] == "Platinum"
    assert facts["penalty_per_hour"] == 7000
    assert facts["delay_hours"] == 6


def test_shortest_path_medpharma_to_sh2049():
    path = queries.shortest_path("customer:medpharma", "shipment:sh-2049")
    assert path.get("path") != [] and "error" not in path
    assert path["length"] >= 1
    assert path["nodes"][0]["id"] == "customer:medpharma"
    assert path["nodes"][-1]["id"] == "shipment:sh-2049"
    # le chemin porte des arêtes citables
    assert path["edges"] and all("type" in e for e in path["edges"])


def test_neighbors_and_subgraph():
    neigh = queries.get_neighbors("shipment:sh-2049")
    assert any(n["neighbor"]["id"] == "product:pharma-22" for n in neigh)
    sub = queries.get_subgraph("shipment:sh-2049", depth=1)
    assert "shipment:sh-2049" in sub["node_ids"]
    assert len(sub["node_ids"]) > 1


def test_structure_tools_return_plausible_keys():
    arts = queries.articulation_points()
    assert isinstance(arts, list) and arts
    cent = queries.centrality(top=15)
    assert len(cent) == 15
    # Le SURFACE structurel combiné (centralité + points d'articulation) — ce que l'agent
    # croise pour répondre « hommes-clés / concentration » — fait remonter l'AM grands
    # comptes (Sarah Martin, central) ET le client stratégique (MedPharma, cut vertex).
    structural = {c["name"] for c in cent} | {a["name"] for a in arts}
    assert "Sarah Martin" in structural
    assert "MedPharma" in structural
