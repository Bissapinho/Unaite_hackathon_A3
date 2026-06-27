"""sources.py — lecture + normalisation de CHAQUE source (Système A, étage 1).

Ce module ne fait QUE lire les sources publiées et renommer leurs champs vers le
vocabulaire canonique (cf. mapping de DATA_README.md). Il ne crée ni entité ni
relation : il rend des enregistrements bruts normalisés, prêts pour resolve.py /
build_ontology.py.

Garde-fou (CLAUDE §9) : ce fichier n'importe JAMAIS data.canonical ni ne lit le
manifest de scénario. Les emails sont chargés via le parser de référence
data/emails/eml_to_json.py (autorisé pour l'oracle).
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import openpyxl
from pypdf import PdfReader

# data.emails.eml_to_json est un OUTIL de référence : l'oracle a le droit de s'en
# servir comme bibliothèque (cf. CLAUDE §9). Ce n'est PAS canonical.
from data.emails.eml_to_json import load_emails

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


# --------------------------------------------------------------------------- #
# ERP Odoo
# --------------------------------------------------------------------------- #
_PAY_STATE_TO_STATUS = {"not_paid": "Pending", "paid": "Paid"}


def load_odoo() -> dict:
    """res.partner (clients + fournisseurs), sale.order, account.move,
    product.product, account.payment.term -> champs canoniques."""
    raw = json.loads((DATA / "odoo" / "odoo_dump.json").read_text(encoding="utf-8"))

    payment_terms = {pt["days"]: pt["name"] for pt in raw.get("account.payment.term", [])}

    customers = []
    for p in raw["res.partner"]:
        if p.get("customer_rank", 0) > 0:
            customers.append({
                "customer_id": p["partner_id"],
                "name": p["name"],
                "priority_tier": p.get("category"),
                "account_manager": p.get("user_id"),
                "strategic_value": p.get("x_strategic_value"),
                "industry": p.get("industry_id"),
            })

    suppliers = []
    for p in raw.get("res.partner.suppliers", []):
        days = p.get("property_payment_term_id")
        suppliers.append({
            "supplier_id": p["partner_id"],
            "name": p["name"],
            "category": p.get("category"),
            "payment_term_days": days,
            "payment_term_name": payment_terms.get(days),
        })

    orders = [{
        "order_id": o["order_id"],
        "customer_id": o["partner_id"],
        "po_number": o.get("client_order_ref"),
        "order_date": o.get("date_order"),
        "status": o.get("state"),
    } for o in raw["sale.order"]]

    invoices = [{
        "invoice_id": m["move_id"],
        "po_number": m.get("invoice_origin"),
        "customer_id": m.get("partner_id"),
        "amount": m.get("amount_total"),
        "currency": m.get("currency_id"),
        "status": _PAY_STATE_TO_STATUS.get(m.get("payment_state"), m.get("payment_state")),
    } for m in raw["account.move"]]

    products = [{
        "sku": p["product_id"],
        "name": p["name"],
        "category": p.get("categ_id"),
        "temperature_min": p.get("x_temp_min"),
        "temperature_max": p.get("x_temp_max"),
        "unit_value": p.get("list_price"),
    } for p in raw["product.product"]]

    return {
        "customers": customers,
        "suppliers": suppliers,
        "orders": orders,
        "invoices": invoices,
        "products": products,
        "payment_terms": raw.get("account.payment.term", []),
    }


# --------------------------------------------------------------------------- #
# TMS Dashdoc
# --------------------------------------------------------------------------- #
_WH_RE = re.compile(r"(WH-\d+)")


def load_dashdoc() -> dict:
    """transports, vehicles, drivers, carriers -> champs canoniques.

    Le transport ne porte PAS d'order_id (trou de source assumé : seul SH-2049 est
    relié à sa commande, via le PDF DeliveryNote). Le transporteur est référencé par
    NOM (carrier.name) ; l'entrepôt d'origine est encodé dans loading_address
    ('Paris WH-1, Paris')."""
    raw = json.loads((DATA / "dashdoc" / "dashdoc_dump.json").read_text(encoding="utf-8"))

    warehouses = {}  # warehouse_id -> {name, city}
    transports = []
    for t in raw["transports"]:
        loading = t.get("loading_address", "")
        wh_name = loading.split(",")[0].strip() if loading else None
        wh_city = loading.split(",")[1].strip() if loading and "," in loading else None
        m = _WH_RE.search(loading or "")
        wh_id = m.group(1) if m else None
        if wh_id and wh_id not in warehouses:
            warehouses[wh_id] = {"warehouse_id": wh_id, "name": wh_name, "city": wh_city}

        setpoint = t.get("temperature_setpoint") or {}
        transports.append({
            "shipment_id": t["uid"],
            "status": t.get("status"),
            "origin_warehouse": wh_id,
            "origin_address": loading,
            "destination": t.get("unloading_address"),
            "carrier_name": (t.get("carrier") or {}).get("name"),
            "requested_vehicle": t.get("requested_vehicle"),
            "temperature_controlled": bool(t.get("is_cold_chain")),
            "temperature_min": setpoint.get("min"),
            "temperature_max": setpoint.get("max"),
            "estimated_arrival": (t.get("tracking") or {}).get("eta"),
            "items": [{"sku": d["sku"], "quantity": d["quantity"]}
                      for d in t.get("deliveries", [])],
        })

    vehicles = [{
        "license_plate": v["license_plate"],
        "type": v.get("type"),
        "year": v.get("year"),
        "is_refrigerated": bool(v.get("is_refrigerated")),
        "carrier_id": v.get("carrier_id"),
    } for v in raw["vehicles"]]

    drivers = [{
        "driver_id": d["driver_id"],
        "name": d["name"],
        "certifications": d.get("certifications", []),
        "carrier_id": d.get("carrier_id"),
    } for d in raw["drivers"]]

    carriers = [{
        "carrier_id": c["carrier_id"],
        "name": c["name"],
        "service_type": c.get("service_type"),
        "reliability_score": c.get("reliability_score"),
    } for c in raw["carriers"]]

    return {
        "transports": transports,
        "vehicles": vehicles,
        "drivers": drivers,
        "carriers": carriers,
        "warehouses": list(warehouses.values()),
    }


# --------------------------------------------------------------------------- #
# Base SQLite annexe
# --------------------------------------------------------------------------- #
def load_sqlite() -> dict:
    """customer_claims, sla_penalty_log, legacy_contacts."""
    con = sqlite3.connect(DATA / "db" / "annex.db")
    con.row_factory = sqlite3.Row
    try:
        def rows(table):
            return [dict(r) for r in con.execute(f"SELECT * FROM {table}").fetchall()]
        return {
            "customer_claims": rows("customer_claims"),
            "sla_penalty_log": rows("sla_penalty_log"),
            "legacy_contacts": rows("legacy_contacts"),
        }
    finally:
        con.close()


# --------------------------------------------------------------------------- #
# Excel
# --------------------------------------------------------------------------- #
def _ws_rows(path: Path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    return list(ws.iter_rows(values_only=True))


def _parse_money(val) -> int | None:
    """'€1,689,940' / '€2,400' -> int ; nombres déjà numériques passent tels quels."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return int(val)
    digits = re.sub(r"[^\d]", "", str(val))
    return int(digits) if digits else None


