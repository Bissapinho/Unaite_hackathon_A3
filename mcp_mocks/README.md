# MCP Mocks (lecture seule)

Trois serveurs MCP **en LECTURE SEULE**, transport **stdio**, qui exposent les
dumps de données synthétiques du MVP. Chaque serveur charge son dump une seule
fois au démarrage et n'effectue **aucune** écriture.

## Prérequis

```bash
pip install -r requirements.txt   # installe le SDK mcp (FastMCP)
python data/generate_all.py       # (re)génère les dumps JSON dans data/
```

> Note : la base SQLite annexe **n'a PAS de serveur MCP**. Elle est lue en
> direct par la couche d'ingestion, pas via MCP.

## Lancer chaque serveur (seul, stdio)

```bash
python mcp_mocks/dashdoc_server.py   # TMS
python mcp_mocks/odoo_server.py      # ERP
python mcp_mocks/email_server.py     # Emails
```

`mcp.run()` ouvre une boucle stdio bloquante : le serveur attend un client MCP
sur stdin/stdout (il ne "rend pas la main" tant qu'aucun EOF/client n'est là).

---

## Outils exposés

### `dashdoc_server.py` — TMS (lit `data/dashdoc/dashdoc_dump.json`)

| Outil | Description |
|---|---|
| `list_transports()` | Liste tous les transports |
| `get_transport(uid: str)` | Transport par `uid` (ou erreur structurée) |
| `list_vehicles()` | Liste de la flotte |
| `list_drivers()` | Liste des chauffeurs |
| `list_carriers()` | Liste des transporteurs |

**Exemples I/O**

- `list_transports()` -> `[ {"uid": "SH-2049", "status": "Delayed", ...}, ... ]` (28 transports)
- `get_transport("SH-2049")` -> `{"uid": "SH-2049", "status": "Delayed", "carrier": {"name": "ColdRoad"}, "deliveries": [{"sku": "PHARMA-22", "quantity": 1000}], "tracking": {"eta": "..."}, ...}`
- `get_transport("NOPE")` -> `{"error": "not_found", "resource": "transport", "uid": "NOPE"}`
- `list_vehicles()` -> `[ {"license_plate": "033-TLC-96", "type": "frigo", "year": 2021, "is_refrigerated": true}, ... ]`
- `list_drivers()` -> `[ {"driver_id": "DRV-001", "name": "Laurent Guillon", "certifications": ["ADR"]}, ... ]`
- `list_carriers()` -> `[ {"carrier_id": "CAR-COLDROAD", "name": "ColdRoad", "service_type": "Cold-chain", "reliability_score": 0.78}, ... ]`

### `odoo_server.py` — ERP (lit `data/odoo/odoo_dump.json`)

| Outil | Description |
|---|---|
| `list_partners()` | Clients `res.partner` |
| `get_partner(partner_id: str)` | Partenaire par `partner_id` (ou erreur) |
| `list_sale_orders()` | Commandes `sale.order` |
| `list_invoices()` | Factures `account.move` |
| `get_invoice(move_id: str)` | Facture par `move_id` (ou erreur) |
| `list_products()` | Produits `product.product` |
| `list_suppliers()` | Fournisseurs `res.partner.suppliers` |

**Exemples I/O**

- `list_partners()` -> `[ {"partner_id": "C001", "name": "MedPharma", "category": "Platinum", "x_strategic_value": 1200000, ...}, ... ]`
- `get_partner("C001")` -> `{"partner_id": "C001", "name": "MedPharma", "industry_id": "Pharma", "user_id": "Sarah Martin", ...}`
- `get_partner("NOPE")` -> `{"error": "not_found", "resource": "res.partner", "partner_id": "NOPE"}`
- `list_sale_orders()` -> `[ {"order_id": "O-881", "partner_id": "C001", "client_order_ref": "PO-8821", "date_order": "2026-06-24", "state": "open"}, ... ]`
- `list_invoices()` -> `[ {"move_id": "INV-7742", "amount_total": 186000, ...}, ... ]` (28 factures)
- `get_invoice("INV-7742")` -> `{"move_id": "INV-7742", "invoice_origin": "PO-8821", "partner_id": "C001", "amount_total": 186000, "currency_id": "EUR", "payment_state": "not_paid"}`
- `get_invoice("NOPE")` -> `{"error": "not_found", "resource": "account.move", "move_id": "NOPE"}`
- `list_products()` -> `[ {"product_id": "PHARMA-22", "name": "Insulin batch", "categ_id": "Cold-chain", "x_temp_min": 2, "x_temp_max": 8, "list_price": 180}, ... ]`
- `list_suppliers()` -> `[ {"partner_id": "SUP-01", "name": "TotalEnergies Fleet", "category": "Fuel", "property_payment_term_id": 60, ...}, ... ]`

### `email_server.py` — Emails (parse `data/emails/raw/*.eml` au démarrage)

| Outil | Description |
|---|---|
| `list_emails()` | Tous les emails |
| `get_email(id: str)` | Email par `id` (ou erreur) |
| `search_emails(query: str)` | Recherche insensible à la casse dans `subject` + `body` + `from` |

**Exemples I/O**

- `list_emails()` -> `[ {"id": "EM-001", "from": "operations@coldroad-logistics.com", "subject": "Delay notification - Shipment SH-2049", ...}, ... ]` (6 emails)
- `get_email("EM-001")` -> `{"id": "EM-001", "from": "...", "to": "...", "subject": "...", "body": "...", "received_at": "...", "labels": [...]}`
- `get_email("NOPE")` -> `{"error": "not_found", "resource": "email", "id": "NOPE"}`
- `search_emails("SH-2049")` -> `[ {"id": "EM-001", "subject": "Delay notification - Shipment SH-2049", ...} ]`
- `search_emails("inconnu")` -> `[]`

---

## Bloc `.mcp.json` (prêt à copier)

Branche les 3 serveurs. Adaptez `command` au binaire Python de votre venv si
besoin (ici le venv `.venv` du projet).

```json
{
  "mcpServers": {
    "dashdoc-tms": {
      "command": ".venv/bin/python",
      "args": ["mcp_mocks/dashdoc_server.py"]
    },
    "odoo-erp": {
      "command": ".venv/bin/python",
      "args": ["mcp_mocks/odoo_server.py"]
    },
    "email-inbox": {
      "command": ".venv/bin/python",
      "args": ["mcp_mocks/email_server.py"]
    }
  }
}
```

> Si vous préférez le Python du PATH, remplacez `".venv/bin/python"` par
> `"python"`. Les chemins `args` peuvent être absolus pour plus de robustesse.
