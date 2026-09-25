from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any, Dict, List, Tuple

from .master_registry import build_active_master, load_genre_profiles
from .prompt_intelligence import (
    analyze_current_prompt, build_old_new_comparison, load_prompt_intelligence_rules,
    validate_optimization_effectiveness, verify_immutable_fields,
)

from .v061_quality_gate import v061_result_failures


TRACK_MUTABLE_FIELDS = {
    "BPM", "bpm", "trackRole", "musicRole", "rapRatio", "rapForwardRatio",
    "genreId", "genreText", "genre", "vocalDesign", "vocalType", "vocal",
    "harmonicDesign", "stylePrompt", "excludePrompt", "negativeStyleText",
    "durationDesign", "bridgeDesign", "highlightDesign", "killingPointDesign",
    "diversityDesign", "generationRunHint", "performanceSignature",
    "groove", "grooveDesign", "drums", "drumDesign", "bass", "bassDesign",
    "instrumentation", "instrumentationDesign", "harmony", "phonation",
    "verseBehavior", "chorusBehavior", "finalDesign", "promptOptimization",
    "qualityScore", "warnings",
}

META_MUTABLE_FIELDS = {
    "revision", "generationStandardVersion", "promptIntelligenceVersion", "sunoModelTarget", "recommendedVariety",
    "durationHardRange", "durationPreferred", "songQualityPriority", "genrePolicy",
    "harmonicPolicy", "vocalPolicy", "bridgePolicy", "highlightPolicy",
    "calibrationTracks", "calibrationNote", "energyArc", "vocalSignaturePolicy",
    "performanceVariationPolicy", "activeRapPolicy", "durationPolicy",
}

GENRE_CHOICES = {
    "자동(원본 유지)": "auto",
    "Chill Rap": "chill_rap",
    "Soft Old Pop Ballad": "old_pop_ballad",
    "Soft Soul": "soul",
    "Cafe Pop": "cafe_pop",
    "French Chanson": "chanson",
    "Deep House": "deep_house",
}


def _strip_fence(text: str) -> str:
    s = (text or "").strip()
    if s.startswith("~~~"):
        s = re.sub(r"^~~~(?:json)?\s*", "", s, flags=re.I)
        s = re.sub(r"\s*~~~$", "", s)
    if s.startswith("'''"):
        s = re.sub(r"^'''(?:json)?\s*", "", s, flags=re.I)
        s = re.sub(r"\s*'''$", "", s)
    return s.strip()


def load_json_text(text: str) -> Dict[str, Any]:
    obj = json.loads(_strip_fence(text))
    if not isinstance(obj, dict):
        raise ValueError("최상위 JSON은 object여야 합니다.")
    return obj


def _songs(obj: Dict[str, Any]) -> List[Dict[str, Any]]:
    for key in ("songs", "tracks", "preassignedSongs"):
        rows = obj.get(key)
        if isinstance(rows, list):
            return [x for x in rows if isinstance(x, dict)]
    return []


def _song_key(obj: Dict[str, Any]) -> str:
    for key in ("songs", "tracks", "preassignedSongs"):
        if isinstance(obj.get(key), list):
            return key
    return "songs"


