"""generate_all.py — point d'entrée UNIQUE et IDEMPOTENT de la Brique 1.

Génère, depuis la source de vérité `data/canonical.py` :
  - data/odoo/odoo_dump.json            (ERP, vocabulaire Odoo-like)
  - data/dashdoc/dashdoc_dump.json      (TMS, vocabulaire Dashdoc-like)
  - data/db/annex.sql + data/db/annex.db (base annexe SQLite : 3 tables)
  - data/excel/*.xlsx                    (3 fichiers bureautiques)
  - data/pdfs/*.pdf                      (4 documents texte extractible)
  - data/_scenario_manifest.json         (filet : IDs du scénario SH-2049)

Les EMAILS ne sont plus générés ici : les fichiers `data/emails/raw/*.eml`
sont la source de vérité figée (anti-triche). L'étape « Emails » se contente
de VÉRIFIER que ces .eml restent cohérents avec canonical.EMAILS.

Ré-exécutable sans erreur. Usage : python data/generate_all.py
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data import canonical as C  # noqa: E402
from data.odoo import build_odoo  # noqa: E402
from data.dashdoc import build_dashdoc  # noqa: E402
from data.emails import build_emails  # noqa: E402
from data.db import build_db  # noqa: E402
from data.excel import generate_excel  # noqa: E402
from data.pdfs import generate_pdfs  # noqa: E402


def write_scenario_manifest() -> pathlib.Path:
    """Expose les IDs du scénario hors des dumps (qui restent réalistes)."""
    path = ROOT / "data" / "_scenario_manifest.json"
    path.write_text(json.dumps(C.scenario_ids(), indent=2, ensure_ascii=False))
    return path


def main() -> None:
    print("=" * 70)
    print(f"generate_all — TODAY = {C.TODAY.isoformat()}")
    print("=" * 70)

    # Générateurs purs (écrivent leurs artefacts depuis canonical).
    steps = [
        ("ERP Odoo dump", build_odoo.main),
        ("TMS Dashdoc dump", build_dashdoc.main),
        ("SQLite annex DB", build_db.main),
        ("Excel files", generate_excel.main),
        ("PDF documents", generate_pdfs.main),
    ]
    for label, fn in steps:
        print(f"\n--- {label} ---")
        fn()

    # Emails : pas de génération (les .eml sont figés) — on VÉRIFIE leur cohérence.
    print("\n--- Emails (.eml figés : vérification de cohérence) ---")
    if build_emails.main() != 0:
        sys.exit("[generate_all] Les .eml divergent de canonical.EMAILS — voir ci-dessus.")

    print("\n--- Scenario manifest ---")
    p = write_scenario_manifest()
    print(f"wrote {p.relative_to(ROOT)}")

    print("\n" + "=" * 70)
    print("Counts:", json.dumps(C.counts(), ensure_ascii=False))
    print("OK — tous les artefacts générés.")
    print("=" * 70)


if __name__ == "__main__":
    main()
