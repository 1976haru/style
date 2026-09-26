import json

from core.prompt_intelligence import (
    analyze_current_prompt,
    load_prompt_intelligence_rules,
    validate_optimization_effectiveness,
    verify_immutable_fields,
)
from core.workflows import build_existing_json_upgrade_instruction, finalize_existing_upgrade


REQUIRED_AREAS = {
    "genre_clarity", "vocal_identity", "phonation", "groove", "drums", "bass",
    "instrumentation", "harmony", "verse_behavior", "chorus_behavior",
    "bridge_contrast", "final_payoff", "prompt_ordering", "redundancy",
    "contradiction", "exclude_efficiency", "prompt_length", "model_specific_behavior",
    "tempo_design", "performance_signature", "duration_design", "generation_hint",
    "information_density", "track_specificity", "bridge_specificity", "final_specificity",
    "money_chord_engine", "bridge_money_chord", "final_highlight_engine", "template_similarity",
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
            "syncopated pocket; dry rim and light hats; moving bass; Rhodes and muted guitar; narrow rhythmic Verse; "
            "melodic Chorus lift; Hook money chord I–V–vi–IV; "
            "Bridge drops hats, bass holds roots, vocal moves closer on IVmaj7–iv6–Imaj7; "
            "Final A+B restores full pocket with root-bass cadence on I–V–vi–IV → ii7–V7–Imaj7; section target 3:00-3:30"
        )
        row.update({
            "BPM": 98, "grooveDesign": "syncopated behind-beat pocket", "instrumentationDesign": "Rhodes and muted guitar",
            "harmonicDesign": {
                "chorusProgression": "I–V–vi–IV",
                "bridgeColor": "IVmaj7–iv6–Imaj7",
                "finalResolution": "I–V–vi–IV → ii7–V7–Imaj7",
            },
            "moneyChordDesign": {
                "hook": ["I–V–vi–IV"],
                "bridge": ["IVmaj7–iv6–Imaj7"],
                "finalHighlight": ["I–V–vi–IV", "ii7–V7–Imaj7"],
            },
            "bridgeDesign": {
                "changeAxes": ["drum density", "bass motion", "vocal distance"],
                "harmonicColor": "IVmaj7–iv6–Imaj7",
            },
            "highlightDesign": {
                "shape": "Final A+B sustained payoff",
                "harmonicPayoff": "I–V–vi–IV → ii7–V7–Imaj7",
            },
            "finalDesign": "Final A+B; full-pocket return; root-bass cadence; no early collapse",
            "durationDesign": "3:00-3:30", "generationRunHint": "reject early ending",
            "stylePrompt": new, "negativeStyleText": "female lead; power belt; early ending",
            "performanceSignature": "dry immediate pickup; clipped endings; one-beat hook pause",
            "promptOptimization": {
                "existingStylePrompt": old, "newStylePrompt": new,
                "changeReasons": ["removed repetition and added missing musical behavior"],
                "expectedImprovements": ["clearer groove, vocal identity and final payoff"],
                "weaknessesAddressed": ["redundancy", "groove", "bridge_contrast", "final_payoff"],
            },
        })
    return _attach_audits(source, result)


