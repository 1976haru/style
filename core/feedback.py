from __future__ import annotations

import csv
import json
import math
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

SCHEMA_VERSION = 1
ISSUE_TAGS = [
    "generic_vocal", "vocal_identity_shift", "too_airy", "too_rnb", "rap_weak",
    "rap_too_hard", "too_slow", "too_fast", "hook_weak", "bridge_weak",
    "final_weak", "early_ending", "wrong_gender", "wrong_language",
    "prompt_ignored", "structure_drift", "lyrics_awkward", "other",
]


def _connect(path: str | Path) -> sqlite3.Connection:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(p)
    con.row_factory = sqlite3.Row
    return con


def init_feedback_db(path: str | Path) -> None:
    with _connect(path) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                session_id TEXT NOT NULL,
                market TEXT,
                goal TEXT,
                preset_id TEXT,
                market_recipe_id TEXT,
                market_recipe_label TEXT,
                model TEXT,
                episode TEXT,
                track_no INTEGER,
                title TEXT,
                music_role TEXT,
                bpm INTEGER,
                genre TEXT,
                vocal TEXT,
                performance_signature TEXT,
                style_prompt TEXT,
                decision TEXT NOT NULL,
                overall INTEGER NOT NULL,
                vocal_identity INTEGER NOT NULL,
                hook INTEGER NOT NULL,
                groove INTEGER NOT NULL,
                prompt_adherence INTEGER NOT NULL,
                runtime_sec REAL,
                issue_tags TEXT,
                notes TEXT
            )
            """
        )
        con.execute("CREATE INDEX IF NOT EXISTS idx_feedback_recipe ON feedback(market_recipe_id)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_feedback_preset ON feedback(preset_id)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback(created_at)")
        con.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)")
        con.execute("INSERT OR REPLACE INTO metadata(key,value) VALUES('schema_version',?)", (str(SCHEMA_VERSION),))
        con.commit()


def _clamp_rating(v: Any) -> int:
    try:
        n = int(v)
    except Exception:
        n = 3
    return max(1, min(5, n))


def add_feedback(path: str | Path, record: Dict[str, Any]) -> int:
    init_feedback_db(path)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    decision = str(record.get("decision") or "MAYBE").upper()
    if decision not in {"KEEP", "REGEN", "MAYBE"}:
        decision = "MAYBE"
    tags = record.get("issue_tags") or []
    if isinstance(tags, str):
        tags = [x.strip() for x in tags.split(",") if x.strip()]
    tags = [x for x in tags if x in ISSUE_TAGS or x]
    vals = (
        now,
        str(record.get("session_id") or datetime.now().strftime("%Y%m%d_%H%M%S")),
        str(record.get("market") or ""), str(record.get("goal") or ""),
        str(record.get("preset_id") or ""), str(record.get("market_recipe_id") or ""),
        str(record.get("market_recipe_label") or ""), str(record.get("model") or ""),
        str(record.get("episode") or ""), int(record.get("track_no") or 0),
        str(record.get("title") or ""), str(record.get("music_role") or ""),
        int(record.get("bpm") or 0), str(record.get("genre") or ""),
        str(record.get("vocal") or ""), str(record.get("performance_signature") or ""),
        str(record.get("style_prompt") or ""), decision,
        _clamp_rating(record.get("overall")), _clamp_rating(record.get("vocal_identity")),
        _clamp_rating(record.get("hook")), _clamp_rating(record.get("groove")),
        _clamp_rating(record.get("prompt_adherence")),
        float(record["runtime_sec"]) if record.get("runtime_sec") not in (None, "") else None,
        json.dumps(tags, ensure_ascii=False), str(record.get("notes") or ""),
    )
    with _connect(path) as con:
        cur = con.execute(
            """
            INSERT INTO feedback(
                created_at,session_id,market,goal,preset_id,market_recipe_id,market_recipe_label,model,episode,
                track_no,title,music_role,bpm,genre,vocal,performance_signature,style_prompt,decision,
                overall,vocal_identity,hook,groove,prompt_adherence,runtime_sec,issue_tags,notes
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, vals
        )
        con.commit()
        return int(cur.lastrowid)