def detect_source_profile(source: Dict[str, Any]) -> Dict[str, Any]:
    meta = source.get("meta") if isinstance(source.get("meta"), dict) else {}
    rows = _songs(source)
    hay = " ".join([
        str(meta.get("storyPov", "")), str(meta.get("vocalPolicy", "")),
        str(meta.get("channelLabel", "")),
        str(meta.get("genrePolicy", "")), str(meta.get("audience", "")),
        " ".join(
            str(r.get("vocalType", "")) + " " + str(r.get("vocalDesign", "")) + " "
            + str(r.get("genreText", "")) + " " + str(r.get("stylePrompt", ""))
            for r in rows[:5]
        ),
    ]).casefold()

    story_pov = str(meta.get("storyPov", "")).strip().casefold()
    vocal_types = " ".join(str(r.get("vocalType", "")) for r in rows).casefold()
    if story_pov in {"dual", "duet", "two", "couple", "두사람"} or re.search(r"\bduet\b|male-female|male/female", vocal_types):
        vocal_mode = "dual"
    elif story_pov in {"female", "woman", "여성", "彼女"}:
        vocal_mode = "female"
    elif story_pov in {"male", "man", "남성", "彼"}:
        vocal_mode = "male"
    elif vocal_types and re.search(r"\bfemale\b", vocal_types) and not re.search(r"\bmale\b", vocal_types):
        vocal_mode = "female"
    elif vocal_types and re.search(r"\bmale\b", vocal_types) and not re.search(r"\bfemale\b", vocal_types):
        vocal_mode = "male"
    elif any(x in hay for x in ("instrumental only", "no lead vocal", "no vocal")):
        vocal_mode = "instrumental"
    elif any(x in hay for x in ("duet", "male/female", "male-female", "두사람", "彼と彼女")):
        vocal_mode = "dual"
    elif any(x in hay for x in ("female", "여성", "彼女")):
        vocal_mode = "female"
    elif any(x in hay for x in ("male", "남성", "彼のstory", "彼story")):
        vocal_mode = "male"
    else:
        vocal_mode = "unknown"

    if any(x in hay for x in ("senior", "시니어", "soft old pop", "soft old-pop", "adult pop")):
        source_type = "시니어"
    elif vocal_mode == "dual":
        source_type = "두사람"
    elif vocal_mode == "female":
        source_type = "여성"
    elif vocal_mode == "male":
        source_type = "남성"
    elif vocal_mode == "instrumental":
        source_type = "인스트루멘탈"
    else:
        source_type = "미확인"

    genre_policy = str(meta.get("genrePolicy", ""))
    genre_text = " ".join(str(r.get("genreText", "")) + " " + str(r.get("stylePrompt", "")) for r in rows[:3])
    genre_blob = (genre_policy + " " + genre_text).casefold()
    genre_candidates = (
        ("Deep House", ("deep house",)),
        ("French Chanson", ("french chanson", "chanson")),
        ("Soft Old Pop Ballad", ("soft old pop", "old-pop ballad", "old pop ballad")),
        ("Soft Soul", ("soft soul",)),
        ("Cafe Pop", ("cafe pop", "café pop")),
        ("Chill Rap", ("chill rap",)),
    )
    genre_hint = next((label for label, tokens in genre_candidates if any(x in genre_blob for x in tokens)), "")

    if source_type == "시니어":
        channel_id = "senior"
    elif source_type == "남성":
        channel_id = "chili_male"
    elif source_type == "여성":
        channel_id = "chili_female"
    elif source_type == "두사람":
        channel_id = "chili_dual"
    else:
        channel_id = "custom"

    return {
        "trackCount": len(rows),
        "sourceType": source_type,
        "channelId": channel_id,
        "vocalMode": vocal_mode,
        "genreHint": genre_hint,
        "episodeTitle": str(meta.get("episodeTitle", "")),
        "channelLabel": str(meta.get("channelLabel", "")),
    }


def detect_master_profile(master_text: str) -> Dict[str, Any]:
    low = (master_text or "").casefold()
    instrumental = any(x in low for x in ("instrumental only", "no lead vocal", "sleep bgm", "healing piano"))
    dual = any(x in low for x in ("male signature", "female signature", "male/female", "male-female", "duet", "두사람"))
    female = bool(re.search(r"(?:^|[^a-z])female(?:\s+solo|-only)(?:[^a-z]|$)", low)) or any(x in low for x in ("여성", "彼女"))
    male = bool(re.search(r"(?:^|[^a-z])male(?:\s+solo|-only)(?:[^a-z]|$)", low)) or any(x in low for x in ("남성", "彼のstory"))
    if instrumental:
        vocal_mode = "instrumental"
    elif dual:
        vocal_mode = "dual"
    elif female and not male:
        vocal_mode = "female"
    elif male and not female:
        vocal_mode = "male"
    else:
        vocal_mode = "unknown"
    return {
        "vocalMode": vocal_mode,
        "genreHint": "Chill Rap" if "chill rap" in low else "",
        "length": len(master_text or ""),
    }


def validate_master_compatibility(source: Dict[str, Any], master_text: str) -> Dict[str, Any]:
    src = detect_source_profile(source)
    mst = detect_master_profile(master_text)
    errors: List[str] = []
    warnings: List[str] = []
    if not (master_text or "").strip():
        errors.append("최신 마스터 TXT가 비어 있습니다.")
    if src["trackCount"] <= 0:
        errors.append("원본 JSON에서 songs/tracks 배열을 찾지 못했습니다.")
    if src["vocalMode"] in {"male", "female", "dual"} and mst["vocalMode"] == "instrumental":
        errors.append(f"보컬 원본({src['vocalMode']})에 Instrumental/Sleep BGM 마스터를 적용할 수 없습니다.")
    if src["vocalMode"] == "male" and mst["vocalMode"] == "female":
        errors.append("남성 STORY 원본에 여성 전용 마스터가 선택되었습니다.")
    if src["vocalMode"] == "female" and mst["vocalMode"] == "male":
        errors.append("여성 STORY 원본에 남성 전용 마스터가 선택되었습니다.")
    if src["vocalMode"] == "dual" and mst["vocalMode"] in {"male", "female"}:
        errors.append("두사람 STORY 원본에는 남/여 듀얼 마스터가 필요합니다.")
    if src["genreHint"] == "Chill Rap" and mst["genreHint"] != "Chill Rap":
        warnings.append("원본은 Chill Rap인데 마스터에서 Chill Rap 표기를 찾지 못했습니다.")
    if mst["vocalMode"] == "unknown":
        warnings.append("마스터 보컬 유형을 자동 판별하지 못했습니다. 결과 검증이 필요합니다.")
    return {"ok": not errors, "source": src, "master": mst, "errors": errors, "warnings": warnings}


