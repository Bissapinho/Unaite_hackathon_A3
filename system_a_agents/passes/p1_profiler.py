"""P1 — Source Profiler (Haiku 4.5). Décrit chaque source isolément."""

from __future__ import annotations

import json

from .._agent import load_prompt, run_pass
from ..blackboard import Blackboard
from ..contracts import ProfilerOutput
from ..logging_ui import RunLogger
from ..models import MAX_TURNS, PASS_MODEL, SYSTEM_PROMPTS


async def run(bb: Blackboard, logger: RunLogger) -> None:
    logger.banner("p1", "Source Profiler", PASS_MODEL["p1"])
    task = load_prompt("p1_profiler.md") + "\n```json\n" + json.dumps(
        bb.raw, ensure_ascii=False)[:12000] + "\n```\n"
    obj = await run_pass(
        pass_id="p1", model=PASS_MODEL["p1"], system_prompt=SYSTEM_PROMPTS["p1"],
        task_prompt=task, allowed_tools=[], logger=logger, max_turns=MAX_TURNS["p1"])
    parsed = ProfilerOutput.model_validate(obj)
    bb.profiles = [p.model_dump() for p in parsed.profiles]
    bb.log("p1", "profiles", f"{len(bb.profiles)} sources profilées")
    logger.summary(f"{len(bb.profiles)} sources profilées")
