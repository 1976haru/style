from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES_PATH = ROOT / "data" / "prompt_intelligence_rules.json"

IMMUTABLE_FIELD_NAMES = {
    "title", "titleLocalized", "lyrics", "hookPhrase", "hook", "story", "storyAct",
    "storyActLabel", "storyArcRole", "scene", "listenerSituation", "emotionArc",
    "relationshipBoundary", "relationshipBoundaries", "relationshipState", "episodeBoundary",
}


def load_prompt_intelligence_rules(path: str | Path = DEFAULT_RULES_PATH) -> Dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Prompt Intelligence 규칙을 읽을 수 없습니다: {exc}") from exc
    areas = data.get("areas") if isinstance(data, dict) else None
    if not isinstance(areas, dict) or not areas:
        raise ValueError("prompt_intelligence_rules.json에 areas object가 필요합니다.")
    return deepcopy(data)


def _songs(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    for key in ("songs", "tracks", "preassignedSongs"):
        rows = source.get(key)
        if isinstance(rows, list):
            return [x for x in rows if isinstance(x, dict)]
    return []


def _split_atoms(text: str) -> List[str]:
    return [re.sub(r"\s+", " ", x).strip() for x in re.split(r"[;,|]+", text or "") if x.strip()]


def _duplicates(text: str) -> List[str]:
    seen, dupes = set(), []
    for atom in _split_atoms(text):
        key = atom.casefold()
        if key in seen and key not in dupes:
            dupes.append(key)
        seen.add(key)
    return dupes


_QUALITY_STOPWORDS = {
    "the", "and", "with", "from", "into", "then", "that", "this", "only",
    "track", "style", "prompt", "section", "desired", "before", "after",
}
_SINGER_IDENTITY_TOKENS = {
    "male", "female", "tenor", "baritone", "soprano", "alto", "mezzo", "singer",
    "vocal", "voice", "recurring", "japanese", "solo", "duet",
}


def _quality_tokens(text: Any, *, omit_singer: bool = False) -> set[str]:
    tokens = {
        token for token in re.findall(r"[a-z0-9]+", str(text or "").casefold())
        if len(token) > 2 and token not in _QUALITY_STOPWORDS
    }
    return tokens - _SINGER_IDENTITY_TOKENS if omit_singer else tokens


def _section_text(style: str, section: str) -> str:
    # Semicolons/pipes delimit major controls; commas often continue the same
    # Bridge or Final instruction and must remain available for axis matching.
    atoms = [re.sub(r"\s+", " ", x).strip() for x in re.split(r"[;|]+", style or "") if x.strip()]
    return " ".join(atom for atom in atoms if section.casefold() in atom.casefold())


def _near_duplicate_atoms(style: str) -> bool:
    atoms = [_quality_tokens(atom) for atom in _split_atoms(style)]
    for i, left in enumerate(atoms):
        if len(left) < 3:
            continue
        for right in atoms[i + 1:]:
            if len(right) < 3:
                continue
            if len(left & right) / len(left | right) >= 0.72:
                return True
    return False


def _axis_parts(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    return [x.strip() for x in re.split(r"\s*\+\s*|[;,|/]+", str(value or "")) if x.strip()]


def _axis_is_represented(axis: str, section_text: str) -> bool:
    axis_tokens = _quality_tokens(axis)
    section_tokens = _quality_tokens(section_text)
    if axis_tokens & section_tokens:
        return True
    semantic_groups = (
        r"drum|kick|snare|rim|hat|percussion|backbeat|rhythm",
        r"bass|sub|lowend",
        r"texture|instrument|guitar|piano|rhodes|keys|pad|density|sparse|layer",
        r"harmon|chord|key|modal|progress|voic|cadence",
        r"register|octave|pitch|range",
        r"vocal|voice|delivery|distance|whisper|spoken|speech|phrase|diction",
        r"space|reverb|dry|wide|mono|stereo|room|mix|filter",
        r"dynamic|energy|loud|soft|intens|volume",
        r"melod|motif|hook|counter",
    )
    return any(re.search(group, axis, re.I) and re.search(group, section_text, re.I) for group in semantic_groups)


def _append_weakness(track: Dict[str, Any], area: str, reason: str, improvement: str) -> None:
    if area not in {x.get("area") for x in track["weaknesses"]}:
        track["weaknesses"].append({"area": area, "reason": reason, "expectedImprovement": improvement})
        track["qualityOpportunityCount"] = len(track["weaknesses"])


def _track_analysis(row: Dict[str, Any], rules: Dict[str, Any], target_model: str = "") -> Dict[str, Any]:
    style = str(row.get("stylePrompt", ""))
    exclude = str(row.get("excludePrompt") or row.get("negativeStyleText", ""))
    all_excludes = " ".join(str(row.get(k, "")) for k in ("excludePrompt", "negativeStyleText"))
    music_fields = " ".join(
        str(row.get(key, "")) for key in (
            "genreText", "genre", "vocalDesign", "vocalType", "phonation", "groove", "grooveDesign",
            "drums", "drumDesign", "bass", "bassDesign", "instrumentation", "instrumentationDesign",
            "harmonicDesign", "verseBehavior", "chorusBehavior", "bridgeDesign", "finalDesign",
            "durationDesign", "performanceSignature", "generationRunHint",
        )
    )
    blob = (style + " " + music_fields).casefold()
    weaknesses: List[Dict[str, str]] = []

    def weak(area: str, reason: str, improvement: str) -> None:
        weaknesses.append({"area": area, "reason": reason, "expectedImprovement": improvement})

    if not re.search(r"\b(?:rap|pop|rock|soul|house|jazz|ballad|chanson|ambient|folk|r&b)\b", blob):
        weak("genre_clarity", "Dominant genre is absent or unclear.", "More consistent generations and less genre drift.")
    try:
        bpm = int(row.get("BPM", row.get("bpm", 0)))
    except (TypeError, ValueError):
        bpm = 0
    if not 30 <= bpm <= 240:
        weak("tempo_design", "BPM is missing or outside the plausible 30-240 range.", "More intentional energy and fewer malformed tempo instructions.")
    if not re.search(r"\b(?:male|female|duet|instrumental|tenor|baritone|mezzo|soprano|alto)\b", blob):
        weak("vocal_identity", "Stable vocal identity is not explicit.", "Lower singer-identity drift across renders.")
    if not re.search(r"breath|grain|resonance|chest|head voice|phonation|supported|speech-forward|whisper", blob):
        weak("phonation", "Phonation is generic or unspecified.", "More repeatable vocal texture and diction.")
    if not re.search(r"groove|pocket|syncopat|swing|behind.the.beat|off.beat|four-on-the-floor", blob):
        weak("groove", "Groove behavior is not audible from the prompt.", "Clearer rhythmic pocket.")
    if not re.search(r"kick|snare|rim|hat|drum|percussion|backbeat", blob):
        weak("drums", "Drum language is missing.", "More controlled transient character.")
    if not re.search(r"bass|sub|low-end", blob):
        weak("bass", "Bass motion/register is missing.", "Stronger groove foundation without low-end guesswork.")
    if not re.search(r"guitar|piano|keys|rhodes|synth|strings|accordion|pad|pluck", blob):
        weak("instrumentation", "No focused instrumental palette is stated.", "More distinctive but coherent arrangement color.")
    if not re.search(r"chord|harmony|harmonic|seventh|ninth|modal|progression|voicing", blob):
        weak("harmony", "Harmony is described only by mood or not at all.", "More intentional tension and release.")
    if "verse" not in blob:
        weak("verse_behavior", "Verse delivery behavior is missing.", "Better control of density and phrasing.")
    if not re.search(r"chorus|hook", blob):
        weak("chorus_behavior", "Chorus/hook lift is missing.", "A more legible memorable payoff.")
    if "bridge" not in blob:
        weak("bridge_contrast", "Bridge contrast is not explicit.", "Less structure drift and stronger late-song contrast.")
    if "final" not in blob and "outro" not in blob:
        weak("final_payoff", "Final payoff is not explicit.", "Lower early-ending risk.")
    if not str(row.get("performanceSignature", "")).strip():
        weak("performance_signature", "Track-specific performance behavior is absent.", "More delivery variety without changing singer identity.")
    if not str(row.get("durationDesign", row.get("duration", ""))).strip():
        weak("duration_design", "Duration target is absent.", "More controlled song length and fewer early endings.")
    if not str(row.get("generationRunHint", "")).strip():
        weak("generation_hint", "Track-specific generation guidance is absent.", "Clearer guard against the track's most likely generation failure.")
    style_atoms = _split_atoms(style)
    order_text = " ".join(style_atoms).casefold()
    order_terms = [
        re.search(r"\b(?:rap|pop|rock|soul|house|jazz|ballad|chanson|ambient|folk)\b", order_text),
        re.search(r"\b\d{2,3}\s*bpm\b", order_text),
        re.search(r"\b(?:male|female|duet|instrumental|tenor|baritone|mezzo|soprano)\b", order_text),
        re.search(r"\b(?:groove|pocket|syncopat|swing|backbeat)\w*\b", order_text),
    ]
    positions = [m.start() for m in order_terms if m]
    if len(positions) >= 2 and positions != sorted(positions):
        weak("prompt_ordering", "Key prompt atoms are not ordered from genre/tempo/vocal into groove.", "Improved attention to the dominant identity and more reliable prompt parsing.")
    if target_model and not re.search(r"\b(?:section|bar|bpm|style prompt|exclude)\b", style, re.I):
        weak("model_specific_behavior", f"Prompt has no structured musical cues for target model {target_model}.", "More reliable interpretation by the selected generation model.")
    elif not target_model:
        weak("model_specific_behavior", "No explicit generation model target is available in source metadata.", "Model-specific syntax can be selected deliberately when a target is known.")
    if len(style) < int(rules["policy"]["targetPromptChars"]["min"]):
        weak("prompt_length", f"stylePrompt is only {len(style)} characters.", "Enough concrete control without adjective padding.")
    elif len(style) > int(rules["policy"]["targetPromptChars"]["max"]):
        weak("prompt_length", f"stylePrompt is {len(style)} characters.", "Less instruction dilution and truncation risk.")
    dupes = _duplicates(style)
    if dupes:
        weak("redundancy", "Repeated prompt atoms: " + ", ".join(dupes[:5]), "Higher information density.")
    # Only mutually exclusive desired states count as contradictions. Ordinary
    # shared words between a positive style and an exclusion are not conflicts:
    # e.g. “male tenor” + “exclude generic polished tenor” is coherent.
    semantic_conflicts = (
        (r"\binstrumental(?:-only)?\b", r"\blead vocal(?:s)?\b", "instrumental and lead vocal both desired"),
        (r"\bsparse (?:arrangement|texture|production)\b", r"\bdense (?:wall|arrangement|texture)\b", "sparse and dense arrangement both desired"),
        (r"\bacoustic-only\b", r"\bfully-electronic-only\b", "acoustic-only and fully-electronic-only both desired"),
        (r"\bno reverb\b", r"\b(?:long|large) reverb\b", "no reverb and long/large reverb both desired"),
        (r"\bslow(?:-tempo)?\b", r"\bfast(?:-tempo)?\b", "slow and fast tempo both desired"),
    )
    contradictions = [label for left, right, label in semantic_conflicts if re.search(left, style, re.I) and re.search(right, style, re.I)]
    if re.search(r"\bwhisper[- ]only\b", style, re.I) and re.search(r"\bwhisper[- ]only\b", all_excludes, re.I):
        contradictions.append("whisper-only desired and excluded")
    contradictions.extend(
        label for left, right, label in semantic_conflicts
        if re.search(left, style, re.I) and re.search(right, all_excludes, re.I)
    )
    if contradictions:
        weak("contradiction", "Semantic conflicts: " + "; ".join(dict.fromkeys(contradictions)), "Fewer mutually cancelling instructions.")
    if len(_split_atoms(exclude)) > 16 or _duplicates(exclude):
        weak("exclude_efficiency", "Exclude list is long or repetitive.", "More targeted negative conditioning.")
    return {
        "trackNo": row.get("trackNo"),
        "title": row.get("title", ""),
        "existingStylePrompt": style,
        "existingExclude": exclude,
        "weaknesses": weaknesses,
        "qualityOpportunityCount": len(weaknesses),
    }


def analyze_current_prompt(source: Dict[str, Any], rules: Dict[str, Any] | None = None) -> Dict[str, Any]:
    rules = rules or load_prompt_intelligence_rules()
    meta = source.get("meta") if isinstance(source.get("meta"), dict) else {}
    target_model = str(meta.get("sunoModelTarget", meta.get("model", "")))
    rows = _songs(source)
    tracks = [_track_analysis(row, rules, target_model) for row in rows]

    # Higher-order checks are conservative: shared singer identity is expected
    # across a set and is removed from similarity scoring.
    for row, track in zip(rows, tracks):
        style = str(row.get("stylePrompt", ""))
        if _near_duplicate_atoms(style):
            _append_weakness(
                track, "information_density",
                "Semantically overlapping stylePrompt atoms repeat the same control.",
                "More musical control per prompt atom without removing distinct behavior.",
            )
        bridge = row.get("bridgeDesign")
        if isinstance(bridge, dict):
            axes = _axis_parts(bridge.get("changeAxes"))
            bridge_text = _section_text(style, "bridge")
            covered = sum(_axis_is_represented(axis, bridge_text) for axis in axes)
            required = 3 if str(row.get("trackRole", "")).casefold() == "anchor" else 2
            if len(axes) >= required and covered < required:
                _append_weakness(
                    track, "bridge_specificity",
                    f"Bridge style text represents {covered} of {len(axes)} declared audible change axes; {required} are required.",
                    "A track-specific Bridge whose audible axes agree with bridgeDesign.",
                )

    has_structured_sections = all(
        isinstance(row.get("bridgeDesign"), dict) and isinstance(row.get("highlightDesign"), dict)
        for row in rows
    )
    if len(rows) >= 3 and has_structured_sections:
        styles = [str(row.get("stylePrompt", "")) for row in rows]
        distinctive = [_quality_tokens(style, omit_singer=True) for style in styles]
        overly_similar: set[int] = set()
        for i, left in enumerate(distinctive):
            peers = 0
            for j, right in enumerate(distinctive):
                if i == j or not (left | right):
                    continue
                if len(left & right) / len(left | right) >= 0.82:
                    peers += 1
            if peers >= max(2, len(rows) // 3):
                overly_similar.add(i)
        for i in overly_similar:
            _append_weakness(
                tracks[i], "template_similarity",
                "Non-singer groove, instrumentation, performance, Bridge and Final controls are overly similar across the set.",
                "More track-level musical differentiation while retaining the recurring singer.",
            )

        final_sections = [_section_text(style, "final") or _section_text(style, "outro") for style in styles]
        final_counts = {text: final_sections.count(text) for text in set(final_sections) if text}
        highlight_variants = {
            json.dumps(row.get("highlightDesign"), ensure_ascii=False, sort_keys=True) for row in rows
            if row.get("highlightDesign")
        }
        if len(highlight_variants) > 1:
            for i, (row, section) in enumerate(zip(rows, final_sections)):
                if not section or final_counts.get(section, 0) < max(3, len(rows) // 2):
                    continue
                highlight = row.get("highlightDesign")
                payoff = highlight.get("harmonicPayoff", "") if isinstance(highlight, dict) else ""
                payoff_tokens = _quality_tokens(payoff)
                if payoff_tokens and not payoff_tokens.intersection(_quality_tokens(section)):
                    _append_weakness(
                        tracks[i], "final_specificity",
                        "A repeated generic Final omits this track's declared highlight payoff.",
                        "A Final instruction tied to the track-specific highlight behavior.",
                    )

        signatures = [str(row.get("performanceSignature", "")).strip().casefold() for row in rows]
        signature_counts = {value: signatures.count(value) for value in set(signatures) if value}
        for i, signature in enumerate(signatures):
            if i in overly_similar and signature_counts.get(signature, 0) >= max(3, len(rows) // 2):
                _append_weakness(
                    tracks[i], "track_specificity",
                    "The same performance signature and high-similarity style template recur across the set.",
                    "A concrete track-specific performance cue without changing singer identity.",
                )
    counts: Dict[str, int] = {}
    for track in tracks:
        for item in track["weaknesses"]:
            counts[item["area"]] = counts.get(item["area"], 0) + 1
    ranked = sorted(counts.items(), key=lambda x: (-x[1], -int(rules["areas"][x[0]]["priority"]), x[0]))
    return {
        "analysisType": "CURRENT_MUSIC_DESIGN_BASELINE",
        "versionUsedAsQualitySignal": False,
        "trackCount": len(tracks),
        "weaknessCounts": dict(ranked),
        "tracks": tracks,
        "note": "Source version labels are intentionally ignored; findings come from current musical fields only.",
    }


def immutable_snapshot(source: Dict[str, Any]) -> Dict[str, Any]:
    rows = _songs(source)
    return {
        str(row.get("trackNo", i)): {k: deepcopy(v) for k, v in row.items() if k in IMMUTABLE_FIELD_NAMES}
        for i, row in enumerate(rows, 1)
    }


def verify_immutable_fields(source: Dict[str, Any], result: Dict[str, Any]) -> List[Dict[str, Any]]:
    expected = immutable_snapshot(source)
    actual = immutable_snapshot(result)
    issues = []
    for no, fields in expected.items():
        if no not in actual:
            issues.append({"level": "FAIL", "code": "IMMUTABLE_TRACK_MISSING", "trackNo": no})
            continue
        for key, value in fields.items():
            if actual[no].get(key) != value:
                issues.append({"level": "FAIL", "code": "IMMUTABLE_CHANGED", "trackNo": no, "field": key})
    return issues


def build_old_new_comparison(source: Dict[str, Any], result: Dict[str, Any]) -> List[Dict[str, Any]]:
    old_rows = {str(x.get("trackNo", i)): x for i, x in enumerate(_songs(source), 1)}
    comparisons = []
    for i, new in enumerate(_songs(result), 1):
        no = str(new.get("trackNo", i))
        old = old_rows.get(no, {})
        audit = new.get("promptOptimization") if isinstance(new.get("promptOptimization"), dict) else {}
        comparisons.append({
            "trackNo": new.get("trackNo", i),
            "title": old.get("title", ""),
            "existingStylePrompt": old.get("stylePrompt", ""),
            "newStylePrompt": new.get("stylePrompt", ""),
            "changeReasons": audit.get("changeReasons", []),
            "expectedImprovements": audit.get("expectedImprovements", []),
        })
    return comparisons


OPTIMIZED_MUSIC_FIELDS = (
    "BPM", "genreId", "genreText", "vocalDesign", "harmonicDesign", "stylePrompt",
    "excludePrompt", "negativeStyleText", "performanceSignature", "generationRunHint",
    "bridgeDesign", "highlightDesign", "finalDesign", "durationDesign", "grooveDesign",
    "drumDesign", "bassDesign", "instrumentationDesign", "verseBehavior", "chorusBehavior",
)

WEAKNESS_FIELDS = {
    "tempo_design": {"BPM"},
    "genre_clarity": {"genreId", "genreText", "stylePrompt"},
    "vocal_identity": {"vocalDesign", "stylePrompt"},
    "phonation": {"vocalDesign", "stylePrompt"},
    "groove": {"grooveDesign", "stylePrompt"},
    "drums": {"drumDesign", "stylePrompt"},
    "bass": {"bassDesign", "stylePrompt"},
    "instrumentation": {"instrumentationDesign", "stylePrompt"},
    "harmony": {"harmonicDesign", "stylePrompt"},
    "verse_behavior": {"verseBehavior", "stylePrompt"},
    "chorus_behavior": {"chorusBehavior", "stylePrompt"},
    "bridge_contrast": {"bridgeDesign", "stylePrompt"},
    "final_payoff": {"finalDesign", "highlightDesign", "stylePrompt"},
    "prompt_ordering": {"stylePrompt"},
    "redundancy": {"stylePrompt", "excludePrompt", "negativeStyleText"},
    "contradiction": {"stylePrompt", "excludePrompt", "negativeStyleText"},
    "exclude_efficiency": {"excludePrompt", "negativeStyleText"},
    "prompt_length": {"stylePrompt"},
    "model_specific_behavior": {"stylePrompt", "generationRunHint"},
    "performance_signature": {"performanceSignature", "stylePrompt"},
    "duration_design": {"durationDesign", "stylePrompt"},
    "generation_hint": {"generationRunHint"},
    "information_density": {"stylePrompt"},
    "track_specificity": {"performanceSignature", "stylePrompt"},
    "bridge_specificity": {"bridgeDesign", "stylePrompt"},
    "final_specificity": {"highlightDesign", "finalDesign", "stylePrompt"},
    "template_similarity": {"grooveDesign", "instrumentationDesign", "performanceSignature", "bridgeDesign", "highlightDesign", "finalDesign", "stylePrompt"},
}


def _analysis_by_track(analysis: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {str(x.get("trackNo", i)): x for i, x in enumerate(analysis.get("tracks", []), 1)}


def _rows_by_track(source: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {str(row.get("trackNo", i)): row for i, row in enumerate(_songs(source), 1)}


def validate_optimization_effectiveness(
    source: Dict[str, Any],
    optimized: Dict[str, Any],
    before_analysis: Dict[str, Any],
    after_analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """Compare actual music-field diffs with actionable weaknesses and model claims."""
    old_rows, new_rows = _rows_by_track(source), _rows_by_track(optimized)
    before_tracks = _analysis_by_track(before_analysis)
    after_tracks = _analysis_by_track(after_analysis)
    issues: List[Dict[str, Any]] = []
    comparisons: List[Dict[str, Any]] = []
    changed_counts: Dict[str, int] = {}
    changed_track_count = 0
    total_before = total_after = resolved_count = 0

    for no, old in old_rows.items():
        new = new_rows.get(no)
        if new is None:
            issues.append({"level": "FAIL", "code": "OPTIMIZATION_TRACK_MISSING", "trackNo": no})
            continue
        before = before_tracks.get(no, {})
        after = after_tracks.get(no, {})
        before_items = before.get("weaknesses", [])
        after_items = after.get("weaknesses", [])
        before_areas = {str(x.get("area")) for x in before_items}
        after_areas = {str(x.get("area")) for x in after_items}
        total_before += len(before_items)
        total_after += len(after_items)
        resolved = sorted(before_areas - after_areas)
        remaining = sorted(before_areas & after_areas)
        resolved_count += sum(1 for x in before_items if x.get("area") not in after_areas)

        newly_added = sorted(after_areas - before_areas)
        if "contradiction" in newly_added:
            issues.append({"level": "FAIL", "code": "NEW_CONTRADICTION_REGRESSION", "trackNo": no})
        if "redundancy" in newly_added:
            issues.append({"level": "FAIL", "code": "DUPLICATE_HEAVY_PROMPT_REGRESSION", "trackNo": no})
        if "exclude_efficiency" in before_areas and "exclude_efficiency" in after_areas:
            issues.append({"level": "FAIL", "code": "EXCLUDE_COMPRESSION_INCOMPLETE", "trackNo": no})

        changed = [field for field in OPTIMIZED_MUSIC_FIELDS if old.get(field) != new.get(field)]
        if changed:
            changed_track_count += 1
            for field in changed:
                changed_counts[field] = changed_counts.get(field, 0) + 1

        unresolved_areas = []
        for area in sorted(before_areas):
            related = WEAKNESS_FIELDS.get(area, set())
            if not related.intersection(changed):
                unresolved_areas.append(area)
        if before.get("qualityOpportunityCount", len(before_items)) > 0 and not changed:
            issues.append({
                "level": "FAIL", "code": "OPTIMIZATION_NOOP", "trackNo": no,
                "unresolvedAreas": sorted(before_areas),
                "message": "Actionable weaknesses were found but no music field changed.",
            })
        elif unresolved_areas:
            issues.append({
                "level": "FAIL", "code": "OPTIMIZATION_NOOP", "trackNo": no,
                "unresolvedAreas": unresolved_areas,
                "message": "No field related to one or more actionable weaknesses changed.",
            })
        if before_items and not resolved:
            issues.append({
                "level": "FAIL", "code": "OPTIMIZATION_NO_GAIN", "trackNo": no,
                "unresolvedAreas": sorted(before_areas),
                "message": "Music fields changed but the analysis found no resolved weakness.",
            })

        audit = new.get("promptOptimization") if isinstance(new.get("promptOptimization"), dict) else {}
        claimed_changed = audit.get("changedFields")
        if claimed_changed is not None and sorted(set(claimed_changed)) != sorted(changed):
            issues.append({"level": "FAIL", "code": "CLAIMED_CHANGED_FIELDS_MISMATCH", "trackNo": no, "actual": changed, "claimed": claimed_changed})
        claimed_resolved = audit.get("resolvedWeaknesses")
        if isinstance(claimed_resolved, list):
            false_claims = sorted(set(str(x) for x in claimed_resolved) - set(resolved))
            if false_claims:
                issues.append({"level": "FAIL", "code": "CLAIMED_WEAKNESS_UNRESOLVED", "trackNo": no, "unresolvedAreas": false_claims})
        if audit.get("status") == "KEEP":
            if before_items:
                issues.append({"level": "FAIL", "code": "KEEP_WITH_ACTIONABLE_WEAKNESS", "trackNo": no, "unresolvedAreas": sorted(before_areas)})
            if changed:
                issues.append({"level": "FAIL", "code": "KEEP_WITH_CHANGED_FIELDS", "trackNo": no})
            if not str(audit.get("keepReason", "")).strip():
                issues.append({"level": "FAIL", "code": "KEEP_REASON_MISSING", "trackNo": no})

        for prompt_key, field in (("oldStylePrompt", "stylePrompt"), ("newStylePrompt", "stylePrompt"), ("oldExcludePrompt", "excludePrompt"), ("newExcludePrompt", "excludePrompt")):
            if prompt_key in audit:
                if prompt_key == "oldStylePrompt":
                    expected = old.get("stylePrompt", "")
                elif prompt_key == "oldExcludePrompt":
                    expected = old.get("excludePrompt") or old.get("negativeStyleText", "")
                elif prompt_key == "newExcludePrompt":
                    expected = new.get("excludePrompt") or new.get("negativeStyleText", "")
                else:
                    expected = new.get(field, "")
                if audit[prompt_key] != expected:
                    issues.append({"level": "FAIL", "code": f"{prompt_key.upper()}_MISMATCH", "trackNo": no})
        if "stylePrompt" in changed and (new.get("stylePrompt") == old.get("stylePrompt")):
            issues.append({"level": "FAIL", "code": "STYLE_PROMPT_CLAIM_WITHOUT_DIFF", "trackNo": no})
        if (audit.get("changeReasons") or audit.get("expectedImprovements")) and not changed:
            issues.append({"level": "FAIL", "code": "AUDIT_WITHOUT_FIELD_DIFF", "trackNo": no})

        comparisons.append({
            "trackNo": new.get("trackNo", no),
            "changedFields": changed,
            "beforeOpportunityCount": len(before_items),
            "afterOpportunityCount": len(after_items),
            "resolvedAreas": resolved,
            "remainingAreas": sorted(after_areas),
            "unresolvedAreas": remaining,
        })

    report = {
        "changedTrackCount": changed_track_count,
        "unchangedTrackCount": max(0, len(old_rows) - changed_track_count),
        "changedFieldCounts": dict(sorted(changed_counts.items())),
        "totalWeaknessBefore": total_before,
        "totalWeaknessAfter": total_after,
        "resolvedWeaknessCount": resolved_count,
        "optimizationEffective": not issues and (total_before == 0 or total_after < total_before),
    }
    if total_before and total_after >= total_before:
        issues.append({"level": "FAIL", "code": "SET_NO_IMPROVEMENT", "message": "Set-level weakness count did not decrease."})
        report["optimizationEffective"] = False
    return {"issues": issues, "comparisons": comparisons, "report": report}
