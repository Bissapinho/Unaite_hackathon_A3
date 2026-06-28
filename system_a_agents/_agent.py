"""_agent.py — glue Claude Agent SDK : exécute une passe LLM en montrant son travail.

Une passe LLM = un system prompt statique (models.py) + un prompt de tâche
(prompts/pX.md) + des outils (MCP mock + readers). Ce module lance `query(...)`,
TRACE chaque appel d'outil (logs visibles, critère #1), accumule la réponse, en
extrait le JSON, et renvoie (objet, usage). Aucune sémantique métier ici : pure glue.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    query,
)

from .logging_ui import RunLogger
from .tools import mcp_clients, readers

ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


class BudgetExhausted(Exception):
    """Le plafond de coût (--max-budget) est atteint : on arrête proprement, sans retry."""


def load_prompt(name: str) -> str:
    """Charge un prompt de tâche versionné depuis prompts/<name>.md."""
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# Extraction du JSON de la réponse finale
# --------------------------------------------------------------------------- #
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json(text: str) -> Any:
    """Extrait le dernier objet JSON valide du texte (fences ou accolades brutes)."""
    candidates: list[str] = []
    candidates.extend(m.group(1).strip() for m in _FENCE_RE.finditer(text))
    candidates.append(text.strip())
    # substring de la première { à la dernière }
    i, j = text.find("{"), text.rfind("}")
    if i != -1 and j != -1 and j > i:
        candidates.append(text[i : j + 1])
    for cand in reversed(candidates):
        try:
            return json.loads(cand)
        except (json.JSONDecodeError, ValueError):
            continue
    raise ValueError("aucun JSON valide dans la réponse de l'agent")


def _count_results(content: Any) -> str:
    """Estime le nombre de résultats d'un ToolResultBlock pour les logs."""
    text = content
    if isinstance(content, list):
        text = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        return f"{len(str(text))} car."
    if isinstance(parsed, list):
        return f"{len(parsed)} résultats"
    if isinstance(parsed, dict):
        if parsed.get("error"):
            return f"erreur:{parsed.get('error')}"
        return "1 objet"
    return "ok"


# Outils de DÉCOUVERTE à bloquer : l'agent les appelait (`ToolSearch(...) → 0 car.`) pour
# « chercher » des outils qu'on lui donne déjà nommément → tours gaspillés, pur coût.
_DISALLOWED = ["ToolSearch"]


def _build_options(model: str, system_prompt: str, allowed_tools: list[str],
                   max_turns: int, max_budget_usd: float | None = None) -> ClaudeAgentOptions:
    mcp_servers = dict(mcp_clients.stdio_servers())
    mcp_servers[readers.READERS_SERVER_NAME] = readers.readers_server()
    return ClaudeAgentOptions(
        model=model,
        system_prompt=system_prompt,  # string STABLE par passe → préfixe cache-hit
        mcp_servers=mcp_servers,
        allowed_tools=allowed_tools,
        disallowed_tools=_DISALLOWED,
        permission_mode="bypassPermissions",
        setting_sources=None,  # n'ingère AUCUN settings/CLAUDE.md du repo
        cwd=str(ROOT),
        max_turns=max_turns,
        max_budget_usd=max_budget_usd,  # plafond dur (le run s'arrête seul s'il dérape)
    )


