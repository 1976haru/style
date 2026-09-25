from __future__ import annotations

import re
from collections import Counter, defaultdict
from copy import deepcopy
from typing import Any, Dict, Iterable, List


DEFAULT_MIN_SAMPLES = 30
DEFAULT_MIN_GROUP = 3


def _score(record: Dict[str, Any]) -> float:
    """Mirror v0.4 feedback policy without mutating stored feedback."""
    def rating(name: str) -> float:
        try:
            value = float(record.get(name, 3))
        except (TypeError, ValueError):
            value = 3.0
        return max(1.0, min(5.0, value))

    weighted = (
        0.30 * rating("overall")
        + 0.22 * rating("vocal_identity")
        + 0.16 * rating("hook")
        + 0.16 * rating("groove")
        + 0.16 * rating("prompt_adherence")
    ) / 5.0 * 100.0
    decision = str(record.get("decision") or "MAYBE").upper()
    bonus = 12.0 if decision == "KEEP" else (-20.0 if decision == "REGEN" else 0.0)
    return max(0.0, min(100.0, weighted + bonus))


def _group_summary(records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows = list(records)
    n = len(rows)
    if not n:
        return {"n": 0, "keepRate": 0.0, "regenRate": 0.0, "avgScore": 0.0}
    keeps = sum(1 for r in rows if str(r.get("decision") or "").upper() == "KEEP")
    regens = sum(1 for r in rows if str(r.get("decision") or "").upper() == "REGEN")
    return {
        "n": n,
        "keepRate": round(keeps / n, 3),
        "regenRate": round(regens / n, 3),
        "avgScore": round(sum(_score(r) for r in rows) / n, 1),
    }


def _evidence_rank(summary: Dict[str, Any]) -> float:
    n = int(summary.get("n", 0) or 0)
    avg = float(summary.get("avgScore", 0) or 0)
    keep = float(summary.get("keepRate", 0) or 0)
    reliability = min(1.0, n / 10.0)
    return (0.70 * avg + 30.0 * keep) * reliability


def _signature_atoms(text: str) -> List[str]:
    atoms = []
    for part in re.split(r"[;,|/]+", str(text or "")):
        atom = re.sub(r"\s+", " ", part).strip().casefold()
        if len(atom) >= 4:
            atoms.append(atom)
    return atoms


def _bpm_bucket(value: Any, width: int = 4) -> str:
    try:
        bpm = int(value)
    except (TypeError, ValueError):
        return ""
    if bpm <= 0:
        return ""
    low = (bpm // width) * width
    high = low + width - 1
    return f"{low}-{high}"


def _rank_groups(groups: Dict[str, List[Dict[str, Any]]], min_group: int) -> List[Dict[str, Any]]:
    ranked: List[Dict[str, Any]] = []
    for key, rows in groups.items():
        summary = _group_summary(rows)
        if summary["n"] < min_group:
            continue
        ranked.append({"key": key, **summary, "evidenceRank": round(_evidence_rank(summary), 1)})
    ranked.sort(key=lambda x: (x["evidenceRank"], x["n"], x["keepRate"]), reverse=True)
    return ranked


def analyze_feedback_patterns(
    records: Iterable[Dict[str, Any]],
    min_samples: int = DEFAULT_MIN_SAMPLES,
    min_group: int = DEFAULT_MIN_GROUP,
) -> Dict[str, Any]:
    """Analyze local Suno feedback conservatively.

    This function never edits masters or Track Plan locks. Before min_samples,
    it reports observations only and keeps active=False.
    """
    rows = [dict(r) for r in records if isinstance(r, dict)]
    overall = _group_summary(rows)
    issue_counts: Counter[str] = Counter()
    by_bpm: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_genre: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_role: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_atom: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for row in rows:
        issue_counts.update(row.get("issue_tags") or [])
        bucket = _bpm_bucket(row.get("bpm"))
        if bucket:
            by_bpm[bucket].append(row)
        genre = re.sub(r"\s+", " ", str(row.get("genre") or "")).strip()
        if genre:
            by_genre[genre].append(row)
        role = str(row.get("music_role") or "Core").strip() or "Core"
        by_role[role].append(row)
        for atom in set(_signature_atoms(str(row.get("performance_signature") or ""))):
            by_atom[atom].append(row)

    n = len(rows)
    active = n >= int(min_samples)
    confidence = "insufficient"
    if active:
        confidence = "high" if n >= 120 else ("medium" if n >= 60 else "early")

    bpm_ranked = _rank_groups(by_bpm, min_group)
    genre_ranked = _rank_groups(by_genre, min_group)
    role_ranked = _rank_groups(by_role, min_group)
    atom_ranked = _rank_groups(by_atom, min_group)

    return {
        "active": active,
        "n": n,
        "minSamples": int(min_samples),
        "minGroup": int(min_group),
        "confidence": confidence,
        "overall": overall,
        "topBpmWindows": bpm_ranked[:5],
        "topGenres": genre_ranked[:5],
        "topRoles": role_ranked[:5],
        "topPerformanceAtoms": atom_ranked[:8],
        "topIssues": dict(issue_counts.most_common(10)),
        "policy": {
            "storyLocksMutable": False,
            "autoMasterRewrite": False,
            "mode": "soft-evidence-only",
        },
    }


def _spread_indices(total: int, count: int) -> List[int]:
    if total <= 0 or count <= 0:
        return []
    count = min(total, count)
    chosen: List[int] = []
    for i in range(count):
        idx = round((i + 1) * (total + 1) / (count + 1)) - 1
        idx = max(0, min(total - 1, idx))
        while idx in chosen and idx + 1 < total:
            idx += 1
        while idx in chosen and idx - 1 >= 0:
            idx -= 1
        if idx not in chosen:
            chosen.append(idx)
    return sorted(chosen)


def build_ab_experiment_plan(
    track_plan: List[Dict[str, Any]],
    analysis: Dict[str, Any],
    exploration_count: int = 4,
) -> List[Dict[str, Any]]:
    """Attach deterministic A/B experiment metadata without changing locked content.

    If analysis is inactive, every track remains baseline arm A. When active,
    selected B tracks receive proposedChanges only; recomputed music remains
    untouched until a later explicit apply step.
    """
    planned = deepcopy(track_plan)
    for row in planned:
        row["experiment"] = {
            "arm": "A",
            "axis": "baseline",
            "proposedChanges": {},
            "reason": "Current recomputed music policy baseline.",
        }

    if not analysis.get("active") or not planned:
        return planned

    indexes = _spread_indices(len(planned), int(exploration_count))
    axes = ("bpm", "performanceSignature", "genre", "structure")

    top_bpm = (analysis.get("topBpmWindows") or [{}])[0].get("key")
    top_genre = (analysis.get("topGenres") or [{}])[0].get("key")
    top_atom = (analysis.get("topPerformanceAtoms") or [{}])[0].get("key")
    issues = analysis.get("topIssues") or {}

    for pos, idx in enumerate(indexes):
        row = planned[idx]
        axis = axes[pos % len(axes)]
        proposed: Dict[str, Any] = {}
        reason = "Empirical B-arm probe; locked story fields remain unchanged."

        if axis == "bpm" and top_bpm:
            low, high = [int(x) for x in str(top_bpm).split("-", 1)]
            proposed["targetBpmWindow"] = [low, high]
            proposed["rule"] = "Clamp to current master role BPM range before applying."
        elif axis == "genre" and top_genre:
            proposed["genreCandidate"] = top_genre
            proposed["rule"] = "Use as secondary family only if current master permits it."
        elif axis == "performanceSignature" and top_atom:
            proposed["performanceSignatureEmphasis"] = top_atom
            proposed["rule"] = "Add emphasis; do not replace fixed channel voice fingerprint."
        elif axis == "structure":
            guards = []
            if int(issues.get("bridge_weak", 0) or 0) > 0:
                guards.append("strengthen Bridge contrast")
            if int(issues.get("final_weak", 0) or 0) > 0:
                guards.append("strengthen Final payoff")
            if int(issues.get("early_ending", 0) or 0) > 0:
                guards.append("add anti-early-ending duration guard")
            proposed["structureEmphasis"] = guards or ["test one stronger Bridge→Final contrast axis"]

        row["experiment"] = {
            "arm": "B",
            "axis": axis,
            "proposedChanges": proposed,
            "reason": reason,
        }

    return planned


def validate_lock_preservation(
    original: List[Dict[str, Any]],
    planned: List[Dict[str, Any]],
) -> List[str]:
    """Return human-readable lock violations. Empty list means preserved."""
    issues: List[str] = []
    if len(original) != len(planned):
        issues.append(f"track count changed: {len(original)} -> {len(planned)}")
        return issues
    for i, (before, after) in enumerate(zip(original, planned), 1):
        if before.get("trusted") != after.get("trusted"):
            issues.append(f"track {i}: trusted Story/Scene/Title/Hook block changed")
    return issues


def select_feedback_scope(
    records: Iterable[Dict[str, Any]],
    preset_id: str = "",
    market_recipe_id: str = "",
) -> Dict[str, Any]:
    """Return only records belonging to the active production context.

    v0.5 deliberately does not pool unrelated channel/recipe feedback to reach
    the activation threshold. This prevents cross-channel contamination.
    """
    rows = [dict(r) for r in records if isinstance(r, dict)]
    selected = rows
    labels: List[str] = []
    if preset_id:
        selected = [r for r in selected if str(r.get("preset_id") or "") == preset_id]
        labels.append(f"preset={preset_id}")
    if market_recipe_id:
        selected = [r for r in selected if str(r.get("market_recipe_id") or "") == market_recipe_id]
        labels.append(f"recipe={market_recipe_id}")
    return {
        "scope": " + ".join(labels) if labels else "all-feedback",
        "presetId": preset_id,
        "marketRecipeId": market_recipe_id,
        "records": selected,
        "n": len(selected),
        "totalAvailable": len(rows),
    }


def build_experiment_manifest(
    track_plan: List[Dict[str, Any]],
    analysis: Dict[str, Any],
    context: Dict[str, Any] | None = None,
    exploration_count: int = 4,
) -> Dict[str, Any]:
    """Build a portable, proposal-only A/B manifest.

    The manifest never mutates or replaces recomputed music values. It records
    suggested experiment axes separately so generation can remain baseline
    until an explicit apply workflow is introduced and reviewed.
    """
    planned = build_ab_experiment_plan(track_plan, analysis, exploration_count)
    lock_issues = validate_lock_preservation(track_plan, planned)
    rows = []
    for row in planned:
        exp = row.get("experiment") or {}
        trusted = row.get("trusted") or {}
        rows.append({
            "trackNo": row.get("trackNo"),
            "title": trusted.get("title", ""),
            "arm": exp.get("arm", "A"),
            "axis": exp.get("axis", "baseline"),
            "proposedChanges": exp.get("proposedChanges") or {},
            "reason": exp.get("reason", ""),
        })
    return {
        "schemaVersion": 1,
        "mode": "PROPOSAL_ONLY",
        "context": dict(context or {}),
        "learning": {
            "active": bool(analysis.get("active")),
            "n": int(analysis.get("n", 0) or 0),
            "minSamples": int(analysis.get("minSamples", DEFAULT_MIN_SAMPLES) or DEFAULT_MIN_SAMPLES),
            "confidence": analysis.get("confidence", "insufficient"),
            "topBpmWindows": analysis.get("topBpmWindows", []),
            "topGenres": analysis.get("topGenres", []),
            "topPerformanceAtoms": analysis.get("topPerformanceAtoms", []),
            "topIssues": analysis.get("topIssues", {}),
        },
        "summary": {
            "tracks": len(rows),
            "armA": sum(1 for r in rows if r["arm"] == "A"),
            "armB": sum(1 for r in rows if r["arm"] == "B"),
            "lockViolations": len(lock_issues),
        },
        "lockViolations": lock_issues,
        "tracks": rows,
    }


def analyze_ab_results(
    records: Iterable[Dict[str, Any]],
    min_per_arm: int = 5,
    min_per_axis: int = 3,
) -> Dict[str, Any]:
    """Summarize observed A/B outcomes without declaring a winner.

    This is descriptive only. It does not rewrite masters, Track Plans, or
    recipes. A/B is considered analyzable only when both arms have enough
    observations.
    """
    rows = [dict(r) for r in records if isinstance(r, dict)]
    a_rows = [r for r in rows if str(r.get("experiment_arm") or "").upper() == "A"]
    b_rows = [r for r in rows if str(r.get("experiment_arm") or "").upper() == "B"]
    a = _group_summary(a_rows)
    b = _group_summary(b_rows)
    active = a["n"] >= int(min_per_arm) and b["n"] >= int(min_per_arm)
    baseline_score = float(a.get("avgScore", 0) or 0)
    baseline_keep = float(a.get("keepRate", 0) or 0)

    by_axis: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in b_rows:
        axis = str(row.get("experiment_axis") or "").strip()
        if axis and axis != "baseline":
            by_axis[axis].append(row)

    axis_rows = []
    for axis, group in by_axis.items():
        summary = _group_summary(group)
        if summary["n"] < int(min_per_axis):
            continue
        score_delta = round(float(summary["avgScore"]) - baseline_score, 1)
        keep_delta = round(float(summary["keepRate"]) - baseline_keep, 3)
        if not active:
            signal = "insufficient"
        elif score_delta >= 5 and keep_delta >= 0:
            signal = "positive_early"
        elif score_delta <= -5 and keep_delta <= 0:
            signal = "negative_early"
        else:
            signal = "mixed_or_unclear"
        axis_rows.append({
            "axis": axis,
            **summary,
            "scoreDeltaVsA": score_delta,
            "keepRateDeltaVsA": keep_delta,
            "signal": signal,
        })
    axis_rows.sort(key=lambda x: (x["scoreDeltaVsA"], x["keepRateDeltaVsA"], x["n"]), reverse=True)

    return {
        "active": active,
        "descriptiveSignalOnly": True,
        "minPerArm": int(min_per_arm),
        "minPerAxis": int(min_per_axis),
        "armA": a,
        "armB": b,
        "scoreDeltaBvsA": round(float(b.get("avgScore", 0) or 0) - baseline_score, 1) if b["n"] else None,
        "keepRateDeltaBvsA": round(float(b.get("keepRate", 0) or 0) - baseline_keep, 3) if b["n"] else None,
        "byAxis": axis_rows,
        "policy": {
            "declareWinner": False,
            "autoApply": False,
            "autoMasterRewrite": False,
        },
    }


def analyze_research_abc_results(
    records: Iterable[Dict[str, Any]],
    min_per_variant: int = 5,
    min_per_axis: int = 3,
) -> Dict[str, Any]:
    """Describe v0.6 A_CONTROL/B_GROOVE/C_CHARACTER outcomes conservatively.

    This function does not choose a winner, auto-apply a candidate, or rewrite
    any master. It only reports observed local feedback once each variant has
    enough evidence for a fair three-way comparison.
    """
    rows = [dict(r) for r in records if isinstance(r, dict)]
    aliases = {
        "A": "A_CONTROL",
        "B": "B_GROOVE",
        "C": "C_CHARACTER",
        "A_CONTROL": "A_CONTROL",
        "B_GROOVE": "B_GROOVE",
        "C_CHARACTER": "C_CHARACTER",
    }
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        raw = str(row.get("experiment_arm") or "").strip().upper()
        variant = aliases.get(raw)
        if variant:
            grouped[variant].append(row)

    summaries = {
        variant: _group_summary(grouped.get(variant, []))
        for variant in ("A_CONTROL", "B_GROOVE", "C_CHARACTER")
    }
    active = all(
        int(summaries[variant]["n"]) >= int(min_per_variant)
        for variant in ("A_CONTROL", "B_GROOVE", "C_CHARACTER")
    )
    baseline = summaries["A_CONTROL"]

    variants = []
    for variant in ("A_CONTROL", "B_GROOVE", "C_CHARACTER"):
        summary = summaries[variant]
        score_delta = round(float(summary["avgScore"]) - float(baseline["avgScore"]), 1) if summary["n"] else None
        keep_delta = round(float(summary["keepRate"]) - float(baseline["keepRate"]), 3) if summary["n"] else None
        variants.append({
            "variant": variant,
            **summary,
            "scoreDeltaVsControl": 0.0 if variant == "A_CONTROL" and summary["n"] else score_delta,
            "keepRateDeltaVsControl": 0.0 if variant == "A_CONTROL" and summary["n"] else keep_delta,
        })

    by_axis: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        axis = str(row.get("experiment_axis") or "").strip()
        if axis and axis != "control_baseline":
            by_axis[axis].append(row)

    axis_rows = []
    for axis, group in by_axis.items():
        summary = _group_summary(group)
        if summary["n"] < int(min_per_axis):
            continue
        axis_rows.append({
            "axis": axis,
            **summary,
            "scoreDeltaVsControl": round(float(summary["avgScore"]) - float(baseline["avgScore"]), 1)
            if baseline["n"] else None,
            "keepRateDeltaVsControl": round(float(summary["keepRate"]) - float(baseline["keepRate"]), 3)
            if baseline["n"] else None,
        })
    axis_rows.sort(key=lambda x: (x["n"], x["avgScore"]), reverse=True)

    return {
        "active": active,
        "descriptiveSignalOnly": True,
        "minPerVariant": int(min_per_variant),
        "minPerAxis": int(min_per_axis),
        "variants": variants,
        "byAxis": axis_rows,
        "policy": {
            "declareWinner": False,
            "autoApply": False,
            "autoMasterRewrite": False,
            "requiresAudioFeedback": True,
        },
    }
