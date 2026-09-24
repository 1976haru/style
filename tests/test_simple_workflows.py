import json

from core.workflows import (
    build_existing_json_upgrade_instruction,
    build_haru_txt_instruction,
    finalize_existing_upgrade,
    finalize_haru_result,
    validate_master_compatibility,
)


def _source():
    return {
        "meta": {
            "storyPov": "male",
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
                "listenerSituation": f"SCENE-{i}",
                "lyrics": f"[Verse]\\nLYRICS-{i}",
                "BPM": 96,
                "trackRole": "general",
                "vocalType": "Male Solo",
                "stylePrompt": f"Chill Rap, OLD-{i}",
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


def test_wrong_instrumental_master_is_blocked_for_male_source():
    source = _source()
    bad = "Sleep BGM / Healing Piano / Ambient\\nInstrumental only\\nno lead vocal"
    result = validate_master_compatibility(source, bad)
    assert result["ok"] is False
    assert any("Instrumental" in x for x in result["errors"])


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
        row["stylePrompt"] = "Chill Rap, NEW MASTER PROMPT"
        row["vocalType"] = "Male Solo"
        row["performanceSignature"] = "speech-forward dry pickup"
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
        assert row["youtube"] == {"title": f"YT-{i}"}
        assert row["customField"] == {"keep": i}
        assert row["BPM"] == 100
        assert row["stylePrompt"] == "Chill Rap, NEW MASTER PROMPT"


def test_haru_instruction_requires_complete_suno_json():
    txt = "EP002 / 15 tracks / rain under one umbrella"
    inst = build_haru_txt_instruction(txt, MALE_MASTER)
    assert "완성형 JSON" in inst
    assert "lyrics" in inst
    assert "stylePrompt" in inst
    assert txt in inst


def test_finalize_haru_requires_title_lyrics_prompt():
    source = _source()
    result, issues = finalize_haru_result(json.dumps(source, ensure_ascii=False))
    assert len(result["songs"]) == 15
    assert all(x["level"] != "FAIL" for x in issues)
