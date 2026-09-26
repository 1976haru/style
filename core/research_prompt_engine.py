from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KNOWLEDGE_PATH = ROOT / "data" / "research_prompt_knowledge.json"
DEFAULT_COMPATIBILITY_PATH = ROOT / "data" / "style_compatibility_matrix.json"

VARIANT_IDS = ("A_CONTROL", "B_GROOVE", "C_CHARACTER")


def _load_json(path: str | Path, label: str) -> Dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label}을 읽을 수 없습니다: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{label} 최상위는 JSON object여야 합니다.")
    return data


def load_research_knowledge(path: str | Path = DEFAULT_KNOWLEDGE_PATH) -> Dict[str, Any]:
    data = _load_json(path, "Research Prompt Knowledge")
    if not isinstance(data.get("sources"), list) or not isinstance(data.get("rules"), list):
        raise ValueError("research_prompt_knowledge.json에 sources/rules 배열이 필요합니다.")
    return deepcopy(data)


def load_style_compatibility(path: str | Path = DEFAULT_COMPATIBILITY_PATH) -> Dict[str, Any]:
    data = _load_json(path, "Style Compatibility Matrix")
    if not isinstance(data.get("genres"), dict) or not data["genres"]:
        raise ValueError("style_compatibility_matrix.json에 genres object가 필요합니다.")
    return deepcopy(data)


