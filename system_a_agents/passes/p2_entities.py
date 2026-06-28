"""P2 — Entity Discovery (Sonnet 4.6).

Découpée en GROUPES de sources (sous-requêtes) pour fiabiliser l'extraction de ~200 entités
et garder chaque sortie JSON digeste (décision d'ingénierie tracée dans CALIBRATION.md). Chaque
groupe émet des entités au format §4 ; on agrège et on valide.
"""

from __future__ import annotations

from .._agent import load_prompt, run_pass_resilient
from ..blackboard import Blackboard
from ..contracts import EntitiesOutput
from ..logging_ui import RunLogger
from ..models import MAX_TURNS, PASS_MODEL, SYSTEM_PROMPTS
from ..tools import mcp_clients as mc
from ..tools.readers import TOOL_NAMES as R

CHUNKS = [
    {
        "label": "odoo-core (clients+fuzzy, fournisseurs, produits)",
        "tools": mc.tool_names(mc.ODOO) + [R["sqlite_rows"], R["name_similarity"]],
        "instruction": (
            "Émets les entités CUSTOMER (Odoo `list_partners`, customer_rank>0), SUPPLIER "
            "(`list_suppliers`), PRODUCT (`list_products`). Pour les CUSTOMER, fais la "
            "résolution floue : lis `legacy_contacts` (sqlite_rows table='legacy_contacts'), "
            "compare chaque raw_name aux noms clients avec name_similarity, et FUSIONNE les "
            "matches dans le client (ajoute la source legacy + une evidence de rapprochement). "
            "N'ajoute pas de nœud pour les legacy."
        ),
    },
    {
        "label": "dashdoc (carriers, vehicles, drivers, warehouses, shipments)",
        "tools": mc.tool_names(mc.DASHDOC),
        "instruction": (
            "Émets les entités CARRIER (`list_carriers`), VEHICLE (`list_vehicles`), DRIVER "
            "(`list_drivers`), et SHIPMENT (`list_transports`). Déduis les WAREHOUSE depuis le "
            "`loading_address` des transports (ex. 'Paris WH-1, Paris' → warehouse:wh-1, "
            "name='Paris WH-1', city='Paris') : une entité par warehouse_id distinct."
        ),
    },
    {
        "label": "odoo-flux (orders, purchase orders, invoices)",
        "tools": mc.tool_names(mc.ODOO),
        "instruction": (
            "Émets les entités ORDER (`list_sale_orders`), et pour chaque order avec un "
            "client_order_ref, une entité PURCHASEORDER (po:{slug(po_number)}). Émets les "
            "INVOICE (`list_invoices`) : status not_paid→'Pending', paid→'Paid'."
        ),
    },
    {
        "label": "annexe+docs (claims, penalties, documents PDF, emails, contrat SLA)",
        "tools": [R["sqlite_rows"], R["pdf_text"]] + mc.tool_names(mc.EMAIL),
        "instruction": (
            "Émets : CLAIM (sqlite_rows table='customer_claims', id=`claim:{id}`), "
            "PENALTYLOGENTRY (table='sla_penalty_log', id=`penalty:{id}`), DOCUMENT (un par PDF, "
            "pdf_text sans filename pour la liste ; id=`document:{slug(nom_sans_extension)}`), "
            "EMAIL (`list_emails`, id=`email:{slug(id)}`, attributs from/to/subject/received_at/"
            "labels). Émets AUSSI l'entité CONTRACT `contract:ct-001` à partir du PDF SLA "
            "(pdf_text filename='SLA-MedPharma-ColdChain.pdf') : lis dans le TEXTE la pénalité "
            "€/h, la deadline, la plage de température, l'escalade account manager ; attributs "
            "customer_name, sla_deadline, late_penalty_per_hour, temperature_min/max, "
            "escalation_to_account_manager. confidence 0.9 + open_question (numéro de contrat non "
            "sourcé)."
        ),
    },
    {
        "label": "rh+finance (company, employees, entités financières)",
        "tools": [R["xlsx_sheet"]],
        "instruction": (
            "Émets COMPANY `company:our-logistics-co` (layer hr) : déduis le domaine email "
            "partagé des employés, headcount, ceo (déduit plus tard), headquarters_city='Paris' ; "
            "confidence 0.9 + open_question (raison sociale déduite du domaine). Émets un EMPLOYEE "
            "par ligne de `company_directory.xlsx` (xlsx_sheet), id=`employee:{slug(full_name)}`, "
            "attributs role_title, org_unit, email, hire_date, et title_rank (1 Directeur Général, "
            "2 Directeur/Directrice, 3 Responsable, 4 sinon). Émets enfin les 3 entités "
            "financières (layer financial) en COQUILLES (attributs minimaux, complétés ensuite) : "
            "`financial:summary` (FinancialSummary), `financial:revenue-concentration` "
            "(RevenueConcentration), `financial:cashflow-gap` (CashflowGap) ; sources "
            "['excel.finances_summary'] ou ['derived.odoo.account_move'], evidence courte, "
            "confidence 0.9."
        ),
    },
]


async def run(bb: Blackboard, logger: RunLogger) -> None:
    logger.banner("p2", "Entity Discovery", PASS_MODEL["p2"])
    base = load_prompt("p2_entities.md")
    # Reprise : on repart des entités DÉJÀ persistées (chunks aboutis lors d'un run précédent
    # interrompu) et on saute ces chunks — on ne re-paie jamais ce qui a réussi (CLAUDE §8 coût).
    for chunk in CHUNKS:
        if bb.chunk_done("p2", chunk["label"]):
            logger.info(f"groupe déjà fait (sauté) : {chunk['label']}")
            continue
        logger.info(f"groupe : {chunk['label']}")
        task = base + "\n" + chunk["instruction"] + "\n\nRéponds par {\"entities\": [...]}."
        obj = await run_pass_resilient(
            pass_id="p2", model=PASS_MODEL["p2"], system_prompt=SYSTEM_PROMPTS["p2"],
            task_prompt=task, allowed_tools=chunk["tools"], logger=logger,
            max_turns=MAX_TURNS["p2"])
        parsed = EntitiesOutput.model_validate(obj)
        ents = [e.model_dump() for e in parsed.entities]
        bb.entities_proposed.extend(ents)
        bb.mark_chunk_done("p2", chunk["label"])
        bb.checkpoint()  # persiste DÈS qu'un chunk aboutit → interruption = travail conservé
        logger.summary(f"{chunk['label']} → {len(ents)} entités")
    bb.log("p2", "entities", f"{len(bb.entities_proposed)} entités proposées")
    logger.summary(f"TOTAL P2 : {len(bb.entities_proposed)} entités proposées")
