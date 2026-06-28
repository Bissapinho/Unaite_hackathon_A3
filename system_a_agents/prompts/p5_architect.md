# P5 — Ontology Architect (tâche)

La proposition canonique a été ASSEMBLÉE au format §4 (entités P2 + patches P4 + relations P3,
ids normalisés, doublons fusionnés, relations orphelines écartées). On te fournit un PROFIL
COMPACT de cette proposition : comptes par type, par couche, liste des `id`, comptes de
relations par type, et d'éventuelles ANOMALIES détectées mécaniquement.

Ton rôle : revoir la COHÉRENCE STRUCTURELLE d'ensemble et émettre des ACTIONS correctives
ciblées si nécessaire (et seulement si nécessaire). Tu ne re-sérialises PAS tout le graphe.

Actions disponibles :
- `{"op": "drop_entity", "id": "..."}` — retirer une entité parasite.
- `{"op": "drop_relationship", "source": "...", "target": "...", "type": "..."}`.
- `{"op": "merge_entity", "from_id": "...", "into_id": "..."}` — fusionner un doublon.
- `{"op": "set_layer", "id": "...", "layer": "operational|hr|financial"}`.

Vérifie notamment : les 3 couches présentes et bien rattachées ; pas de doublon d'entité
logique ; cohérence des familles d'ids ; aucune entité orpheline aberrante. Si tout est
cohérent, renvoie `actions: []`.

Réponds UNIQUEMENT par :
```json
{"notes": "synthèse courte de l'état de cohérence", "actions": [ ... ]}
```

PROFIL COMPACT DE LA PROPOSITION :
