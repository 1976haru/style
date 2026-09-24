from __future__ import annotations
import json, re, math
from copy import deepcopy
from typing import Any, Dict, List, Tuple


def _songs_from_json(obj: Any) -> List[Dict[str, Any]]:
    if isinstance(obj, dict):
        for key in ("songs", "tracks", "preassignedSongs", "items"):
            val = obj.get(key)
            if isinstance(val, list) and all(isinstance(x, dict) for x in val):
                return val
        for v in obj.values():
            r = _songs_from_json(v)
            if r:
                return r
    return []


def _s(v: Any) -> str:
    return "" if v is None else str(v).strip()


def _int_bpm(v: Any) -> int | None:
    if isinstance(v, (int, float)):
        n = int(round(v))
        return n if 30 <= n <= 300 else None
    m = re.search(r"(?<!\d)(\d{2,3})\s*(?:BPM)?\b", _s(v), re.I)
    if m:
        n = int(m.group(1))
        return n if 30 <= n <= 300 else None
    return None


def _base_row(track_no: int) -> Dict[str, Any]:
    return {
        "trackNo": track_no,
        "locks": {"story": True, "scene": True, "title": True, "hook": True},
        "trusted": {
            "title": "", "hookPhrase": "", "storyAct": "", "storyActLabel": "",
            "storyArcRole": "", "scene": "", "listenerSituation": "", "emotionArc": ""
        },
        "importedMusic": {
            "BPM": None, "genre": "", "vocal": "", "structure": "", "intro": "", "trackRole": ""
        },
        "recomputed": {
            "BPM": None, "genre": "", "vocal": "", "musicRole": "Core", "structure": "",
            "performanceSignature": "", "reason": []
        },
        "manualOverrides": {},
        "source": {"kind": "unknown", "confidence": 0.0}
    }


def _row_from_song(song: Dict[str, Any], idx: int) -> Dict[str, Any]:
    no = song.get("trackNo", song.get("track", idx))
    try: no = int(no)
    except Exception: no = idx
    r = _base_row(no)
    t = r["trusted"]; m = r["importedMusic"]
    t["title"] = _s(song.get("title", song.get("titleLocalized", "")))
    t["hookPhrase"] = _s(song.get("hookPhrase", song.get("hook", "")))
    t["storyAct"] = _s(song.get("storyAct", ""))
    t["storyActLabel"] = _s(song.get("storyActLabel", ""))
    t["storyArcRole"] = _s(song.get("storyArcRole", song.get("role", "")))
    t["scene"] = _s(song.get("lyricThemeText", song.get("seasonMoment", song.get("scene", ""))))
    t["listenerSituation"] = _s(song.get("listenerSituation", t["scene"]))
    t["emotionArc"] = _s(song.get("emotionArc", song.get("lyricThemeArc", "")))
    m["BPM"] = _int_bpm(song.get("BPM", song.get("bpm")))
    m["genre"] = _s(song.get("genreText", song.get("genre", song.get("genreId", ""))))
    m["vocal"] = _s(song.get("vocalType", song.get("vocalText", song.get("vocalGender", ""))))
    m["structure"] = _s(song.get("structureTemplate", song.get("structure", "")))
    m["intro"] = _s(song.get("introMode", song.get("intro", "")))
    m["trackRole"] = _s(song.get("trackRole", song.get("role", "")))
    r["source"] = {"kind": "json-song", "confidence": 0.98}
    return r


def _parse_json(raw: str) -> List[Dict[str, Any]]:
    s = (raw or "").strip()
    if not s.startswith(("{", "[")):
        return []
    try:
        obj = json.loads(s)
    except Exception:
        return []
    songs = _songs_from_json(obj)
    return [_row_from_song(song, i + 1) for i, song in enumerate(songs)]


def _split_table_line(line: str) -> List[str]:
    return [x.strip() for x in line.strip().strip("|").split("|")]