def _parse_pct(val) -> float | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    m = re.search(r"([\d.]+)", str(val))
    return float(m.group(1)) / 100.0 if m else None


def load_excel() -> dict:
    xdir = DATA / "excel"

    # --- annuaire interne (SANS colonne manager) ---
    emp_rows = _ws_rows(xdir / "company_directory.xlsx")
    employees = []
    for r in emp_rows[1:]:
        if not r or not r[0]:
            continue
        employees.append({
            "employee_id": r[0], "full_name": r[1], "role_title": r[2],
            "org_unit": r[3], "email": r[4], "hire_date": str(r[5]) if r[5] else None,
        })

    # --- liste de priorité client ---
    prio_rows = _ws_rows(xdir / "customer_priority_list.xlsx")
    priority = []
    for r in prio_rows[1:]:
        if not r or not r[0]:
            continue
        priority.append({
            "customer_name": r[0], "priority_tier": r[1],
            "account_manager": r[2], "escalation_required": r[3],
        })

    # --- inventaire ---
    inv_rows = _ws_rows(xdir / "warehouse_inventory_snapshot.xlsx")
    inventory = []
    for r in inv_rows[1:]:
        if not r or not r[0]:
            continue
        inventory.append({
            "warehouse_id": r[0], "sku": r[1],
            "available_units": r[2], "reserved_units": r[3],
        })

    # --- matrice transporteurs de secours ---
    bk_rows = _ws_rows(xdir / "carrier_backup_matrix.xlsx")
    backup = []
    for r in bk_rows[1:]:
        if not r or not r[0]:
            continue
        backup.append({
            "route": r[0], "backup_carrier": r[1],
            "max_cold_chain_capacity": r[2], "emergency_rate": _parse_money(r[3]),
        })

    # --- finances : 2 blocs (agrégats société + concentration CA) ---
    fin_rows = _ws_rows(xdir / "finances_summary.xlsx")
    summary = {}
    concentration = []
    mode = "summary"
    for r in fin_rows:
        if not r or all(c is None for c in r):
            continue
        key = r[0]
        if key == "Concentration du CA par client":
            mode = "concentration"
            continue
        if mode == "concentration":
            if key == "Client":  # en-tête du bloc concentration
                continue
            concentration.append({
                "customer_name": key, "revenue": _parse_money(r[1]),
                "share_pct": _parse_pct(r[2]),
            })
        else:
            summary[key] = r[1]

    return {
        "employees": employees,
        "priority": priority,
        "inventory": inventory,
        "backup": backup,
        "finances_summary": summary,
        "finances_concentration": concentration,
    }


