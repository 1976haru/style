import json

from core.prompt_intelligence import analyze_current_prompt
from core.v061_quality_gate import (
    female_section_labels_equivalent,
    japanese_positive_controls,
    normalize_female_section_labels,
    v061_result_failures,
    v061_track_findings,
)
from core.workflows import finalize_existing_upgrade


def _jp_male_source():
    songs = []
    for i in range(1, 16):
        songs.append({
            "trackNo": i,
            "title": f"T-{i}",
            "titleLocalized": f"T-{i}",
            "hookPhrase": f"H-{i}",
            "lyrics": f"歌詞-{i}",
            "story": f"S-{i}",
            "scene": "cafe-window music talk",
            "BPM": 96,
            "genreText": "Chill Rap / jazz-hop tint",
            "vocalType": "Male Solo",
            "stylePrompt": (
                "Chill Rap, jazz-hop tint, 96 BPM relaxed head-nod pocket; "
                "HARD LOCK young Japanese male tenor only; "
                "VOICE close-mic speech-forward warm-light chest, breath 10-20%, dry grain 5-12%, "
                "JP-native diction, mora timing, natural sentence accent; "
                "RAP Verse40-55% half-rap, syncopated pickups; "
                "soft kick, dry rim, moving bass; Rhodes + muted guitar; "
                f"Hook H-{i} melodic; Bridge drums thin, bass sparse, vocal close; "
                "Final A+B full pocket; Money H I-V-vi-IV / B vi-IV-I-V / F ii-V-I; "
                "SCENE cafe-window shy-sweet; 2:45-3:30, no early end."
            ),
            "excludePrompt": "female or duet contamination; generic polished tenor; mature crooner; whisper-only; falsetto hero; non-native Japanese; full R&B ballad; hard trap; festival EDM; early ending",
            "vocalDesign": {
                "base": "young Japanese male tenor, close-mic speech-forward warm-light chest, breath 10-20%, dry grain 5-12%, native Japanese diction, mora-timed phrasing, natural sentence accent",
                "verse": "40-55% rap-forward, breath 10-20%, straight tone, compact endings",
                "chorus": "same singer, breath 10-20%, brighter hook",
                "bridge": "same singer, breath 10-20%, closer/drier",
                "final": "same singer, breath 10-20%, supported male self-response",
            },
            "performanceSignature": f"track-{i} pickup/rest pattern",
            "generationRunHint": "Suno v6; Variety 0; reject singer drift",
            "bridgeDesign": {"changeAxes": ["drums", "bass", "vocal distance"], "specificCue": "drums thin; bass sparse; vocal close"},
            "highlightDesign": {"harmonicPayoff": "ii-V-I", "specificCue": "full pocket return"},
            "finalDesign": {"specificCue": "Final A+B full pocket"},
            "durationDesign": {"hardRange": "2:45-3:30"},
            "instrumentationDesign": "Rhodes and muted guitar",
            "grooveDesign": "relaxed head-nod pocket",
            "harmonicDesign": "I-V-vi-IV, Bridge vi-IV-I-V, Final ii-V-I",
            "verseBehavior": "40-55% half-rap",
            "chorusBehavior": "melodic title hook",
        })
    return {
        "meta": {
            "lyricLanguage": "japanese",
            "channelId": "jp-chili-lab-story",
            "sunoModelTarget": "v6",
            "genrePolicy": "Chill Rap",
        },
        "songs": songs,
    }


def test_japanese_positive_controls_accept_complete_style():
    controls = japanese_positive_controls(_jp_male_source()["songs"][0]["stylePrompt"])
    assert all(controls.values())


def test_japanese_positive_controls_flag_missing_positive_controls():
    row = _jp_male_source()["songs"][0]
    row["stylePrompt"] = row["stylePrompt"].replace("close-mic ", "").replace("JP-native diction, mora timing, natural sentence accent; ", "")
    findings = v061_track_findings(row, {"lyricLanguage": "japanese"})
    assert "jp_native_positive_controls" in {x["area"] for x in findings}