def _parse_markdown_tables(raw: str) -> List[Dict[str, Any]]:
    lines = raw.splitlines()
    best: List[Dict[str, Any]] = []
    i = 0
    while i < len(lines) - 2:
        if "|" not in lines[i] or "track" not in lines[i].lower():
            i += 1; continue
        hdr = _split_table_line(lines[i])
        if not any(h.lower().startswith("track") for h in hdr):
            i += 1; continue
        if i + 1 >= len(lines) or not re.search(r"---", lines[i+1]):
            i += 1; continue
        rows=[]; j=i+2
        while j < len(lines) and lines[j].strip().startswith("|"):
            vals=_split_table_line(lines[j])
            if len(vals) < 2: break
            d={hdr[k].strip().lower(): vals[k] if k < len(vals) else "" for k in range(len(hdr))}
            tr = next((v for k,v in d.items() if k.startswith("track")), "")
            mtr=re.search(r"\d+", tr)
            if not mtr: j += 1; continue
            no=int(mtr.group())
            r=_base_row(no); t=r["trusted"]; m=r["importedMusic"]
            def col(*keys):
                for key in keys:
                    for hk,hv in d.items():
                        if key in hk: return hv
                return ""
            m["genre"]=col("genre")
            m["BPM"]=_int_bpm(col("bpm"))
            m["vocal"]=col("vocal")
            m["structure"]=col("structure")
            m["intro"]=col("intro")
            m["trackRole"]=col("role")
            t["scene"]=col("scene frame", "scene")
            t["listenerSituation"]=t["scene"]
            r["source"]={"kind":"markdown-track-table","confidence":0.9}
            rows.append(r); j += 1
        if len(rows) > len(best): best=rows
        i=j
    return best


def _parse_story_map(raw: str) -> Dict[int, Dict[str, str]]:
    out={}
    for line in raw.splitlines():
        m=re.match(r"\s*[-*]\s*T(\d+)\s*:\s*(.+)$", line, re.I)
        if not m: continue
        no=int(m.group(1)); text=m.group(2).strip()
        title=""; hook=""; vocal=""
        mt=re.search(r'title\s*=\s*["“](.*?)["”]', text, re.I)
        mh=re.search(r'hook\s*=\s*["“](.*?)["”]', text, re.I)
        mv=re.search(r'vocal\s*=\s*([^\s-]+)', text, re.I)
        if mt: title=mt.group(1)
        if mh: hook=mh.group(1)
        if mv: vocal=mv.group(1)
        act=""; ma=re.search(r"(Act\s*\d+\s*/\s*[^-]+)", text, re.I)
        if ma: act=ma.group(1).strip()
        out[no]={"storyArcRole":text,"title":title,"hookPhrase":hook,"vocal":vocal,"storyActLabel":act}
    return out


def _parse_lyric_scenes(raw: str) -> Dict[int, Dict[str, str]]:
    lines=raw.splitlines(); out={}; i=0
    while i < len(lines):
        m=re.match(r"\s*(?:[-*]\s*)?Track\s+(\d+)\s*:\s*(.+)$", lines[i], re.I)
        if not m: i += 1; continue
        no=int(m.group(1)); scene=m.group(2).strip(); emotional=""; time=""
        j=i+1
        while j < len(lines) and j <= i+5:
            s=lines[j].strip()
            if re.match(r"(?:[-*]\s*)?Track\s+\d+\s*:", s, re.I): break
            em=re.match(r"emotional\s+turn\s*:\s*(.+)", s, re.I)
            tm=re.match(r"time\s*:\s*(.+)", s, re.I)
            if em: emotional=em.group(1).strip()
            if tm: time=tm.group(1).strip()
            j += 1
        out[no]={"scene":scene,"listenerSituation":scene,"emotionArc":emotional,"context":time}
        i=j
    return out


