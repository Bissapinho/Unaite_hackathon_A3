"""P0 — Extraction de métadonnées (DÉTERMINISTE, NO LLM).

Inventorie chaque source publiée : entités/tables, schéma (clés présentes),
échantillon (2-3 enregistrements), comptes. Remplit `blackboard.raw`. C'est ce que
les passes LLM liront en premier pour se repérer (elles rechargeront les données
complètes via les outils MCP/readers — ici on ne donne qu'un plan de la donnée).

Garde-fou (CLAUDE §9) : lit les sources PUBLIÉES (dumps JSON, SQLite, Excel, PDF,
.eml). N'importe JAMAIS data.canonical ni le manifest de scénario.
"""

from __future__ import annotations

import json
import sqlite3
from email import message_from_string
from pathlib import Path

import openpyxl
from pypdf import PdfReader

from ..blackboard import Blackboard
from ..logging_ui import RunLogger

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


def _schema_count_sample(records: list[dict], n: int = 2) -> dict:
    keys: list[str] = []
    for r in records[:5]:
        for k in (r or {}):
            if k not in keys:
                keys.append(k)
    return {"schema": keys, "count": len(records), "sample": records[:n]}


def run(bb: Blackboard, logger: RunLogger) -> None:
    logger.banner("p0", "Extraction métadonnées (déterministe)")
    raw: dict = {}

    # --- Odoo dump ---
    odoo = json.loads((DATA / "odoo" / "odoo_dump.json").read_text(encoding="utf-8"))
    raw["odoo"] = {table: _schema_count_sample(recs) for table, recs in odoo.items()
                   if isinstance(recs, list)}
    logger.tool_call("file", "odoo_dump.json", "", f"{len(raw['odoo'])} tables")

    # --- Dashdoc dump ---
    dd = json.loads((DATA / "dashdoc" / "dashdoc_dump.json").read_text(encoding="utf-8"))
    raw["dashdoc"] = {k: _schema_count_sample(v) for k, v in dd.items()
                      if isinstance(v, list)}
    logger.tool_call("file", "dashdoc_dump.json", "", f"{len(raw['dashdoc'])} collections")

    # --- SQLite annexe ---
    con = sqlite3.connect(DATA / "db" / "annex.db")
    con.row_factory = sqlite3.Row
    try:
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        raw["sqlite"] = {}
        for t in tables:
            rows = [dict(r) for r in con.execute(f"SELECT * FROM {t}")]
            raw["sqlite"][t] = _schema_count_sample(rows)
    finally:
        con.close()
    logger.tool_call("sqlite", "annex.db", "", f"{len(raw['sqlite'])} tables")

    # --- Excel ---
    raw["excel"] = {}
    for path in sorted((DATA / "excel").glob("*.xlsx")):
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        raw["excel"][path.name] = {
            "headers": list(rows[0]) if rows else [],
            "rowcount": len(rows),
            "sample": [list(r) for r in rows[1:3]],
        }
    logger.tool_call("excel", "*.xlsx", "", f"{len(raw['excel'])} fichiers")

    # --- PDF ---
    raw["pdfs"] = []
    for path in sorted((DATA / "pdfs").glob("*.pdf")):
        reader = PdfReader(str(path))
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        raw["pdfs"].append({"name": path.name, "first_lines": lines[:3]})
    logger.tool_call("pdf", "*.pdf", "", f"{len(raw['pdfs'])} documents")

    # --- Emails bruts (.eml) : en-têtes seulement (le corps = travail des passes) ---
    raw["emails"] = []
    for path in sorted((DATA / "emails" / "raw").glob("*.eml")):
        msg = message_from_string(path.read_text(encoding="utf-8", errors="replace"))
        raw["emails"].append({
            "file": path.name,
            "from": msg.get("From"), "to": msg.get("To"),
            "subject": msg.get("Subject"),
        })
    logger.tool_call("eml", "*.eml", "", f"{len(raw['emails'])} emails")

    bb.raw = raw
    bb.log("p0", "extraction_complete",
           f"{len(raw['odoo'])} tables odoo, {len(raw['dashdoc'])} collections dashdoc, "
           f"{len(raw['sqlite'])} tables sqlite, {len(raw['excel'])} xlsx, "
           f"{len(raw['pdfs'])} pdf, {len(raw['emails'])} emails")
    logger.summary("inventaire des sources construit (blackboard.raw)")
