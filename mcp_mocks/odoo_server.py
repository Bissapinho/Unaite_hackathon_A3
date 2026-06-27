"""Serveur MCP mock (LECTURE SEULE) pour l'ERP Odoo.

Transport: stdio. Lit data/odoo/odoo_dump.json au demarrage et expose des
outils de consultation des partenaires, commandes, factures, produits et
fournisseurs.
"""

import json
import pathlib

from mcp.server.fastmcp import FastMCP

ROOT = pathlib.Path(__file__).resolve().parents[1]
DUMP_PATH = ROOT / "data" / "odoo" / "odoo_dump.json"


def _load() -> dict:
    """Charge le dump Odoo depuis le disque (une fois, en cache module)."""
    with DUMP_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


_DATA = _load()

mcp = FastMCP("odoo-erp")


# --- Fonctions testables -----------------------------------------------------

def _list_partners() -> list:
    return _DATA.get("res.partner", [])


def _get_partner(partner_id: str) -> dict:
    for partner in _DATA.get("res.partner", []):
        if partner.get("partner_id") == partner_id:
            return partner
    return {"error": "not_found", "resource": "res.partner", "partner_id": partner_id}


def _list_sale_orders() -> list:
    return _DATA.get("sale.order", [])


def _list_invoices() -> list:
    return _DATA.get("account.move", [])


def _get_invoice(move_id: str) -> dict:
    for move in _DATA.get("account.move", []):
        if move.get("move_id") == move_id:
            return move
    return {"error": "not_found", "resource": "account.move", "move_id": move_id}


def _list_products() -> list:
    return _DATA.get("product.product", [])


def _list_suppliers() -> list:
    return _DATA.get("res.partner.suppliers", [])


# --- Outils MCP --------------------------------------------------------------

@mcp.tool()
def list_partners() -> list:
    """Liste les partenaires clients res.partner (partner_id, name,
    customer_rank, supplier_rank, industry_id, category, user_id,
    x_strategic_value)."""
    return _list_partners()


@mcp.tool()
def get_partner(partner_id: str) -> dict:
    """Retourne le partenaire dont partner_id correspond, ou un objet d'erreur
    structure {error, resource, partner_id} si absent."""
    return _get_partner(partner_id)


@mcp.tool()
def list_sale_orders() -> list:
    """Liste les commandes de vente sale.order (order_id, partner_id,
    client_order_ref, date_order, state)."""
    return _list_sale_orders()


@mcp.tool()
def list_invoices() -> list:
    """Liste les factures account.move (move_id, invoice_origin, partner_id,
    amount_total, currency_id, payment_state)."""
    return _list_invoices()


@mcp.tool()
def get_invoice(move_id: str) -> dict:
    """Retourne la facture account.move dont move_id correspond, ou un objet
    d'erreur structure {error, resource, move_id} si absente."""
    return _get_invoice(move_id)


@mcp.tool()
def list_products() -> list:
    """Liste les produits product.product (product_id, name, categ_id,
    x_temp_min, x_temp_max, list_price)."""
    return _list_products()


@mcp.tool()
def list_suppliers() -> list:
    """Liste les fournisseurs res.partner.suppliers (partner_id, name,
    customer_rank, supplier_rank, category, property_payment_term_id)."""
    return _list_suppliers()


if __name__ == "__main__":
    mcp.run()
