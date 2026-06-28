# P4 — Attribute Mapping & Finances (tâche)

Tu produis des PATCHES d'attributs ciblés pour enrichir/compléter des entités déjà créées, et
tu calcules les agrégats financiers. Tu renvoies UNIQUEMENT `{"patches": [{"id": "...",
"attributes": {...}, "layer": "financial"}]}` (le champ `layer` est optionnel).

Utilise les outils MCP/readers (montre ton travail). Tu calcules, tu n'inventes pas.

## 1. FinancialSummary (`financial:summary`)
Lis `excel.finances_summary.xlsx` (bloc 1, agrégats société). Patch `financial:summary` avec :
`period`, `payroll_monthly`, `fleet_leasing_monthly`, `fuel_monthly`, `other_opex_monthly`,
`gross_margin_pct` (en fraction, ex. 0.18), `dso_days`, `dpo_days`, `cash_on_hand`. Les montants
"€1,689,940" → entier 1689940.

## 2. RevenueConcentration (`financial:revenue-concentration`) — CALCULÉE depuis les factures
- Récupère toutes les factures (Odoo `list_invoices`) et toutes les sale.orders.
- Associe chaque facture à un client : `invoice.invoice_origin` (=PO) → `sale.order` de même
  `client_order_ref` → `partner_id`. (À défaut, `account.move.partner_id`.)
- Regroupe les montants par client, somme-les avec l'outil `sum_amounts`.
- `total_revenue` = somme de TOUTES les factures (via `sum_amounts`).
- Patch avec : `total_revenue`, `currency` "EUR", `top_customer` (nom du 1er), et `by_customer`
  = liste triée décroissante d'objets `{customer_id, name, revenue, share}` (share = revenue /
  total, arrondi 4 décimales).

## 3. CashflowGap (`financial:cashflow-gap`)
Patch avec `dso_days`, `dpo_days`, `gap_days` = dso − dpo (lus du bloc 1 finances).

## 4. Délais d'expédition extraits du CORPS des emails (couche operational)
Les emails de notification de retard contiennent dans leur `body` des chiffres qui ne sont
PAS dans les en-têtes : retard estimé en heures, autonomie de la batterie du groupe froid,
deadline. Il faut les structurer sur le shipment concerné.

- Liste les emails (`list_emails`) et repère ceux dont le `subject`/`labels` indiquent un
  retard (`delay`) lié à un shipment (ex. mention d'un identifiant `SH-####` dans le sujet).
- Pour chacun, lis le `body` (`get_email`) et extrais, **uniquement si présents** :
  - `delay_hours` (entier) — ex. "Estimated delay: 6 hours" → 6.
  - `battery_autonomy_h` (entier) — ex. "battery backup ... last 3 more hours" → 3.
  - `sla_deadline` (string "HH:MM") si une heure limite est citée dans ce body ou dans un
    email d'escalade lié au même shipment (ex. "la deadline 18:00 ne sera pas tenue" → "18:00").
- Patch l'entité shipment correspondante (`id` = `shipment:sh-####` en minuscules) avec ces
  attributs et `layer` "operational". N'extrais QUE ce qui est écrit dans le body — aucune
  estimation, aucun chiffre déduit.

Réponds UNIQUEMENT par l'objet JSON `{"patches": [...]}`.
