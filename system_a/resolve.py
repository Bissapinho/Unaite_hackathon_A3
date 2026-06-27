"""resolve.py — entity resolution (Système A, étage 1).

Rapproche une même entité réelle apparue sous des vocabulaires différents :
  - clé métier exacte (IDs identiques entre sources) : géré directement dans
    build_ontology via les IDs ;
  - résolution FLOUE des noms sales (legacy_contacts -> client canonique), via
    difflib.SequenceMatcher + confirmation par le domaine email ;
  - account manager (nom) -> Employee (full_name) ;
  - driver (nom) -> Employee (full_name).

Garde-fou (CLAUDE §9) : n'importe pas data.canonical, ne lit aucun manifest.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

# Suffixes juridiques à retirer pour normaliser un nom d'entreprise.
_LEGAL_SUFFIXES = [
    "sarl", "s.a.r.l", "sas", "s.a.s", "sa", "s.a", "sasu", "eurl", "old",
]
FUZZY_THRESHOLD = 0.82


def normalize_name(name: str) -> str:
    """minuscule, sans ponctuation ni suffixe juridique, espaces compactés."""
    if not name:
        return ""
    s = name.lower()
    s = re.sub(r"[().,\-_/]", " ", s)
    tokens = [t for t in s.split() if t and t not in _LEGAL_SUFFIXES]
    return " ".join(tokens)


def _domain(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    return email.split("@", 1)[1].strip().lower()


def name_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_name(a), normalize_name(b)).ratio()


def resolve_legacy_contacts(customers: list[dict], legacy: list[dict]) -> dict:
    """Rapproche chaque legacy_contact d'un client canonique (ou personne).

    Retourne {customer_id: [match, ...]} où match = {
        legacy_id, raw_name, email, ratio, domain_match, reason}.
    Un legacy non rattachable (bruit : SANCHEZ, DELAHAYE…) n'est associé à personne.
    """
    # Domaines email connus des clients : déduits du nom (pas exposé en Odoo) ->
    # on s'appuie d'abord sur le ratio de nom, confirmé par domaine quand dispo.
    matches: dict[str, list[dict]] = {}
    for lc in legacy:
        raw = lc.get("raw_name", "")
        lc_domain = _domain(lc.get("email"))
        best = None
        for cust in customers:
            ratio = name_ratio(raw, cust["name"])
            # confirmation par domaine : le domaine email du legacy contient le
            # nom normalisé du client (ex. medpharma.com contient 'medpharma').
            cust_token = normalize_name(cust["name"]).replace(" ", "")
            domain_match = bool(lc_domain and cust_token and cust_token in lc_domain.replace(".", ""))
            score = ratio + (0.15 if domain_match else 0.0)
            if best is None or score > best["_score"]:
                best = {
                    "customer_id": cust["customer_id"], "customer_name": cust["name"],
                    "legacy_id": lc["id"], "raw_name": raw, "email": lc.get("email"),
                    "ratio": round(ratio, 3), "domain_match": domain_match,
                    "_score": score,
                }
        # Acceptation : un nom au-dessus du seuil CONFIRMÉ par le domaine email,
        # ou un nom quasi identique (>=0.93) qui se passe de confirmation. Un nom
        # seulement « proche » sans domaine (ex. MARTINEZ S.A.R.L.) est du bruit
        # non rattachable -> on ne force pas le match (CLAUDE §9, anti-faux positif).
        accept = best and (
            (best["ratio"] >= FUZZY_THRESHOLD and best["domain_match"])
            or best["ratio"] >= 0.93
        )
        if accept:
            best.pop("_score")
            reason = []
            reason.append(f"SequenceMatcher ratio {best['ratio']} sur noms normalisés")
            if best["domain_match"]:
                reason.append(f"domaine email '{_domain(best['email'])}' confirme '{best['customer_name']}'")
            best["reason"] = "; ".join(reason)
            matches.setdefault(best["customer_id"], []).append(best)
    return matches


def index_employees_by_name(employees: list[dict]) -> dict:
    return {e["full_name"]: e for e in employees}


def resolve_account_managers(customers: list[dict], employees: list[dict]) -> dict:
    """{customer_id: employee} pour chaque AM dont le nom == un full_name d'employé."""
    by_name = index_employees_by_name(employees)
    out = {}
    for c in customers:
        am = c.get("account_manager")
        if am and am in by_name:
            out[c["customer_id"]] = by_name[am]
    return out


def resolve_drivers_to_employees(drivers: list[dict], employees: list[dict]) -> dict:
    """{driver_id: employee} pour chaque chauffeur dont le name == un full_name."""
    by_name = index_employees_by_name(employees)
    out = {}
    for d in drivers:
        if d["name"] in by_name:
            out[d["driver_id"]] = by_name[d["name"]]
    return out
