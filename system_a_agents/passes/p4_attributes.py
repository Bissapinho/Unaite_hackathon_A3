"""P4 — Attribute Mapping & Finances (Sonnet 4.6). Patches d'attributs + agrégats financiers."""

from __future__ import annotations

from .._agent import load_prompt, run_pass
from ..blackboard import Blackboard
from ..contracts import AttributesOutput
from ..logging_ui import RunLogger
from ..models import MAX_TURNS, PASS_MODEL, SYSTEM_PROMPTS
from ..tools import mcp_clients as mc
from ..tools.readers import TOOL_NAMES as R


async def run(bb: Blackboard, logger: RunLogger) -> None:
    logger.banner("p4", "Attribute Mapping & Finances", PASS_MODEL["p4"])
    tools = [R["xlsx_sheet"], R["sum_amounts"]] + mc.tool_names(mc.ODOO) + mc.tool_names(mc.EMAIL)
    task = load_prompt("p4_attributes.md")
    obj = await run_pass(
        pass_id="p4", model=PASS_MODEL["p4"], system_prompt=SYSTEM_PROMPTS["p4"],
        task_prompt=task, allowed_tools=tools, logger=logger, max_turns=MAX_TURNS["p4"])
    parsed = AttributesOutput.model_validate(obj)
    bb.attributes = {"patches": [p.model_dump() for p in parsed.patches]}
    bb.log("p4", "attributes", f"{len(parsed.patches)} patches")
    logger.summary(f"{len(parsed.patches)} patches d'attributs (dont finances)")
