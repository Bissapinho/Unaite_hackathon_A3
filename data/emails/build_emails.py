"""build_emails.py — Sérialise les emails canoniques en JSON réaliste.

Lit la source de vérité (data/canonical.py) et écrit
`data/emails/emails.json` : un tableau JSON d'objets email (id, from, to,
subject, body, received_at, labels) SANS les clés internes `_scenario*`.

Idempotent et lançable seul :
    .venv/bin/python data/emails/build_emails.py
"""

from __future__ import annotations

import json
import pathlib
import sys

# --- Bootstrap : rendre le package `data` importable (parents[2] = racine repo) #
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from data import canonical as C  # noqa: E402


OUTPUT_PATH = ROOT / "data" / "emails" / "emails.json"


def main() -> None:
    """Écrit emails.json depuis C.EMAILS (clés internes retirées) et résume."""
    emails = C.strip_internal_list(C.EMAILS)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(emails, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # --- Résumé -------------------------------------------------------------- #
    print(f"[build_emails] Wrote {len(emails)} emails -> {OUTPUT_PATH}")
    for e in emails:
        labels = ", ".join(e.get("labels", []))
        print(f"  - {e['id']:<7} {e['from']:<38} | {e['subject']}  [{labels}]")

    # garantit qu'aucune clé interne n'a fuité
    leaked = [k for e in emails for k in e if k.startswith("_")]
    assert not leaked, f"Internal keys leaked into emails.json: {set(leaked)}"


if __name__ == "__main__":
    main()
