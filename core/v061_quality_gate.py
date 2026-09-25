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
    blob = " ".join([
        str(context.get("lyricLanguage", "")),
        str(context.get("language", "")),
        str(context.get("channelId", "")),
        str(context.get("channelLabel", "")),
        str(row.get("vocalDesign", "")),
        str(row.get("stylePrompt", "")),
    ]).casefold()
    return any(token in blob for token in ("japanese", "日本語", "jp-native", "jp native", "tokyo chill"))


def _vocal_role(row: Dict[str, Any]) -> str:
    blob = " ".join([
        str(row.get("vocalType", "")),
        _text(row.get("vocalDesign", "")),
    ]).casefold()
    if "duet" in blob or ("male" in blob and "female" in blob):
        return "duet"
    if "female" in blob:
        return "female"
    if "male" in blob:
        return "male"
    if "instrumental" in blob:
        return "instrumental"
    return "unknown"


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
    role = _vocal_role(row)

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
    design_breath = _range_values(vocal_design, r"breath(?:iness)?|breath texture")
    style_grain = _range_values(style, r"grain|dry grain")
    design_grain = _range_values(vocal_design, r"grain|dry grain")

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
            "prompt_ordering": "PROMPT_ORDER_V061",
        }.get(area, "V061_QUALITY_GATE")
        failures.append({
            "level": "FAIL",
            "code": code,
            "trackNo": no,
            "message": finding["reason"],
        })
    return failures