def build_existing_json_upgrade_instruction(
    source_text: str,
    master_text: str,
    genre_choice: str = "자동(원본 유지)",
) -> Tuple[str, Dict[str, Any]]:
    source = load_json_text(source_text)
    compat = validate_master_compatibility(source, master_text)
    if not compat["ok"]:
        raise ValueError("\n".join(compat["errors"]))
    rows = _songs(source)
    if len(rows) != 15:
        raise ValueError(f"기존 JSON은 15곡이어야 합니다. 현재 {len(rows)}곡입니다.")
    if genre_choice not in GENRE_CHOICES:
        raise ValueError(f"지원하지 않는 장르 선택입니다: {genre_choice}")
    genre_id = GENRE_CHOICES[genre_choice]
    if genre_id == "auto":
        detected_label = compat["source"].get("genreHint")
        genre_id = GENRE_CHOICES.get(detected_label or "", "")
        if not genre_id or genre_id == "auto":
            raise ValueError("원본 장르를 자동 감지하지 못했습니다. 장르를 직접 선택하세요.")
    profiles = load_genre_profiles()
    genre_profile = profiles.get(genre_id)
    if not genre_profile:
        raise ValueError(f"Genre Master Profile을 찾을 수 없습니다: {genre_id}")
    active_master = build_active_master(master_text, genre_profile, compat["source"])
    intelligence_rules = load_prompt_intelligence_rules()
    current_analysis = analyze_current_prompt(source, intelligence_rules)
    contract_lines = []
    guidance_by_area = {
        "exclude_efficiency": ("shorten and deduplicate exclusion list", ("excludePrompt", "negativeStyleText")),
        "redundancy": ("remove repeated instructions while retaining distinct musical intent", ("stylePrompt", "excludePrompt")),
        "prompt_ordering": ("order prompt by genre, BPM/energy, singer, phonation, groove, rhythm section, instruments, sections, harmony, runtime", ("stylePrompt",)),
        "bridge_contrast": ("write a track-specific audible Bridge contrast", ("bridgeDesign",)),
        "final_payoff": ("connect Final payoff to the track highlight instead of reusing a generic ending", ("highlightDesign", "finalDesign")),
        "performance_signature": ("preserve or strengthen this track's distinct delivery cue", ("performanceSignature",)),
        "genre_clarity": ("keep one dominant selected genre and at most one compatible tint", ("genreText", "genreId", "stylePrompt")),
        "vocal_identity": ("preserve the source singer gender and solo/duet role while stating the recurring identity", ("vocalDesign",)),
        "phonation": ("make phonation concise and internally consistent", ("vocalDesign", "stylePrompt")),
        "groove": ("state the audible pocket and rhythmic delivery", ("grooveDesign", "stylePrompt")),
        "drums": ("specify a compact genre-appropriate drum behavior", ("drumDesign", "stylePrompt")),
        "bass": ("describe bass movement and its relation to the kick", ("bassDesign", "stylePrompt")),
        "instrumentation": ("select a focused signature palette", ("instrumentationDesign", "stylePrompt")),
        "harmony": ("describe chord color or tension and release", ("harmonicDesign", "stylePrompt")),
        "verse_behavior": ("make Verse delivery behavior audible", ("verseBehavior", "stylePrompt")),
        "chorus_behavior": ("make the Chorus lift perceptible without changing singer identity", ("chorusBehavior", "stylePrompt")),
        "tempo_design": ("set BPM from the selected Channel and Genre Master ranges", ("BPM",)),
        "prompt_length": ("compress stylePrompt to high information density and stay below the hard maximum", ("stylePrompt",)),
        "contradiction": ("remove only semantically incompatible instructions", ("stylePrompt", "excludePrompt", "negativeStyleText")),
        "duration_design": ("add a suitable duration/section target and prevent early ending", ("durationDesign",)),
        "generation_hint": ("add a concise track-specific generation guard", ("generationRunHint",)),
        "model_specific_behavior": ("format explicit musical controls for the target generation model", ("stylePrompt", "generationRunHint")),
        "information_density": ("collapse semantically repeated style atoms without losing distinct musical controls", ("stylePrompt",)),
        "track_specificity": ("add a concrete per-track performance cue while retaining the recurring singer", ("performanceSignature", "stylePrompt")),
        "bridge_specificity": ("align the stylePrompt Bridge with at least two declared audible change axes, or three for an Anchor", ("bridgeDesign", "stylePrompt")),
        "final_specificity": ("express this track's highlight payoff in the Final instead of a generic repeated ending", ("highlightDesign", "finalDesign", "stylePrompt")),
        "template_similarity": ("differentiate groove, instrumentation, performance, Bridge or Final while retaining singer identity", ("grooveDesign", "instrumentationDesign", "performanceSignature", "bridgeDesign", "highlightDesign", "finalDesign", "stylePrompt")),
        "jp_native_positive_controls": ("restore explicit close-mic + JP-native diction + mora timing + natural sentence/pitch-accent behavior in the actual stylePrompt", ("vocalDesign", "stylePrompt")),
        "vocal_design_consistency": ("align vocalDesign and stylePrompt to one fixed channel fingerprint; remove conflicting breath/grain coordinates", ("vocalDesign", "stylePrompt")),
    }
    for analysis_track in current_analysis["tracks"]:
        areas = [x["area"] for x in analysis_track["weaknesses"]]
        actions = list(dict.fromkeys(guidance_by_area[x][0] for x in areas if x in guidance_by_area))
        fields = list(dict.fromkeys(field for x in areas for field in guidance_by_area.get(x, ("", ()))[1]))
        contract_lines.append(
            f"[TRACK {int(analysis_track.get('trackNo') or 0):02d} CURRENT ANALYSIS]\n"
            + "Actionable weaknesses:\n" + ("\n".join(f"- {x}" for x in areas) or "- none detected")
            + "\nMUST ADDRESS:\n" + ("\n".join(f"- {x}" for x in actions) or "- no required change; use KEEP only with a content-based keepReason")
            + "\nMUST PRESERVE:\n- title\n- lyrics\n- hook\n- story\n- scene\n- relationship boundaries\n"
            + "EXPECTED MUTABLE FIELDS:\n" + ("\n".join(f"- {x}" for x in fields) or "- none required")
        )

    instruction = """# EXISTING JSON -> PROMPT INTELLIGENCE OPTIMIZER

목표:
아래 ORIGINAL JSON의 현재 음악 설계를 baseline으로 분석하고 Prompt Intelligence로 최적화하여,
완성형 Suno 복붙용 JSON 전체를 반환한다.

중요 평가 원칙:
- 입력 JSON의 version/revision/generationStandardVersion 값(v14/v15/v16 등)은 품질 판단 근거가 아니다.
- "이미 최신 버전"이라는 이유로 KEEP하거나 변경 없음을 선언하지 마라.
- 실제 stylePrompt와 음악 설계의 명료성, 구체성, 충돌, 중복, 구조적 완성도만 평가한다.
- 실제 개선 가능성이 없는 개별 필드는 유지할 수 있지만 그 이유는 내용 기반이어야 한다.

처리 단계:
1. Analyze Current Prompt
2. Detect weaknesses
3. Apply Channel Master
4. Apply Genre Master
5. Apply Prompt Intelligence Knowledge
6. Remove redundancy/conflicts
7. Generate optimized music fields
8. Compare Old vs New
9. Verify immutable fields unchanged
10. Save full Suno-ready JSON

절대 규칙:
1. ORIGINAL JSON의 전체 구조와 기존 필드를 삭제하지 마라.
2. trackNo/order/title/titleLocalized/hookPhrase/lyrics/story/scene/listenerSituation/emotionArc/centralImage/seasonMoment/distinctChoice/youtube 및 기타 비음악 콘텐츠는 글자 하나도 바꾸지 마라.
3. 가사는 재작성/교정/요약/번역하지 마라. ORIGINAL lyrics를 정확히 그대로 복사한다.
4. 제목과 훅도 정확히 그대로 유지한다.
5. 최신 MASTER를 반영할 수 있는 것은 음악 관련 필드뿐이다.
6. ORIGINAL JSON의 필드를 축약하거나 structured_track_plan 형태로 바꾸지 마라.
7. 각 곡에 title + lyrics + stylePrompt가 반드시 존재해야 한다.
8. 원본 보컬 성별/역할과 최신 MASTER가 충돌하면 억지 적용하지 마라.
9. 최종 응답은 설명 없이 JSON object 하나만 출력한다.
10. songs 15곡을 모두 출력한다.
11. 적극 개선 대상은 BPM/Genre/Vocal Design/Style Prompt/Exclude/Performance Signature/Groove/Instrumentation/Harmony/Bridge/Final/Duration/Generation Hint이다.
12. 각 song에 promptOptimization object를 추가한다: status, changedFields, resolvedWeaknesses, remainingWeaknesses, changeReasons[], expectedImprovements[], oldStylePrompt, newStylePrompt, oldExcludePrompt, newExcludePrompt.
13. oldStylePrompt/oldExcludePrompt는 ORIGINAL의 값을 정확히 복사하고 newStylePrompt/newExcludePrompt는 최종 JSON 값과 정확히 같아야 한다.
14. 중복 형용사 나열보다 들리는 음악 행동을 우선하고, positive prompt와 exclude의 충돌을 제거한다.
15. 결과가 개선 가능성을 발견한 트랙에서 관련 음악 필드를 하나도 바꾸지 않으면 안 된다. claimed changedFields는 실제 old/new diff와 일치시킨다.
16. before/after 분석을 모두 실행하고 resolvedWeaknesses는 after 분석에서 사라진 영역만 선언한다.
17. promptOptimization은 status, changedFields, resolvedWeaknesses, remainingWeaknesses, changeReasons, expectedImprovements, oldStylePrompt, newStylePrompt, oldExcludePrompt, newExcludePrompt를 포함한다.
18. 변경이 없고 actionable weakness가 전혀 없는 트랙만 status=KEEP을 쓸 수 있으며, keepReason="No actionable weakness remained after analysis"와 구체적인 내용 근거를 쓴다.
19. CHILI 남성 exclude는 8-16개의 의미 범주로 압축하되 female/duet 오염, generic polished male-pop tenor, K-pop belt, mature/dark crooner, whisper-only, falsetto hook/final, rock rasp/gravel, 일본어 발음 오류, fully-sung R&B Verse, hard trap/drill, festival EDM, static bass 등 현재 마스터의 실제 실패 방어를 유지한다.
20. lyricLanguage가 Japanese인 보컬 세트만 actual stylePrompt에 close-mic + JP-native/native Japanese diction + mora timing + natural sentence accent/pitch-accent를 positive control로 직접 넣는다. Tokyo/Japan 타깃이라도 lyricLanguage=English이면 이 규칙을 적용하지 말고 natural connected English / relaxed consonants / idiomatic reductions / natural stress를 우선한다.
21. vocalDesign과 stylePrompt의 breath/grain/resonance 좌표가 서로 충돌하면 안 된다. 최신 MASTER의 고정 channel fingerprint를 vocalDesign의 Verse/Chorus/Bridge/Final까지 일관되게 반영하고, 섹션 차이는 phrase density/rap ratio/brightness/공간감으로 만든다.
22. Chill Rap stylePrompt 순서는 genre + secondary tint → BPM+groove → gender hard lock → channel voice/phonation → JP-native + rap pocket → drum/moving bass → focused instruments → Hook → Bridge → Final → compact money chord → short scene/runtime로 한다.
23. Chill Rap stylePrompt는 기본 72-88 words, 허용 65-95 words, 가능하면 900 chars 이하를 목표로 한다.
24. 스토리/장면을 바꾸지 않는 범위에서 짧은 scene anchor를 actual stylePrompt 말미에 유지한다.

[DETECTED SOURCE]
""" + json.dumps(compat["source"], ensure_ascii=False, indent=2) + """

[CURRENT PROMPT ANALYSIS - VERSION-AGNOSTIC]
""" + json.dumps(current_analysis, ensure_ascii=False, indent=2) + """

[PROMPT INTELLIGENCE RULES]
""" + json.dumps(intelligence_rules, ensure_ascii=False, indent=2) + """

[TRACK-BY-TRACK OPTIMIZATION CONTRACTS]
""" + "\n\n".join(contract_lines) + """

[ACTIVE MASTER - CHANNEL + GENRE]
""" + active_master + """

[ORIGINAL JSON - IMMUTABLE CONTENT + FULL SCHEMA]
""" + json.dumps(source, ensure_ascii=False, indent=2)
    return instruction, compat