def test_vocal_design_conflict_detected_when_legacy_breath_ranges_remain():
    row = _jp_male_source()["songs"][0]
    row["vocalDesign"]["verse"] = "breathiness 35-45; airy spoken-sung"
    row["vocalDesign"]["bridge"] = "breathiness 30-40; closer vocal"
    findings = v061_track_findings(row, {"lyricLanguage": "japanese"})
    assert "vocal_design_consistency" in {x["area"] for x in findings}


def test_v061_order_requires_bpm_groove_before_singer_lock():
    row = _jp_male_source()["songs"][0]
    row["stylePrompt"] = (
        "Chill Rap, jazz-hop tint, 96 BPM; HARD LOCK young Japanese male tenor only; "
        "relaxed head-nod pocket; VOICE close-mic JP-native diction, mora timing, natural sentence accent; "
        "RAP Verse40-55% half-rap; soft kick, dry rim, moving bass; Rhodes; Hook H melodic; "
        "Bridge drums thin; Final A+B; Money H I-V-vi-IV; SCENE cafe-window; 2:45-3:30."
    )
    findings = v061_track_findings(row, {"lyricLanguage": "japanese"})
    assert "prompt_ordering" in {x["area"] for x in findings}


def test_analyzer_surfaces_v061_cross_field_findings():
    source = _jp_male_source()
    source["songs"][0]["vocalDesign"]["verse"] = "breathiness 35-45"
    analysis = analyze_current_prompt(source)
    areas = {x["area"] for x in analysis["tracks"][0]["weaknesses"]}
    assert "vocal_design_consistency" in areas


def test_result_gate_rejects_missing_jp_controls_and_voice_conflict():
    source = _jp_male_source()
    row = source["songs"][0]
    row["stylePrompt"] = row["stylePrompt"].replace("close-mic ", "").replace("JP-native diction, mora timing, natural sentence accent; ", "")
    row["vocalDesign"]["verse"] = "breathiness 35-45"
    codes = {x["code"] for x in v061_result_failures(row, source["meta"])}
    assert "JP_NATIVE_POSITIVE_CONTROLS_MISSING" in codes
    assert "VOCAL_DESIGN_CONFLICT" in codes


def test_finalizer_blocks_v06_style_conflict_until_v061_fixed():
    source = _jp_male_source()
    upgraded = json.loads(json.dumps(source, ensure_ascii=False))
    for old, row in zip(source["songs"], upgraded["songs"]):
        row["stylePrompt"] = row["stylePrompt"].replace("JP-native diction, mora timing, natural sentence accent; ", "")
        row["vocalDesign"]["verse"] = "breathiness 35-45"
        row["promptOptimization"] = {
            "status": "IMPROVED",
            "changedFields": ["stylePrompt", "vocalDesign"],
            "resolvedWeaknesses": [],
            "remainingWeaknesses": [],
            "changeReasons": ["test"],
            "expectedImprovements": ["test"],
            "oldStylePrompt": old["stylePrompt"],
            "newStylePrompt": row["stylePrompt"],
            "oldExcludePrompt": old["excludePrompt"],
            "newExcludePrompt": row["excludePrompt"],
        }
    _, issues = finalize_existing_upgrade(json.dumps(source, ensure_ascii=False), json.dumps(upgraded, ensure_ascii=False), "Chill Rap")
    codes = {x["code"] for x in issues if x.get("level") == "FAIL"}
    assert "JP_NATIVE_POSITIVE_CONTROLS_MISSING" in codes or "VOCAL_DESIGN_CONFLICT" in codes


def test_english_lyric_tokyo_channel_does_not_require_jp_native_controls():
    source = _jp_male_source()
    source["meta"]["lyricLanguage"] = "english"
    source["meta"]["channelLabel"] = "Tokyo Chill Love Story"
    row = source["songs"][0]
    row["stylePrompt"] = row["stylePrompt"].replace(
        "JP-native diction, mora timing, natural sentence accent; ",
        "natural connected English, relaxed consonants, idiomatic reductions; ",
    )
    findings = v061_track_findings(row, source["meta"])
    assert "jp_native_positive_controls" not in {x["area"] for x in findings}


