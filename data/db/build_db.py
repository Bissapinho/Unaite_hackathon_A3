"""build_db.py — Construit la "base annexe interne" SQLite d'une PME.

EXACTEMENT TROIS TABLES (pas de base centrale) :
  - customer_claims   (depuis C.CUSTOMER_CLAIMS)
  - sla_penalty_log   (depuis C.SLA_PENALTY_LOG)
  - legacy_contacts   (depuis C.LEGACY_CONTACTS)  -- volontairement "sale"

Pipeline de main() :
  1. construit la chaîne SQL (DDL + INSERT littéraux, apostrophes doublées, NULL gérés)
  2. écrit data/db/annex.sql
  3. supprime data/db/annex.db s'il existe puis recrée la base via executescript
  4. imprime un résumé (nb lignes par table)

Idempotent : DROP TABLE IF EXISTS en tête, base recréée à zéro à chaque run.
Aucune valeur métier en dur : tout provient de data/canonical.py.
"""

from __future__ import annotations

import pathlib
import sqlite3
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from data import canonical as C  # noqa: E402


# --------------------------------------------------------------------------- #
# Définition des tables : (nom, DDL colonnes, liste de colonnes, source)
# --------------------------------------------------------------------------- #
TABLES = [
    {
        "name": "customer_claims",
        "ddl": (
            "id INTEGER PRIMARY KEY",
            "customer_ref TEXT",
            "shipment_ref TEXT",
            "type TEXT",
            "opened_at TEXT",
            "closed_at TEXT",
            "status TEXT",
        ),
        "columns": ["id", "customer_ref", "shipment_ref", "type",
                    "opened_at", "closed_at", "status"],
        "rows": C.CUSTOMER_CLAIMS,
    },
    {
        "name": "sla_penalty_log",
        "ddl": (
            "id INTEGER PRIMARY KEY",
            "customer_ref TEXT",
            "shipment_ref TEXT",
            "hours_late INTEGER",
            "penalty_amount INTEGER",
            "month TEXT",
        ),
        "columns": ["id", "customer_ref", "shipment_ref",
                    "hours_late", "penalty_amount", "month"],
        "rows": C.SLA_PENALTY_LOG,
    },
    {
        "name": "legacy_contacts",
        "ddl": (
            "id INTEGER PRIMARY KEY",
            "raw_name TEXT",
            "email TEXT",
            "phone TEXT",
            "notes TEXT",
        ),
        "columns": ["id", "raw_name", "email", "phone", "notes"],
        "rows": C.LEGACY_CONTACTS,
    },
]


def sql_literal(value) -> str:
    """Représente une valeur Python en littéral SQL (pour le fichier .sql)."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    # chaîne : on double les apostrophes
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def build_sql() -> str:
    """Construit la chaîne SQL complète (DDL + INSERT littéraux)."""
    parts: list[str] = []
    parts.append("-- annex.sql — base annexe interne (généré par build_db.py)")
    parts.append("-- NE PAS éditer à la main : source de vérité = data/canonical.py")
    parts.append("PRAGMA foreign_keys = OFF;")
    parts.append("")

    for table in TABLES:
        name = table["name"]
        cols = table["columns"]

        parts.append(f"DROP TABLE IF EXISTS {name};")
        ddl_cols = ",\n    ".join(table["ddl"])
        parts.append(f"CREATE TABLE {name} (\n    {ddl_cols}\n);")

        col_list = ", ".join(cols)
        for row in table["rows"]:
            values = ", ".join(sql_literal(row.get(col)) for col in cols)
            parts.append(f"INSERT INTO {name} ({col_list}) VALUES ({values});")
        parts.append("")

    return "\n".join(parts) + "\n"


def main() -> None:
    db_dir = ROOT / "data" / "db"
    db_dir.mkdir(parents=True, exist_ok=True)
    sql_path = db_dir / "annex.sql"
    db_path = db_dir / "annex.db"

    # (1) construit la chaîne SQL
    sql = build_sql()

    # (2) écrit annex.sql
    sql_path.write_text(sql, encoding="utf-8")

    # (3) supprime annex.db s'il existe puis recrée la base
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(sql)
        conn.commit()

        # (4) résumé : nb lignes par table
        print(f"SQL écrit  : {sql_path}")
        print(f"Base créée : {db_path}")
        print("Lignes par table :")
        for table in TABLES:
            cur = conn.execute(f"SELECT COUNT(*) FROM {table['name']}")
            count = cur.fetchone()[0]
            print(f"  - {table['name']:16s} : {count}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