def list_feedback(path: str | Path, limit: int = 500) -> List[Dict[str, Any]]:
    init_feedback_db(path)
    with _connect(path) as con:
        rows = con.execute("SELECT * FROM feedback ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
    out=[]
    for r in rows:
        d=dict(r)
        try: d["issue_tags"] = json.loads(d.get("issue_tags") or "[]")
        except Exception: d["issue_tags"] = []
        out.append(d)
    return out


def delete_feedback(path: str | Path, row_id: int) -> None:
    init_feedback_db(path)
    with _connect(path) as con:
        con.execute("DELETE FROM feedback WHERE id=?", (int(row_id),))
        con.commit()


def _record_score(r: Dict[str, Any]) -> float:
    # User judgement is deliberately dominant. 0..100.
    rating = (
        0.30 * float(r.get("overall", 3)) +
        0.22 * float(r.get("vocal_identity", 3)) +
        0.16 * float(r.get("hook", 3)) +
        0.16 * float(r.get("groove", 3)) +
        0.16 * float(r.get("prompt_adherence", 3))
    ) / 5.0 * 100.0
    decision = str(r.get("decision", "MAYBE")).upper()
    decision_bonus = 12.0 if decision == "KEEP" else (-20.0 if decision == "REGEN" else 0.0)
    return max(0.0, min(100.0, rating + decision_bonus))


def aggregate_feedback(path: str | Path) -> Dict[str, Any]:
    rows = list_feedback(path, 100000)
    by_recipe: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_preset: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    issue_counts = Counter()
    for r in rows:
        by_recipe[r.get("market_recipe_id") or "(none)"].append(r)
        by_preset[r.get("preset_id") or "(none)"].append(r)
        issue_counts.update(r.get("issue_tags") or [])

    def summarize(group: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        out={}
        for key, rs in group.items():
            n=len(rs); keeps=sum(1 for r in rs if r.get("decision")=="KEEP"); regens=sum(1 for r in rs if r.get("decision")=="REGEN")
            score=sum(_record_score(r) for r in rs)/n if n else 0
            out[key]={
                "n":n,"keepRate":round(keeps/n,3) if n else 0,"regenRate":round(regens/n,3) if n else 0,
                "feedbackScore":round(score,1),
                "avgOverall":round(sum(r.get("overall",3) for r in rs)/n,2),
                "avgVocalIdentity":round(sum(r.get("vocal_identity",3) for r in rs)/n,2),
                "avgHook":round(sum(r.get("hook",3) for r in rs)/n,2),
                "avgGroove":round(sum(r.get("groove",3) for r in rs)/n,2),
                "avgAdherence":round(sum(r.get("prompt_adherence",3) for r in rs)/n,2),
            }
        return out

    return {
        "total":len(rows),
        "byRecipe":summarize(by_recipe),
        "byPreset":summarize(by_preset),
        "issueCounts":dict(issue_counts.most_common()),
    }


def apply_feedback_ranking(market_rows: List[Dict[str, Any]], path: str | Path, min_samples: int = 3) -> List[Dict[str, Any]]:
    agg = aggregate_feedback(path)
    stats = agg.get("byRecipe", {})
    out=[]
    for row in market_rows:
        r=dict(row)
        st=stats.get(r.get("id") or "", {})
        n=int(st.get("n",0) or 0)
        r["feedbackN"] = n
        r["feedbackScore"] = st.get("feedbackScore") if n else None
        r["keepRate"] = st.get("keepRate") if n else None
        base=float(r.get("marketScore",0) or 0)
        # marketScore may be 0..10 or 0..100 depending on catalog version.
        base100 = base*10.0 if base <= 10.0 else base
        if n >= min_samples:
            # Feedback weight grows gradually; capped at 55% after ~12 evaluated tracks.
            w=min(0.55, 0.20 + 0.035*(n-min_samples))
            adjusted=(1-w)*base100 + w*float(st.get("feedbackScore",50))
            r["feedbackWeight"] = round(w,3)
            r["adjustedScore"] = round(adjusted,1)
            r["adjustedScore10"] = round(adjusted/10.0,2)
        else:
            r["feedbackWeight"] = 0.0
            r["adjustedScore"] = round(base100,1)
            r["adjustedScore10"] = round(base100/10.0,2)
        out.append(r)
    out.sort(key=lambda x:(float(x.get("adjustedScore",0)), float(x.get("marketScore",0))), reverse=True)
    return out


def build_feedback_insights(path: str | Path, preset_id: str = "", market_recipe_id: str = "", min_samples: int = 3) -> Dict[str, Any]:
    rows=list_feedback(path,100000)
    filt=[r for r in rows if (not preset_id or r.get("preset_id")==preset_id) and (not market_recipe_id or r.get("market_recipe_id")==market_recipe_id)]
    scope="preset+recipe"
    if len(filt) < min_samples and market_recipe_id:
        filt=[r for r in rows if r.get("market_recipe_id")==market_recipe_id]
        scope="recipe"
    if len(filt) < min_samples and preset_id:
        filt=[r for r in rows if r.get("preset_id")==preset_id]
        scope="preset"
    if len(filt) < min_samples:
        return {"active":False,"n":len(filt),"scope":scope,"minSamples":min_samples,"guidance":[]}

    issue=Counter(); genre=defaultdict(list); roles=defaultdict(list); bpm_keep=[]; positive_perf=[]
    for r in filt:
        issue.update(r.get("issue_tags") or [])
        genre[r.get("genre") or "(unknown)"].append(_record_score(r))
        roles[r.get("music_role") or "Core"].append(_record_score(r))
        if r.get("decision")=="KEEP" and r.get("bpm"): bpm_keep.append(int(r["bpm"]))
        if r.get("decision")=="KEEP" and r.get("performance_signature"):
            positive_perf.append((float(_record_score(r)), r.get("performance_signature")))
    top_genres=sorted(((sum(v)/len(v),k,len(v)) for k,v in genre.items()), reverse=True)[:3]
    top_perf=[]; seen=set()
    for score,p in sorted(positive_perf, reverse=True):
        if p not in seen:
            top_perf.append(p); seen.add(p)
        if len(top_perf)>=4: break
    guidance=[]
    if bpm_keep:
        guidance.append(f"Local KEEP BPM center: {round(sum(bpm_keep)/len(bpm_keep),1)} from {len(bpm_keep)} kept tracks; treat as a soft prior, not a hard lock.")
    if top_genres:
        guidance.append("Locally stronger genre/prompt families: " + "; ".join(f"{g} ({s:.0f}/100, n={n})" for s,g,n in top_genres))
    if top_perf:
        guidance.append("Repeat these successful performance behaviors selectively: " + " | ".join(top_perf))
    if issue:
        guidance.append("Recurring failure tags to actively guard against: " + ", ".join(f"{k}({v})" for k,v in issue.most_common(6)))
    avg=sum(_record_score(r) for r in filt)/len(filt)
    return {
        "active":True,"n":len(filt),"scope":scope,"minSamples":min_samples,"feedbackScore":round(avg,1),
        "keepRate":round(sum(1 for r in filt if r.get("decision")=="KEEP")/len(filt),3),
        "topIssues":dict(issue.most_common(8)),"guidance":guidance,
    }


def export_feedback_json(path: str | Path, out_path: str | Path) -> None:
    payload={"schemaVersion":SCHEMA_VERSION,"exportedAt":datetime.now(timezone.utc).isoformat(),"aggregate":aggregate_feedback(path),"records":list_feedback(path,100000)}
    Path(out_path).write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")


def export_feedback_csv(path: str | Path, out_path: str | Path) -> None:
    rows=list_feedback(path,100000)
    fields=[
        "id","created_at","session_id","market","goal","preset_id","market_recipe_id","market_recipe_label","model","episode",
        "track_no","title","music_role","bpm","genre","vocal","performance_signature","decision","overall","vocal_identity",
        "hook","groove","prompt_adherence","runtime_sec","issue_tags","notes"
    ]
    with Path(out_path).open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for r in rows:
            d={k:r.get(k,"") for k in fields}
            d["issue_tags"]=",".join(r.get("issue_tags") or [])
            w.writerow(d)