def build_haru_txt_instruction(
    haru_text: str,
    master_text: str,
    expected_count: int = 15,
    channel_id: str = "custom",
    genre_choice: str = "Chill Rap",
) -> str:
    if not (haru_text or "").strip():
        raise ValueError("Haru Studio TXT가 비어 있습니다.")
    if not (master_text or "").strip():
        raise ValueError("최신 마스터 TXT가 비어 있습니다.")
    genre_id = GENRE_CHOICES.get(genre_choice)
    if not genre_id or genre_id == "auto":
        raise ValueError("Haru Studio workflow에서는 장르를 직접 선택하세요.")
    genre_profile = load_genre_profiles().get(genre_id)
    if not genre_profile:
        raise ValueError(f"Genre Master Profile을 찾을 수 없습니다: {genre_id}")
    source_profile = {"sourceType": channel_id, "channelId": channel_id, "trackCount": expected_count}
    active_master = build_active_master(master_text, genre_profile, source_profile)
    return """# HARU STUDIO TXT -> COMPLETE SUNO JSON

목표:
아래 HARU STUDIO TXT의 스토리/회차/장면/제목/훅/금지사항을 기준으로
최신 MASTER를 적용하여 완성형 JSON을 만든다.

절대 규칙:
1. HARU TXT의 스토리 사실, 순서, 관계 경계, 지정 제목/훅을 존중한다.
2. 최신 MASTER는 BPM/장르/보컬/발성/stylePrompt/Bridge/Final/화성/길이의 최우선 기준이다.
3. structured_track_plan 같은 중간 산출물만 반환하지 마라.
4. 최종 결과는 Suno에 바로 복사/붙여넣기 가능한 완성형 JSON이어야 한다.
5. 각 곡에는 최소 trackNo, title, hookPhrase, BPM, trackRole, vocalType 또는 vocalDesign, lyrics, stylePrompt가 있어야 한다.
6. lyrics와 stylePrompt는 모든 곡에 실제 내용이 들어가야 한다.
7. 메타와 곡별 세부 설계 필드를 가능한 충실하게 유지한다.
8. 최종 응답은 설명 없이 JSON object 하나만 출력한다.
9. 정확히 """ + str(expected_count) + """곡을 출력한다.

[ACTIVE MASTER - CHANNEL + GENRE]
""" + active_master + """

[HARU STUDIO TXT - STORY / EPISODE AUTHORITY]
""" + haru_text.strip()


