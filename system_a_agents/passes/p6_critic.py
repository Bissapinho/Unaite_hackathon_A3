"""P6 — Critic / Consistency (Opus 4.8).

Attaque la proposition assemblée à partir de son PROFIL COMPACT + anomalies mécaniques ;
renvoie findings + actions correctives, appliquées au draft. Écrit le `bb.ontology_draft` final.
"""

from __future__ import annotations

import json

from .._agent import load_prompt, run_pass
from .._assemble import apply_actions, compact_profile, finalize, merge_entities
from ..blackboard import Blackboard
from ..contracts import CriticReview
from ..logging_ui import RunLogger
from ..models import MAX_TURNS, PASS_MODEL, SYSTEM_PROMPTS


async def run(bb: Blackboard, logger: RunLogger) -> None:
    logger.banner("p6", "Critic / Consistency", PASS_MODEL["p6"])
    draft = bb.ontology_draft
    profile = compact_profile(draft)
    task = load_prompt("p6_critic.md") + "\n```json\n" + \
        json.dumps(profile, ensure_ascii=False) + "\n```\n"
    obj = await run_pass(
        pass_id="p6", model=PASS_MODEL["p6"], system_prompt=SYSTEM_PROMPTS["p6"],
        task_prompt=task, allowed_tools=[], logger=logger, max_turns=MAX_TURNS["p6"])
    review = CriticReview.model_validate(obj)

    if review.actions:
        emap = merge_entities(draft["entities"])
        rels = [dict(r) for r in draft["relationships"]]
        apply_actions(emap, rels, review.actions)
        draft = finalize(emap, rels)
        bb.ontology_draft = draft

    bb.critic_findings = {
        "findings": [f.model_dump() for f in review.findings],
        "actions": review.actions,
    }
    blockers = [f for f in review.findings if f.severity == "blocker"]
    bb.log("p6", "critic",
           f"{len(review.findings)} findings ({len(blockers)} blockers), "
           f"{len(review.actions)} corrections")
    for f in review.findings[:12]:
        (logger.error if f.severity == "blocker" else logger.warn)(
            f"[{f.severity}] {f.kind}: {f.detail[:120]}")
    logger.summary(f"critic : {len(review.findings)} constats, "
                   f"{len(review.actions)} corrections appliquées")
