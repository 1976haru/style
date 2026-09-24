from __future__ import annotations
import json, re
from typing import Any, Dict, List


def analyze_directive_conflicts(raw: str, preset: Dict[str,Any]) -> List[Dict[str,str]]:
    issues=[]
    low=raw.lower()
    label=preset.get("label","")
    if "chili" in label.lower():
        bpms=[int(x) for x in re.findall(r'\b(\d{2,3})\s*bpm\b', low)]
        very_low=[x for x in bpms if x < 86]
        if very_low:
            issues.append({"level":"WARN","code":"LEGACY_LOW_BPM","message":f"Imported directive contains low BPM values {sorted(set(very_low))[:12]}; Hybrid mode should treat them as replaceable unless explicitly marked as current user override."})

    # For JSON directives, inspect only positive vocal-role fields. Exclude/negative
    # prompt text must not create a false gender conflict.
    positive_vocals=[]
    try:
        obj=json.loads(raw)
        songs=obj.get('songs') if isinstance(obj,dict) else obj if isinstance(obj,list) else []
        if isinstance(songs,list):
            for song in songs:
                if isinstance(song,dict):
                    for k in ('vocalType','vocalGender','vocalText'):
                        if song.get(k): positive_vocals.append(str(song.get(k)).lower())
    except Exception:
        for line in raw.splitlines():
            ll=line.lower()
            if re.search(r'negative|exclude|금지|no female|no male|without female|without male',ll):
                continue
            if re.search(r'vocal|lead|duet',ll): positive_vocals.append(ll)
    vocal_blob='\n'.join(positive_vocals)
    if "彼のSTORY" in label and re.search(r'\bfemale\b|\bduet\b|mixed vocal', vocal_blob):
        issues.append({"level":"WARN","code":"MALE_LOCK_CONFLICT","message":"Imported directive includes positive female/duet vocal assignments that may conflict with male-only channel lock."})
    if "彼女のSTORY" in label and re.search(r'\bmale\b|\bduet\b|mixed vocal', vocal_blob):
        issues.append({"level":"WARN","code":"FEMALE_LOCK_CONFLICT","message":"Imported directive includes positive male/duet vocal assignments that may conflict with female-only channel lock."})

    legacy=[]
    for t in ["lowered larynx","deep gravel","mature crooner","soft male voice just above a whisper","breath-mix: verse 35-45","v14.4","v14.3","v13"]:
        if t in low: legacy.append(t)
    if legacy:
        issues.append({"level":"INFO","code":"LEGACY_VOCAL_RULES","message":"Legacy vocal/prompt directives detected: "+", ".join(legacy[:6])+". Hybrid mode will keep story data but supersede outdated music/vocal instructions."})
    if not raw.strip():
        issues.append({"level":"INFO","code":"NO_DIRECTIVE","message":"No imported directive. Compiler will rely on channel preset + custom master + episode brief."})
    return issues


def validate_generated_json(text: str, preset: Dict[str,Any]) -> List[Dict[str,str]]:
    issues=[]
    try:
        obj=json.loads(text)
    except Exception as e:
        return [{"level":"FAIL","code":"JSON_PARSE","message":str(e)}]
    songs=obj.get("songs") if isinstance(obj,dict) else obj if isinstance(obj,list) else None
    if not isinstance(songs,list):
        return [{"level":"FAIL","code":"NO_SONGS","message":"Expected a songs array or a top-level song array."}]
    if len(songs)!=15:
        issues.append({"level":"WARN","code":"SONG_COUNT","message":f"Expected 15 songs for the default workflow; found {len(songs)}."})
    male_only="彼のSTORY" in preset.get("label","")
    female_only="彼女のSTORY" in preset.get("label","")
    for idx,s in enumerate(songs,1):
        if not isinstance(s,dict):
            issues.append({"level":"FAIL","code":"SONG_OBJECT","message":f"Track {idx} is not an object."}); continue
        for req in ["trackNo","title","lyrics","stylePrompt"]:
            if req not in s: issues.append({"level":"FAIL","code":"MISSING_FIELD","message":f"Track {idx}: missing {req}."})
        sp=str(s.get("stylePrompt",""))
        if "CHILI" in preset.get("label","") and not sp.startswith("Chill Rap,"):
            issues.append({"level":"FAIL","code":"CHILI_PREFIX","message":f"Track {idx}: CHILI stylePrompt must start exactly with 'Chill Rap,'."})
        if len(sp)>1000:
            issues.append({"level":"WARN","code":"STYLE_LENGTH","message":f"Track {idx}: stylePrompt is {len(sp)} chars; consider compacting."})
        vt=str(s.get("vocalType","")).lower()
        if male_only and (re.search(r"\bfemale\b",vt) or re.search(r"\bduet\b",vt)): issues.append({"level":"FAIL","code":"GENDER","message":f"Track {idx}: male-only preset but vocalType={s.get('vocalType')}"})
        if female_only and (re.search(r"\bmale\b",vt) or re.search(r"\bduet\b",vt)): issues.append({"level":"FAIL","code":"GENDER","message":f"Track {idx}: female-only preset but vocalType={s.get('vocalType')}"})
        if "negativeStyleText" not in s and "excludePrompt" not in s:
            issues.append({"level":"WARN","code":"NO_EXCLUDE","message":f"Track {idx}: no negativeStyleText/excludePrompt field."})
    if not issues:
        issues.append({"level":"PASS","code":"OK","message":"JSON structure and main preset checks passed."})
    return issues
