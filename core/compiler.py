from __future__ import annotations
from typing import Any, Dict, List, Tuple
from .parser import parse_directive
from .validator import analyze_directive_conflicts
from .reference_dna import extract_reference_dna
from .track_plan import compact_plan_for_prompt, validate_track_plan


def _bullet(lines):
    return "\n".join(f"- {x}" for x in lines if x)


def _jsonish(obj: Any) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False, indent=2)



def _extract_array(raw: str, key: str):
    import re, json
    m=re.search(r'["\']?'+re.escape(key)+r'["\']?\s*[:=]\s*(\[[\s\S]*?\])', raw or '', re.I)
    if not m: return []
    try:
        val=json.loads(m.group(1))
        return val if isinstance(val,list) else []
    except Exception:
        # Conservative fallback: only quoted strings from the captured array.
        return re.findall(r'["\']([^"\']{1,160})["\']', m.group(1))[:200]

def _directive_digest(raw: str, parsed, structured_plan):
    import re
    histories={}
    for key in ("alreadyUsedTitles","alreadyUsedHooks","alreadyUsedScenes","alreadyUsedLyricLines","alreadyUsedOpenings"):
        vals=_extract_array(raw,key)
        if vals: histories[key]=vals
    keep=[]
    keys=(
        "source event","source summary","story source","storypov","pov contract","episode boundary","relationship boundary",
        "do not advance","next episode","next event","다음 회차","다음 사건","관계 경계","고백","키스","손잡","연인 확정",
        "phone-number","phone number","confession","kiss","hand-holding","couple confirmation","date confirmation"
    )
    for line in (raw or '').splitlines():
        low=line.lower().strip()
        if low and any(k in low for k in keys):
            # Avoid dragging obvious old music instructions back into the compact digest.
            if not any(x in low for x in ("bpm","baritone","tenor","alto","mezzo","breath-mix","genre","styleprompt","vocal preset")):
                keep.append(line.strip())
        if len(keep)>=60: break
    return {
        "episodeId":parsed.episode_id,"concept":parsed.concept,"storyPov":parsed.story_pov,"language":parsed.language,"songCount":parsed.song_count,
        "alreadyUsed":histories,"storyBoundaryNotes":keep,
        "note":"Music/BPM/vocal/structure rules from the legacy directive are intentionally omitted here because the structured current track plan supersedes them."
    }

