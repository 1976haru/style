from __future__ import annotations
from typing import Any, Dict, List

GOAL_WEIGHTS = {
    "revenue_balance": {"demand":0.28,"repeatability":0.22,"monetizationProxy":0.18,"aiFit":0.17,"opportunity":0.15},
    "long_watch": {"demand":0.20,"repeatability":0.35,"monetizationProxy":0.20,"aiFit":0.15,"opportunity":0.10},
    "discovery": {"demand":0.38,"repeatability":0.12,"monetizationProxy":0.12,"aiFit":0.14,"opportunity":0.24},
    "low_competition": {"demand":0.18,"repeatability":0.18,"monetizationProxy":0.12,"aiFit":0.17,"opportunity":0.35},
    "senior": {"demand":0.25,"repeatability":0.27,"monetizationProxy":0.22,"aiFit":0.12,"opportunity":0.14},
    "cafe_store": {"demand":0.20,"repeatability":0.32,"monetizationProxy":0.22,"aiFit":0.17,"opportunity":0.09},
    "focus_work": {"demand":0.20,"repeatability":0.36,"monetizationProxy":0.18,"aiFit":0.18,"opportunity":0.08},
    "sleep": {"demand":0.24,"repeatability":0.38,"monetizationProxy":0.20,"aiFit":0.14,"opportunity":0.04},
    "drive": {"demand":0.25,"repeatability":0.28,"monetizationProxy":0.17,"aiFit":0.18,"opportunity":0.12},
    "vocal_story": {"demand":0.24,"repeatability":0.18,"monetizationProxy":0.14,"aiFit":0.18,"opportunity":0.26},
    "streaming_release": {"demand":0.29,"repeatability":0.18,"monetizationProxy":0.18,"aiFit":0.18,"opportunity":0.17}
}

def opportunity(recipe: Dict[str,Any]) -> float:
    return max(0.0, 10.0 - float(recipe.get("competitionIntensity", 5)))

def score_recipe(recipe: Dict[str,Any], goal: str="revenue_balance") -> float:
    w = GOAL_WEIGHTS.get(goal, GOAL_WEIGHTS["revenue_balance"])
    vals = {
        "demand": float(recipe.get("demand",0)),
        "repeatability": float(recipe.get("repeatability",0)),
        "monetizationProxy": float(recipe.get("monetizationProxy",0)),
        "aiFit": float(recipe.get("aiFit",0)),
        "opportunity": opportunity(recipe),
    }
    base = sum(vals[k]*w[k] for k in w)
    if goal in recipe.get("useCases",[]):
        base += 0.7
    return round(min(base,10.0),2)

def recommend(catalog: Dict[str,Any], market: str, goal: str, vocal_pref: str="any", language: str="any", top_n: int=8) -> List[Dict[str,Any]]:
    candidates=[]
    for r in catalog.get("recipes",[]):
        if market != "ANY" and market not in r.get("markets",[]):
            continue
        vm = r.get("vocalMode","")
        if vocal_pref == "vocal" and "instrumental" == vm:
            continue
        if vocal_pref == "instrumental" and vm == "vocal":
            continue
        langs = r.get("languages",[])
        if language != "any" and language not in langs and "Instrumental" not in langs:
            continue
        candidates.append(r)
    # For intent-specific requests, relevance beats raw global demand.
    specialized = {"senior","cafe_store","focus_work","sleep","drive","vocal_story","streaming_release"}
    matched = [r for r in candidates if goal in r.get("useCases",[])]
    if goal in specialized and len(matched) >= 1:
        candidates = matched
    out=[]
    for r in candidates:
        x=dict(r)
        x["marketScore"] = score_recipe(r, goal)
        # Small home-market preference when a recipe is explicitly authored for that market.
        if market != "ANY" and r.get("markets") and r.get("markets")[0] == market:
            x["marketScore"] = round(min(10.0, x["marketScore"] + 0.20), 2)
        x["opportunityScore"] = round(opportunity(r),1)
        out.append(x)
    out.sort(key=lambda x:(x["marketScore"],x.get("demand",0),x.get("repeatability",0)), reverse=True)
    return out[:top_n]
