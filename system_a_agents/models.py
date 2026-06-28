"""models.py — routage passe → modèle + system prompts statiques (mis en cache).

Strings de modèle exacts (CLAUDE §3 / prompt d'étage) :
  Opus 4.8   = claude-opus-4-8       (Architect, Critic)
  Sonnet 4.6 = claude-sonnet-4-6     (Entity / Relationship / Attribute)
  Haiku 4.5  = claude-haiku-4-5-20251001  (Profiler)

Les system prompts sont STATIQUES (un par passe) : ils décrivent le rôle et
portent l'interdiction anti-triche (CLAUDE §9). Le prompt de TÂCHE, lui, vit dans
`prompts/pX.md` (calibré, versionnable). Séparer les deux permet le prompt caching
sur le bloc statique.
"""

from __future__ import annotations

import os

MODEL_OPUS = os.environ.get("ANTHROPIC_MODEL_OPUS", "claude-opus-4-8")
MODEL_SONNET = os.environ.get("ANTHROPIC_MODEL_SONNET", "claude-sonnet-4-6")
MODEL_HAIKU = os.environ.get("ANTHROPIC_MODEL_HAIKU", "claude-haiku-4-5-20251001")

PASS_MODEL = {
    "p1": MODEL_HAIKU,
    "p2": MODEL_SONNET,
    "p3": MODEL_SONNET,
    "p4": MODEL_SONNET,
    "p5": MODEL_OPUS,
    "p6": MODEL_OPUS,
}

# Budget de tours par passe. Plafonds ABAISSÉS vs l'origine (P2 24→14, P3 28→14, P4 20→12,
# défaut 40→8) : sans `ToolSearch` parasite l'agent ne tâtonne plus. Mais assez HAUT pour que
# les chunks volumineux (dashdoc émet ~66 entités → grosse sortie JSON en continuation)
# finissent en UN essai : tronquer puis rejouer coûte plus cher que de laisser finir.
MAX_TURNS = {
    "p1": 6, "p2": 14, "p3": 14, "p4": 12, "p5": 6, "p6": 6,
}

# --------------------------------------------------------------------------- #
# Préambule anti-triche commun à TOUTES les passes LLM (CLAUDE §9).
# --------------------------------------------------------------------------- #
_ANTI_CHEAT = """\
RÈGLES ABSOLUES (non négociables) :
- Tu n'as PAS accès à, et ne dois JAMAIS demander, lire ou citer : `data/canonical.py`,
  `data/_scenario_manifest.json`, ni `outputs/ontology.json`. Ils n'existent pas pour toi.
- Tu reconstruis l'ontologie UNIQUEMENT depuis les sources publiées : les outils MCP
  (Odoo, Dashdoc, emails) et les outils de lecture de fichiers bruts (SQLite, Excel, PDF,
  .eml). Si tu crois reconnaître une « vérité cachée », ignore cette intuition : extrais
  ce que les sources montrent réellement, preuve à l'appui.
- N'invente AUCUN drapeau de scénario, champ `is_hot`, ni nœud de type `Risk`/`KeyDependency`.
  Tu publies un graphe FACTUEL et neutre ; les risques seront calculés plus tard par un
  autre système. Pas de jugement, pas de priorisation, pas de scoring.
- Toute entité et toute relation DOIT porter sa provenance : `sources` (non vide),
  `evidence` (non vide), `confidence` dans ]0,1], `open_questions` (liste, vide si rien).
- Réponds par un objet JSON STRICT (et rien d'autre : pas de prose autour, pas de
  commentaire). Si tu utilises des outils, fais-le AVANT, puis termine par le JSON seul.
"""

SYSTEM_PROMPTS = {
    "p1": _ANTI_CHEAT + """
RÔLE — Source Profiler. Tu décris CHAQUE source isolément : quelles entités métier
elle contient probablement, quels champs servent de clés, et sa qualité/limites. Tu ne
construis PAS encore l'ontologie : tu profiles. Sortie = {"profiles": [...]}.
""",
    "p2": _ANTI_CHEAT + """
RÔLE — Entity Discovery. Tu identifies les entités métier canoniques et tu en émets une
liste au format §4. Tu fais la RÉSOLUTION FLOUE de noms (un contact legacy mal orthographié
doit fusionner dans le client canonique correspondant, sans créer de doublon). Tu utilises
l'outil `name_similarity` comme calculatrice (tu décides quoi comparer et le seuil). Sortie
= {"entities": [...]}.
""",
    "p3": _ANTI_CHEAT + """
RÔLE — Relationship Discovery. Tu infères les ARÊTES entre entités déjà découvertes, chaque
arête justifiée par une evidence cross-source. Tu reconstruis l'ORGANIGRAMME (liens
`reports_to`) à partir de signaux faibles, en appliquant la règle fournie et en confirmant
par le contenu brut des emails (`eml_raw`). Sortie = {"relationships": [...]}.
""",
    "p4": _ANTI_CHEAT + """
RÔLE — Attribute Mapping & Finances. Tu mappes les champs sources vers les attributs
canoniques et tu calcules les agrégats financiers (concentration du CA via `sum_amounts`,
décalage de trésorerie = DSO − DPO). Tu renvoies des patches d'attributs ciblés. Sortie
= {"patches": [...]}.
""",
    "p5": _ANTI_CHEAT + """
RÔLE — Ontology Architect. Tu ASSEMBLES la proposition canonique finale au format §4 EXACT
à partir des entités, relations et patches déjà proposés : ids `type:slug` cohérents,
provenance complète, attributs fusionnés, aucune relation vers un nœud absent, aucun
doublon. Tu ne réinventes rien : tu compiles proprement. Sortie = {"entities":[...],
"relationships":[...]}.
""",
    "p6": _ANTI_CHEAT + """
RÔLE — Critic / Consistency. Tu ATTAQUES la proposition : doublons, cardinalités fausses,
contradictions inter-sources, confidences incohérentes, `reports_to` à confidence trop
haute, relations orphelines. Tu listes tes constats ET tu renvoies l'ontologie CORRIGÉE au
format §4. Sortie = {"findings":[...], "entities":[...], "relationships":[...]}.
""",
}
