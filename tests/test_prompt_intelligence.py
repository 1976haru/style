import json

from core.prompt_intelligence import (
    analyze_current_prompt,
    load_prompt_intelligence_rules,
    verify_immutable_fields,
)
from core.workflows import build_existing_json_upgrade_instruction, finalize_existing_upgrade


REQUIRED_AREAS = {
    "genre_clarity", "vocal_identity", "phonation", "groove", "drums", "bass",
    "instrumentation", "harmony", "verse_behavior", "chorus_behavior",
    "bridge_contrast", "final_payoff", "prompt_ordering", "redundancy",
    "contradiction", "exclude_efficiency", "prompt_length", "model_specific_behavior",
    "tempo_design", "performance_signature", "duration_design", "generation_hint",
}

MASTER = """CHILI LAB Male Solo ONLY
Chill Rap
Core 92~100 BPM
Anchor 96~104 BPM
Memory 88~92 BPM
"""


def _source(version="v14"):
    return {
        "meta": {"version": version, "generationStandardVersion": version, "storyPov": "male", "genrePolicy": "Chill Rap"},
        "songs": [
            {
                "trackNo": i,
                "title": f"TITLE-{i}",
                "lyrics": f"LYRICS-{i}",
                "hookPhrase": f"HOOK-{i}",
                "story": f"STORY-{i}",
                "scene": f"SCENE-{i}",
                "relationshipBoundary": "아직 고백하지 않는다",
                "BPM": 94,
                "genre": "Chill Rap",
                "vocalType": "Male Solo",
                "stylePrompt": "Chill Rap; soft; soft",
                "negativeStyleText": "soft; soft",
            }
            for i in range(1, 16)
        ],
    }


def _optimized(source):
    result = json.loads(json.dumps(source, ensure_ascii=False))
    for row in result["songs"]:
        old = row["stylePrompt"]
        new = (
            "Chill Rap, 98 BPM; recurring male speech-forward tenor, supported warm chest and dry grain; "
            "syncopated pocket; dry rim and light hats; moving bass; Rhodes and muted guitar; seventh-chord motion; "
            "narrow rhythmic Verse; melodic Chorus lift; Bridge with rhythm and texture contrast; Final A+B payoff"
        )
        row.update({
            "BPM": 98, "grooveDesign": "syncopated behind-beat pocket", "instrumentationDesign": "Rhodes and muted guitar",
            "harmonicDesign": "seventh-chord tension and release", "bridgeDesign": "rhythm and texture contrast",
            "finalDesign": "Final A+B payoff", "durationDesign": "3:00-3:30", "generationRunHint": "reject early ending",
            "stylePrompt": new, "negativeStyleText": "female lead; power belt; early ending",
            "performanceSignature": "dry immediate pickup; clipped endings; one-beat hook pause",
            "promptOptimization": {
                "existingStylePrompt": old, "newStylePrompt": new,
                "changeReasons": ["removed repetition and added missing musical behavior"],
                "expectedImprovements": ["clearer groove, vocal identity and final payoff"],
                "weaknessesAddressed": ["redundancy", "groove", "bridge_contrast", "final_payoff"],
            },
        })
    return result


def test_rules_cover_all_required_prompt_intelligence_areas():
    rules = load_prompt_intelligence_rules()
    assert REQUIRED_AREAS <= set(rules["areas"])
    assert "version" in rules["policy"]["baseline"].lower()


def test_analysis_is_version_agnostic_and_detects_content_weaknesses():
    old = analyze_current_prompt(_source("v14"))
    latest = analyze_current_prompt(_source("v16"))
    assert old == latest
    assert old["versionUsedAsQualitySignal"] is False
    assert old["weaknessCounts"]["redundancy"] == 15
    assert old["weaknessCounts"]["contradiction"] == 15
    assert old["weaknessCounts"]["bridge_contrast"] == 15
    assert "model_specific_behavior" in old["weaknessCounts"]
    assert old["weaknessCounts"]["performance_signature"] == 15
    assert old["weaknessCounts"]["duration_design"] == 15
    assert old["weaknessCounts"]["generation_hint"] == 15


def test_analysis_detects_bad_prompt_ordering_from_music_content():
    source = _source()
    source["meta"]["sunoModelTarget"] = "v6"
    source["songs"][0]["stylePrompt"] = "moving bass; syncopated groove; 98 BPM; Chill Rap; Male Solo; Verse then Chorus"
    analysis = analyze_current_prompt(source)
    first_areas = {x["area"] for x in analysis["tracks"][0]["weaknesses"]}
    assert "prompt_ordering" in first_areas


def test_optimizer_instruction_has_ten_steps_rules_analysis_and_no_version_keep_logic():
    instruction, _ = build_existing_json_upgrade_instruction(json.dumps(_source(), ensure_ascii=False), MASTER, "Chill Rap")
    for step in (
        "Analyze Current Prompt", "Detect weaknesses", "Apply Channel Master", "Apply Genre Master",
        "Apply Prompt Intelligence Knowledge", "Remove redundancy/conflicts", "Generate optimized music fields",
        "Compare Old vs New", "Verify immutable fields unchanged", "Save full Suno-ready JSON",
    ):
        assert step in instruction
    assert "[PROMPT INTELLIGENCE RULES]" in instruction
    assert "[CURRENT PROMPT ANALYSIS - VERSION-AGNOSTIC]" in instruction
    assert "이미 최신 버전" in instruction
    assert "품질 판단 근거가 아니다" in instruction


def test_finalize_preserves_all_immutable_fields_and_builds_visible_comparison():
    source = _source()
    proposed = _optimized(source)
    for row in proposed["songs"]:
        row.update({"title": "CHANGED", "lyrics": "CHANGED", "hookPhrase": "CHANGED", "story": "CHANGED", "scene": "CHANGED", "relationshipBoundary": "연인이 된다"})
    final, issues = finalize_existing_upgrade(json.dumps(source, ensure_ascii=False), json.dumps(proposed, ensure_ascii=False))
    assert not [x for x in issues if x["level"] == "FAIL"], issues
    assert not verify_immutable_fields(source, final)
    for i, row in enumerate(final["songs"], 1):
        assert row["title"] == f"TITLE-{i}"
        assert row["lyrics"] == f"LYRICS-{i}"
        assert row["hookPhrase"] == f"HOOK-{i}"
        assert row["story"] == f"STORY-{i}"
        assert row["scene"] == f"SCENE-{i}"
        assert row["relationshipBoundary"] == "아직 고백하지 않는다"
    comparison = final["promptOptimizationReport"]["comparisons"][0]
    assert comparison["existingStylePrompt"] == "Chill Rap; soft; soft"
    assert comparison["newStylePrompt"].startswith("Chill Rap, 98 BPM")
    assert comparison["changeReasons"]
    assert comparison["expectedImprovements"]


def test_finalize_rejects_missing_old_new_reason_improvement_audit():
    source = _source()
    proposed = _optimized(source)
    proposed["songs"][0]["promptOptimization"] = {"existingStylePrompt": "wrong", "newStylePrompt": "wrong"}
    _, issues = finalize_existing_upgrade(json.dumps(source), json.dumps(proposed))
    codes = {x["code"] for x in issues}
    assert {"OLD_PROMPT_MISMATCH", "NEW_PROMPT_MISMATCH", "MISSING_CHANGE_REASONS", "MISSING_EXPECTED_IMPROVEMENTS"} <= codes
