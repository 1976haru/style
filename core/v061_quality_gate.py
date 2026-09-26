from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


def _text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_text(v) for v in value)
    return str(value or "")


def _is_japanese_source(source_context: Dict[str, Any] | None, row: Dict[str, Any]) -> bool:
    context = source_context or {}
    explicit_language = str(
        context.get("lyricLanguage") or context.get("language") or ""
    ).strip().casefold()
    # Explicit lyric language outranks market/channel naming. Tokyo Chill Love
    # Story can intentionally publish English-lyric sets; those must not be
    # forced into Japanese mora/pitch-accent controls.
    if explicit_language:
        if explicit_language in {"english", "en", "eng"}:
            return False
        if explicit_language in {"japanese", "ja", "jp", "jpn", "日本語"}:
            return True

    blob = " ".join([
        str(context.get("channelId", "")),
        str(context.get("channelLabel", "")),
        str(row.get("vocalDesign", "")),
        str(row.get("stylePrompt", "")),
    ]).casefold()
    return any(token in blob for token in ("japanese", "日本語", "jp-native", "jp native"))


def _vocal_role(row: Dict[str, Any]) -> str:
    # Explicit vocalType outranks descriptive/negative words inside vocalDesign.
    # A Female Solo track may legitimately have legacy text such as "male 0" in
    # genderLock; that must not cause the role detector to misclassify it as duet.
    explicit = str(row.get("vocalType", "")).casefold()
    if explicit:
        if "instrumental" in explicit:
            return "instrumental"
        if "duet" in explicit or ("male" in explicit and "female" in explicit):
            return "duet"
        if "female" in explicit:
            return "female"
        if "male" in explicit:
            return "male"

    blob = _text(row.get("vocalDesign", "")).casefold()
    if "duet" in blob or ("male" in blob and "female" in blob):
        return "duet"
    if "female" in blob:
        return "female"
    if "male" in blob:
        return "male"
    if "instrumental" in blob:
        return "instrumental"
    return "unknown"



_FEMALE_POSITIVE_RISK_PATTERNS = {
    "male": r"\bmale\b",
    "duet": r"\bduet\b",
    "self-response": r"\bself-response\b",
    "self-answer": r"\bself-answer\b",
    "self-double": r"\bself-double\b",
    "vocal-stack": r"\bvocal\s+stack\b",
    "giant-stack": r"\bgiant\s+(?:vocal\s+)?stack\b",
    "second-singer": r"\bsecond\s+singer\b",
}


def is_female_only_track(
    row: Dict[str, Any],
    source_context: Dict[str, Any] | None = None,
) -> bool:
    if _vocal_role(row) != "female":
        return False
    context = source_context or {}
    allocation = context.get("vocalAllocation")
    if isinstance(allocation, dict):
        try:
            female = int(allocation.get("Female Solo", allocation.get("female", 0)) or 0)
            male = int(allocation.get("Male Solo", allocation.get("male", 0)) or 0)
            duet = int(allocation.get("Duet", allocation.get("duet", 0)) or 0)
            mixed = int(allocation.get("Mixed", allocation.get("mixed", 0)) or 0)
            if female and not (male or duet or mixed):
                return True
        except (TypeError, ValueError):
            pass
    # Per-track Female Solo is sufficient when the set-level allocation is
    # absent. Explicit vocalType already outranks negative wording in designs.
    return "female" in str(row.get("vocalType", "")).casefold()


def female_single_voice_controls(style_prompt: str) -> Dict[str, bool]:
    low = str(style_prompt or "").casefold()
    return {
        "femaleIdentity": bool(re.search(r"\bfemale\b|\blight[- ]?mezzo\b|\bmezzo[- ]?soprano\b", low)),
        "soloLock": bool(
            re.search(r"\bsolo\s+female\b|\bfemale\s+solo\b", low)
            or re.search(r"\bone\s+(?:recurring\s+|young\s+|japanese\s+){0,4}female\b", low)
            or re.search(r"\bsingle\s+(?:unlayered\s+)?female\b", low)
        ),
        "singleLayer": any(token in low for token in (
            "single unlayered", "one recurring", "same single", "one singer", "single lead",
        )),
        "sectionContinuity": any(token in low for token in (
            "throughout", "every section", "all sections", "same solo female",
        )),
    }