def _attach_audits(source, result):
    before = analyze_current_prompt(source)
    after = analyze_current_prompt(result)
    before_tracks = {str(x["trackNo"]): x for x in before["tracks"]}
    after_tracks = {str(x["trackNo"]): x for x in after["tracks"]}
    for old, new in zip(source["songs"], result["songs"]):
        changed = [
            field for field in (
                "BPM", "genreId", "genreText", "vocalDesign", "harmonicDesign", "stylePrompt", "excludePrompt",
                "negativeStyleText", "performanceSignature", "generationRunHint", "bridgeDesign", "highlightDesign",
                "finalDesign", "durationDesign", "grooveDesign", "drumDesign", "bassDesign",
                "instrumentationDesign", "verseBehavior", "chorusBehavior",
            ) if old.get(field) != new.get(field)
        ]
        b = before_tracks[str(old["trackNo"])]
        a = after_tracks[str(new["trackNo"])]
        b_areas = {x["area"] for x in b["weaknesses"]}
        a_areas = {x["area"] for x in a["weaknesses"]}
        reasons = ["Resolved content-based prompt weaknesses through concrete music-field changes"] if changed else []
        expected = ["Clearer musical control and fewer conflicting or diluted instructions"] if changed else []
        new["promptOptimization"] = {
            "status": "IMPROVED" if changed else "KEEP",
            "keepReason": "No actionable weakness remained after analysis" if not changed else "",
            "changedFields": changed,
            "resolvedWeaknesses": sorted(b_areas - a_areas),
            "remainingWeaknesses": sorted(a_areas),
            "changeReasons": reasons,
            "expectedImprovements": expected,
            "oldStylePrompt": old.get("stylePrompt", ""),
            "newStylePrompt": new.get("stylePrompt", ""),
            "oldExcludePrompt": old.get("excludePrompt") or old.get("negativeStyleText", ""),
            "newExcludePrompt": new.get("excludePrompt") or new.get("negativeStyleText", ""),
        }
    return result


def _mature_prompt_source(exclude_count=37):
    source = _source()
    source["meta"]["sunoModelTarget"] = "v6"
    style = (
        "Chill Rap, 98 BPM; young Japanese male tenor, speech-forward supported chest and subtle dry grain; "
        "syncopated relaxed pocket; dry rim, soft kick and light hats; moving warm bass; Rhodes and muted guitar; "
        "narrow rhythmic Verse; melodic Chorus lift; Hook money chord I–V–vi–IV; "
        "Bridge drops hats, bass holds roots, vocal moves closer on IVmaj7–iv6–Imaj7; "
        "Final A+B restores full pocket with root-bass cadence on I–V–vi–IV → ii7–V7–Imaj7; section target 3:00-3:30"
    )
    excludes = [
        "generic polished AI tenor", "generic Suno male pop vocal", "hyper-polished K-pop idol tenor", "power belt",
        "deep baritone", "gravel baritone", "middle-aged crooner", "smoky adult lounge", "falsetto-led hook",
        "falsetto hero Final", "female lead", "duet wall", "whisper-only lead", "rock rasp", "hard trap",
        "drill drums", "festival EDM", "static bass", "non-native Japanese pronunciation", "fully sung R&B Verse",
        "long portamento", "soul melisma", "anime voice", "idol squeak", "harsh cymbals", "muddy sub-bass",
        "over-lush strings", "giant vocal stack", "early fade", "abrupt ending", "random genre switch",
        "wide stereo vocal", "excessive reverb", "shouty hook", "slow dragged diction", "third voice", "choir wall",
    ][:exclude_count]
    for row in source["songs"]:
        row.update({
            "BPM": 98,
            "genreText": "Chill Rap",
            "vocalDesign": "recurring young Japanese male tenor, speech-forward supported chest, subtle dry grain",
            "harmonicDesign": {
                "chorusProgression": "I–V–vi–IV",
                "bridgeColor": "IVmaj7–iv6–Imaj7",
                "finalResolution": "I–V–vi–IV → ii7–V7–Imaj7",
            },
            "moneyChordDesign": {
                "hook": ["I–V–vi–IV", "vi–IV–I–V"],
                "bridge": ["IVmaj7–iv6–Imaj7"],
                "finalHighlight": ["I–V–vi–IV", "ii7–V7–Imaj7"],
            },
            "stylePrompt": style,
            "excludePrompt": "; ".join(excludes),
            "performanceSignature": "track-specific dry pickup and clipped phrase endings",
            "generationRunHint": "reject early ending and preserve native Japanese mora",
            "bridgeDesign": {
                "changeAxes": ["drum density", "bass motion", "vocal distance"],
                "purpose": "drop hats, simplify bass, move vocal closer before Final",
            },
            "highlightDesign": {
                "shape": "Final A+B sustained payoff",
                "harmonicPayoff": "I–V–vi–IV → ii7–V7–Imaj7",
            },
            "finalDesign": "Final A+B; restore full pocket; root-bass cadence; sustain payoff to ending",
            "durationDesign": "3:00-3:30",
            "grooveDesign": "relaxed syncopated pocket",
            "drumDesign": "dry rim, soft kick and light hats",
            "bassDesign": "warm moving bass locked to kick",
            "instrumentationDesign": "Rhodes and muted guitar",
            "verseBehavior": "narrow speech-rhythmic verse with clipped endings",
            "chorusBehavior": "melodic hook lift without singer change",
        })
    return source