# --------------------------------------------------------------------------- #
# PDF
# --------------------------------------------------------------------------- #
def load_pdfs() -> list[dict]:
    """Chaque PDF -> {doc_name, lines, fields} ; fields = paires 'Clé: Valeur'."""
    docs = []
    for path in sorted((DATA / "pdfs").glob("*.pdf")):
        reader = PdfReader(str(path))
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        fields = {}
        for ln in lines:
            if ": " in ln:
                k, v = ln.split(": ", 1)
                fields[k.strip()] = v.strip()
        docs.append({"doc_name": path.stem, "title": lines[0] if lines else "",
                     "lines": lines, "fields": fields})
    return docs


# --------------------------------------------------------------------------- #
# Emails (.eml -> via le parser de référence)
# --------------------------------------------------------------------------- #
def load_email_messages() -> list[dict]:
    return load_emails(DATA / "emails" / "raw")


# --------------------------------------------------------------------------- #
# Agrégateur
# --------------------------------------------------------------------------- #
def load_all() -> dict:
    odoo = load_odoo()
    dashdoc = load_dashdoc()
    sqlite_data = load_sqlite()
    excel = load_excel()
    pdfs = load_pdfs()
    emails = load_email_messages()
    return {
        "odoo": odoo,
        "dashdoc": dashdoc,
        "sqlite": sqlite_data,
        "excel": excel,
        "pdfs": pdfs,
        "emails": emails,
    }


if __name__ == "__main__":
    data = load_all()
    print("odoo: customers", len(data["odoo"]["customers"]),
          "suppliers", len(data["odoo"]["suppliers"]),
          "orders", len(data["odoo"]["orders"]),
          "invoices", len(data["odoo"]["invoices"]),
          "products", len(data["odoo"]["products"]))
    print("dashdoc: transports", len(data["dashdoc"]["transports"]),
          "vehicles", len(data["dashdoc"]["vehicles"]),
          "drivers", len(data["dashdoc"]["drivers"]),
          "carriers", len(data["dashdoc"]["carriers"]),
          "warehouses", len(data["dashdoc"]["warehouses"]))
    print("sqlite: claims", len(data["sqlite"]["customer_claims"]),
          "penalties", len(data["sqlite"]["sla_penalty_log"]),
          "legacy", len(data["sqlite"]["legacy_contacts"]))
    print("excel: employees", len(data["excel"]["employees"]),
          "priority", len(data["excel"]["priority"]),
          "inventory", len(data["excel"]["inventory"]),
          "backup", len(data["excel"]["backup"]),
          "concentration", len(data["excel"]["finances_concentration"]))
    print("pdfs", [d["doc_name"] for d in data["pdfs"]])
    print("emails", len(data["emails"]))
