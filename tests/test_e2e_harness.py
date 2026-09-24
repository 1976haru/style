import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.e2e import run_e2e_harness, validate_e2e_output
from core.feedback import add_feedback, init_feedback_db, list_feedback
from core.io_utils import load_json
from core.track_plan import extract_track_plan, recompute_track_plan


PRESETS = load_json(ROOT / "data" / "channel_presets.json")
RECIPES = load_json(ROOT / "data" / "genre_recipes.json")
PUBLIC = load_json(ROOT / "data" / "public_rules.json")
MARKET_RECIPE = {
    "id": "e2e_chill",
    "label": "E2E Chill Rap",
    "genreFamily": "Chill Rap / lo-fi soul",
    "vocalMode": "vocal",
    "languages": ["Japanese"],
    "bpmRange": [88, 104],
}
MASTER = """핵심 장르: Chill Rap
BPM 정책
Core 92~100 BPM
Flagship 96~104 BPM
Memory 88~92 BPM
"""


def _directive(kind):
    roles = {
        "male": ["Male Solo"] * 15,
        "female": ["Female Solo"] * 15,
        "dual": (["Male Solo", "Female Solo", "Male-Female Asymmetric Duet"] * 5),
    }[kind]
    songs = []
    for i, vocal in enumerate(roles, 1):
        songs.append({
            "trackNo": i,
            "title": f"窓辺の記憶 {kind} {i}",
            "hookPhrase": f"まだここにいる {kind} {i}",
            "storyAct": f"Act {(i - 1) // 3 + 1}",
            "storyArcRole": f"story beat {i}",
            "listenerSituation": f"終電の窓で場面 {i} を思い出す",
            "emotionArc": f"ためらいから受容へ {i}",
            "BPM": 64 + i,
            "genre": "Lo-fi Hip-Hop Study",
            "vocalType": vocal + " soft male voice just above a whisper",
            "structure": "old short ending",
            "trackRole": "flagship" if i in (2, 9, 15) else ("memory" if i in (6, 12) else "core"),
        })
    payload = {
        "storySource": f"{kind} locked source",
        "legacyAppendix": "obsolete production appendix\n" * 2100,
        "songs": songs,
    }
    # Simulate a large legacy directive without committing private/real inputs.
    return json.dumps(payload, ensure_ascii=False)


def _generated(rows):
    songs = []
    for row in rows:
        trusted, music = row["trusted"], row["recomputed"]
        gender = "Male Solo" if "male solo only" in music["vocal"].lower() else (
            "Female Solo" if "female solo only" in music["vocal"].lower() else (
                "Male-Female Asymmetric Duet" if "exactly two" in music["vocal"].lower() else (
                    "Female Solo" if "female" in music["vocal"].lower() else "Male Solo"
                )
            )
        )
        songs.append({
            "trackNo": row["trackNo"],
            "title": trusted["title"],
            "hookPhrase": trusted["hookPhrase"],
            "storyAct": trusted["storyAct"],
            "storyArcRole": trusted["storyArcRole"],
            "listenerSituation": trusted["listenerSituation"],
            "emotionArc": trusted["emotionArc"],
            "BPM": music["BPM"],
            "genre": music["genre"],
            "trackRole": music["musicRole"],
            "vocalType": gender,
            "performanceSignature": music["performanceSignature"],
            "structure": music["structure"],
            "lyrics": "[Verse]\n終電の窓に映る君を見て\n[Chorus]\nまだここにいる",
            "stylePrompt": "Chill Rap, " + music["genre"] + "; " + music["structure"],
            "negativeStyleText": "legacy vocal, early ending",
            "generationRunHint": "preserve locked scene",
        })
    return json.dumps({"songs": songs}, ensure_ascii=False)


@pytest.mark.parametrize(
    "kind,preset_id",
    [("male", "chili_male"), ("female", "chili_female"), ("dual", "chili_dual")],
)
def test_full_e2e_male_female_dual_fixtures(kind, preset_id):
    directive = _directive(kind)
    plan, _ = extract_track_plan(directive, 15)
    recomputed, _ = recompute_track_plan(plan, preset_id, PRESETS[preset_id], MARKET_RECIPE, MASTER)
    result = run_e2e_harness(
        directive, _generated(recomputed), preset_id, PRESETS[preset_id],
        RECIPES["auto"], PUBLIC, MARKET_RECIPE, MASTER, "HYBRID", 15,
    )
    assert result["passed"], result["qa"]
    assert result["summary"] == {"expectedTracks": 15, "parsedTracks": 15, "finalTracks": 15, "failures": 0}
    assert result["compiler"]["manifest"]["directiveEmbeddingMode"] == "STRUCTURED_DIGEST_ONLY"
    assert "obsolete production appendix\n" * 100 not in result["compiler"]["instruction"]
    for old, new, final in zip(result["comparison"]["original"], result["comparison"]["recomputed"], result["comparison"]["final"]):
        assert old["trusted"] == new["trusted"]
        assert final["title"] == old["trusted"]["title"]
        assert final["hookPhrase"] == old["trusted"]["hookPhrase"]


