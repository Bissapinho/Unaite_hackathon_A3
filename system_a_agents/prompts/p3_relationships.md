# P3 — Relationship Discovery (calibration partagée)

Tu infères les ARÊTES entre entités déjà découvertes (leurs `id` te sont fournis). Chaque
arête porte `source`, `target` (des `id` existants), `type`, `confidence`, `evidence`,
`open_questions`. N'émets JAMAIS une arête vers un `id` absent de la liste fournie. Utilise
les outils pour justifier (montre ton travail). Tu travailles sur un GROUPE précisé en bas.

Réponds UNIQUEMENT par `{"relationships": [...]}`.

## Catalogue des relations (avec id de référence — `slug` = minuscules)

**Opérationnel (Odoo + Dashdoc + PDF + Excel inventaire)**
- `customer:{c} places po:{p}` — le client de la sale.order a ce client_order_ref. conf 0.95.
- `po:{p} creates order:{o}` — client_order_ref → order_id. conf 0.95.
- `invoice:{i} bills order:{o}` — account.move.invoice_origin == sale.order.client_order_ref.
  conf 0.95.
- `shipment:{s} operated_by carrier:{ca}` — dashdoc transport.carrier.name. conf 0.95.
- `shipment:{s} departs_from warehouse:{w}` — loading_address. conf 0.95.
- `shipment:{s} contains product:{pr}` — deliveries[].sku (porte `attributes.quantity`). conf 0.95.
- `carrier:{ca} operates vehicle:{v}` — vehicle.carrier_id. conf 0.95.
- `carrier:{ca} mandates driver:{d}` — driver.carrier_id. conf 0.95.
- `product:{pr} stored_in warehouse:{w}` — excel inventaire (porte available/reserved_units). conf 0.95.
- `order:{o} fulfilled_by shipment:{s}` — **SH-2049 UNIQUEMENT**, via le PDF DeliveryNote qui
  relie le Shipment au PO (le TMS n'expose aucun order_id). conf 0.9 + open_question.
- `customer:{c} governed_by contract:ct-001` — PDF SLA nominatif. conf 0.9.

**SQLite + emails + documents**
- `customer:{c} filed claim:{id}` — customer_claims.customer_ref. conf 0.9.
- `claim:{id} concerns shipment:{s}` — customer_claims.shipment_ref (si présent). conf 0.9.
- `customer:{c} incurred penalty:{id}` — sla_penalty_log.customer_ref. conf 0.9.
- `penalty:{id} concerns shipment:{s}` — sla_penalty_log.shipment_ref. conf 0.9.
- `email:{e} mentions shipment:{s}` / `email:{e} mentions po:{p}` — SH-…/PO-… cités dans
  sujet/corps/labels. conf 0.88.
- `document:{doc} references shipment:{s}|po:{p}|invoice:{i}|customer:{c}` — entité citée dans
  le texte du PDF. conf 0.95.

**RH + finances**
- `company:our-logistics-co employs employee:{emp}` — chaque employé de l'annuaire. conf 0.95.
- `employee:{emp} reports_to employee:{mgr}` — ORGANIGRAMME reconstruit (règle ci-dessous).
- `employee:{emp} manages customer:{c}` — l'account_manager Odoo (user_id) == full_name
  d'un employé (Commercial). conf 0.95.
- `driver:{d} is_a employee:{emp}` — nom du chauffeur == full_name d'un employé (exact). conf 0.9
  + open_question (rapprochement par nom, pas d'id partagé).
- `company:our-logistics-co has_financials financial:summary`. conf 0.95.
- `invoice:{i} contributes_to financial:revenue-concentration` — chaque facture entre dans le
  CA. conf 0.95.
- `financial:summary implies financial:cashflow-gap` — DSO/DPO. conf 0.9.
- `supplier:{su} feeds financial:cashflow-gap` — conditions de paiement fournisseur → DPO. conf 0.85.

## Reconstruction de l'ORGANIGRAMME (`reports_to`) — règle à 2 branches

L'organigramme n'est dans AUCUNE source (l'annuaire n'a pas de colonne manager). Reconstruis-le.

1. **Rang de titre** (déduit du `role_title`) : `Directeur Général`/`Directrice Générale` = 1 ;
   `Directeur/Directrice <X>` = 2 ; `Responsable <X>` = 3 ; sinon (`Chargé(e)`, `Chauffeur`,
   `Comptable`…) = 4.
2. **Le DG (rang 1) n'a pas de manager** (racine — pas d'arête `reports_to`).
3. **Branche chef de service → DG** : dans chaque service (`org_unit`) hors Direction, la
   personne du rang le PLUS ÉLEVÉ (le plus petit numéro) reporte DIRECTEMENT au Directeur Général.
4. **Branche intra-service** : tout autre employé reporte, DANS son propre service, à la personne
   du rang immédiatement supérieur (candidat unique).
5. `confidence` = **0.70** par défaut (lien inféré) ; **0.85** si une escalade/délégation email
   entre les deux personnes confirme le lien (lis le contenu BRUT via `eml_raw` : signatures
   « Nom — Poste », phrases « je transmets à… », « je remonte au DG… »). **Jamais > 0.85.**
   Toujours au moins une `open_question` (« lien reconstruit par inférence, non écrit dans une
   source RH »).

`target` d'un `reports_to` = `employee:{slug(full_name_du_manager)}`.

---

GROUPE À TRAITER :
