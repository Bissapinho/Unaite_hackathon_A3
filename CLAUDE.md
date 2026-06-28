# Hackathon — Le Palantir des PME (transport)

> **Statut du document.** Spec de référence technique du projet, vivant **dans le repo de
> code** (lu par Claude Code). Réécrit le 2026-06-27 autour de l'architecture en **deux
> systèmes** (compilateur d'ontologie + agent conversationnel) décidée après brainstorm.
> Remplace les versions antérieures : control tower Streamlit tout-mocké, puis « swarm
> linéaire » Source Profiler→…→Critic. La vision business et les prompts de specs vivent
> dans le dossier séparé `YC QRT/` (stratégie, pitch YC).
>
> **MAJ 2026-06-28 — tout le pipeline est implémenté et la démo tourne bout-en-bout**
> (Système A oracle + agentique, Système B, UI Flask + viz du collègue + surlignage). Voir la
> **§8 (état d'avancement)** qui fait foi. Restent surtout l'optim latence et le polish vidéo.

---

## 1. Vue d'ensemble

On construit le **Palantir des PME** : un système qui ingère le chaos hétérogène d'une
entreprise (ERP, TMS, base interne, RH, Excel, PDF, emails) et le transforme en une
**ontologie métier interrogeable** — une carte vivante de toute la boîte, sur laquelle un
repreneur peut poser ses questions en langage naturel.

Le produit a **deux systèmes distincts** (détaillés en §3) :

- **Système A — le compilateur d'ontologie.** Sources → **3 livrables** : `ontology.json`
  (le document sérialisé avec provenance), le **graphe NetworkX** (la structure en mémoire,
  pivot des deux autres) et la **visualisation Pyvis** (la carte HTML). Il *construit* toute
  la connaissance — entités, relations, provenance, confidence — **et va jusqu'à la carte
  visualisable.** Pensé comme un **compilateur** (passes spécialisées), pas comme un essaim
  d'agents qui bavardent.
- **Système B — l'agent conversationnel.** Son **seul rôle : interroger** l'ontologie
  publiée par A. L'utilisateur pose une question, B charge le graphe et l'explore via des
  **outils de requête NetworkX**, raisonne, répond avec sa chaîne de preuves, propose des
  actions. **B ne construit rien, ne dessine rien** — il query.

> **La frontière A/B est nette et non négociable** : A construit (json + graphe + carte),
> B exploite (queries). A ne répond à aucune question ; B ne reconstruit ni ne dessine
> rien. C'est ce qui évite que B ne soit qu'un « formatage » de A (voir garde-fous §9).

L'ontologie couvre **toute la structure de la boîte** sur trois couches reliées :

- **Opérationnel & commercial** (clients, commandes, factures, produits, tournées, flotte,
  transporteurs, fournisseurs) — *le flux de l'activité* ;
- **Structure humaine / RH** (la société, son dirigeant, les employés, leurs rôles,
  l'organigramme, les hommes-clés) — *qui fait tourner la boîte* ;
- **Finances de la société** (CA total et concentration par client, marge, masse salariale,
  charges flotte/leasing, trésorerie & décalage de paiement) — *la santé financière*.

C'est cette vue à 360° qui tient la promesse « comprendre ce qu'on achète ». Cible
business : les **repreneurs / acheteurs sériels** de PME (search funds, ETA, holdings,
family offices). La phrase :

> *« On transforme n'importe quelle PME en carte navigable en 10 minutes, pour que les
> repreneurs comprennent ce qu'ils achètent. »*

Pour le hackathon, l'entreprise de démo est une **PME de transport régionale**, et le
moment fort est une **disruption** (la tournée SH-2049) révélée par une question posée à
Système B. Track visé : **Software for Agents**. Démo = **vidéo enregistrée** (pas de live
→ on optimise le rendu visuel, pas la robustesse runtime).

---

## 2. Le scénario de démo

Une PME de transport vient d'être reprise. Ses données sont éparpillées et illisibles :
opérationnel dans un TMS, finance dans un ERP, bricolages dans une base SQL interne, des
Excel et PDF qui traînent, une boîte email pleine. **Rien n'est relié.**

On lance **Système A**. En quelques minutes une carte se construit sous les yeux : clients,
contrats, tournées, flotte, chauffeurs, fournisseurs, factures, CA, employés,
organigramme. Le **« avant/après » chaos → carte est le premier moment waouh.**

Puis on **parle à Système B**. L'utilisateur tape une question vague :

> *« Y a-t-il un problème avec une livraison ? »*

B explore l'ontologie et **remonte une réponse précise qu'aucune table ne contenait** :

- SH-2049 transporte 1000 unités de **PHARMA-22** (insuline, cold-chain 2–8°C) pour
  **MedPharma** — le client le plus stratégique (`strategic_value` 1 200 000, le max).
- Camion **ColdRoad** en panne près de Lyon : retard **6h**, deadline contractuelle
  **18:00** dépassée → arrivée estimée **minuit**, alors que la batterie du groupe froid ne
  tient que **3h**.
- Facture liée **INV-7742 = 186 000 €**, la plus grosse facture **en cours (Pending)**.
  Contrat **CT-001** : pénalité **7 000 €/h** (la plus lourde) + escalade obligatoire vers
  l'account manager **Sarah Martin**.
- **Capacité de secours** : ColdFast Express, Paris→Lyon, 20 palettes, 2 400 €.
- **Pourquoi c'est LE point chaud** : parmi tous les shipments en retard, SH-2049 est le
  **seul** à cumuler cold-chain + client Platinum + pénalité ≥ 7 000 €/h + deadline du jour.
  **B le déduit par les chiffres** (il score les candidats), pas par un trucage.
- **Actions recommandées** (proposées en texte) : réserver ColdFast Express · notifier
  MedPharma · créer un incident · réserver le stock · escalader à Sarah Martin.

D'autres questions **génériques sur la structure** marchent aussi (« de qui dépend mon
CA ? », « qui sont les hommes-clés ? », « quelle est ma concentration client ? ») — c'est
ce qui prouve que B interroge une *vraie* base de connaissance, pas un script figé.

> **Note de positionnement.** Le scénario pharma cold-chain SH-2049 n'est pas un domaine à
> part : il est **encapsulé dans** la PME de transport. MedPharma est le gros client
> (concentration du CA), SH-2049 la tournée critique. Démo à la fois sectorielle
> (transport) et spectaculaire (incident cold-chain à fort enjeu).

---

## 3. Architecture — deux systèmes

```
                          SYSTÈME A — COMPILATEUR D'ONTOLOGIE
   SOURCES                  (passes spécialisées, orchestrées)          3 LIVRABLES DE A
┌────────────────┐   ┌──────────────────────────────────────────┐   ┌──────────────────┐
│ Odoo (ERP)      │   │            Superviseur                    │   │ graphe NetworkX   │
│ Dashdoc (TMS)   │   │  (workflow déterministe + gates + état)   │   │  (PIVOT en mémoire)│
│ SQLite annexe   │──▶│   ├─ Extraction métadonnées (déterministe)│──▶│      │      │      │
│ company_dir.xlsx│   │   ├─ Source Profiler                      │   │      ▼      ▼      │
│ finances.xlsx   │   │   ├─ Entity Discovery (+ fuzzy)           │   │ ontology  Pyvis    │
│ PDF             │   │   ├─ Relationship Discovery               │   │  .json    .html    │
│ emails          │   │   ├─ Attribute Mapping                    │   │ (3 couches:        │
└────────────────┘   │   ├─ Ontology Architect                   │   │  entités+relations │
                     │   ├─ Critic / Consistency                 │   │  +confidence+      │
                     │   └─ Validation (light en MVP)            │   │  evidence+open_q+  │
                     └──────────────────────────────────────────┘   │  layer) + carte    │
                                                                     └────────┬─────────┘
   SYSTÈME B — AGENT CONVERSATIONNEL (interroge SEULEMENT)                     │
┌──────────────────────────────────────────────────────────┐                │
│ User pose une question  ─▶  Agent (Claude)                │  charge        │
│                              │ appelle des OUTILS NetworkX │  ontology.json │
│  réponse + chaîne d'evidence │  find_nodes / get_neighbors │◀───────────────┘
│  + actions proposées (texte) │  shortest_path / impact /   │  → reconstruit son
│                              │  articulation_points        │    propre graphe NetworkX
└──────────────────────────────────────────────────────────┘    pour le requêter
```

### Système A — le compilateur

**Principe central : on ne *devine* pas l'ontologie, on la *propose, justifie et valide*.**
L'erreur serait qu'un agent infère l'ontologie directement des tables brutes. À la place,
chaque passe **propose** des éléments et **attache ses preuves** ; le tout est assemblé,
critiqué, puis publié. Le mental model est un **compilateur** : sources = entrée,
ontologie = artefact compilé, agents = passes spécialisées.

Pattern de mutation, **non négociable** :
`passe PROPOSE → système VALIDE → Critic ATTAQUE → (humain APPROUVE, vision) → PUBLIE`.
Jamais « un agent décide → l'ontologie change » : pour une ontologie d'entreprise, les
erreurs silencieuses coûtent cher.

**Les 3 livrables de A.** Une fois les passes terminées, A matérialise un **graphe
NetworkX** en mémoire — c'est la **structure pivot**. Il en dérive ensuite les deux autres
sorties : `ontology.json` (sérialisation avec provenance, le document qui persiste et
traverse la frontière vers B) et la **carte Pyvis HTML** (le rendu visuel des 3 couches).
A va donc **jusqu'à la carte** ; B n'en produit aucune.

```
... passes ...  →  graphe NetworkX G  ─┬─▶  graph_to_json(G)  → outputs/ontology.json
                                       └─▶  nx_to_pyvis(G)    → outputs/ontology_graph.html
```

Les passes (★ = MVP, on code ; ◇ = vision, on présente) :

| Passe | Rôle | MVP/vision |
|---|---|---|
| **Extraction métadonnées** | Schémas, en-têtes, samples, clés. **Déterministe**, pas d'LLM. | ★ |
| **Source Profiler** | Comprend chaque source isolément (entités probables, champs clés). | ★ |
| **Entity Discovery** | Regroupe les objets physiques en entités métier ; **résolution floue** (`Med Pharma SARL` ↔ `MedPharma`). | ★ |
| **Relationship Discovery** | Infère les arêtes, **avec evidence** (overlap de clés, jointures). | ★ |
| **Attribute Mapping** | Mappe les champs sources → attributs canoniques. | ★ |
| **Ontology Architect** | Assemble la proposition canonique (compile les sorties des passes). | ★ |
| **Critic / Consistency** | Attaque la proposition : doublons, cardinalités fausses, contradictions inter-sources (ERP « in transit » vs email « delayed »). | ★ |
| **Validation** | Vérifie empiriquement (couverture de jointure, orphelins…). **Light en MVP** (quelques checks clés) ; moteur SQL complet = vision. | ★ (light) |
| **Governance / PII** | Classifie les données sensibles. | ◇ |
| **Business Glossary** | Définit les termes métier (« client actif »…). | ◇ |
| **Metric Definition** | Définit les métriques (CA, marge, MRR) formellement. | ◇ |
| **Human Review** | Prépare les décisions à fort enjeu pour un humain. | ◇ |

**Orchestration.** Un **superviseur** enchaîne les passes dans un **workflow
déterministe** ; le raisonnement agentique vit *à l'intérieur* des passes. **Pas** de
multi-agent chat décentralisé (ingérable). Build d'abord **déterministe bout-en-bout**,
puis on emballe chaque passe en agent nommé avec **logs visibles** (Claude Agent SDK).

### Système B — l'agent conversationnel

**Le seul rôle de B est d'interroger l'ontologie de A.** Il ne construit rien, ne dessine
aucune carte. Au démarrage, il **recharge `ontology.json`** (l'artefact publié par A) et le
reconstruit en **graphe NetworkX** côté B — son terrain de requête. Puis B est un **agent**
(Claude) qui répond en langage naturel **en explorant ce graphe** via des **outils de
requête**. Il ne reçoit pas tout le graphe en contexte (trop lourd, ~150 nœuds) : il
**appelle des outils** qui renvoient des sous-ensembles digestes. Outils génériques visés
(couvrent la question phare + les questions structure) :

- `find_nodes(type=…, attr=…)` — ex. tous les shipments `Delayed`.
- `get_neighbors(node)` — voisinage direct d'une entité.
- `shortest_path(a, b)` / `get_subgraph(node, depth)` — chaîne de liens + evidence.
- `compute_impact(shipment)` — pénalité = `delay_h × penalty/h`, SLA, facture liée.
- `articulation_points()` / `centrality()` — fragilité structurelle (homme-clé,
  concentration : retirer Sarah ou MedPharma → ce qui se fragmente).

**B fait un vrai raisonnement** (ex. récupère tous les `Delayed`, **score** chacun,
désigne le pire) — il ne lit pas un champ `is_hot` que A aurait pré-mâché. Réponse en
langage naturel + **chaîne d'evidence citée** + **actions proposées en texte** (pas
d'exécution). Pour la démo (vidéo), les questions sont **scriptées** : une question phare
(disruption) + 2-3 questions structure qui marchent à coup sûr.

### Stack & tiering

- **Graphe** : NetworkX (analyse en mémoire) + Pyvis (rendu HTML interactif, nœuds
  cliquables, 3 couches colorées, zoom sur SH-2049).
- **Agents** : Claude Agent SDK (Python). **Opus 4.8** pour Architect, Critic, et le
  raisonnement de B ; **Sonnet 4.6** pour Entity/Relationship/Attribute ; **Haiku 4.5**
  pour Profiler + extraction mécanique. Prompt caching sur les blocs statiques.
- **Sources** : Odoo (mock MCP), Dashdoc (mock MCP), emails (mock MCP), SQLite (lecture
  directe), Excel/PDF (fichiers). Vrai Odoo / Outlook réel = upgrade derrière la même
  interface → le pipeline n'en dépend jamais.

> **Hors Cowork.** L'agent ne tourne pas dans Cowork : MCP configurés dans le runtime de
> l'agent (`.mcp.json`). Le scaffolding doit prévoir cette config côté runtime.

---

## 4. Format de l'ontologie — `outputs/ontology.json`

Contrat de sortie de Système A, entrée de Système B. Chaque entité et relation porte sa
**provenance** : c'est ce qui rend l'ontologie digne de confiance (sans evidence, pas de
confiance) et ce qui alimente les réponses sourcées de B.

```json
{
  "entities": [
    {
      "id": "customer:medpharma", "type": "Customer", "name": "MedPharma",
      "layer": "operational",
      "attributes": { "priority_tier": "Platinum", "strategic_value": 1200000, "account_manager": "Sarah Martin" },
      "sources": ["odoo.res_partner:C001", "sqlite.legacy_contacts:'Med Pharma SARL'"],
      "confidence": 0.95,
      "evidence": ["odoo name = 'MedPharma'", "legacy 'Med Pharma SARL' rapproché fuzzy 0.87", "même domaine medpharma.com"],
      "open_questions": []
    },
    {
      "id": "employee:sarah-martin", "type": "Employee", "name": "Sarah Martin",
      "layer": "hr",
      "attributes": { "role_title": "Responsable Grands Comptes", "org_unit": "Commercial", "is_key_person": true },
      "sources": ["odoo.user_id", "company_directory.xlsx", "email:EM-003"],
      "confidence": 0.92,
      "evidence": ["odoo user_id sur C001+C004", "directory ligne Sarah Martin", "signature email EM-003"],
      "open_questions": ["reports_to déduit, non confirmé par une source RH explicite"]
    }
  ],
  "relationships": [
    { "source": "employee:sarah-martin", "target": "customer:medpharma", "type": "manages",
      "confidence": 0.95, "evidence": ["odoo res_partner.user_id = 'Sarah Martin' pour C001"], "open_questions": [] },
    { "source": "employee:sarah-martin", "target": "employee:dir-commercial", "type": "reports_to",
      "confidence": 0.70,
      "evidence": ["title_rank 3 sous title_rank 2 même org_unit Commercial", "email escalade 'je transmets à [Dir. Commercial]'"],
      "open_questions": ["lien reconstruit par inférence, pas écrit dans une source"] }
  ]
}
```

Trois propriétés à respecter :

- **`layer`** ∈ `operational | hr | financial` — rattache chaque nœud à une couche
  (coloration du graphe ; permet à B de raisonner « ce risque ops touche aussi la RH »).
- **`confidence` variable et honnête** — 0.95 pour ce qui est sourcé deux fois, ~0.70 pour
  ce qui est *reconstruit par inférence* (ex. l'organigramme). C'est cette nuance qui rend
  l'outil crédible auprès d'un repreneur.
- **`open_questions`** — la marque de fabrique : l'ontologie dit ce qu'elle déduit vs ce
  qu'elle sait. Ne pas la supprimer pour « faire propre ».

> Les **risques** (ex. `risk:sh-2049-delay`, pénalité estimée) **ne sont PAS produits par
> A** : ils sont calculés par **B** au moment de la question (B fait le raisonnement). A
> publie le graphe factuel ; B en tire les risques à la demande.

### Entités & relations canoniques (les 3 couches)

**Opérationnel** : Customer · PurchaseOrder · Order · Invoice · Shipment · ShipmentItem ·
Product · Carrier · Vehicle · Driver · Certification · Warehouse · Inventory · Contract ·
SLA · Supplier · Email · Document.
`Customer places PO` · `PO creates Order` · `Order fulfilled_by Shipment` · `Shipment
contains Product` · `Shipment operated_by Carrier/Vehicle/Driver` · `Driver holds
Certification` · `Customer governed_by Contract` · `Contract defines SLA` · `Invoice bills
Order` · `Email mentions Shipment/PO` · `Document references PO/Shipment`.

**RH** : Company · Employee · Role · OrgUnit · KeyDependency.
`Company employs Employee` · `Employee has Role` · `Employee reports_to Employee`
*(reconstruit, cf. §6)* · `Employee manages Customer` *(account manager — relie RH ↔
commercial)* · `Driver is_a Employee` · `KeyDependency concentrated_on Employee/Customer`.

**Finances** : FinancialSummary · RevenueConcentration · CashflowGap.
`Company has FinancialSummary` · `Invoice contributes_to RevenueConcentration` *(le CA se
calcule depuis les factures)* · `Supplier payment_terms feeds CashflowGap`.

---

## 5. L'interface de démo

**Techno tranchée : serveur Flask (`ui/`) + viz canvas animée du collègue** (faite avec
Claude Design, pas Pyvis), graphe et chat dans **une même page**. Fichiers de la viz dans
`ui/static/graph_data.js`, `ui/static/support.js`, `ui/templates/ontology-graph.dc.html`. Le
chat appelle le vrai Système B via `POST /ask` ; les `node_ids` de la réponse pilotent le
**surlignage synchronisé** de la carte (zoom sur SH-2049). État : **marche bout-en-bout.**

Ce qu'on voit à l'écran :

1. **Graphe** — carte canvas de toute la PME (3 couches colorées), animée au build (couche
   par couche puis révélation du **chemin critique MedPharma → SH-2049**), zoom/pan/drag
   **manuels** (plus de re-cadrage auto une fois que l'utilisateur a la main).
2. **Chat (Système B)** — champ de question + questions cliquables. B répond (texte brut,
   sans markdown) avec impact + chaîne d'evidence + actions proposées, et **surligne** les
   nœuds concernés sur la carte. SSE dispo pour montrer les appels d'outils en direct.

> Les écrans **Sources** et **Build** (logs des passes de A) décrits dans les versions
> antérieures ne sont pas dans l'UI actuelle : la démo se concentre sur **carte + chat**, le
> « waouh » du jury. Le build de A reste visible via ses logs console (`outputs/*.log`).

---

## 6. Reconstruction de l'organigramme (point technique clé)

L'organigramme **n'est exposé dans aucune source** (réaliste : une PME n'a pas de fichier
« org_chart » propre). La hiérarchie (`manager_id`) vit comme **vérité cachée** dans
`canonical.py` et **Système A la reconstruit** par recoupement de trois familles
d'indices :

- **(a) hiérarchie des titres** (`role_title` + `title_rank` + `org_unit`) ;
- **(b) signatures et escalades d'emails** (« je transmets à <Directeur> ») ;
- **(c) références croisées ops** (AM ↔ clients, chauffeurs ↔ tournées).

Règle d'arbre à deux branches : un chef de service reporte au dirigeant (inter-service) ;
tout autre employé reporte dans son propre service au rang au-dessus. La data est conçue
pour que la reconstruction soit **fiable** (cf. prompt Brique 1bis dans `YC QRT/prompts/`).
Les liens reconstruits portent une `confidence` plus basse et une `open_question` (§4).

---

## 7. Pourquoi l'ontologie compte

La force de la démo : les réponses de B ne sont **pas** lues dans une table, elles sont
**assemblées** depuis des sources hétérogènes aux vocabulaires différents. La chaîne
d'evidence le montre, p. ex. :

- SH-2049 trouvé dans Dashdoc (`transports[].uid`) → lié à O-881 (Odoo `sale.order`) →
  PO-8821 (`client_order_ref`) → confirmé dans le PDF de bon de commande.
- INV-7742 (Odoo `account.move`) référence O-881, 186 000 €, `payment_state=not_paid`.
- SLA PDF : pénalité 7 000 €/h après 18:00. Email ColdRoad : panne Lyon, 6h, batterie 3h.
- Excel secours : ColdFast couvre Paris→Lyon. Résolution floue : `Med Pharma SARL` ↔
  `MedPharma`. Organigramme : Sarah Martin → Directeur Commercial (reconstruit).

---

## 8. État d'avancement

### ✅ Brique 1 — Data synthétique opérationnelle (FAITE)
Dans ce repo (voir `DATA_README.md`). Sources : Odoo mock, Dashdoc mock (SH-2049 y vit),
SQLite annexe (fuzzy MedPharma), Excel (secours/priorité/inventaire), PDF
(PO/INV/SLA/DeliveryNote), emails, + 3 serveurs MCP mock.

### ✅ Brique 1bis — Data RH + finances (FAITE)
Étend la Brique 1 (même principe : `canonical.py` source de vérité + `validate.py`). Ajoute
Company, ~15 Employees (organigramme **caché**, reconstructible — cf. §6), KeyDependency,
FinancialSummary. Sources : `company_directory.xlsx` (annuaire **sans colonne manager**) +
emails RH (signatures/escalades) + `finances_summary.xlsx`. CA/concentration **calculés**
depuis les factures. Prompt : `YC QRT/prompts/01b-data-rh-finances.md`.

> **État vérifié.** `validate.py` = **83/83 PASS** (dont 23 checks RH/finance, section 10 :
> organigramme caché cohérent + anti-fuite + reconstructibilité 100 %). Audit indépendant
> dans `AUDIT-brique-1bis-RH-finance.md` → **conforme**. 4 écarts mineurs *cosmétiques*,
> aucun bloquant : (M1) `_scenario_manifest.json` ne couvre pas la couche RH — à corriger
> seulement si l'UI s'en sert pour mettre en avant l'homme-clé ; (M2/M3) tournures
> « Brique 1 » / « 4 fichiers » à actualiser dans `DATA_README.md` ; (M4) faux positif
> d'environnement sur `annex.db`. → **La voie est libre pour le Système A.**

### ✅ Système A — oracle déterministe (FAIT)
Script Python sans LLM (`system_a/`) : lit les dumps produits (PAS `canonical.py`), entity
resolution + reconstruction organigramme, produit `outputs/ontology.json` + graphe NetworkX.
Sert d'**oracle de référence**. Audit : `YC QRT/AUDIT-systeme-A-oracle.md`. Dette assumée :
oracle ne matérialise que CT-001 (anti-triche, choix MVP) ; confidence fuzzy 0.97 vs ~0.85
visée (à corriger après MVP).

### ✅ Carte / graphe NetworkX (FAIT)
Le loader `system_a/ontology_graph.py` (JSON → `nx.MultiDiGraph`, résilient strict/hybrid)
est en place et partagé A/B. La **carte visuelle** finale n'est PAS du Pyvis : c'est la viz
canvas animée du collègue (cf. §5), alimentée par l'ontologie.

### ✅ Système A — extracteur agentique (FAIT)
`system_a_agents/` (Claude Agent SDK) : passes p0→p7 (Extraction, Profiler, Entity,
Relationship, Attribute, Architect, Critic, Validation), supervisor + blackboard, logs
visibles. Produit `outputs/ontology.agentic.json` (**242 entités / 356 relations**).
Convergence ~99,8 % vs oracle. Un run d'optimisation coût/latence peut encore tourner.
**Dette délai email** : le `delay_hours:6` de SH-2049 vit dans le *corps* des `.eml` ; la
passe p4 a été modifiée pour l'extraire (et le JSON patché en dur en attendant un re-run qui
le confirme).

### ✅ Système B — agent conversationnel (FAIT)
`system_b/` : recharge `ontology.agentic.json` → NetworkX via le loader de A, outils de
requête génériques (`find_nodes`, `get_neighbors`, `shortest_path`, `get_subgraph`,
`compute_impact`, `score_delayed_shipments`, `articulation_points`, `centrality`), agent
**Opus 4.8** qui raisonne + répond sourcé + propose des actions. Sortie structurée via
`submit_answer` : `answer(question) -> {answer, evidence, actions, node_ids, tool_trace}`.
Désigne SH-2049 **par scoring** (pas de `is_hot`). ~37 s/réponse (latence = génération, pas
les tours ; optim = resserrer la sortie, non faite). Spec : `YC QRT/prompts/05`.

### ✅ UI — Flask + viz du collègue + vrai B (FAIT, marche bout-en-bout)
`ui/` : serveur **Flask** (`app.py` + `backend.py`) qui sert la viz canvas du collègue et
expose `POST /ask` → vrai B (+ `GET /ask_stream` SSE pour les logs en direct). Chat branché
sur B (`node_ids` → surlignage de la carte). Spec d'intégration : `YC QRT/prompts/07` ;
correctifs cosmétiques : `YC QRT/prompts/08`-`10`.

### ⏭️ Reste (optionnel)
- **Optim latence de B** (resserrer la sortie) — « si impossible, pas grave ».
- **Polish vidéo** : pacing, voix off, enchaînement chaos → carte → révélation SH-2049.
- Solder les dettes (fuzzy confidence, confirmer le `delay_hours` via re-run de A).

> **Principe de build** (rappel) : déterministe bout-en-bout d'abord, puis emballage en
> agents. Le « waouh » du jury, c'est **B + la carte** — c'est en place.

---

## 9. Garde-fous

**Architecture**
- **A construit, B exploite — frontière nette.** A ne répond à aucune question. B ne
  reconstruit rien. Si B se contente de relire un champ pré-mâché par A (ex. `is_hot`), la
  séparation est cosmétique → **B doit faire le vrai calcul** (scorer, prioriser, mesurer
  la fragilité).
- **B s'appuie sur des outils génériques** (voisins, chemins, centralité, impact), pas sur
  10 outils sur-spécifiques. C'est ce qui lui permet de couvrir une *famille* de questions,
  pas une seule.
- **A ne devine pas, il justifie.** Tout élément porte evidence + confidence. Pattern :
  propose → valide → critic → publie. Jamais de mutation directe.

**Anti-triche (crucial pour le jury)**
- **A n'a JAMAIS accès au scénario caché** : ni `_scenario_manifest.json`, ni les flags
  `_scenario`, ni le `manager_id` de la vérité cachée. A reconstruit à partir des **mêmes
  signaux faibles qu'en vrai**. Sinon c'est de la triche, et ça se verra.
- La data est **synthétique mais réaliste** ; la saillance de SH-2049 est *structurelle*
  (par les chiffres), pas un drapeau planté. B la redécouvre en scorant.
- **Les emails sont des `.eml` bruts ; le parsing est une passe de A.** La source email,
  ce sont les fichiers `data/emails/raw/*.eml` (RFC822). Transformer un email en données
  structurées (en-têtes, corps, signatures `Nom — Poste`, escalades) **est le travail de
  la passe email de A**, pas un pré-traitement servi à A. Conséquence sur le parser
  `data/emails/eml_to_json.py` :
  - C'est un **outil de référence / data** : utilisé par `validate.py` (cohérence
    `.eml` ↔ canonical), `seed_outlook.py`, et **l'oracle déterministe** (étage 1) qui a
    le droit de s'en servir comme lib pour produire la vérité de référence.
  - Ce n'est **PAS** le chemin d'accès de l'**extracteur agentique** (étage 2) : lui doit
    **extraire l'information depuis le texte brut** du `.eml` (lecture directe ou via le
    MCP email qui sert les messages), pour qu'on *voie* A faire le travail. Lui passer le
    JSON déjà parsé rendrait l'extraction cosmétique — même faute que `is_hot` pour B.

**Demo-first**
- Optimiser le récit qui marche à tous les coups à la vidéo, pas la robustesse prod.
  Hardcoder si besoin, mais garder l'archi extensible.
- **Ne pas surinvestir** : auth, déploiement, vrai ERP/MySQL, base graphe avancée, vector
  search, les passes ◇ (governance, glossary, metrics, human review). Connecteurs
  synthétiques acceptés (vrai Outlook/Odoo = upgrade optionnel).
- **Logs visibles partout** : critère #1 du hackathon (voir A compiler, voir B requêter).

**Data**
- **Source de vérité = `canonical.py`.** Ne jamais dupliquer une valeur métier ailleurs.
  CA/concentration **calculés** depuis les factures, jamais saisis en dur.
