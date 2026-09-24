import sys, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.track_plan import extract_track_plan, recompute_track_plan, validate_track_plan
from core.compiler import compile_instruction
from core.io_utils import load_json
from core.market import recommend

PRESETS=load_json(ROOT/'data'/'channel_presets.json')
RECIPES=load_json(ROOT/'data'/'genre_recipes.json')
PUBLIC=load_json(ROOT/'data'/'public_rules.json')
MARKET=load_json(ROOT/'data'/'market_catalog.json')


def sample_directive():
    table=['[This pack\'s 15-track plan]','| Track | Genre | BPM | Vocal | Structure | Intro | Scene frame | Role |','| --- | --- | --- | --- | --- | --- | --- | --- |']
    for i in range(1,16):
        genre=['Mellow Boom-Bap','Lo-fi Hip-Hop Study','Chill Rap','Jazz Rap','Trap-Soul'][(i-1)%5]
        bpm=[78,74,77,87,74,84,76,82,97,74,89,82,78,84,64][i-1]
        role='flagship' if i in (2,9) else ('memory-focused late track' if i in (11,13) else 'steady')
        table.append(f'| {i} | {genre} | {bpm} BPM | male | T{1+(i%5)} | instrumental | jpstory-train-{i} | {role} |')
    story=[]; scenes=[]
    for i in range(1,16):
        story.append(f'- T{i}: Act {1+(i-1)//3} / story beat {i} - his first-person interpretation - vocal=male - title="Title {i}" - hook="Hook {i}"')
        scenes.append(f'  Track {i}: 같은 기차 안에서 장면 {i}를 떠올린다.\n    emotional turn: 감정 전환 {i}\n    time: the present day / cast: two people / motion: train')
    legacy='\n'.join(['full-voiced male tenor, firm glottal closure','soft male voice just above a whisper','male baritone with lowered larynx']*100)
    return '\n'.join(['001. 窓ぎわの君が気になった','彼のSTORY / male POV / Japanese / 15 tracks']+story+table+['[Lyric scenes]']+scenes+[legacy])


def test_extract_15_track_plan_and_locks():
    plan,meta=extract_track_plan(sample_directive(),15)
    assert len(plan)==15
    assert meta['trackCount']==15
    assert plan[0]['trusted']['title']=='Title 1'
    assert '장면 1' in plan[0]['trusted']['listenerSituation']
    assert plan[0]['locks']['story'] and plan[0]['locks']['scene']
    assert plan[14]['importedMusic']['BPM']==64


def test_recompute_chili_male_replaces_legacy_music_not_story():
    plan,meta=extract_track_plan(sample_directive(),15)
    rows=recommend(MARKET,'JP','vocal_story','vocal','Japanese',20)
    mr=next((r for r in rows if 'Chill' in r.get('label','')), rows[0])
    new,rmeta=recompute_track_plan(plan,'chili_male',PRESETS['chili_male'],mr,'Core 92-100 BPM; Flagship 96-104; Memory 88-92')
    assert new[14]['trusted']['title']=='Title 15'
    assert '장면 15' in new[14]['trusted']['listenerSituation']
    assert 88 <= new[14]['recomputed']['BPM'] <= 104
    assert new[14]['recomputed']['genre'].startswith('Chill Rap')
    assert 'speech-forward' in new[14]['recomputed']['vocal']
    assert any(r['recomputed']['musicRole']=='Anchor' for r in new)
    q=validate_track_plan(new,15)
    assert not any(x['level']=='FAIL' for x in q)


def test_compile_embeds_authoritative_structured_plan():
    raw=sample_directive(); plan,pmeta=extract_track_plan(raw,15)
    rows=recommend(MARKET,'JP','vocal_story','vocal','Japanese',20); mr=rows[0]
    plan,rmeta=recompute_track_plan(plan,'chili_male',PRESETS['chili_male'],mr,'Core 92-100 BPM; Flagship 96-104; Memory 88-92'); pmeta.update(rmeta)
    inst,manifest,qa=compile_instruction(raw,'chili_male',PRESETS['chili_male'],RECIPES['auto'],PUBLIC,market_recipe=mr,market='JP',goal='vocal_story',song_count=15,structured_track_plan=plan,track_plan_meta=pmeta)
    assert 'STRUCTURED TRACK PLAN — AUTHORITATIVE WHEN PRESENT' in inst
    assert 'TRACK PLAN LOCK CONTRACT' in inst
    assert manifest['compilerVersion']=='0.4.1'
    assert len(manifest['structuredTrackPlan'])==15
    assert manifest['structuredTrackPlan'][0]['locks']['story'] is True


def test_hybrid_does_not_reinject_full_legacy_directive():
    raw=sample_directive(); plan,pmeta=extract_track_plan(raw,15)
    rows=recommend(MARKET,'JP','vocal_story','vocal','Japanese',20); mr=rows[0]
    plan,rmeta=recompute_track_plan(plan,'chili_male',PRESETS['chili_male'],mr,''); pmeta.update(rmeta)
    inst,manifest,qa=compile_instruction(raw,'chili_male',PRESETS['chili_male'],RECIPES['auto'],PUBLIC,mode='HYBRID',market_recipe=mr,market='JP',goal='vocal_story',song_count=15,structured_track_plan=plan,track_plan_meta=pmeta)
    assert manifest['directiveEmbeddingMode']=='STRUCTURED_DIGEST_ONLY'
    assert 'soft male voice just above a whisper' not in inst
    assert 'male baritone with lowered larynx' not in inst
    assert 'Title 1' in inst and '장면 1' in inst


def test_custom_master_fingerprint_and_ranges_override():
    raw=sample_directive(); plan,_=extract_track_plan(raw,15)
    mr=recommend(MARKET,'JP','vocal_story','vocal','Japanese',20)[0]
    master="""핵심 장르: Chill Rap
[FIXED VOICE FINGERPRINT — 15곡 공통 70~80%]
- one young-adult Japanese male tenor / light tenor-baritone
- close-mic, speech-forward, intimate but alert
- warm-light chest core, forward oral resonance
- controlled breath texture 10~20%
- subtle dry grain 5~12%
- compact clipped endings
[PHRASING FINGERPRINT]
- Verse 체감 40~55% rap-forward / speech-rhythmic
- syncopated pickup
- slight behind the beat
- micro-rest
Core BPM 권장 92~100
Flagship 96~104
Memory 84~92
"""
    new,meta=recompute_track_plan(plan,'chili_male',PRESETS['chili_male'],mr,master)
    assert meta['rangesUsed']['memory']==[84,92]
    assert 'warm-light chest core' in new[0]['recomputed']['vocal']
    assert meta['masterProfile']['genre']=='Chill Rap'