def _compress_excludes(source, count=12):
    result = json.loads(json.dumps(source, ensure_ascii=False))
    compact = [
        "female or duet contamination", "generic polished male-pop tenor", "K-pop idol belt",
        "dark mature crooner", "whisper-only vocal", "falsetto-led hook or Final", "rock rasp or gravel",
        "non-native Japanese pronunciation", "fully sung R&B Verse", "hard trap or drill",
        "festival EDM", "static bass",
    ][:count]
    for row in result["songs"]:
        row["excludePrompt"] = "; ".join(compact)
    return _attach_audits(source, result)


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
    assert "contradiction" not in old["weaknessCounts"]
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


def test_actionable_weakness_without_related_change_is_noop_failure():
    source = _mature_prompt_source(37)
    result = json.loads(json.dumps(source, ensure_ascii=False))
    before, after = analyze_current_prompt(source), analyze_current_prompt(result)
    report = validate_optimization_effectiveness(source, result, before, after)
    issue = next(x for x in report["issues"] if x["code"] == "OPTIMIZATION_NOOP")
    assert issue["trackNo"] == "1"
    assert "exclude_efficiency" in issue["unresolvedAreas"]


def test_no_weakness_and_no_change_allows_explicit_keep():
    source = _mature_prompt_source(12)
    result = _attach_audits(source, json.loads(json.dumps(source, ensure_ascii=False)))
    final, issues = finalize_existing_upgrade(json.dumps(source), json.dumps(result), "Chill Rap")
    assert not [x for x in issues if x["level"] == "FAIL"], issues
    assert final["promptOptimizationReport"]["changedTrackCount"] == 0
    assert final["promptOptimizationReport"]["unchangedTrackCount"] == 15
    assert final["promptOptimizationReport"]["optimizationEffective"] is True
    assert all(x["promptOptimization"]["status"] == "KEEP" for x in final["songs"])


def test_exclude_over_16_is_actionable_and_compression_resolves_it():
    source = _mature_prompt_source(37)
    result = _compress_excludes(source, 12)
    before, after = analyze_current_prompt(source), analyze_current_prompt(result)
    assert before["weaknessCounts"]["exclude_efficiency"] == 15
    assert "exclude_efficiency" not in after["weaknessCounts"]
    effect = validate_optimization_effectiveness(source, result, before, after)
    assert not [x for x in effect["issues"] if x["code"] == "OPTIMIZATION_NOOP"]
    assert effect["report"]["changedFieldCounts"]["excludePrompt"] == 15
    assert effect["report"]["resolvedWeaknessCount"] == 15


def test_exclude_still_over_16_after_edit_is_rejected():
    source = _mature_prompt_source(37)
    result = _compress_excludes(source, 12)
    for row in result["songs"]:
        row["excludePrompt"] += "; extra category A; extra category B; extra category C; extra category D; extra category E"
    result = _attach_audits(source, result)
    _, issues = finalize_existing_upgrade(json.dumps(source), json.dumps(result), "Chill Rap")
    assert "EXCLUDE_COMPRESSION_INCOMPLETE" in {x["code"] for x in issues}


