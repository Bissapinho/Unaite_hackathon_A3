# Prompt Claude Code — Brique 1 : Data synthétique (scénario SH-2049)

> **Comment utiliser ce prompt :** copie tout le contenu sous la ligne `===` dans Claude Code, à la racine du projet. C'est une brique autonome : elle ne produit QUE la data + les sources (mocks MCP, DB, fichiers). L'ontologie, les agents et l'UI sont des briques séparées.

---

===

## Rôle et objectif

Tu es un ingénieur qui prépare les **données synthétiques** d'un MVP de hackathon : un *agentic ontology builder* pour une société de transport/logistique. Cette tâche se limite STRICTEMENT à produire les données et les sources qui les exposent. **Ne code NI l'ontologie, NI les agents, NI l'UI.** Ne fais rien de plus que ce qui est listé ici.

Le but : alimenter une démo où un agent ingère des sources **hétérogènes et réparties de façon réaliste** (un TMS, un ERP, une petite base SQL annexe, des fichiers, des emails) et reconstruit un graphe métier autour d'un incident. Le scénario fil rouge est le retard de la livraison **SH-2049**.

### Deux exigences transverses (les plus importantes)

1. **Cohérence inter-sources.** Les mêmes entités (MedPharma, PO-8821, SH-2049, INV-7742, PHARMA-22…) apparaissent dans plusieurs sources, avec des **identifiants métier identiques** mais des **schémas/noms de champs différents** selon la source. C'est ce recoupement (mêmes IDs, vocabulaires différents) qui prouvera la valeur de l'ontologie et forcera l'entity resolution. Toute incohérence non intentionnelle sur les IDs/montants/dates est un bug.

2. **Répartition réaliste des sources.** Une PME de transport ne stocke PAS tout dans une base SQL maison. Respecte cette répartition (détaillée plus bas) :
   - **TMS (faux MCP « Dashdoc »)** → tout l'opérationnel transport : transports/expéditions, eCMR, véhicules, chauffeurs, tournées, suivi.
   - **ERP (mock MCP « Odoo »)** → finance & commercial : clients (partners), commandes de vente, factures, produits, conditions de paiement, fournisseurs.
   - **SQLite (base annexe interne)** → seulement ce qu'une PME bricole vraiment en interne : registre de réclamations/incidents, suivi des pénalités SLA, et un export *legacy* de contacts clients (vieux fichier). PAS la base centrale.
   - **Excel** → fichiers bureautiques qui traînent : matrice de transporteurs de secours, liste de priorité client tenue à la main, snapshot d'inventaire.
   - **PDF** → documents : PO, facture, contrat SLA, bon de livraison.
   - **Emails (JSON + seed Outlook + mock MCP)** → les messages du scénario.

## Stack imposée