def extract_track_plan(raw: str, expected_count: int=15) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Parse a large Haru/Claude instruction or JSON into structured track rows.
    Trusted story/scene/title/hook are locked by default. Music fields remain editable/recomputable.
    """
    rows=_parse_json(raw)
    parse_mode="json" if rows else ""
    if not rows:
        rows=_parse_markdown_tables(raw)
        parse_mode="markdown-table" if rows else ""
    story=_parse_story_map(raw); scenes=_parse_lyric_scenes(raw)
    by={r["trackNo"]:r for r in rows}
    all_n=set(by)|set(story)|set(scenes)
    if not all_n and expected_count:
        all_n=set(range(1,expected_count+1)); parse_mode="skeleton"
    for no in sorted(all_n):
        r=by.get(no) or _base_row(no)
        if no in story:
            x=story[no]; t=r["trusted"]; m=r["importedMusic"]
            for k in ("title","hookPhrase","storyActLabel","storyArcRole"):
                if x.get(k) and not t.get(k): t[k]=x[k]
            if x.get("vocal") and not m.get("vocal"): m["vocal"]=x["vocal"]
            if r["source"]["kind"]=="unknown": r["source"]={"kind":"story-map","confidence":0.84}
        if no in scenes:
            x=scenes[no]; t=r["trusted"]
            for k in ("scene","listenerSituation","emotionArc"):
                if x.get(k): t[k]=x[k]
            if r["source"]["kind"]=="unknown": r["source"]={"kind":"lyric-scene","confidence":0.86}
        by[no]=r
    result=[by[n] for n in sorted(by)]
    meta={
        "parseMode":parse_mode or "mixed",
        "trackCount":len(result),
        "storyMapHits":len(story),
        "sceneHits":len(scenes),
        "lockedByDefault":["story","scene","title","hook"],
        "recomputableByDefault":["BPM","genre","vocal","musicRole","structure","performanceSignature"]
    }
    return result, meta


def _parse_master_ranges(master: str) -> Dict[str, Tuple[int,int]]:
    """Extract tempo policy from a master with section-aware parsing.

    Masters contain many non-tempo numeric ranges (lyric chars, percentages,
    duration, QA scores). Only BPM-policy context is trusted.
    """
    text=master or ""; lines=text.splitlines(); out={}

    def valid(a: int, b: int) -> bool:
        lo,hi=min(a,b),max(a,b)
        return 30 <= lo <= 240 and 30 <= hi <= 240 and (hi-lo) <= 120

    def put(key: str, a: int, b: int):
        # Last valid declaration wins. Current masters intentionally keep older
        # baseline sections above and place v15 conflict overrides later.
        if valid(a,b): out[key]=(min(a,b),max(a,b))

    # Locate explicit BPM/tempo policy sections. This catches both:
    #   Core BPM 권장 92~100 / Flagship 96~104 / Memory 84~92
    # and:
    #   94~102: <next line says 여성 Core 주력>
    #   100~108: <next line says Flagship>
    section_idx=[]
    for i,line in enumerate(lines):
        if re.search(r"(?:^|\s)(?:\d+\.?\s*)?BPM\s*/\s*ENERGY|BPM\s*(?:정책|범위|권장)|TEMPO\s*(?:/|POLICY|RANGE)",line,re.I):
            section_idx.append(i)
    windows=[]
    for i in section_idx:
        # Stop at next major separator/header, otherwise cap to 45 lines.
        end=min(len(lines),i+45)
        for j in range(i+1,end):
            if j>i+3 and re.match(r"^={8,}\s*$",lines[j].strip()):
                end=j; break
        windows.extend(range(i,end))
    windows=sorted(set(windows))

    range_re=re.compile(r"(?<!\d)(\d{2,3})\s*[-~–]\s*(\d{2,3})(?!\s*%)")
    for i in windows:
        line=lines[i]
        # percentage lines are vocal/ratio rules, never tempo policy.
        if '%' in line: continue
        m=range_re.search(line)
        if not m: continue
        a,b=int(m.group(1)),int(m.group(2))
        if not valid(a,b): continue
        line_low=line.lower()
        # Prefer a label on the SAME line. Only use look-ahead when the range line
        # itself is unlabeled (female master style: `94~102:` then `여성 Core 주력`).
        if re.search(r"memory|메모리",line_low): put('memory',a,b); continue
        if re.search(r"flagship|anchor|플래그십|앵커",line_low): put('anchor',a,b); continue
        if re.search(r"\bcore\b|코어|세트\s*중심|주력",line_low): put('core',a,b); continue
        ahead=(' '.join(lines[i+1:i+3])).lower()
        if re.search(r"memory|메모리",ahead): put('memory',a,b); continue
        if re.search(r"flagship|anchor|플래그십|앵커",ahead): put('anchor',a,b); continue
        if re.search(r"\bcore\b|코어|세트\s*중심|주력",ahead): put('core',a,b); continue

    # Same-line fallbacks outside a formal section. Require BPM/tempo on the line
    # so lyric-count and rap-percentage rules cannot be mistaken for tempo.
    for line in lines:
        if '%' in line or not re.search(r"\bBPM\b|tempo|템포",line,re.I):
            continue
        m=range_re.search(line)
        if not m: continue
        a,b=int(m.group(1)),int(m.group(2))
        low=line.lower()
        if re.search(r"memory|메모리",low): put('memory',a,b)
        elif re.search(r"flagship|anchor|플래그십|앵커",low): put('anchor',a,b)
        elif re.search(r"\bcore\b|코어|세트\s*중심|대체로",low): put('core',a,b)

    # Continuation fallback for compact male-style blocks: once a line explicitly
    # says Core BPM, the following few label-only lines are considered tempo lines.
    for i,line in enumerate(lines):
        if re.search(r"(?:Core|코어).*\bBPM\b",line,re.I):
            for j in range(i,min(len(lines),i+4)):
                l=lines[j]
                if '%' in l: continue
                m=range_re.search(l)
                if not m: continue
                a,b=int(m.group(1)),int(m.group(2)); low=l.lower()
                if re.search(r"memory|메모리",low): put('memory',a,b)
                elif re.search(r"flagship|anchor|플래그십|앵커",low): put('anchor',a,b)
                elif re.search(r"\bcore\b|코어",low): put('core',a,b)
            break

    return out



def _parse_master_profile(master: str) -> Dict[str, Any]:
    text=master or ""
    profile: Dict[str,Any] = {"ranges": _parse_master_ranges(text), "vocalFingerprint":"", "genre":"", "structureCue":""}
    # Current masters often expose this exact block; retain musical behavior, not prose around it.
    m=re.search(r"\[FIXED VOICE FINGERPRINT[^\]]*\]\s*((?:\s*-\s*[^\n]+\n?){3,20})", text, re.I)
    if m:
        bullets=[]
        for line in m.group(1).splitlines():
            line=re.sub(r"^\s*-\s*","",line).strip()
            if line: bullets.append(line)
        # A compact set is enough for Track Plan display and prompt conditioning.
        profile["vocalFingerprint"]="; ".join(bullets[:9])[:900]
    pm=re.search(r"\[PHRASING FINGERPRINT[^\]]*\]\s*((?:\s*-\s*[^\n]+\n?){2,12})", text, re.I)
    if pm:
        phrases=[]
        for line in pm.group(1).splitlines():
            line=re.sub(r"^\s*-\s*","",line).strip()
            if line: phrases.append(line)
        if phrases:
            profile["vocalFingerprint"]=(profile["vocalFingerprint"] + "; PHRASING: " + "; ".join(phrases[:5])).strip("; ")[:1200]
    # Dual-story masters expose separate male/female signature blocks.
    profile["maleFingerprint"]=""; profile["femaleFingerprint"]=""
    for key,label in (("maleFingerprint","MALE SIGNATURE"),("femaleFingerprint","FEMALE SIGNATURE")):
        sm=re.search(r"\["+label+r"[^\]]*\]\s*((?:\s*-\s*[^\n]+\n?){3,20})",text,re.I)
        if sm:
            vals=[]
            for line in sm.group(1).splitlines():
                line=re.sub(r"^\s*-\s*","",line).strip()
                if line: vals.append(line)
            profile[key]="; ".join(vals[:11])[:1000]
    for pat in [r"핵심\s*장르\s*:\s*([^\n]+)",r"main\s*genre\s*[:=]\s*([^\n]+)",r"주\s*장르\s*[:=]\s*([^\n]+)"]:
        gm=re.search(pat,text,re.I)
        if gm:
            profile["genre"]=gm.group(1).strip(" .-")[:180]; break
    # Fallback for CHILI masters that state the required prefix instead of a 'main genre' line.
    if not profile["genre"] and re.search(r"stylePrompt[^\n]{0,80}Chill Rap|모든 stylePrompt[^\n]{0,80}Chill Rap",text,re.I):
        profile["genre"]="Chill Rap"
    cues=[]
    for line in text.splitlines():
        low=line.lower()
        if ("bridge" in low and "final" in low) or "final a+b+c" in low or "8-bar turnaround" in low:
            if len(line.strip()) <= 260: cues.append(line.strip(" -"))
        if len(cues)>=5: break
    profile["structureCue"]="; ".join(cues)[:900]
    return profile

def _default_ranges(preset_id: str, market_recipe: Dict[str,Any] | None) -> Dict[str,Tuple[int,int]]:
    if preset_id == "chili_male": return {"core":(92,100),"anchor":(96,104),"memory":(88,92)}
    if preset_id == "chili_female": return {"core":(94,102),"anchor":(100,108),"memory":(88,92)}
    if preset_id == "chili_dual": return {"core":(92,100),"anchor":(96,104),"memory":(88,92)}
    br=(market_recipe or {}).get("bpmRange") or [78,104]
    lo,hi=int(br[0]),int(br[1]); span=max(4,hi-lo)
    return {
        "memory":(lo, min(hi, lo+max(3,span//4))),
        "core":(lo+span//4, hi-span//5),
        "anchor":(max(lo,hi-max(4,span//4)),hi)
    }


def _role_from_import(r: Dict[str,Any], n: int, total: int, vocal_mode: str) -> str:
    txt=(r["importedMusic"].get("trackRole","")+" "+r["trusted"].get("storyArcRole","")).lower()
    if any(x in txt for x in ["anchor","flagship","high point","main season","peak","대표곡","최고점"]): return "Anchor"
    if any(x in txt for x in ["memory","reflect","pause","wind-down","quiet","afterglow","회상","여운","쉼"]): return "Memory"
    if vocal_mode == "instrumental" and any(x in txt for x in ["sleep","ambient","focus"]): return "Core"
    return "Core"


def _ensure_anchor_distribution(rows: List[Dict[str,Any]], vocal_mode: str) -> None:
    if not rows or vocal_mode == "instrumental": return
    anchors=[r for r in rows if r["recomputed"]["musicRole"]=="Anchor"]
    target=min(3, max(1, len(rows)//5))
    preferred=[]
    if len(rows)>=15: preferred=[2,9,15]
    elif len(rows)>=10: preferred=[2,6,len(rows)]
    else: preferred=[max(1,round(len(rows)*.2)),max(1,round(len(rows)*.6)),len(rows)]
    for no in preferred:
        if len(anchors)>=target: break
        r=next((x for x in rows if x["trackNo"]==no),None)
        if r and r["recomputed"]["musicRole"]!="Anchor":
            r["recomputed"]["musicRole"]="Anchor"; r["recomputed"]["reason"].append("promoted for set-level anchor distribution")
            anchors.append(r)


def _pick_bpm(rng: Tuple[int,int], track_no: int, role: str) -> int:
    lo,hi=rng
    if hi < lo: lo,hi=hi,lo
    if lo==hi: return lo
    fractions={"Anchor":[.65,.82,.5,.92],"Core":[.35,.55,.72,.45,.62,.78],"Memory":[.2,.4,.6]}
    fs=fractions.get(role,fractions["Core"]); f=fs[(track_no-1)%len(fs)]
    val=int(round(lo+(hi-lo)*f))
    # Music prompting is usually cleaner on even BPM for these playlist workflows.
    if val%2: val += 1 if val < hi else -1
    return max(lo,min(hi,val))


def _genre_for(preset_id: str, preset: Dict[str,Any], market_recipe: Dict[str,Any], imported: str, master_profile: Dict[str,Any] | None=None) -> str:
    mp=master_profile or {}
    master_genre=mp.get("genre","")
    if preset_id.startswith("chili_"):
        tint=""
        for token in [x.strip() for x in re.split(r"[/,]", imported or "") if x.strip()]:
            if token.lower() not in {"chill rap","chill-rap"}:
                tint=re.sub(r"\s+tint\s*$","",token,flags=re.I).strip(); break
        if not tint:
            fam=(market_recipe or {}).get("genreFamily","")
            tint=next((x.strip() for x in fam.split("/") if x.strip() and "chill rap" not in x.lower()),"")
        main = "Chill Rap" if not master_genre else master_genre.split("/")[0].strip()
        return main + (f" / {tint} tint" if tint else "")
    if preset_id=="chanson": return "French Chanson / acoustic cafe-jazz tint"
    if preset_id=="deep_house": return "Deep House / restrained melodic-organic tint"
    fam=(market_recipe or {}).get("genreFamily")
    if fam: return fam
    return imported or preset.get("mainGenrePolicy", "Custom")[:100]


def _vocal_for(preset_id: str, preset: Dict[str,Any], market_recipe: Dict[str,Any], master_profile: Dict[str,Any] | None=None, imported_vocal: str="") -> str:
    vm=(market_recipe or {}).get("vocalMode","")
    mp=master_profile or {}
    if vm=="instrumental": return "Instrumental — no lead/backing vocal"

    # Couple-story packs contain male solo, female solo and duet tracks. Preserve the
    # per-track vocal role while refreshing the recurring identities.
    if preset_id=="chili_dual":
        low=(imported_vocal or "").lower()
        male=mp.get("maleFingerprint") or "one recurring young-adult male tenor/light tenor-baritone; close-mic speech-forward; warm-light chest core; forward oral resonance; breath 10-20%; subtle dry grain 5-12%; compact clipped endings; Verse 40-55% rap-forward"
        female=mp.get("femaleFingerprint") or "one recurring young-adult female light mezzo/light mezzo-soprano; close-mic speech-forward; supported clean core; breath 15-30%; subtle dry husky grain 5-15%; bright-forward resonance; compact clipped endings; Verse 45-60% rap-forward"
        is_duet=any(x in low for x in ["duet","male-female","female-male","two lead","two-lead","asymmetric"])
        is_female=bool(re.search(r"\bfemale\b",low)) and not is_duet
        is_male=bool(re.search(r"\bmale\b",low)) and not is_duet
        if is_male:
            return "HARD LOCK male solo only; CHANNEL SIGNATURE: " + male
        if is_female:
            return "HARD LOCK female solo only; CHANNEL SIGNATURE: " + female
        return "HARD LOCK exactly two recurring leads; MALE: " + male + "; FEMALE: " + female + "; alternate compact phrases; short joined title hook only; no third voice"

    if mp.get("vocalFingerprint"):
        return mp["vocalFingerprint"]
    if preset_id=="chili_male": return "one recurring young-adult Japanese male; speech-forward tenor/light tenor-baritone; warm-light chest; forward oral resonance; breath 10-20%; dry grain 5-12%; clipped endings; Verse 45-55% rap-forward"
    if preset_id=="chili_female": return "one recurring young-adult Japanese female light mezzo; speech-forward supported core; breath 15-30%; dry husky grain 5-15%; bright-forward resonance; clipped endings; Verse 45-60% rap-forward"
    return preset.get("vocalPolicy", "Use a coherent recurring vocal identity.")[:360]


def _structure_for(role: str, vocal_mode: str, preset_id: str) -> str:
    if vocal_mode=="instrumental":
        if role=="Anchor": return "Intro groove → development → contrast/breakdown → clear re-entry → extended payoff/outro; no startling peak"
        if role=="Memory": return "soft intro → sparse development → subtle texture variation → loop-friendly return/outro"
        return "intro → development → variation → return → loop-compatible outro; stable utility flow"
    if role=="Anchor": return "Verse rhythm-first → Pre/Turn → Chorus → 8-bar turnaround → Bridge >=3 audible contrast axes → Pre-Final → Final A + Final B + Post C; no early end"
    if role=="Memory": return "compact Verse → restrained Chorus → 8-bar turnaround → Bridge >=2 axes, lower density but not ballad collapse → Final A+B"
    return "Verse rhythm-first → Pre/Turn → melodic Chorus → 8-bar turnaround → Bridge >=2 axes → Pre-Final → Final A+B"


_PERF = [
    "dry immediate pickup; one delayed keyword landing; compact clipped endings",
    "quick off-beat pickup; one-beat micro-rest before hook; same-voice melodic opening only in Chorus",
    "2-bar speech-rhythmic burst; slight behind-the-beat release; narrow Verse pitch",
    "stop-start cadence with two deliberate micro-rests; clean supported hook entry",
    "late phrase endings; low Verse intensity; Chorus widens one step without singer change",
    "brisk syncopated chain; short answer phrases; dry consonant release",
    "playful off-beat attack; clipped refrain endings; no scoop-in",
    "smooth pocket with sparse pauses; delayed final word; restrained upper-mid hook",
    "closest dry delivery; tension pause before title hook; Final restores full groove",
    "low-dynamic supported talk-rap; no whisper/croon; lazy behind-beat landing",
    "one-beat pause before hook; warm supported center; compact self-response",
    "message-like short phrases; swallowed start then crisp ending; no airy fade",
    "intimate narrow-pitch talk-rap; sparse micro-rests; steady chest/support core",
    "confident conversational pocket; short pickups; wider hook only",
    "reflective opener; repeated hook with changed pickup timing; fuller Final with same timbre"
]


def recompute_track_plan(rows: List[Dict[str,Any]], preset_id: str, preset: Dict[str,Any], market_recipe: Dict[str,Any] | None=None, custom_master: str="") -> Tuple[List[Dict[str,Any]], Dict[str,Any]]:
    rows=deepcopy(rows); mr=market_recipe or {}
    master_profile=_parse_master_profile(custom_master)
    master_ranges=master_profile.get("ranges",{})
    ranges=_default_ranges(preset_id,mr); ranges.update(master_ranges)
    vocal_mode=mr.get("vocalMode", "vocal")
    for r in rows:
        rc=r["recomputed"]
        rc["reason"]=[]
        rc["musicRole"]=_role_from_import(r,r["trackNo"],len(rows),vocal_mode)
    _ensure_anchor_distribution(rows,vocal_mode)
    for r in rows:
        rc=r["recomputed"]; role=rc["musicRole"]
        rr=ranges.get(role.lower(),ranges["core"])
        rc["BPM"]=_pick_bpm(rr,r["trackNo"],role)
        rc["genre"]=_genre_for(preset_id,preset,mr,r["importedMusic"].get("genre",""),master_profile)
        rc["vocal"]=_vocal_for(preset_id,preset,mr,master_profile,r["importedMusic"].get("vocal",""))
        rc["structure"]=_structure_for(role,vocal_mode,preset_id)
        rc["performanceSignature"]=_PERF[(r["trackNo"]-1)%len(_PERF)] if vocal_mode!="instrumental" else "arrangement individuality: " + _PERF[(r["trackNo"]-1)%len(_PERF)]
        old=r["importedMusic"]
        if old.get("BPM") and old.get("BPM")!=rc["BPM"]: rc["reason"].append(f"BPM {old.get('BPM')}→{rc['BPM']} from current range {rr[0]}-{rr[1]}")
        if old.get("genre") and old.get("genre")!=rc["genre"]: rc["reason"].append("legacy/imported genre replaced by current dominant genre policy")
        if old.get("vocal") and old.get("vocal")!=rc["vocal"]: rc["reason"].append("legacy/imported singer description replaced by current recurring vocal identity")
        if old.get("structure") and old.get("structure")!=rc["structure"]: rc["reason"].append("legacy structure replaced by current Core/Memory/Anchor structure")
        overrides=r.get("manualOverrides",{}) or {}
        for field in ("BPM","genre","vocal","musicRole","structure","performanceSignature"):
            if field in overrides and overrides[field] not in (None,""):
                rc[field]=overrides[field]
                rc["reason"].append(f"manual override applied: {field}")
    meta={
        "rangesUsed":{k:list(v) for k,v in ranges.items()},
        "masterRangeOverrides":{k:list(v) for k,v in master_ranges.items()},
        "masterProfile":{"genre":master_profile.get("genre"),"vocalFingerprint":master_profile.get("vocalFingerprint"),"maleFingerprint":master_profile.get("maleFingerprint"),"femaleFingerprint":master_profile.get("femaleFingerprint"),"structureCue":master_profile.get("structureCue")},
        "vocalMode":vocal_mode,
        "recomputedFields":["BPM","genre","vocal","musicRole","structure","performanceSignature"],
        "preservedLockedFields":["story","scene","title","hook"]
    }
    return rows,meta


def compact_plan_for_prompt(rows: List[Dict[str,Any]]) -> List[Dict[str,Any]]:
    out=[]
    for r in rows:
        t=r["trusted"]; rc=r["recomputed"]
        out.append({
            "trackNo":r["trackNo"],
            "locks":r["locks"],
            "title":t.get("title"),"hookPhrase":t.get("hookPhrase"),
            "storyAct":t.get("storyAct"),"storyActLabel":t.get("storyActLabel"),"storyArcRole":t.get("storyArcRole"),
            "listenerSituation":t.get("listenerSituation") or t.get("scene"),"emotionArc":t.get("emotionArc"),
            "BPM":rc.get("BPM"),"genre":rc.get("genre"),"vocal":rc.get("vocal"),
            "musicRole":rc.get("musicRole"),"structure":rc.get("structure"),"performanceSignature":rc.get("performanceSignature")
        })
    return out


def validate_track_plan(rows: List[Dict[str,Any]], expected_count: int=15) -> List[Dict[str,str]]:
    q=[]
    if len(rows)!=expected_count:
        q.append({"level":"WARN","code":"TRACK_PLAN_COUNT","message":f"structured plan has {len(rows)} tracks; expected {expected_count}."})
    nums=[r.get("trackNo") for r in rows]
    if len(nums)!=len(set(nums)):
        q.append({"level":"FAIL","code":"TRACK_PLAN_DUP_NO","message":"duplicate trackNo detected."})
    missing_scene=[r["trackNo"] for r in rows if not (r["trusted"].get("listenerSituation") or r["trusted"].get("scene"))]
    if missing_scene:
        q.append({"level":"INFO","code":"TRACK_PLAN_SCENE_GAPS","message":f"No scene text detected on tracks {missing_scene[:15]}; story lock still prevents invented replacement unless user supplies it."})
    unlocked=[r["trackNo"] for r in rows if not r.get("locks",{}).get("story",True) or not r.get("locks",{}).get("scene",True)]
    if unlocked:
        q.append({"level":"WARN","code":"TRACK_PLAN_UNLOCKED","message":f"Story/scene unlocked on tracks {unlocked}."})
    bad_bpm=[(r["trackNo"],r.get("recomputed",{}).get("BPM")) for r in rows if r.get("recomputed",{}).get("BPM") and not (30 <= int(r["recomputed"]["BPM"]) <= 240)]
    if bad_bpm: q.append({"level":"FAIL","code":"TRACK_PLAN_BPM_RANGE","message":f"Implausible recomputed BPM detected: {bad_bpm}."})
    no_bpm=[r["trackNo"] for r in rows if not r.get("recomputed",{}).get("BPM")]
    if no_bpm: q.append({"level":"FAIL","code":"TRACK_PLAN_NO_BPM","message":f"No recomputed BPM on tracks {no_bpm}."})
    if not q: q.append({"level":"PASS","code":"TRACK_PLAN_OK","message":"Structured track plan locks and recomputed music fields passed."})
    return q
