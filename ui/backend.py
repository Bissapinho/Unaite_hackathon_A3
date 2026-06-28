"""backend.py — the single bridge to System B.

`app.py` never imports System B directly: everything about "calling B" lives here, so the
day B changes nothing else moves. `answer_for_ui` returns the FROZEN UI contract
(see the /ask spec): {answer, evidence, actions, node_ids, tool_trace}.

Default mode is the REAL B (`system_b.agent.answer`). Set `UI_MOCK=1` to return a hardcoded
SH-2049 contract instead — a dev convenience to iterate on CSS/highlight without paying the
~35 s Opus call. The mock is NOT the default.
"""

from __future__ import annotations

import os

# Hardcoded SH-2049 contract — dev-only fallback (UI_MOCK=1). Shape-identical to the real B.
_MOCK_CONTRACT = {
    "answer": (
        "Yes — shipment SH-2049 is the single hottest disruption. It carries 1,000 units of "
        "PHARMA-22 (insulin, cold-chain 2–8°C) for MedPharma, our most strategic customer. "
        "The ColdRoad truck broke down near Lyon: 6h delay past the 18:00 contractual "
        "deadline, while the cooling unit battery only lasts 3h. Linked invoice INV-7742 "
        "(€186,000, still Pending) is the largest open invoice, and contract CT-001 carries a "
        "€7,000/h penalty plus mandatory escalation to account manager Sarah Martin."
    ),
    "evidence": [
        {"claim": "SH-2049 carries PHARMA-22 cold-chain for MedPharma",
         "sources": ["dashdoc.transports:SH-2049", "odoo.sale_order:O-881"]},
        {"claim": "6h delay past 18:00 deadline; battery lasts 3h",
         "sources": ["email:EM-001", "pdf.sla:CT-001"]},
        {"claim": "INV-7742 = €186,000, payment_state not_paid",
         "sources": ["odoo.account_move:INV-7742"]},
        {"claim": "CT-001 penalty €7,000/h + escalation to Sarah Martin",
         "sources": ["pdf.sla:CT-001", "odoo.res_partner:C001"]},
    ],
    "actions": [
        {"label": "Book ColdFast Express", "detail": "Paris→Lyon, 20 pallets, €2,400"},
        {"label": "Notify MedPharma", "detail": "Proactive delay notice to account contact"},
        {"label": "Create incident", "detail": "Open cold-chain incident on SH-2049"},
        {"label": "Escalate to Sarah Martin", "detail": "Account manager, per CT-001 SLA"},
    ],
    "node_ids": ["shipment:sh-2049", "customer:medpharma", "contract:ct-001", "invoice:inv-7742"],
    "tool_trace": [
        {"tool": "score_delayed_shipments", "args": {}, "result_summary": "7 results"},
        {"tool": "get_subgraph", "args": {"node": "shipment:sh-2049", "depth": 2}, "result_summary": "1 objet"},
        {"tool": "compute_impact", "args": {"shipment": "shipment:sh-2049"}, "result_summary": "1 objet"},
    ],
}


def answer_for_ui(question: str) -> dict:
    """Return the UI contract for `question` by querying System B (or the mock)."""
    if os.environ.get("UI_MOCK") == "1":
        return _MOCK_CONTRACT

    # Imported lazily so UI_MOCK dev mode never needs the SDK / API key.
    from system_b.agent import answer

    # `answer()` already wraps `answer_async` in `asyncio.run(...)`. Flask's dev server is
    # sync (no running loop), so calling it directly is correct — do NOT wrap in asyncio.run.
    return answer(question)
