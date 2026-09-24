from __future__ import annotations
import json, re, statistics
from collections import Counter
from typing import Any, Dict, List

SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]", re.M)
BPM_RE = re.compile(r"(?<!\d)(\d{2,3})\s*BPM\b", re.I)


def _walk_songs(obj: Any) -> List[Dict[str,Any]]:
    if isinstance(obj, dict):
        for k in ("songs","tracks","items"):
            if isinstance(obj.get(k), list) and all(isinstance(x,dict) for x in obj[k]):
                return obj[k]
        for v in obj.values():
            r=_walk_songs(v)
            if r: return r
    return []


def _collect_sections(lyrics: str) -> List[str]:
    return [m.group(1).strip() for m in SECTION_RE.finditer(lyrics or "")]


def _safe_excerpt(text: str, n: int=0) -> str:
    # Deliberately do not preserve lyric lines. Reference DNA is structural, not copying.
    return ""


def extract_reference_dna(raw: str) -> Dict[str,Any]:
    raw = raw or ""
    dna: Dict[str,Any] = {
        "sourceType":"text",
        "songCount":0,
        "bpms":[],
        "bpmSummary":{},
        "vocalTypes":{},
        "genres":{},
        "sectionPatterns":{},
        "stylePromptStats":{},
        "styleAtoms":[],
        "excludeAtoms":[],
        "lyricStructureNotes":[],
        "copyrightMode":"STRUCTURE_ONLY",
        "copyPolicy":"Do not reproduce source lyric lines or melodies. Reuse only abstract structure, musical traits, pacing, section logic and prompt atoms."
    }
    try:
        obj=json.loads(raw)
        dna["sourceType"]="json"
        songs=_walk_songs(obj)
        dna["songCount"]=len(songs)
        bpms=[]; vocals=Counter(); genres=Counter(); sections=Counter(); style_lens=[]; style_atoms=Counter(); excl=Counter()
        for s in songs:
            b=s.get("BPM", s.get("bpm"))
            if isinstance(b,(int,float)): bpms.append(int(b))
            vt=str(s.get("vocalType",s.get("vocalGender",""))).strip()
            if vt: vocals[vt]+=1
            g=str(s.get("genreText",s.get("genre",s.get("genreId","")))).strip()
            if g: genres[g]+=1
            lyr=str(s.get("lyrics",""))
            sec=_collect_sections(lyr)
            if sec: sections[" > ".join(sec[:12])]+=1
            sp=str(s.get("stylePrompt",s.get("style","")))
            if sp:
                style_lens.append(len(sp))
                for atom in re.split(r"[;\n]+", sp):
                    atom=atom.strip(" -\t")
                    if 4 <= len(atom) <= 180: style_atoms[atom]+=1
            neg=str(s.get("negativeStyleText",s.get("excludePrompt",s.get("exclude",""))))
            for atom in re.split(r"[,;\n]+", neg):
                atom=atom.strip()
                if 2 <= len(atom) <= 80: excl[atom]+=1
        dna["bpms"]=bpms
        if bpms:
            dna["bpmSummary"]={"min":min(bpms),"max":max(bpms),"avg":round(statistics.mean(bpms),1),"median":statistics.median(bpms)}
        dna["vocalTypes"]=dict(vocals.most_common(12))
        dna["genres"]=dict(genres.most_common(12))
        dna["sectionPatterns"]=dict(sections.most_common(8))
        if style_lens:
            dna["stylePromptStats"]={"count":len(style_lens),"minChars":min(style_lens),"maxChars":max(style_lens),"avgChars":round(statistics.mean(style_lens),1)}
        # retain abstract/technical prompt atoms, not lyric prose
        dna["styleAtoms"]=[x for x,_ in style_atoms.most_common(30)]
        dna["excludeAtoms"]=[x for x,_ in excl.most_common(30)]
        dna["lyricStructureNotes"]=["Detected section-tag patterns are reusable as structure only.","Source lyric wording is intentionally not carried into the compiled instruction."]
        return dna
    except Exception:
        pass

    bpms=[int(x) for x in BPM_RE.findall(raw)]
    dna["bpms"]=bpms[:100]
    if bpms:
        dna["bpmSummary"]={"min":min(bpms),"max":max(bpms),"avg":round(statistics.mean(bpms),1),"median":statistics.median(bpms)}
    secs=_collect_sections(raw)
    if secs:
        dna["sectionPatterns"]={" > ".join(secs[:20]):1}
    # technical lines only; skip lyric-like short lines
    atoms=[]
    for line in raw.splitlines():
        line=line.strip()
        if any(k.lower() in line.lower() for k in ["styleprompt","genre","bpm","vocal","production","instrument","exclude","bridge","chorus","tempo","phonation"]):
            if 8 <= len(line) <= 220:
                atoms.append(line)
    dna["styleAtoms"]=atoms[:30]
    dna["lyricStructureNotes"]=["Plain-text reference parsed conservatively.","Only technical/structural traits are reusable; exact lyric wording is excluded."]
    return dna
