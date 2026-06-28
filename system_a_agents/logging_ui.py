"""logging_ui.py — logs « voir le compilateur travailler » (critère #1 du jury).

Affiche, pour chaque passe : une bannière (nom + modèle), CHAQUE appel d'outil
(serveur.outil(args) → n résultats), un résumé (entités/relations/fusions), et les
tokens + durée. Écrit aussi `outputs/run_log.md` (markdown lisible) pour le montage
vidéo de la démo.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

# couleurs ANSI (terminal) — sans dépendance
_C = {
    "reset": "\033[0m", "bold": "\033[1m", "dim": "\033[2m",
    "cyan": "\033[36m", "green": "\033[32m", "yellow": "\033[33m",
    "magenta": "\033[35m", "red": "\033[31m", "blue": "\033[34m",
}


def _short(v: Any, n: int = 80) -> str:
    s = str(v)
    return s if len(s) <= n else s[: n - 1] + "…"


class RunLogger:
    def __init__(self, md_path: str | Path, max_budget: float | None = None):
        self.md_path = Path(md_path)
        self.max_budget = max_budget
        self.lines: list[str] = []
        self._t0 = time.time()
        self._pass_t0 = time.time()
        self.totals = {"input_tokens": 0, "output_tokens": 0, "cache_read": 0,
                       "cache_creation": 0, "cost_usd": 0.0, "tool_calls": 0,
                       "duration_s": 0.0}
        self.md(f"# Système A — extracteur agentique · run_log\n")

    def budget_remaining(self) -> float | None:
        """Budget USD restant (None si pas de plafond)."""
        if self.max_budget is None:
            return None
        return self.max_budget - self.totals["cost_usd"]

    # ---- markdown ---------------------------------------------------------- #
    def md(self, line: str = "") -> None:
        self.lines.append(line)

    def flush(self) -> None:
        self.md_path.parent.mkdir(parents=True, exist_ok=True)
        self.md_path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")

    # ---- console + markdown ------------------------------------------------ #
    def banner(self, pass_id: str, title: str, model: str | None = None) -> None:
        self._pass_t0 = time.time()
        head = f"━━━ {pass_id.upper()} · {title}"
        if model:
            head += f"  [{model}]"
        print(f"\n{_C['bold']}{_C['cyan']}{head}{_C['reset']}")
        self.md(f"\n## {pass_id.upper()} · {title}" + (f" — `{model}`" if model else ""))

    def info(self, msg: str) -> None:
        print(f"  {_C['dim']}{msg}{_C['reset']}")
        self.md(f"- {msg}")

    def tool_call(self, server: str, tool: str, args: Any, n_results: Any) -> None:
        self.totals["tool_calls"] += 1
        a = _short(args, 60)
        line = f"{server}.{tool}({a}) → {n_results}"
        print(f"    {_C['blue']}↳ {line}{_C['reset']}")
        self.md(f"  - 🔧 `{line}`")

    def agent_text(self, pass_id: str, text: str) -> None:
        # trace courte du raisonnement final (sans noyer la console)
        snippet = _short(text.strip().replace("\n", " "), 100)
        print(f"    {_C['dim']}» {snippet}{_C['reset']}")

    def summary(self, msg: str) -> None:
        print(f"  {_C['green']}✓ {msg}{_C['reset']}")
        self.md(f"- ✅ {msg}")

    def warn(self, msg: str) -> None:
        print(f"  {_C['yellow']}⚠ {msg}{_C['reset']}")
        self.md(f"- ⚠️ {msg}")

    def error(self, msg: str) -> None:
        print(f"  {_C['red']}✗ {msg}{_C['reset']}")
        self.md(f"- ❌ {msg}")

    def usage(self, input_tokens: int, output_tokens: int, cache_read: int = 0,
              cache_creation: int = 0, cost_usd: float = 0.0) -> None:
        self.totals["input_tokens"] += input_tokens
        self.totals["output_tokens"] += output_tokens
        self.totals["cache_read"] += cache_read
        self.totals["cache_creation"] += cache_creation
        self.totals["cost_usd"] += cost_usd
        dt = time.time() - self._pass_t0
        cache_str = f" (+{cache_read} cache)" if cache_read else ""
        cost_str = f" · ${cost_usd:.3f}" if cost_usd else ""
        line = (f"{input_tokens} in{cache_str} / {output_tokens} out tokens · "
                f"{dt:.1f}s{cost_str}")
        print(f"  {_C['magenta']}∑ {line}{_C['reset']}")
        self.md(f"- 📊 {line}")

    def finalize(self) -> None:
        self.totals["duration_s"] = time.time() - self._t0
        t = self.totals
        line = (f"TOTAL — {t['tool_calls']} appels outils · "
                f"{t['input_tokens']} in (+{t['cache_read']} cache) / "
                f"{t['output_tokens']} out tokens · "
                f"${t['cost_usd']:.2f} · {t['duration_s']:.1f}s")
        print(f"\n{_C['bold']}{_C['green']}{line}{_C['reset']}")
        self.md(f"\n## {line}")
        self.flush()
