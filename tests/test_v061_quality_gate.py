import json

from core.prompt_intelligence import analyze_current_prompt
from core.v061_quality_gate import japanese_positive_controls, v061_result_failures, v061_track_findings
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
