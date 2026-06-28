"""supervisor.py — orchestration DÉTERMINISTE des passes (Système A, étage 2).

Enchaîne P0 → P1 → … → P6 → P7 dans un workflow fixe (le raisonnement agentique vit DANS
les passes, pas ici). Chaque passe LLM est rejouée UNE fois en cas d'échec (JSON invalide /
contrat non respecté) ; si elle échoue encore, on s'arrête proprement. Gère `--dry-run`
(passes déterministes seules) et `--passes` (sous-ensemble, via rechargement du Blackboard).

Garde-fou (CLAUDE §9) : le superviseur n'importe ni canonical, ni le manifest, ni l'oracle.
"""

from __future__ import annotations

import json
from pathlib import Path

from ._agent import BudgetExhausted
from .blackboard import Blackboard
from .logging_ui import RunLogger
from .passes import (
    p0_extraction, p1_profiler, p2_entities, p3_relationships,
    p4_attributes, p5_architect, p6_critic, p7_validation,
)

ROOT = Path(__file__).resolve().parents[1]
OUT_ONTOLOGY = ROOT / "outputs" / "ontology.agentic.json"
OUT_BLACKBOARD = ROOT / "outputs" / "blackboard.json"

LLM_PASSES = {
    "p1": p1_profiler, "p2": p2_entities, "p3": p3_relationships,
    "p4": p4_attributes, "p5": p5_architect, "p6": p6_critic,
}
LLM_ORDER = ["p1", "p2", "p3", "p4", "p5", "p6"]
# Passes qui gèrent leur propre retry par sous-requête → pas de retry global (anti double-coût).
_SELF_RETRYING = {"p2", "p3"}


async def _run_llm_pass(pid: str, bb: Blackboard, logger: RunLogger) -> None:
    """Exécute une passe LLM avec retry x1 (CLAUDE §3 : propose → valide).

    Exception : un dépassement de budget (`BudgetExhausted`) n'est PAS rejoué (le retry
    re-paierait pour rien) — on remonte pour arrêter le pipeline proprement.
    """
    mod = LLM_PASSES[pid]
    # P2/P3 sont chunkées et gèrent DÉJÀ leur retry par sous-requête (run_pass_resilient) :
    # un retry de toute la passe ici re-paierait les chunks déjà réussis (le bug observé).
    if pid in _SELF_RETRYING:
        await mod.run(bb, logger)
        return
    try:
        await mod.run(bb, logger)
    except BudgetExhausted:
        raise
    except Exception as e:  # noqa: BLE001 — on veut un retry contrôlé
        logger.warn(f"{pid} a échoué ({type(e).__name__}: {str(e)[:160]}) — nouvel essai")
        bb.log(pid, "retry", str(e)[:200])
        await mod.run(bb, logger)  # 2e essai ; s'il relance, on remonte l'exception


async def run_pipeline(passes: list[str] | None = None, dry_run: bool = False,
                       max_budget: float | None = None) -> int:
    """Exécute le pipeline. Retourne un code de sortie (0 = OK)."""
    logger = RunLogger(ROOT / "outputs" / "run_log.md",
                       max_budget=None if dry_run else max_budget)

    # Blackboard : neuf, ou rechargé si on rejoue un sous-ensemble
    if passes and OUT_BLACKBOARD.exists():
        bb = Blackboard.load_json(OUT_BLACKBOARD)
        logger.info(f"Blackboard rechargé depuis {OUT_BLACKBOARD.name}")
    else:
        bb = Blackboard()
    # Auto-sauvegarde après chaque chunk (P2/P3) → une interruption (budget) garde le travail
    # déjà fait, et une relance saute les chunks aboutis (reprise, cf. blackboard.checkpoint).
    bb.set_autosave(OUT_BLACKBOARD)

    selected = passes or (["p0"] + ([] if dry_run else LLM_ORDER) + ["p7"])
    # P0 est requis si on va lancer des passes LLM et que raw est vide
    if any(p in LLM_PASSES for p in selected) and not bb.raw and "p0" not in selected:
        selected = ["p0"] + selected

    budget_str = f" · budget ${max_budget:.2f}" if (max_budget and not dry_run) else ""
    logger.info(f"passes : {', '.join(selected)}"
                + (" (dry-run)" if dry_run else budget_str))

    if "p0" in selected:
        p0_extraction.run(bb, logger)

    budget_hit = False
    if not dry_run:
        try:
            for pid in LLM_ORDER:
                if pid in selected:
                    await _run_llm_pass(pid, bb, logger)
        except BudgetExhausted as e:
            budget_hit = True
            logger.error(f"PLAFOND DE BUDGET ATTEINT : {e} — arrêt propre, sortie partielle "
                         "écrite (relance avec un --max-budget plus haut pour finir).")
    else:
        logger.warn("dry-run : passes LLM P1→P6 ignorées")

    # En dry-run, on produit un draft MINIMAL pour prouver l'écriture de bout en bout.
    if dry_run and not bb.ontology_draft:
        bb.ontology_draft = {"entities": [], "relationships": [],
                             "_note": "dry-run : aucune passe LLM exécutée"}

    # P7 ne tourne pas si on s'est arrêté sur budget (le draft est incomplet → faux négatifs).
    val_ok = True
    if "p7" in selected and not dry_run and not budget_hit:
        val_ok = p7_validation.run(bb, logger)

    # Écritures
    OUT_ONTOLOGY.parent.mkdir(parents=True, exist_ok=True)
    if bb.ontology_draft:
        OUT_ONTOLOGY.write_text(
            json.dumps(bb.ontology_draft, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.summary(f"écrit : {OUT_ONTOLOGY.relative_to(ROOT)}")
    bb.dump_json(OUT_BLACKBOARD)
    logger.finalize()
    if budget_hit:
        return 2
    return 0 if val_ok else 1
