"""readers.py — outils SDK (@tool) qui rendent les OCTETS lisibles. AUCUNE sémantique.

Frontière §9 : ces outils ne font que transformer des octets en texte/lignes/cellules
lisibles (SQLite, Excel, PDF, .eml) + deux calculatrices pures (`name_similarity`,
`sum_amounts`). Ils ne décident JAMAIS quoi fusionner, quel est le CA, ni ce qu'un terme
SLA signifie. Toute la sémantique (résolution floue, organigramme, lecture des termes du
contrat) est produite par l'agent LLM, evidence à l'appui.

Les sources couvertes par un serveur MCP (Odoo, Dashdoc, emails-pour-lister) sont servies
par leurs serveurs ; ici on couvre ce qui n'a pas de MCP : SQLite, Excel, PDF, et le texte
BRUT des .eml (chemin obligatoire pour la reconstruction d'organigramme — cf. §9).
"""

from __future__ import annotations

import json
import sqlite3
from difflib import SequenceMatcher
from pathlib import Path

import openpyxl
from claude_agent_sdk import create_sdk_mcp_server, tool
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


def _ok(payload) -> dict:
    """Emballe une charge utile au format de retour attendu par le SDK."""
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, indent=2)
    return {"content": [{"type": "text", "text": text}]}


# --------------------------------------------------------------------------- #
# SQLite (data/db/annex.db)
# --------------------------------------------------------------------------- #
@tool("sqlite_tables", "Liste les tables de la base SQLite annexe (data/db/annex.db).", {})
async def sqlite_tables(args) -> dict:
    con = sqlite3.connect(DATA / "db" / "annex.db")
    try:
        rows = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    finally:
        con.close()
    return _ok([r[0] for r in rows])


@tool("sqlite_rows", "Retourne toutes les lignes (dicts) d'une table SQLite annexe. Param: table (str).",
      {"table": str})
async def sqlite_rows(args) -> dict:
    table = (args or {}).get("table", "")
    if not table.replace("_", "").isalnum():
        return _ok({"error": "nom de table invalide", "table": table})
    con = sqlite3.connect(DATA / "db" / "annex.db")
    con.row_factory = sqlite3.Row
    try:
        rows = [dict(r) for r in con.execute(f"SELECT * FROM {table}").fetchall()]
    except sqlite3.Error as e:
        return _ok({"error": str(e), "table": table})
    finally:
        con.close()
    return _ok(rows)


# --------------------------------------------------------------------------- #
# Excel (data/excel/*.xlsx) — matrice de cellules brutes
# --------------------------------------------------------------------------- #
@tool("xlsx_sheet",
      "Retourne la matrice de cellules (lignes de valeurs) de la feuille active d'un .xlsx "
      "de data/excel/. Param: filename (str, ex. 'finances_summary.xlsx').",
      {"filename": str})
async def xlsx_sheet(args) -> dict:
    filename = (args or {}).get("filename", "")
    path = DATA / "excel" / Path(filename).name
    if not path.exists():
        avail = [p.name for p in (DATA / "excel").glob("*.xlsx")]
        return _ok({"error": "fichier introuvable", "filename": filename, "available": avail})
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = [[c for c in row] for row in ws.iter_rows(values_only=True)]
    return _ok({"filename": path.name, "sheet": ws.title, "rows": rows})


# --------------------------------------------------------------------------- #
# PDF (data/pdfs/*.pdf) — texte brut extrait
# --------------------------------------------------------------------------- #
@tool("pdf_text",
      "Retourne le texte brut (lignes) d'un PDF de data/pdfs/. L'agent y lit lui-même les "
      "paires Clé/Valeur ET les termes SLA. Param: filename (str) — ou vide pour la liste.",
      {"filename": str})
