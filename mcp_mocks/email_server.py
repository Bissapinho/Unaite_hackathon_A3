"""Serveur MCP mock (LECTURE SEULE) pour la boite email.

Transport: stdio. Parse les .eml bruts de data/emails/raw/ au demarrage
(via le parser eml_to_json) et expose des outils de consultation et de
recherche des emails. Il n'y a plus de emails.json : les .eml sont la
source de verite (l'extraction se fait depuis l'email brut, comme en vrai).
"""

import pathlib
import sys

from mcp.server.fastmcp import FastMCP

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.emails.eml_to_json import load_emails  # noqa: E402

RAW_DIR = ROOT / "data" / "emails" / "raw"


def _load() -> list:
    """Charge les emails en parsant les .eml bruts (une fois, en cache module)."""
    return load_emails(RAW_DIR)


_DATA = _load()

mcp = FastMCP("email-inbox")


# --- Fonctions testables -----------------------------------------------------

def _list_emails() -> list:
    return _DATA


def _get_email(id: str) -> dict:
    for email in _DATA:
        if email.get("id") == id:
            return email
    return {"error": "not_found", "resource": "email", "id": id}


def _search_emails(query: str) -> list:
    needle = (query or "").lower()
    results = []
    for email in _DATA:
        haystack = " ".join([
            str(email.get("subject", "")),
            str(email.get("body", "")),
            str(email.get("from", "")),
        ]).lower()
        if needle in haystack:
            results.append(email)
    return results


# --- Outils MCP --------------------------------------------------------------

@mcp.tool()
def list_emails() -> list:
    """Liste tous les emails (id, from, to, subject, body, received_at, labels)."""
    return _list_emails()


@mcp.tool()
def get_email(id: str) -> dict:
    """Retourne l'email dont l'id correspond, ou un objet d'erreur structure
    {error, resource, id} si absent."""
    return _get_email(id)


@mcp.tool()
def search_emails(query: str) -> list:
    """Recherche insensible a la casse dans subject + body + from. Retourne la
    liste des emails correspondants (liste vide si aucun)."""
    return _search_emails(query)


if __name__ == "__main__":
    mcp.run()
