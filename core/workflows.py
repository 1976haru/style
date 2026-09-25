from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any, Dict, List, Tuple

from .master_registry import build_active_master, load_genre_profiles
from .prompt_intelligence import (
    analyze_current_prompt, build_old_new_comparison, load_prompt_intelligence_rules,
    verify_immutable_fields,
)


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
    "revision", "generationStandardVersion", "sunoModelTarget", "recommendedVariety",
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
12. 각 song에 promptOptimization object를 추가한다: existingStylePrompt, newStylePrompt, changeReasons[], expectedImprovements[], weaknessesAddressed[].
13. existingStylePrompt는 ORIGINAL의 값을 정확히 복사하고 newStylePrompt는 최종 stylePrompt와 정확히 같아야 한다.
14. 중복 형용사 나열보다 들리는 음악 행동을 우선하고, positive prompt와 exclude의 충돌을 제거한다.

[DETECTED SOURCE]
""" + json.dumps(compat["source"], ensure_ascii=False, indent=2) + """

[CURRENT PROMPT ANALYSIS - VERSION-AGNOSTIC]
""" + json.dumps(current_analysis, ensure_ascii=False, indent=2) + """

[PROMPT INTELLIGENCE RULES]
""" + json.dumps(intelligence_rules, ensure_ascii=False, indent=2) + """

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


def finalize_existing_upgrade(source_text: str, upgraded_text: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    final = merge_existing_upgrade(source_text, upgraded_text)
    source = load_json_text(source_text)
    issues = validate_complete_json(final, len(_songs(source)), source)
    issues.extend(verify_immutable_fields(source, final))
    source_by_no = {int(x.get("trackNo", i)): x for i, x in enumerate(_songs(source), 1)}
    for i, row in enumerate(_songs(final), 1):
        no = int(row.get("trackNo", i))
        audit = row.get("promptOptimization")
        if not isinstance(audit, dict):
            issues.append({"level": "FAIL", "code": "MISSING_OPTIMIZATION_AUDIT", "trackNo": no, "message": "promptOptimization 없음"})
            continue
        old_style = str(source_by_no.get(no, {}).get("stylePrompt", ""))
        if audit.get("existingStylePrompt") != old_style:
            issues.append({"level": "FAIL", "code": "OLD_PROMPT_MISMATCH", "trackNo": no, "message": "기존 stylePrompt 비교값 불일치"})
        if audit.get("newStylePrompt") != row.get("stylePrompt"):
            issues.append({"level": "FAIL", "code": "NEW_PROMPT_MISMATCH", "trackNo": no, "message": "신규 stylePrompt 비교값 불일치"})
        for field, code in (("changeReasons", "MISSING_CHANGE_REASONS"), ("expectedImprovements", "MISSING_EXPECTED_IMPROVEMENTS")):
            if not isinstance(audit.get(field), list) or not audit[field]:
                issues.append({"level": "FAIL", "code": code, "trackNo": no, "message": f"{field} 없음"})
    final["promptOptimizationReport"] = {
        "versionUsedAsQualitySignal": False,
        "immutableFieldsVerified": not any(x.get("level") == "FAIL" and str(x.get("code", "")).startswith("IMMUTABLE") for x in issues),
        "comparisons": build_old_new_comparison(source, final),
    }
    return final, issues


def finalize_haru_result(result_text: str, expected_count: int = 15) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    result = load_json_text(result_text)
    return result, validate_complete_json(result, expected_count)
