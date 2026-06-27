"""build_odoo.py — génère odoo_dump.json (vision ERP finance/commercial, vocabulaire Odoo-like).

Toutes les valeurs métier proviennent de data/canonical.py (source de vérité unique).
Aucune valeur n'est inventée ici : on se contente de ré-exprimer le canonique dans le
vocabulaire Odoo. Les clés internes `_scenario*` ne sont jamais recopiées.
"""

from __future__ import annotations

import json
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from data import canonical as C

# Mapping statut facture canonique -> payment_state Odoo
_PAYMENT_STATE = {"Pending": "not_paid", "Paid": "paid"}


def build_dump() -> dict:
    # res.partner (clients)
    res_partner = [
        {
            "partner_id": cust["customer_id"],
            "name": cust["name"],
            "customer_rank": 1,
            "supplier_rank": 0,
            "industry_id": cust["industry"],
            "category": cust["priority_tier"],
            "user_id": cust["account_manager"],
            "x_strategic_value": cust["strategic_value"],
        }
        for cust in C.CUSTOMERS
    ]

    # sale.order
    sale_order = [
        {
            "order_id": order["order_id"],
            "partner_id": order["customer_id"],
            "client_order_ref": order["po_number"],
            "date_order": order["order_date"],
            "state": order["status"],
        }
        for order in C.ORDERS
    ]

    # account.move (factures)
    account_move = []
    for inv in C.INVOICES:
        order = C.ORDER_BY_ID[inv["order_id"]]
        account_move.append({
            "move_id": inv["invoice_id"],
            "invoice_origin": order["po_number"],
            "partner_id": order["customer_id"],
            "amount_total": inv["amount"],
            "currency_id": inv["currency"],
            "payment_state": _PAYMENT_STATE[inv["status"]],
        })

    # product.product
    product_product = [
        {
            "product_id": prod["sku"],
            "name": prod["name"],
            "categ_id": prod["category"],
            "x_temp_min": prod["temperature_min"],
            "x_temp_max": prod["temperature_max"],
            "list_price": prod["unit_value"],
        }
        for prod in C.PRODUCTS
    ]

    # res.partner.suppliers (fournisseurs)
    res_partner_suppliers = [
        {
            "partner_id": sup["supplier_id"],
            "name": sup["name"],
            "customer_rank": 0,
            "supplier_rank": 1,
            "category": sup["category"],
            "property_payment_term_id": sup["payment_term_days"],
        }
        for sup in C.SUPPLIERS
    ]

    # account.payment.term
    account_payment_term = [
        {"name": term["name"], "days": term["days"]}
        for term in C.PAYMENT_TERMS
    ]

    return {
        "res.partner": res_partner,
        "sale.order": sale_order,
        "account.move": account_move,
        "product.product": product_product,
        "res.partner.suppliers": res_partner_suppliers,
        "account.payment.term": account_payment_term,
    }


def main() -> None:
    dump = build_dump()
    out_path = ROOT / "data" / "odoo" / "odoo_dump.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(dump, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {out_path}")
    for table, rows in dump.items():
        print(f"  {table}: {len(rows)} records")


if __name__ == "__main__":
    main()