async def pdf_text(args) -> dict:
    filename = (args or {}).get("filename", "")
    if not filename:
        return _ok({"available": [p.name for p in sorted((DATA / "pdfs").glob("*.pdf"))]})
    path = DATA / "pdfs" / Path(filename).name
    if not path.exists():
        avail = [p.name for p in sorted((DATA / "pdfs").glob("*.pdf"))]
        return _ok({"error": "fichier introuvable", "filename": filename, "available": avail})
    reader = PdfReader(str(path))
    text = "\n".join((p.extract_text() or "") for p in reader.pages)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return _ok({"filename": path.name, "lines": lines})


# --------------------------------------------------------------------------- #
# Emails bruts (.eml) — texte RFC822 BRUT (en-têtes + corps)
# --------------------------------------------------------------------------- #
@tool("eml_raw",
      "Retourne le contenu TEXTE BRUT d'un .eml de data/emails/raw/ (en-têtes + corps "
      "lisibles ; l'agent y lit signatures '— Poste' et escalades). Param: filename (str, "
      "ex. 'EM-003.eml') — ou vide pour la liste des fichiers.",
      {"filename": str})
async def eml_raw(args) -> dict:
    filename = (args or {}).get("filename", "")
    raw_dir = DATA / "emails" / "raw"
    if not filename:
        return _ok({"available": [p.name for p in sorted(raw_dir.glob("*.eml"))]})
    path = raw_dir / Path(filename).name
    if not path.exists():
        avail = [p.name for p in sorted(raw_dir.glob("*.eml"))]
        return _ok({"error": "fichier introuvable", "filename": filename, "available": avail})
    return _ok(path.read_text(encoding="utf-8", errors="replace"))


# --------------------------------------------------------------------------- #
# Calculatrices pures (pas des réponses)
# --------------------------------------------------------------------------- #
@tool("name_similarity",
      "Calculatrice : ratio de similarité difflib (0..1) entre deux chaînes (minuscule). "
      "Ne dit PAS quoi fusionner — l'agent décide. Params: a (str), b (str).",
      {"a": str, "b": str})
async def name_similarity(args) -> dict:
    a = (args or {}).get("a", "") or ""
    b = (args or {}).get("b", "") or ""
    ratio = SequenceMatcher(None, a.strip().lower(), b.strip().lower()).ratio()
    return _ok({"a": a, "b": b, "ratio": round(ratio, 4)})


@tool("sum_amounts",
      "Calculatrice : somme une liste de montants numériques. Ne dit PAS ce qu'est le CA — "
      "l'agent décide quoi sommer. Param: amounts (liste de nombres).",
      {"amounts": list})
async def sum_amounts(args) -> dict:
    amounts = (args or {}).get("amounts", []) or []
    total = 0.0
    bad = []
    for x in amounts:
        try:
            total += float(x)
        except (TypeError, ValueError):
            bad.append(x)
    out = {"count": len(amounts), "total": round(total, 2)}
    if bad:
        out["ignored_non_numeric"] = bad
    return _ok(out)


ALL_TOOLS = [
    sqlite_tables, sqlite_rows, xlsx_sheet, pdf_text, eml_raw,
    name_similarity, sum_amounts,
]

# noms exposés aux passes (namespace SDK = mcp__<server>__<tool>)
READERS_SERVER_NAME = "readers"
TOOL_NAMES = {
    "sqlite_tables": f"mcp__{READERS_SERVER_NAME}__sqlite_tables",
    "sqlite_rows": f"mcp__{READERS_SERVER_NAME}__sqlite_rows",
    "xlsx_sheet": f"mcp__{READERS_SERVER_NAME}__xlsx_sheet",
    "pdf_text": f"mcp__{READERS_SERVER_NAME}__pdf_text",
    "eml_raw": f"mcp__{READERS_SERVER_NAME}__eml_raw",
    "name_similarity": f"mcp__{READERS_SERVER_NAME}__name_similarity",
    "sum_amounts": f"mcp__{READERS_SERVER_NAME}__sum_amounts",
}


def readers_server():
    """Serveur MCP en-process exposant les readers aux agents."""
    return create_sdk_mcp_server(READERS_SERVER_NAME, "1.0.0", tools=ALL_TOOLS)