def merge_existing_upgrade(source_text: str, upgraded_text: str) -> Dict[str, Any]:
    source = load_json_text(source_text)
    upgraded = load_json_text(upgraded_text)
    source_rows = _songs(source)
    upgraded_rows = _songs(upgraded)
    if len(source_rows) != len(upgraded_rows):
        raise ValueError(f"곡 수가 다릅니다: 원본 {len(source_rows)} / 결과 {len(upgraded_rows)}")

    by_no: Dict[int, Dict[str, Any]] = {}
    for i, row in enumerate(upgraded_rows, 1):
        try:
            no = int(row.get("trackNo", i))
        except Exception:
            no = i
        by_no[no] = row

    final = deepcopy(source)
    if isinstance(source.get("meta"), dict) and isinstance(upgraded.get("meta"), dict):
        for key in META_MUTABLE_FIELDS:
            if key in upgraded["meta"]:
                final["meta"][key] = deepcopy(upgraded["meta"][key])

    key = _song_key(source)
    merged_rows: List[Dict[str, Any]] = []
    for i, src in enumerate(source_rows, 1):
        try:
            no = int(src.get("trackNo", i))
        except Exception:
            no = i
        new = by_no.get(no)
        if not new:
            raise ValueError(f"업그레이드 결과에서 trackNo {no}를 찾지 못했습니다.")
        merged = deepcopy(src)
        for field in TRACK_MUTABLE_FIELDS:
            if field in new:
                merged[field] = deepcopy(new[field])
        merged_rows.append(merged)
    final[key] = merged_rows
    return final


