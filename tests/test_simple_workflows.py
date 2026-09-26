import json
from pathlib import Path

from core.workflows import (
    build_existing_json_upgrade_instruction,
    build_haru_txt_instruction,
    finalize_existing_upgrade,
    finalize_haru_result,
    validate_master_compatibility,
    detect_source_profile,
)
from core.master_registry import (
    build_active_master,
    default_registry,
    load_genre_profiles,
    load_master_registry,
    read_registered_master,
    register_master,
    save_master_registry,
)


def _source():
    return {
        "meta": {
            "storyPov": "male",
            "sunoModelTarget": "v6",
            "channelLabel": "Tokyo Chill Love Story",
            "genrePolicy": "All stylePrompts start with Chill Rap",
            "episodeTitle": "傘を閉じたくなかった",
        },
        "songs": [
            {
                "trackNo": i,
                "title": f"TITLE-{i}",
                "titleLocalized": f"TITLE-{i}",
                "hookPhrase": f"HOOK-{i}",
                "story": f"STORY-{i}",
                "storyAct": f"ACT-{i}",
                "scene": f"SCENE-RAW-{i}",
                "listenerSituation": f"SCENE-{i}",
                "emotionArc": f"EMOTION-{i}",
                "centralImage": f"IMAGE-{i}",
                "seasonMoment": f"SEASON-{i}",
                "distinctChoice": f"CHOICE-{i}",
                "lyrics": f"[Verse]\\nLYRICS-{i}",
                "BPM": 96,
                "trackRole": "general",
                "vocalType": "Male Solo",
                "stylePrompt": (
                    f"Chill Rap, 98 BPM; recurring male speech-forward tenor, supported warm chest and dry grain; "
                    f"syncopated pocket; dry rim and light hats; moving bass; palette{i:02d} Rhodes and muted guitar; "
                    f"narrow rhythmic Verse; melodic Chorus lift; Hook money chord I–V–vi–IV; "
                    f"Bridge bridgecue{i:02d} drops hats, bass holds roots, vocal moves closer on IVmaj7–iv6–Imaj7; "
                    f"Final A+B finalcue{i:02d} restores full pocket with root-bass cadence on I–V–vi–IV → ii7–V7–Imaj7; "
                    f"section length 3:00-3:30; exclude early ending"
                ),
                "moneyChordDesign": {
                    "hook": ["I–V–vi–IV", "vi–IV–I–V"],
                    "bridge": ["IVmaj7–iv6–Imaj7"],
                    "finalHighlight": ["I–V–vi–IV", "ii7–V7–Imaj7"],
                },
                "excludePrompt": "; ".join(f"legacy failure category {n}" for n in range(37)),
                "performanceSignature": f"pickup{i:02d} dry immediate attack; articulation{i:02d}; ending{i:02d} clipped release",
                "durationDesign": "3:00-3:30",
                "generationRunHint": "reject early ending",
                "bridgeDesign": "drop kick and rim; sparse root bass; close-mic return before Final",
                "finalDesign": "full backbeat return; doubled hook only on final two lines",
                "youtube": {"title": f"YT-{i}"},
                "customField": {"keep": i},
            }
            for i in range(1, 16)
        ],
    }


MALE_MASTER = """
日本語 CHILI LAB 男性 master v15.0
彼のSTORY / Male Solo ONLY
All stylePrompt must start exactly with Chill Rap,
Core 92~100
Anchor 96~104
Memory 84~92
"""


def test_existing_upgrade_instruction_contains_full_source_and_master():
    source = _source()
    inst, compat = build_existing_json_upgrade_instruction(
        json.dumps(source, ensure_ascii=False), MALE_MASTER
    )
    assert compat["ok"] is True
    assert "LYRICS-15" in inst
    assert "Male Solo ONLY" in inst
    assert "structured_track_plan" in inst
    assert "[CHANNEL / VOCAL MASTER]" in inst
    assert "[SELECTED GENRE MASTER]" in inst
    assert '"id": "chill_rap"' in inst
    assert "[PRECEDENCE]" in inst


def test_existing_upgrade_selected_genre_is_explicit():
    inst, _ = build_existing_json_upgrade_instruction(
        json.dumps(_source(), ensure_ascii=False), MALE_MASTER, "Deep House"
    )
    assert '"id": "deep_house"' in inst
    assert "four-on-the-floor" in inst
    assert "extended payoff/outro" in inst