def _jp_female_source():
    source = _jp_male_source()
    source["meta"]["vocalAllocation"] = {"Female Solo": 15, "Male Solo": 0, "Duet": 0, "Mixed": 0}
    for row in source["songs"]:
        row["vocalType"] = "Female Solo"
        row["stylePrompt"] = (
            "Chill Rap, jazz-hop tint, 96 BPM relaxed head-nod pocket; "
            "HARD LOCK recurring young Japanese female light-mezzo only, no male/duet; "
            "VOICE close-mic supported clear core, breath 15-30%, dry husky grain 5-15%; "
            "JP-native diction, mora timing, natural sentence accent; "
            "RAP Verse45-60% half-rap, syncopated pickups; soft kick, dry rim, moving bass; Rhodes; "
            "Hook H melodic; Bridge drums thin; Final A+B clipped self-response; "
            "Money H I-V-vi-IV; SCENE cafe-window; 2:45-3:30."
        )
        row["vocalDesign"] = {
            "genderLock": "Female Solo 15/15; male lead/backing/response 0; duet 0",
            "base": "young Japanese female light-mezzo, close-mic clear core, breath 15-30%, dry husky grain 5-15%",
            "verse": "same singer, 45-60% half-rap",
            "chorus": "same singer, brighter hook",
            "bridge": "same singer, closer/drier",
            "final": "same singer, female self-response only; no male backing or giant vocal stack",
        }
        row["highlightDesign"] = {"specificCue": "Final A+B clipped self-response", "vocalRule": "female self-response only; no male backing"}
        row["finalDesign"] = {"specificCue": "Final A+B clipped self-response", "vocalRule": "female self-response only"}
        row["moneyChordDesign"] = {"executionRule": "warm cadence and female self-response; no giant vocal stack"}
        row["generationRunHint"] = "FULL REGEN for male contamination"
        row["lyrics"] = "[Verse]\n歌詞\n[Final B - Variation / Female Self-Response]\n続き"
    return source


def test_female_voice_isolation_detects_wrong_gender_and_multivoice_tokens():
    source = _jp_female_source()
    findings = v061_track_findings(source["songs"][0], source["meta"])
    areas = {x["area"] for x in findings}
    assert "female_voice_isolation" in areas


def test_female_voice_isolation_accepts_affirmative_single_voice_controls():
    source = _jp_female_source()
    row = source["songs"][0]
    row["stylePrompt"] = (
        "Chill Rap, jazz-hop tint, 96 BPM relaxed head-nod pocket; "
        "SOLO FEMALE ONLY, same young Japanese light-mezzo, single unlayered lead throughout; "
        "VOICE close-mic supported clear core, breath 15-30%, dry husky grain 5-15%; "
        "JP-native diction, mora timing, natural sentence accent; "
        "RAP Verse45-60% half-rap; soft kick, dry rim, moving bass; Rhodes; "
        "Hook H melodic; Bridge drums thin; Final A+B same-solo-female tag; "
        "Money H I-V-vi-IV; SCENE cafe-window; 2:45-3:30."
    )
    row["vocalDesign"] = {
        "genderLock": "One recurring Japanese female solo singer throughout; identical female timbre in every section",
        "base": "young Japanese female light-mezzo, close-mic clear core, breath 15-30%, dry husky grain 5-15%",
        "verse": "same single singer, 45-60% half-rap",
        "chorus": "same single singer, brighter hook",
        "bridge": "same single singer, closer/drier",
        "final": "same single singer, Final B remains one unlayered solo female lead",
    }
    row["highlightDesign"] = {"specificCue": "Final A+B same-solo-female tag", "vocalRule": "identical solo female voice, one unlayered lead"}
    row["finalDesign"] = {"specificCue": "Final A+B same-solo-female tag", "vocalRule": "identical single solo female voice"}
    row["moneyChordDesign"] = {"executionRule": "warmer cadence with the identical solo female lead"}
    row["generationRunHint"] = "FULL REGEN for wrong-gender voice"
    findings = v061_track_findings(row, source["meta"])
    assert "female_voice_isolation" not in {x["area"] for x in findings}


