# CALIBRATION — aides données aux agents (transparence anti-triche)

Ce journal liste **tout** le guidage donné aux passes LLM, pour qu'on connaisse le niveau
d'autonomie réel et qu'on puisse le défendre au jury. Règle (CLAUDE §9 / prompt d'étage) :
le calibrage fort est autorisé ; lire l'oracle / `canonical` / le manifest ne l'est jamais.

## Garde-fous respectés (jamais franchis)
- Aucune passe n'importe ni ne lit `data/canonical.py`, `data/_scenario_manifest.json`,
  `outputs/ontology.json`. Interdiction répétée dans chaque system prompt (`models.py`).
- Les outils `readers.py` ne rendent que des octets lisibles (SQLite/Excel/PDF/.eml) + deux
  calculatrices pures (`name_similarity`, `sum_amounts`). Aucune sémantique servie.
- L'organigramme (P3) est confirmé via le **texte brut** des `.eml` (`eml_raw`), pas via le
  JSON pré-parsé du MCP email.
- Sortie neutre : aucun nœud `Risk`/`KeyDependency`, aucun `is_hot`, aucun flag de scénario
  (vérifié par P7).
- Le few-shot du format §4 utilise un exemple FICTIF neutre (`customer:acme`), jamais une
  entité réelle de la PME.

## Aides explicites fournies (calibrage autorisé)
1. **Conventions d'`id`** (`prompts/p2_entities.md`) : le schéma `type:slug` + un exemple par
   type. Nécessaire pour que les ids agentiques soient comparables à ceux de l'oracle.
2. **Mapping des champs sources → canonique** (`p2_entities.md`, `p3_relationships.md`) :
   repris de `DATA_README.md` (public). Ex. `payment_state=not_paid` → `Pending`.
3. **Catalogue des relations** (`p3_relationships.md`) : la liste des types d'arêtes attendus
   + leur evidence type + leur confidence indicative.
4. **Règle d'organigramme à 2 branches** (`p3_relationships.md`) : reprise mot pour mot de
   CLAUDE §6 / DATA_README §2bis (rangs de titre + branche chef→DG + branche intra-service +
   confidence ≤ 0.85 + open_question).
5. **Seuil de résolution floue** (~0.82, ou ≥0.93 sans confirmation) + méthode (comparer via
   `name_similarity`, confirmer par domaine email).
6. **Trous de source assumés** : `fulfilled_by` seulement pour SH-2049 (via PDF) ; un seul
   contrat documenté (`contract:ct-001`).
7. **Couches (`layer`) par type** : table fournie.

## Décisions d'ingénierie (pas du calibrage de contenu)
- **P2 / P3 découpées en sous-requêtes par groupe de sources.** Émettre ~200 entités / ~350
  relations en un seul appel est fragile (troncature, dérive JSON). On découpe par domaine
  (odoo-core, dashdoc, odoo-flux, annexe/docs, rh/finance). Chaque sous-requête reste une
  extraction agentique complète (appels d'outils + raisonnement). C'est de la robustesse, pas
  une fuite d'information.
- **P5 / P6 fonctionnent par ACTIONS, pas par re-sérialisation.** L'assemblage au format §4
  est fait mécaniquement (`_assemble.py`) ; Opus reçoit un PROFIL COMPACT et émet des actions
  correctives ciblées (drop/merge/set_layer/set_confidence). Cela garde le coût/temps d'un run
  raisonnable et évite qu'Opus réécrive 240 nœuds (source d'erreurs). Le raisonnement de
  cohérence reste celui d'Opus.
- **Retry x1 au superviseur** : une passe qui produit un JSON/contrat invalide est rejouée une
  fois (variance LLM). Simplification vs « message d'erreur réinjecté dans le prompt ».

## Journal d'itérations (score `compare_to_oracle.py`)
| Date | Run | Score global | chaîne | orga | CA | Ajustement appliqué |
|---|---|---|---|---|---|---|
| 2026-06-28 | run #1 (8 passes complètes) | **99.8 %** ✅ | 7/7 (100 %) | 14/14 (100 %) | 100 % | aucun — convergence dès le 1er run complet |

### Notes run #1
- Comptes par type : **21/21 exacts** (242 entités / 356 relations, comme l'oracle) ;
  couches identiques (operational 223 / hr 16 / financial 3).
- Ids : **240/242** (99.2 %). 2 divergences COSMÉTIQUES de slugification d'accents :
  oracle `customer:l-ger` / `customer:pichon-mend-s-sarl` (l'oracle remplace tout
  non-`[a-z0-9]` par `-`, donc `é`→`-`) vs agentique `customer:leger` /
  `customer:pichon-mendes-sarl` (l'agent « déburre » l'accent en lettre de base). L'entité,
  ses sources et sa résolution floue sont par ailleurs identiques. Non bloquant (chaîne,
  organigramme et CA exacts). Pour un 100 % d'ids littéral : resserrer la convention d'id de
  `p2_entities.md` (« ne pas déburrer : tout caractère hors `[a-z0-9]` → `-` »).
- Coût/temps : ~36 min, 103 appels d'outils MCP/readers, 1.18M tokens in / 186K out.
- Anti-triche vérifié (statique + runtime) : aucune lecture de `canonical`/manifest/oracle
  par le pipeline ; sortie neutre (aucun `is_hot`/`Risk`/`KeyDependency`/flag de scénario).