def _female_positive_fields(row: Dict[str, Any]) -> Dict[str, str]:
    vocal = row.get("vocalDesign") if isinstance(row.get("vocalDesign"), dict) else {}
    phonation = row.get("phonationDesign") if isinstance(row.get("phonationDesign"), dict) else {}
    highlight = row.get("highlightDesign") if isinstance(row.get("highlightDesign"), dict) else {}
    final = row.get("finalDesign") if isinstance(row.get("finalDesign"), dict) else {}
    money = row.get("moneyChordDesign") if isinstance(row.get("moneyChordDesign"), dict) else {}
    return {
        "stylePrompt": str(row.get("stylePrompt", "")),
        "voicePalette": str(row.get("voicePalette", "")),
        "vocalDesign": " ".join(_text(vocal.get(k, "")) for k in (
            "system", "genderLock", "base", "signature", "verse", "chorus", "bridge", "final",
        )),
        "phonationDesign": " ".join(_text(phonation.get(k, "")) for k in (
            "coordinates", "fixedSignature", "sectionContrast", "jpNative", "rapPocket", "performanceSignature",
        )),
        "highlightDesign": " ".join(_text(highlight.get(k, "")) for k in ("specificCue", "vocalRule")),
        "finalDesign": " ".join(_text(final.get(k, "")) for k in ("specificCue", "vocalRule", "roleLock")),
        "moneyChordDesign": _text(money.get("executionRule", "")),
        "generationRunHint": str(row.get("generationRunHint", "")),
    }


def female_positive_voice_risks(row: Dict[str, Any]) -> List[Tuple[str, str]]:
    risks: List[Tuple[str, str]] = []
    for field, text in _female_positive_fields(row).items():
        for label, pattern in _FEMALE_POSITIVE_RISK_PATTERNS.items():
            if re.search(pattern, text, re.I):
                risks.append((field, label))
    return risks


def normalize_female_section_labels(text: str) -> str:
    """Normalize only bracketed vocal-role labels; lyric body stays byte-for-byte."""
    value = str(text or "")
    value = re.sub(
        r"(\[[^\]\n]*?/\s*)Female\s+Self-(?:Response|Answer|Double)(\s*\])",
        r"\1Same Solo Female Voice\2",
        value,
        flags=re.I,
    )
    value = re.sub(
        r"\[\s*Female\s+Self-(?:Response|Answer|Double)\s*\]",
        "[Same Solo Female Voice]",
        value,
        flags=re.I,
    )
    return value


def female_section_labels_equivalent(original: str, candidate: str) -> bool:
    return str(candidate or "") == normalize_female_section_labels(str(original or ""))


def _range_values(text: str, label_pattern: str) -> List[Tuple[int, int]]:
    values: List[Tuple[int, int]] = []
    for match in re.finditer(
        rf"(?:{label_pattern})[^0-9]{{0,18}}(\d{{1,2}})\s*(?:-|–|~|to)\s*(\d{{1,2}})\s*%?",
        text,
        re.I,
    ):
        lo, hi = int(match.group(1)), int(match.group(2))
        if lo > hi:
            lo, hi = hi, lo
        values.append((lo, hi))
    return values


def _ranges_conflict(left: List[Tuple[int, int]], right: List[Tuple[int, int]]) -> bool:
    if not left or not right:
        return False
    # If stylePrompt declares a fixed channel range, any additional vocalDesign
    # section range that is fully disjoint from every style range is a conflict.
    # Example: style breath 10-20 plus legacy Verse breathiness 35-45.
    return any(
        all(max(a, c) > min(b, d) for a, b in left)
        for c, d in right
    )


def japanese_positive_controls(style_prompt: str) -> Dict[str, bool]:
    low = str(style_prompt or "").casefold()
    return {
        "closeMic": "close-mic" in low or "close mic" in low,
        "nativeDiction": any(x in low for x in (
            "jp-native diction", "jp native diction", "native japanese diction",
            "native contemporary japanese diction", "native jp diction",
        )),
        "moraTiming": "mora" in low,
        "sentenceAccent": any(x in low for x in (
            "sentence accent", "pitch-accent", "pitch accent",
        )),
    }


