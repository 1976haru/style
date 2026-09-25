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


def _track_analysis(row: Dict[str, Any], rules: Dict[str, Any], target_model: str = "") -> Dict[str, Any]:
    style = str(row.get("stylePrompt", ""))
    exclude = str(row.get("negativeStyleText", row.get("excludePrompt", "")))
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
    contradiction_pairs = (
        (r"\bwhisper\w*\b", r"\b(?:power belt|belting|shout\w*)\b"),
        (r"\bsparse\b", r"\bdense\b"),
        (r"\bslow\b", r"\bfast\b"),
        (r"\bacoustic\b", r"\bfully electronic\b"),
        (r"\binstrumental\b", r"\blead vocal\b"),
        (r"\bno (?:reverb|echo)\b", r"\b(?:large|long) (?:reverb|echo)\b"),
    )
    contradictions = [f"{a}/{b}" for a, b in contradiction_pairs if re.search(a, blob) and re.search(b, blob)]
    positive_tokens = {token for atom in style_atoms for token in re.findall(r"[\w-]+", atom.casefold())}
    negative_tokens = {token for atom in _split_atoms(exclude) for token in re.findall(r"[\w-]+", atom.casefold())}
    overlap = sorted(positive_tokens & negative_tokens)
    if contradictions or overlap:
        details = contradictions + overlap[:5]
        weak("contradiction", "Conflicting instructions: " + ", ".join(details[:8]), "Fewer mutually cancelling instructions.")
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
    tracks = [_track_analysis(row, rules, target_model) for row in _songs(source)]
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