def test_source_profile_detects_male_female_dual_and_senior():
    male = _source()
    assert detect_source_profile(male)["sourceType"] == "남성"
    female = json.loads(json.dumps(male))
    female["meta"]["storyPov"] = "female"
    for row in female["songs"]:
        row["vocalType"] = "Female Solo"
    assert detect_source_profile(female)["sourceType"] == "여성"
    dual = json.loads(json.dumps(male))
    dual["meta"]["storyPov"] = "dual"
    dual["songs"][0]["vocalType"] = "Male-Female Duet"
    assert detect_source_profile(dual)["sourceType"] == "두사람"
    senior = json.loads(json.dumps(male))
    senior["meta"]["channelLabel"] = "시니어 채널"
    senior["meta"]["genrePolicy"] = "Soft Old Pop Ballad"
    assert detect_source_profile(senior)["sourceType"] == "시니어"
    assert detect_source_profile(male)["channelId"] == "chili_male"
    assert detect_source_profile(male)["genreHint"] == "Chill Rap"


def test_registry_save_load_register_and_automatic_reuse():
    registry_path = Path(__file__).resolve().parents[1] / ".test_master_registry.json"
    master_path = Path(__file__).resolve().parents[1] / ".test_male_master.txt"
    try:
        master_path.write_text(MALE_MASTER, encoding="utf-8")
        save_master_registry(default_registry(), registry_path)
        assert load_master_registry(registry_path)["channelMasters"]["chili_male"]["path"] == ""
        register_master("chili_male", master_path, registry_path)
        first_text, first_path = read_registered_master("chili_male", registry_path)
        second_text, second_path = read_registered_master("chili_male", registry_path)
        assert first_text == second_text == MALE_MASTER
        assert first_path == second_path == master_path.resolve()
    finally:
        for path in (registry_path, master_path):
            if path.exists():
                path.unlink()


def test_genre_master_profiles_are_materially_distinct():
    profiles = load_genre_profiles()
    chill = profiles["chill_rap"]
    old = profiles["old_pop_ballad"]
    deep = profiles["deep_house"]
    assert set(("chill_rap", "old_pop_ballad", "soul", "cafe_pop", "chanson", "deep_house")) <= set(profiles)
    assert chill["bpm"] == {"min": 88, "max": 108}
    assert old["bpm"] == {"min": 72, "max": 92}
    assert deep["bpm"] == {"min": 116, "max": 124}
    assert chill["bridge"] != old["bridge"] != deep["bridge"]
    assert chill["final"] != old["final"] != deep["final"]
    assert chill["stylePromptRules"] != old["stylePromptRules"] != deep["stylePromptRules"]
    assert chill["excludeRules"] != old["excludeRules"] != deep["excludeRules"]


def test_active_master_contains_full_blocks_and_precedence():
    profile = load_genre_profiles()["deep_house"]
    active = build_active_master(MALE_MASTER, profile, detect_source_profile(_source()))
    assert "[CHANNEL / VOCAL MASTER]" in active
    assert "[SELECTED GENRE MASTER]" in active
    assert "Channel vocal identity and hard locks override genre defaults." in active
    assert "116" in active and "124" in active


def test_wrong_instrumental_master_is_blocked_for_male_source():
    source = _source()
    bad = "Sleep BGM / Healing Piano / Ambient\\nInstrumental only\\nno lead vocal"
    result = validate_master_compatibility(source, bad)
    assert result["ok"] is False
    assert any("Instrumental" in x for x in result["errors"])


def test_wrong_male_female_dual_masters_are_blocked():
    male = _source()
    female_master = "CHILI female-only / Female Solo / 彼女 / Chill Rap"
    assert validate_master_compatibility(male, female_master)["ok"] is False
    female = json.loads(json.dumps(male))
    female["meta"]["storyPov"] = "female"
    for row in female["songs"]:
        row["vocalType"] = "Female Solo"
    assert validate_master_compatibility(female, MALE_MASTER)["ok"] is False
    dual = json.loads(json.dumps(male))
    dual["meta"]["storyPov"] = "dual"
    dual["songs"][0]["vocalType"] = "Male-Female Duet"
    assert validate_master_compatibility(dual, MALE_MASTER)["ok"] is False


