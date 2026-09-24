from __future__ import annotations
import hashlib, json, re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

@dataclass
class ParsedDirective:
    fingerprint: str
    raw_length: int
    episode_id: Optional[str] = None
    concept: Optional[str] = None
    story_pov: Optional[str] = None
    language: Optional[str] = None
    song_count: Optional[int] = None
    detected_bpms: List[int] = None
    detected_vocal_terms: List[str] = None
    detected_model_versions: List[str] = None
    has_already_used_lists: bool = False
    has_track_plan: bool = False
    likely_json: bool = False
    raw_json: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["detected_bpms"] = self.detected_bpms or []
        d["detected_vocal_terms"] = self.detected_vocal_terms or []
        d["detected_model_versions"] = self.detected_model_versions or []
        return d


def _first(patterns, text, flags=re.I|re.M):
    for p in patterns:
        m = re.search(p, text, flags)
        if m:
            return m.group(1).strip()
    return None


def _walk(obj, key_candidates):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in key_candidates and isinstance(v, (str, int, float, bool)):
                return v
        for v in obj.values():
            x = _walk(v, key_candidates)
            if x is not None:
                return x
    elif isinstance(obj, list):
        for v in obj:
            x = _walk(v, key_candidates)
            if x is not None:
                return x
    return None


def parse_directive(raw: str) -> ParsedDirective:
    raw = raw or ""
    fp = hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()[:16]
    result = ParsedDirective(fp, len(raw), detected_bpms=[], detected_vocal_terms=[], detected_model_versions=[])

    s = raw.strip()
    if s.startswith("{") or s.startswith("["):
        try:
            obj = json.loads(s)
            result.likely_json = True
            result.raw_json = obj
            result.episode_id = str(_walk(obj, {"episodeId","storyPlanEpisodeId","sourcePlanningEpisodeId","deliveryEpisodeId"}) or "") or None
            result.concept = str(_walk(obj, {"concept","conceptLabel","storyPovTitle","storySourceTitle","setName"}) or "") or None
            result.story_pov = str(_walk(obj, {"storyPov","pov"}) or "") or None
            result.language = str(_walk(obj, {"lyricLanguage","language"}) or "") or None
            count = _walk(obj, {"songCount"})
            if isinstance(count, (int,float)):
                result.song_count = int(count)
        except Exception:
            pass

    if not result.episode_id:
        result.episode_id = _first([
            r'\bEP\.?\s*0*(\d{1,4})\b',
            r'\bstoryPlanEpisodeId\s*[=:]\s*["\']?(\d{1,4})',
            r'\bdeliveryEpisodeId\s*[=:]\s*["\']?(\d{1,4})',
            r'^\s*0*(\d{1,4})[\.\s]'
        ], raw)
        if result.episode_id:
            result.episode_id = result.episode_id.zfill(3)

    if not result.concept:
        result.concept = _first([
            r'^\s*\d{1,4}\.?\s+([^\n—-]{3,80})',
            r'컨셉\s+([^\n]+)',
            r'conceptLabel["\']?\s*[:=]\s*["\']([^"\']+)'
        ], raw)

    if not result.story_pov:
        pov = _first([
            r'storyPov["\']?\s*[:=]\s*["\']?(male|female|dual|couple)',
            r'\b(彼のSTORY|彼女のSTORY|ふたりのSTORY)\b'
        ], raw)
        if pov:
            result.story_pov = {"彼のSTORY":"male","彼女のSTORY":"female","ふたりのSTORY":"dual"}.get(pov, pov.lower())

    if not result.language:
        if re.search(r'Japanese|日本語|일본어', raw, re.I): result.language = "Japanese"
        elif re.search(r'French|Français|불어|프랑스어', raw, re.I): result.language = "French"
        elif re.search(r'English|영어', raw, re.I): result.language = "English"
        elif re.search(r'Korean|한국어', raw, re.I): result.language = "Korean"

    if result.song_count is None:
        m = re.search(r'\b(\d{1,2})\s*(?:tracks|songs|곡)\b', raw, re.I)
        if m: result.song_count = int(m.group(1))
        elif "15곡" in raw or "15 tracks" in raw.lower(): result.song_count = 15

    bpms = [int(x) for x in re.findall(r'\b(\d{2,3})\s*BPM\b', raw, re.I)]
    result.detected_bpms = sorted(set(x for x in bpms if 30 <= x <= 300))[:80]

    vocab = [
        "baritone","tenor","alto","mezzo","soprano","contralto","whisper","breathy","husky",
        "crooner","falsetto","belt","rasp","grain","speech-forward","behind-the-beat"
    ]
    low = raw.lower()
    result.detected_vocal_terms = [v for v in vocab if v.lower() in low]
    result.detected_model_versions = sorted(set(re.findall(r'\bv(?:4(?:\.5)?|5(?:\.5)?|6(?:-wild|-mini)?)\b', raw, re.I)))
    result.has_already_used_lists = bool(re.search(r'alreadyUsed(?:Titles|Hooks|Scenes|LyricLines)', raw, re.I))
    result.has_track_plan = bool(re.search(r'(Track story arc map|SetPlan handoff|This pack.?s 15-track plan|preassignedSongs|\bTrack\s*1\b)', raw, re.I))
    return result