def test_positive_male_tenor_and_generic_male_tenor_exclude_is_not_conflict():
    source = _mature_prompt_source(12)
    for row in source["songs"]:
        row["excludePrompt"] = "generic polished AI tenor; female vocal"
    analysis = analyze_current_prompt(source)
    assert "contradiction" not in analysis["weaknessCounts"]


def test_male_positive_and_female_exclude_is_not_conflict():
    source = _mature_prompt_source(12)
    for row in source["songs"]:
        row["excludePrompt"] = "female lead; duet contamination"
    analysis = analyze_current_prompt(source)
    assert "contradiction" not in analysis["weaknessCounts"]


def test_only_semantic_exclusive_conditions_are_contradictions():
    source = _mature_prompt_source(12)
    source["songs"][0]["stylePrompt"] += "; whisper-only lead"
    source["songs"][0]["excludePrompt"] += "; whisper-only"
    analysis = analyze_current_prompt(source)
    assert "contradiction" in {x["area"] for x in analysis["tracks"][0]["weaknesses"]}
    source["songs"][1]["stylePrompt"] += "; instrumental-only; lead vocal desired"
    analysis = analyze_current_prompt(source)
    assert "contradiction" in {x["area"] for x in analysis["tracks"][1]["weaknesses"]}


def test_claimed_changed_fields_must_match_actual_diff():
    source = _mature_prompt_source(37)
    result = _compress_excludes(source)
    result["songs"][0]["promptOptimization"]["changedFields"] = ["stylePrompt"]
    effect = validate_optimization_effectiveness(source, result, analyze_current_prompt(source), analyze_current_prompt(result))
    assert "CLAIMED_CHANGED_FIELDS_MISMATCH" in {x["code"] for x in effect["issues"]}


def test_reason_or_improvement_claim_without_any_field_diff_fails():
    source = _mature_prompt_source(12)
    result = json.loads(json.dumps(source, ensure_ascii=False))
    for row in result["songs"]:
        row["promptOptimization"] = {
            "changeReasons": ["Reordered the prompt"],
            "expectedImprovements": ["Clearer generation"],
        }
    effect = validate_optimization_effectiveness(source, result, analyze_current_prompt(source), analyze_current_prompt(result))
    assert "AUDIT_WITHOUT_FIELD_DIFF" in {x["code"] for x in effect["issues"]}


def test_claimed_resolved_weakness_must_disappear_after_analysis():
    source = _mature_prompt_source(37)
    result = json.loads(json.dumps(source, ensure_ascii=False))
    for row in result["songs"]:
        row["performanceSignature"] += "; extra articulation cue"
    result = _attach_audits(source, result)
    result["songs"][0]["promptOptimization"]["resolvedWeaknesses"] = ["exclude_efficiency"]
    effect = validate_optimization_effectiveness(source, result, analyze_current_prompt(source), analyze_current_prompt(result))
    codes = {x["code"] for x in effect["issues"]}
    assert "CLAIMED_WEAKNESS_UNRESOLVED" in codes
    assert "OPTIMIZATION_NOOP" in codes


def test_report_counts_changed_tracks_fields_and_before_after_weaknesses():
    source = _mature_prompt_source(37)
    result = _compress_excludes(source)
    final, issues = finalize_existing_upgrade(json.dumps(source), json.dumps(result), "Chill Rap")
    assert not [x for x in issues if x["level"] == "FAIL"], issues
    report = final["promptOptimizationReport"]
    assert report["changedTrackCount"] == 15
    assert report["unchangedTrackCount"] == 0
    assert report["changedFieldCounts"] == {"excludePrompt": 15}
    assert report["totalWeaknessBefore"] == 15
    assert report["totalWeaknessAfter"] == 0
    assert report["resolvedWeaknessCount"] == 15
    assert report["optimizationEffective"] is True
    for row in final["songs"]:
        audit = row["promptOptimization"]
        assert audit["status"] == "IMPROVED"
        assert audit["changedFields"] == ["excludePrompt"]
        assert audit["resolvedWeaknesses"] == ["exclude_efficiency"]
        assert audit["remainingWeaknesses"] == []
        assert audit["oldStylePrompt"] == audit["newStylePrompt"]
        assert audit["oldExcludePrompt"] != audit["newExcludePrompt"]