def test_female_section_label_normalization_changes_label_only():
    original = "[Verse]\n歌詞本文\n[Final B - Variation / Female Self-Response]\n最後の歌詞"
    normalized = normalize_female_section_labels(original)
    assert "[Final B - Variation / Same Solo Female Voice]" in normalized
    assert normalized.replace("[Final B - Variation / Same Solo Female Voice]", "") == original.replace("[Final B - Variation / Female Self-Response]", "")
    assert female_section_labels_equivalent(original, normalized)


def test_finalizer_auto_normalizes_female_vocal_section_label():
    source = _jp_female_source()
    upgraded = json.loads(json.dumps(source, ensure_ascii=False))
    for old, row in zip(source["songs"], upgraded["songs"]):
        # Make all positive controls safe so the only remaining repair is the
        # program-owned bracket-label normalization.
        row["stylePrompt"] = (
            "Chill Rap, jazz-hop tint, 96 BPM relaxed head-nod pocket; "
            "SOLO FEMALE ONLY, same young Japanese light-mezzo, single unlayered lead throughout; "
            "VOICE close-mic supported clear core, breath 15-30%, dry husky grain 5-15%; "
            "JP-native diction, mora timing, natural sentence accent; RAP Verse45-60% half-rap; "
            "soft kick, dry rim, moving bass; Rhodes; Hook H melodic; Bridge drums thin; "
            "Final A+B same-solo-female tag; Money H I-V-vi-IV; SCENE cafe-window; 2:45-3:30."
        )
        row["vocalDesign"] = {
            "genderLock": "One recurring Japanese female solo singer throughout; identical female timbre in every section",
            "base": "young Japanese female light-mezzo, close-mic clear core, breath 15-30%, dry husky grain 5-15%",
            "verse": "same single singer, 45-60% half-rap",
            "chorus": "same single singer, brighter hook",
            "bridge": "same single singer, closer/drier",
            "final": "same single singer, Final B remains one unlayered solo female lead",
        }
        row["highlightDesign"] = {"specificCue": "Final A+B same-solo-female tag", "vocalRule": "identical solo female voice, one unlayered lead"}
        row["finalDesign"] = {"specificCue": "Final A+B same-solo-female tag", "vocalRule": "identical single solo female voice"}
        row["moneyChordDesign"] = {"executionRule": "warmer cadence with the identical solo female lead"}
        row["generationRunHint"] = "FULL REGEN for wrong-gender voice"
        row["excludePrompt"] = "male lead; generic airy AI female pop; mature contralto; whisper-only; falsetto hero; non-native Japanese; R&B ballad; hard trap; festival EDM; early fade"
        row["performanceSignature"] = "track-specific pickup/rest pattern"
        row["promptOptimization"] = {
            "status": "IMPROVED",
            "changedFields": [],
            "resolvedWeaknesses": [],
            "remainingWeaknesses": [],
            "changeReasons": ["test"],
            "expectedImprovements": ["test"],
            "oldStylePrompt": old["stylePrompt"],
            "newStylePrompt": row["stylePrompt"],
            "oldExcludePrompt": old["excludePrompt"],
            "newExcludePrompt": row["excludePrompt"],
        }
    # We only need to prove the merge-level label sanitation itself here.
    from core.workflows import merge_existing_upgrade
    final = merge_existing_upgrade(json.dumps(source, ensure_ascii=False), json.dumps(upgraded, ensure_ascii=False))
    assert all("[Final B - Variation / Same Solo Female Voice]" in row["lyrics"] for row in final["songs"])
