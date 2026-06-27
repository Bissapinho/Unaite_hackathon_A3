"""canonical.py — SOURCE DE VÉRITÉ UNIQUE (Brique 1, scénario SH-2049).

Tout (dumps Odoo/Dashdoc, emails, SQLite, Excel, PDF, validation) importe d'ici.
Aucune valeur métier ne doit être dupliquée/hardcodée ailleurs.

Structure :
  - Les enregistrements DU SCÉNARIO sont codés à la main, "au caractère près".
    Ils portent un flag interne `_scenario: True` (+ `_scenario_role`) — filet pour
    la démo, jamais sérialisé dans les dumps réalistes.
  - Le BRUIT est généré avec Faker + random.Random sur une SEED FIXE -> reproductible.

Conventions :
  - Les dates "aujourd'hui/demain" sont calculées à l'exécution (date système),
    ISO 8601, heures locales conservées. La démo reste cohérente quel que soit le jour.
  - Les noms de champs ici sont CANONIQUES. Chaque source les ré-exprime dans son
    propre vocabulaire (mapping documenté dans DATA_README.md).
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from faker import Faker

# --------------------------------------------------------------------------- #
# Reproductibilité
# --------------------------------------------------------------------------- #
SEED = 2049
fake = Faker("fr_FR")
Faker.seed(SEED)
_rng = random.Random(SEED)

# --------------------------------------------------------------------------- #
# Dates (calculées au runtime)
# --------------------------------------------------------------------------- #
TODAY = date.today()
TOMORROW = TODAY + timedelta(days=1)


def iso_at(d: date, hhmm: str) -> str:
    """Datetime ISO 8601 local, ex. iso_at(TODAY, '18:00') -> '2026-06-27T18:00:00'."""
    return f"{d.isoformat()}T{hhmm}:00"


def iso_date(d: date) -> str:
    return d.isoformat()


# =========================================================================== #
# 1. SCÉNARIO — codé à la main (à respecter au caractère près)
# =========================================================================== #

# --- Customers -------------------------------------------------------------- #
SCENARIO_CUSTOMERS = [
    {"customer_id": "C001", "name": "MedPharma", "industry": "Pharma",
     "priority_tier": "Platinum", "account_manager": "Sarah Martin",
     "strategic_value": 1200000, "city": "Lyon",
     "_scenario": True, "_scenario_role": "customer"},
    {"customer_id": "C002", "name": "FreshMarket", "industry": "Retail",
     "priority_tier": "Gold", "account_manager": "Jules Bernard",
     "strategic_value": None, "city": "Marseille",
     "_scenario": True, "_scenario_role": "customer"},
    {"customer_id": "C003", "name": "AutoParts SAS", "industry": "Automotive",
     "priority_tier": "Silver", "account_manager": "Clara Moreau",
     "strategic_value": None, "city": "Lille",
     "_scenario": True, "_scenario_role": "customer"},
    {"customer_id": "C004", "name": "BioCare Labs", "industry": "Healthcare",
     "priority_tier": "Platinum", "account_manager": "Sarah Martin",
     "strategic_value": None, "city": "Lyon",
     "_scenario": True, "_scenario_role": "customer"},
]

# --- Products --------------------------------------------------------------- #
SCENARIO_PRODUCTS = [
    {"sku": "PHARMA-22", "name": "Insulin batch", "category": "Cold-chain",
     "temperature_min": 2, "temperature_max": 8, "unit_value": 180,
     "_scenario": True, "_scenario_role": "product"},
    {"sku": "FOOD-19", "name": "Fresh salmon", "category": "Cold-chain",
     "temperature_min": 0, "temperature_max": 4, "unit_value": 35,
     "_scenario": True, "_scenario_role": "product"},
    {"sku": "AUTO-77", "name": "Brake components", "category": "Standard",
     "temperature_min": None, "temperature_max": None, "unit_value": 90,
     "_scenario": True, "_scenario_role": "product"},
    {"sku": "LAB-12", "name": "Diagnostic reagent", "category": "Cold-chain",
     "temperature_min": 2, "temperature_max": 8, "unit_value": 250,
     "_scenario": True, "_scenario_role": "product"},
]

# --- Orders ----------------------------------------------------------------- #
SCENARIO_ORDERS = [
    {"order_id": "O-881", "customer_id": "C001", "po_number": "PO-8821",
     "promised_delivery_deadline": iso_at(TODAY, "18:00"), "status": "open",
     "order_date": iso_date(TODAY - timedelta(days=3)),
     "_scenario": True, "_scenario_role": "po"},
    {"order_id": "O-882", "customer_id": "C002", "po_number": "PO-8822",
     "promised_delivery_deadline": iso_at(TODAY, "20:00"), "status": "open",
     "order_date": iso_date(TODAY - timedelta(days=2)),
     "_scenario": True, "_scenario_role": "po"},
    {"order_id": "O-883", "customer_id": "C003", "po_number": "PO-8823",
     "promised_delivery_deadline": iso_at(TOMORROW, "12:00"), "status": "open",
     "order_date": iso_date(TODAY - timedelta(days=2)),
     "_scenario": True, "_scenario_role": "po"},
    {"order_id": "O-884", "customer_id": "C004", "po_number": "PO-8824",
     "promised_delivery_deadline": iso_at(TODAY, "16:00"), "status": "open",
     "order_date": iso_date(TODAY - timedelta(days=1)),
     "_scenario": True, "_scenario_role": "po"},
]

# --- Shipments -------------------------------------------------------------- #
# *SH-2049 : deadline 18:00 + retard 6h => arrivée minuit = 00:00 du lendemain (ISO 8601 valide). Central.
SCENARIO_SHIPMENTS = [
    {"shipment_id": "SH-2049", "order_id": "O-881", "carrier_id": "CAR-COLDROAD",
     "origin_warehouse": "WH-1", "destination": "Lyon Hospital Distribution Center",
     "status": "Delayed", "estimated_arrival": iso_at(TOMORROW, "00:00"),
     "temperature_controlled": True, "battery_backup_hours": 3,
     "_scenario": True, "_scenario_role": "shipment"},
    {"shipment_id": "SH-2050", "order_id": "O-882", "carrier_id": "CAR-FRESHMOVE",
     "origin_warehouse": "WH-1", "destination": "Marseille",
     "status": "In transit", "estimated_arrival": iso_at(TODAY, "20:00"),
     "temperature_controlled": True, "battery_backup_hours": 6,
     "_scenario": True, "_scenario_role": "shipment"},
    {"shipment_id": "SH-2051", "order_id": "O-883", "carrier_id": "CAR-ROADX",
     "origin_warehouse": "WH-1", "destination": "Lille",
     "status": "In transit", "estimated_arrival": iso_at(TOMORROW, "12:00"),
     "temperature_controlled": False, "battery_backup_hours": 0,
     "_scenario": True, "_scenario_role": "shipment"},
    {"shipment_id": "SH-2052", "order_id": "O-884", "carrier_id": "CAR-COLDROAD",
     "origin_warehouse": "WH-2", "destination": "Lyon",
     "status": "Delayed", "estimated_arrival": iso_at(TODAY, "18:00"),
     "temperature_controlled": True, "battery_backup_hours": 2,
     "_scenario": True, "_scenario_role": "shipment"},
]

# --- ShipmentItems ---------------------------------------------------------- #
SCENARIO_SHIPMENT_ITEMS = [
    {"shipment_id": "SH-2049", "sku": "PHARMA-22", "quantity": 1000,
     "_scenario": True, "_scenario_role": "shipment_item"},
    {"shipment_id": "SH-2050", "sku": "FOOD-19", "quantity": 400,
     "_scenario": True, "_scenario_role": "shipment_item"},
    {"shipment_id": "SH-2051", "sku": "AUTO-77", "quantity": 250,
     "_scenario": True, "_scenario_role": "shipment_item"},
    {"shipment_id": "SH-2052", "sku": "LAB-12", "quantity": 150,
     "_scenario": True, "_scenario_role": "shipment_item"},
]

# --- Carriers --------------------------------------------------------------- #
SCENARIO_CARRIERS = [
    {"carrier_id": "CAR-COLDROAD", "name": "ColdRoad", "service_type": "Cold-chain",
     "reliability_score": 0.78, "_scenario": True, "_scenario_role": "carrier"},
    {"carrier_id": "CAR-FRESHMOVE", "name": "FreshMove", "service_type": "Cold-chain",
     "reliability_score": 0.88, "_scenario": True, "_scenario_role": "carrier"},
    {"carrier_id": "CAR-ROADX", "name": "RoadX", "service_type": "Standard",
     "reliability_score": 0.82, "_scenario": True, "_scenario_role": "carrier"},
    {"carrier_id": "CAR-COLDFAST", "name": "ColdFast Express",
     "service_type": "Cold-chain (emergency)", "reliability_score": 0.91,
     "_scenario": True, "_scenario_role": "carrier_backup"},
    {"carrier_id": "CAR-NORTHLOG", "name": "NorthLog", "service_type": "Cold-chain",
     "reliability_score": 0.80, "_scenario": True, "_scenario_role": "carrier"},
]

# --- Warehouses ------------------------------------------------------------- #
SCENARIO_WAREHOUSES = [
    {"warehouse_id": "WH-1", "name": "Paris WH-1", "city": "Paris",
     "_scenario": True, "_scenario_role": "warehouse"},
    {"warehouse_id": "WH-2", "name": "Lyon WH-2", "city": "Lyon",
     "_scenario": True, "_scenario_role": "warehouse"},
]

# --- Inventory -------------------------------------------------------------- #
SCENARIO_INVENTORY = [
    {"warehouse_id": "WH-1", "sku": "PHARMA-22", "available_units": 800, "reserved_units": 600,
     "_scenario": True, "_scenario_role": "inventory"},
    {"warehouse_id": "WH-2", "sku": "PHARMA-22", "available_units": 200, "reserved_units": 100,
     "_scenario": True, "_scenario_role": "inventory"},
    {"warehouse_id": "WH-1", "sku": "FOOD-19", "available_units": 500, "reserved_units": 200,
     "_scenario": True, "_scenario_role": "inventory"},
    {"warehouse_id": "WH-2", "sku": "LAB-12", "available_units": 150, "reserved_units": 50,
     "_scenario": True, "_scenario_role": "inventory"},
]

# --- Contracts -------------------------------------------------------------- #
SCENARIO_CONTRACTS = [
    {"contract_id": "CT-001", "customer_id": "C001", "sla_deadline": "18:00",
     "late_penalty_per_hour": 7000,
     "special_terms": "Cold-chain 2-8C. Critical shipments must be escalated to account manager.",
     "_scenario": True, "_scenario_role": "sla"},
    {"contract_id": "CT-004", "customer_id": "C004", "sla_deadline": "16:00",
     "late_penalty_per_hour": 5000,
     "special_terms": "Cold-chain 2-8C. Escalation required.",
     "_scenario": True, "_scenario_role": "sla"},
]

# --- Invoices --------------------------------------------------------------- #
# INV-7742 doit rester la plus grosse facture PENDING de tout le jeu (bruit compris).
SCENARIO_INVOICES = [
    {"invoice_id": "INV-7742", "order_id": "O-881", "amount": 186000, "currency": "EUR",
     "status": "Pending", "_scenario": True, "_scenario_role": "invoice"},
    {"invoice_id": "INV-7743", "order_id": "O-882", "amount": 14000, "currency": "EUR",
     "status": "Pending", "_scenario": True, "_scenario_role": "invoice"},
    {"invoice_id": "INV-7744", "order_id": "O-883", "amount": 22500, "currency": "EUR",
     "status": "Paid", "_scenario": True, "_scenario_role": "invoice"},
    {"invoice_id": "INV-7745", "order_id": "O-884", "amount": 37500, "currency": "EUR",
     "status": "Pending", "_scenario": True, "_scenario_role": "invoice"},
]


# =========================================================================== #
# 2. BRUIT — généré déterministe (Faker + _rng), cohérent, sans orphelins
# =========================================================================== #

FRENCH_CITIES = ["Paris", "Lyon", "Marseille", "Lille", "Bordeaux", "Strasbourg",
                 "Nantes", "Toulouse", "Nice", "Rennes", "Rouen", "Dijon"]

# --- Customers de bruit (C005..C018 -> 18 au total) ------------------------- #
_NOISE_INDUSTRIES = ["Retail", "Food", "Automotive", "Chemicals", "Electronics",
                     "Cosmetics", "Beverage", "Industrial"]
_NOISE_AMS = ["Jules Bernard", "Clara Moreau", "Paul Lefevre", "Emma Dubois", "Hugo Petit"]

NOISE_CUSTOMERS = []
for i in range(5, 19):  # 14 clients de bruit
    cid = f"C{i:03d}"
    # priority tier de bruit : jamais Platinum (réservé au scénario => saliency propre)
    tier = _rng.choice(["Bronze", "Silver", "Silver", "Gold"])
    # strategic_value de bruit borné < 600000 (aucun ne dépasse MedPharma=1_200_000)
    sval = _rng.choice([None, None, _rng.randint(50000, 580000)])
    NOISE_CUSTOMERS.append({
        "customer_id": cid,
        "name": fake.unique.company(),
        "industry": _rng.choice(_NOISE_INDUSTRIES),
        "priority_tier": tier,
        "account_manager": _rng.choice(_NOISE_AMS),
        "strategic_value": sval,
        "city": _rng.choice(FRENCH_CITIES),
    })

# --- Products de bruit (8 -> 12 au total) ----------------------------------- #
_NOISE_PRODUCT_DEFS = [
    ("FOOD-23", "Frozen vegetables", "Cold-chain", -18, -12, 22),
    ("FOOD-31", "Yogurt pallet", "Cold-chain", 2, 6, 18),
    ("PHARMA-41", "Vaccine vials", "Cold-chain", 2, 8, 320),
    ("LAB-30", "Blood sample kit", "Cold-chain", 2, 8, 140),
    ("AUTO-12", "Tire set", "Standard", None, None, 75),
    ("AUTO-55", "Engine filter", "Standard", None, None, 40),
    ("IND-08", "Steel fittings", "Standard", None, None, 60),
    ("ELEC-14", "Control boards", "Standard", None, None, 210),
]
NOISE_PRODUCTS = [
    {"sku": sku, "name": name, "category": cat,
     "temperature_min": tmin, "temperature_max": tmax, "unit_value": val}
    for (sku, name, cat, tmin, tmax, val) in _NOISE_PRODUCT_DEFS
]

# --- Carriers de bruit (5 -> 10 au total) ----------------------------------- #
_NOISE_CARRIER_DEFS = [
    ("CAR-RAPIDFR", "Rapid France", "Standard"),
    ("CAR-FROIDEXP", "Froid Express", "Cold-chain"),
    ("CAR-TRANSALP", "TransAlpes", "Standard"),
    ("CAR-GELITRANS", "Geli Trans", "Cold-chain"),
    ("CAR-HEXLOG", "Hexa Logistics", "Standard"),
]
NOISE_CARRIERS = [
    {"carrier_id": cid, "name": name, "service_type": st,
     "reliability_score": round(_rng.uniform(0.62, 0.94), 2)}
    for (cid, name, st) in _NOISE_CARRIER_DEFS
]

# --- Warehouses de bruit (2 -> 4 au total) ---------------------------------- #
NOISE_WAREHOUSES = [
    {"warehouse_id": "WH-3", "name": "Marseille WH-3", "city": "Marseille"},
    {"warehouse_id": "WH-4", "name": "Lille WH-4", "city": "Lille"},
]

# --- Listes consolidées (scénario + bruit) — nécessaires pour générer le reste #
CUSTOMERS = SCENARIO_CUSTOMERS + NOISE_CUSTOMERS
PRODUCTS = SCENARIO_PRODUCTS + NOISE_PRODUCTS
CARRIERS = SCENARIO_CARRIERS + NOISE_CARRIERS
WAREHOUSES = SCENARIO_WAREHOUSES + NOISE_WAREHOUSES

_ALL_CUSTOMER_IDS = [c["customer_id"] for c in CUSTOMERS]
_ALL_SKUS = [p["sku"] for p in PRODUCTS]
_COLD_SKUS = [p["sku"] for p in PRODUCTS if p["category"] == "Cold-chain"]
_STD_SKUS = [p["sku"] for p in PRODUCTS if p["category"] == "Standard"]
_ALL_CARRIER_IDS = [c["carrier_id"] for c in CARRIERS]
_ALL_WH_IDS = [w["warehouse_id"] for w in WAREHOUSES]
_COLD_CARRIERS = [c["carrier_id"] for c in CARRIERS if "Cold-chain" in c["service_type"]]

# --- Orders / Shipments / Invoices de bruit (24 chacun -> 28 au total) ------- #
# Un order -> un shipment -> une invoice (cohérence 1-1, comme le scénario).
NOISE_ORDERS = []
NOISE_SHIPMENTS = []
NOISE_INVOICES = []
NOISE_SHIPMENT_ITEMS = []

_STATUSES = ["Delivered", "Delivered", "In transit", "Delayed", "Planned"]
_PAY_BY_SHIPMENT_STATUS = {"Delivered": "Paid", "In transit": "Pending",
                           "Delayed": "Pending", "Planned": "Pending"}

for n in range(24):
    idx = n + 5                         # O-885.., PO-8825.., SH-2053.., INV-7746..
    order_id = f"O-{880 + idx}"         # O-885 .. O-908
    po_number = f"PO-{8820 + idx}"      # PO-8825 .. PO-8848
    shipment_id = f"SH-{2048 + idx}"    # SH-2053 .. SH-2076
    invoice_id = f"INV-{7741 + idx}"    # INV-7746 .. INV-7769

    customer_id = _rng.choice(_ALL_CUSTOMER_IDS[1:])  # évite de surcharger C001
    ship_status = _rng.choice(_STATUSES)
    days_off = _rng.randint(-25, 5)
    deadline_day = TODAY + timedelta(days=days_off)
    order_day = deadline_day - timedelta(days=_rng.randint(1, 6))

    # cold-chain ~40% du bruit
    is_cold = _rng.random() < 0.4
    sku = _rng.choice(_COLD_SKUS if is_cold else _STD_SKUS)
    carrier_id = _rng.choice(_COLD_CARRIERS if is_cold else _ALL_CARRIER_IDS)
    qty = _rng.choice([50, 100, 120, 150, 200, 250, 300, 400, 500])

    origin = _rng.choice(_ALL_WH_IDS)
    destination = _rng.choice([c for c in FRENCH_CITIES])

    NOISE_ORDERS.append({
        "order_id": order_id, "customer_id": customer_id, "po_number": po_number,
        "promised_delivery_deadline": iso_at(deadline_day, _rng.choice(["10:00", "14:00", "16:00", "18:00"])),
        "status": _rng.choice(["open", "open", "done"]),
        "order_date": iso_date(order_day),
    })

    eta_hhmm = _rng.choice(["09:00", "11:00", "15:00", "17:00", "19:00"])
    NOISE_SHIPMENTS.append({
        "shipment_id": shipment_id, "order_id": order_id, "carrier_id": carrier_id,
        "origin_warehouse": origin, "destination": destination,
        "status": ship_status, "estimated_arrival": iso_at(deadline_day, eta_hhmm),
        "temperature_controlled": is_cold,
        "battery_backup_hours": (_rng.choice([4, 6, 8, 10]) if is_cold else 0),
    })

    NOISE_SHIPMENT_ITEMS.append({"shipment_id": shipment_id, "sku": sku, "quantity": qty})

    # Montants de bruit bornés < 186000 (INV-7742 reste la plus grosse PENDING).
    pay_state = _PAY_BY_SHIPMENT_STATUS[ship_status]
    if pay_state == "Pending":
        amount = _rng.randint(3000, 90000)     # strictement < 186000
    else:
        amount = _rng.randint(3000, 150000)    # Paid : peu importe pour la saliency
    NOISE_INVOICES.append({
        "invoice_id": invoice_id, "order_id": order_id, "amount": amount,
        "currency": "EUR", "status": pay_state,
    })

# --- Inventory de bruit (~21 -> ~25 au total) ------------------------------- #
NOISE_INVENTORY = []
_inv_seen = {(r["warehouse_id"], r["sku"]) for r in SCENARIO_INVENTORY}
while len(NOISE_INVENTORY) < 21:
    wh = _rng.choice(_ALL_WH_IDS)
    sku = _rng.choice(_ALL_SKUS)
    if (wh, sku) in _inv_seen:
        continue
    _inv_seen.add((wh, sku))
    avail = _rng.choice([80, 120, 150, 200, 300, 450, 600])
    NOISE_INVENTORY.append({
        "warehouse_id": wh, "sku": sku,
        "available_units": avail,
        "reserved_units": _rng.randint(0, avail // 2),
    })

# --- Contracts de bruit (6 -> 8 au total) ----------------------------------- #
# Pénalités de bruit < 7000 (CT-001=7000 reste le seul >= 7000 => saliency).
NOISE_CONTRACTS = []
_contract_customers = _rng.sample([c for c in _ALL_CUSTOMER_IDS if c not in ("C001", "C004")], 6)
for j, cid in enumerate(_contract_customers, start=2):
    NOISE_CONTRACTS.append({
        "contract_id": f"CT-{j:03d}" if j != 4 else f"CT-{j:03d}b",  # CT-004 réservé scénario
        "customer_id": cid,
        "sla_deadline": _rng.choice(["12:00", "14:00", "17:00", "20:00"]),
        "late_penalty_per_hour": _rng.choice([1000, 1500, 2000, 3000, 5000]),
        "special_terms": _rng.choice([
            "Standard delivery terms.",
            "Cold-chain handling required.",
            "Delivery during business hours only.",
        ]),
    })

# --- Suppliers (~8) --------------------------------------------------------- #
PAYMENT_TERMS = [
    {"name": "Immediate", "days": 0},
    {"name": "30 Days", "days": 30},
    {"name": "45 Days", "days": 45},
    {"name": "60 Days", "days": 60},
]
_SUPPLIER_DEFS = [
    ("SUP-01", "TotalEnergies Fleet", "Fuel"),
    ("SUP-02", "Arval Leasing", "Leasing"),
    ("SUP-03", "Michelin Pro", "Tires"),
    ("SUP-04", "EuroMaster Maintenance", "Maintenance"),
    ("SUP-05", "Carrier Transicold", "Refrigeration maintenance"),
    ("SUP-06", "Antargaz", "Fuel"),
    ("SUP-07", "Norauto Pro", "Maintenance"),
    ("SUP-08", "Bridgestone Fleet", "Tires"),
]
SUPPLIERS = [
    {"supplier_id": sid, "name": name, "category": cat,
     "payment_term_days": _rng.choice([30, 45, 60])}
    for (sid, name, cat) in _SUPPLIER_DEFS
]

# --- Vehicles (~10) --------------------------------------------------------- #
_VEHICLE_TYPES = [("frigo", True), ("frigo", True), ("tautliner", False),
                  ("fourgon", False), ("porteur frigo", True), ("semi", False)]
VEHICLES = []
for k in range(10):
    vtype, refrig = _rng.choice(_VEHICLE_TYPES)
    VEHICLES.append({
        "license_plate": f"{fake.unique.license_plate()}",
        "type": vtype,
        "year": _rng.randint(2015, 2024),
        "is_refrigerated": refrig,
        "carrier_id": _rng.choice(_ALL_CARRIER_IDS),
    })

# --- Drivers (~14) avec certifications -------------------------------------- #
_CERTS = ["ADR", "FIMO", "frigo"]
DRIVERS = []
for d in range(14):
    n_certs = _rng.randint(1, 3)
    certs = _rng.sample(_CERTS, n_certs)
    DRIVERS.append({
        "driver_id": f"DRV-{d + 1:03d}",
        "name": fake.unique.name(),
        "certifications": certs,
        "carrier_id": _rng.choice(_ALL_CARRIER_IDS),
    })

# Liens Driver <-> Employee (futur `Driver is_a Employee`) : on FIXE le `name` de
# 3 chauffeurs pour qu'il matche un EMPLOYEES.full_name. On NE retire PAS l'appel
# `fake.unique.name()` ci-dessus (cela décalerait toute la séquence) : on ÉCRASE
# après coup, la séquence Faker reste intacte. Les noms choisis sont distincts des
# noms Faker déjà tirés (aucune collision). Les 11 autres chauffeurs restent des
# noms Faker non reliés (tous les chauffeurs ne sont pas salariés — sous-traitance).
FIXED_DRIVER_NAMES = ["Thomas Girard", "Mehdi Faure", "David Olivier"]
for _i, _nm in enumerate(FIXED_DRIVER_NAMES):
    DRIVERS[_i]["name"] = _nm

# --- Customer claims (~12) — TOUTES closes, aucune liée à SH-2049 ------------ #
_CLAIM_TYPES = ["Damaged goods", "Late delivery", "Temperature breach",
                "Wrong quantity", "Billing dispute", "Lost parcel"]
CUSTOMER_CLAIMS = []
_hist_shipment_ids = [s["shipment_id"] for s in NOISE_SHIPMENTS]
for c in range(12):
    opened = TODAY - timedelta(days=_rng.randint(60, 300))
    closed = opened + timedelta(days=_rng.randint(3, 30))
    cust = _rng.choice(_ALL_CUSTOMER_IDS)
    # shipment_ref nullable, jamais SH-2049/2050/2051/2052 (scénario "frais")
    sref = _rng.choice([None] + _hist_shipment_ids)
    CUSTOMER_CLAIMS.append({
        "id": c + 1,
        "customer_ref": cust,
        "shipment_ref": sref,
        "type": _rng.choice(_CLAIM_TYPES),
        "opened_at": iso_date(opened),
        "closed_at": iso_date(closed),
        "status": "closed",
    })

# --- SLA penalty log (~6) — historique ------------------------------------- #
SLA_PENALTY_LOG = []
for p in range(6):
    month_date = TODAY - timedelta(days=_rng.randint(40, 250))
    hours = _rng.randint(1, 8)
    SLA_PENALTY_LOG.append({
        "id": p + 1,
        "customer_ref": _rng.choice(_ALL_CUSTOMER_IDS),
        "shipment_ref": _rng.choice(_hist_shipment_ids),
        "hours_late": hours,
        "penalty_amount": hours * _rng.choice([800, 1000, 1500, 2000]),
        "month": month_date.strftime("%Y-%m"),
    })

# --- Legacy contacts — "sale", avec variante floue de MedPharma ------------- #
# Incohérence INTENTIONNELLE : "Med Pharma SARL" != "MedPharma" (résolution floue).
LEGACY_CONTACTS = [
    {"id": 1, "raw_name": "Med Pharma SARL", "email": "contact@medpharma.com",
     "phone": "01 42 11 22 33", "notes": "Ancien contact - voir compte principal pharma"},
    {"id": 2, "raw_name": "MEDPHARMA (old)", "email": "old.billing@medpharma.com",
     "phone": "01 42 11 22 30", "notes": "Doublon probable - a fusionner"},
    {"id": 3, "raw_name": "FreshMarket SA", "email": "achats@freshmarket.fr",
     "phone": "04 91 00 11 22", "notes": ""},
]
# bruit "sale" supplémentaire
for q in range(4, 12):
    LEGACY_CONTACTS.append({
        "id": q,
        "raw_name": fake.unique.company().upper(),
        "email": fake.unique.company_email(),
        "phone": fake.phone_number(),
        "notes": _rng.choice(["", "old", "verifier", "contact perdu", "RAS"]),
    })

# --- Carrier backup matrix (Excel) ------------------------------------------ #
CARRIER_BACKUP_MATRIX = [
    {"route": "Paris->Lyon", "backup_carrier": "ColdFast Express",
     "max_cold_chain_capacity": 20, "emergency_rate": 2400,
     "_scenario": True, "_scenario_role": "carrier_backup"},
    {"route": "Lyon->Marseille", "backup_carrier": "FreshMove",
     "max_cold_chain_capacity": 12, "emergency_rate": 1700},
    {"route": "Paris->Lille", "backup_carrier": "NorthLog",
     "max_cold_chain_capacity": 18, "emergency_rate": 1300},
    # bruit
    {"route": "Lyon->Bordeaux", "backup_carrier": "Froid Express",
     "max_cold_chain_capacity": 10, "emergency_rate": 1500},
    {"route": "Paris->Strasbourg", "backup_carrier": "Geli Trans",
     "max_cold_chain_capacity": 14, "emergency_rate": 1600},
]

# --- Emails (scénario : 4 exacts + bruit anodin) ---------------------------- #
OPS_INBOX = "ops@ourlogisticsco.com"
SCENARIO_EMAILS = [
    {"id": "EM-001", "from": "operations@coldroad-logistics.com", "to": OPS_INBOX,
     "subject": "Delay notification - Shipment SH-2049",
     "body": ("Truck assigned to shipment SH-2049 has broken down near Lyon. "
              "Estimated delay: 6 hours. Refrigeration unit battery backup is "
              "expected to last 3 more hours."),
     "received_at": iso_at(TODAY, "09:12"),
     "labels": ["carrier", "delay", "SH-2049"],
     "_scenario": True, "_scenario_role": "email"},
    {"id": "EM-002", "from": "procurement@medpharma.com", "to": OPS_INBOX,
     "subject": "URGENT - PO-8821 delivery confirmation",
     "body": ("Please confirm that PO-8821 will arrive before 18:00 today. "
              "This shipment is needed for tomorrow morning hospital distribution."),
     "received_at": iso_at(TODAY, "09:45"),
     "labels": ["customer", "urgent", "PO-8821"],
     "_scenario": True, "_scenario_role": "email"},
    {"id": "EM-003", "from": "sarah.martin@ourlogisticsco.com", "to": OPS_INBOX,
     "subject": "MedPharma is strategic",
     "body": ("MedPharma is one of our top 5 accounts. Any delivery risk should "
              "be escalated immediately."),
     "received_at": iso_at(TODAY, "10:02"),
     "labels": ["internal", "strategic"],
     "_scenario": True, "_scenario_role": "email"},
    {"id": "EM-004", "from": "dispatch@coldfast-express.com", "to": OPS_INBOX,
     "subject": "Emergency cold-chain capacity Paris to Lyon",
     "body": ("We have emergency refrigerated capacity available today for Paris "
              "to Lyon. Max capacity: 20 pallets. Emergency rate: 2,400 EUR."),
     "received_at": iso_at(TODAY, "10:20"),
     "labels": ["carrier", "backup", "emergency"],
     "_scenario": True, "_scenario_role": "email"},
    # --- Indices RH (cohérents avec l'organigramme caché EMPLOYEES.manager_id) ---
    # EM-007 : Sarah Martin escalade le risque MedPharma à SON n+1, Jules Bernard
    # (Directeur Commercial). Matérialise reports_to(Sarah -> Jules) SANS le nommer
    # "manager". Lié au fil SH-2049.
    {"id": "EM-007", "from": "sarah.martin@ourlogisticsco.com",
     "to": "jules.bernard@ourlogisticsco.com",
     "subject": "Escalade risque livraison MedPharma (SH-2049)",
     "body": ("Bonjour Jules,\n\n"
              "Le lot insuline pour MedPharma (PO-8821) est en retard, la deadline "
              "18:00 ne sera pas tenue. Vu l'enjeu sur ce compte, je te transmets "
              "le dossier pour validation : peux-tu arbitrer l'option de secours "
              "ColdFast Express ?\n\n"
              "Je reste en première ligne côté client.\n\n"
              "Cordialement,\n"
              "Sarah Martin\n"
              "Responsable Grands Comptes — ourlogisticsco.com"),
     "received_at": iso_at(TODAY, "10:35"),
     "labels": ["internal", "escalation", "SH-2049"],
     "_scenario": True, "_scenario_role": "email"},
    # EM-009 : Jules Bernard escalade à SON n+1, le Directeur Général Philippe Caron.
    # Matérialise reports_to(Jules -> Philippe). Couvre le chef de service Commercial.
    {"id": "EM-009", "from": "jules.bernard@ourlogisticsco.com",
     "to": "philippe.caron@ourlogisticsco.com",
     "subject": "Pour validation DG : secours MedPharma",
     "body": ("Philippe,\n\n"
              "Suite au retard MedPharma remonté par Sarah Martin (ma Responsable "
              "Grands Comptes), je valide le recours au transporteur de secours. "
              "Comme la pénalité contractuelle est lourde, je remonte la décision à "
              "ton niveau pour accord final.\n\n"
              "Bien à toi,\n"
              "Jules Bernard\n"
              "Directeur Commercial — ourlogisticsco.com"),
     "received_at": iso_at(TODAY, "10:48"),
     "labels": ["internal", "escalation", "SH-2049"],
     "_scenario": True, "_scenario_role": "email"},
]
NOISE_EMAILS = [
    {"id": "EM-005", "from": "logistics@freshmarket.fr", "to": OPS_INBOX,
     "subject": "Delivery confirmation PO-8822",
     "body": "Thanks, we received the salmon delivery on time. Everything looks good.",
     "received_at": iso_at(TODAY, "08:30"),
     "labels": ["customer", "routine"]},
    {"id": "EM-006", "from": "accounting@autoparts-sas.fr", "to": OPS_INBOX,
     "subject": "Question about invoice payment terms",
     "body": "Could you confirm the payment terms on our latest invoice? Thanks.",
     "received_at": iso_at(TODAY, "11:05"),
     "labels": ["billing", "routine"]},
    # --- Indices RH (bruit opérationnel, signatures + 1 délégation chauffeur) ---
    # EM-008 : délégation descendante du Responsable d'Exploitation vers un chauffeur
    # fixé (Thomas Girard). Matérialise reports_to(Thomas -> Karim) ; la réponse de
    # Thomas porte AUSSI sa signature (couverture). Opérationnel, hors scénario.
    {"id": "EM-008", "from": "karim.benali@ourlogisticsco.com",
     "to": "thomas.girard@ourlogisticsco.com",
     "subject": "Tournée de demain - prise en charge",
     "body": ("Thomas,\n\n"
              "Peux-tu prendre la tournée frigo Paris->Lille demain matin ? Tu es "
              "mon chauffeur le plus dispo sur ce créneau. Confirme-moi.\n\n"
              "Karim Benali\n"
              "Responsable d'Exploitation — ourlogisticsco.com\n\n"
              "----- Réponse -----\n"
              "Ok Karim, c'est noté, je m'en occupe.\n"
              "Thomas Girard\n"
              "Chauffeur — ourlogisticsco.com"),
     "received_at": iso_at(TODAY, "08:55"),
     "labels": ["internal", "ops", "routine"]},
    # EM-010 : la Directrice de l'Exploitation délègue à son Responsable d'Exploitation.
    # Matérialise reports_to(Karim -> Nadia) + signatures.
    {"id": "EM-010", "from": "nadia.renard@ourlogisticsco.com",
     "to": "karim.benali@ourlogisticsco.com",
     "subject": "Planning chauffeurs semaine prochaine",
     "body": ("Karim,\n\n"
              "Je te délègue le bouclage du planning chauffeurs de la semaine "
              "prochaine ; transmets-moi la version finale vendredi.\n\n"
              "Nadia Renard\n"
              "Directrice de l'Exploitation — ourlogisticsco.com"),
     "received_at": iso_at(TODAY, "07:40"),
     "labels": ["internal", "ops", "routine"]},
    # EM-011 : la Comptable transmet à sa Responsable Comptabilité pour validation,
    # qui elle-même remonte au DG. reports_to(Nathalie -> Sophie) + (Sophie -> Philippe).
    {"id": "EM-011", "from": "nathalie.roux@ourlogisticsco.com",
     "to": "sophie.lambert@ourlogisticsco.com",
     "subject": "Relances clients - pour validation",
     "body": ("Sophie,\n\n"
              "Je te transmets le tableau des relances clients pour validation "
              "avant envoi. Le délai d'encaissement se tend ce mois-ci.\n\n"
              "Nathalie Roux\n"
              "Comptable — ourlogisticsco.com\n\n"
              "----- Réponse -----\n"
              "Merci Nathalie, je valide et je remonte le point trésorerie à "
              "Philippe Caron, notre Directeur Général.\n"
              "Sophie Lambert\n"
              "Responsable Comptabilité — ourlogisticsco.com"),
     "received_at": iso_at(TODAY, "11:30"),
     "labels": ["internal", "finance", "routine"]},
    # EM-012 : signature de la Responsable RH (couverture annuaire) + remontée au DG.
    {"id": "EM-012", "from": "olivier.mercier@ourlogisticsco.com", "to": OPS_INBOX,
     "subject": "Mise à jour annuaire interne",
     "body": ("Bonjour à tous,\n\n"
              "L'annuaire interne a été mis à jour (postes et services). Toute "
              "correction est à me remonter ; je transmets ensuite à Philippe Caron, "
              "Directeur Général.\n\n"
              "Olivier Mercier\n"
              "Responsable RH — ourlogisticsco.com"),
     "received_at": iso_at(TODAY, "12:10"),
     "labels": ["internal", "rh", "routine"]},
]

# =========================================================================== #
# 2bis. STRUCTURE HUMAINE (RH) + FINANCES SOCIÉTÉ
# =========================================================================== #
# L'ORGANIGRAMME (champ `manager_id`) est une VÉRITÉ CACHÉE : il ne doit JAMAIS
# être sérialisé dans une source (ni l'annuaire Excel, ni un dump JSON). Il vit
# uniquement ici, pour (1) générer des INDICES cohérents et (2) valider plus tard
# la reconstruction par les agents. Les sources n'exposent que des indices
# dispersés (postes + services dans l'annuaire, signatures/escalades dans les
# emails, références croisées ops AM<->clients & chauffeurs<->tournées).

# --- La société (la PME elle-même) ------------------------------------------ #
COMPANY = {
    "company_id": "CO-001",
    "legal_name": "Our Logistics Co SAS",
    "trade_name": "Our Logistics Co",
    "headquarters_city": "Paris",       # cohérent avec WH-1 (siège + entrepôt principal)
    "founded_year": 2011,
    "headcount": 15,                    # == len(EMPLOYEES)
    "ceo_employee_id": "EMP-001",       # le dirigeant (Philippe Caron)
    "domain": "ourlogisticsco.com",
}

# --- Employés + organigramme caché (15) ------------------------------------- #
# Règle structurelle à DEUX branches (cf. DATA_README "Reconstruction de l'orga") :
#   (1) le chef de chaque service (rang max du service, hors Direction) reporte
#       DIRECTEMENT au DG  -> rattachement INTER-service ;
#   (2) tout autre employé reporte, DANS SON PROPRE service, à la personne du
#       title_rank immédiatement supérieur  -> invariant : manager dans le même
#       org_unit. Un seul manager par niveau (rangs 2 et 3) -> candidat unique.
# title_rank : 1=DG, 2=Directeur, 3=Responsable, 4=Chargé/Chauffeur/Comptable.
EMPLOYEES = [
    # Direction
    {"employee_id": "EMP-001", "full_name": "Philippe Caron",
     "role_title": "Directeur Général", "org_unit": "Direction",
     "manager_id": None, "title_rank": 1,
     "email": "philippe.caron@ourlogisticsco.com",
     "hire_date": "2011-03-01", "monthly_gross_salary": 9500,
     "is_key_person": False},

    # Commercial (AM existants réutilisés -> un employé par AM distinct)
    {"employee_id": "EMP-002", "full_name": "Jules Bernard",
     "role_title": "Directeur Commercial", "org_unit": "Commercial",
     "manager_id": "EMP-001", "title_rank": 2,
     "email": "jules.bernard@ourlogisticsco.com",
     "hire_date": "2012-09-15", "monthly_gross_salary": 6500,
     "is_key_person": False},
    {"employee_id": "EMP-003", "full_name": "Sarah Martin",
     "role_title": "Responsable Grands Comptes", "org_unit": "Commercial",
     "manager_id": "EMP-002", "title_rank": 3,
     "email": "sarah.martin@ourlogisticsco.com",
     "hire_date": "2014-01-20", "monthly_gross_salary": 4800,
     "is_key_person": True},                 # ★ homme-clé (gère MedPharma, C001/C004)
    {"employee_id": "EMP-004", "full_name": "Clara Moreau",
     "role_title": "Chargée de clientèle", "org_unit": "Commercial",
     "manager_id": "EMP-003", "title_rank": 4,
     "email": "clara.moreau@ourlogisticsco.com",
     "hire_date": "2018-06-04", "monthly_gross_salary": 2800,
     "is_key_person": False},
    {"employee_id": "EMP-005", "full_name": "Paul Lefevre",
     "role_title": "Chargé de clientèle", "org_unit": "Commercial",
     "manager_id": "EMP-003", "title_rank": 4,
     "email": "paul.lefevre@ourlogisticsco.com",
     "hire_date": "2019-02-11", "monthly_gross_salary": 2700,
     "is_key_person": False},
    {"employee_id": "EMP-006", "full_name": "Emma Dubois",
     "role_title": "Chargée de clientèle", "org_unit": "Commercial",
     "manager_id": "EMP-003", "title_rank": 4,
     "email": "emma.dubois@ourlogisticsco.com",
     "hire_date": "2020-09-01", "monthly_gross_salary": 2750,
     "is_key_person": False},
    {"employee_id": "EMP-007", "full_name": "Hugo Petit",
     "role_title": "Chargé de clientèle", "org_unit": "Commercial",
     "manager_id": "EMP-003", "title_rank": 4,
     "email": "hugo.petit@ourlogisticsco.com",
     "hire_date": "2021-05-17", "monthly_gross_salary": 2650,
     "is_key_person": False},

    # Exploitation (chauffeurs fixés reliés à DRIVERS)
    {"employee_id": "EMP-008", "full_name": "Nadia Renard",
     "role_title": "Directrice de l'Exploitation", "org_unit": "Exploitation",
     "manager_id": "EMP-001", "title_rank": 2,
     "email": "nadia.renard@ourlogisticsco.com",
     "hire_date": "2012-11-05", "monthly_gross_salary": 6200,
     "is_key_person": False},
    {"employee_id": "EMP-009", "full_name": "Karim Benali",
     "role_title": "Responsable d'Exploitation", "org_unit": "Exploitation",
     "manager_id": "EMP-008", "title_rank": 3,
     "email": "karim.benali@ourlogisticsco.com",
     "hire_date": "2015-04-22", "monthly_gross_salary": 4200,
     "is_key_person": False},
    {"employee_id": "EMP-010", "full_name": "Thomas Girard",   # == DRIVERS[0].name
     "role_title": "Chauffeur", "org_unit": "Exploitation",
     "manager_id": "EMP-009", "title_rank": 4,
     "email": "thomas.girard@ourlogisticsco.com",
     "hire_date": "2017-08-28", "monthly_gross_salary": 2400,
     "is_key_person": False},
    {"employee_id": "EMP-011", "full_name": "Mehdi Faure",     # == DRIVERS[1].name
     "role_title": "Chauffeur", "org_unit": "Exploitation",
     "manager_id": "EMP-009", "title_rank": 4,
     "email": "mehdi.faure@ourlogisticsco.com",
     "hire_date": "2019-10-14", "monthly_gross_salary": 2300,
     "is_key_person": False},
    {"employee_id": "EMP-012", "full_name": "David Olivier",   # == DRIVERS[2].name
     "role_title": "Chauffeur", "org_unit": "Exploitation",
     "manager_id": "EMP-009", "title_rank": 4,
     "email": "david.olivier@ourlogisticsco.com",
     "hire_date": "2022-03-07", "monthly_gross_salary": 2250,
     "is_key_person": False},

    # Comptabilité (chef de service = Responsable, rang 3 -> reporte au DG)
    {"employee_id": "EMP-013", "full_name": "Sophie Lambert",
     "role_title": "Responsable Comptabilité", "org_unit": "Comptabilité",
     "manager_id": "EMP-001", "title_rank": 3,
     "email": "sophie.lambert@ourlogisticsco.com",
     "hire_date": "2013-06-10", "monthly_gross_salary": 4000,
     "is_key_person": False},
    {"employee_id": "EMP-014", "full_name": "Nathalie Roux",
     "role_title": "Comptable", "org_unit": "Comptabilité",
     "manager_id": "EMP-013", "title_rank": 4,
     "email": "nathalie.roux@ourlogisticsco.com",
     "hire_date": "2018-01-08", "monthly_gross_salary": 2900,
     "is_key_person": False},

    # RH (service mono-personne ; chef de service -> reporte au DG)
    {"employee_id": "EMP-015", "full_name": "Olivier Mercier",
     "role_title": "Responsable RH", "org_unit": "RH",
     "manager_id": "EMP-001", "title_rank": 3,
     "email": "olivier.mercier@ourlogisticsco.com",
     "hire_date": "2016-09-19", "monthly_gross_salary": 3900,
     "is_key_person": False},
]

# Marque l'homme-clé (Sarah Martin) comme enregistrement de scénario : il fait
# partie du récit SH-2049 (escalade MedPharma). Le reste des employés = pas de flag.
for _e in EMPLOYEES:
    if _e["is_key_person"]:
        _e["_scenario"] = True
        _e["_scenario_role"] = "key_person"

# Liste des services distincts (dérivée, pratique pour la doc / l'UI plus tard).
ORG_UNITS = sorted({e["org_unit"] for e in EMPLOYEES})

# --- Dépendances clés (hommes-clés / points de défaillance) ----------------- #
# Ne FABRIQUE pas un fait : NOMME une réalité déjà présente (Sarah Martin est l'AM
# de C001/C004 et MedPharma a la strategic_value max).
KEY_DEPENDENCIES = [
    {"key_dependency_id": "KD-001", "type": "key_person",
     "employee_id": "EMP-003", "customer_id": "C001",
     "note": "Gère seule le plus gros compte (MedPharma).",
     "_scenario": True, "_scenario_role": "key_person"},
]


# --- Finances société : CA & concentration CALCULÉS depuis les factures ------ #
def total_revenue() -> int:
    """CA total = somme des montants de TOUTES les factures (tous statuts)."""
    return sum(i["amount"] for i in INVOICES)


def revenue_by_customer() -> dict:
    """{customer_id: CA cumulé} via order_id -> customer_id (toutes factures)."""
    out: dict[str, int] = {}
    for inv in INVOICES:
        order = ORDER_BY_ID.get(inv["order_id"])
        if not order:
            continue
        cid = order["customer_id"]
        out[cid] = out.get(cid, 0) + inv["amount"]
    return out


def revenue_concentration() -> list[dict]:
    """Part du CA par client, triée décroissante.

    [{customer_id, name, revenue, share}], share = revenue / total_revenue.
    Tout est dérivé de INVOICES (rien n'est saisi en dur).
    """
    by_cust = revenue_by_customer()
    total = total_revenue() or 1
    rows = [
        {"customer_id": cid, "name": CUSTOMER_BY_ID[cid]["name"],
         "revenue": rev, "share": rev / total}
        for cid, rev in by_cust.items()
    ]
    rows.sort(key=lambda r: r["revenue"], reverse=True)
    return rows


# --- Snapshot de gestion (agrégats société SAISIS, plausibles, non calibrés) - #
# Le CA (annual_revenue) reste None ici : il se dérive via total_revenue().
# Le décalage de trésorerie (CashflowGap) émerge de dso_days - dpo_days : on ne le
# pré-calcule pas. payroll_monthly est cohérent avec sum(monthly_gross_salary)
# (~60k) majoré du chargement patronal (~1.42x).
FINANCIAL_SUMMARY = {
    "company_id": "CO-001",
    "period": "12 derniers mois glissants",
    "annual_revenue": None,             # dérivé : total_revenue()
    "payroll_monthly": 85000,           # ≈ 1.42 x somme des salaires bruts
    "fleet_leasing_monthly": 14000,     # ~10 véhicules en leasing
    "fuel_monthly": 9000,
    "other_opex_monthly": 7000,
    "gross_margin_pct": 0.16,
    "dso_days": 68,                     # encaissement clients (Days Sales Outstanding)
    "dpo_days": 38,                     # paiement fournisseurs (Days Payable Outstanding)
    "cash_on_hand": 145000,
}


# =========================================================================== #
# 3. LISTES CONSOLIDÉES + API publique
# =========================================================================== #
ORDERS = SCENARIO_ORDERS + NOISE_ORDERS
SHIPMENTS = SCENARIO_SHIPMENTS + NOISE_SHIPMENTS
SHIPMENT_ITEMS = SCENARIO_SHIPMENT_ITEMS + NOISE_SHIPMENT_ITEMS
INVOICES = SCENARIO_INVOICES + NOISE_INVOICES
INVENTORY = SCENARIO_INVENTORY + NOISE_INVENTORY
CONTRACTS = SCENARIO_CONTRACTS + NOISE_CONTRACTS
EMAILS = SCENARIO_EMAILS + NOISE_EMAILS

# Index pratiques
CUSTOMER_BY_ID = {c["customer_id"]: c for c in CUSTOMERS}
PRODUCT_BY_SKU = {p["sku"]: p for p in PRODUCTS}
CARRIER_BY_ID = {c["carrier_id"]: c for c in CARRIERS}
WAREHOUSE_BY_ID = {w["warehouse_id"]: w for w in WAREHOUSES}
ORDER_BY_ID = {o["order_id"]: o for o in ORDERS}


def strip_internal(record: dict) -> dict:
    """Retourne une copie du record sans les clés internes `_scenario*`.

    À utiliser par tous les sérialiseurs de sources réalistes (Odoo, Dashdoc,
    emails) pour ne pas dénaturer les formats.
    """
    return {k: v for k, v in record.items() if not k.startswith("_")}


def strip_internal_list(records: list[dict]) -> list[dict]:
    return [strip_internal(r) for r in records]


def scenario_records() -> list[dict]:
    """Tous les enregistrements portant `_scenario: True`, à plat."""
    out = []
    for coll in (CUSTOMERS, PRODUCTS, ORDERS, SHIPMENTS, SHIPMENT_ITEMS, CARRIERS,
                 WAREHOUSES, INVENTORY, CONTRACTS, INVOICES, EMAILS, CARRIER_BACKUP_MATRIX,
                 EMPLOYEES, KEY_DEPENDENCIES):
        out.extend([r for r in coll if r.get("_scenario")])
    return out


def scenario_ids() -> dict:
    """IDs métier du scénario, par type — sert au _scenario_manifest.json."""
    return {
        "customers": [c["customer_id"] for c in SCENARIO_CUSTOMERS],
        "products": [p["sku"] for p in SCENARIO_PRODUCTS],
        "orders": [o["order_id"] for o in SCENARIO_ORDERS],
        "po_numbers": [o["po_number"] for o in SCENARIO_ORDERS],
        "shipments": [s["shipment_id"] for s in SCENARIO_SHIPMENTS],
        "carriers": [c["carrier_id"] for c in SCENARIO_CARRIERS],
        "warehouses": [w["warehouse_id"] for w in SCENARIO_WAREHOUSES],
        "contracts": [c["contract_id"] for c in SCENARIO_CONTRACTS],
        "invoices": [i["invoice_id"] for i in SCENARIO_INVOICES],
        "emails": [e["id"] for e in SCENARIO_EMAILS],
        "hot_shipment": "SH-2049",
        "hot_invoice": "INV-7742",
        "hot_customer": "C001",
        "hot_po": "PO-8821",
    }


def counts() -> dict:
    return {
        "customers": len(CUSTOMERS), "products": len(PRODUCTS),
        "orders": len(ORDERS), "shipments": len(SHIPMENTS),
        "carriers": len(CARRIERS), "vehicles": len(VEHICLES),
        "drivers": len(DRIVERS), "warehouses": len(WAREHOUSES),
        "inventory": len(INVENTORY), "suppliers": len(SUPPLIERS),
        "contracts": len(CONTRACTS), "invoices": len(INVOICES),
        "claims": len(CUSTOMER_CLAIMS), "sla_penalties": len(SLA_PENALTY_LOG),
        "legacy_contacts": len(LEGACY_CONTACTS), "emails": len(EMAILS),
        "employees": len(EMPLOYEES), "key_dependencies": len(KEY_DEPENDENCIES),
    }


if __name__ == "__main__":
    import json
    print("TODAY =", TODAY.isoformat())
    print("Counts:", json.dumps(counts(), indent=2))
    print("Scenario IDs:", json.dumps(scenario_ids(), indent=2))
