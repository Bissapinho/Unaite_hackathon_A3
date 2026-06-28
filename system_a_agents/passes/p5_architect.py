"""P5 — Ontology Architect (Opus 4.8).

Assemble la proposition au format §4 (fusion entités P2 + patches P4 + relations P3, ids
normalisés, orphelines/doublons écartés) PUIS soumet un PROFIL COMPACT à Opus, qui revoit la
cohérence structurelle et émet des ACTIONS correctives ciblées (sans re-sérialiser le graphe —
décision d'ingénierie tracée dans CALIBRATION.md). Écrit `bb.ontology_draft`.
"""

from __future__ import annotations

import json

from .._agent import load_prompt, run_pass
from .._assemble import assemble, compact_profile
from ..blackboard import Blackboard
from ..contracts import ArchitectOutput
from ..logging_ui import RunLogger
from ..models import MAX_TURNS, PASS_MODEL, SYSTEM_PROMPTS


async def run(bb: Blackboard, logger: RunLogger) -> None:
    logger.banner("p5", "Ontology Architect", PASS_MODEL["p5"])
    patches = bb.attributes.get("patches", [])
    draft = assemble(bb.entities_proposed, bb.relationships_proposed, patches)
    logger.info(f"assemblage : {len(draft['entities'])} entités, "
                f"{len(draft['relationships'])} relations")

    profile = compact_profile(draft)
    task = load_prompt("p5_architect.md") + "\n```json\n" + \
        json.dumps(profile, ensure_ascii=False) + "\n```\n"
    obj = await run_pass(
        pass_id="p5", model=PASS_MODEL["p5"], system_prompt=SYSTEM_PROMPTS["p5"],
        task_prompt=task, allowed_tools=[], logger=logger, max_turns=MAX_TURNS["p5"])
    review = ArchitectOutput.model_validate(obj)
    if review.actions:
        draft = assemble(bb.entities_proposed, bb.relationships_proposed, patches,
                         actions=review.actions)
    bb.ontology_draft = draft
    bb.log("p5", "assembled",
           f"{len(draft['entities'])} entités, {len(draft['relationships'])} relations, "
           f"{len(review.actions)} actions architecte")
    logger.summary(f"proposition assemblée — {len(draft['entities'])} entités, "
                   f"{len(draft['relationships'])} relations ({len(review.actions)} actions)")
    if review.notes:
        logger.info(f"architecte : {review.notes[:160]}")
