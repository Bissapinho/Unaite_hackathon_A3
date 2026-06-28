# P2 — Entity Discovery (calibration partagée)

Tu identifies les entités métier canoniques et tu les émets au **format §4**. Tu travailles
sur un GROUPE de sources précisé en bas. Utilise les outils MCP/readers pour lire les données
RÉELLES (ne te fie pas qu'à l'inventaire). Montre ton travail en appelant les outils.

## Format §4 (exemple FICTIF neutre — ne reprends jamais ces valeurs)

```json
{"entities": [
  {
    "id": "customer:acme",
    "type": "Customer",
    "name": "ACME Corp",
    "layer": "operational",
    "attributes": {"priority_tier": "Gold", "strategic_value": 50000, "account_manager": "Jane Doe"},
    "sources": ["odoo.res_partner:C999"],
    "confidence": 0.95,
    "evidence": ["odoo res.partner.name = 'ACME Corp' (partner_id=C999)"],
    "open_questions": []
  }
]}
```

## Conventions d'`id` (à respecter EXACTEMENT — `slug` = minuscules, non-alphanum → '-')

| Type | id | exemple |
|---|---|---|
| Customer | `customer:{slug(name)}` | `customer:medpharma` |
| Supplier | `supplier:{slug(supplier_id)}` | `supplier:sup-01` |
| Product | `product:{slug(sku)}` | `product:pharma-22` |
| Warehouse | `warehouse:{slug(warehouse_id)}` | `warehouse:wh-1` |
| Carrier | `carrier:{slug(name)}` | `carrier:coldroad` |
| Vehicle | `vehicle:{slug(license_plate)}` | `vehicle:033-tlc-96` |
| Driver | `driver:{slug(driver_id)}` | `driver:drv-001` |
| Order | `order:{slug(order_id)}` | `order:o-881` |
| PurchaseOrder | `po:{slug(po_number)}` | `po:po-8821` |
| Invoice | `invoice:{slug(invoice_id)}` | `invoice:inv-7742` |
| Shipment | `shipment:{slug(shipment_id)}` | `shipment:sh-2049` |
| Contract | `contract:ct-001` (numéro non sourcé, assumé) | `contract:ct-001` |
| Claim | `claim:{id}` (id numérique SQLite) | `claim:1` |
| PenaltyLogEntry | `penalty:{id}` | `penalty:1` |
| Email | `email:{slug(id)}` | `email:em-001` |
| Document | `document:{slug(doc_name_sans_extension)}` | `document:sla-medpharma-coldchain` |
| Company | `company:our-logistics-co` | (raison sociale déduite du domaine email) |
| Employee | `employee:{slug(full_name)}` | `employee:sarah-martin` |
| FinancialSummary | `financial:summary` | |
| RevenueConcentration | `financial:revenue-concentration` | |
| CashflowGap | `financial:cashflow-gap` | |

## `layer` par type
- `operational` : Customer, Supplier, Product, Warehouse, Carrier, Vehicle, Driver, Order,
  PurchaseOrder, Invoice, Shipment, Contract, Claim, PenaltyLogEntry, Email, Document.
- `hr` : Company, Employee.
- `financial` : FinancialSummary, RevenueConcentration, CashflowGap.

## Mapping des champs sources → canonique (DATA_README)
- Odoo res.partner (clients, `customer_rank>0`) : `partner_id`→customer_id, `name`,
  `category`→priority_tier, `user_id`→account_manager, `x_strategic_value`→strategic_value,
  `industry_id`→industry.
- Odoo res.partner.suppliers : `partner_id`→supplier_id, `name`, `category`,
  `property_payment_term_id`→payment_term_days.
- Odoo sale.order : `order_id`, `partner_id`→customer_id, `client_order_ref`→po_number,
  `date_order`→order_date, `state`→status. **Chaque sale.order avec un client_order_ref donne
  AUSSI une entité PurchaseOrder** (po:{slug(po_number)}).
- Odoo account.move : `move_id`→invoice_id, `invoice_origin`→po_number, `partner_id`,
  `amount_total`→amount, `currency_id`→currency, `payment_state`→status
  (`not_paid`→"Pending", `paid`→"Paid").
- Odoo product.product : `product_id`→sku, `name`, `categ_id`→category, `x_temp_min/max`→
  temperature_min/max, `list_price`→unit_value.
- Dashdoc transports : `uid`→shipment_id, `status`, `unloading_address`→destination,
  `is_cold_chain`→temperature_controlled, `temperature_setpoint.{min,max}`,
  `tracking.eta`→estimated_arrival, `requested_vehicle`. L'entrepôt d'origine est dans
  `loading_address` (ex. "Paris WH-1, Paris" → warehouse_id=WH-1, name="Paris WH-1", city).
- Dashdoc carriers/vehicles/drivers : champs homonymes.
- SQLite : `customer_claims`, `sla_penalty_log`, `legacy_contacts`.
- Excel `company_directory.xlsx` : Matricule→employee_id, Nom→full_name, Poste→role_title,
  Service→org_unit, Email→email, Date d'entrée→hire_date.

## Résolution floue (legacy → client)
Les `legacy_contacts` SQLite contiennent des noms « sales » (ex. "Med Pharma SARL"). Compare
chaque `raw_name` aux noms clients Odoo avec l'outil `name_similarity`. **Fusionne** un legacy
dans le client canonique si la similarité est élevée (seuil ~0.82) ET confirmée par le domaine
email, OU si le nom est quasi identique (≥0.93). N'ajoute PAS de nœud séparé pour le legacy :
ajoute sa référence dans `sources` et son rapprochement dans `evidence` du client. Un legacy
non rapprochable (bruit) est ignoré (pas de faux positif).

## Provenance & confidence
- Sourcé directement : confidence 0.95 (0.97 si recoupé par 2+ sources).
- Lu d'un PDF (texte) : 0.9.
- `sources` cite la source précise (ex. `odoo.res_partner:C001`, `dashdoc.transports:SH-2049`,
  `sqlite.legacy_contacts:3 ('Med Pharma SARL')`, `pdf.SLA-MedPharma-ColdChain`, `email:EM-001`,
  `excel.company_directory:E-007`).

Réponds UNIQUEMENT par `{"entities": [...]}`. Pas de prose.

---

GROUPE À TRAITER :
