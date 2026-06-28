"""run.py — point d'entrée de l'extracteur agentique (Système A, étage 2).

Usage :
  python -m system_a_agents.run                 # pipeline complet (8 passes), nécessite la clé
  python -m system_a_agents.run --dry-run       # P0 + écriture, SANS clé API (test plomberie)
  python -m system_a_agents.run --passes p2,p3  # rejoue un sous-ensemble (recharge le Blackboard)

Écrit outputs/ontology.agentic.json + outputs/run_log.md (+ outputs/blackboard.json pour rejouer).
NE touche jamais outputs/ontology.json (l'oracle).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Système A — extracteur agentique")
    parser.add_argument("--passes", help="sous-ensemble, ex. p2,p3", default=None)
    parser.add_argument("--dry-run", action="store_true",
                        help="exécute P0 (déterministe) sans appeler les passes LLM")
    parser.add_argument("--max-budget", type=float, default=2.0,
                        help="plafond de coût DUR du run en USD (défaut 2.0). Le run s'arrête "
                             "proprement dès qu'il est atteint.")
    args = parser.parse_args()

    _load_env()
    passes = [p.strip() for p in args.passes.split(",")] if args.passes else None

    if not args.dry_run and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERREUR : ANTHROPIC_API_KEY manquante (.env). Utilise --dry-run pour tester "
              "la plomberie sans clé.", file=sys.stderr)
        return 2

    from .supervisor import run_pipeline
    return asyncio.run(run_pipeline(passes=passes, dry_run=args.dry_run,
                                    max_budget=args.max_budget))


if __name__ == "__main__":
    raise SystemExit(main())