async def run_pass(
    *,
    pass_id: str,
    model: str,
    system_prompt: str,
    task_prompt: str,
    allowed_tools: list[str],
    logger: RunLogger,
    max_turns: int = 8,
) -> dict:
    """Exécute une (sous-)requête LLM, trace les outils, renvoie l'objet JSON parsé."""
    # Plafond de coût : on passe le BUDGET RESTANT en cap dur à la requête, pour qu'aucune
    # sous-requête ne dépasse le total autorisé. Budget épuisé → on s'arrête sans appeler l'API.
    remaining = logger.budget_remaining()
    if remaining is not None and remaining <= 0.01:
        raise BudgetExhausted(f"budget épuisé avant {pass_id} (reste ${remaining:.2f})")
    mb = round(remaining, 4) if remaining is not None else None

    options = _build_options(model, system_prompt, allowed_tools, max_turns, max_budget_usd=mb)
    pending: dict[str, tuple[str, str, Any]] = {}  # tool_use_id -> (server, tool, args)
    final_text_parts: list[str] = []
    in_tok = out_tok = cache_read = cache_creation = 0
    cost_usd = 0.0

    result_err: str | None = None
    try:
        async for msg in query(prompt=task_prompt, options=options):
            if isinstance(msg, AssistantMessage):
                text_here: list[str] = []
                for block in msg.content:
                    if isinstance(block, ToolUseBlock):
                        name = block.name  # mcp__<server>__<tool>
                        parts = name.split("__")
                        server = parts[1] if len(parts) > 2 else "?"
                        tool = parts[-1]
                        pending[block.id] = (server, tool, block.input)
                    elif isinstance(block, TextBlock):
                        text_here.append(block.text)
                if text_here:
                    final_text_parts = text_here  # garde le dernier message texte
            elif isinstance(msg, UserMessage):
                for block in msg.content if isinstance(msg.content, list) else []:
                    if isinstance(block, ToolResultBlock):
                        server, tool, args = pending.pop(
                            block.tool_use_id, ("?", "?", {}))
                        logger.tool_call(server, tool, args, _count_results(block.content))
            elif isinstance(msg, ResultMessage):
                u = msg.usage or {}
                # Tokens facturés plein tarif vs lus du cache : on les SÉPARE (avant ils
                # étaient additionnés, ce qui masquait l'effet du prompt caching).
                in_tok = u.get("input_tokens", 0) or 0
                out_tok = u.get("output_tokens", 0) or 0
                cache_read = u.get("cache_read_input_tokens", 0) or 0
                cache_creation = u.get("cache_creation_input_tokens", 0) or 0
                cost_usd = msg.total_cost_usd or 0.0
                if getattr(msg, "is_error", False):
                    result_err = (msg.result or msg.subtype or "")
    except Exception as e:  # noqa: BLE001
        # Le SDK signale le dépassement de plafond par une exception générique : on la
        # convertit en BudgetExhausted pour ARRÊTER le run sans le rejouer (le retry
        # re-paierait pour rien — cf. supervisor._run_llm_pass).
        if "budget" in str(e).lower():
            logger.usage(in_tok, out_tok, cache_read, cache_creation, cost_usd)
            raise BudgetExhausted(str(e)[:200]) from e
        raise

    # Plafond atteint signalé via un ResultMessage d'erreur (selon la version du CLI).
    if result_err and "budget" in result_err.lower():
        logger.usage(in_tok, out_tok, cache_read, cache_creation, cost_usd)
        raise BudgetExhausted(result_err[:200])

    final_text = "\n".join(final_text_parts).strip()
    logger.agent_text(pass_id, final_text)
    logger.usage(in_tok, out_tok, cache_read, cache_creation, cost_usd)
    return extract_json(final_text)


async def run_pass_resilient(*, retries: int = 1, **kwargs) -> dict:
    """`run_pass` + retry x`retries` au niveau d'UNE sous-requête (chunk).

    Pour les passes chunked (P2/P3) : si un chunk volumineux échoue (JSON tronqué…), on ne
    rejoue QUE ce chunk, pas toute la passe (sinon on re-paie les chunks déjà réussis). Un
    dépassement de budget n'est jamais rejoué.
    """
    logger: RunLogger = kwargs["logger"]
    attempt = 0
    while True:
        try:
            return await run_pass(**kwargs)
        except BudgetExhausted:
            raise
        except Exception as e:  # noqa: BLE001
            attempt += 1
            if attempt > retries:
                raise
            logger.warn(f"sous-requête {kwargs.get('pass_id')} échouée "
                        f"({type(e).__name__}: {str(e)[:120]}) — nouvel essai du chunk")
