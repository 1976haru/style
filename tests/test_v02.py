import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.market import recommend
from core.reference_dna import extract_reference_dna
from core.compiler import compile_instruction
from core.io_utils import load_json

MARKET=load_json(ROOT/'data'/'market_catalog.json')
PRESETS=load_json(ROOT/'data'/'channel_presets.json')
RECIPES=load_json(ROOT/'data'/'genre_recipes.json')
PUBLIC=load_json(ROOT/'data'/'public_rules.json')

def test_jp_market_recommendation():
    rows=recommend(MARKET,'JP','revenue_balance','any','any',8)
    assert rows
    assert all('JP' in r['markets'] for r in rows)
    assert rows[0]['marketScore'] >= rows[-1]['marketScore']

def test_reference_json_dna_no_lyric_copy():
    sample={"songs":[{"trackNo":1,"BPM":98,"vocalType":"Female Solo","genreText":"Chill Rap","stylePrompt":"Chill Rap, 98 BPM; dry rim; moving bass; speech-forward female","negativeStyleText":"power belt, hard trap","lyrics":"[Verse 1]\nこれは秘密の一行\n[Chorus]\n忘れないで"}]}
    dna=extract_reference_dna(json.dumps(sample,ensure_ascii=False))
    assert dna['songCount']==1
    assert dna['bpmSummary']['avg']==98
    dump=json.dumps(dna,ensure_ascii=False)
    assert 'これは秘密の一行' not in dump
    assert dna['copyrightMode']=='STRUCTURE_ONLY'

def test_compile_without_user_directive():
    rows=recommend(MARKET,'KR','cafe_store','instrumental','any',5)
    mr=rows[0]
    inst,manifest,qa=compile_instruction('', 'market_auto', PRESETS['market_auto'], RECIPES['auto'], PUBLIC, market_recipe=mr, market='KR', goal='cafe_store', song_count=20)
    assert 'UNIVERSAL MARKET RECIPE' in inst
    assert manifest['songCount']==20
    assert manifest['marketRecipeId']==mr['id']
