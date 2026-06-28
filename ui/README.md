# `ui/` — Serveur de démo (viz canvas du collègue + chat Système B)

Serveur Flask local qui sert **l'interface de démo de l'équipe viz** (graphe canvas animé +
chat intégré, exportée depuis Claude Design) et branche son chat sur le **vrai Système B**.
Quand B répond, la carte **surligne et zoome** sur les nœuds concernés (`node_ids`).

## Lancer

```bash
source .venv/bin/activate
python -m ui.app                 # → http://127.0.0.1:5000  (vrai Système B, ~35 s/question)
UI_MOCK=1 python -m ui.app       # → réponse SH-2049 mockée, instantanée (dev front)
```

## Routes

| Route | Rôle |
|---|---|
| `GET /` | la page du collègue (`templates/ontology-graph.dc.html`) |
| `GET /support.js`, `GET /graph_data.js` | les assets de la viz (chemins relatifs attendus par la page) |
| `POST /ask` | `{question}` → contrat `{answer, evidence, actions, node_ids, tool_trace}` |
| `GET /ask_stream?question=…` | SSE : events d'outils en direct puis contrat final (optionnel, front à brancher) |

## Architecture

- `app.py` — routes seulement, délègue à `backend.py`. **Inchangé** côté B.
- `backend.py` — **le seul pont vers B** (`system_b.agent.answer`), `UI_MOCK` + piège async gérés.
- `templates/ontology-graph.dc.html` — **la viz du collègue, intacte** sauf `runQuery` :
  l'appel `window.claude.complete(...)` a été remplacé par un `fetch('/ask')`. Le mapping
  `node_ids → highlightIds` alimente le surlignage + zoom (`applyResult`/`fitToIds`) déjà câblés.
- `static/graph_data.js`, `static/support.js` — assets du collègue, **inchangés**.

## graph_data.js — figé (décision actée)

On **ne régénère pas** `graph_data.js` : c'est un export Claude Design vérifié contre
l'ontologie courante (242 nœuds, ids `type:slug`, chaîne critique SH-2049 présente avec les
mêmes ids que B → le surlignage de la question phare marche). Limites assumées : SH-2049 sans
`delay_hours`/`battery_autonomy_h` dans le tooltip (B calcule côté serveur), et 2 ids clients
périphériques divergent par translittération d'accents (hors scénario).

## Garde-fous

- `system_b/` et `system_a*/` ne sont **pas** modifiés ; B est en **lecture seule**.
- L'UI **affiche** les actions proposées par B ; elle n'**exécute rien**.
- Le design et les animations du collègue sont préservés à l'identique.
