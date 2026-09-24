import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.io_utils import load_json, read_text
from core.compiler import compile_instruction
from core.parser import parse_directive
from core.validator import validate_generated_json

presets=load_json(ROOT/'data'/'channel_presets.json')
recipes=load_json(ROOT/'data'/'genre_recipes.json')
public=load_json(ROOT/'data'/'public_rules.json')
raw=read_text(ROOT/'samples'/'001_male_story_brief.txt')
p=parse_directive(raw)
assert p.episode_id=='001', p
assert p.story_pov=='male', p
inst,manifest,qa=compile_instruction(raw,'chili_male',presets['chili_male'],recipes['chill_rap'],public,'v6','HYBRID','','')
assert 'STRUCTURED_DIGEST_ONLY' in inst
assert 'LEGACY DIRECTIVE HANDLING' in inst
assert 'Chill Rap' in inst
assert manifest['parsedDirective']['episode_id']=='001'
mock={'songs':[]}
for i in range(1,16):
    mock['songs'].append({'trackNo':i,'title':f'T{i}','lyrics':'[Verse]\nテスト','stylePrompt':'Chill Rap, 98 BPM; male lead; dry rim, moving bass; Bridge contrast; Final payoff.','negativeStyleText':'female lead, duet','vocalType':'Male Solo'})
issues=validate_generated_json(json.dumps(mock,ensure_ascii=False),presets['chili_male'])
assert not any(x['level']=='FAIL' for x in issues), issues
print('PASS')
