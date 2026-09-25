import json

from core.learning import analyze_research_abc_results

from core.research_prompt_engine import (
    VARIANT_IDS,
    apply_research_candidate_variant,
    build_research_candidate_pack,
    load_research_knowledge,
    load_style_compatibility,
)


def _source():
    songs = []
    for i in range(1, 16):
        female = i % 2 == 0
        vocal_type = "Female Solo" if female else "Male Solo"
        hard = (
            "HARD LOCK one young-adult female lead only"
            if female else
            "HARD LOCK one young-adult male lead only"
        )
        signature = (
            "CHANNEL SIGNATURE: close-mic speech-forward light mezzo, bright-forward resonance, clipped endings"
            if female else
            "CHANNEL SIGNATURE: close-mic speech-forward warm-light chest, forward oral resonance, clipped endings"
        )
        songs.append({
            "trackNo": i,
            "title": f"TITLE-{i}",
            "lyrics": f"LYRICS-{i}",
            "hookPhrase": f"HOOK-{i}",
            "story": f"STORY-{i}",
            "scene": f"SCENE-{i}",
            "BPM": 96 + (i % 4),
            "genreText": "Chill Rap / lo-fi soul tint",
            "vocalType": vocal_type,
            "stylePrompt": (
                f"Chill Rap, lo-fi soul tint, {96 + (i % 4)} BPM dry head-nod; "
                f"{hard}; {signature}; "
                "ACTIVE RAP: syncopated half-rap, micro-rests, slight behind-beat release; "
                "soft kick, dry rim, light hats, clean guitar, warm moving bass; "
                f"Hook “HOOK-{i}” melodic; Bridge density drop; Final A+B full pocket; "
                "Money H I–V–vi–IV; full-length 3:05-3:25."
            ),
            "excludePrompt": "generic AI pop vocal; power belt; full R&B ballad; hard trap; festival EDM; early ending",
            "performanceSignature": f"track-{i} dry pickup and clipped ending",
            "harmonicDesign": "I–V–vi–IV with add9 warmth and a clear final cadence",
            "bridgeDesign": {
                "specificCue": "drums thin; bass movement reduces; vocal closer/drier",
                "minimumContrastAxes": 3,
            },
            "highlightDesign": {
                "specificCue": "full pocket return with root-bass cadence",
                "finalHarmony": "I–V–vi–IV → ii7–V7–Imaj7",
            },
            "durationDesign": {"preferred": "3:10-3:25", "hardRange": "2:45-3:30"},
        })
    songs[-1]["vocalType"] = "Male-Female Duet"
    songs[-1]["stylePrompt"] = songs[-1]["stylePrompt"].replace(
        "HARD LOCK one young-adult male lead only",
        "HARD LOCK exactly two young-adult leads, one male + one female"
    )
    return {
        "meta": {
            "sunoModelTarget": "v6",
            "genrePolicy": "Chill Rap",
            "episodeTitle": "EP002",
        },
        "songs": songs,
    }


def test_research_knowledge_has_provenance_and_official_sources():
    knowledge = load_research_knowledge()
    assert knowledge["schemaVersion"] == 1
    source_ids = {x["id"] for x in knowledge["sources"]}
    assert {"suno_v6_faq", "suno_inspire", "suno_style_influence", "suno_custom_models"} <= source_ids
    assert any(x["type"] == "official" for x in knowledge["sources"])
    assert any(x["type"] == "community" for x in knowledge["sources"])
    assert all(x.get("sourceIds") for x in knowledge["rules"])


def test_style_matrix_has_all_current_genres_and_one_tint_policy():
    matrix = load_style_compatibility()
    assert matrix["policy"]["maxSecondaryTints"] == 1
    assert set(("chill_rap", "old_pop_ballad", "soul", "cafe_pop", "chanson", "deep_house")) <= set(matrix["genres"])
    assert "lo-fi soul" in matrix["genres"]["chill_rap"]["stableTints"]


def test_candidate_pack_builds_three_research_arms_for_all_tracks():
    source = _source()
    pack = build_research_candidate_pack(source, "chill_rap")
    assert pack["engineVersion"] == "0.6.0-dev"
    assert pack["candidatePolicy"]["onePrimaryAxisPerExperiment"] is True
    assert pack["candidatePolicy"]["noWinnerBeforeAudioFeedback"] is True
    assert len(pack["tracks"]) == 15
    for track in pack["tracks"]:
        candidates = track["candidates"]
        assert [x["variantId"] for x in candidates] == list(VARIANT_IDS)
        assert all(x["stylePrompt"].startswith("Chill Rap,") for x in candidates)
        assert all(len(x["stylePrompt"]) <= 900 for x in candidates)
        assert all(x["generationRecipe"]["model"] == "v6" for x in candidates)
        assert all(x["generationRecipe"]["variety"] == 0 for x in candidates)
        assert all(x["generationRecipe"]["maxMode"] is True for x in candidates)
        assert all(x["generationRecipe"]["styleInfluence"] == "Strong" for x in candidates)
        assert all(x["generationRecipe"]["inspire"]["playlistSize"].startswith("3-5") for x in candidates)


