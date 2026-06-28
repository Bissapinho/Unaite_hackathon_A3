"""compare_to_oracle.py — score de convergence agentique vs oracle (TEST EXTERNE).

Charge outputs/ontology.agentic.json (sortie de l'étage 2) et outputs/ontology.json
(l'oracle déterministe, étage 1) et imprime un score + un diff actionnable. Ce script
N'EST PAS une passe du pipeline : c'est un test, il a le DROIT de lire l'oracle (comme
data/validate.py). Le pipeline, lui, ne lit jamais l'oracle.

Objectif (prompt d'étage) : SCORE ≥ 95 % avec chaîne SH-2049 + organigramme + CA EXACTS.

Usage : python compare_to_oracle.py [--agentic chemin] [--oracle chemin]
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# 7 relations clés de la chaîne SH-2049 (CLAUDE §7)
SH_CHAIN = [
    ("customer:medpharma", "po:po-8821", "places"),
    ("po:po-8821", "order:o-881", "creates"),
    ("invoice:inv-7742", "order:o-881", "bills"),
    ("order:o-881", "shipment:sh-2049", "fulfilled_by"),
    ("shipment:sh-2049", "carrier:coldroad", "operated_by"),
    ("shipment:sh-2049", "product:pharma-22", "contains"),
    ("customer:medpharma", "contract:ct-001", "governed_by"),
]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _rel_set(o: dict) -> set:
    return {(r["source"], r["target"], r["type"]) for r in o.get("relationships", [])}


def _id_set(o: dict) -> set:
    return {e["id"] for e in o.get("entities", [])}


def _reports_to(o: dict) -> dict:
    return {r["source"]: r["target"] for r in o.get("relationships", [])
            if r["type"] == "reports_to"}


def _revenue(o: dict) -> dict | None:
    for e in o.get("entities", []):
        if e.get("type") == "RevenueConcentration":
            a = e.get("attributes", {})
            top3 = [c.get("name") for c in (a.get("by_customer") or [])[:3]]
            return {"total": a.get("total_revenue"), "top3": top3}
    return None


def _pct(part: int, whole: int) -> float:
    return 100.0 * part / whole if whole else 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agentic", default=str(ROOT / "outputs" / "ontology.agentic.json"))
    ap.add_argument("--oracle", default=str(ROOT / "outputs" / "ontology.json"))
    args = ap.parse_args()

    ag = _load(Path(args.agentic))
    orc = _load(Path(args.oracle))

    print("=" * 70)
    print("CONVERGENCE — agentique vs oracle")
    print("=" * 70)

    # --- 1. comptes par type (30 %) ---
    ag_t = Counter(e["type"] for e in ag.get("entities", []))
    orc_t = Counter(e["type"] for e in orc.get("entities", []))
    types = sorted(set(ag_t) | set(orc_t))
    print("\n[1] Comptes par type (agentique / oracle / Δ) :")
    type_match = 0
    for t in types:
        a, o = ag_t.get(t, 0), orc_t.get(t, 0)
        flag = "" if a == o else "  <-- Δ"
        if a == o:
            type_match += 1
        print(f"  {t:20s} {a:3d} / {o:3d}{flag}")
    count_score = _pct(type_match, len(types))
    ag_layer = Counter(e["layer"] for e in ag.get("entities", []))
    orc_layer = Counter(e["layer"] for e in orc.get("entities", []))
    print(f"  layers agentique={dict(ag_layer)} oracle={dict(orc_layer)}")
    print(f"  → score comptes : {count_score:.1f}% ({type_match}/{len(types)} types exacts)")

    # --- 2. ensembles d'id (20 %) ---
    ag_ids, orc_ids = _id_set(ag), _id_set(orc)
    missing = orc_ids - ag_ids
    extra = ag_ids - orc_ids
    inter = ag_ids & orc_ids
    id_score = _pct(len(inter), len(orc_ids))
    print(f"\n[2] Ids : {len(inter)}/{len(orc_ids)} de l'oracle présents")
    if missing:
        print(f"  manquants ({len(missing)}): {sorted(missing)[:15]}")
    if extra:
        print(f"  en plus ({len(extra)}): {sorted(extra)[:15]}")
    print(f"  → score ids : {id_score:.1f}%")

    # --- 3. chaîne SH-2049 (20 %) ---
    ag_rels = _rel_set(ag)
    print("\n[3] Chaîne SH-2049 :")
    chain_ok = 0
    for s, t, ty in SH_CHAIN:
        present = (s, t, ty) in ag_rels
        chain_ok += present
        print(f"  [{'OK' if present else 'KO'}] {ty}({s} → {t})")
    chain_score = _pct(chain_ok, len(SH_CHAIN))
    print(f"  → score chaîne : {chain_score:.1f}% ({chain_ok}/{len(SH_CHAIN)})")

    # --- 4. organigramme (20 %) ---
    ag_rt, orc_rt = _reports_to(ag), _reports_to(orc)
    print(f"\n[4] Organigramme (reports_to) : agentique={len(ag_rt)} oracle={len(orc_rt)}")
    org_match = sum(1 for k, v in orc_rt.items() if ag_rt.get(k) == v)
    org_score = _pct(org_match, len(orc_rt)) if orc_rt else 0.0
    divergent = [f"{k}: ag={ag_rt.get(k)} vs orc={v}"
                 for k, v in orc_rt.items() if ag_rt.get(k) != v]
    for d in divergent[:12]:
        print(f"  Δ {d}")
    print(f"  → score organigramme : {org_score:.1f}% ({org_match}/{len(orc_rt)})")

    # --- 5. CA / concentration (10 %) ---
    ag_rev, orc_rev = _revenue(ag), _revenue(orc)
    print("\n[5] CA / concentration :")
    ca_score = 0.0
    if ag_rev and orc_rev:
        total_ok = ag_rev["total"] == orc_rev["total"]
        top3_ok = ag_rev["top3"] == orc_rev["top3"]
        print(f"  total_revenue : agentique={ag_rev['total']} oracle={orc_rev['total']} "
              f"{'OK' if total_ok else 'KO'}")
        print(f"  top-3 : agentique={ag_rev['top3']}")
        print(f"          oracle   ={orc_rev['top3']} {'OK' if top3_ok else 'KO'}")
        ca_score = 100.0 * (0.5 * total_ok + 0.5 * top3_ok)
    else:
        print(f"  RevenueConcentration introuvable (agentique={bool(ag_rev)} "
              f"oracle={bool(orc_rev)})")
    print(f"  → score CA : {ca_score:.1f}%")

    # --- provenance (info) ---
    def prov_pct(o):
        items = o.get("entities", []) + o.get("relationships", [])
        good = sum(1 for x in items if x.get("sources", x.get("source")) and x.get("evidence"))
        # relations n'ont pas "sources" : on compte evidence
        good = sum(1 for x in o.get("entities", []) if x.get("sources") and x.get("evidence"))
        good += sum(1 for r in o.get("relationships", []) if r.get("evidence"))
        n = len(o.get("entities", [])) + len(o.get("relationships", []))
        return _pct(good, n)
    rt_ok = all((r.get("confidence") or 0) <= 0.85
                for r in ag.get("relationships", []) if r["type"] == "reports_to")
    print(f"\n[i] Provenance agentique : {prov_pct(ag):.1f}% des éléments avec evidence ; "
          f"reports_to ≤ 0.85 : {'oui' if rt_ok else 'NON'}")

    # --- SCORE GLOBAL ---
    score = (0.30 * count_score + 0.20 * id_score + 0.20 * chain_score
             + 0.20 * org_score + 0.10 * ca_score)
    exact = chain_score == 100 and org_score == 100 and ca_score == 100
    print("\n" + "=" * 70)
    print(f"SCORE GLOBAL : {score:.1f}%   (objectif ≥ 95% avec chaîne+orga+CA exacts)")
    print(f"  comptes {count_score:.0f}%·0.30 | ids {id_score:.0f}%·0.20 | "
          f"chaîne {chain_score:.0f}%·0.20 | orga {org_score:.0f}%·0.20 | CA {ca_score:.0f}%·0.10")
    if score >= 95 and exact:
        print("✅ OBJECTIF ATTEINT")
    else:
        print("⏳ pas encore — chaîne/orga/CA doivent être à 100% et score ≥ 95%")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