- Python 3.11+.
- `sqlite3` (stdlib) pour la base annexe.
- `openpyxl` pour les `.xlsx`.
- `reportlab` pour les PDF (texte extractible — pas d'image).
- `mcp` (SDK Model Context Protocol Python officiel, `pip install mcp`) pour les serveurs mock.
- `Faker` autorisé UNIQUEMENT pour générer le bruit réaliste (noms d'entreprises, villes, dates). Les enregistrements du scénario, eux, sont fixés à la main.
- Pas d'autre dépendance lourde. Mets tout dans `requirements.txt`.

## Arborescence à créer

```
data/
  canonical.py                    # SOURCE DE VÉRITÉ UNIQUE : tous les enregistrements (scénario + bruit) en Python
  generate_all.py                 # point d'entrée unique, idempotent
  validate.py                     # vérifications de cohérence (code retour non-zéro si fail)

  odoo/
    odoo_dump.json                # ERP : partners, sale orders, invoices, products, suppliers, payment terms
  dashdoc/
    dashdoc_dump.json             # TMS : transports, vehicles, drivers, tours (format Dashdoc-like)
  db/
    annex.sql                     # DDL + INSERT de la base annexe (réclamations, pénalités, legacy contacts)
    annex.db                      # généré depuis annex.sql
    build_db.py
  emails/
    emails.json
    seed_outlook.py               # seed des emails vers Outlook via MCP (paramétrable, --dry-run)
  excel/
    carrier_backup_matrix.xlsx
    customer_priority_list.xlsx
    warehouse_inventory_snapshot.xlsx
    generate_excel.py
  pdfs/
    PO-8821-MedPharma.pdf
    INV-7742-MedPharma.pdf
    SLA-MedPharma-ColdChain.pdf
    DeliveryNote-SH-2049.pdf
    generate_pdfs.py

mcp_mocks/
  dashdoc_server.py               # faux MCP TMS qui sert dashdoc_dump.json
  odoo_server.py                  # mock MCP ERP qui sert odoo_dump.json
  email_server.py                 # mock MCP email qui sert emails.json
  README.md                       # lancement, outils exposés, exemples I/O, bloc .mcp.json

requirements.txt
DATA_README.md
```

## Volume cible (~3-4× le strict scénario) — « bruit relevant »

Le scénario seul fait trop « cousu main ». Étoffe avec des données **plausibles et cohérentes** pour qu'une vraie activité de transporteur PME apparaisse dans le graphe. Volume cible :

| Entité | Volume |
|---|---|
| Customers / partners | **~18** (dont les 4 du scénario) |
| Products / SKU | **~12** (dont les 4 du scénario) |
| Orders + PO | **~28** |
| Shipments / transports | **~28** |
| Carriers | **~10** (dont ColdRoad, FreshMove, RoadX, ColdFast, NorthLog + bruit) |
| Vehicles (flotte) | **~10** |
| Drivers (chauffeurs) | **~14**, avec certifications (ADR, FIMO/CQC, frigo) |
| Warehouses | **~4** (dont WH-1 Paris, WH-2 Lyon) |
| Inventory rows | **~25** |
| Suppliers (fournisseurs) | **~8** (carburant, leasing, maintenance, pneus…) |
| Contracts | **~8** (dont CT-001 MedPharma, CT-004 BioCare) |
| Invoices | **~28** (une par order) |
| Claims/incidents (base annexe) | **~12** historiques (clos), 0 ouvert lié à SH-2049 |
| SLA penalty log (base annexe) | **~6** lignes historiques |

Règles pour le bruit :
- **Cohérent** : chaque shipment de bruit a un order, un customer, un carrier, un véhicule, un ou des items existants. Pas d'orphelins (sauf 1-2 incohérences *intentionnelles* décrites plus bas).
- **Plausible** : transporteur régional France. Villes réelles (Paris, Lyon, Marseille, Lille, Bordeaux, Strasbourg…), montants réalistes, dates étalées sur ~30 jours autour d'aujourd'hui.
- **Varié** : mélange cold-chain et standard, plusieurs statuts (Delivered, In transit, Delayed, Planned), plusieurs transporteurs.
- Le bruit n'est **pas distingué** des données du scénario dans les sources (pas de séparation visible). MAIS voir « Flag interne » ci-dessous.

## Saillance du scénario : SH-2049/MedPharma doit ressortir SANS tricher

Le bruit reste « normal ». Les enregistrements du scénario sont rendus **structurellement les plus extrêmes**, de sorte qu'une analyse honnête fasse remonter SH-2049 en tête :

- **MedPharma** = le plus gros compte : `priority_tier` Platinum, `strategic_value` **le plus élevé de tous** (1 200 000 ; aucun autre client > ~600 000).
- **INV-7742 (186 000 €)** = **la plus grosse facture en cours (Pending)** du jeu de données. Les autres factures Pending sont nettement plus petites.
- **SH-2049** = le **seul** retard *critique* qui cumule : cold-chain (2–8°C), deadline serrée aujourd'hui 18:00, pénalité la plus lourde (7 000 €/h), backup battery limité (3h), et le client le plus stratégique. (SH-2052 est aussi `Delayed` mais moins grave : montant plus faible, pénalité 5 000 €/h, deadline moins critique — il sert de comparaison, pas de concurrent.)
- Aucun autre shipment de bruit ne doit avoir simultanément : cold-chain + Platinum + grosse facture + grosse pénalité. SH-2049 est unique sur cette combinaison.

> Objectif : la démo doit pouvoir dire « parmi 28 expéditions, voici LA critique » et avoir raison, par les chiffres, pas par un trucage.

## Flag interne du scénario (best-effort, non bloquant)

Dans `canonical.py`, marque les enregistrements appartenant au scénario SH-2049 avec un champ booléen interne `_scenario: true` (et un `_scenario_role` optionnel : "shipment", "customer", "invoice", "po", "sla", "carrier_backup", "email"…).

- Ce flag est conservé dans `canonical.py` et peut être propagé dans les dumps si trivial, MAIS **ne doit pas casser le réalisme des formats source** : si l'ajouter dans `odoo_dump.json`/`dashdoc_dump.json` dénature le format (un vrai Dashdoc n'a pas de champ `_scenario`), alors **ne le mets pas dans ces dumps** — garde-le seulement dans `canonical.py` et expose-le via un fichier annexe `data/_scenario_manifest.json` (liste des IDs du scénario).
- Le flag est un **filet** pour la viz/démo. Si plus tard il s'avère inutilisable, ce n'est pas grave : la saillance structurelle (section précédente) doit suffire à elle seule. Ne sur-investis pas dessus.

## Données canoniques du scénario (à respecter au caractère près)

> Réutilise EXACTEMENT ces identifiants et montants partout où l'entité apparaît. Mêmes valeurs, vocabulaires de champs différents selon la source.

### Customers (scénario)
| customer_id | name | industry | priority_tier | account_manager | strategic_value |
|---|---|---|---|---|---|
| C001 | MedPharma | Pharma | Platinum | Sarah Martin | 1200000 |
| C002 | FreshMarket | Retail | Gold | Jules Bernard | null |
| C003 | AutoParts SAS | Automotive | Silver | Clara Moreau | null |
| C004 | BioCare Labs | Healthcare | Platinum | Sarah Martin | null |

### Products (scénario)
| sku | name | category | temperature_min | temperature_max | unit_value |
|---|---|---|---|---|---|
| PHARMA-22 | Insulin batch | Cold-chain | 2 | 8 | 180 |
| FOOD-19 | Fresh salmon | Cold-chain | 0 | 4 | 35 |
| AUTO-77 | Brake components | Standard | null | null | 90 |
| LAB-12 | Diagnostic reagent | Cold-chain | 2 | 8 | 250 |

### Orders (scénario)
| order_id | customer_id | po_number | promised_delivery_deadline | status |
|---|---|---|---|---|
| O-881 | C001 | PO-8821 | <AUJOURD'HUI>T18:00 | open |
| O-882 | C002 | PO-8822 | <AUJOURD'HUI>T20:00 | open |
| O-883 | C003 | PO-8823 | <DEMAIN>T12:00 | open |
| O-884 | C004 | PO-8824 | <AUJOURD'HUI>T16:00 | open |

> Dates : calcule « aujourd'hui » à l'exécution (date système), formate en ISO 8601, garde les heures locales indiquées. La démo doit rester cohérente quel que soit le jour de lancement.

### Shipments / transports (scénario)
| shipment_id | order_id | carrier_id | origin_warehouse | destination | status | estimated_arrival | temperature_controlled | battery_backup_hours |
|---|---|---|---|---|---|---|---|---|
| SH-2049 | O-881 | CAR-COLDROAD | WH-1 | Lyon Hospital Distribution Center | Delayed | <AUJOURD'HUI>T24:00* | true | 3 |
| SH-2050 | O-882 | CAR-FRESHMOVE | WH-1 | Marseille | In transit | <AUJOURD'HUI>T20:00 | true | 6 |
| SH-2051 | O-883 | CAR-ROADX | WH-1 | Lille | In transit | <DEMAIN>T12:00 | false | 0 |
| SH-2052 | O-884 | CAR-COLDROAD | WH-2 | Lyon | Delayed | <AUJOURD'HUI>T18:00 | true | 2 |

> *SH-2049 : deadline 18:00 + retard 6h = arrivée estimée 24:00 (minuit). Volontaire et central.

### ShipmentItems (scénario)
| shipment_id | sku | quantity |
|---|---|---|
| SH-2049 | PHARMA-22 | 1000 |
| SH-2050 | FOOD-19 | 400 |
| SH-2051 | AUTO-77 | 250 |
| SH-2052 | LAB-12 | 150 |

### Carriers (scénario + à compléter par bruit)
| carrier_id | name | service_type | reliability_score |
|---|---|---|---|
| CAR-COLDROAD | ColdRoad | Cold-chain | 0.78 |
| CAR-FRESHMOVE | FreshMove | Cold-chain | 0.88 |
| CAR-ROADX | RoadX | Standard | 0.82 |
| CAR-COLDFAST | ColdFast Express | Cold-chain (emergency) | 0.91 |
| CAR-NORTHLOG | NorthLog | Cold-chain | 0.80 |

### Warehouses (scénario + bruit)
| warehouse_id | name | city |
|---|---|---|
| WH-1 | Paris WH-1 | Paris |
| WH-2 | Lyon WH-2 | Lyon |

### Inventory (scénario)
| warehouse_id | sku | available_units | reserved_units |
|---|---|---|---|
| WH-1 | PHARMA-22 | 800 | 600 |
| WH-2 | PHARMA-22 | 200 | 100 |
| WH-1 | FOOD-19 | 500 | 200 |
| WH-2 | LAB-12 | 150 | 50 |

### Contracts (scénario)
| contract_id | customer_id | sla_deadline | late_penalty_per_hour | special_terms |
|---|---|---|---|---|
| CT-001 | C001 | 18:00 | 7000 | Cold-chain 2–8°C. Critical shipments must be escalated to account manager. |
| CT-004 | C004 | 16:00 | 5000 | Cold-chain 2–8°C. Escalation required. |

### Invoices (scénario)
| invoice_id | order_id | amount | currency | status |
|---|---|---|---|---|
| INV-7742 | O-881 | 186000 | EUR | Pending |
| INV-7743 | O-882 | 14000 | EUR | Pending |
| INV-7744 | O-883 | 22500 | EUR | Paid |
| INV-7745 | O-884 | 37500 | EUR | Pending |

> INV-7742 doit rester la plus grosse facture **Pending** de tout le jeu (bruit compris).

## Répartition par source — détails de format

### ERP — `odoo/odoo_dump.json` (mock MCP Odoo)
Vision finance/commercial. Vocabulaire **Odoo-like** (c'est le but : forcer la résolution) :
- `res.partner` : `{ "partner_id", "name", "customer_rank", "industry_id", "category" (tier), "user_id" (account manager), "x_strategic_value" }`
- `sale.order` : `{ "order_id", "partner_id", "client_order_ref" (= le PO number), "date_order", "state" }`
- `account.move` (factures) : `{ "move_id" (= invoice_id), "invoice_origin" (= order/PO), "partner_id", "amount_total", "currency_id", "payment_state" }`
- `product.product` : `{ "product_id" (= sku), "name", "categ_id", "x_temp_min", "x_temp_max", "list_price" }`
- `res.partner` fournisseurs (`supplier_rank` > 0) + `account.payment.term` (conditions de paiement : 30j, 45j, 60j…).
> Les IDs métier (PO-8821, INV-7742, MedPharma, PHARMA-22) matchent le scénario. Le mapping champ Odoo ↔ canonique est documenté dans `DATA_README.md`.

### TMS — `dashdoc/dashdoc_dump.json` (faux MCP Dashdoc)
Vision opérationnelle transport. Vocabulaire **Dashdoc-like** :
- `transports` : `[{ "uid" (= shipment_id), "status", "loading_address" (origin), "unloading_address" (destination), "carrier" {name}, "requested_vehicle" (frigo/standard), "deliveries" [{ "sku", "quantity" }], "tracking" {eta}, "is_cold_chain", "temperature_setpoint" {min,max} }]`
- `vehicles` : `[{ "license_plate", "type" (frigo/tautliner/…), "year", "is_refrigerated" }]`
- `drivers` : `[{ "driver_id", "name", "certifications" ["ADR","FIMO","frigo"] }]`
- `carriers` : la liste des transporteurs.
> Mêmes IDs métier que la DB/ERP, vocabulaire différent. C'est ICI que vivent SH-2049 et son suivi — PAS dans SQLite.

### Base annexe — `db/annex.sql` → `db/annex.db` (SQLite)
Ce qu'une PME a vraiment en interne. **Trois tables seulement** :
- `customer_claims` : ~12 réclamations historiques (id, customer_ref, shipment_ref nullable, type, opened_at, closed_at, status). Toutes **closes**, aucune ouverte liée à SH-2049 (le scénario est « frais »).
- `sla_penalty_log` : ~6 pénalités passées appliquées (id, customer_ref, shipment_ref, hours_late, penalty_amount, month). Historique, pour le contexte.
- `legacy_contacts` : export d'un vieux fichier de contacts clients (id, raw_name, email, phone, notes) — **volontairement « sale »** : 1-2 noms en doublon orthographique du scénario (ex. « Med Pharma SARL » vs « MedPharma ») pour tester la résolution floue. Les autres = bruit.
> Cette base sert à montrer que l'agent lit AUSSI une source SQL hétérogène, et à créer un cas de résolution floue (Med Pharma vs MedPharma).

### Excel — `data/excel/`
- `carrier_backup_matrix.xlsx` — `Route, Backup Carrier, Max Cold Chain Capacity, Emergency Rate` : Paris→Lyon · ColdFast Express · 20 pallets · €2,400 ; Lyon→Marseille · FreshMove · 12 pallets · €1,700 ; Paris→Lille · NorthLog · 18 pallets · €1,300. (+ 2-3 routes de bruit.)
- `customer_priority_list.xlsx` — `Customer, Priority Tier, Account Manager, Escalation Required` : les 4 du scénario (MedPharma/Platinum/Sarah Martin/Yes ; FreshMarket/Gold/Jules Bernard/No ; AutoParts SAS/Silver/Clara Moreau/No ; BioCare Labs/Platinum/Sarah Martin/Yes) + le reste des ~18 clients.
- `warehouse_inventory_snapshot.xlsx` — `Warehouse, SKU, Available Units, Reserved Units` : reprend l'inventory complet (~25 lignes).

### PDF — `data/pdfs/` (texte extractible, reportlab)
Chaque PDF contient AU MOINS ces champs en phrases :
- **PO-8821-MedPharma.pdf** : PO Number PO-8821 · Customer MedPharma · SKU PHARMA-22 · Quantity 1000 units · Required delivery: today before 18:00 · Destination: Lyon Hospital Distribution Center.
- **INV-7742-MedPharma.pdf** : Invoice INV-7742 · Related PO PO-8821 · Customer MedPharma · Amount €186,000 · Status Pending.
- **SLA-MedPharma-ColdChain.pdf** : Customer MedPharma · Cold-chain products must remain between 2°C and 8°C · Delivery deadline 18:00 local time · Late penalty €7,000 per hour · Critical shipments must be escalated to the account manager.
- **DeliveryNote-SH-2049.pdf** : Shipment SH-2049 · PO PO-8821 · SKU PHARMA-22 · Quantity 1000 · Carrier ColdRoad · Origin Paris WH-1 · Destination Lyon Hospital Distribution Center.

### Emails — `data/emails/emails.json` (+ seed + mock)
Tableau JSON de 4 objets : `id, from, to, subject, body, received_at` (ISO 8601, aujourd'hui), `labels`. `to` = `ops@ourlogisticsco.com` pour les 4. Contenu exact :
1. **Carrier delay** — `operations@coldroad-logistics.com` · `Delay notification - Shipment SH-2049` · *"Truck assigned to shipment SH-2049 has broken down near Lyon. Estimated delay: 6 hours. Refrigeration unit battery backup is expected to last 3 more hours."*
2. **Customer escalation** — `procurement@medpharma.com` · `URGENT - PO-8821 delivery confirmation` · *"Please confirm that PO-8821 will arrive before 18:00 today. This shipment is needed for tomorrow morning hospital distribution."*
3. **Internal strategic** — `sarah.martin@ourlogisticsco.com` · `MedPharma is strategic` · *"MedPharma is one of our top 5 accounts. Any delivery risk should be escalated immediately."*
4. **Backup carrier** — `dispatch@coldfast-express.com` · `Emergency cold-chain capacity Paris to Lyon` · *"We have emergency refrigerated capacity available today for Paris to Lyon. Max capacity: 20 pallets. Emergency rate: €2,400."*

> Optionnel (bruit) : tu peux ajouter 2-3 emails opérationnels anodins (confirmation de livraison routine, question facturation) pour étoffer, clairement non liés au scénario.

## Script de seed Outlook — `data/emails/seed_outlook.py`
- Lit `emails.json` et pousse chaque email dans une boîte Outlook **via un outil MCP Microsoft 365 / Outlook**.
- **Tu n'as PAS accès à la boîte ici.** Écris le script paramétrable, pas pour tourner dans cet environnement :
  - Adresse cible + nom du serveur/outil MCP = **variables de config** en tête de fichier (ou via `.env`/variables d'environnement), avec placeholders explicites et commentaires.
  - Isole l'appel réel dans une fonction `send_via_mcp(email)` avec un TODO clair, et un mode `--dry-run` qui imprime ce qui serait envoyé. Le dry-run doit tourner sans dépendance externe.
  - Documente l'usage en tête du fichier (prérequis, config, dry-run puis réel).

## Serveurs MCP mock — `mcp_mocks/`
SDK `mcp` Python, transport stdio, **lecture seule**. Chacun lit son dump et expose des outils :
- **`dashdoc_server.py`** (TMS, lit `dashdoc_dump.json`) : `list_transports()`, `get_transport(uid)`, `list_vehicles()`, `list_drivers()`, `list_carriers()`.
- **`odoo_server.py`** (ERP, lit `odoo_dump.json`) : `list_partners()`, `get_partner(partner_id)`, `list_sale_orders()`, `list_invoices()`, `get_invoice(move_id)`, `list_products()`, `list_suppliers()`.
- **`email_server.py`** (lit `emails.json`) : `list_emails()`, `get_email(id)`, `search_emails(query)`.
Contraintes : chaque serveur lançable seul (`python mcp_mocks/<x>.py`). `mcp_mocks/README.md` documente lancement, outils, un exemple I/O par outil, et un bloc `.mcp.json` prêt à copier pour brancher les trois serveurs.

> Note : la base annexe SQLite n'a PAS de serveur MCP (une base SQL locale se lit en direct par l'ingestion). Seuls TMS/ERP/email sont exposés en MCP.

## Scripts de génération
- `data/canonical.py` : **source de vérité unique**. Tous les enregistrements (scénario codés à la main + bruit généré avec Faker via une **seed fixe** pour la reproductibilité). Tout le reste importe d'ici.
- `data/generate_all.py` : point d'entrée unique, **idempotent**. Génère annex.db (depuis annex.sql), PDF, Excel, et écrit les dumps JSON ERP/TMS + emails.json. Ré-exécutable sans erreur.
- Chaque sous-générateur lançable seul. Aucune valeur dupliquée hors `canonical.py`.

## Validation — `data/validate.py` (NON optionnel, code retour non-zéro si fail)
Rapport PASS/FAIL sur :
1. **Recoupement inter-sources** : MedPharma/C001, PO-8821, O-881, SH-2049, INV-7742, PHARMA-22 présents dans CHAQUE source censée les contenir, avec les mêmes valeurs clés (186000, 1000, 18:00…), malgré les noms de champs différents.
2. **Intégrité référentielle** (sur l'ensemble scénario+bruit) : chaque order→customer existe, chaque shipment→order existe, chaque shipment_item→sku existe, chaque shipment→carrier existe, etc. (hors incohérences intentionnelles documentées).
3. **Saillance du scénario** : MedPharma a la `strategic_value` max ; INV-7742 est la plus grosse facture Pending ; SH-2049 est le seul shipment cumulant cold-chain + Platinum + pénalité ≥7000 + deadline du jour. Le check ÉCHOUE si un enregistrement de bruit vole la vedette.
4. **Cohérence scénario** : SH-2049 `Delayed`, O-881→PO-8821, invoice de O-881 = INV-7742 (186000), contrat C001 = 7000/h & deadline 18:00, inventory WH-2/PHARMA-22 = 200/100.
5. **Résolution floue** : `legacy_contacts` contient bien une variante orthographique de MedPharma distincte de l'entrée canonique.
6. **PDF lisibles** : ré-extraction du texte des 4 PDF, présence de PO-8821, INV-7742, €186,000, SH-2049, 2°C/8°C, €7,000.
7. **Excel lisibles** : ré-ouverture des 3 fichiers, en-têtes + nombre de lignes attendus.
8. **Volume** : les comptes approximatifs du tableau « Volume cible » sont respectés (±20%).

## Documentation — `DATA_README.md`
- Tableau « quelle entité vit dans quelle source » + mapping noms de champs Odoo/Dashdoc/legacy ↔ canonique.
- Pourquoi cette répartition est réaliste (TMS vs ERP vs base annexe), en 3-4 lignes.
- Le scénario SH-2049 en 5 lignes (ce que la démo doit révéler, pourquoi SH-2049 est LE point chaud).
- Les incohérences intentionnelles (résolution floue MedPharma, éventuels orphelins) listées explicitement pour qu'on ne les prenne pas pour des bugs.
- Commandes : générer (`python data/generate_all.py`), valider (`python data/validate.py`), lancer les mocks, seeder Outlook (dry-run).

## Definition of Done
- `python data/generate_all.py` produit tous les fichiers sans erreur, idempotent.
- `python data/validate.py` imprime tout PASS et sort en code 0.
- Les 3 serveurs MCP démarrent et répondent à ≥1 appel d'outil chacun (teste-les).
- `seed_outlook.py --dry-run` imprime les emails sans dépendance externe.
- Volume conforme au tableau cible ; SH-2049 démontrablement le point chaud.
- `requirements.txt`, `DATA_README.md`, `mcp_mocks/README.md` présents et corrects.
- **Aucune** ontologie, **aucun** agent, **aucune** UI.

## Ce que tu NE fais PAS
- Pas d'ontologie, pas de graphe, pas de NetworkX/Pyvis.
- Pas d'agents, pas de Claude Agent SDK, pas d'appel LLM.
- Pas d'UI/Streamlit.
- Pas de base SQL « centrale » qui contient tout (SQLite = base annexe uniquement).
- Pas de dépendances au-delà de celles listées.

Commence par `data/canonical.py` (vérité unique : scénario à la main + bruit avec seed Faker fixe), puis les générateurs, puis les mocks, puis la validation. Termine en lançant `generate_all.py` puis `validate.py` et en me montrant le rapport.