def test_candidate_arms_are_distinct_but_preserve_role_lock():
    source = _source()
    pack = build_research_candidate_pack(source, "chill_rap")
    for track in pack["tracks"]:
        prompts = {x["stylePrompt"] for x in track["candidates"]}
        assert len(prompts) == 3
        source_song = source["songs"][track["trackNo"] - 1]
        if source_song["vocalType"] == "Female Solo":
            assert all("female lead only" in x["stylePrompt"].lower() for x in track["candidates"])
        elif source_song["vocalType"] == "Male Solo":
            assert all("male lead only" in x["stylePrompt"].lower() for x in track["candidates"])
        else:
            assert all("exactly two young-adult leads" in x["stylePrompt"].lower() for x in track["candidates"])


def test_apply_variant_preserves_content_and_only_updates_music_prompt_plus_recipe():
    source = _source()
    original = json.loads(json.dumps(source, ensure_ascii=False))
    pack = build_research_candidate_pack(source, "chill_rap")
    result = apply_research_candidate_variant(source, pack, "C_CHARACTER")
    assert source == original
    assert len(result["songs"]) == 15
    for old, new in zip(source["songs"], result["songs"]):
        assert new["title"] == old["title"]
        assert new["lyrics"] == old["lyrics"]
        assert new["hookPhrase"] == old["hookPhrase"]
        assert new["story"] == old["story"]
        assert new["scene"] == old["scene"]
        assert new["stylePrompt"] != old["stylePrompt"]
        assert new["researchRecipe"]["variantId"] == "C_CHARACTER"
        assert new["researchRecipe"]["primaryAxis"] == "performance_character"
        assert new["researchRecipe"]["feedbackBinding"]["experiment_arm"] == "C_CHARACTER"
        assert new["researchRecipe"]["feedbackBinding"]["experiment_axis"] == "performance_character"


def test_groove_arm_changes_secondary_direction_without_changing_model_settings():
    source = _source()
    pack = build_research_candidate_pack(source, "chill_rap")
    first = pack["tracks"][0]["candidates"]
    a = next(x for x in first if x["variantId"] == "A_CONTROL")
    b = next(x for x in first if x["variantId"] == "B_GROOVE")
    assert a["stylePrompt"] != b["stylePrompt"]
    assert a["generationRecipe"] == {**b["generationRecipe"], "variant": "A_CONTROL"}
    assert b["primaryAxis"] == "groove_and_secondary_tint"


def test_research_abc_feedback_analysis_is_descriptive_and_never_auto_applies():
    rows = []
    for variant, axis, base in (
        ("A_CONTROL", "control_baseline", 4),
        ("B_GROOVE", "groove_and_secondary_tint", 5),
        ("C_CHARACTER", "performance_character", 5),
    ):
        for i in range(5):
            rows.append({
                "experiment_arm": variant,
                "experiment_axis": axis,
                "decision": "KEEP" if base >= 5 else "MAYBE",
                "overall": base,
                "vocal_identity": base,
                "hook": base,
                "groove": base,
                "prompt_adherence": base,
            })
    result = analyze_research_abc_results(rows, min_per_variant=5, min_per_axis=3)
    assert result["active"] is True
    assert result["descriptiveSignalOnly"] is True
    assert result["policy"]["declareWinner"] is False
    assert result["policy"]["autoApply"] is False
    assert result["policy"]["autoMasterRewrite"] is False
    assert {x["variant"] for x in result["variants"]} == {"A_CONTROL", "B_GROOVE", "C_CHARACTER"}
    assert {x["axis"] for x in result["byAxis"]} >= {"groove_and_secondary_tint", "performance_character"}


def test_research_abc_feedback_stays_inactive_with_tiny_samples():
    rows = [
        {
            "experiment_arm": "A_CONTROL",
            "experiment_axis": "control_baseline",
            "decision": "KEEP",
            "overall": 5,
            "vocal_identity": 5,
            "hook": 5,
            "groove": 5,
            "prompt_adherence": 5,
        },
        {
            "experiment_arm": "B_GROOVE",
            "experiment_axis": "groove_and_secondary_tint",
            "decision": "KEEP",
            "overall": 5,
            "vocal_identity": 5,
            "hook": 5,
            "groove": 5,
            "prompt_adherence": 5,
        },
        {
            "experiment_arm": "C_CHARACTER",
            "experiment_axis": "performance_character",
            "decision": "KEEP",
            "overall": 5,
            "vocal_identity": 5,
            "hook": 5,
            "groove": 5,
            "prompt_adherence": 5,
        },
    ]
    result = analyze_research_abc_results(rows, min_per_variant=5)
    assert result["active"] is False
    assert result["policy"]["requiresAudioFeedback"] is True