def test_finalizer_preserves_title_lyrics_hook_story_and_scene():
    source = _mature_prompt_source(37)
    result = _compress_excludes(source)
    for row in result["songs"]:
        row["title"] = "rewritten title"
        row["lyrics"] = "rewritten lyrics"
        row["hookPhrase"] = "rewritten hook"
        row["story"] = "rewritten story"
        row["scene"] = "rewritten scene"
    final, issues = finalize_existing_upgrade(json.dumps(source, ensure_ascii=False), json.dumps(result, ensure_ascii=False), "Chill Rap")
    assert not [x for x in issues if x["level"] == "FAIL"], issues
    assert not verify_immutable_fields(source, final)


def test_wrong_gender_regression_is_blocked():
    source = _mature_prompt_source(37)
    result = _compress_excludes(source)
    result["songs"][0]["vocalType"] = "Female Solo"
    _, issues = finalize_existing_upgrade(json.dumps(source), json.dumps(result), "Chill Rap")
    assert "WRONG_VOCAL_ROLE" in {x["code"] for x in issues}


def test_genre_drift_regression_is_blocked():
    source = _mature_prompt_source(37)
    result = _compress_excludes(source)
    result["songs"][0]["genreText"] = "Hard Trap"
    result["songs"][0]["stylePrompt"] = result["songs"][0]["stylePrompt"].replace("Chill Rap", "Hard Trap", 1)
    result = _attach_audits(source, result)
    _, issues = finalize_existing_upgrade(json.dumps(source), json.dumps(result), "Chill Rap")
    assert "GENRE_DRIFT" in {x["code"] for x in issues}


def test_style_prompt_hard_max_regression_is_blocked():
    source = _mature_prompt_source(37)
    result = _compress_excludes(source)
    result["songs"][0]["stylePrompt"] += "; " + ("overlong instruction " * 100)
    result = _attach_audits(source, result)
    _, issues = finalize_existing_upgrade(json.dumps(source), json.dumps(result), "Chill Rap")
    assert "STYLE_PROMPT_HARD_MAX" in {x["code"] for x in issues}


def test_wrong_bridge_final_signature_and_generic_vocal_regressions_are_blocked():
    source = _mature_prompt_source(37)
    result = _compress_excludes(source)
    result["songs"][0]["bridgeDesign"] = ""
    result["songs"][0]["finalDesign"] = ""
    result["songs"][0]["stylePrompt"] = result["songs"][0]["stylePrompt"].replace("Bridge", "Break").replace("Final", "End")
    result["songs"][0]["performanceSignature"] = ""
    result["songs"][0]["vocalDesign"] = "generic polished AI tenor vocal"
    result = _attach_audits(source, result)
    _, issues = finalize_existing_upgrade(json.dumps(source), json.dumps(result), "Chill Rap")
    codes = {x["code"] for x in issues}
    assert {"MISSING_BRIDGE", "MISSING_FINAL", "MISSING_PERFORMANCE_SIGNATURE", "GENERIC_VOCAL_REGRESSION"} <= codes


def test_new_contradiction_and_duplicate_prompt_regressions_are_blocked():
    source = _mature_prompt_source(37)
    result = _compress_excludes(source)
    result["songs"][0]["stylePrompt"] += "; whisper-only lead"
    result["songs"][0]["excludePrompt"] += "; whisper-only"
    result["songs"][1]["stylePrompt"] += "; repeated cue; repeated cue"
    result = _attach_audits(source, result)
    _, issues = finalize_existing_upgrade(json.dumps(source), json.dumps(result), "Chill Rap")
    codes = {x["code"] for x in issues}
    assert {"NEW_CONTRADICTION_REGRESSION", "DUPLICATE_HEAVY_PROMPT_REGRESSION"} <= codes


