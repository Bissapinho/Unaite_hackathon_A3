"""generate_pdfs.py — Génère 4 PDF à texte extractible depuis la source de vérité.

Brique "documents PDF" du scénario SH-2049. Tout vient de data/canonical.py.
Aucune valeur métier inventée. Texte extractible (drawString/Paragraph, pas d'image).
Les caractères spéciaux (€, °C) doivent ressortir à la ré-extraction.

Lançable seul :  .venv/bin/python data/pdfs/generate_pdfs.py
Idempotent : ré-écrit les mêmes 4 fichiers à chaque exécution.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from data import canonical as C  # noqa: E402

from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402

PDF_DIR = ROOT / "data" / "pdfs"

# Helvetica (police standard reportlab) utilise l'encodage WinAnsi : € et ° y sont
# présents et donc extractibles en tant que vrais caractères texte.
FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"


# --------------------------------------------------------------------------- #
# Helpers de récupération depuis canonical
# --------------------------------------------------------------------------- #
def _find(records, key, value):
    for r in records:
        if r.get(key) == value:
            return r
    raise KeyError(f"{key}={value} introuvable dans canonical")


def _fmt_eur(amount: int) -> str:
    """186000 -> '186,000' (séparateur de milliers à l'anglaise, comme la spec)."""
    return f"{amount:,}"


# --------------------------------------------------------------------------- #
# Rendu d'une page simple à partir de lignes (titre + (label, value) ...)
# --------------------------------------------------------------------------- #
def _write_doc(path: pathlib.Path, title: str, intro: str, lines: list[str]) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    x = 25 * mm
    y = height - 30 * mm

    c.setFont(FONT_BOLD, 16)
    c.drawString(x, y, title)
    y -= 12 * mm

    c.setFont(FONT, 11)
    if intro:
        for chunk in intro.split("\n"):
            c.drawString(x, y, chunk)
            y -= 7 * mm
        y -= 3 * mm

    for line in lines:
        c.setFont(FONT, 11)
        c.drawString(x, y, line)
        y -= 8 * mm

    c.showPage()
    c.save()


# --------------------------------------------------------------------------- #
# Construction des 4 documents
# --------------------------------------------------------------------------- #
def build_purchase_order() -> pathlib.Path:
    order = _find(C.ORDERS, "po_number", "PO-8821")
    customer = C.CUSTOMER_BY_ID[order["customer_id"]]
    item = _find(C.SHIPMENT_ITEMS, "shipment_id", "SH-2049")
    sku = item["sku"]
    qty = item["quantity"]
    contract = _find(C.CONTRACTS, "customer_id", customer["customer_id"])
    deadline = contract["sla_deadline"]  # "18:00"
    shipment = _find(C.SHIPMENTS, "shipment_id", "SH-2049")
    destination = shipment["destination"]

    path = PDF_DIR / "PO-8821-MedPharma.pdf"
    _write_doc(
        path,
        title="Purchase Order",
        intro="",
        lines=[
            f"PO Number: {order['po_number']}",
            f"Customer: {customer['name']}",
            f"SKU: {sku}",
            f"Quantity: {qty} units",
            f"Required delivery: today before {deadline}",
            f"Destination: {destination}",
        ],
    )
    return path


def build_invoice() -> pathlib.Path:
    invoice = _find(C.INVOICES, "invoice_id", "INV-7742")
    order = C.ORDER_BY_ID[invoice["order_id"]]
    customer = C.CUSTOMER_BY_ID[order["customer_id"]]
    amount = invoice["amount"]  # 186000

    path = PDF_DIR / "INV-7742-MedPharma.pdf"
    _write_doc(
        path,
        title="Invoice",
        intro="",
        lines=[
            f"Invoice: {invoice['invoice_id']}",
            f"Related PO: {order['po_number']}",
            f"Customer: {customer['name']}",
            f"Amount: €{_fmt_eur(amount)}",
            f"Status: {invoice['status']}",
        ],
    )
    return path


def build_sla() -> pathlib.Path:
    customer = _find(C.CUSTOMERS, "name", "MedPharma")
    product = _find(C.PRODUCTS, "sku", "PHARMA-22")
    tmin = product["temperature_min"]  # 2
    tmax = product["temperature_max"]  # 8
    contract = _find(C.CONTRACTS, "customer_id", customer["customer_id"])
    deadline = contract["sla_deadline"]  # "18:00"
    penalty = contract["late_penalty_per_hour"]  # 7000

    path = PDF_DIR / "SLA-MedPharma-ColdChain.pdf"
    _write_doc(
        path,
        title="Service Level Agreement — Cold Chain",
        intro="",
        lines=[
            f"Customer: {customer['name']}",
            f"Cold-chain products must remain between {tmin}°C and {tmax}°C.",
            f"Delivery deadline: {deadline} local time.",
            f"Late penalty: €{_fmt_eur(penalty)} per hour.",
            "Critical shipments must be escalated to the account manager.",
        ],
    )
    return path


def build_delivery_note() -> pathlib.Path:
    shipment = _find(C.SHIPMENTS, "shipment_id", "SH-2049")
    order = C.ORDER_BY_ID[shipment["order_id"]]
    item = _find(C.SHIPMENT_ITEMS, "shipment_id", "SH-2049")
    carrier = C.CARRIER_BY_ID[shipment["carrier_id"]]
    warehouse = C.WAREHOUSE_BY_ID[shipment["origin_warehouse"]]

    path = PDF_DIR / "DeliveryNote-SH-2049.pdf"
    _write_doc(
        path,
        title="Delivery Note",
        intro="",
        lines=[
            f"Shipment: {shipment['shipment_id']}",
            f"PO: {order['po_number']}",
            f"SKU: {item['sku']}",
            f"Quantity: {item['quantity']}",
            f"Carrier: {carrier['name']}",
            f"Origin: {warehouse['name']}",
            f"Destination: {shipment['destination']}",
        ],
    )
    return path


def main() -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    paths = [
        build_purchase_order(),
        build_invoice(),
        build_sla(),
        build_delivery_note(),
    ]
    print("PDF generes dans", PDF_DIR)
    for p in paths:
        print("  -", p.name)


if __name__ == "__main__":
    main()