def v061_track_findings(
    row: Dict[str, Any],
    source_context: Dict[str, Any] | None = None,
) -> List[Dict[str, str]]:
    """Return actionable v0.6.1 consistency findings for one track.

    These checks are intentionally narrow. They do not try to infer musical
    quality; they catch internal control conflicts that can make a good prompt
    less repeatable.
    """
    findings: List[Dict[str, str]] = []
    style = str(row.get("stylePrompt", ""))
    vocal_design = _text(row.get("vocalDesign", ""))
    phonation_design = _text(row.get("phonationDesign", ""))
    role = _vocal_role(row)

    if is_female_only_track(row, source_context):
        controls = female_single_voice_controls(style)
        missing = [name for name, ok in controls.items() if not ok]
        risks = female_positive_voice_risks(row)
        if missing or risks:
            risk_text = ", ".join(f"{field}:{label}" for field, label in risks[:12])
            details = []
            if missing:
                details.append("missing affirmative controls=" + ", ".join(missing))
            if risk_text:
                details.append("risky positive tokens=" + risk_text)
            findings.append({
                "area": "female_voice_isolation",
                "reason": "Female-only generation controls are not isolated to one affirmative solo voice: " + "; ".join(details) + ".",
                "expectedImprovement": (
                    "Use affirmative single-female wording in positive generation fields, keep one identical unlayered female timbre "
                    "through Verse/Chorus/Bridge/Final, move wrong-gender terms to excludePrompt/negativeStyleText only, and replace "
                    "self-response/self-answer/self-double/stack cues with same-solo-female wording."
                ),
            })

    if _is_japanese_source(source_context, row) and role not in {"instrumental", "unknown"}:
        controls = japanese_positive_controls(style)
        missing = [name for name, ok in controls.items() if not ok]
        if missing:
            findings.append({
                "area": "jp_native_positive_controls",
                "reason": "Actual stylePrompt is missing explicit positive Japanese-vocal controls: " + ", ".join(missing) + ".",
                "expectedImprovement": "More repeatable native Japanese diction/mora/accent behavior instead of relying only on exclusions or nationality labels.",
            })

    style_breath = _range_values(style, r"breath(?:iness)?|breath texture")
    design_breath = _range_values(vocal_design + " " + phonation_design, r"breath(?:iness)?|breath texture")
    style_grain = _range_values(style, r"grain|dry grain")
    design_grain = _range_values(vocal_design + " " + phonation_design, r"grain|dry grain")

    conflict_bits: List[str] = []
    if _ranges_conflict(style_breath, design_breath):
        conflict_bits.append(f"breath style={style_breath} vocalDesign={design_breath}")
    if _ranges_conflict(style_grain, design_grain):
        conflict_bits.append(f"grain style={style_grain} vocalDesign={design_grain}")

    # Current CHILI v15 male/female channel coordinates use one fixed channel
    # fingerprint across sections. Legacy high section-specific breath ranges
    # are a known source of contradiction when the stylePrompt carries a much
    # lower fixed range.
    if conflict_bits:
        findings.append({
            "area": "vocal_design_consistency",
            "reason": "stylePrompt and vocalDesign contain conflicting phonation coordinates: " + "; ".join(conflict_bits),
            "expectedImprovement": "One recurring singer fingerprint across Verse/Chorus/Bridge/Final with section differences expressed through phrasing/density rather than contradictory breath/grain coordinates.",
        })

    # v0.6.1 compiler order for Chill Rap: genre/tint -> BPM+groove -> singer -> phonation/JP-native -> rap pocket.
    if style.lstrip().casefold().startswith("chill rap,"):
        low = style.casefold()
        bpm = re.search(r"\b\d{2,3}\s*bpm\b", low)
        groove = re.search(r"\b(?:groove|pocket|head-nod|2-step|broken-beat|boom-bap|swing|backbeat)\b", low)
        singer = re.search(r"\b(?:male|female|duet|tenor|baritone|mezzo|soprano|alto)\b", low)
        if bpm and groove and singer and not (bpm.start() <= groove.start() < singer.start()):
            findings.append({
                "area": "prompt_ordering",
                "reason": "For Chill Rap v0.6.1, BPM+groove should be established before the singer/phonation lock.",
                "expectedImprovement": "The model sees dominant genre and rhythmic pocket before voice-detail density.",
            })

    return findings


def v061_result_failures(
    row: Dict[str, Any],
    source_context: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    failures: List[Dict[str, Any]] = []
    no = row.get("trackNo")
    for finding in v061_track_findings(row, source_context):
        area = finding["area"]
        code = {
            "jp_native_positive_controls": "JP_NATIVE_POSITIVE_CONTROLS_MISSING",
            "vocal_design_consistency": "VOCAL_DESIGN_CONFLICT",
            "female_voice_isolation": "FEMALE_VOICE_ISOLATION_RISK",
            "prompt_ordering": "PROMPT_ORDER_V061",
        }.get(area, "V061_QUALITY_GATE")
        failures.append({
            "level": "FAIL",
            "code": code,
            "trackNo": no,
            "message": finding["reason"],
        })
    return failures
