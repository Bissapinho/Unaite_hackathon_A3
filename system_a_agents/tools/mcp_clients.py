"""mcp_clients.py — config des 3 serveurs MCP mock (stdio) + registre des outils.

Réutilise le bloc de `mcp_mocks/README.md` (chemins venv). Ces serveurs sont en
LECTURE SEULE. Les noms de serveur ci-dessous deviennent le namespace SDK des outils :
`mcp__<server>__<tool>`.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable  # le python courant (venv) — robuste quel que soit l'OS

ODOO = "odoo_erp"
DASHDOC = "dashdoc_tms"
EMAIL = "email_inbox"


def stdio_servers() -> dict:
    """Config stdio des 3 mock pour ClaudeAgentOptions(mcp_servers=...)."""
    return {
        ODOO: {
            "type": "stdio",
            "command": PY,
            "args": [str(ROOT / "mcp_mocks" / "odoo_server.py")],
        },
        DASHDOC: {
            "type": "stdio",
            "command": PY,
            "args": [str(ROOT / "mcp_mocks" / "dashdoc_server.py")],
        },
        EMAIL: {
            "type": "stdio",
            "command": PY,
            "args": [str(ROOT / "mcp_mocks" / "email_server.py")],
        },
    }


# outils par serveur (cf. mcp_mocks/README.md)
ODOO_TOOLS = ["list_partners", "get_partner", "list_sale_orders", "list_invoices",
              "get_invoice", "list_products", "list_suppliers"]
DASHDOC_TOOLS = ["list_transports", "get_transport", "list_vehicles", "list_drivers",
                 "list_carriers"]
EMAIL_TOOLS = ["list_emails", "get_email", "search_emails"]


def _ns(server: str, tools: list[str]) -> list[str]:
    return [f"mcp__{server}__{t}" for t in tools]


def tool_names(server: str) -> list[str]:
    return {
        ODOO: _ns(ODOO, ODOO_TOOLS),
        DASHDOC: _ns(DASHDOC, DASHDOC_TOOLS),
        EMAIL: _ns(EMAIL, EMAIL_TOOLS),
    }[server]


ALL_MCP_TOOL_NAMES = tool_names(ODOO) + tool_names(DASHDOC) + tool_names(EMAIL)
