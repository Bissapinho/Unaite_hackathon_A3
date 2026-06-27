"""Serveur MCP mock (LECTURE SEULE) pour le TMS Dashdoc.

Transport: stdio. Lit data/dashdoc/dashdoc_dump.json au démarrage et
expose des outils de consultation des transports, vehicules, chauffeurs
et transporteurs.
"""

import json
import pathlib

from mcp.server.fastmcp import FastMCP

ROOT = pathlib.Path(__file__).resolve().parents[1]
DUMP_PATH = ROOT / "data" / "dashdoc" / "dashdoc_dump.json"


def _load() -> dict:
    """Charge le dump Dashdoc depuis le disque (une fois, en cache module)."""
    with DUMP_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


_DATA = _load()

mcp = FastMCP("dashdoc-tms")


# --- Fonctions testables (appelees par les @mcp.tool ci-dessous) -------------

def _list_transports() -> list:
    return _DATA.get("transports", [])


def _get_transport(uid: str) -> dict:
    for transport in _DATA.get("transports", []):
        if transport.get("uid") == uid:
            return transport
    return {"error": "not_found", "resource": "transport", "uid": uid}


def _list_vehicles() -> list:
    return _DATA.get("vehicles", [])


def _list_drivers() -> list:
    return _DATA.get("drivers", [])


def _list_carriers() -> list:
    return _DATA.get("carriers", [])


# --- Outils MCP --------------------------------------------------------------

@mcp.tool()
def list_transports() -> list:
    """Liste tous les transports du TMS (uid, status, adresses, transporteur,
    vehicule demande, livraisons, tracking/eta, chaine du froid)."""
    return _list_transports()


@mcp.tool()
def get_transport(uid: str) -> dict:
    """Retourne le transport dont l'uid correspond. Renvoie un objet d'erreur
    structure {error, resource, uid} si aucun transport ne correspond."""
    return _get_transport(uid)


@mcp.tool()
def list_vehicles() -> list:
    """Liste la flotte de vehicules (license_plate, type, year, is_refrigerated)."""
    return _list_vehicles()


@mcp.tool()
def list_drivers() -> list:
    """Liste les chauffeurs (driver_id, name, certifications)."""
    return _list_drivers()


@mcp.tool()
def list_carriers() -> list:
    """Liste les transporteurs (carrier_id, name, service_type, reliability_score)."""
    return _list_carriers()


if __name__ == "__main__":
    mcp.run()
