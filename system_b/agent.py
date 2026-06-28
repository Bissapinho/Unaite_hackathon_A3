"""agent.py — l'agent SDK de B : answer(question) -> dict (le contrat de l'UI).

B charge le graphe (graph_store), lance Claude (Opus 4.8) avec les outils de requête en
lecture seule (tools.py), TRACE chaque appel d'outil (logs visibles, critère #1 du jury),
puis renvoie le contrat stable attendu par l'UI Flask :

    {answer, evidence, actions, node_ids, tool_trace}

`answer_async` accepte un callback `on_event` optionnel : il émet les events d'outils au fil
de l'eau (pour un éventuel endpoint SSE), sans refonte. `answer` est le wrapper synchrone.
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any, Awaitable, Callable

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    create_sdk_mcp_server,
    query,
    tool,
)

from system_a_agents.logging_ui import RunLogger
from system_a_agents.models import MODEL_OPUS

from . import tools
from .graph_store import get_graph

ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "system_b.md"

# Comme pour A : bloquer la DÉCOUVERTE d'outils (on les donne déjà nommément) → pas de tours
# gaspillés à appeler ToolSearch.
_DISALLOWED = ["ToolSearch"]

EventCallback = Callable[[dict[str, Any]], Awaitable[None] | None]

# --------------------------------------------------------------------------- #
# Outil de SORTIE STRUCTURÉE — l'agent termine en appelant submit_answer.
# Remplir un schéma d'outil est bien plus fiable que produire du JSON libre : le contrat
# est ainsi garanti même quand le modèle ferait une coquille de syntaxe JSON. C'est de la
# remontée de données, PAS une exécution (aucun effet de bord — frontière §9 respectée).
# --------------------------------------------------------------------------- #
_SUBMIT_SERVER = "system_b_submit"
SUBMIT_TOOL = f"mcp__{_SUBMIT_SERVER}__submit_answer"


def _submit_ok() -> dict:
    return {"content": [{"type": "text", "text": json.dumps({"received": True})}]}


@tool(
    "submit_answer",
    "Submit the FINAL answer to the user. Call this exactly once, last, after your queries. "
    "Fields: answer (str, natural-language English answer), evidence (list of {claim, "
    "sources}), actions (list of {label, detail}, proposals only), node_ids (list of str, the "
    "ids of every node you highlighted — always populated).",
    {"answer": str, "evidence": list, "actions": list, "node_ids": list},
)
async def submit_answer(args) -> dict:  # capture réelle faite dans la boucle (block.input)
    return _submit_ok()


def _submit_server():
    return create_sdk_mcp_server(_SUBMIT_SERVER, "1.0.0", tools=[submit_answer])


# --------------------------------------------------------------------------- #
# Extraction du JSON final (même esprit que system_a_agents._agent.extract_json)
# --------------------------------------------------------------------------- #
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def _extract_json(text: str) -> Any:
    """Extrait le dernier objet JSON valide du texte (fences ou accolades brutes)."""
    candidates: list[str] = [m.group(1).strip() for m in _FENCE_RE.finditer(text)]
    candidates.append(text.strip())
    i, j = text.find("{"), text.rfind("}")
    if i != -1 and j != -1 and j > i:
        candidates.append(text[i : j + 1])
    for cand in reversed(candidates):
        try:
            return json.loads(cand)
        except (json.JSONDecodeError, ValueError):
            continue
    return None


def _result_summary(content: Any) -> str:
    """Résumé court d'un résultat d'outil pour la trace (n résultats / 1 objet / erreur)."""
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


def _build_options(model: str = MODEL_OPUS) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        model=model,  # défaut Opus 4.8 (raisonnement de B, CLAUDE §3) ; surchargé pour bench
        system_prompt=PROMPT_PATH.read_text(encoding="utf-8"),
        mcp_servers={tools.SERVER_NAME: tools.query_server(), _SUBMIT_SERVER: _submit_server()},
        allowed_tools=[*tools.TOOL_NAMES, SUBMIT_TOOL],
        disallowed_tools=_DISALLOWED,
        permission_mode="bypassPermissions",
        setting_sources=None,  # n'ingère aucun settings/CLAUDE.md du repo
        cwd=str(ROOT),
        max_turns=16,  # marge ; submit_answer arrête la boucle bien avant en pratique
    )


# Marqueurs de tool-call (pseudo-XML) que le modèle laisse parfois FUIR dans le champ
# `answer` quand la sortie structurée est longue. On tronque `answer` au premier marqueur.
_LEAK_MARKERS = ("</answer>", "<answer>", "<parameter name=", "</parameter>",
                 "<invoke", "</invoke", "<function_calls", "</function_calls")


def _clean_answer(text: str) -> str:
    """Nettoie le champ answer d'une fuite de syntaxe d'appel d'outil (cf. _LEAK_MARKERS)."""
    cut = len(text)
    for marker in _LEAK_MARKERS:
        idx = text.find(marker)
        if idx != -1:
            cut = min(cut, idx)
    return text[:cut].strip()


