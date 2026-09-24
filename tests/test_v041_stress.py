import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.track_plan import _parse_master_ranges, extract_track_plan, recompute_track_plan, validate_track_plan
from core.io_utils import load_json
PRESETS=load_json(ROOT/'data'/'channel_presets.json')

def test_lyric_char_range_is_not_bpm():
    master='''Anchor 460~560 chars\nCore BPM 권장 92~100\nFlagship 96~104\nMemory 84~92는 1~2곡까지만'''
    r=_parse_master_ranges(master)
    assert r['core']==(92,100)
    assert r['anchor']==(96,104)
    assert r['memory']==(84,92)
    assert all(max(v)<=240 for v in r.values())

def test_dual_preserves_track_vocal_roles():
    songs={'songs':[
      {'trackNo':1,'title':'M','hookPhrase':'M','BPM':94,'genre':'Chill Rap','vocalType':'Male Solo','listenerSituation':'a'},
      {'trackNo':2,'title':'F','hookPhrase':'F','BPM':96,'genre':'Chill Rap','vocalType':'Female Solo','listenerSituation':'b'},
      {'trackNo':3,'title':'D','hookPhrase':'D','BPM':98,'genre':'Chill Rap','vocalType':'Male-Female Asymmetric Duet','listenerSituation':'c'},
    ]}
    rows,_=extract_track_plan(__import__('json').dumps(songs),3)
    rows,_=recompute_track_plan(rows,'chili_dual',PRESETS['chili_dual'],{'vocalMode':'vocal','bpmRange':[92,104]},'')
    assert 'male solo only' in rows[0]['recomputed']['vocal'].lower()
    assert 'female solo only' in rows[1]['recomputed']['vocal'].lower()
    assert 'exactly two' in rows[2]['recomputed']['vocal'].lower()

def test_tint_not_duplicated():
    songs={'songs':[{'trackNo':1,'title':'A','hookPhrase':'A','BPM':94,'genre':'Chill Rap / lo-fi soul tint','vocalType':'Male Solo','listenerSituation':'x'}]}
    rows,_=extract_track_plan(__import__('json').dumps(songs),1)
    rows,_=recompute_track_plan(rows,'chili_male',PRESETS['chili_male'],{'vocalMode':'vocal','bpmRange':[92,104]},'')
    assert 'tint tint' not in rows[0]['recomputed']['genre'].lower()

def test_validator_catches_impossible_bpm():
    songs={'songs':[{'trackNo':1,'title':'A','hookPhrase':'A','BPM':94,'genre':'Chill Rap','vocalType':'Male Solo','listenerSituation':'x'}]}
    rows,_=extract_track_plan(__import__('json').dumps(songs),1)
    rows[0]['recomputed']['BPM']=542
    q=validate_track_plan(rows,1)
    assert any(x['code']=='TRACK_PLAN_BPM_RANGE' for x in q)

def test_female_bpm_energy_section_beats_rap_percentage():
    master='''12. BPM / ENERGY\n82~88:\nMemory / tender low-energy\n88~94:\nsoft sweet chill rap\n94~102:\n여성 Core 주력\n100~108:\nFlagship / airy 2-step\n여성 Core는 Verse 45~60% rap-forward, 세트 중심 94~102 BPM을 기본값으로 한다.'''
    r=_parse_master_ranges(master)
    assert r['memory']==(82,88)
    assert r['core']==(94,102)
    assert r['anchor']==(100,108)

def test_gender_conflict_ignores_negative_excludes_and_female_not_male_substring():
    from core.validator import analyze_directive_conflicts, validate_generated_json
    male_raw=__import__('json').dumps({'songs':[{'vocalType':'Male Solo','negativeStyleText':'female lead, duet'}]})
    assert not any(x['code']=='MALE_LOCK_CONFLICT' for x in analyze_directive_conflicts(male_raw,PRESETS['chili_male']))
    female_song={'songs':[{'trackNo':i,'title':f'T{i}','lyrics':'x','stylePrompt':'Chill Rap, test','vocalType':'Female Solo','negativeStyleText':'male lead'} for i in range(1,16)]}
    q=validate_generated_json(__import__('json').dumps(female_song),PRESETS['chili_female'])
    assert not any(x['code']=='GENDER' for x in q)
