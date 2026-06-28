"""P3 — Relationship Discovery (Sonnet 4.6).

Découpée en GROUPES d'arêtes. Reçoit la liste des `id` d'entités (de P2) pour ne jamais cibler
un nœud absent. Le groupe RH reconstruit l'organigramme depuis le texte BRUT des emails
(`eml_raw`), conformément à la frontière §9.
"""

from __future__ import annotations

import json

from .._agent import load_prompt, run_pass_resilient
from ..blackboard import Blackboard
from ..contracts import RelationshipsOutput
from ..logging_ui import RunLogger
from ..models import MAX_TURNS, PASS_MODEL, SYSTEM_PROMPTS
from ..tools import mcp_clients as mc
from ..tools.readers import TOOL_NAMES as R

CHUNKS = [
    {
        "label": "opérationnel (places/creates/bills/operated_by/contains/operates/mandates/stored_in/fulfilled_by/governed_by)",
        "tools": mc.tool_names(mc.ODOO) + mc.tool_names(mc.DASHDOC) + [R["pdf_text"], R["xlsx_sheet"]],
        "instruction": (
            "Émets les arêtes opérationnelles : places, creates (via sale.order.client_order_ref "
            "→ order), bills (account.move.invoice_origin == client_order_ref → order), "
            "operated_by (transport.carrier.name → carrier:{slug}), departs_from (loading_address "
            "→ warehouse), contains (deliveries[].sku → product, attributes.quantity), operates "
            "(vehicle.carrier_id), mandates (driver.carrier_id), stored_in (excel "
            "warehouse_inventory_snapshot.xlsx : product→warehouse, attributes available/reserved). "
            "Émets fulfilled_by UNIQUEMENT pour SH-2049 via pdf_text "
            "filename='DeliveryNote-SH-2049.pdf' (order:o-881 → shipment:sh-2049). Émets "
            "governed_by (customer → contract:ct-001) via le PDF SLA."
        ),
    },
    {
        "label": "annexe+emails+docs (filed/concerns/incurred/mentions/references)",
        "tools": [R["sqlite_rows"]] + mc.tool_names(mc.EMAIL) + [R["pdf_text"]],
        "instruction": (
            "Émets : filed (customer_claims.customer_ref → claim), concerns (claim/penalty "
            ".shipment_ref → shipment, si présent), incurred (sla_penalty_log.customer_ref → "
            "penalty). Émets mentions : pour chaque email (`list_emails`), repère les SH-#### et "
            "PO-#### cités dans subject/body/labels → email mentions shipment/po. Émets references "
            ": pour chaque DOCUMENT PDF, les SH/PO/INV/Customer cités dans le texte → document "
            "references l'entité."
        ),
    },
    {
        "label": "rh+finance (employs/reports_to/manages/is_a/has_financials/contributes_to/implies/feeds)",
        "tools": [R["xlsx_sheet"], R["eml_raw"]] + mc.tool_names(mc.ODOO) + mc.tool_names(mc.DASHDOC),
        "instruction": (
            "Émets employs (company → chaque employee). Reconstruis reports_to (organigramme) "
            "selon la règle à 2 branches : lis company_directory.xlsx (role_title/org_unit), "
            "déduis les rangs, et CONFIRME les liens via le contenu brut des emails internes "
            "(eml_raw : liste d'abord avec filename vide, puis lis les emails RH/escalade). "
            "confidence 0.70 (ou 0.85 si confirmé par escalade email), jamais plus, + "
            "open_question. Émets manages (Odoo res.partner.user_id == full_name d'un employee → "
            "employee manages customer). Émets is_a (driver.name == full_name d'un employee → "
            "driver is_a employee, confidence 0.9 + open_question). Émets has_financials (company "
            "→ financial:summary), contributes_to (chaque invoice → financial:revenue-concentration), "
            "implies (financial:summary → financial:cashflow-gap), feeds (chaque supplier → "
            "financial:cashflow-gap, confidence 0.85)."
        ),
    },
]


async def run(bb: Blackboard, logger: RunLogger) -> None:
    logger.banner("p3", "Relationship Discovery", PASS_MODEL["p3"])
    base = load_prompt("p3_relationships.md")
    id_index = [{"id": e["id"], "type": e["type"], "name": e["name"]}
                for e in bb.entities_proposed]
    id_block = "\n\nENTITÉS DISPONIBLES (id | type | name) — ne cible QUE ces id :\n```json\n" \
        + json.dumps(id_index, ensure_ascii=False) + "\n```\n"
    # Reprise : on repart des relations déjà persistées et on saute les chunks aboutis.
    for chunk in CHUNKS:
        if bb.chunk_done("p3", chunk["label"]):
            logger.info(f"groupe déjà fait (sauté) : {chunk['label']}")
            continue
        logger.info(f"groupe : {chunk['label']}")
        task = base + "\n" + chunk["instruction"] + id_block + \
            "\nRéponds par {\"relationships\": [...]}."
        obj = await run_pass_resilient(
            pass_id="p3", model=PASS_MODEL["p3"], system_prompt=SYSTEM_PROMPTS["p3"],
            task_prompt=task, allowed_tools=chunk["tools"], logger=logger,
            max_turns=MAX_TURNS["p3"])
        parsed = RelationshipsOutput.model_validate(obj)
        rels = [r.model_dump() for r in parsed.relationships]
        bb.relationships_proposed.extend(rels)
        bb.mark_chunk_done("p3", chunk["label"])
        bb.checkpoint()  # persiste DÈS qu'un chunk aboutit
        logger.summary(f"{chunk['label']} → {len(rels)} relations")
    bb.log("p3", "relationships", f"{len(bb.relationships_proposed)} relations proposées")
    logger.summary(f"TOTAL P3 : {len(bb.relationships_proposed)} relations proposées")
