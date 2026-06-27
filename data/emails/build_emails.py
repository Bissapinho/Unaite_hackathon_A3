"""build_emails.py — Vérifie la cohérence entre les .eml bruts et canonical.

Depuis le refactor « emails = .eml bruts » (anti-triche : le Système A doit
extraire l'info d'emails réalistes, pas lire un JSON pré-structuré), il n'y a
plus de emails.json généré depuis canonical. Les fichiers `data/emails/raw/*.eml`
sont la **source de vérité figée**.

Ce script ne génère donc plus rien : il **vérifie** que le contenu parsé des
.eml correspond toujours à `canonical.EMAILS` (mêmes id, from, to, subject,
body, received_at, labels). C'est un garde-fou contre une divergence silencieuse
entre les emails écrits à la main et la vérité métier de canonical.

Lançable seul :
    .venv/bin/python data/emails/build_emails.py   # exit != 0 si divergence
"""

from __future__ import annotations

import pathlib
import sys

# --- Bootstrap : rendre le package `data` importable (parents[2] = racine repo) #
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from data import canonical as C  # noqa: E402
from data.emails.eml_to_json import load_emails  # noqa: E402

RAW_DIR = ROOT / "data" / "emails" / "raw"
FIELDS = ("from", "to", "subject", "body", "received_at", "labels")


def main() -> int:
    """Compare les .eml parsés à canonical.EMAILS. Retourne 0 si identiques."""
    parsed = {e["id"]: e for e in load_emails(RAW_DIR)}
    canonical = {e["id"]: C.strip_internal(e) for e in C.EMAILS}

    errors: list[str] = []
    missing = set(canonical) - set(parsed)
    extra = set(parsed) - set(canonical)
    if missing:
        errors.append(f"Emails absents des .eml : {sorted(missing)}")
    if extra:
        errors.append(f".eml en trop (pas dans canonical) : {sorted(extra)}")

    for eid in sorted(set(canonical) & set(parsed)):
        for field in FIELDS:
            if canonical[eid].get(field) != parsed[eid].get(field):
                errors.append(
                    f"{eid}.{field} diffère :\n"
                    f"    canonical: {canonical[eid].get(field)!r}\n"
                    f"    .eml     : {parsed[eid].get(field)!r}"
                )

    print(f"[build_emails] {len(parsed)} .eml parsés depuis {RAW_DIR}")
    if errors:
        print("[build_emails] DIVERGENCE .eml ↔ canonical :")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("[build_emails] OK — les .eml correspondent exactement à canonical.EMAILS.")
    for e in sorted(parsed.values(), key=lambda x: x["id"]):
        labels = ", ".join(e.get("labels", []))
        print(f"  - {e['id']:<7} {e['from']:<38} | {e['subject']}  [{labels}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