def validate_complete_json(result: Dict[str, Any], expected_count: int = 15, source: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    rows = _songs(result)
    if len(rows) != expected_count:
        issues.append({"level": "FAIL", "code": "COUNT", "message": f"{expected_count}곡 필요, 현재 {len(rows)}곡"})
    for i, row in enumerate(rows, 1):
        no = row.get("trackNo", i)
        for field in ("title", "lyrics", "stylePrompt"):
            if not str(row.get(field, "")).strip():
                issues.append({"level": "FAIL", "code": f"MISSING_{field.upper()}", "trackNo": no, "message": f"{field} 없음"})
        if not row.get("BPM") and not row.get("bpm"):
            issues.append({"level": "FAIL", "code": "MISSING_BPM", "trackNo": no, "message": "BPM 없음"})

    if source:
        src_rows = _songs(source)
        by_no = {int(r.get("trackNo", i)): r for i, r in enumerate(rows, 1)}
        for i, src in enumerate(src_rows, 1):
            no = int(src.get("trackNo", i))
            cur = by_no.get(no)
            if not cur:
                continue
            for field in ("title", "titleLocalized", "hookPhrase", "lyrics"):
                if field in src and src.get(field) != cur.get(field):
                    issues.append({"level": "FAIL", "code": f"LOCK_{field.upper()}", "trackNo": no, "message": f"{field}가 원본과 다름"})
            missing_keys = [k for k in src.keys() if k not in cur]
            if missing_keys:
                issues.append({"level": "FAIL", "code": "SCHEMA_FIELDS_DROPPED", "trackNo": no, "message": f"원본 필드 누락: {missing_keys[:8]}"})

    if not issues:
        issues.append({"level": "PASS", "code": "COMPLETE_JSON_OK", "message": "완성형 JSON 검증 통과"})
    return issues


def _vocal_role(row: Dict[str, Any]) -> str:
    value = str(row.get("vocalType", row.get("vocalDesign", ""))).casefold()
    if "instrumental" in value or "no lead vocal" in value:
        return "instrumental"
    if "duet" in value or (re.search(r"\bfemale\b", value) and re.search(r"\bmale\b", value)):
        return "duet"
    if re.search(r"\bfemale\b", value):
        return "female"
    if re.search(r"\bmale\b", value):
        return "male"
    return "unknown"


def _optimization_regression_issues(source: Dict[str, Any], result: Dict[str, Any], genre_choice: str = "") -> List[Dict[str, Any]]:
    from .master_registry import load_genre_profiles
    from .prompt_intelligence import load_prompt_intelligence_rules

    issues: List[Dict[str, Any]] = []
    profiles = load_genre_profiles()
    genre_id = GENRE_CHOICES.get(genre_choice or "", "")
    if not genre_id or genre_id == "auto":
        genre_id = GENRE_CHOICES.get(detect_source_profile(source).get("genreHint", ""), "")
    profile = profiles.get(genre_id, {})
    dominant = str(profile.get("dominantGenre", ""))
    bpm_range = profile.get("bpm", {})
    hard_max = int(load_prompt_intelligence_rules()["policy"]["targetPromptChars"]["hardMax"])
    source_rows = {str(x.get("trackNo", i)): x for i, x in enumerate(_songs(source), 1)}

    source_context = source.get("meta") if isinstance(source.get("meta"), dict) else {}
    for i, row in enumerate(_songs(result), 1):
        no = row.get("trackNo", i)
        old = source_rows.get(str(no), {})
        issues.extend(v061_result_failures(row, source_context))
        voice_role, old_voice_role = _vocal_role(row), _vocal_role(old)
        if old_voice_role != "unknown" and voice_role != old_voice_role:
            issues.append({"level": "FAIL", "code": "WRONG_VOCAL_ROLE", "trackNo": no, "message": f"Expected {old_voice_role}; found {voice_role}."})
        vocal_blob = str(row.get("vocalDesign", row.get("vocalType", ""))).casefold()
        if re.search(r"\bgeneric(?: polished)? (?:ai )?(?:male|female)?\s*(?:vocal|singer|tenor)", vocal_blob):
            issues.append({"level": "FAIL", "code": "GENERIC_VOCAL_REGRESSION", "trackNo": no})
        try:
            bpm = int(row.get("BPM", row.get("bpm", 0)))
        except (TypeError, ValueError):
            bpm = 0
        if bpm_range and bpm and not int(bpm_range.get("min", 0)) <= bpm <= int(bpm_range.get("max", 999)):
            issues.append({"level": "FAIL", "code": "BPM_OUT_OF_GENRE_RANGE", "trackNo": no, "BPM": bpm, "range": bpm_range})
        genre = str(row.get("genreText", row.get("genre", "")))
        genre_id_value = str(row.get("genreId", "")).casefold()
        style = str(row.get("stylePrompt", ""))
        explicit_genre_ok = (
            dominant.casefold() in genre.casefold()
            or (genre_id and genre_id_value == genre_id.casefold())
        ) if (genre or genre_id_value) else dominant.casefold() in style.casefold()
        if dominant and not explicit_genre_ok:
            issues.append({"level": "FAIL", "code": "GENRE_DRIFT", "trackNo": no, "expected": dominant, "actual": genre})
        if len(style) > hard_max:
            issues.append({"level": "FAIL", "code": "STYLE_PROMPT_HARD_MAX", "trackNo": no, "length": len(style), "hardMax": hard_max})
        if voice_role != "instrumental" and not str(row.get("performanceSignature", "")).strip():
            issues.append({"level": "FAIL", "code": "MISSING_PERFORMANCE_SIGNATURE", "trackNo": no})
        if not (str(row.get("bridgeDesign", "")).strip() or re.search(r"\bbridge\b", style, re.I)):
            issues.append({"level": "FAIL", "code": "MISSING_BRIDGE", "trackNo": no})
        if not (str(row.get("finalDesign", "")).strip() or str(row.get("highlightDesign", "")).strip() or re.search(r"\b(?:final|outro)\b", style, re.I)):
            issues.append({"level": "FAIL", "code": "MISSING_FINAL", "trackNo": no})
    return issues


def finalize_existing_upgrade(
    source_text: str,
    upgraded_text: str,
    genre_choice: str = "",
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    final = merge_existing_upgrade(source_text, upgraded_text)
    source = load_json_text(source_text)
    issues = validate_complete_json(final, len(_songs(source)), source)
    issues.extend(verify_immutable_fields(source, final))
    before_analysis = analyze_current_prompt(source)
    after_analysis = analyze_current_prompt(final)
    effectiveness = validate_optimization_effectiveness(source, final, before_analysis, after_analysis)
    issues.extend(effectiveness["issues"])

    source_by_no = {str(x.get("trackNo", i)): x for i, x in enumerate(_songs(source), 1)}
    before_by_no = {str(x.get("trackNo", i)): x for i, x in enumerate(before_analysis["tracks"], 1)}
    after_by_no = {str(x.get("trackNo", i)): x for i, x in enumerate(after_analysis["tracks"], 1)}
    comparison_by_no = {str(x["trackNo"]): x for x in effectiveness["comparisons"]}
    for i, row in enumerate(_songs(final), 1):
        no = row.get("trackNo", i)
        key = str(no)
        old = source_by_no.get(key, {})
        audit = row.get("promptOptimization")
        if not isinstance(audit, dict):
            issues.append({"level": "FAIL", "code": "MISSING_OPTIMIZATION_AUDIT", "trackNo": no})
            continue
        old_style, new_style = str(old.get("stylePrompt", "")), str(row.get("stylePrompt", ""))
        old_exclude = str(old.get("excludePrompt") or old.get("negativeStyleText", ""))
        new_exclude = str(row.get("excludePrompt") or row.get("negativeStyleText", ""))
        compare = comparison_by_no.get(key, {})
        actual_changed = compare.get("changedFields", [])
        before_areas = {x["area"] for x in before_by_no.get(key, {}).get("weaknesses", [])}
        after_areas = {x["area"] for x in after_by_no.get(key, {}).get("weaknesses", [])}
        resolved, remaining = sorted(before_areas - after_areas), sorted(after_areas)

        for field, expected, code in (
            ("oldStylePrompt", old_style, "OLD_PROMPT_MISMATCH"),
            ("newStylePrompt", new_style, "NEW_PROMPT_MISMATCH"),
            ("oldExcludePrompt", old_exclude, "OLD_EXCLUDE_MISMATCH"),
            ("newExcludePrompt", new_exclude, "NEW_EXCLUDE_MISMATCH"),
        ):
            if audit.get(field) != expected:
                issues.append({"level": "FAIL", "code": code, "trackNo": no})
        claimed_fields = audit.get("changedFields")
        if not isinstance(claimed_fields, list):
            issues.append({"level": "FAIL", "code": "CHANGED_FIELDS_MISSING", "trackNo": no})
        elif sorted(set(claimed_fields)) != sorted(actual_changed):
            issues.append({"level": "FAIL", "code": "CLAIMED_CHANGED_FIELDS_MISMATCH", "trackNo": no, "actual": actual_changed, "claimed": claimed_fields})
        for field in ("resolvedWeaknesses", "remainingWeaknesses", "changeReasons", "expectedImprovements"):
            if not isinstance(audit.get(field), list):
                issues.append({"level": "FAIL", "code": f"{field.upper()}_MISSING", "trackNo": no})
        if isinstance(audit.get("resolvedWeaknesses"), list) and set(audit["resolvedWeaknesses"]) != set(resolved):
            issues.append({"level": "FAIL", "code": "CLAIMED_WEAKNESS_RESOLUTION_MISMATCH", "trackNo": no, "actual": resolved, "claimed": audit["resolvedWeaknesses"]})
        if isinstance(audit.get("remainingWeaknesses"), list) and set(audit["remainingWeaknesses"]) != set(remaining):
            issues.append({"level": "FAIL", "code": "REMAINING_WEAKNESSES_MISMATCH", "trackNo": no, "actual": remaining, "claimed": audit["remainingWeaknesses"]})
        if actual_changed:
            if audit.get("status") != "IMPROVED":
                issues.append({"level": "FAIL", "code": "OPTIMIZATION_STATUS_MISMATCH", "trackNo": no})
            if not audit.get("changeReasons"):
                issues.append({"level": "FAIL", "code": "MISSING_CHANGE_REASONS", "trackNo": no})
            if not audit.get("expectedImprovements"):
                issues.append({"level": "FAIL", "code": "MISSING_EXPECTED_IMPROVEMENTS", "trackNo": no})
        elif not before_areas:
            if audit.get("status") != "KEEP" or not str(audit.get("keepReason", "")).strip():
                issues.append({"level": "FAIL", "code": "KEEP_REASON_MISSING", "trackNo": no})
        elif audit.get("status") == "KEEP":
            issues.append({"level": "FAIL", "code": "KEEP_WITH_ACTIONABLE_WEAKNESS", "trackNo": no})

        row["promptOptimization"] = {
            **audit,
            "status": audit.get("status"),
            "changedFields": actual_changed,
            "resolvedWeaknesses": resolved,
            "remainingWeaknesses": remaining,
            "oldStylePrompt": old_style,
            "newStylePrompt": new_style,
            "oldExcludePrompt": old_exclude,
            "newExcludePrompt": new_exclude,
        }

    issues.extend(_optimization_regression_issues(source, final, genre_choice))
    if not any(x.get("level") == "FAIL" for x in issues):
        issues.append({"level": "PASS", "code": "OPTIMIZATION_EFFECTIVE", "message": "Actual field changes and before/after analysis passed."})
    effectiveness["report"]["optimizationEffective"] = not any(x.get("level") == "FAIL" for x in issues)
    final["promptOptimizationReport"] = {
        "versionUsedAsQualitySignal": False,
        "immutableFieldsVerified": not any(x.get("level") == "FAIL" and str(x.get("code", "")).startswith("IMMUTABLE") for x in issues),
        **effectiveness["report"],
        "beforeWeaknessCounts": before_analysis["weaknessCounts"],
        "afterWeaknessCounts": after_analysis["weaknessCounts"],
        "comparisons": build_old_new_comparison(source, final),
        "trackComparisons": effectiveness["comparisons"],
        "qa": issues,
    }
    return final, issues


def finalize_haru_result(result_text: str, expected_count: int = 15) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    result = load_json_text(result_text)
    return result, validate_complete_json(result, expected_count)