def _coerce_contract(parsed: Any, fallback_text: str, node_ids: list[str], trace: list[dict]) -> dict:
    """Garantit la forme EXACTE du contrat, même si le JSON de l'agent est partiel/absent.

    `parsed` provient en priorité de l'outil submit_answer (args structurés, fiables) ;
    à défaut, du JSON extrait du texte final ; à défaut, le texte brut sert de réponse.
    """
    out: dict[str, Any] = {
        "answer": fallback_text,
        "evidence": [],
        "actions": [],
        "node_ids": [],
        "tool_trace": trace,
    }
    if isinstance(parsed, dict):
        if isinstance(parsed.get("answer"), str) and parsed["answer"].strip():
            out["answer"] = _clean_answer(parsed["answer"])
        if isinstance(parsed.get("evidence"), list):
            out["evidence"] = parsed["evidence"]
        if isinstance(parsed.get("actions"), list):
            out["actions"] = parsed["actions"]
        if isinstance(parsed.get("node_ids"), list):
            out["node_ids"] = [str(n) for n in parsed["node_ids"]]
    # node_ids toujours peuplé : à défaut, retomber sur ceux vus dans les appels d'outils.
    if not out["node_ids"]:
        out["node_ids"] = node_ids
    return out


async def answer_async(
    question: str, on_event: EventCallback | None = None, model: str = MODEL_OPUS
) -> dict:
    """Répond à `question` en interrogeant l'ontologie. Renvoie le contrat UI.

    `on_event`, si fourni, est appelé pour chaque event d'outil (`{"type": "tool_call",
    "tool": ..., "args": ..., "result_summary": ...}`) puis un event `{"type": "usage",
    cost_usd, input_tokens, output_tokens}` en fin de run — base d'un streaming SSE / bench.
    `model` surcharge le modèle (défaut Opus 4.8).
    """
    get_graph()  # s'assure que l'ontologie est chargée (et échoue tôt sinon)
    logger = RunLogger(ROOT / "outputs" / "system_b_log.md")
    logger.banner("système-b", f"Question : {question[:80]}", model)

    options = _build_options(model)
    pending: dict[str, tuple[str, dict]] = {}  # tool_use_id -> (tool, args)
    node_ids_seen: list[str] = []
    tool_trace: list[dict[str, Any]] = []
    final_text_parts: list[str] = []
    submitted: dict[str, Any] | None = None  # args de submit_answer (sortie structurée)

    async def _emit(event: dict[str, Any]) -> None:
        if on_event is None:
            return
        res = on_event(event)
        if asyncio.iscoroutine(res):
            await res

    agen = query(prompt=question, options=options)
    async for msg in agen:
        if isinstance(msg, AssistantMessage):
            text_here: list[str] = []
            for block in msg.content:
                if isinstance(block, ToolUseBlock):
                    parts = block.name.split("__")
                    tool_name = parts[-1]
                    pending[block.id] = (tool_name, block.input or {})
                elif isinstance(block, TextBlock):
                    text_here.append(block.text)
            if text_here:
                final_text_parts = text_here  # garde le dernier message texte
        elif isinstance(msg, UserMessage):
            for block in msg.content if isinstance(msg.content, list) else []:
                if isinstance(block, ToolResultBlock):
                    tool_name, args = pending.pop(block.tool_use_id, ("?", {}))
                    if tool_name == "submit_answer":
                        # submit_answer est TERMINAL : on a le contrat structuré, on arrête la
                        # boucle tout de suite. (Sans ça, le modèle peut rappeler submit_answer
                        # en boucle et heurter max_turns → erreur ; et on gagne en latence/coût.)
                        submitted = args
                        logger.info("↳ submit_answer (réponse finale structurée) — fin")
                        break
                    summary = _result_summary(block.content)
                    logger.tool_call(tools.SERVER_NAME, tool_name, args, summary)
                    entry = {"tool": tool_name, "args": args, "result_summary": summary}
                    tool_trace.append(entry)
                    _collect_node_ids(block.content, node_ids_seen)
                    await _emit({"type": "tool_call", **entry})
            if submitted is not None:
                await agen.aclose()  # ferme proprement le flux SDK (pas de sous-processus orphelin)
                break
        elif isinstance(msg, ResultMessage):
            u = msg.usage or {}
            await _emit(
                {
                    "type": "usage",
                    "cost_usd": msg.total_cost_usd or 0.0,
                    "input_tokens": u.get("input_tokens", 0) or 0,
                    "output_tokens": u.get("output_tokens", 0) or 0,
                    "cache_read_input_tokens": u.get("cache_read_input_tokens", 0) or 0,
                }
            )
            logger.usage(
                u.get("input_tokens", 0) or 0,
                u.get("output_tokens", 0) or 0,
                u.get("cache_read_input_tokens", 0) or 0,
                u.get("cache_creation_input_tokens", 0) or 0,
                msg.total_cost_usd or 0.0,
            )

    final_text = "\n".join(final_text_parts).strip()
    logger.agent_text("système-b", final_text)
    # Priorité à la sortie structurée (submit_answer) ; sinon, JSON extrait du texte final.
    parsed = submitted if submitted is not None else _extract_json(final_text)
    fallback = final_text or "Aucune réponse produite."
    contract = _coerce_contract(parsed, fallback, node_ids_seen, tool_trace)
    logger.summary(
        f"{len(tool_trace)} appels outils · {len(contract['node_ids'])} nœuds · "
        f"{len(contract['evidence'])} preuves · {len(contract['actions'])} actions"
    )
    logger.finalize()
    await _emit({"type": "result", "contract": contract})
    return contract


def _collect_node_ids(content: Any, acc: list[str]) -> None:
    """Récupère les ids `type:slug` présents dans un résultat d'outil (fallback node_ids)."""
    text = content
    if isinstance(content, list):
        text = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        return

    def _walk(obj: Any) -> None:
        if isinstance(obj, dict):
            nid = obj.get("id") or obj.get("shipment_id") or obj.get("node_id")
            if isinstance(nid, str) and ":" in nid and nid not in acc:
                acc.append(nid)
            for value in obj.values():
                _walk(value)
        elif isinstance(obj, list):
            for value in obj:
                _walk(value)

    _walk(parsed)


def answer(question: str, model: str = MODEL_OPUS) -> dict:
    """Wrapper synchrone de `answer_async` (pratique pour Flask : asyncio.run(...))."""
    return asyncio.run(answer_async(question, model=model))


if __name__ == "__main__":  # smoke test manuel : python -m system_b.agent "ma question"
    import sys

    q = " ".join(sys.argv[1:]) or "Y a-t-il un problème avec une livraison ?"
    print(json.dumps(answer(q), ensure_ascii=False, indent=2))
