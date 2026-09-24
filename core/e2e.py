from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any, Dict, List

from .compiler import compile_instruction
from .track_plan import extract_track_plan, recompute_track_plan, validate_track_plan
from .validator import validate_generated_json


LEGACY_VOCAL_MARKERS = (
    "soft male voice just above a whisper",
    "male baritone with lowered larynx",
    "full-voiced male tenor, firm glottal closure",
    "breath-mix: verse 35-45",
)


def _issue(level: str, code: str, message: str, track_no: int | None = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {"level": level, "code": code, "message": message}
    if track_no is not None:
        out["trackNo"] = track_no
    return out


def _songs(text: str) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    try:
        obj = json.loads(text)
    except Exception as exc:
        return [], [_issue("FAIL", "JSON_PARSE", str(exc))]
    value = obj.get("songs") if isinstance(obj, dict) else obj
    if not isinstance(value, list):
        return [], [_issue("FAIL", "NO_SONGS", "Expected a songs array.")]
    return [x for x in value if isinstance(x, dict)], []


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def _has_wrong_language(lyrics: str, language_policy: str) -> bool:
    letters = re.sub(r"\[[^]]+\]", "", lyrics or "")
    latin = len(re.findall(r"[A-Za-z]", letters))
    japanese = len(re.findall(r"[\u3040-\u30ff\u3400-\u9fff]", letters))
    policy = (language_policy or "").lower()
    if "japanese" in policy:
        return latin >= 40 and japanese == 0
    if "french" in policy:
        return japanese >= 20 and latin == 0
    return False


def _expected_gender(vocal: str) -> str:
    low = vocal.lower()
    if "exactly two" in low or "duet" in low:
        return "duet"
    if re.search(r"\bfemale\b", low):
        return "female"
    if re.search(r"\bmale\b", low):
        return "male"
    if "instrumental" in low:
        return "instrumental"
    return ""


def validate_e2e_output(
    generated_json: str,
    original_plan: List[Dict[str, Any]],
    recomputed_plan: List[Dict[str, Any]],
    recompute_meta: Dict[str, Any],
    preset: Dict[str, Any],
    expected_count: int = 15,
) -> List[Dict[str, Any]]:
    """Validate generated songs against both immutable input and recomputed music policy."""
    issues: List[Dict[str, Any]] = list(validate_generated_json(generated_json, preset))
    issues = [x for x in issues if x.get("code") != "OK"]
    songs, parse_issues = _songs(generated_json)
    issues.extend(parse_issues)
    if parse_issues:
        return issues
    if len(songs) != expected_count:
        issues.append(_issue("FAIL", "E2E_SONG_COUNT", f"Expected exactly {expected_count} songs; found {len(songs)}."))

    source = {int(r.get("trackNo", 0)): r for r in original_plan}
    current = {int(r.get("trackNo", 0)): r for r in recomputed_plan}
    seen_titles: Dict[str, int] = {}
    seen_hooks: Dict[str, int] = {}
    ranges = {k.lower(): tuple(v) for k, v in (recompute_meta.get("rangesUsed") or {}).items()}
    language = str(preset.get("language", ""))

    for index, song in enumerate(songs, 1):
        try:
            no = int(song.get("trackNo", index))
        except (TypeError, ValueError):
            no = index
        old = source.get(no)
        new = current.get(no)
        if not old or not new:
            issues.append(_issue("FAIL", "E2E_TRACK_MAPPING", "Generated track has no matching plan row.", no))
            continue
        trusted = old["trusted"]
        recomputed = new["recomputed"]
        comparisons = (
            ("title", trusted.get("title"), song.get("title"), "LOCK_TITLE"),
            ("hook", trusted.get("hookPhrase"), song.get("hookPhrase"), "LOCK_HOOK"),
            ("scene", trusted.get("listenerSituation") or trusted.get("scene"), song.get("listenerSituation") or song.get("scene"), "LOCK_SCENE"),
            ("story", trusted.get("storyAct") or trusted.get("storyActLabel") or trusted.get("storyArcRole"), song.get("storyAct") or song.get("storyActLabel") or song.get("storyArcRole"), "LOCK_STORY"),
        )
        for label, expected, actual, code in comparisons:
            if expected and _norm(expected) != _norm(actual):
                issues.append(_issue("FAIL", code, f"Locked {label} changed from {expected!r} to {actual!r}.", no))

        title = _norm(song.get("title"))
        hook = _norm(song.get("hookPhrase"))
        if title:
            if title in seen_titles:
                issues.append(_issue("FAIL", "DUPLICATE_TITLE", f"Duplicates track {seen_titles[title]} title.", no))
            seen_titles[title] = no
        if hook:
            if hook in seen_hooks:
                issues.append(_issue("FAIL", "DUPLICATE_HOOK", f"Duplicates track {seen_hooks[hook]} hook.", no))
            seen_hooks[hook] = no

        role = str(recomputed.get("musicRole", "Core"))
        actual_role = str(song.get("trackRole", song.get("musicRole", "")))
        if _norm(role) != _norm(actual_role):
            issues.append(_issue("FAIL", "MUSIC_ROLE", f"Expected {role}; got {actual_role!r}.", no))
        try:
            bpm = int(song.get("BPM"))
        except (TypeError, ValueError):
            bpm = -1
        bounds = ranges.get(role.lower())
        if bounds and not (int(bounds[0]) <= bpm <= int(bounds[1])):
            issues.append(_issue("FAIL", "ROLE_BPM_RANGE", f"{role} BPM {bpm} is outside {bounds[0]}-{bounds[1]}.", no))
        imported_bpm = old.get("importedMusic", {}).get("BPM")
        if imported_bpm != recomputed.get("BPM") and bpm == imported_bpm:
            issues.append(_issue("FAIL", "LEGACY_BPM_LEAK", f"Legacy BPM {bpm} leaked into final output.", no))

        genre = str(song.get("genre", song.get("genreText", "")))
        style = str(song.get("stylePrompt", ""))
        if _norm(genre) != _norm(recomputed.get("genre")):
            issues.append(_issue("FAIL", "GENRE_POLICY", f"Expected genre {recomputed.get('genre')!r}; got {genre!r}.", no))
        if len(style) > 1000:
            issues.append(_issue("FAIL", "STYLE_LENGTH", f"stylePrompt is {len(style)} characters; maximum is 1000.", no))
        structure = str(song.get("structure", "")) + " " + style
        if "bridge" not in structure.lower() or "final" not in structure.lower():
            issues.append(_issue("FAIL", "BRIDGE_FINAL", "Bridge and Final must both be explicit.", no))
        if role.lower() == "anchor" and not (re.search(r"final\s*a\s*\+\s*(?:final\s*)?b\s*\+", structure, re.I) or "post c" in structure.lower()):
            issues.append(_issue("FAIL", "ANCHOR_FINAL", "Anchor requires strengthened Final A+B+C/Post C.", no))

        vocal = str(song.get("vocalType", song.get("vocal", "")))
        expected_gender = _expected_gender(str(recomputed.get("vocal", "")))
        actual_gender = _expected_gender(vocal)
        if expected_gender and actual_gender != expected_gender:
            issues.append(_issue("FAIL", "WRONG_GENDER", f"Expected {expected_gender}; got {vocal!r}.", no))
        imported_vocal = _norm(old.get("importedMusic", {}).get("vocal"))
        if imported_vocal and imported_vocal != _norm(recomputed.get("vocal")) and imported_vocal in _norm(vocal + " " + style):
            issues.append(_issue("FAIL", "LEGACY_VOCAL_LEAK", "Legacy vocal description leaked into final output.", no))
        if any(marker in _norm(vocal + " " + style) for marker in LEGACY_VOCAL_MARKERS):
            issues.append(_issue("FAIL", "LEGACY_VOCAL_LEAK", "Known legacy vocal marker leaked into final output.", no))
        if expected_gender != "instrumental":
            signature = str(song.get("performanceSignature", ""))
            if len(signature.strip()) < 20 or re.search(r"^(?:generic|natural|emotional|good)\s+(?:male|female)?\s*vocal", signature, re.I):
                issues.append(_issue("FAIL", "GENERIC_VOCAL", "Performance signature is missing or generic.", no))
        if _has_wrong_language(str(song.get("lyrics", "")), language):
            issues.append(_issue("FAIL", "WRONG_LANGUAGE", f"Lyrics do not follow {language}.", no))
    if not issues:
        issues.append(_issue("PASS", "E2E_OK", "Full parse/recompute/compile/final-output comparison passed."))
    return issues


def run_e2e_harness(
    directive: str,
    generated_json: str,
    preset_id: str,
    preset: Dict[str, Any],
    recipe: Dict[str, Any],
    public_rules: Dict[str, Any],
    market_recipe: Dict[str, Any],
    custom_master: str = "",
    mode: str = "HYBRID",
    expected_count: int = 15,
) -> Dict[str, Any]:
    """Run the production boundaries and return an auditable old/new/final report."""
    original, parse_meta = extract_track_plan(directive, expected_count)
    original_snapshot = deepcopy(original)
    recomputed, recompute_meta = recompute_track_plan(original, preset_id, preset, market_recipe, custom_master)
    instruction, manifest, compile_qa = compile_instruction(
        directive, preset_id, preset, recipe, public_rules, mode=mode,
        custom_master=custom_master, market_recipe=market_recipe,
        song_count=expected_count, structured_track_plan=recomputed,
        track_plan_meta={**parse_meta, **recompute_meta},
    )
    harness_qa: List[Dict[str, Any]] = []
    harness_qa.extend(validate_track_plan(recomputed, expected_count))
    harness_qa.extend(validate_e2e_output(generated_json, original_snapshot, recomputed, recompute_meta, preset, expected_count))
    if mode in {"HYBRID", "MASTER_FIRST"}:
        if directive.strip() and directive.strip() in instruction:
            harness_qa.append(_issue("FAIL", "HYBRID_RAW_REINJECTION", "The full legacy directive was re-injected."))
        leaked = [x for x in LEGACY_VOCAL_MARKERS if x in instruction.casefold()]
        if leaked:
            harness_qa.append(_issue("FAIL", "HYBRID_LEGACY_VOCAL", f"Legacy vocal markers in compiled prompt: {leaked}."))
    failures = [x for x in harness_qa if x.get("level") == "FAIL"]
    final_songs, _ = _songs(generated_json)
    return {
        "passed": not failures,
        "summary": {"expectedTracks": expected_count, "parsedTracks": len(original), "finalTracks": len(final_songs), "failures": len(failures)},
        "parseMeta": parse_meta,
        "recomputeMeta": recompute_meta,
        "compiler": {"instruction": instruction, "manifest": manifest, "qa": compile_qa},
        "comparison": {"original": original_snapshot, "recomputed": recomputed, "final": final_songs},
        "qa": harness_qa,
    }