def test_sanitized_nam002_acceptance_compresses_excludes_15_of_15():
    source = _mature_prompt_source(37)
    result = _compress_excludes(source, 12)
    final, issues = finalize_existing_upgrade(json.dumps(source, ensure_ascii=False), json.dumps(result, ensure_ascii=False), "Chill Rap")
    assert not [x for x in issues if x["level"] == "FAIL"], issues
    assert final["promptOptimizationReport"]["changedFieldCounts"]["excludePrompt"] == 15
    assert all(len(row["excludePrompt"].split(";")) <= 16 for row in final["songs"])
    assert all(row["promptOptimization"]["changeReasons"] for row in final["songs"])
    assert all(row["promptOptimization"]["expectedImprovements"] for row in final["songs"])
    for before, after in zip(source["songs"], final["songs"]):
        for field in ("title", "lyrics", "hookPhrase", "story", "scene"):
            assert before[field] == after[field]


def _structured_quality_set(*, generic_template=False, weak_bridge=False, generic_final=False):
    source = _mature_prompt_source(12)
    palettes = [
        "muted guitar harmonics and brushed rim", "Rhodes tremolo and side-stick", "nylon guitar and shaker",
        "Wurlitzer pulse and dry clap", "piano ostinato and woodblock", "marimba flecks and rim click",
        "organ stabs and soft kick", "acoustic guitar taps and tambourine", "electric piano and cross-stick",
        "plucked synth and brushed snare", "vibraphone accents and rim", "clean guitar arpeggio and shaker",
        "piano dyads and dry backbeat", "Rhodes chords and hand percussion", "muted guitar pulse and soft snare",
    ]
    for i, row in enumerate(source["songs"]):
        palette = "Rhodes loop and dry rim" if generic_template else palettes[i]
        bridge = (
            "Bridge drops drums on IVmaj7–iv6–Imaj7"
            if weak_bridge else
            "Bridge drops drums, bass holds roots, vocal moves to far-room distance on IVmaj7–iv6–Imaj7"
        )
        final = (
            "Final A+B restores the full pocket with root-bass cadence on I–V–vi–IV → ii7–V7–Imaj7"
            if generic_final else
            f"Final A+B restores the full pocket with root-bass cadence and cadence color {i + 1} on I–V–vi–IV → ii7–V7–Imaj7"
        )
        row["stylePrompt"] = (
            f"Chill Rap, 98 BPM; recurring Japanese male tenor, supported chest and dry grain; {palette}; "
            f"syncopated pocket; Hook money chord I–V–vi–IV; {bridge}; {final}; section target 3:00-3:30"
        )
        row["moneyChordDesign"] = {
            "hook": ["I–V–vi–IV", "IVmaj7–V–iii7–vi7"],
            "bridge": ["IVmaj7–iv6–Imaj7"],
            "finalHighlight": ["I–V–vi–IV", "ii7–V7–Imaj7"],
        }
        row["bridgeDesign"] = {
            "changeAxes": "drums and percussion + bass motion + vocal distance",
            "purpose": "audible late-song contrast",
            "mustNot": "do not swap singer",
        }
        row["highlightDesign"] = {
            "shape": "Final A+B sustained payoff",
            "harmonicPayoff": f"cadence color {i + 1}",
            "rule": "retain singer identity",
        }
        row["performanceSignature"] = f"track {i + 1} pickup and phrase-ending behavior"
    return source


def test_good_specific_prompt_is_not_rewritten_by_quality_checks():
    analysis = analyze_current_prompt(_structured_quality_set())
    advanced = {"information_density", "track_specificity", "bridge_specificity", "final_specificity", "template_similarity"}
    assert not (advanced & set(analysis["weaknessCounts"]))


