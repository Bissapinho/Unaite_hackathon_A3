"""validate_ontology.py — oracle de test (Système A, étage 1).

SEUL fichier autorisé à importer data.canonical (c'est un TEST, pas le système).
Compare outputs/ontology.json à la vérité de canonical.py et imprime un rapport
PASS/FAIL (exit non-zéro si échec).

Usage : python system_a/validate_ontology.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data import canonical  # noqa: E402  (autorisé UNIQUEMENT ici)

ONTOLOGY = ROOT / "outputs" / "ontology.json"

# --------------------------------------------------------------------------- #
# Mini-framework de checks
# --------------------------------------------------------------------------- #
_RESULTS = []


def check(cond: bool, label: str, detail: str = "") -> bool:
    _RESULTS.append((bool(cond), label, detail))
    mark = "PASS" if cond else "FAIL"
    line = f"[{mark}] {label}"
    if detail and not cond:
        line += f"\n        -> {detail}"
    print(line)
    return bool(cond)


def info(label: str, detail: str = "") -> None:
    print(f"[INFO] {label}" + (f"\n        -> {detail}" if detail else ""))


def slug(s: str) -> str:
    s = (s or "").strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def main() -> int:
    onto = json.loads(ONTOLOGY.read_text(encoding="utf-8"))
    entities = onto["entities"]
    rels = onto["relationships"]
    by_id = {e["id"]: e for e in entities}
    by_type = {}
    for e in entities:
        by_type.setdefault(e["type"], []).append(e)

    def count(t):
        return len(by_type.get(t, []))

    def has_rel(src, tgt, rtype=None, undirected=False):
        for r in rels:
            ok = (r["source"] == src and r["target"] == tgt)
            if undirected:
                ok = ok or (r["source"] == tgt and r["target"] == src)
            if ok and (rtype is None or r["type"] == rtype):
                return True
        return False

    print("=" * 70)
    print("VALIDATION ontology.json vs canonical.py")
    print("=" * 70)

    # ---- 1. Comptes d'entités ------------------------------------------- #
    print("\n--- 1. Comptes d'entités (vs canonical.counts) ---")
    cc = canonical.counts()
    expected = {
        "Customer": cc["customers"], "Order": cc["orders"], "Shipment": cc["shipments"],
        "Invoice": cc["invoices"], "Product": cc["products"], "Carrier": cc["carriers"],
        "Vehicle": cc["vehicles"], "Driver": cc["drivers"], "Warehouse": cc["warehouses"],
        "Supplier": cc["suppliers"], "Employee": cc["employees"],
    }
    for t, n in expected.items():
        check(count(t) == n, f"{t} == {n}", f"trouvé {count(t)}")
    # PurchaseOrder : un par commande
    check(count("PurchaseOrder") == cc["orders"], f"PurchaseOrder == {cc['orders']}",
          f"trouvé {count('PurchaseOrder')}")
    # Contrats : TROU DE SOURCE assumé (cf. build_ontology). canonical en a 8, mais
    # aucune source ne les expose ; seul CT-001 est documenté (PDF SLA).
    info(f"Contrats : canonical={cc['contracts']}, ontologie={count('Contract')} "
         f"(trou de source assumé — seul CT-001 est exposé par le PDF SLA ; les autres "
         f"contrats ne figurent dans aucune source, comme le lien shipment<->order).")
    check("contract:ct-001" in by_id, "Contrat sourcé CT-001 présent (PDF SLA)")
    ct = by_id.get("contract:ct-001", {}).get("attributes", {})
    check(ct.get("late_penalty_per_hour") == canonical.SCENARIO_CONTRACTS[0]["late_penalty_per_hour"],
          "CT-001 pénalité/h == canonical (7000)",
          f"trouvé {ct.get('late_penalty_per_hour')}")

    # ---- 2. Couverture des 3 couches ------------------------------------ #
    print("\n--- 2. Couverture des 3 couches ---")
    layers = {e["layer"] for e in entities}
    check(layers == {"operational", "hr", "financial"},
          "couches == {operational, hr, financial}", f"trouvé {layers}")
    bad = [e["id"] for e in entities if e["layer"] not in ("operational", "hr", "financial")]
    check(not bad, "chaque entité a une couche valide", f"invalides: {bad[:5]}")
    for lyr in ("operational", "hr", "financial"):
        check(any(e["layer"] == lyr for e in entities), f"couche '{lyr}' non vide")

    # ---- 3. Organigramme reconstruit à 100 % ---------------------------- #
    print("\n--- 3. Organigramme (reports_to == canonical.manager_id) ---")
    emp_by_id = {e["employee_id"]: e for e in canonical.EMPLOYEES}
    reports_to = {}
    for r in rels:
        if r["type"] == "reports_to":
            reports_to[r["source"]] = r["target"]
    org_ok = True
    detail = []
    for e in canonical.EMPLOYEES:
        src = f"employee:{slug(e['full_name'])}"
        if e["manager_id"] is None:
            if src in reports_to:
                org_ok = False
                detail.append(f"{e['full_name']} (DG) ne devrait pas avoir de manager")
            continue
        mgr = emp_by_id[e["manager_id"]]
        exp_tgt = f"employee:{slug(mgr['full_name'])}"
        if reports_to.get(src) != exp_tgt:
            org_ok = False
            detail.append(f"{e['full_name']} -> attendu {mgr['full_name']}, "
                          f"trouvé {reports_to.get(src)}")
    check(org_ok, "100% des liens reports_to == manager_id caché", "; ".join(detail[:5]))

    # acyclique + racine unique
    roots = [e["id"] for e in by_type.get("Employee", []) if e["id"] not in reports_to]
    check(len(roots) == 1, "une seule racine d'organigramme", f"racines: {roots}")
    check(roots == ["employee:philippe-caron"] if roots else False,
          "racine == Philippe Caron", f"trouvé {roots}")
    # détection de cycle
    acyclic = True
    for start in [e["id"] for e in by_type.get("Employee", [])]:
        seen, cur = set(), start
        while cur in reports_to:
            if cur in seen:
                acyclic = False
                break
            seen.add(cur)
            cur = reports_to[cur]
        if not acyclic:
            break
    check(acyclic, "organigramme acyclique")

    # ---- 4. Résolution floue -------------------------------------------- #
    print("\n--- 4. Résolution floue (legacy -> client) ---")
    mp = by_id.get("customer:medpharma", {})
    check(any("legacy_contacts" in s for s in mp.get("sources", [])),
          "MedPharma a une source legacy_contacts (fuzzy)",
          f"sources={mp.get('sources')}")
    fm = by_id.get("customer:freshmarket", {})
    check(any("legacy_contacts" in s for s in fm.get("sources", [])),
          "FreshMarket a une source legacy_contacts (fuzzy)",
          f"sources={fm.get('sources')}")

    # ---- 5. Account managers -------------------------------------------- #
    print("\n--- 5. Account managers (Employee manages Customer) ---")
    manages = {}  # customer_node -> employee_node
    for r in rels:
        if r["type"] == "manages":
            manages[r["target"]] = r["source"]
    am_ok = True
    am_detail = []
    for c in canonical.CUSTOMERS:
        am = c.get("account_manager")
        if not am:
            continue
        cust_node = f"customer:{slug(c['name'])}"
        exp_emp = f"employee:{slug(am)}"
        if manages.get(cust_node) != exp_emp:
            am_ok = False
            am_detail.append(f"{c['name']}: attendu {am}, trouvé {manages.get(cust_node)}")
    check(am_ok, "chaque manages == account_manager canonique", "; ".join(am_detail[:5]))
    check(manages.get("customer:medpharma") == "employee:sarah-martin"
          and manages.get("customer:biocare-labs") == "employee:sarah-martin",
          "Sarah Martin gère MedPharma (C001) et BioCare (C004)")

    # ---- 6. Driver is_a Employee ---------------------------------------- #
    print("\n--- 6. Driver is_a Employee ---")
    isa = [(r["source"], r["target"]) for r in rels if r["type"] == "is_a"]
    check(len(isa) == 3, "exactement 3 liens is_a", f"trouvé {len(isa)}")
    isa_emp = {tgt for _, tgt in isa}
    expected_drv = {f"employee:{slug(n)}" for n in ("Thomas Girard", "Mehdi Faure", "David Olivier")}
    check(isa_emp == expected_drv, "is_a == Thomas/Mehdi/David",
          f"trouvé {isa_emp}")

    # ---- 7. Chaîne du scénario ------------------------------------------ #
    print("\n--- 7. Chaîne scénario SH-2049 ---")
    check(has_rel("customer:medpharma", "po:po-8821", "places"),
          "MedPharma places PO-8821")
    check(has_rel("po:po-8821", "order:o-881", "creates"),
          "PO-8821 creates O-881")
    check(has_rel("order:o-881", "shipment:sh-2049", "fulfilled_by"),
          "O-881 fulfilled_by SH-2049 (via PDF)")
    check(has_rel("shipment:sh-2049", "product:pharma-22", "contains"),
          "SH-2049 contains PHARMA-22")
    check(has_rel("invoice:inv-7742", "order:o-881", "bills", undirected=True),
          "INV-7742 <-> O-881 (bills)")
    check(has_rel("customer:medpharma", "contract:ct-001", "governed_by"),
          "MedPharma governed_by CT-001")

    # ---- 8. CA / concentration ------------------------------------------ #
    print("\n--- 8. CA & concentration (calculés depuis les factures) ---")
    rc = by_id.get("financial:revenue-concentration", {}).get("attributes", {})
    check(rc.get("total_revenue") == canonical.total_revenue(),
          f"total_revenue == {canonical.total_revenue()}",
          f"trouvé {rc.get('total_revenue')}")
    check(canonical.total_revenue() == 1_689_940, "canonical total_revenue == 1 689 940")
    canon_rc = {row["customer_id"]: row["revenue"] for row in canonical.revenue_concentration()}
    onto_rc = {row["customer_id"]: row["revenue"] for row in rc.get("by_customer", [])}
    check(onto_rc == canon_rc, "concentration par client == canonical",
          f"diffs: {[(k, onto_rc.get(k), canon_rc.get(k)) for k in canon_rc if onto_rc.get(k) != canon_rc.get(k)][:5]}")
    top3_onto = [r["name"] for r in rc.get("by_customer", [])[:3]]
    top3_canon = [r["name"] for r in canonical.revenue_concentration()[:3]]
    check(top3_onto == top3_canon, f"top 3 CA == {top3_canon}", f"trouvé {top3_onto}")

    # ---- 9. Provenance --------------------------------------------------- #
    print("\n--- 9. Provenance (sources / confidence / evidence) ---")
    ent_bad = [e["id"] for e in entities
               if not e.get("sources") or not e.get("evidence")
               or not (0 < e.get("confidence", 0) <= 1)]
    check(not ent_bad, "chaque entité : sources+evidence non vides, confidence in ]0,1]",
          f"manquants: {ent_bad[:5]}")
    rel_bad = [(r["source"], r["target"], r["type"]) for r in rels
               if not r.get("evidence") or not (0 < r.get("confidence", 0) <= 1)]
    check(not rel_bad, "chaque relation : evidence non vide, confidence in ]0,1]",
          f"manquants: {rel_bad[:5]}")
    rt_bad = [(r["source"], r["target"]) for r in rels if r["type"] == "reports_to"
              and (r["confidence"] > 0.85 or not r.get("open_questions"))]
    check(not rt_bad, "chaque reports_to : confidence <= 0.85 + open_question",
          f"violations: {rt_bad[:5]}")

    # ---- 10. Anti-triche (statique) ------------------------------------- #
    print("\n--- 10. Anti-triche (statique) ---")
    import_re = re.compile(r"^\s*(?:from|import)\s+(.+)$", re.M)
    for fname in ("build_ontology.py", "sources.py", "resolve.py", "orgchart.py"):
        src = (ROOT / "system_a" / fname).read_text(encoding="utf-8")
        imports = import_re.findall(src)
        imports_canonical = any("canonical" in imp for imp in imports)
        check(not imports_canonical, f"{fname} n'importe pas canonical",
              f"imports suspects: {[i for i in imports if 'canonical' in i]}")
        check("_scenario_manifest" not in src, f"{fname} ne lit pas _scenario_manifest.json")

    # ---- bilan ----------------------------------------------------------- #
    print("\n" + "=" * 70)
    passed = sum(1 for ok, _, _ in _RESULTS if ok)
    total = len(_RESULTS)
    failed = total - passed
    print(f"RÉSULTAT : {passed}/{total} PASS" + (f"  —  {failed} FAIL" if failed else "  —  tout PASS ✅"))
    print("=" * 70)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
