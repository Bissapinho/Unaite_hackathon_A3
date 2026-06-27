"""build_ontology.py — POINT D'ENTRÉE de l'oracle déterministe (Système A, étage 1).

Assemble les sources normalisées (sources.py), la résolution d'entités (resolve.py)
et l'organigramme reconstruit (orgchart.py) en `outputs/ontology.json`, au format du
CLAUDE §4 (3 couches : operational | hr | financial ; provenance complète :
sources + confidence + evidence + open_questions sur chaque entité ET relation).

Garde-fous (CLAUDE §9) : aucun import de data.canonical, aucune lecture du manifest
de scénario, aucun flag de scénario, aucun nœud « risque » / is_hot.
L'oracle publie un graphe FACTUEL ; les risques seront calculés par le Système B.

Usage : python -m system_a.build_ontology  ->  écrit outputs/ontology.json (idempotent).
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from system_a import orgchart, resolve, sources

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "ontology.json"

LAYER = {
    "Customer": "operational", "Supplier": "operational", "Product": "operational",
    "Warehouse": "operational", "Carrier": "operational", "Vehicle": "operational",
    "Driver": "operational", "Order": "operational", "PurchaseOrder": "operational",
    "Invoice": "operational", "Shipment": "operational", "Contract": "operational",
    "Claim": "operational", "PenaltyLogEntry": "operational", "Email": "operational",
    "Document": "operational",
    "Company": "hr", "Employee": "hr",
    "FinancialSummary": "financial", "RevenueConcentration": "financial",
    "CashflowGap": "financial",
}

_SH_RE = re.compile(r"\bSH-\d+\b")
_PO_RE = re.compile(r"\bPO-\d+\b")
_INV_RE = re.compile(r"\bINV-\d+\b")


def slug(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


class OntologyBuilder:
    def __init__(self):
        self.entities: dict[str, dict] = {}
        self.relationships: list[dict] = []
        self._rel_seen: set = set()

    # -- entités --
    def add_entity(self, id, type, name, attributes=None, sources=None,
                   confidence=0.95, evidence=None, open_questions=None):
        if id in self.entities:
            e = self.entities[id]
            for s in (sources or []):
                if s not in e["sources"]:
                    e["sources"].append(s)
            for ev in (evidence or []):
                if ev not in e["evidence"]:
                    e["evidence"].append(ev)
            for q in (open_questions or []):
                if q not in e["open_questions"]:
                    e["open_questions"].append(q)
            e["confidence"] = max(e["confidence"], confidence)
            if attributes:
                e["attributes"].update({k: v for k, v in attributes.items() if v is not None})
            return id
        self.entities[id] = {
            "id": id, "type": type, "name": name, "layer": LAYER[type],
            "attributes": {k: v for k, v in (attributes or {}).items() if v is not None},
            "sources": list(sources or []),
            "confidence": confidence,
            "evidence": list(evidence or []),
            "open_questions": list(open_questions or []),
        }
        return id

    # -- relations --
    def add_rel(self, source, target, type, confidence=0.95, evidence=None,
                open_questions=None):
        key = (source, target, type)
        if key in self._rel_seen:
            return
        if source not in self.entities or target not in self.entities:
            return  # on ne crée jamais un lien vers un nœud inexistant
        self._rel_seen.add(key)
        self.relationships.append({
            "source": source, "target": target, "type": type,
            "confidence": confidence,
            "evidence": list(evidence or []),
            "open_questions": list(open_questions or []),
        })


def build() -> dict:
    data = sources.load_all()
    odoo = data["odoo"]
    dd = data["dashdoc"]
    sq = data["sqlite"]
    xl = data["excel"]
    pdfs = data["pdfs"]
    emails = data["emails"]

    b = OntologyBuilder()

    # index pratiques
    cust_node: dict[str, str] = {}      # customer_id -> node id
    cust_name_node: dict[str, str] = {}  # name -> node id
    prod_node: dict[str, str] = {}      # sku -> node id
    carrier_id_node: dict[str, str] = {}   # carrier_id -> node id
    carrier_name_node: dict[str, str] = {}  # name -> node id
    wh_node: dict[str, str] = {}        # warehouse_id -> node id
    order_node: dict[str, str] = {}     # order_id -> node id
    po_node: dict[str, str] = {}        # po_number -> node id
    order_by_po: dict[str, dict] = {}   # po_number -> order record
    ship_node: dict[str, str] = {}      # shipment_id -> node id
    emp_node: dict[str, str] = {}       # employee_id -> node id

    # ----------------------------------------------------------------- #
    # CUSTOMERS (+ priorité Excel + résolution floue legacy)
    # ----------------------------------------------------------------- #
    prio_by_name = {p["customer_name"]: p for p in xl["priority"]}
    fuzzy = resolve.resolve_legacy_contacts(odoo["customers"], sq["legacy_contacts"])

    for c in odoo["customers"]:
        nid = f"customer:{slug(c['name'])}"
        cust_node[c["customer_id"]] = nid
        cust_name_node[c["name"]] = nid
        attrs = {
            "priority_tier": c.get("priority_tier"),
            "strategic_value": c.get("strategic_value"),
            "account_manager": c.get("account_manager"),
            "industry": c.get("industry"),
        }
        srcs = [f"odoo.res_partner:{c['customer_id']}"]
        evid = [f"odoo res.partner.name = '{c['name']}' (partner_id={c['customer_id']})"]
        conf = 0.95
        prio = prio_by_name.get(c["name"])
        if prio:
            srcs.append(f"excel.customer_priority_list:'{c['name']}'")
            evid.append(f"liste de priorité Excel : tier {prio['priority_tier']}, "
                        f"escalation={prio['escalation_required']}")
            attrs["escalation_required"] = (str(prio.get("escalation_required")).lower() == "yes")
            conf = 0.97
        oq = []
        for match in fuzzy.get(c["customer_id"], []):
            srcs.append(f"sqlite.legacy_contacts:{match['legacy_id']} ('{match['raw_name']}')")
            evid.append(f"rapprochement flou '{match['raw_name']}' -> '{c['name']}' "
                        f"({match['reason']})")
        b.add_entity(nid, "Customer", c["name"], attrs, srcs, conf, evid, oq)

    # ----------------------------------------------------------------- #
    # SUPPLIERS
    # ----------------------------------------------------------------- #
    for s in odoo["suppliers"]:
        nid = f"supplier:{slug(s['supplier_id'])}"
        b.add_entity(
            nid, "Supplier", s["name"],
            {"category": s.get("category"),
             "payment_term_days": s.get("payment_term_days"),
             "payment_term_name": s.get("payment_term_name")},
            [f"odoo.res_partner.suppliers:{s['supplier_id']}"], 0.95,
            [f"odoo res.partner (supplier_rank>0) name='{s['name']}', "
             f"payment_term={s.get('payment_term_days')}j"])

    # ----------------------------------------------------------------- #
    # PRODUCTS
    # ----------------------------------------------------------------- #
    for p in odoo["products"]:
        nid = f"product:{slug(p['sku'])}"
        prod_node[p["sku"]] = nid
        b.add_entity(
            nid, "Product", p["name"],
            {"sku": p["sku"], "category": p.get("category"),
             "temperature_min": p.get("temperature_min"),
             "temperature_max": p.get("temperature_max"),
             "unit_value": p.get("unit_value")},
            [f"odoo.product_product:{p['sku']}"], 0.95,
            [f"odoo product.product product_id={p['sku']} name='{p['name']}'"])

    # ----------------------------------------------------------------- #
    # WAREHOUSES (dashdoc loading_address ; recoupé par l'inventaire)
    # ----------------------------------------------------------------- #
    inv_wh_ids = {r["warehouse_id"] for r in xl["inventory"]}
    for w in dd["warehouses"]:
        nid = f"warehouse:{slug(w['warehouse_id'])}"
        wh_node[w["warehouse_id"]] = nid
        srcs = [f"dashdoc.transports.loading_address:{w['warehouse_id']}"]
        evid = [f"dashdoc loading_address '{w['name']}, {w['city']}' -> {w['warehouse_id']}"]
        if w["warehouse_id"] in inv_wh_ids:
            srcs.append(f"excel.warehouse_inventory_snapshot:{w['warehouse_id']}")
            evid.append(f"présent dans l'inventaire Excel ({w['warehouse_id']})")
        b.add_entity(nid, "Warehouse", w["name"],
                     {"city": w.get("city"), "warehouse_id": w["warehouse_id"]},
                     srcs, 0.95, evid)

    # ----------------------------------------------------------------- #
    # CARRIERS
    # ----------------------------------------------------------------- #
    for c in dd["carriers"]:
        nid = f"carrier:{slug(c['name'])}"
        carrier_id_node[c["carrier_id"]] = nid
        carrier_name_node[c["name"]] = nid
        b.add_entity(
            nid, "Carrier", c["name"],
            {"carrier_id": c["carrier_id"], "service_type": c.get("service_type"),
             "reliability_score": c.get("reliability_score")},
            [f"dashdoc.carriers:{c['carrier_id']}"], 0.95,
            [f"dashdoc carrier_id={c['carrier_id']} name='{c['name']}' "
             f"service={c.get('service_type')}"])

    # ----------------------------------------------------------------- #
    # VEHICLES  (Carrier operates Vehicle)
    # ----------------------------------------------------------------- #
    for v in dd["vehicles"]:
        nid = f"vehicle:{slug(v['license_plate'])}"
        b.add_entity(
            nid, "Vehicle", v["license_plate"],
            {"type": v.get("type"), "year": v.get("year"),
             "is_refrigerated": v.get("is_refrigerated")},
            [f"dashdoc.vehicles:{v['license_plate']}"], 0.95,
            [f"dashdoc vehicle license_plate={v['license_plate']} type={v.get('type')}"])
        carrier = carrier_id_node.get(v["carrier_id"])
        if carrier:
            b.add_rel(carrier, nid, "operates", 0.95,
                      [f"dashdoc vehicle.carrier_id = {v['carrier_id']}"])

    # ----------------------------------------------------------------- #
    # DRIVERS  (Carrier mandates Driver)
    # ----------------------------------------------------------------- #
    for d in dd["drivers"]:
        nid = f"driver:{slug(d['driver_id'])}"
        b.add_entity(
            nid, "Driver", d["name"],
            {"driver_id": d["driver_id"], "certifications": d.get("certifications", [])},
            [f"dashdoc.drivers:{d['driver_id']}"], 0.95,
            [f"dashdoc driver_id={d['driver_id']} name='{d['name']}' "
             f"certifications={d.get('certifications')}"])
        carrier = carrier_id_node.get(d["carrier_id"])
        if carrier:
            b.add_rel(carrier, nid, "mandates", 0.95,
                      [f"dashdoc driver.carrier_id = {d['carrier_id']}"])

    # ----------------------------------------------------------------- #
    # PURCHASE ORDERS + ORDERS  (Customer places PO ; PO creates Order)
    # ----------------------------------------------------------------- #
    for o in odoo["orders"]:
        onid = f"order:{slug(o['order_id'])}"
        order_node[o["order_id"]] = onid
        b.add_entity(
            onid, "Order", o["order_id"],
            {"status": o.get("status"), "order_date": o.get("order_date"),
             "po_number": o.get("po_number")},
            [f"odoo.sale_order:{o['order_id']}"], 0.95,
            [f"odoo sale.order order_id={o['order_id']} partner_id={o['customer_id']}"])

        po = o.get("po_number")
        cust = cust_node.get(o["customer_id"])
        if po:
            order_by_po[po] = o
            pnid = f"po:{slug(po)}"
            po_node[po] = pnid
            b.add_entity(
                pnid, "PurchaseOrder", po,
                {"po_number": po},
                [f"odoo.sale_order.client_order_ref:{o['order_id']}"], 0.95,
                [f"odoo sale.order.client_order_ref = '{po}' (commande {o['order_id']})"])
            if cust:
                b.add_rel(cust, pnid, "places", 0.95,
                          [f"odoo sale.order.partner_id={o['customer_id']} a pour "
                           f"client_order_ref '{po}'"])
            b.add_rel(pnid, onid, "creates", 0.95,
                      [f"odoo sale.order : client_order_ref '{po}' -> order {o['order_id']}"])

    # ----------------------------------------------------------------- #
    # INVOICES  (Invoice bills Order)
    # ----------------------------------------------------------------- #
    for inv in odoo["invoices"]:
        nid = f"invoice:{slug(inv['invoice_id'])}"
        po = inv.get("po_number")
        order = order_by_po.get(po)
        b.add_entity(
            nid, "Invoice", inv["invoice_id"],
            {"amount": inv.get("amount"), "currency": inv.get("currency"),
             "status": inv.get("status"), "po_number": po},
            [f"odoo.account_move:{inv['invoice_id']}"], 0.95,
            [f"odoo account.move move_id={inv['invoice_id']} amount_total={inv.get('amount')} "
             f"payment_state -> {inv.get('status')}, invoice_origin={po}"])
        if order:
            onid = order_node[order["order_id"]]
            b.add_rel(nid, onid, "bills", 0.95,
                      [f"odoo account.move.invoice_origin='{po}' = sale.order.client_order_ref "
                       f"(order {order['order_id']})"])

    # ----------------------------------------------------------------- #
    # SHIPMENTS  (operated_by / departs_from / contains)
    # ----------------------------------------------------------------- #
    for t in dd["transports"]:
        nid = f"shipment:{slug(t['shipment_id'])}"
        ship_node[t["shipment_id"]] = nid
        b.add_entity(
            nid, "Shipment", t["shipment_id"],
            {"status": t.get("status"), "destination": t.get("destination"),
             "temperature_controlled": t.get("temperature_controlled"),
             "temperature_min": t.get("temperature_min"),
             "temperature_max": t.get("temperature_max"),
             "estimated_arrival": t.get("estimated_arrival"),
             "requested_vehicle": t.get("requested_vehicle")},
            [f"dashdoc.transports:{t['shipment_id']}"], 0.95,
            [f"dashdoc transport uid={t['shipment_id']} status={t.get('status')} "
             f"carrier='{t.get('carrier_name')}'"])

        carrier = carrier_name_node.get(t.get("carrier_name"))
        if carrier:
            b.add_rel(nid, carrier, "operated_by", 0.95,
                      [f"dashdoc transport.carrier.name = '{t['carrier_name']}'"])
        wh = wh_node.get(t.get("origin_warehouse"))
        if wh:
            b.add_rel(nid, wh, "departs_from", 0.95,
                      [f"dashdoc loading_address '{t.get('origin_address')}' "
                       f"-> {t.get('origin_warehouse')}"])
        for item in t.get("items", []):
            prod = prod_node.get(item["sku"])
            if prod:
                b.add_rel(nid, prod, "contains", 0.95,
                          [f"dashdoc deliveries: sku={item['sku']} quantity={item['quantity']}"],
                          )
                # quantité portée sur l'arête
                b.relationships[-1].setdefault("attributes", {})["quantity"] = item["quantity"]

    # ----------------------------------------------------------------- #
    # INVENTORY  (Product stored_in Warehouse)
    # ----------------------------------------------------------------- #
    for r in xl["inventory"]:
        prod = prod_node.get(r["sku"])
        wh = wh_node.get(r["warehouse_id"])
        if prod and wh:
            b.add_rel(prod, wh, "stored_in", 0.95,
                      [f"excel inventory : {r['sku']} @ {r['warehouse_id']} "
                       f"available={r['available_units']} reserved={r['reserved_units']}"])
            b.relationships[-1].setdefault("attributes", {}).update(
                {"available_units": r["available_units"], "reserved_units": r["reserved_units"]})

    # ----------------------------------------------------------------- #
    # SHIPMENT <-> ORDER : SH-2049 SEULEMENT, via le PDF DeliveryNote
    # (trou de source assumé pour les 27 autres : aucun order_id en dashdoc)
    # ----------------------------------------------------------------- #
    pdf_by_name = {d["doc_name"]: d for d in pdfs}
    for d in pdfs:
        f = d["fields"]
        sh = f.get("Shipment")
        po = f.get("PO")
        if sh and po and sh in ship_node and po in order_by_po:
            order = order_by_po[po]
            b.add_rel(order_node[order["order_id"]], ship_node[sh], "fulfilled_by", 0.9,
                      [f"PDF {d['doc_name']} relie Shipment {sh} <-> PO {po}",
                       f"odoo : PO {po} -> commande {order['order_id']}"],
                      ["lien shipment<->order reconstruit via le bon de livraison PDF "
                       "(le TMS Dashdoc n'expose aucun order_id)"])

    # ----------------------------------------------------------------- #
    # CONTRACT  (depuis le PDF SLA ; trou de source : 1 seul contrat documenté)
    # ----------------------------------------------------------------- #
    sla = next((d for d in pdfs if "SLA" in d["doc_name"]), None)
    if sla:
        f = sla["fields"]
        cust_name = f.get("Customer")
        cust = cust_name_node.get(cust_name)
        # termes lus dans le texte du PDF
        penalty = None
        deadline = None
        tmin = tmax = None
        for ln in sla["lines"]:
            m = re.search(r"€?([\d,]+)\s*per hour", ln)
            if m:
                penalty = int(m.group(1).replace(",", ""))
            m = re.search(r"deadline:\s*([\d:]+)", ln, re.I)
            if m:
                deadline = m.group(1)
            m = re.search(r"between\s*(\d+)°C\s*and\s*(\d+)°C", ln)
            if m:
                tmin, tmax = int(m.group(1)), int(m.group(2))
        cid = "contract:ct-001"
        b.add_entity(
            cid, "Contract", "CT-001",
            {"customer_name": cust_name, "sla_deadline": deadline,
             "late_penalty_per_hour": penalty, "temperature_min": tmin,
             "temperature_max": tmax,
             "escalation_to_account_manager": any("escalated to the account manager" in ln.lower()
                                                   for ln in sla["lines"])},
            [f"pdf.{sla['doc_name']}"], 0.9,
            [f"PDF SLA : client {cust_name}, deadline {deadline}, pénalité €{penalty}/h, "
             f"plage {tmin}-{tmax}°C, escalade account manager"],
            ["numéro de contrat 'CT-001' non présent en source (les termes proviennent du "
             "PDF SLA ; les autres contrats de la PME ne sont exposés dans aucune source)"])
        # SLA porté en ATTRIBUTS du contrat (pas de nœud SLA séparé).
        if cust:
            b.add_rel(cust, cid, "governed_by", 0.9,
                      [f"PDF SLA nominatif pour le client {cust_name}"])

    # ----------------------------------------------------------------- #
    # CLAIMS + PENALTY LOG (SQLite)
    # ----------------------------------------------------------------- #
    for cl in sq["customer_claims"]:
        nid = f"claim:{cl['id']}"
        b.add_entity(
            nid, "Claim", f"Claim #{cl['id']} ({cl['type']})",
            {"type": cl.get("type"), "status": cl.get("status"),
             "opened_at": cl.get("opened_at"), "closed_at": cl.get("closed_at")},
            [f"sqlite.customer_claims:{cl['id']}"], 0.9,
            [f"sqlite customer_claims id={cl['id']} type={cl['type']} "
             f"customer_ref={cl.get('customer_ref')}"])
        cust = cust_node.get(cl.get("customer_ref"))
        if cust:
            b.add_rel(cust, nid, "filed", 0.9,
                      [f"sqlite customer_claims.customer_ref = {cl['customer_ref']}"])
        ship = ship_node.get(cl.get("shipment_ref"))
        if ship:
            b.add_rel(nid, ship, "concerns", 0.9,
                      [f"sqlite customer_claims.shipment_ref = {cl['shipment_ref']}"])

    for pen in sq["sla_penalty_log"]:
        nid = f"penalty:{pen['id']}"
        b.add_entity(
            nid, "PenaltyLogEntry", f"Penalty #{pen['id']} ({pen['month']})",
            {"hours_late": pen.get("hours_late"), "penalty_amount": pen.get("penalty_amount"),
             "month": pen.get("month")},
            [f"sqlite.sla_penalty_log:{pen['id']}"], 0.9,
            [f"sqlite sla_penalty_log id={pen['id']} hours_late={pen.get('hours_late')} "
             f"amount={pen.get('penalty_amount')}"])
        cust = cust_node.get(pen.get("customer_ref"))
        if cust:
            b.add_rel(cust, nid, "incurred", 0.9,
                      [f"sqlite sla_penalty_log.customer_ref = {pen['customer_ref']}"])
        ship = ship_node.get(pen.get("shipment_ref"))
        if ship:
            b.add_rel(nid, ship, "concerns", 0.9,
                      [f"sqlite sla_penalty_log.shipment_ref = {pen['shipment_ref']}"])

    # ----------------------------------------------------------------- #
    # EMAILS  (Email mentions Shipment/PO)
    # ----------------------------------------------------------------- #
    for m in emails:
        nid = f"email:{slug(m['id'])}"
        b.add_entity(
            nid, "Email", m.get("subject") or m["id"],
            {"email_id": m["id"], "from": m.get("from"), "to": m.get("to"),
             "received_at": m.get("received_at"), "labels": m.get("labels", [])},
            [f"email:{m['id']}"], 0.9,
            [f".eml {m['id']} subject='{m.get('subject')}' from={m.get('from')}"])
        haystack = " ".join([m.get("subject") or "", m.get("body") or ""] + (m.get("labels") or []))
        for sh in set(_SH_RE.findall(haystack)):
            if sh in ship_node:
                b.add_rel(nid, ship_node[sh], "mentions", 0.88,
                          [f"email {m['id']} mentionne {sh} (sujet/corps/labels)"])
        for po in set(_PO_RE.findall(haystack)):
            if po in po_node:
                b.add_rel(nid, po_node[po], "mentions", 0.88,
                          [f"email {m['id']} mentionne {po} (sujet/corps/labels)"])

    # ----------------------------------------------------------------- #
    # DOCUMENTS (PDF)  (Document references PO/Shipment/Invoice/Customer)
    # ----------------------------------------------------------------- #
    for d in pdfs:
        nid = f"document:{slug(d['doc_name'])}"
        b.add_entity(
            nid, "Document", d["doc_name"],
            {"doc_type": d.get("title")},
            [f"pdf.{d['doc_name']}"], 0.95,
            [f"PDF '{d['doc_name']}' ({d.get('title')})"])
        text = "\n".join(d["lines"])
        for sh in set(_SH_RE.findall(text)):
            if sh in ship_node:
                b.add_rel(nid, ship_node[sh], "references", 0.95,
                          [f"PDF {d['doc_name']} cite Shipment {sh}"])
        for po in set(_PO_RE.findall(text)):
            if po in po_node:
                b.add_rel(nid, po_node[po], "references", 0.95,
                          [f"PDF {d['doc_name']} cite PO {po}"])
        for invref in set(_INV_RE.findall(text)):
            invid = f"invoice:{slug(invref)}"
            if invid in b.entities:
                b.add_rel(nid, invid, "references", 0.95,
                          [f"PDF {d['doc_name']} cite la facture {invref}"])
        cust = cust_name_node.get(d["fields"].get("Customer"))
        if cust:
            b.add_rel(nid, cust, "references", 0.95,
                      [f"PDF {d['doc_name']} nomme le client {d['fields'].get('Customer')}"])

    # ----------------------------------------------------------------- #
    # COMPANY + EMPLOYEES (RH)
    # ----------------------------------------------------------------- #
    employees = xl["employees"]
    domain = None
    for e in employees:
        dom = (e.get("email") or "").split("@")[-1].lower()
        if dom:
            domain = dom
            break
    company_id = "company:our-logistics-co"
    org = orgchart.reconstruct(employees, emails)
    # PDG = racine de l'organigramme reconstruit
    ceo = next((e for e in employees if e["employee_id"] not in org), None)
    b.add_entity(
        company_id, "Company", "Our Logistics Co",
        {"domain": domain, "headcount": len(employees),
         "ceo_employee": ceo["full_name"] if ceo else None,
         "headquarters_city": "Paris"},
        [f"derived.company_directory ({len(employees)} employés)",
         "derived.email_domain"], 0.9,
        [f"domaine email partagé par {len(employees)} employés : {domain}",
         f"PDG = racine de l'organigramme reconstruit ({ceo['full_name'] if ceo else '?'})"],
        ["raison sociale / siège déduits du domaine email partagé ; non écrits "
         "explicitement dans une source structurée"])

    for e in employees:
        nid = f"employee:{slug(e['full_name'])}"
        emp_node[e["employee_id"]] = nid
        b.add_entity(
            nid, "Employee", e["full_name"],
            {"role_title": e.get("role_title"), "org_unit": e.get("org_unit"),
             "email": e.get("email"), "hire_date": e.get("hire_date"),
             "title_rank": orgchart.title_rank(e["role_title"])},
            [f"excel.company_directory:{e['employee_id']}"], 0.95,
            [f"annuaire Excel : {e['full_name']}, {e['role_title']}, service {e['org_unit']}"])
        b.add_rel(company_id, nid, "employs", 0.95,
                  [f"annuaire Excel : {e['full_name']} (matricule {e['employee_id']})"])

    # reports_to (organigramme reconstruit)
    for emp_id, link in org.items():
        src = emp_node.get(emp_id)
        tgt = emp_node.get(link["manager_id"])
        if src and tgt:
            b.add_rel(src, tgt, "reports_to", link["confidence"],
                      link["evidence"], link["open_questions"])

    # manages (account manager -> customer)
    am = resolve.resolve_account_managers(odoo["customers"], employees)
    for cid, emp in am.items():
        src = emp_node.get(emp["employee_id"])
        tgt = cust_node.get(cid)
        if src and tgt:
            b.add_rel(src, tgt, "manages", 0.95,
                      [f"account manager '{emp['full_name']}' = odoo res.partner.user_id "
                       f"du client {cid} ; même full_name dans l'annuaire"])

    # Driver is_a Employee (3 cas : nom chauffeur == full_name employé)
    drv_emp = resolve.resolve_drivers_to_employees(dd["drivers"], employees)
    for drv_id, emp in drv_emp.items():
        src = f"driver:{slug(drv_id)}"
        tgt = emp_node.get(emp["employee_id"])
        if src in b.entities and tgt:
            b.add_rel(src, tgt, "is_a", 0.9,
                      [f"nom chauffeur '{emp['full_name']}' (dashdoc {drv_id}) == full_name "
                       f"annuaire (matricule {emp['employee_id']})"],
                      ["rapprochement par nom exact ; pas d'ID partagé entre TMS et annuaire"])

    # ----------------------------------------------------------------- #
    # FINANCES (financial)
    # ----------------------------------------------------------------- #
    fin = xl["finances_summary"]

    def money(key):
        v = fin.get(key)
        if v is None:
            return None
        return sources._parse_money(v)

    fs_id = "financial:summary"
    dso = fin.get("DSO (encaissement clients, jours)")
    dpo = fin.get("DPO (paiement fournisseurs, jours)")
    b.add_entity(
        fs_id, "FinancialSummary", "Snapshot financier (12 mois glissants)",
        {"period": fin.get("Période"),
         "payroll_monthly": money("Masse salariale (mensuelle)"),
         "fleet_leasing_monthly": money("Charges flotte / leasing (mensuel)"),
         "fuel_monthly": money("Carburant (mensuel)"),
         "other_opex_monthly": money("Autres OPEX (mensuel)"),
         "gross_margin_pct": sources._parse_pct(fin.get("Marge brute %")),
         "dso_days": dso, "dpo_days": dpo,
         "cash_on_hand": money("Trésorerie disponible")},
        ["excel.finances_summary"], 0.95,
        ["Excel finances_summary : agrégats société (masse salariale, flotte, marge, "
         "DSO/DPO, trésorerie)"])
    b.add_rel(company_id, fs_id, "has_financials", 0.95,
              ["snapshot de gestion rattaché à la société"])

    # RevenueConcentration : CALCULÉE depuis les factures (invoice -> order -> customer)
    rev_by_cust: dict[str, int] = defaultdict(int)
    for inv in odoo["invoices"]:
        order = order_by_po.get(inv.get("po_number"))
        cid = order["customer_id"] if order else inv.get("customer_id")
        if cid and inv.get("amount"):
            rev_by_cust[cid] += inv["amount"]
    total_rev = sum(rev_by_cust.values())
    cust_name_by_id = {c["customer_id"]: c["name"] for c in odoo["customers"]}
    by_customer = sorted(
        [{"customer_id": cid, "name": cust_name_by_id.get(cid, cid),
          "revenue": rev, "share": round(rev / total_rev, 4) if total_rev else 0}
         for cid, rev in rev_by_cust.items()],
        key=lambda r: r["revenue"], reverse=True)
    rc_id = "financial:revenue-concentration"
    b.add_entity(
        rc_id, "RevenueConcentration", "Concentration du CA par client",
        {"total_revenue": total_rev, "currency": "EUR",
         "by_customer": by_customer,
         "top_customer": by_customer[0]["name"] if by_customer else None},
        ["derived.odoo.account_move (somme des factures)"], 0.95,
        [f"CA total = somme de {len(odoo['invoices'])} factures = {total_rev} EUR ; "
         f"concentration calculée par client (invoice_origin -> sale.order -> partner_id)"])
    # chaque facture contribue à la concentration
    for inv in odoo["invoices"]:
        invid = f"invoice:{slug(inv['invoice_id'])}"
        if invid in b.entities:
            b.add_rel(invid, rc_id, "contributes_to", 0.95,
                      [f"facture {inv['invoice_id']} ({inv.get('amount')} EUR) entre dans le CA"])

    # CashflowGap : dérivé dso - dpo
    if dso is not None and dpo is not None:
        cg_id = "financial:cashflow-gap"
        b.add_entity(
            cg_id, "CashflowGap", "Décalage de trésorerie",
            {"dso_days": dso, "dpo_days": dpo, "gap_days": dso - dpo},
            ["derived.excel.finances_summary (DSO - DPO)"], 0.9,
            [f"décalage = DSO {dso}j - DPO {dpo}j = {dso - dpo}j (clients payés après "
             f"les fournisseurs)"])
        b.add_rel(fs_id, cg_id, "implies", 0.9,
                  ["DSO et DPO du snapshot financier impliquent le décalage de trésorerie"])
        # les conditions de paiement fournisseurs alimentent le décalage
        for s in odoo["suppliers"]:
            sid = f"supplier:{slug(s['supplier_id'])}"
            if sid in b.entities:
                b.add_rel(sid, cg_id, "feeds", 0.85,
                          [f"conditions de paiement fournisseur {s['supplier_id']} "
                           f"({s.get('payment_term_days')}j) -> DPO"])

    return {"entities": list(b.entities.values()), "relationships": b.relationships}


def summarize(ontology: dict) -> None:
    by_type = defaultdict(int)
    by_layer = defaultdict(int)
    for e in ontology["entities"]:
        by_type[e["type"]] += 1
        by_layer[e["layer"]] += 1
    rel_type = defaultdict(int)
    for r in ontology["relationships"]:
        rel_type[r["type"]] += 1
    print("\n===== ontology.json — récapitulatif =====")
    print(f"Entités : {len(ontology['entities'])}   Relations : {len(ontology['relationships'])}")
    print("\nEntités par type :")
    for t in sorted(by_type):
        print(f"  {t:20s} {by_type[t]}")
    print("\nEntités par couche :")
    for l in sorted(by_layer):
        print(f"  {l:14s} {by_layer[l]}")
    print("\nRelations par type :")
    for t in sorted(rel_type):
        print(f"  {t:16s} {rel_type[t]}")


def main():
    ontology = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(ontology, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"écrit : {OUT.relative_to(ROOT)}")
    summarize(ontology)


if __name__ == "__main__":
    main()
