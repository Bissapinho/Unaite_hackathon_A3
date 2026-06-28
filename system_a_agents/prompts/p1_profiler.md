# P1 — Source Profiler (tâche)

Tu reçois ci-dessous un INVENTAIRE des sources (schémas, comptes, échantillons), produit
par une passe déterministe. Pour CHAQUE source, décris brièvement :
- `source` : son nom (ex. "odoo.res.partner", "dashdoc.transports", "sqlite.legacy_contacts",
  "excel.company_directory.xlsx", "pdf.SLA-MedPharma-ColdChain", "email.EM-003").
- `likely_entities` : les types d'entités métier qu'elle contient probablement
  (Customer, Order, Invoice, Shipment, Product, Carrier, Vehicle, Driver, Employee,
  Supplier, Contract, Claim, Email, Document, FinancialSummary…).
- `key_fields` : les champs qui servent de clés ou de jointures (ids métier, refs croisées).
- `quality_notes` : limites/pièges (noms « sales » à rapprocher, organigramme absent,
  order_id absent du TMS, etc.).

Tu n'as pas besoin d'appeler d'outils : l'inventaire suffit. Reste FACTUEL et neutre (aucun
scoring, aucune priorisation).

Réponds UNIQUEMENT par un objet JSON :
```json
{"profiles": [{"source": "...", "likely_entities": ["..."], "key_fields": ["..."], "quality_notes": "..."}]}
```

INVENTAIRE DES SOURCES :