def test_e2e_validator_reports_required_regressions():
    directive = _directive("male")
    original, _ = extract_track_plan(directive, 15)
    recomputed, meta = recompute_track_plan(original, "chili_male", PRESETS["chili_male"], MARKET_RECIPE, MASTER)
    generated = json.loads(_generated(recomputed))
    first = generated["songs"][0]
    first.update({
        "title": generated["songs"][1]["title"],
        "hookPhrase": generated["songs"][1]["hookPhrase"],
        "listenerSituation": "changed scene",
        "storyAct": "changed story",
        "BPM": original[0]["importedMusic"]["BPM"],
        "genre": "Trap",
        "trackRole": "Memory",
        "vocalType": "Female Solo soft male voice just above a whisper",
        "performanceSignature": "generic vocal",
        "lyrics": "[Verse]\nThis is entirely the wrong language and contains only English words for the whole song.",
        "stylePrompt": "Chill Rap, " + ("x" * 1100),
        "structure": "Verse then abrupt ending",
    })
    generated["songs"][1]["structure"] = "Verse then Bridge then weak Final"
    generated["songs"][1]["stylePrompt"] = "Chill Rap, Bridge then weak Final"
    issues = validate_e2e_output(json.dumps(generated, ensure_ascii=False), original, recomputed, meta, PRESETS["chili_male"])
    codes = {x["code"] for x in issues}
    assert {
        "LOCK_TITLE", "LOCK_HOOK", "LOCK_SCENE", "LOCK_STORY", "DUPLICATE_TITLE", "DUPLICATE_HOOK",
        "MUSIC_ROLE", "ROLE_BPM_RANGE", "LEGACY_BPM_LEAK", "GENRE_POLICY", "STYLE_LENGTH",
        "BRIDGE_FINAL", "ANCHOR_FINAL", "WRONG_GENDER", "LEGACY_VOCAL_LEAK", "GENERIC_VOCAL", "WRONG_LANGUAGE",
    } <= codes


def test_e2e_accepts_preserved_basic_vocal_role_labels():
    directive = json.loads(_directive("male"))
    for song in directive["songs"]:
        song["vocalType"] = "Male Solo"
    raw = json.dumps(directive, ensure_ascii=False)
    original, _ = extract_track_plan(raw, 15)
    recomputed, meta = recompute_track_plan(
        original, "chili_male", PRESETS["chili_male"], MARKET_RECIPE, MASTER
    )
    issues = validate_e2e_output(
        _generated(recomputed), original, recomputed, meta, PRESETS["chili_male"]
    )
    assert "LEGACY_VOCAL_LEAK" not in {x["code"] for x in issues}


def test_dual_flexible_language_policy_accepts_english_project():
    directive = _directive("dual")
    original, _ = extract_track_plan(directive, 15)
    recomputed, meta = recompute_track_plan(
        original, "chili_dual", PRESETS["chili_dual"], MARKET_RECIPE, MASTER
    )
    generated = json.loads(_generated(recomputed))
    for song in generated["songs"]:
        song["lyrics"] = "[Verse]\nThis English project follows the brief with natural conversational lines."
    issues = validate_e2e_output(
        json.dumps(generated), original, recomputed, meta, PRESETS["chili_dual"]
    )
    assert "WRONG_LANGUAGE" not in {x["code"] for x in issues}


def test_windows_sqlite_connections_release_file_handles():
    # Keep the database on the project volume. Besides sandbox compatibility,
    # this exercises the same Windows filesystem semantics as user_data/.
    db = ROOT / ".test_feedback_lock.sqlite3"
    moved = ROOT / ".test_feedback_lock_moved.sqlite3"
    try:
        init_feedback_db(db)
        record = {
            "session_id": "lock-test", "preset_id": "chili_male", "market_recipe_id": "e2e_chill",
            "track_no": 1, "title": "T", "bpm": 98, "decision": "KEEP",
            "overall": 5, "vocal_identity": 5, "hook": 5, "groove": 5, "prompt_adherence": 5,
        }
        for _ in range(3):
            add_feedback(db, record)
            assert list_feedback(db)
        os.replace(db, moved)
        moved.unlink()
        assert not moved.exists()
    finally:
        for path in (db, moved):
            if path.exists():
                path.unlink()
