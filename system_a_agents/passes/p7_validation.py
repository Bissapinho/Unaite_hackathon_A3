"""P7 — Validation light (DÉTERMINISTE, NO LLM).

Vérifie empiriquement la proposition `ontology_draft` SANS jamais lire canonical ni
l'oracle. Checks (CLAUDE §9, prompt d'étage) :
  - chaque entité/relation porte sources + evidence non vides, confidence ∈ ]0,1] ;
  - chaque `reports_to` a confidence ≤ 0.85 + au moins une open_question ;
  - aucune relation vers un nœud absent ;
  - aucun doublon (source, target, type) ;
  - les 3 layers (operational, hr, financial) sont présents ;
  - aucune fuite anti-triche (is_hot / Risk / flag de scénario).

Échec = log clair ; le superviseur sort en code non-zéro.
"""

from __future__ import annotations

from ..blackboard import Blackboard
from ..logging_ui import RunLogger

_FORBIDDEN_TYPES = {"Risk", "KeyDependency"}
_FORBIDDEN_ATTR_SUBSTR = ("is_hot", "_scenario", "scenario_flag")


def run(bb: Blackboard, logger: RunLogger) -> bool:
    logger.banner("p7", "Validation light (déterministe)")
    draft = bb.ontology_draft or {}
    entities = draft.get("entities", [])
    relationships = draft.get("relationships", [])
    errors: list[str] = []
    warns: list[str] = []

    ids = {e.get("id") for e in entities}

    # entités
    layers_seen = set()
    for e in entities:
        eid = e.get("id", "<sans id>")
        layers_seen.add(e.get("layer"))
        if not e.get("sources"):
            errors.append(f"entité {eid} sans sources")
        if not e.get("evidence"):
            errors.append(f"entité {eid} sans evidence")
        c = e.get("confidence")
        if not (isinstance(c, (int, float)) and 0.0 < c <= 1.0):
            errors.append(f"entité {eid} confidence invalide ({c})")
        if e.get("type") in _FORBIDDEN_TYPES:
            errors.append(f"entité {eid} type interdit (anti-triche) : {e.get('type')}")
        attr_blob = str(e.get("attributes", {})).lower()
        for bad in _FORBIDDEN_ATTR_SUBSTR:
            if bad in attr_blob:
                errors.append(f"entité {eid} attribut interdit (anti-triche) : {bad}")

    for layer in ("operational", "hr", "financial"):
        if layer not in layers_seen:
            errors.append(f"layer manquant : {layer}")

    # relations
    seen: set = set()
    for r in relationships:
        s, t, ty = r.get("source"), r.get("target"), r.get("type")
        tag = f"{ty}({s}->{t})"
        if s not in ids:
            errors.append(f"relation {tag} : source absente du graphe")
        if t not in ids:
            errors.append(f"relation {tag} : target absente du graphe")
        key = (s, t, ty)
        if key in seen:
            errors.append(f"relation en doublon : {tag}")
        seen.add(key)
        if not r.get("evidence"):
            errors.append(f"relation {tag} sans evidence")
        c = r.get("confidence")
        if not (isinstance(c, (int, float)) and 0.0 < c <= 1.0):
            errors.append(f"relation {tag} confidence invalide ({c})")
        if ty == "reports_to":
            if c is not None and c > 0.85:
                errors.append(f"reports_to {tag} confidence > 0.85 ({c}) — lien inféré")
            if not r.get("open_questions"):
                warns.append(f"reports_to {tag} sans open_question")

    ok = not errors
    bb.validation = {"ok": ok, "errors": errors, "warnings": warns,
                     "n_entities": len(entities), "n_relationships": len(relationships)}
    for w in warns[:20]:
        logger.warn(w)
    if ok:
        logger.summary(f"validation OK — {len(entities)} entités, "
                       f"{len(relationships)} relations, 3 layers présents")
    else:
        for e in errors[:30]:
            logger.error(e)
        logger.error(f"VALIDATION ÉCHOUÉE : {len(errors)} erreurs")
    bb.log("p7", "validation", f"ok={ok} errors={len(errors)} warnings={len(warns)}")
    return ok