def test_finalize_existing_preserves_content_and_full_schema_but_updates_music():
    source = _source()
    upgraded = json.loads(json.dumps(source))
    for row in upgraded["songs"]:
        row["title"] = "CHANGED"
        row["hookPhrase"] = "CHANGED"
        row["lyrics"] = "CHANGED"
        row["listenerSituation"] = "CHANGED"
        row["youtube"] = {}
        row["customField"] = {}
        row["BPM"] = 100
        row["excludePrompt"] = "; ".join([
            "female or duet contamination", "generic polished male-pop tenor", "K-pop idol belt",
            "dark mature crooner", "whisper-only vocal", "falsetto-led hook/final", "rock rasp or gravel",
            "non-native Japanese pronunciation", "fully sung R&B Verse", "hard trap or drill",
            "festival EDM", "static bass",
        ])
        row["performanceSignature"] = "speech-forward dry pickup"
        row["promptOptimization"] = {
            "status": "IMPROVED",
            "changedFields": ["BPM", "excludePrompt", "performanceSignature"],
            "resolvedWeaknesses": ["exclude_efficiency"],
            "remainingWeaknesses": [],
            "changeReasons": ["Condensed overlapping exclusion categories", "Added a track-specific dry pickup cue"],
            "expectedImprovements": ["Lower instruction dilution", "Cleaner channel-specific failure prevention"],
            "oldStylePrompt": source["songs"][row["trackNo"] - 1]["stylePrompt"],
            "newStylePrompt": row["stylePrompt"],
            "oldExcludePrompt": source["songs"][row["trackNo"] - 1]["excludePrompt"],
            "newExcludePrompt": row["excludePrompt"],
        }
    final, issues = finalize_existing_upgrade(
        json.dumps(source, ensure_ascii=False),
        json.dumps(upgraded, ensure_ascii=False),
    )
    assert all(x["level"] != "FAIL" for x in issues)
    assert len(final["songs"]) == 15
    for i, row in enumerate(final["songs"], 1):
        assert row["title"] == f"TITLE-{i}"
        assert row["hookPhrase"] == f"HOOK-{i}"
        assert row["lyrics"] == f"[Verse]\\nLYRICS-{i}"
        assert row["listenerSituation"] == f"SCENE-{i}"
        assert row["story"] == f"STORY-{i}"
        assert row["storyAct"] == f"ACT-{i}"
        assert row["scene"] == f"SCENE-RAW-{i}"
        assert row["emotionArc"] == f"EMOTION-{i}"
        assert row["centralImage"] == f"IMAGE-{i}"
        assert row["seasonMoment"] == f"SEASON-{i}"
        assert row["distinctChoice"] == f"CHOICE-{i}"
        assert row["youtube"] == {"title": f"YT-{i}"}
        assert row["customField"] == {"keep": i}
        assert row["BPM"] == 100
        assert row["stylePrompt"] == source["songs"][i - 1]["stylePrompt"]
        assert row["promptOptimization"]["changeReasons"]
    assert final["promptOptimizationReport"]["immutableFieldsVerified"] is True
    assert len(final["promptOptimizationReport"]["comparisons"]) == 15
    assert final["promptOptimizationReport"]["changedFieldCounts"]["excludePrompt"] == 15


def test_haru_instruction_requires_complete_suno_json():
    txt = "EP002 / 15 tracks / rain under one umbrella"
    inst = build_haru_txt_instruction(txt, MALE_MASTER)
    assert "완성형 JSON" in inst
    assert "lyrics" in inst
    assert "stylePrompt" in inst
    assert txt in inst
    assert '"id": "chill_rap"' in inst


def test_haru_instruction_uses_selected_channel_and_genre():
    inst = build_haru_txt_instruction(
        "senior episode brief", MALE_MASTER, 15, "senior", "Soft Old Pop Ballad"
    )
    assert '"channelId": "senior"' in inst
    assert '"id": "old_pop_ballad"' in inst
    assert "warm natural instruments" in inst


def test_finalize_haru_requires_title_lyrics_prompt():
    source = _source()
    result, issues = finalize_haru_result(json.dumps(source, ensure_ascii=False))
    assert len(result["songs"]) == 15
    assert all(x["level"] != "FAIL" for x in issues)