def compile_instruction(
    raw_directive: str,
    preset_id: str,
    preset: Dict[str,Any],
    recipe: Dict[str,Any],
    public_rules: Dict[str,Any],
    model: str="v6",
    mode: str="HYBRID",
    custom_master: str="",
    episode_brief: str="",
    market_recipe: Dict[str,Any] | None=None,
    market: str="ANY",
    goal: str="revenue_balance",
    reference_raw: str="",
    reference_ownership: str="external",
    song_count: int=15,
    output_mode: str="full_pack",
    structured_track_plan: List[Dict[str,Any]] | None=None,
    track_plan_meta: Dict[str,Any] | None=None,
    performance_insights: Dict[str,Any] | None=None
) -> Tuple[str, Dict[str,Any], List[Dict[str,str]]]:
    parsed=parse_directive(raw_directive)
    qa=analyze_directive_conflicts(raw_directive,preset)
    rule_texts=[r["text"] for r in sorted(public_rules.get("rules",[]), key=lambda x:-int(x.get("priority",0))) if int(r.get("priority",0))>=85]
    excludes=", ".join(preset.get("hardExcludes",[])) or "Use only explicit user exclusions."
    ref_dna=extract_reference_dna(reference_raw) if reference_raw.strip() else {}
    mr=market_recipe or {}
    structured_track_plan = structured_track_plan or []
    track_plan_meta = track_plan_meta or {}
    performance_insights = performance_insights or {}
    if structured_track_plan:
        qa.extend(validate_track_plan(structured_track_plan, song_count))
    plan_for_prompt = compact_plan_for_prompt(structured_track_plan) if structured_track_plan else []
    directive_digest = _directive_digest(raw_directive, parsed, structured_track_plan) if raw_directive.strip() else {}
    directive_injection = raw_directive.strip() if mode == "PRESERVE" else _jsonish(directive_digest)
    directive_embedding_mode = "FULL_RAW_PRESERVE" if mode == "PRESERVE" else "STRUCTURED_DIGEST_ONLY"
    mode_explain={
        "HYBRID":"Preserve user story/POV/track-plan/history as authoritative content data, but supersede stale music-model, BPM, genre, vocal-phonation and prompt-syntax instructions when they conflict with the current market recipe/channel preset/master.",
        "PRESERVE":"Preserve the imported directive as much as possible. Only repair direct contradictions, invalid output shape, copyright/safety issues and obvious Suno-field conflicts.",
        "MASTER_FIRST":"Current market recipe/channel preset/custom master is authoritative for music, vocal, structure and output; imported directive is used mainly for story, scenes, titles/hooks/history and track-specific intent."
    }[mode]

    ref_policy = (
        "The reference is declared USER-OWNED. You may preserve user-authored lyrics if the user explicitly asks, but default to reusing structure and prompt DNA rather than cloning wording."
        if reference_ownership == "user_owned" else
        "The reference may be external. Do NOT copy lyric lines, melodies, title phrases, or distinctive expressive wording. Reuse only abstract structure, pacing, section logic, genre/production/vocal traits, BPM tendencies and non-expressive technical prompt atoms."
    )

    market_block = "[none selected]" if not mr else f"""- Market: {market}
- Goal: {goal}
- Market recipe: {mr.get('label')}
- Genre family: {mr.get('genreFamily')}
- Vocal mode: {mr.get('vocalMode')}
- Languages: {', '.join(mr.get('languages',[]))}
- Suggested BPM: {mr.get('bpmRange')}
- Style blueprint: {mr.get('styleBlueprint')}
- Lyric blueprint: {mr.get('lyricBlueprint')}
- Core excludes: {', '.join(mr.get('excludeCore',[]))}
- Market rationale: {mr.get('marketRationale')}
- Market-risk note: {mr.get('risk')}
- Heuristic market score: {mr.get('marketScore','n/a')}/10 (NOT a revenue guarantee)"""

    instruction=f"""[SUNO MASTER PROMPT STUDIO v0.4 — CLOSED-LOOP TRACK PLAN COMPILER]

ROLE
You are a production composer, lyricist and Suno prompt engineer. Create original Suno-ready material for the selected market/use-case. Do not merely discuss the plan.

OUTPUT TARGET
- Requested song count: {song_count}
- Output mode: {output_mode}
- Suno target: {model}

PRIORITY STACK — resolve conflicts in this order
1. User's latest explicit instruction in CURRENT BRIEF.
2. STRUCTURED TRACK PLAN: locked story/scene/title/hook + recomputed current BPM/genre/vocal/structure.
3. Trusted imported USER DIRECTIVE data: story source, episode boundary, POV, track order, already-used histories and explicit locks not represented in the structured plan.
4. CUSTOM MASTER if supplied.
5. SELECTED MARKET RECIPE and CURRENT CHANNEL PRESET for music/vocal/BPM/use-case behavior.
6. REFERENCE DNA for abstract inspiration only.
7. Version-aware public Suno knowledge rules.
8. Stale/legacy music rules embedded in old directives.

COMPILE MODE: {mode}
{mode_explain}

UNIVERSAL MARKET RECIPE
{market_block}

CHANNEL / SERIES PRESET: {preset.get('label')}
- Audience: {preset.get('audience')}
- Language: {preset.get('language')}
- Main genre policy: {preset.get('mainGenrePolicy')}
- BPM/energy: {preset.get('bpmPolicy')}
- Vocal identity: {preset.get('vocalPolicy')}
- Mix/groove: {preset.get('mixPolicy')}
- Structure: {preset.get('structurePolicy')}
- Hard excludes: {excludes}

OPTIONAL LEGACY GENRE RECIPE
- Recipe: {recipe.get('label')}
- Main genre: {recipe.get('mainGenre')}
- Secondary colors: {recipe.get('secondary')}
- Typical tempo: {recipe.get('tempo')}
- Note: {recipe.get('notes')}
Use this only when it supports the selected market recipe or an explicit user instruction.

REFERENCE IMPORT POLICY
{ref_policy}
REFERENCE DNA EXTRACT (structure/technical traits only):
{_jsonish(ref_dna) if ref_dna else '[none supplied]'}

PUBLIC KNOWLEDGE RULES — generalized research rules, not magic incantations
{_bullet(rule_texts)}

LOCAL GENERATION FEEDBACK — use only when sample threshold is met
{_jsonish(performance_insights) if performance_insights.get('active') else '[inactive — insufficient local samples]'}
- Local feedback is a soft empirical prior, not a hard rule.
- Never let feedback overwrite locked story/scene/title/hook data.
- Reuse successful performance behaviors selectively; do not clone one cadence across the whole set.
- Recurring failure tags should become explicit guards in style/exclude/generationRunHint when relevant.

CORE PROMPT ENGINE RULES
- Keep Lyrics / Style of Music / Exclude separate.
- Front-load the dominant genre, use-case, vocal identity and groove behavior.
- Prefer concrete musical behaviors over piles of adjectives.
- Avoid contradictory genre stacks; use one dominant family plus restrained secondary color.
- If vocal: preserve a coherent singer/phonation identity across a series; create variety through phrase attack, density, micro-rests, syncopation, range openness and arrangement.
- If instrumental: remove vocal-positive terms and design for the selected utility (focus, sleep, cafe, drive, etc.).
- Market scores are discovery heuristics only; never claim guaranteed revenue or guaranteed recommendation performance.

ORIGINALITY / REFERENCE SAFETY
- Never imitate a named real artist or copy a known melody/lyrics.
- External references are DNA only: structure + technical traits + general genre conventions.
- If the imported reference contains exact lyrics, do not output those lines unless clearly user-authored and explicitly requested for preservation.

OUTPUT CONTRACT
- For full_pack: return VALID RAW JSON only, no markdown fences. Use a top-level meta + songs array.
- For prompt_only: return JSON containing generated stylePrompt/exclude/structure/vocal DNA and no full lyrics.
- For lyrics_plus_prompt: return JSON songs with title, hookPhrase, lyrics, stylePrompt, negativeStyleText and essential metadata.
- Do not prefix creative title with track numbers; trackNo is separate.
- Required per-song fields for vocal full_pack: trackNo, title, hookPhrase, BPM, trackRole, vocalType, listenerSituation, emotionArc, distinctChoice, performanceSignature, lyrics, stylePrompt, negativeStyleText, generationRunHint.
- For instrumental recipes, lyrics may be empty and vocalType="Instrumental"; replace performanceSignature with arrangementSignature if more appropriate.
- Validate language, duplicate titles/hooks, BPM distribution, style/exclude conflicts, prompt length, section logic, and JSON parseability before final output.

SET DESIGN
- Do not make every track equally intense. Build Core / Memory / Anchor or an equivalent three-tier energy map appropriate to the recipe.
- Long-watch utility genres: avoid sudden peaks and keep transitions compatible with continuous listening.
- Vocal discovery genres: make 2-3 Anchors clearly memorable through hook, arrangement contrast and final payoff, not through excessive loudness.
- Track variety must come from scene, groove, instrument signature, phrase behavior, structure or harmony — not random genre switching.

STRUCTURED TRACK PLAN — AUTHORITATIVE WHEN PRESENT
{_jsonish(plan_for_prompt) if plan_for_prompt else '[none — derive from imported directive/brief]'}

TRACK PLAN LOCK CONTRACT
- story/scene/title/hook fields marked locked are TRUSTED CONTENT DATA. Do not rewrite, relocate, advance the relationship, invent a new setting, or substitute another scene.
- BPM/genre/vocal/musicRole/structure/performanceSignature in the structured plan are CURRENT RECOMPUTED MUSIC DATA. Use them instead of obsolete values embedded later in the raw imported directive.
- The raw directive remains evidence/context, but when it disagrees with the structured plan on BPM, genre, vocal identity or structure, the structured plan wins.
- Keep trackNo/order exactly. Preserve scene-specific emotional logic.
- For each track, make stylePrompt reflect its recomputed performanceSignature so 15 tracks do not collapse into one generic delivery.

CURRENT BRIEF (highest priority)
{episode_brief.strip() or '[none supplied]'}

CUSTOM MASTER (optional)
{custom_master.strip() or '[none supplied]'}

IMPORTED USER DIRECTIVE CONTEXT ({directive_embedding_mode})
{directive_injection or '[none supplied]'}

LEGACY DIRECTIVE HANDLING
- In HYBRID/MASTER_FIRST, the original multi-thousand-line directive is NOT injected verbatim. Its trusted story/history data is represented above and in the structured track plan; stale music instructions are intentionally excluded from active context.
- In PRESERVE mode only, the full imported directive is embedded.

FINAL TASK
Create the requested original Suno-ready output now. Use the market recipe for commercial/use-case fit, preserve trusted user planning data when present, and use references only as abstract DNA. Return the requested JSON output only.
"""
    manifest={
        "compilerVersion":"0.4.1",
        "mode":mode,"model":model,"market":market,"goal":goal,
        "songCount":song_count,"outputMode":output_mode,
        "presetId":preset_id,"presetLabel":preset.get("label"),
        "legacyRecipe":recipe.get("label"),
        "marketRecipeId":mr.get("id"),"marketRecipeLabel":mr.get("label"),"marketScore":mr.get("marketScore"),
        "parsedDirective":parsed.to_dict(),
        "referenceDNA":ref_dna,
        "referenceOwnership":reference_ownership,
        "structuredTrackPlan":plan_for_prompt,
        "trackPlanMeta":track_plan_meta,
        "performanceInsights":performance_insights,
        "directiveEmbeddingMode":directive_embedding_mode,
        "directiveDigest":directive_digest,
        "priorityStack":["latest user brief","structured locked track plan","trusted imported planning data","custom master","market recipe/channel preset","local generation feedback","reference DNA","public rules","legacy music rules"],
        "trustedImportedFields":["story/episode source","POV","trackNo/order","story acts","track-specific scenes","listenerSituation","fixed titles/hooks","alreadyUsed histories","explicit locks"],
        "replaceableLegacyFields":["old model version","obsolete BPM policy","old singer age/weight","track-by-track singer swapping","legacy breath-mix ratios","outdated prompt syntax","stale genre hierarchy"],
        "sources":public_rules.get("sources",[]),
        "qa":qa
    }
    return instruction,manifest,qa
