import sys, uuid
from contextlib import contextmanager
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from core.feedback import init_feedback_db, add_feedback, aggregate_feedback, apply_feedback_ranking, build_feedback_insights
from core.compiler import compile_instruction
from core.io_utils import load_json

PRESETS=load_json(ROOT/'data'/'channel_presets.json')
RECIPES=load_json(ROOT/'data'/'genre_recipes.json')
PUBLIC=load_json(ROOT/'data'/'public_rules.json')


@contextmanager
def _project_db():
    """Use the project volume so Windows SQLite locking is exercised reliably."""
    db = ROOT / f'.test_feedback_{uuid.uuid4().hex}.sqlite3'
    try:
        yield db
    finally:
        if db.exists():
            db.unlink()


def _rec(recipe='jp_chill_test', decision='KEEP', score=5, issue=None):
    return {
        'session_id':'s1','market':'JP','goal':'vocal_story','preset_id':'chili_male',
        'market_recipe_id':recipe,'market_recipe_label':'JP Chill Test','model':'v6','episode':'EP001',
        'track_no':1,'title':'Test','music_role':'Core','bpm':98,'genre':'Chill Rap','vocal':'speech-forward male',
        'performance_signature':'dry pickup; micro-rest','style_prompt':'Chill Rap, 98 BPM',
        'decision':decision,'overall':score,'vocal_identity':score,'hook':score,'groove':score,'prompt_adherence':score,
        'issue_tags':[issue] if issue else [],'notes':''
    }


def test_feedback_threshold_and_ranking():
    with _project_db() as db:
        init_feedback_db(db)
        rows=[{'id':'jp_chill_test','label':'JP Chill Test','marketScore':7.0,'demand':7,'repeatability':8,'competitionIntensity':6,'aiFit':9,'monetizationProxy':7,'bpmRange':[92,102],'vocalMode':'vocal'}]
        ranked=apply_feedback_ranking(rows,db,min_samples=3)
        assert ranked[0]['feedbackN']==0 and ranked[0]['adjustedScore10']==7.0
        add_feedback(db,_rec(score=5)); add_feedback(db,_rec(score=5))
        ranked=apply_feedback_ranking(rows,db,min_samples=3)
        assert ranked[0]['feedbackN']==2 and ranked[0]['adjustedScore10']==7.0
        add_feedback(db,_rec(score=5))
        ranked=apply_feedback_ranking(rows,db,min_samples=3)
        assert ranked[0]['feedbackN']==3
        assert ranked[0]['adjustedScore10']>7.0


def test_feedback_insights_activate_after_three_and_capture_failures():
    with _project_db() as db:
        init_feedback_db(db)
        add_feedback(db,_rec(decision='KEEP',score=5))
        add_feedback(db,_rec(decision='KEEP',score=4))
        x=build_feedback_insights(db,'chili_male','jp_chill_test',3)
        assert x['active'] is False
        add_feedback(db,_rec(decision='REGEN',score=2,issue='generic_vocal'))
        x=build_feedback_insights(db,'chili_male','jp_chill_test',3)
        assert x['active'] is True and x['n']==3
        assert 'generic_vocal' in x['topIssues']
        assert any('failure tags' in g for g in x['guidance'])


def test_compiler_embeds_feedback_only_as_soft_prior():
    insights={'active':True,'n':5,'scope':'recipe','guidance':['Recurring failure tags to actively guard against: generic_vocal(3)']}
    inst,manifest,qa=compile_instruction(
        '', 'chili_male', PRESETS['chili_male'], RECIPES['auto'], PUBLIC,
        market_recipe={'id':'jp_chill_test','label':'JP Chill Test','genreFamily':'Chill Rap','vocalMode':'vocal','languages':['Japanese'],'bpmRange':[92,102]},
        performance_insights=insights
    )
    assert 'LOCAL GENERATION FEEDBACK' in inst
    assert 'generic_vocal' in inst
    assert 'soft empirical prior' in inst
    assert manifest['compilerVersion']=='0.4.1'
    assert manifest['performanceInsights']['active'] is True


def test_feedback_db_aggregate():
    with _project_db() as db:
        add_feedback(db,_rec(decision='KEEP',score=5))
        add_feedback(db,_rec(decision='REGEN',score=2,issue='rap_weak'))
        agg=aggregate_feedback(db)
        assert agg['total']==2
        assert agg['byRecipe']['jp_chill_test']['n']==2
        assert agg['issueCounts']['rap_weak']==1
