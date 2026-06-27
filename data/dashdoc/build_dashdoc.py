"""build_dashdoc.py — Génère un dump Dashdoc-like (vision opérationnelle transport).

Source de vérité unique : data/canonical.py (NE PAS modifier).
Vocabulaire Dashdoc-like reconstruit à la main depuis les enregistrements canoniques.
Idempotent, lançable seul :
    .venv/bin/python data/dashdoc/build_dashdoc.py
"""

import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from data import canonical as C

import json


def _address(warehouse_id: str) -> str:
    """Nom + ville de l'entrepôt, ex. 'Paris WH-1, Paris'."""
    wh = C.WAREHOUSE_BY_ID.get(warehouse_id)
    if wh is None:
        return warehouse_id
    return f"{wh['name']}, {wh['city']}"


def _items_for(shipment_id: str) -> list[dict]:
    return [
        {"sku": it["sku"], "quantity": it["quantity"]}
        for it in C.SHIPMENT_ITEMS
        if it["shipment_id"] == shipment_id
    ]


def _temperature_setpoint(deliveries: list[dict], is_cold_chain: bool):
    """Setpoint {min,max} dérivé du SKU du premier delivery ; null sinon."""
    if not is_cold_chain or not deliveries:
        return None
    first_sku = deliveries[0]["sku"]
    product = C.PRODUCT_BY_SKU.get(first_sku)
    if product is None:
        return None
    tmin = product.get("temperature_min")
    tmax = product.get("temperature_max")
    if tmin is None or tmax is None:
        return None
    return {"min": tmin, "max": tmax}


def build_transport(shipment: dict) -> dict:
    shipment_id = shipment["shipment_id"]
    is_cold_chain = shipment["temperature_controlled"]
    deliveries = _items_for(shipment_id)
    carrier = C.CARRIER_BY_ID.get(shipment["carrier_id"], {})
    return {
        "uid": shipment_id,
        "status": shipment["status"],
        "loading_address": _address(shipment["origin_warehouse"]),
        "unloading_address": shipment["destination"],
        "carrier": {"name": carrier.get("name")},
        "requested_vehicle": "frigo" if is_cold_chain else "standard",
        "deliveries": deliveries,
        "tracking": {"eta": shipment["estimated_arrival"]},
        "is_cold_chain": is_cold_chain,
        "temperature_setpoint": _temperature_setpoint(deliveries, is_cold_chain),
    }


def build_dump() -> dict:
    return {
        "transports": [build_transport(s) for s in C.SHIPMENTS],
        "vehicles": [
            {
                "license_plate": v["license_plate"],
                "type": v["type"],
                "year": v["year"],
                "is_refrigerated": v["is_refrigerated"],
            }
            for v in C.VEHICLES
        ],
        "drivers": [
            {
                "driver_id": d["driver_id"],
                "name": d["name"],
                "certifications": d["certifications"],
            }
            for d in C.DRIVERS
        ],
        "carriers": [
            {
                "carrier_id": c["carrier_id"],
                "name": c["name"],
                "service_type": c["service_type"],
                "reliability_score": c["reliability_score"],
            }
            for c in C.CARRIERS
        ],
    }


def main():
    dump = build_dump()
    out_path = ROOT / "data" / "dashdoc" / "dashdoc_dump.json"
    out_path.write_text(json.dumps(dump, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Dashdoc dump écrit : {out_path}")
    print(
        f"  transports={len(dump['transports'])} "
        f"vehicles={len(dump['vehicles'])} "
        f"drivers={len(dump['drivers'])} "
        f"carriers={len(dump['carriers'])}"
    )
    sh2049 = next((t for t in dump["transports"] if t["uid"] == "SH-2049"), None)
    if sh2049:
        print(
            f"  SH-2049: carrier={sh2049['carrier']['name']} "
            f"cold_chain={sh2049['is_cold_chain']} "
            f"setpoint={sh2049['temperature_setpoint']} "
            f"deliveries={sh2049['deliveries']}"
        )


if __name__ == "__main__":
    main()