def test_semantically_repetitive_style_atoms_reduce_information_density():
    source = _structured_quality_set()
    source["songs"][0]["stylePrompt"] += "; muted guitar harmonics with brushed rim detail"
    analysis = analyze_current_prompt(source)
    assert "information_density" in {x["area"] for x in analysis["tracks"][0]["weaknesses"]}


def test_generic_bridge_missing_declared_axes_is_detected():
    analysis = analyze_current_prompt(_structured_quality_set(weak_bridge=True))
    assert analysis["weaknessCounts"]["bridge_specificity"] == 15


def test_track_specific_bridge_axes_are_accepted():
    analysis = analyze_current_prompt(_structured_quality_set())
    assert "bridge_specificity" not in analysis["weaknessCounts"]


def test_generic_final_omitting_distinct_highlight_is_detected():
    analysis = analyze_current_prompt(_structured_quality_set(generic_final=True))
    assert analysis["weaknessCounts"]["final_specificity"] == 15


def test_shared_singer_identity_alone_is_not_template_similarity():
    analysis = analyze_current_prompt(_structured_quality_set())
    assert "template_similarity" not in analysis["weaknessCounts"]


def test_repeated_instrument_groove_bridge_final_template_is_detected():
    source = _structured_quality_set(generic_template=True)
    for row in source["songs"]:
        row["performanceSignature"] = "same clipped pickup and ending"
    analysis = analyze_current_prompt(source)
    assert analysis["weaknessCounts"]["template_similarity"] == 15
    assert analysis["weaknessCounts"]["track_specificity"] == 15


def test_advanced_quality_analysis_still_ignores_version_label():
    old = _structured_quality_set(weak_bridge=True)
    latest = json.loads(json.dumps(old))
    old["meta"]["version"] = "v15.0"
    latest["meta"]["version"] = "v99.0"
    assert analyze_current_prompt(old) == analyze_current_prompt(latest)


def test_multiple_money_chord_progressions_per_section_are_accepted():
    source = _mature_prompt_source(12)
    row = source["songs"][0]
    row["moneyChordDesign"]["hook"] = ["I–V–vi–IV", "IVmaj7–V–iii7–vi7"]
    row["stylePrompt"] = row["stylePrompt"].replace(
        "Hook money chord I–V–vi–IV",
        "Hook money chords I–V–vi–IV and IVmaj7–V–iii7–vi7",
    )
    analysis = analyze_current_prompt(source)
    first = {x["area"] for x in analysis["tracks"][0]["weaknesses"]}
    assert "money_chord_engine" not in first


def test_money_chord_metadata_without_actual_style_prompt_is_rejected():
    source = _mature_prompt_source(12)
    source["songs"][0]["stylePrompt"] = (
        "Chill Rap, 98 BPM; young Japanese male tenor; syncopated pocket; dry rim; moving bass; "
        "Bridge drops hats and bass, vocal moves closer; Final A+B restores full pocket with root-bass cadence"
    )
    analysis = analyze_current_prompt(source)
    first = {x["area"] for x in analysis["tracks"][0]["weaknesses"]}
    assert "money_chord_engine" in first
    assert "final_highlight_engine" in first


def test_anchor_requires_three_bridge_axes_and_final_abc():
    source = _mature_prompt_source(12)
    row = source["songs"][0]
    row["trackRole"] = "anchor"
    row["stylePrompt"] = row["stylePrompt"].replace(
        "Bridge drops hats, bass holds roots, vocal moves closer",
        "Bridge drops hats, bass holds roots",
    ).replace("Final A+B", "Final A+B")
    analysis = analyze_current_prompt(source)
    first = {x["area"] for x in analysis["tracks"][0]["weaknesses"]}
    assert "bridge_money_chord" in first
    assert "final_highlight_engine" in first
