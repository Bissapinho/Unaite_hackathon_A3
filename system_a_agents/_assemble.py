"""_assemble.py — assemblage déterministe de la proposition (support de P5 Architect).

Compile les entités (P2), les patches d'attributs (P4) et les relations (P3) en une
proposition propre au format §4 : fusion des entités de même `id`, application des patches,
des ACTIONS correctives (architecte P5 / critic P6), suppression des relations orphelines et
des doublons. Pure mécanique — aucune sémantique métier, aucun accès oracle/canonical.
"""

from __future__ import annotations

from typing import Any


def merge_entities(entities: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for e in entities:
        eid = e.get("id")
        if not eid:
            continue
        if eid not in out:
            out[eid] = {
                "id": eid, "type": e.get("type"), "name": e.get("name"),
                "layer": e.get("layer"),
                "attributes": dict(e.get("attributes") or {}),
                "sources": list(e.get("sources") or []),
                "confidence": e.get("confidence", 0.9),
                "evidence": list(e.get("evidence") or []),
                "open_questions": list(e.get("open_questions") or []),
            }
        else:
            cur = out[eid]
            for s in e.get("sources") or []:
                if s not in cur["sources"]:
                    cur["sources"].append(s)
            for ev in e.get("evidence") or []:
                if ev not in cur["evidence"]:
                    cur["evidence"].append(ev)
            for q in e.get("open_questions") or []:
                if q not in cur["open_questions"]:
                    cur["open_questions"].append(q)
            cur["confidence"] = max(cur["confidence"], e.get("confidence", 0))
            for k, v in (e.get("attributes") or {}).items():
                if v is not None:
                    cur["attributes"].setdefault(k, v)
    return out


def apply_patches(emap: dict[str, dict], patches: list[dict]) -> None:
    for p in patches or []:
        eid = p.get("id")
        if eid in emap:
            for k, v in (p.get("attributes") or {}).items():
                if v is not None:
                    emap[eid]["attributes"][k] = v
            if p.get("layer"):
                emap[eid]["layer"] = p["layer"]


def apply_actions(emap: dict[str, dict], rels: list[dict], actions: list[dict]) -> None:
    """Applique les ops correctives de l'architecte (P5) et du critic (P6)."""
    for a in actions or []:
        op = a.get("op")
        if op == "drop_entity":
            emap.pop(a.get("id"), None)
        elif op == "set_layer" and a.get("id") in emap:
            emap[a["id"]]["layer"] = a.get("layer")
        elif op == "merge_entity":
            frm, into = a.get("from_id"), a.get("into_id")
            if frm in emap and into in emap:
                src, dst = emap.pop(frm), emap[into]
                for s in src["sources"]:
                    if s not in dst["sources"]:
                        dst["sources"].append(s)
                for ev in src["evidence"]:
                    if ev not in dst["evidence"]:
                        dst["evidence"].append(ev)
                for r in rels:
                    if r.get("source") == frm:
                        r["source"] = into
                    if r.get("target") == frm:
                        r["target"] = into
        elif op == "drop_relationship":
            s, t, ty = a.get("source"), a.get("target"), a.get("type")
            rels[:] = [r for r in rels
                       if not (r.get("source") == s and r.get("target") == t
                               and r.get("type") == ty)]
        elif op == "set_confidence" and a.get("scope") == "relationship":
            for r in rels:
                if (r.get("source") == a.get("source") and r.get("target") == a.get("target")
                        and r.get("type") == a.get("type")):
                    r["confidence"] = a.get("value")


def finalize(emap: dict[str, dict], rels: list[dict]) -> dict[str, Any]:
    """Retire les relations orphelines + doublons ; renvoie {entities, relationships}."""
    ids = set(emap)
    seen: set = set()
    clean_rels: list[dict] = []
    for r in rels:
        s, t, ty = r.get("source"), r.get("target"), r.get("type")
        if s not in ids or t not in ids:
            continue
        key = (s, t, ty)
        if key in seen:
            continue
        seen.add(key)
        clean = {
            "source": s, "target": t, "type": ty,
            "confidence": r.get("confidence", 0.9),
            "evidence": list(r.get("evidence") or []),
            "open_questions": list(r.get("open_questions") or []),
        }
        if r.get("attributes"):
            clean["attributes"] = r["attributes"]
        clean_rels.append(clean)
    return {"entities": list(emap.values()), "relationships": clean_rels}


def assemble(entities: list[dict], relationships: list[dict], patches: list[dict],
             actions: list[dict] | None = None) -> dict[str, Any]:
    emap = merge_entities(entities)
    apply_patches(emap, patches)
    rels = [dict(r) for r in relationships]
    if actions:
        apply_actions(emap, rels, actions)
    return finalize(emap, rels)


def compact_profile(draft: dict) -> dict:
    """Profil compact (pour P5/P6) : comptes + ids + anomalies mécaniques."""
    from collections import Counter

    entities = draft.get("entities", [])
    rels = draft.get("relationships", [])
    by_type = Counter(e.get("type") for e in entities)
    by_layer = Counter(e.get("layer") for e in entities)
    rel_types = Counter(r.get("type") for r in rels)
    ids = [e.get("id") for e in entities]
    id_set = set(ids)

    anomalies: list[str] = []
    # doublons d'id
    dup = [i for i, c in Counter(ids).items() if c > 1]
    if dup:
        anomalies.append(f"ids dupliqués: {dup}")
    # relations orphelines
    dangling = [f"{r.get('type')}({r.get('source')}->{r.get('target')})"
                for r in rels if r.get("source") not in id_set or r.get("target") not in id_set]
    if dangling:
        anomalies.append(f"relations orphelines ({len(dangling)}): {dangling[:10]}")
    # provenance manquante
    no_prov = [e.get("id") for e in entities if not e.get("sources") or not e.get("evidence")]
    if no_prov:
        anomalies.append(f"entités sans provenance: {no_prov[:10]}")
    # reports_to trop confiant
    bad_rt = [f"{r.get('source')}->{r.get('target')}" for r in rels
              if r.get("type") == "reports_to" and (r.get("confidence") or 0) > 0.85]
    if bad_rt:
        anomalies.append(f"reports_to confidence>0.85: {bad_rt}")
    # layers manquants
    for layer in ("operational", "hr", "financial"):
        if layer not in by_layer:
            anomalies.append(f"layer manquant: {layer}")

    return {
        "n_entities": len(entities), "n_relationships": len(rels),
        "by_type": dict(by_type), "by_layer": dict(by_layer),
        "rel_types": dict(rel_types),
        "ids": sorted(ids),
        "anomalies": anomalies,
    }
