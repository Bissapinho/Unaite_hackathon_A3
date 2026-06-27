"""orgchart.py — reconstruction de l'organigramme (Système A, étage 1).

L'organigramme n'est exposé dans AUCUNE source (l'annuaire Excel n'a pas de colonne
manager). On le reconstruit par une règle structurelle déterministe à deux branches
(cf. CLAUDE §6 / DATA_README §2bis), confirmée quand c'est possible par les escalades
d'emails internes.

Garde-fou (CLAUDE §9) : aucun import de data.canonical, aucun manager_id lu d'une
source. Les liens produits sont *inférés* -> confidence basse + open_question.
"""

from __future__ import annotations

import re

# Rang hiérarchique déduit du seul intitulé de poste (title_rank n'est PAS dans
# l'annuaire ; on le dérive localement).
#   1 = Directeur Général ; 2 = Directeur/Directrice <X> ; 3 = Responsable <X> ;
#   4 = Chargé(e) / Chauffeur / Comptable.
def title_rank(role_title: str) -> int:
    t = (role_title or "").strip().lower()
    if t.startswith("directeur général") or t.startswith("directrice générale"):
        return 1
    if t.startswith("directeur") or t.startswith("directrice"):
        return 2
    if t.startswith("responsable"):
        return 3
    return 4  # chargé(e), chauffeur, comptable, …


_EMAIL_RE = re.compile(r"[\w.\-]+@[\w.\-]+")


def _emp_by_email(employees: list[dict]) -> dict:
    return {(e.get("email") or "").lower(): e for e in employees}


def _email_confirmations(employees: list[dict], emails: list[dict]) -> set:
    """Paires {frozenset({emp_id_a, emp_id_b})} pour lesquelles un email interne
    employé->employé matérialise un lien hiérarchique (escalade/délégation).

    On reste prudent : on ne retient que les échanges directs expéditeur->destinataire
    entre deux salariés ; le langage métier ('je transmets pour validation', 'je remonte
    au DG', 'peux-tu prendre la tournée') matérialise alors un lien hiérarchique entre
    eux, sans jamais que le mot 'manager' soit écrit.
    """
    by_email = _emp_by_email(employees)
    pairs = set()
    for msg in emails:
        frm = (msg.get("from") or "").lower()
        to = (msg.get("to") or "").lower()
        # 'to' peut contenir plusieurs adresses / un display name -> on extrait.
        from_emp = by_email.get(frm)
        if from_emp is None:
            m = _EMAIL_RE.search(frm)
            from_emp = by_email.get(m.group(0).lower()) if m else None
        for addr in _EMAIL_RE.findall(to):
            to_emp = by_email.get(addr.lower())
            if from_emp and to_emp and from_emp is not to_emp:
                pairs.add(frozenset({from_emp["employee_id"], to_emp["employee_id"]}))
    return pairs


def reconstruct(employees: list[dict], emails: list[dict] | None = None) -> dict:
    """Reconstruit les liens reports_to.

    Retourne {employee_id: {manager_id, confidence, evidence: [...], open_questions: [...]}}.
    Le DG (rang 1) n'a pas de manager (absent du dict).
    """
    emails = emails or []
    # title_rank par employé
    ranked = []
    for e in employees:
        ranked.append({**e, "title_rank": title_rank(e["role_title"])})

    # DG = unique employé de rang 1 (org_unit Direction)
    dg = next((e for e in ranked if e["title_rank"] == 1), None)

    # rangs présents par service
    units: dict[str, list[dict]] = {}
    for e in ranked:
        units.setdefault(e["org_unit"], []).append(e)

    confirmations = _email_confirmations(employees, emails)
    by_id = {e["employee_id"]: e for e in ranked}

    result = {}
    for e in ranked:
        if dg and e["employee_id"] == dg["employee_id"]:
            continue  # racine
        unit = e["org_unit"]
        peers = units[unit]
        unit_ranks = sorted({p["title_rank"] for p in peers})
        is_chef = e["title_rank"] == unit_ranks[0]  # plus haut rang du service

        if is_chef and dg:
            manager = dg
            base_ev = (f"chef de service '{unit}' (rang {e['title_rank']}, "
                       f"le plus élevé du service) -> reporte au Directeur Général")
        else:
            # manager = rang immédiatement supérieur DANS le même service (unique)
            higher = [r for r in unit_ranks if r < e["title_rank"]]
            mgr_rank = higher[-1]
            manager = next(p for p in peers if p["title_rank"] == mgr_rank)
            base_ev = (f"même service '{unit}', rang {e['title_rank']} reporte au rang "
                       f"{mgr_rank} immédiatement supérieur (candidat unique du service)")

        evidence = [base_ev]
        open_q = ["lien reconstruit par inférence (titre + service), non écrit dans une source RH explicite"]
        confidence = 0.70

        # confirmation par escalade email entre les deux personnes ?
        if frozenset({e["employee_id"], manager["employee_id"]}) in confirmations:
            confidence = 0.85
            evidence.append(
                f"escalade/délégation email entre {e['full_name']} et {manager['full_name']} "
                f"confirme le lien hiérarchique")

        result[e["employee_id"]] = {
            "manager_id": manager["employee_id"],
            "manager_name": manager["full_name"],
            "confidence": confidence,
            "evidence": evidence,
            "open_questions": open_q,
        }
    return result