def _songs(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    for key in ("songs", "tracks", "preassignedSongs"):
        rows = source.get(key)
        if isinstance(rows, list):
            return [x for x in rows if isinstance(x, dict)]
    return []


def _song_key(source: Dict[str, Any]) -> str:
    for key in ("songs", "tracks", "preassignedSongs"):
        if isinstance(source.get(key), list):
            return key
    return "songs"


def _compact(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _clip(value: Any, limit: int) -> str:
    text = _compact(value)
    if len(text) <= limit:
        return text
    shortened = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:/")
    return shortened or text[:limit]


def _dict_text(value: Any, keys: tuple[str, ...]) -> str:
    if isinstance(value, dict):
        parts = [_compact(value.get(key)) for key in keys if _compact(value.get(key))]
        return "; ".join(parts)
    if isinstance(value, list):
        return "; ".join(_compact(x) for x in value if _compact(x))
    return _compact(value)


def _find_atom(style: str, needle: str) -> str:
    for atom in [x.strip() for x in re.split(r"[;|]+", style or "") if x.strip()]:
        if needle.casefold() in atom.casefold():
            return atom
    return ""


def _detect_genre_id(source: Dict[str, Any], matrix: Dict[str, Any], selected_genre_id: str = "auto") -> str:
    if selected_genre_id and selected_genre_id != "auto":
        if selected_genre_id not in matrix["genres"]:
            raise ValueError(f"지원하지 않는 research genre id: {selected_genre_id}")
        return selected_genre_id
    rows = _songs(source)
    blob = " ".join(
        _compact(row.get("genreText")) + " " + _compact(row.get("stylePrompt"))
        for row in rows[:5]
    ).casefold()
    for genre_id, profile in matrix["genres"].items():
        label = _compact(profile.get("label")).casefold()
        if label and label in blob:
            return genre_id
    if "chill rap" in blob:
        return "chill_rap"
    raise ValueError("Research Engine이 장르를 자동 감지하지 못했습니다. 장르를 직접 선택하세요.")


def _current_tint(style: str, profile: Dict[str, Any]) -> str:
    low = (style or "").casefold()
    for tint in profile.get("stableTints", []):
        if str(tint).casefold() in low:
            return str(tint)
    first = [x.strip() for x in (style or "").split(",")[:3] if x.strip()]
    for atom in first[1:]:
        if "bpm" not in atom.casefold() and len(atom) <= 60:
            return re.sub(r"\s+tint$", "", atom, flags=re.I)
    return str((profile.get("stableTints") or [""])[0])


def _alternate_tint(current: str, profile: Dict[str, Any], track_no: int) -> str:
    tints = [str(x) for x in profile.get("stableTints", []) if str(x).strip()]
    if not tints:
        return current
    candidates = [x for x in tints if x.casefold() != current.casefold()] or tints
    return candidates[(max(track_no, 1) - 1) % len(candidates)]


def _role_lock(song: Dict[str, Any]) -> str:
    # Role comes from explicit vocalType before any legacy HARD LOCK atom. This
    # prevents old negative wording ("no male/duet") from leaking into positive
    # female-only research prompts.
    vocal_type = _compact(song.get("vocalType"))
    low = vocal_type.casefold()
    if "female" in low and "male" in low:
        return "DUAL LOCK exactly two young-adult leads, one male and one female, fixed alternating roles"
    if "female" in low:
        return "SOLO FEMALE ONLY, one young-adult female singer throughout, same single unlayered lead in every section"
    if "male" in low:
        return "SOLO MALE ONLY, one young-adult male singer throughout, same single unlayered lead in every section"

    style = _compact(song.get("stylePrompt"))
    hard = _find_atom(style, "HARD LOCK")
    if hard:
        return _clip(hard, 150)
    return vocal_type or "preserve source vocal role"


def _voice_core(song: Dict[str, Any]) -> str:
    style = _compact(song.get("stylePrompt"))
    channel = _find_atom(style, "CHANNEL SIGNATURE")
    if channel:
        return _clip(channel, 220)
    vocal = song.get("vocalDesign")
    text = _dict_text(vocal, ("signature", "phonation", "coordinates", "base"))
    return _clip(text, 220)


def _performance(song: Dict[str, Any]) -> str:
    for value in (
        song.get("performanceSignature"),
        _dict_text(song.get("vocalDesign"), ("performance", "verse")),
        _dict_text(song.get("humanFeelDesign"), ("trackHabit", "timing")),
        _dict_text(song.get("phonationDesign"), ("trackHabit",)),
    ):
        if _compact(value):
            return _clip(value, 170)
    active = _find_atom(_compact(song.get("stylePrompt")), "ACTIVE RAP")
    return _clip(active, 170)


def _groove(song: Dict[str, Any], profile: Dict[str, Any], track_no: int, *, explore: bool = False) -> str:
    if explore:
        mods = [str(x) for x in profile.get("grooveModules", []) if str(x).strip()]
        if mods:
            return mods[(max(track_no, 1) - 1) % len(mods)]
    for key in ("grooveDesign", "groove", "chillRapDesign"):
        if _compact(song.get(key)):
            return _clip(song.get(key), 120)
    mods = profile.get("grooveModules") or ["controlled pocket"]
    return str(mods[0])


def _instrumentation(song: Dict[str, Any], profile: Dict[str, Any], track_no: int) -> str:
    current = _dict_text(song.get("instrumentationDesign") or song.get("instrumentation"), ("palette", "signature", "color"))
    if current:
        return _clip(current, 150)
    rhythm = ", ".join(str(x) for x in (profile.get("rhythmSection") or [])[:4])
    colors = [str(x) for x in profile.get("characterColors", []) if str(x).strip()]
    color = colors[(max(track_no, 1) - 1) % len(colors)] if colors else ""
    return _clip(", ".join(x for x in (rhythm, color) if x), 150)


def _harmony(song: Dict[str, Any]) -> str:
    for value in (
        song.get("harmonicDesign"),
        _dict_text(song.get("moneyChordDesign"), ("hook", "bridge", "finalHighlight")),
        song.get("moneyChordProgression"),
    ):
        if _compact(value):
            return _clip(value, 180)
    return ""


def _bridge(song: Dict[str, Any]) -> str:
    value = song.get("bridgeDesign")
    text = _dict_text(value, ("specificCue", "changeAxes", "purpose", "handoff"))
    return _clip(text, 150)


def _sanitize_female_positive_text(text: str) -> str:
    value = str(text or "")
    value = re.sub(r"\bfemale\s+self-(?:response|answer)\b", "same-solo-female tag", value, flags=re.I)
    value = re.sub(r"\bself-(?:response|answer)\b", "same-solo-female tag", value, flags=re.I)
    value = re.sub(r"\bself-double\b", "same-solo-female repeat", value, flags=re.I)
    value = re.sub(r"\b(?:giant\s+)?vocal\s+stack\b", "single unlayered female lead", value, flags=re.I)
    # Wrong-gender words belong in excludePrompt, not positive candidate text.
    value = re.sub(r"\bno\s+male(?:\s+backing)?\b", "", value, flags=re.I)
    value = re.sub(r"\bno\s+duet\b", "", value, flags=re.I)
    value = re.sub(r"\s{2,}", " ", value)
    value = re.sub(r"\s*[/,;]+\s*([,;])", r"\1 ", value)
    return value.strip(" ,;/;-")


def _final(song: Dict[str, Any]) -> str:
    value = song.get("highlightDesign") or song.get("finalDesign")
    vocal_type = _compact(song.get("vocalType")).casefold()
    if "female" in vocal_type and "male" not in vocal_type:
        text = _dict_text(value, ("specificCue", "finalHarmony", "structure"))
        return _clip(_sanitize_female_positive_text(text), 170)
    text = _dict_text(value, ("specificCue", "finalHarmony", "structure", "vocalRule"))
    return _clip(text, 170)


def _duration(song: Dict[str, Any]) -> str:
    value = song.get("durationDesign")
    text = _dict_text(value, ("preferred", "hardRange", "form"))
    return _clip(text, 90)


def _language_control(source: Dict[str, Any]) -> str:
    meta = source.get("meta") if isinstance(source.get("meta"), dict) else {}
    explicit_language = str(
        meta.get("lyricLanguage") or meta.get("language") or ""
    ).strip().casefold()
    if explicit_language in {"english", "en", "eng"}:
        return "ENGLISH close-mic natural connected English, relaxed consonants, idiomatic reductions, natural stress"
    if explicit_language in {"japanese", "ja", "jp", "jpn", "日本語"}:
        return "JP-NATIVE close-mic native Japanese diction, mora timing, natural sentence accent/pitch-accent feel"

    blob = " ".join([
        str(meta.get("channelId", "")),
        str(meta.get("channelLabel", "")),
    ]).casefold()
    if any(token in blob for token in ("japanese", "日本語", "jp-chili")):
        return "JP-NATIVE close-mic native Japanese diction, mora timing, natural sentence accent/pitch-accent feel"
    return ""


def _compose_prompt(
    genre_label: str,
    tint: str,
    bpm: Any,
    groove: str,
    role_lock: str,
    voice_core: str,
    language_control: str,
    performance: str,
    instrumentation: str,
    hook: str,
    bridge: str,
    final: str,
    harmony: str,
    duration: str,
    hard_max: int = 900,
) -> str:
    head = genre_label
    if tint:
        head += f", {tint} tint"
    if bpm not in (None, ""):
        head += f", {bpm} BPM"
    if groove:
        head += f" {groove}"
    atoms = [
        head,
        role_lock,
        voice_core,
        language_control,
        f"PERFORMANCE: {performance}" if performance else "",
        instrumentation,
        f"Hook “{hook}” melodic and immediately recognizable" if hook else "",
        f"Bridge: {bridge}" if bridge else "",
        f"Final: {final}" if final else "",
        f"Harmony: {harmony}" if harmony else "",
        f"Runtime: {duration}; no early ending" if duration else "no early ending",
    ]
    atoms = [_compact(x).strip(" ;") for x in atoms if _compact(x)]
    prompt = "; ".join(atoms)
    while len(prompt) > hard_max and len(atoms) > 5:
        # Remove the least essential tail atom first, preserving genre, role,
        # singer, performance and core arrangement.
        removable_order = [8, 9, 7, 6, 5]
        removed = False
        for idx in removable_order:
            if idx < len(atoms):
                atoms.pop(idx)
                removed = True
                break
        if not removed:
            break
        prompt = "; ".join(atoms)
    return _clip(prompt, hard_max)


def _generation_recipe(variant_id: str, model_target: str) -> Dict[str, Any]:
    return {
        "model": model_target or "v6",
        "variety": 0,
        "styleInfluence": "Strong",
        "maxMode": True,
        "inspire": {
            "recommended": True,
            "playlistSize": "3-5 approved user-made songs",
            "purpose": "channel identity / arrangement reference",
        },
        "customModel": {
            "considerWhen": "at least 6 approved channel tracks exist",
            "purpose": "recurring channel sound",
        },
        "experimentRule": "Keep model/settings constant; change only the candidate's primary prompt axis.",
        "variant": variant_id,
    }


def _candidate(
    *,
    variant_id: str,
    primary_axis: str,
    description: str,
    prompt: str,
    exclude: str,
    model_target: str,
    source_ids: List[str],
) -> Dict[str, Any]:
    return {
        "variantId": variant_id,
        "primaryAxis": primary_axis,
        "description": description,
        "stylePrompt": prompt,
        "excludePrompt": exclude,
        "generationRecipe": _generation_recipe(variant_id, model_target),
        "evidence": {
            "sourceIds": source_ids,
            "claimType": "experiment_direction_not_quality_prediction",
        },
    }


def build_research_candidate_pack(
    source: Dict[str, Any],
    genre_id: str = "auto",
    knowledge_path: str | Path = DEFAULT_KNOWLEDGE_PATH,
    compatibility_path: str | Path = DEFAULT_COMPATIBILITY_PATH,
) -> Dict[str, Any]:
    knowledge = load_research_knowledge(knowledge_path)
    matrix = load_style_compatibility(compatibility_path)
    rows = _songs(source)
    if not rows:
        raise ValueError("Research Engine 입력에 songs/tracks 배열이 필요합니다.")
    resolved_genre_id = _detect_genre_id(source, matrix, genre_id)
    profile = matrix["genres"][resolved_genre_id]
    genre_label = str(profile["label"])
    meta = source.get("meta") if isinstance(source.get("meta"), dict) else {}
    model_target = str(meta.get("sunoModelTarget") or "v6")

    track_packs = []
    for pos, song in enumerate(rows, 1):
        track_no = int(song.get("trackNo") or song.get("order") or pos)
        current_style = _compact(song.get("stylePrompt"))
        current_tint = _current_tint(current_style, profile)
        alt_tint = _alternate_tint(current_tint, profile, track_no)
        bpm = song.get("BPM", song.get("bpm", ""))
        role = _role_lock(song)
        voice = _voice_core(song)
        perf = _performance(song)
        instr = _instrumentation(song, profile, track_no)
        harmony = _harmony(song)
        bridge = _bridge(song)
        final = _final(song)
        duration = _duration(song)
        hook = _compact(song.get("hookPhrase") or song.get("hook") or song.get("title"))

        base_kwargs = dict(
            genre_label=genre_label, bpm=bpm, role_lock=role, voice_core=voice,
            language_control=_language_control(source),
            instrumentation=instr, hook=hook, bridge=bridge, final=final,
            harmony=harmony, duration=duration,
        )
        prompt_a = _compose_prompt(
            tint=current_tint,
            groove=_groove(song, profile, track_no, explore=False),
            performance=perf,
            **base_kwargs,
        )
        prompt_b = _compose_prompt(
            tint=alt_tint,
            groove=_groove(song, profile, track_no, explore=True),
            performance=perf,
            **base_kwargs,
        )
        character_perf = perf
        if character_perf:
            character_perf = _clip(
                character_perf + "; emphasize one recognizable pickup/rest/ending habit without changing age, weight or core resonance",
                190,
            )
        else:
            character_perf = "one recognizable pickup/rest/ending habit; preserve recurring singer identity"
        prompt_c = _compose_prompt(
            tint=current_tint,
            groove=_groove(song, profile, track_no, explore=False),
            performance=character_perf,
            **base_kwargs,
        )

        exclude = _compact(song.get("excludePrompt") or song.get("negativeStyleText"))
        candidates = [
            _candidate(
                variant_id="A_CONTROL",
                primary_axis="control_baseline",
                description="High-control reconstruction: preserve current genre/tint/identity while compressing the prompt into audible controls.",
                prompt=prompt_a,
                exclude=exclude,
                model_target=model_target,
                source_ids=["suno_v6_faq", "suno_style_influence", "suno_inspire"],
            ),
            _candidate(
                variant_id="B_GROOVE",
                primary_axis="groove_and_secondary_tint",
                description="Controlled groove exploration: keep singer/story/harmony constant and change the rhythmic pocket plus one compatible secondary tint.",
                prompt=prompt_b,
                exclude=exclude,
                model_target=model_target,
                source_ids=["community_style_mesh", "community_suno_lab", "suno_v6_faq"],
            ),
            _candidate(
                variant_id="C_CHARACTER",
                primary_axis="performance_character",
                description="Vocal-character experiment: keep genre/tint/groove constant and strengthen one track-specific performance habit.",
                prompt=prompt_c,
                exclude=exclude,
                model_target=model_target,
                source_ids=["community_suno_lab", "suno_v6_faq", "suno_style_influence"],
            ),
        ]
        track_packs.append({
            "trackNo": track_no,
            "title": song.get("title", ""),
            "sourceStylePrompt": song.get("stylePrompt", ""),
            "currentTint": current_tint,
            "candidates": candidates,
        })

    return {
        "engineVersion": "0.6.1-dev",
        "mode": "RESEARCH_DRIVEN_AB_CANDIDATES",
        "genreId": resolved_genre_id,
        "genreLabel": genre_label,
        "modelTarget": model_target,
        "candidatePolicy": {
            "variants": list(VARIANT_IDS),
            "onePrimaryAxisPerExperiment": True,
            "noWinnerBeforeAudioFeedback": True,
            "immutableContentNotCopiedIntoCandidatePrompts": True,
        },
        "researchSummary": {
            "officialSourceCount": sum(1 for x in knowledge["sources"] if x.get("type") == "official"),
            "communitySourceCount": sum(1 for x in knowledge["sources"] if x.get("type") == "community"),
            "sourceIds": [x.get("id") for x in knowledge["sources"]],
        },
        "tracks": track_packs,
    }


def apply_research_candidate_variant(
    source: Dict[str, Any],
    candidate_pack: Dict[str, Any],
    variant_id: str,
) -> Dict[str, Any]:
    if variant_id not in VARIANT_IDS:
        raise ValueError(f"지원하지 않는 candidate variant: {variant_id}")
    result = deepcopy(source)
    rows = _songs(result)
    pack_by_no = {int(x["trackNo"]): x for x in candidate_pack.get("tracks", [])}
    for pos, song in enumerate(rows, 1):
        track_no = int(song.get("trackNo") or song.get("order") or pos)
        pack = pack_by_no.get(track_no)
        if not pack:
            raise ValueError(f"candidate pack에 track {track_no}가 없습니다.")
        candidate = next((x for x in pack.get("candidates", []) if x.get("variantId") == variant_id), None)
        if not candidate:
            raise ValueError(f"track {track_no}에 {variant_id} 후보가 없습니다.")
        song["stylePrompt"] = candidate["stylePrompt"]
        if candidate.get("excludePrompt"):
            if "excludePrompt" in song or "negativeStyleText" not in song:
                song["excludePrompt"] = candidate["excludePrompt"]
            else:
                song["negativeStyleText"] = candidate["excludePrompt"]
        feedback_context = {
            "researchEngineVersion": candidate_pack.get("engineVersion"),
            "genreId": candidate_pack.get("genreId"),
            "genreLabel": candidate_pack.get("genreLabel"),
            "modelTarget": candidate_pack.get("modelTarget"),
            "variantId": variant_id,
            "primaryAxis": candidate.get("primaryAxis"),
        }
        song["researchRecipe"] = {
            "engineVersion": candidate_pack.get("engineVersion"),
            "variantId": variant_id,
            "primaryAxis": candidate.get("primaryAxis"),
            "description": candidate.get("description"),
            "generationRecipe": deepcopy(candidate.get("generationRecipe") or {}),
            "evidence": deepcopy(candidate.get("evidence") or {}),
            "sourceStylePrompt": pack.get("sourceStylePrompt", ""),
            "feedbackBinding": {
                "experiment_arm": variant_id,
                "experiment_axis": candidate.get("primaryAxis"),
                "experiment_context": feedback_context,
            },
        }
    return result
