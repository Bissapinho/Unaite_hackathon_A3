"""Serveur MCP mock (LECTURE SEULE) pour la boite email.

Transport: stdio. Lit data/emails/emails.json au demarrage et expose des
outils de consultation et de recherche des emails.
"""

import json
import pathlib

from mcp.server.fastmcp import FastMCP

ROOT = pathlib.Path(__file__).resolve().parents[1]
DUMP_PATH = ROOT / "data" / "emails" / "emails.json"


def _load() -> list:
    """Charge le dump emails depuis le disque (une fois, en cache module)."""
    with DUMP_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


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
