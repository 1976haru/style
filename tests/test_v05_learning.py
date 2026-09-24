import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.learning import (
    analyze_feedback_patterns, build_ab_experiment_plan, validate_lock_preservation,
    select_feedback_scope, build_experiment_manifest,
)


def _record(i, *, keep=True, bpm=98, genre="Chill Rap", signature="dry pickup; micro-rest", issue=None):
    return {
        "id": i,
        "decision": "KEEP" if keep else "REGEN",
        "overall": 5 if keep else 2,
        "vocal_identity": 5 if keep else 2,
        "hook": 4 if keep else 2,
        "groove": 5 if keep else 2,
        "prompt_adherence": 5 if keep else 2,
        "bpm": bpm,
        "genre": genre,
        "music_role": "Core",
        "performance_signature": signature,
        "issue_tags": [issue] if issue else [],
    }


def _plan():
    rows = []
    for i in range(1, 16):
        rows.append({
            "trackNo": i,
            "trusted": {
                "title": f"T{i}",
                "hookPhrase": f"H{i}",
                "storyAct": f"Act {(i - 1) // 3 + 1}",
                "listenerSituation": f"Scene {i}",
            },
            "recomputed": {
                "BPM": 96 + (i % 3),
                "genre": "Chill Rap",
                "vocal": "fixed channel voice",
                "musicRole": "Core",
                "structure": "Verse → Chorus → Bridge → Final",
                "performanceSignature": "dry pickup; micro-rest",
            },
        })
    return rows


def test_learning_inactive_before_30_samples():
    analysis = analyze_feedback_patterns([_record(i) for i in range(12)])
    assert analysis["active"] is False
    assert analysis["confidence"] == "insufficient"
    assert analysis["policy"]["storyLocksMutable"] is False


def test_learning_activates_and_ranks_repeated_patterns():
    rows = []
    for i in range(24):
        rows.append(_record(i, keep=True, bpm=98, genre="Chill Rap", signature="dry pickup; micro-rest"))
    for i in range(24, 30):
        rows.append(_record(i, keep=False, bpm=86, genre="Slow R&B", signature="airy legato", issue="too_rnb"))
    analysis = analyze_feedback_patterns(rows)
    assert analysis["active"] is True
    assert analysis["n"] == 30
    assert analysis["topBpmWindows"][0]["key"] == "96-99"
    assert analysis["topGenres"][0]["key"] == "Chill Rap"
    assert analysis["topPerformanceAtoms"][0]["key"] in {"dry pickup", "micro-rest"}
    assert analysis["topIssues"]["too_rnb"] == 6


def test_ab_plan_preserves_locks_and_only_adds_proposals():
    original = _plan()
    analysis = analyze_feedback_patterns([_record(i) for i in range(30)])
    planned = build_ab_experiment_plan(original, analysis, exploration_count=4)
    assert validate_lock_preservation(original, planned) == []
    assert [x["recomputed"] for x in planned] == [x["recomputed"] for x in original]
    assert sum(1 for x in planned if x["experiment"]["arm"] == "B") == 4
    assert all("experiment" in x for x in planned)


def test_inactive_analysis_keeps_all_tracks_baseline():
    original = _plan()
    analysis = analyze_feedback_patterns([_record(i) for i in range(10)])
    planned = build_ab_experiment_plan(original, analysis, exploration_count=5)
    assert validate_lock_preservation(original, planned) == []
    assert all(x["experiment"]["arm"] == "A" for x in planned)


def test_scope_does_not_pool_unrelated_recipes():
    rows = [
        {**_record(i), "preset_id": "chili_male", "market_recipe_id": "jp_chill"}
        for i in range(20)
    ] + [
        {**_record(100 + i), "preset_id": "senior_kr", "market_recipe_id": "kr_oldpop"}
        for i in range(20)
    ]
    scope = select_feedback_scope(rows, "chili_male", "jp_chill")
    assert scope["n"] == 20
    analysis = analyze_feedback_patterns(scope["records"])
    assert analysis["active"] is False


def test_experiment_manifest_is_proposal_only_and_lock_safe():
    original = _plan()
    analysis = analyze_feedback_patterns([_record(i) for i in range(30)])
    manifest = build_experiment_manifest(
        original,
        analysis,
        {"presetId": "chili_male", "marketRecipeId": "jp_chill"},
        exploration_count=4,
    )
    assert manifest["mode"] == "PROPOSAL_ONLY"
    assert manifest["summary"]["armB"] == 4
    assert manifest["summary"]["lockViolations"] == 0
    assert manifest["context"]["presetId"] == "chili_male"
    assert all("proposedChanges" in row for row in manifest["tracks"])
