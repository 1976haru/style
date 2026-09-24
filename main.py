from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from core.io_utils import load_json, read_text, write_text, write_json
from core.compiler import compile_instruction
from core.validator import validate_generated_json
from core.market import recommend
from core.reference_dna import extract_reference_dna
from core.track_plan import extract_track_plan, recompute_track_plan, validate_track_plan
from core.feedback import (
    init_feedback_db, add_feedback, list_feedback, delete_feedback, aggregate_feedback,
    apply_feedback_ranking, build_feedback_insights, export_feedback_json, export_feedback_csv, ISSUE_TAGS
)
from core.learning import (
    analyze_feedback_patterns, build_ab_experiment_plan, validate_lock_preservation,
    select_feedback_scope, build_experiment_manifest, analyze_ab_results,
)

PRESETS = load_json(ROOT/'data'/'channel_presets.json')
RECIPES = load_json(ROOT/'data'/'genre_recipes.json')
PUBLIC = load_json(ROOT/'data'/'public_rules.json')
MARKET = load_json(ROOT/'data'/'market_catalog.json')
SOURCES = load_json(ROOT/'data'/'research_sources.json')
FEEDBACK_TAG_DATA = load_json(ROOT/'data'/'feedback_issue_tags.json')

class App(tk.Tk):
    def __init__(self):
        print('[APP-INIT 1/6] creating Tk root...', flush=True)
        super().__init__()
        print('[APP-INIT 2/6] Tk root created', flush=True)
        self.title('Suno Master Prompt Studio v0.5-dev — Evidence-guided A/B Learning')
        self.geometry('1540x960')
        self.minsize(1220,780)
        self.compiled=''; self.manifest={}; self.qa=[]; self.market_rows=[]; self.selected_market_recipe={}
        self.track_plan=[]; self.track_plan_meta={}; self.selected_track_no=None

        self.feedback_db=ROOT/'user_data'/'feedback.sqlite3'
        print(f'[APP-INIT 3/6] feedback DB scheduled after UI paint: {self.feedback_db}', flush=True)

        self.feedback_tracks=[]; self.feedback_track_map={}; self.feedback_selected_id=None
        self.learning_analysis={}; self.learning_scope={}; self.experiment_plan=[]; self.experiment_manifest={}; self.ab_results={}

        print('[APP-INIT 4/6] building UI...', flush=True)
        self._build()
        print('[APP-INIT 5/6] UI widgets built', flush=True)
        self.update_idletasks()
        print('[APP-INIT 6/6] initial UI paint complete', flush=True)
        self.after(50, self._startup_initialize)

    def _startup_initialize(self):
        """Paint the Tk window first, then run data-heavy startup work."""
        try:
            print('[STARTUP] UI ready', flush=True)
            init_feedback_db(self.feedback_db)
            print('[STARTUP] feedback DB ready', flush=True)
            self.run_recommendations()
            print('[STARTUP] market recommendations ready', flush=True)
            self.refresh_feedback_view()
            print('[STARTUP] feedback + learning analysis ready', flush=True)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            try:
                messagebox.showerror('시작 오류', f'초기화 중 오류가 발생했습니다.\n\n{exc}\n\nPowerShell 로그를 확인하세요.')
            except Exception:
                pass

    def _build(self):
        print('[UI 1/10] header/notebook', flush=True)
        hdr=ttk.Frame(self,padding=(10,8)); hdr.pack(fill='x')
        ttk.Label(hdr,text='Suno Master Prompt Studio v0.5-dev',font=('Segoe UI',16,'bold')).pack(side='left')
        ttk.Label(hdr,text='  Track Plan LOCK + Feedback Learning + 15곡 A/B 실험 제안(PROPOSAL ONLY)',font=('Segoe UI',10)).pack(side='left',padx=8)
        nb=ttk.Notebook(self); nb.pack(fill='both',expand=True,padx=10,pady=(0,10))
        self.market_tab=ttk.Frame(nb,padding=8); self.ref_tab=ttk.Frame(nb,padding=8); self.directive_tab=ttk.Frame(nb,padding=8)
        self.plan_tab=ttk.Frame(nb,padding=8); self.master_tab=ttk.Frame(nb,padding=8); self.output_tab=ttk.Frame(nb,padding=8); self.feedback_tab=ttk.Frame(nb,padding=8); self.learning_tab=ttk.Frame(nb,padding=8); self.qa_tab=ttk.Frame(nb,padding=8)
        for tab,label in [(self.market_tab,'1. 시장/장르 추천'),(self.ref_tab,'2. Reference DNA'),(self.directive_tab,'3. 사용자 지시문'),(self.plan_tab,'4. 15곡 Track Plan'),(self.master_tab,'5. 마스터/현재 지시'),(self.output_tab,'6. ChatGPT 최종지시문'),(self.feedback_tab,'7. Suno 결과 Feedback'),(self.learning_tab,'8. 학습/A-B 실험'),(self.qa_tab,'9. QA / 결과검증')]: nb.add(tab,text=label)
        self.nb=nb
        print('[UI 2/10] market tab', flush=True); self._build_market()
        print('[UI 3/10] reference tab', flush=True); self._build_reference()
        print('[UI 4/10] directive tab', flush=True); self._build_directive()
        print('[UI 5/10] track plan tab', flush=True); self._build_plan()
        print('[UI 6/10] master tab', flush=True); self._build_master()
        print('[UI 7/10] output tab', flush=True); self._build_output()
        print('[UI 8/10] feedback tab', flush=True); self._build_feedback()
        print('[UI 9/10] learning tab', flush=True); self._build_learning()
        print('[UI 10/10] QA tab', flush=True); self._build_qa()

    def _build_market(self):
        ctrl=ttk.Frame(self.market_tab); ctrl.pack(fill='x')
        ttk.Label(ctrl,text='시장').pack(side='left'); self.market_var=tk.StringVar(value='JP')
        ttk.Combobox(ctrl,textvariable=self.market_var,state='readonly',width=12,values=['KR','JP','GLOBAL','ANY']).pack(side='left',padx=5)
        ttk.Label(ctrl,text='목표').pack(side='left',padx=(12,0)); self.goal_var=tk.StringVar(value='revenue_balance')
        ttk.Combobox(ctrl,textvariable=self.goal_var,state='readonly',width=19,values=list(MARKET['useCases'].keys())).pack(side='left',padx=5)
        ttk.Label(ctrl,text='보컬').pack(side='left',padx=(12,0)); self.vocal_pref=tk.StringVar(value='any')
        ttk.Combobox(ctrl,textvariable=self.vocal_pref,state='readonly',width=14,values=['any','vocal','instrumental']).pack(side='left',padx=5)
        ttk.Label(ctrl,text='언어').pack(side='left',padx=(12,0)); self.language_var=tk.StringVar(value='any')
        ttk.Combobox(ctrl,textvariable=self.language_var,state='readonly',width=14,values=['any','Korean','Japanese','English','French','Instrumental']).pack(side='left',padx=5)
        ttk.Button(ctrl,text='시장 추천 새로고침',command=self.run_recommendations).pack(side='left',padx=12)
        ttk.Label(self.market_tab,text='점수는 실험 우선순위용 휴리스틱이며 수익을 보장하지 않습니다.',foreground='#555').pack(anchor='w',pady=(8,5))
        cols=('score','adjusted','local','n','label','demand','repeat','competition','ai','money','bpm','vocal'); self.tree=ttk.Treeview(self.market_tab,columns=cols,show='headings',height=11)
        heads={'score':'시장점수','adjusted':'통합점수','local':'실측점수','n':'표본','label':'장르/레시피','demand':'수요','repeat':'반복재생','competition':'경쟁','ai':'AI적합','money':'수익Proxy','bpm':'BPM','vocal':'보컬'}
        widths={'score':68,'adjusted':68,'local':68,'n':45,'label':285,'demand':48,'repeat':62,'competition':48,'ai':52,'money':68,'bpm':82,'vocal':135}
        for c in cols: self.tree.heading(c,text=heads[c]); self.tree.column(c,width=widths[c],anchor='center' if c!='label' else 'w')
        self.tree.pack(fill='x',pady=(0,8)); self.tree.bind('<<TreeviewSelect>>',self.market_selected)
        pane=ttk.Panedwindow(self.market_tab,orient='horizontal'); pane.pack(fill='both',expand=True)
        lf=ttk.Labelframe(pane,text='선택 레시피 상세',padding=6); rf=ttk.Labelframe(pane,text='시장조사 근거 메모',padding=6); pane.add(lf,weight=3); pane.add(rf,weight=2)
        self.market_detail=tk.Text(lf,wrap='word',font=('Consolas',10)); self.market_detail.pack(fill='both',expand=True)
        self.source_text=tk.Text(rf,wrap='word',font=('Consolas',9)); self.source_text.pack(fill='both',expand=True); self.source_text.insert('1.0',json.dumps(SOURCES,ensure_ascii=False,indent=2)); self.source_text.configure(state='disabled')

    def _build_reference(self):
        row=ttk.Frame(self.ref_tab); row.pack(fill='x')
        ttk.Button(row,text='Reference TXT/JSON 불러오기',command=self.load_reference).pack(side='left'); ttk.Button(row,text='Reference 지우기',command=self.clear_reference).pack(side='left',padx=5)
        ttk.Label(row,text='소유권').pack(side='left',padx=(15,5)); self.ownership_var=tk.StringVar(value='external'); ttk.Combobox(row,textvariable=self.ownership_var,state='readonly',width=18,values=['external','user_owned']).pack(side='left')
        ttk.Button(row,text='DNA 분석',command=self.analyze_reference).pack(side='left',padx=8); ttk.Label(row,text='외부 파일은 가사 문장을 복사하지 않고 구조/기술 요소만 추출').pack(side='left',padx=10)
        pw=ttk.Panedwindow(self.ref_tab,orient='horizontal'); pw.pack(fill='both',expand=True,pady=(8,0)); a=ttk.Labelframe(pw,text='원본 Reference',padding=5); b=ttk.Labelframe(pw,text='추출된 Reference DNA',padding=5); pw.add(a,weight=3); pw.add(b,weight=2)
        self.reference=tk.Text(a,wrap='word',font=('Consolas',9)); self.reference.pack(fill='both',expand=True); self.dna_preview=tk.Text(b,wrap='word',font=('Consolas',9)); self.dna_preview.pack(fill='both',expand=True)

    def _build_directive(self):
        row=ttk.Frame(self.directive_tab); row.pack(fill='x')
        ttk.Button(row,text='기존 지시문 TXT/JSON 불러오기',command=self.load_directive).pack(side='left'); ttk.Button(row,text='지우기',command=self.clear_directive).pack(side='left',padx=5)
        ttk.Button(row,text='지시문 → Track Plan 파싱',command=self.parse_track_plan).pack(side='left',padx=(15,5))
        ttk.Label(row,text='Haru Studio/Claude instruction/기존 2,000줄 지시문을 그대로 불러와도 됩니다.').pack(side='left',padx=10)
        self.directive=tk.Text(self.directive_tab,wrap='word',undo=True,font=('Consolas',9)); self.directive.pack(fill='both',expand=True,pady=(8,0))

    def _build_plan(self):
        top=ttk.Frame(self.plan_tab); top.pack(fill='x')
        ttk.Button(top,text='① 지시문 파싱',command=self.parse_track_plan).pack(side='left')
        ttk.Button(top,text='② 최신 마스터로 음악 재계산',command=self.recompute_plan).pack(side='left',padx=5)
        ttk.Button(top,text='스토리/장면 전체 LOCK',command=lambda:self.set_all_locks(True)).pack(side='left',padx=(15,5))
        ttk.Button(top,text='Plan JSON 저장',command=self.save_track_plan).pack(side='left',padx=5)
        self.plan_status=tk.StringVar(value='아직 Track Plan이 없습니다.'); ttk.Label(top,textvariable=self.plan_status).pack(side='left',padx=15)

        cols=('no','lock','arm','axis','title','act','scene','oldbpm','newbpm','oldgenre','newgenre','role','structure')
        self.plan_tree=ttk.Treeview(self.plan_tab,columns=cols,show='headings',height=14)
        labels={'no':'#','lock':'LOCK','arm':'A/B','axis':'실험축','title':'제목','act':'Story Act','scene':'장면','oldbpm':'Old BPM','newbpm':'NEW BPM','oldgenre':'Old Genre','newgenre':'NEW Genre','role':'Music Role','structure':'NEW Structure'}
        widths={'no':38,'lock':55,'arm':42,'axis':115,'title':145,'act':95,'scene':220,'oldbpm':65,'newbpm':70,'oldgenre':130,'newgenre':165,'role':75,'structure':250}
        for c in cols: self.plan_tree.heading(c,text=labels[c]); self.plan_tree.column(c,width=widths[c],anchor='center' if c in ('no','lock','arm','axis','oldbpm','newbpm','role') else 'w')
        self.plan_tree.pack(fill='both',expand=True,pady=(8,6)); self.plan_tree.bind('<<TreeviewSelect>>',self.plan_selected)

        edit=ttk.Labelframe(self.plan_tab,text='선택 트랙 상세 / 예외 Override',padding=6); edit.pack(fill='x')
        row1=ttk.Frame(edit); row1.pack(fill='x')
        self.story_lock=tk.BooleanVar(value=True); self.scene_lock=tk.BooleanVar(value=True); self.title_lock=tk.BooleanVar(value=True); self.hook_lock=tk.BooleanVar(value=True)
        for label,var in [('Story LOCK',self.story_lock),('Scene LOCK',self.scene_lock),('Title LOCK',self.title_lock),('Hook LOCK',self.hook_lock)]: ttk.Checkbutton(row1,text=label,variable=var).pack(side='left',padx=4)
        ttk.Label(row1,text='BPM override').pack(side='left',padx=(20,3)); self.override_bpm=tk.StringVar(); ttk.Entry(row1,textvariable=self.override_bpm,width=7).pack(side='left')
        ttk.Label(row1,text='MusicRole').pack(side='left',padx=(12,3)); self.override_role=tk.StringVar(); ttk.Combobox(row1,textvariable=self.override_role,width=10,values=['','Core','Memory','Anchor']).pack(side='left')
        ttk.Label(row1,text='Genre override').pack(side='left',padx=(12,3)); self.override_genre=tk.StringVar(); ttk.Entry(row1,textvariable=self.override_genre,width=30).pack(side='left')
        ttk.Button(row1,text='선택 트랙에 적용',command=self.apply_track_override).pack(side='left',padx=10)
        self.plan_detail=tk.Text(edit,height=7,wrap='word',font=('Consolas',9)); self.plan_detail.pack(fill='x',pady=(6,0))

    def _build_master(self):
        top=ttk.Frame(self.master_tab); top.pack(fill='x')
        ttk.Label(top,text='시리즈/채널 프리셋').pack(side='left'); self.preset_var=tk.StringVar(value='market_auto')
        self.preset_cb=ttk.Combobox(top,textvariable=self.preset_var,state='readonly',width=28,values=list(PRESETS.keys())); self.preset_cb.pack(side='left',padx=5); self.preset_cb.bind('<<ComboboxSelected>>',lambda e:self.refresh_preset())
        ttk.Label(top,text='구형 레시피(선택)').pack(side='left',padx=(12,0)); self.recipe_var=tk.StringVar(value='auto'); ttk.Combobox(top,textvariable=self.recipe_var,state='readonly',width=22,values=list(RECIPES.keys())).pack(side='left',padx=5)
        ttk.Label(top,text='모델').pack(side='left',padx=(12,0)); self.model_var=tk.StringVar(value='v6'); ttk.Combobox(top,textvariable=self.model_var,state='readonly',width=10,values=['v6','v6-wild','v6-mini']).pack(side='left',padx=5)
        ttk.Label(top,text='모드').pack(side='left',padx=(12,0)); self.mode_var=tk.StringVar(value='HYBRID'); ttk.Combobox(top,textvariable=self.mode_var,state='readonly',width=14,values=['HYBRID','MASTER_FIRST','PRESERVE']).pack(side='left',padx=5)
        ttk.Label(top,text='곡수').pack(side='left',padx=(12,0)); self.song_count=tk.IntVar(value=15); ttk.Spinbox(top,from_=1,to=50,textvariable=self.song_count,width=5).pack(side='left',padx=5)
        ttk.Label(top,text='출력').pack(side='left',padx=(12,0)); self.output_mode=tk.StringVar(value='full_pack'); ttk.Combobox(top,textvariable=self.output_mode,state='readonly',width=17,values=['full_pack','lyrics_plus_prompt','prompt_only']).pack(side='left',padx=5)
        row=ttk.Frame(self.master_tab); row.pack(fill='x',pady=(8,0)); ttk.Button(row,text='현재 마스터 TXT 불러오기',command=self.load_master).pack(side='left'); ttk.Button(row,text='마스터 반영 Track Plan 재계산',command=self.recompute_plan).pack(side='left',padx=5)
        ttk.Label(row,text='현재 제작 지시(최우선)').pack(side='left',padx=(15,5)); self.episode=tk.Entry(row); self.episode.pack(side='left',fill='x',expand=True)
        pw=ttk.Panedwindow(self.master_tab,orient='vertical'); pw.pack(fill='both',expand=True,pady=(8,0)); a=ttk.Labelframe(pw,text='현재 마스터(선택)',padding=5); b=ttk.Labelframe(pw,text='프리셋 미리보기',padding=5); pw.add(a,weight=3); pw.add(b,weight=2)
        # Tk uses ``master`` internally for its parent-widget chain. Replacing
        # self.master here creates a cycle and makes later Variable creation
        # loop forever while resolving the default root.
        self.master_text=tk.Text(a,wrap='word',font=('Consolas',9)); self.master_text.pack(fill='both',expand=True); self.preset_preview=tk.Text(b,wrap='word',font=('Consolas',9)); self.preset_preview.pack(fill='both',expand=True); self.refresh_preset()

    def _build_output(self):
        bar=ttk.Frame(self.output_tab); bar.pack(fill='x'); ttk.Button(bar,text='Track Plan 포함 컴파일',command=self.compile).pack(side='left'); ttk.Button(bar,text='클립보드 복사',command=self.copy_output).pack(side='left',padx=5); ttk.Button(bar,text='TXT 저장',command=self.save_instruction).pack(side='left'); ttk.Button(bar,text='패키지 저장',command=self.save_package).pack(side='left',padx=5)
        self.output=tk.Text(self.output_tab,wrap='word',font=('Consolas',9)); self.output.pack(fill='both',expand=True,pady=(8,0))

    def _build_feedback(self):
        print('[FEEDBACK-UI 1] top controls start', flush=True)
        top=ttk.Frame(self.feedback_tab); top.pack(fill='x')
        ttk.Label(top,text='실제 Suno 생성 결과를 평가하면 최소 3개 표본부터 시장/레시피 추천과 다음 컴파일에 반영됩니다.').pack(side='left')
        ttk.Button(top,text='현재 Track Plan 가져오기',command=self.feedback_from_plan).pack(side='left',padx=(14,4))
        ttk.Button(top,text='생성결과 JSON 불러오기',command=self.feedback_load_result).pack(side='left',padx=4)
        ttk.Button(top,text='DB 새로고침',command=self.refresh_feedback_view).pack(side='left',padx=4)
        ttk.Button(top,text='JSON 백업',command=self.export_feedback_json_ui).pack(side='right',padx=4)
        ttk.Button(top,text='CSV 내보내기',command=self.export_feedback_csv_ui).pack(side='right',padx=4)

        print('[FEEDBACK-UI 2] top controls done; entry start', flush=True)
        entry=ttk.Labelframe(self.feedback_tab,text='선택 트랙 평가',padding=7); entry.pack(fill='x',pady=(8,6))
        r1=ttk.Frame(entry); r1.pack(fill='x')
        ttk.Label(r1,text='트랙').pack(side='left'); self.fb_track_var=tk.StringVar(); self.fb_track_cb=ttk.Combobox(r1,textvariable=self.fb_track_var,state='readonly',width=42); self.fb_track_cb.pack(side='left',padx=5); self.fb_track_cb.bind('<<ComboboxSelected>>',lambda e:self.feedback_track_selected())
        ttk.Label(r1,text='판정').pack(side='left',padx=(12,3)); self.fb_decision=tk.StringVar(value='KEEP'); ttk.Combobox(r1,textvariable=self.fb_decision,state='readonly',width=9,values=['KEEP','MAYBE','REGEN']).pack(side='left')
        ttk.Label(r1,text='Runtime sec').pack(side='left',padx=(12,3)); self.fb_runtime=tk.StringVar(); ttk.Entry(r1,textvariable=self.fb_runtime,width=8).pack(side='left')
        ttk.Label(r1,text='Session').pack(side='left',padx=(12,3)); self.fb_session=tk.StringVar(); ttk.Entry(r1,textvariable=self.fb_session,width=18).pack(side='left')

        print('[FEEDBACK-UI 3] entry row 1 done; ratings start', flush=True)
        r2=ttk.Frame(entry); r2.pack(fill='x',pady=(6,0))
        self.fb_overall=tk.IntVar(value=4); self.fb_vocal=tk.IntVar(value=4); self.fb_hook=tk.IntVar(value=4); self.fb_groove=tk.IntVar(value=4); self.fb_adherence=tk.IntVar(value=4)
        for label,var in [('전체',self.fb_overall),('보컬고유성',self.fb_vocal),('훅',self.fb_hook),('그루브',self.fb_groove),('프롬프트준수',self.fb_adherence)]:
            ttk.Label(r2,text=label).pack(side='left',padx=(8,2)); ttk.Spinbox(r2,from_=1,to=5,textvariable=var,width=3).pack(side='left')
        ttk.Button(r2,text='평가 저장',command=self.save_feedback).pack(side='right',padx=4)

        print('[FEEDBACK-UI 4] ratings done; tags start', flush=True)
        r3=ttk.Frame(entry); r3.pack(fill='x',pady=(6,0)); ttk.Label(r3,text='문제태그').pack(side='left')
        self.fb_tag_vars={}
        labels={x['id']:x['label'] for x in FEEDBACK_TAG_DATA.get('tags',[])}
        tag_box=ttk.Frame(r3); tag_box.pack(side='left',fill='x',expand=True,padx=5)
        for i,tag in enumerate(ISSUE_TAGS):
            v=tk.BooleanVar(value=False); self.fb_tag_vars[tag]=v
            ttk.Checkbutton(tag_box,text=labels.get(tag,tag),variable=v).grid(row=i//6,column=i%6,sticky='w',padx=3)
        print(f'[FEEDBACK-UI 5] {len(ISSUE_TAGS)} tag checkbuttons done', flush=True)
        ttk.Label(r3,text='메모').pack(side='left',padx=(10,3)); self.fb_notes=tk.StringVar(); ttk.Entry(r3,textvariable=self.fb_notes,width=38).pack(side='left')

        print('[FEEDBACK-UI 6] tags done; paned window start', flush=True)
        split=ttk.Panedwindow(self.feedback_tab,orient='vertical'); split.pack(fill='both',expand=True,pady=(4,0))
        print('[FEEDBACK-UI 7] paned window created; panes start', flush=True)
        a=ttk.Labelframe(split,text='최근 평가',padding=5); b=ttk.Labelframe(split,text='Recipe Ranking / 학습 요약',padding=5); split.add(a,weight=3); split.add(b,weight=2)
        print('[FEEDBACK-UI 8] panes done; tree start', flush=True)
        cols=('id','date','decision','arm','axis','track','title','recipe','role','bpm','overall','vocal','hook','groove','adh')
        self.fb_tree=ttk.Treeview(a,columns=cols,show='headings',height=10)
        heads={'id':'ID','date':'날짜','decision':'판정','arm':'A/B','axis':'실험축','track':'#','title':'제목','recipe':'Market Recipe','role':'Role','bpm':'BPM','overall':'전체','vocal':'보컬','hook':'훅','groove':'그루브','adh':'준수'}
        widths={'id':45,'date':120,'decision':65,'arm':42,'axis':105,'track':38,'title':170,'recipe':160,'role':60,'bpm':52,'overall':45,'vocal':45,'hook':45,'groove':45,'adh':45}
        for c in cols: self.fb_tree.heading(c,text=heads[c]); self.fb_tree.column(c,width=widths[c],anchor='center' if c not in ('title','recipe') else 'w')
        print('[FEEDBACK-UI 9] tree columns done; final widgets start', flush=True)
        self.fb_tree.pack(fill='both',expand=True); self.fb_tree.bind('<<TreeviewSelect>>',self.feedback_record_selected)
        row=ttk.Frame(a); row.pack(fill='x',pady=(4,0)); ttk.Button(row,text='선택 평가 삭제',command=self.delete_feedback_ui).pack(side='left')
        self.fb_summary=tk.Text(b,wrap='word',font=('Consolas',9),height=10); self.fb_summary.pack(fill='both',expand=True)
        print('[FEEDBACK-UI 10] feedback UI done', flush=True)

    def _build_learning(self):
        top=ttk.Frame(self.learning_tab); top.pack(fill='x')
        ttk.Label(top,text='현재 preset + market recipe의 실제 Feedback만 사용합니다. 30곡 미만은 관찰 전용이며 A/B 활성화 금지.').pack(side='left')
        ttk.Button(top,text='학습 분석 새로고침',command=self.refresh_learning_analysis).pack(side='left',padx=8)
        ttk.Button(top,text='Experiment Manifest 저장',command=self.save_experiment_manifest).pack(side='right')
        self.learning_status=tk.StringVar(value='학습 분석 대기'); ttk.Label(top,textvariable=self.learning_status).pack(side='right',padx=12)

        split=ttk.Panedwindow(self.learning_tab,orient='horizontal'); split.pack(fill='both',expand=True,pady=(8,0))
        left=ttk.Labelframe(split,text='성공곡/실패 패턴 분석',padding=6); right=ttk.Labelframe(split,text='15곡 A/B 제안 (실제 음악값 미변경)',padding=6)
        split.add(left,weight=2); split.add(right,weight=3)
        self.learning_text=tk.Text(left,wrap='word',font=('Consolas',9)); self.learning_text.pack(fill='both',expand=True)

        cols=('no','arm','axis','title','proposal')
        self.exp_tree=ttk.Treeview(right,columns=cols,show='headings',height=18)
        labels={'no':'#','arm':'A/B','axis':'실험축','title':'제목','proposal':'제안 내용'}
        widths={'no':40,'arm':45,'axis':130,'title':180,'proposal':520}
        for key in cols:
            self.exp_tree.heading(key,text=labels[key]); self.exp_tree.column(key,width=widths[key],anchor='center' if key in ('no','arm') else 'w')
        self.exp_tree.pack(fill='both',expand=True)
        ttk.Label(right,text='B-arm은 제안만 기록합니다. 현재 recomputed BPM/Genre/Vocal/Structure와 Story LOCK을 자동 변경하지 않습니다.',foreground='#555').pack(anchor='w',pady=(6,0))

    def _build_qa(self):
        bar=ttk.Frame(self.qa_tab); bar.pack(fill='x'); ttk.Button(bar,text='ChatGPT 결과 JSON 검증',command=self.validate_result_file).pack(side='left'); ttk.Button(bar,text='현재 QA 새로고침',command=self.render_qa).pack(side='left',padx=5)
        self.qa_text=tk.Text(self.qa_tab,wrap='word',font=('Consolas',9)); self.qa_text.pack(fill='both',expand=True,pady=(8,0))

    def run_recommendations(self):
        base=recommend(MARKET,self.market_var.get(),self.goal_var.get(),self.vocal_pref.get(),self.language_var.get(),top_n=20)
        self.market_rows=apply_feedback_ranking(base,self.feedback_db,min_samples=3)[:12]
        for x in self.tree.get_children(): self.tree.delete(x)
        for i,r in enumerate(self.market_rows):
            local='-' if r.get('feedbackScore') is None else f"{r['feedbackScore']/10:.1f}"
            self.tree.insert('', 'end', iid=str(i), values=(r['marketScore'],r.get('adjustedScore10',r['marketScore']),local,r.get('feedbackN',0),r['label'],r['demand'],r['repeatability'],r['competitionIntensity'],r['aiFit'],r['monetizationProxy'],f"{r['bpmRange'][0]}-{r['bpmRange'][1]}",r['vocalMode']))
        if self.market_rows: self.tree.selection_set('0'); self.tree.focus('0'); self.market_selected()

    def market_selected(self,event=None):
        sel=self.tree.selection();
        if not sel: return
        self.selected_market_recipe=self.market_rows[int(sel[0])]; self.market_detail.delete('1.0','end'); self.market_detail.insert('1.0',json.dumps(self.selected_market_recipe,ensure_ascii=False,indent=2))

    def load_reference(self):
        p=filedialog.askopenfilename(filetypes=[('Text/JSON','*.txt *.json'),('All','*.*')])
        if p: self.reference.delete('1.0','end'); self.reference.insert('1.0',read_text(p)); self.analyze_reference()
    def clear_reference(self): self.reference.delete('1.0','end'); self.dna_preview.delete('1.0','end')
    def analyze_reference(self):
        dna=extract_reference_dna(self.reference.get('1.0','end')); self.dna_preview.delete('1.0','end'); self.dna_preview.insert('1.0',json.dumps(dna,ensure_ascii=False,indent=2))

    def load_directive(self):
        p=filedialog.askopenfilename(filetypes=[('Text/JSON','*.txt *.json'),('All','*.*')])
        if p:
            self.directive.delete('1.0','end'); self.directive.insert('1.0',read_text(p)); self.parse_track_plan()
    def clear_directive(self):
        self.directive.delete('1.0','end'); self.track_plan=[]; self.track_plan_meta={}; self.render_track_plan()
    def load_master(self):
        p=filedialog.askopenfilename(filetypes=[('Text/JSON','*.txt *.json'),('All','*.*')])
        if p: self.master_text.delete('1.0','end'); self.master_text.insert('1.0',read_text(p))
    def refresh_preset(self):
        p=PRESETS[self.preset_var.get()]; self.preset_preview.delete('1.0','end'); self.preset_preview.insert('1.0',json.dumps(p,ensure_ascii=False,indent=2))

    def parse_track_plan(self):
        raw=self.directive.get('1.0','end').strip(); self.track_plan,self.track_plan_meta=extract_track_plan(raw,int(self.song_count.get()))
        self.refresh_learning_analysis(); self.nb.select(self.plan_tab)
        self.plan_status.set(f"파싱 완료: {len(self.track_plan)}곡 / mode={self.track_plan_meta.get('parseMode')} / 장면 {self.track_plan_meta.get('sceneHits',0)}개")

    def recompute_plan(self):
        if not self.track_plan: self.parse_track_plan()
        if not self.selected_market_recipe: self.run_recommendations()
        pid=self.preset_var.get(); master=self.master_text.get('1.0','end').strip()
        self.track_plan, recmeta=recompute_track_plan(self.track_plan,pid,PRESETS[pid],self.selected_market_recipe,master)
        self.track_plan_meta.update(recmeta); self.refresh_learning_analysis(); self.nb.select(self.plan_tab)
        self.plan_status.set(f"재계산 완료: {len(self.track_plan)}곡 / BPM·Genre·Vocal·Role·Structure 갱신 / Story·Scene LOCK 유지")

    def refresh_learning_analysis(self):
        records=list_feedback(self.feedback_db,100000)
        pid=self.preset_var.get() if hasattr(self,'preset_var') else ''
        rid=(self.selected_market_recipe or {}).get('id','')
        self.learning_scope=select_feedback_scope(records,pid,rid)
        self.learning_analysis=analyze_feedback_patterns(self.learning_scope.get('records',[]),min_samples=30,min_group=3)
        self.ab_results=analyze_ab_results(self.learning_scope.get('records',[]),min_per_arm=5,min_per_axis=3)
        context={'presetId':pid,'marketRecipeId':rid,'scope':self.learning_scope.get('scope',''),'feedbackN':self.learning_scope.get('n',0)}
        self.experiment_manifest=build_experiment_manifest(self.track_plan,self.learning_analysis,context,exploration_count=4)
        self.experiment_plan=build_ab_experiment_plan(self.track_plan,self.learning_analysis,exploration_count=4)

        if hasattr(self,'learning_text'):
            payload={
                'scope':self.learning_scope.get('scope'),
                'scopeN':self.learning_scope.get('n',0),
                'totalFeedbackAvailable':self.learning_scope.get('totalAvailable',0),
                'active':self.learning_analysis.get('active',False),
                'confidence':self.learning_analysis.get('confidence'),
                'activationRule':'same preset + same market recipe n>=30',
                'overall':self.learning_analysis.get('overall',{}),
                'topBpmWindows':self.learning_analysis.get('topBpmWindows',[]),
                'topGenres':self.learning_analysis.get('topGenres',[]),
                'topPerformanceAtoms':self.learning_analysis.get('topPerformanceAtoms',[]),
                'topIssues':self.learning_analysis.get('topIssues',{}),
                'abResults':self.ab_results,
                'policy':self.learning_analysis.get('policy',{}),
            }
            self.learning_text.delete('1.0','end'); self.learning_text.insert('1.0',json.dumps(payload,ensure_ascii=False,indent=2))
            for x in self.exp_tree.get_children(): self.exp_tree.delete(x)
            for row in self.experiment_manifest.get('tracks',[]):
                proposal=json.dumps(row.get('proposedChanges',{}),ensure_ascii=False,separators=(',',':'))
                self.exp_tree.insert('', 'end', iid=f"exp-{row.get('trackNo')}", values=(row.get('trackNo'),row.get('arm'),row.get('axis'),str(row.get('title',''))[:32],proposal[:180]))
            n=self.learning_scope.get('n',0); active=self.learning_analysis.get('active',False); conf=self.learning_analysis.get('confidence','insufficient')
            self.learning_status.set(f"{'ACTIVE' if active else 'OBSERVE'} / n={n}/30 / confidence={conf}")
        if hasattr(self,'plan_tree'): self.render_track_plan()

    def save_experiment_manifest(self):
        self.refresh_learning_analysis()
        p=filedialog.asksaveasfilename(defaultextension='.json',initialfile='experiment_manifest_v05.json',filetypes=[('JSON','*.json')])
        if p:
            write_json(p,self.experiment_manifest)
            messagebox.showinfo('저장',f'Experiment Manifest 저장 완료\n{p}')

    def render_track_plan(self):
        for x in self.plan_tree.get_children(): self.plan_tree.delete(x)
        exp_map={int(r.get('trackNo',0)):r.get('experiment',{}) for r in self.experiment_plan}
        for r in self.track_plan:
            t=r['trusted']; old=r['importedMusic']; new=r['recomputed']; locks=r['locks']; exp=exp_map.get(int(r.get('trackNo',0)),{})
            lock='🔒' if locks.get('story') and locks.get('scene') else '⚠'
            scene=t.get('listenerSituation') or t.get('scene') or ''
            self.plan_tree.insert('', 'end', iid=str(r['trackNo']), values=(r['trackNo'],lock,exp.get('arm','A'),exp.get('axis','baseline'),t.get('title',''),t.get('storyActLabel') or t.get('storyAct',''),scene[:90],old.get('BPM') or '',new.get('BPM') or '',old.get('genre','')[:45],new.get('genre','')[:55],new.get('musicRole',''),new.get('structure','')[:95]))
        if self.track_plan:
            first=str(self.track_plan[0]['trackNo']); self.plan_tree.selection_set(first); self.plan_tree.focus(first); self.plan_selected()
        else:
            self.plan_detail.delete('1.0','end'); self.plan_status.set('아직 Track Plan이 없습니다.')

    def plan_selected(self,event=None):
        sel=self.plan_tree.selection()
        if not sel: return
        no=int(sel[0]); self.selected_track_no=no; r=next((x for x in self.track_plan if x['trackNo']==no),None)
        if not r: return
        l=r['locks']; self.story_lock.set(l.get('story',True)); self.scene_lock.set(l.get('scene',True)); self.title_lock.set(l.get('title',True)); self.hook_lock.set(l.get('hook',True))
        ov=r.get('manualOverrides',{}); self.override_bpm.set(str(ov.get('BPM',''))); self.override_role.set(str(ov.get('musicRole',''))); self.override_genre.set(str(ov.get('genre','')))
        self.plan_detail.delete('1.0','end'); self.plan_detail.insert('1.0',json.dumps(r,ensure_ascii=False,indent=2))

    def apply_track_override(self):
        if self.selected_track_no is None: return
        r=next((x for x in self.track_plan if x['trackNo']==self.selected_track_no),None)
        if not r: return
        r['locks']={'story':bool(self.story_lock.get()),'scene':bool(self.scene_lock.get()),'title':bool(self.title_lock.get()),'hook':bool(self.hook_lock.get())}
        ov=r.setdefault('manualOverrides',{})
        bpm=self.override_bpm.get().strip()
        if bpm:
            try: ov['BPM']=int(bpm)
            except ValueError: messagebox.showerror('오류','BPM은 숫자로 입력하세요.'); return
        else: ov.pop('BPM',None)
        role=self.override_role.get().strip(); genre=self.override_genre.get().strip()
        if role: ov['musicRole']=role
        else: ov.pop('musicRole',None)
        if genre: ov['genre']=genre
        else: ov.pop('genre',None)
        self.recompute_plan()

    def set_all_locks(self, value: bool):
        for r in self.track_plan:
            r['locks']['story']=value; r['locks']['scene']=value
        self.render_track_plan()

    def save_track_plan(self):
        if not self.track_plan: self.parse_track_plan(); self.recompute_plan()
        p=filedialog.asksaveasfilename(defaultextension='.json',initialfile='structured_track_plan.json',filetypes=[('JSON','*.json')])
        if p: write_json(p,{'meta':self.track_plan_meta,'tracks':self.track_plan})

    def compile(self):
        if not self.selected_market_recipe: self.run_recommendations()
        if not self.track_plan and self.directive.get('1.0','end').strip(): self.parse_track_plan()
        if self.track_plan: self.recompute_plan()
        raw=self.directive.get('1.0','end').strip(); master=self.master_text.get('1.0','end').strip(); ep=self.episode.get().strip(); ref=self.reference.get('1.0','end').strip(); pid=self.preset_var.get(); rid=self.recipe_var.get()
        feedback_insights=build_feedback_insights(self.feedback_db,pid,self.selected_market_recipe.get('id',''),min_samples=3)
        self.compiled,self.manifest,self.qa=compile_instruction(raw,pid,PRESETS[pid],RECIPES[rid],PUBLIC,self.model_var.get(),self.mode_var.get(),master,ep,self.selected_market_recipe,self.market_var.get(),self.goal_var.get(),ref,self.ownership_var.get(),int(self.song_count.get()),self.output_mode.get(),self.track_plan,self.track_plan_meta,feedback_insights)
        self.refresh_learning_analysis()
        self.output.delete('1.0','end'); self.output.insert('1.0',self.compiled); self.render_qa(); self.nb.select(self.output_tab); messagebox.showinfo('완료',f"{len(self.track_plan) if self.track_plan else 0}곡 구조화 Track Plan을 포함한 최종 지시문을 생성했습니다.")

    def feedback_from_plan(self):
        if not self.track_plan:
            self.parse_track_plan()
        self.refresh_learning_analysis()
        exp_map={int(r.get('trackNo',0)):r.get('experiment',{}) for r in self.experiment_plan}
        self.feedback_tracks=[]; self.feedback_track_map={}
        for r in self.track_plan:
            t=r.get('trusted',{}); new=r.get('recomputed',{}); old=r.get('importedMusic',{}); exp=exp_map.get(int(r.get('trackNo',0)),{})
            d={'trackNo':r.get('trackNo'), 'title':t.get('title',''), 'BPM':new.get('BPM') or old.get('BPM'), 'genre':new.get('genre') or old.get('genre',''), 'vocal':new.get('vocal') or old.get('vocal',''), 'trackRole':new.get('musicRole',''), 'performanceSignature':new.get('performanceSignature',''), 'stylePrompt':'', 'experimentArm':exp.get('arm','A'), 'experimentAxis':exp.get('axis','baseline'), 'experimentContext':exp.get('proposedChanges',{})}
            self.feedback_tracks.append(d)
        self._feedback_populate_tracks()
        self.nb.select(self.feedback_tab)

    def feedback_load_result(self):
        p=filedialog.askopenfilename(filetypes=[('JSON','*.json'),('Text','*.txt'),('All','*.*')])
        if not p: return
        try:
            obj=json.loads(read_text(p))
        except Exception as e:
            messagebox.showerror('오류',f'JSON을 읽지 못했습니다.\n{e}'); return
        songs=obj.get('songs') if isinstance(obj,dict) else obj
        if not isinstance(songs,list): messagebox.showerror('오류','songs 배열을 찾지 못했습니다.'); return
        self.refresh_learning_analysis()
        exp_map={int(r.get('trackNo',0)):r.get('experiment',{}) for r in self.experiment_plan}
        self.feedback_tracks=[]; self.feedback_track_map={}
        for i,x in enumerate(songs,1):
            if not isinstance(x,dict): continue
            no=int(x.get('trackNo',i) or i); exp=exp_map.get(no,{})
            self.feedback_tracks.append({'trackNo':no,'title':x.get('title',''),'BPM':x.get('BPM',x.get('bpm')),'genre':x.get('genre',x.get('genreText','')),'vocal':x.get('vocalType',x.get('vocalDesign','')),'trackRole':x.get('trackRole',''),'performanceSignature':x.get('performanceSignature',''),'stylePrompt':x.get('stylePrompt',''),'experimentArm':x.get('experimentArm',exp.get('arm','A')),'experimentAxis':x.get('experimentAxis',exp.get('axis','baseline')),'experimentContext':x.get('experimentContext',exp.get('proposedChanges',{}))})
        self._feedback_populate_tracks(); self.nb.select(self.feedback_tab)

    def _feedback_populate_tracks(self):
        vals=[]; self.feedback_track_map={}
        for x in self.feedback_tracks:
            key=f"{int(x.get('trackNo') or 0):02d} | {x.get('title','(untitled)')}"
            vals.append(key); self.feedback_track_map[key]=x
        self.fb_track_cb['values']=vals
        if vals: self.fb_track_var.set(vals[0]); self.feedback_track_selected()

    def feedback_track_selected(self):
        # Keep rating inputs as the user set them; only track context changes.
        if not self.fb_session.get().strip():
            import datetime as _dt
            self.fb_session.set(_dt.datetime.now().strftime('%Y%m%d_%H%M'))

    def save_feedback(self):
        key=self.fb_track_var.get(); tr=self.feedback_track_map.get(key)
        if not tr: messagebox.showwarning('선택 필요','먼저 현재 Track Plan 또는 생성결과 JSON에서 트랙을 가져오세요.'); return
        runtime=self.fb_runtime.get().strip()
        try: runtime_val=float(runtime) if runtime else None
        except ValueError: messagebox.showerror('오류','Runtime은 초 단위 숫자로 입력하세요.'); return
        issues=[k for k,v in self.fb_tag_vars.items() if v.get()]
        mr=self.selected_market_recipe or {}
        rec={'session_id':self.fb_session.get().strip(),'market':self.market_var.get(),'goal':self.goal_var.get(),'preset_id':self.preset_var.get(),'market_recipe_id':mr.get('id',''),'market_recipe_label':mr.get('label',''),'model':self.model_var.get(),'episode':self.episode.get().strip(),'track_no':tr.get('trackNo'),'title':tr.get('title',''),'music_role':tr.get('trackRole',''),'bpm':tr.get('BPM') or 0,'genre':tr.get('genre',''),'vocal':tr.get('vocal',''),'performance_signature':tr.get('performanceSignature',''),'style_prompt':tr.get('stylePrompt',''),'decision':self.fb_decision.get(),'overall':self.fb_overall.get(),'vocal_identity':self.fb_vocal.get(),'hook':self.fb_hook.get(),'groove':self.fb_groove.get(),'prompt_adherence':self.fb_adherence.get(),'runtime_sec':runtime_val,'issue_tags':issues,'notes':self.fb_notes.get().strip(),'experiment_arm':tr.get('experimentArm',''),'experiment_axis':tr.get('experimentAxis',''),'experiment_context':tr.get('experimentContext',{})}
        row_id=add_feedback(self.feedback_db,rec)
        self.refresh_feedback_view(); self.run_recommendations()
        messagebox.showinfo('저장',f"Feedback #{row_id} 저장 완료. A/B={tr.get('experimentArm','-')} / axis={tr.get('experimentAxis','-')}. 레시피 가이드는 n>=3, v0.5 A/B 분석은 같은 preset+recipe n>=30에서 활성화됩니다.")

    def refresh_feedback_view(self):
        if not hasattr(self,'fb_tree'): return
        for x in self.fb_tree.get_children(): self.fb_tree.delete(x)
        rows=list_feedback(self.feedback_db,300)
        for r in rows:
            self.fb_tree.insert('', 'end', iid=str(r['id']), values=(r['id'],str(r['created_at'])[:16],r['decision'],r.get('experiment_arm',''),r.get('experiment_axis',''),r['track_no'],r['title'][:30],(r['market_recipe_label'] or r['market_recipe_id'])[:32],r['music_role'],r['bpm'],r['overall'],r['vocal_identity'],r['hook'],r['groove'],r['prompt_adherence']))
        agg=aggregate_feedback(self.feedback_db)
        recipe_rows=[]
        for rid,st in sorted(agg.get('byRecipe',{}).items(), key=lambda kv:(kv[1].get('feedbackScore',0),kv[1].get('n',0)), reverse=True):
            recipe_rows.append({'recipe':rid,**st})
        summary={'db':str(self.feedback_db),'totalEvaluations':agg.get('total',0),'recipeRanking':recipe_rows,'experimentArms':agg.get('byExperimentArm',{}),'experimentAxes':agg.get('byExperimentAxis',{}),'recurringIssues':agg.get('issueCounts',{}),'activationRule':'recipe/preset local guidance starts at n>=3; v0.5 A/B descriptive analysis requires both arms >=5 within same preset+recipe scope'}
        self.fb_summary.delete('1.0','end'); self.fb_summary.insert('1.0',json.dumps(summary,ensure_ascii=False,indent=2))
        if hasattr(self,'learning_text'): self.refresh_learning_analysis()

    def feedback_record_selected(self,event=None):
        sel=self.fb_tree.selection(); self.feedback_selected_id=int(sel[0]) if sel else None

    def delete_feedback_ui(self):
        if not self.feedback_selected_id: return
        if messagebox.askyesno('삭제',f'Feedback #{self.feedback_selected_id}를 삭제할까요?'):
            delete_feedback(self.feedback_db,self.feedback_selected_id); self.feedback_selected_id=None; self.refresh_feedback_view(); self.run_recommendations()

    def export_feedback_json_ui(self):
        p=filedialog.asksaveasfilename(defaultextension='.json',initialfile='suno_feedback_backup.json',filetypes=[('JSON','*.json')])
        if p: export_feedback_json(self.feedback_db,p); messagebox.showinfo('완료',f'백업 완료\n{p}')

    def export_feedback_csv_ui(self):
        p=filedialog.asksaveasfilename(defaultextension='.csv',initialfile='suno_feedback.csv',filetypes=[('CSV','*.csv')])
        if p: export_feedback_csv(self.feedback_db,p); messagebox.showinfo('완료',f'내보내기 완료\n{p}')

    def render_qa(self):
        self.qa_text.delete('1.0','end')
        if not self.manifest:
            q=validate_track_plan(self.track_plan,int(self.song_count.get())) if self.track_plan else []
            self.qa_text.insert('1.0','\n'.join(f"{x['level']:>4}  {x['code']}: {x['message']}" for x in q) if q else '아직 컴파일하지 않았습니다.'); return
        summary={k:v for k,v in self.manifest.items() if k not in ('referenceDNA','qa','structuredTrackPlan')}
        lines=['[COMPILE MANIFEST]',json.dumps(summary,ensure_ascii=False,indent=2),'','[STRUCTURED TRACK PLAN]',json.dumps(self.manifest.get('structuredTrackPlan',[]),ensure_ascii=False,indent=2),'','[REFERENCE DNA]',json.dumps(self.manifest.get('referenceDNA',{}),ensure_ascii=False,indent=2),'','[QA]']
        for q in self.qa: lines.append(f"{q['level']:>4}  {q['code']}: {q['message']}")
        self.qa_text.insert('1.0','\n'.join(lines))

    def copy_output(self):
        text=self.output.get('1.0','end').strip()
        if text: self.clipboard_clear(); self.clipboard_append(text); self.update(); messagebox.showinfo('복사','최종 지시문을 복사했습니다.')
    def save_instruction(self):
        if not self.compiled: self.compile()
        p=filedialog.asksaveasfilename(defaultextension='.txt',initialfile='compiled_structured_chatgpt_instruction.txt')
        if p: write_text(p,self.compiled)
    def save_package(self):
        if not self.compiled: self.compile()
        d=filedialog.askdirectory(title='패키지 저장 폴더 선택')
        if not d: return
        self.refresh_learning_analysis()
        rid=self.selected_market_recipe.get('id','market'); base=Path(d)/f"suno_v05_package_{rid}"; base.mkdir(parents=True,exist_ok=True)
        write_text(base/'compiled_chatgpt_instruction.txt',self.compiled); write_json(base/'compile_manifest.json',self.manifest); write_json(base/'structured_track_plan.json',{'meta':self.track_plan_meta,'tracks':self.track_plan}); write_json(base/'selected_market_recipe.json',self.selected_market_recipe); write_json(base/'selected_channel_preset.json',PRESETS[self.preset_var.get()]); write_json(base/'reference_dna.json',self.manifest.get('referenceDNA',{})); write_json(base/'feedback_insights.json',self.manifest.get('performanceInsights',{})); write_json(base/'learning_analysis_v05.json',self.learning_analysis); write_json(base/'ab_results_v05.json',self.ab_results); write_json(base/'experiment_manifest_v05.json',self.experiment_manifest); messagebox.showinfo('저장',f'저장 완료\n{base}')
    def validate_result_file(self):
        p=filedialog.askopenfilename(filetypes=[('JSON','*.json'),('Text','*.txt'),('All','*.*')])
        if not p: return
        issues=validate_generated_json(read_text(p),PRESETS[self.preset_var.get()]); self.qa_text.delete('1.0','end'); self.qa_text.insert('1.0','\n'.join(f"{x['level']:>4}  {x['code']}: {x['message']}" for x in issues))

def cli(args):
    raw=read_text(args.directive) if args.directive else ''; master=read_text(args.master) if args.master else ''; ref=read_text(args.reference) if args.reference else ''
    rows=recommend(MARKET,args.market,args.goal,args.vocal,args.language,top_n=20); mr=next((r for r in rows if r['id']==args.market_recipe), rows[0] if rows else {})
    plan=[]; pmeta={}
    if raw and not args.no_track_plan:
        plan,pmeta=extract_track_plan(raw,args.song_count); plan,rmeta=recompute_track_plan(plan,args.preset,PRESETS[args.preset],mr,master); pmeta.update(rmeta)
    feedback_db=Path(args.feedback_db) if args.feedback_db else ROOT/'user_data'/'feedback.sqlite3'
    init_feedback_db(feedback_db)
    insights={} if args.no_feedback_learning else build_feedback_insights(feedback_db,args.preset,mr.get('id',''),min_samples=3)
    inst,manifest,qa=compile_instruction(raw,args.preset,PRESETS[args.preset],RECIPES[args.recipe],PUBLIC,args.model,args.mode,master,args.episode or '',mr,args.market,args.goal,ref,args.ownership,args.song_count,args.output_mode,plan,pmeta,insights)
    if args.track_plan_out: write_json(args.track_plan_out,{'meta':pmeta,'tracks':plan})
    if args.out: write_text(args.out,inst); write_json(str(Path(args.out).with_suffix('.manifest.json')),manifest)
    else: print(inst)
    return 0

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--directive'); ap.add_argument('--master'); ap.add_argument('--reference'); ap.add_argument('--preset',default='market_auto',choices=PRESETS.keys()); ap.add_argument('--recipe',default='auto',choices=RECIPES.keys()); ap.add_argument('--market',default='JP',choices=['KR','JP','GLOBAL','ANY']); ap.add_argument('--goal',default='revenue_balance',choices=MARKET['useCases'].keys()); ap.add_argument('--vocal',default='any',choices=['any','vocal','instrumental']); ap.add_argument('--language',default='any'); ap.add_argument('--market-recipe',default=''); ap.add_argument('--ownership',default='external',choices=['external','user_owned']); ap.add_argument('--song-count',type=int,default=15); ap.add_argument('--output-mode',default='full_pack',choices=['full_pack','lyrics_plus_prompt','prompt_only']); ap.add_argument('--model',default='v6',choices=['v6','v6-wild','v6-mini']); ap.add_argument('--mode',default='HYBRID',choices=['HYBRID','MASTER_FIRST','PRESERVE']); ap.add_argument('--episode',default=''); ap.add_argument('--out'); ap.add_argument('--track-plan-out'); ap.add_argument('--no-track-plan',action='store_true'); ap.add_argument('--feedback-db'); ap.add_argument('--no-feedback-learning',action='store_true'); ap.add_argument('--cli',action='store_true'); ap.add_argument('--startup-check',action='store_true')
    args=ap.parse_args()
    if args.cli or args.directive or args.out or args.reference: raise SystemExit(cli(args))
    if args.startup_check:
        print('[STARTUP-CHECK] imports/data OK', flush=True)
        app=App()
        print('[STARTUP-CHECK] App() returned', flush=True)
        app.update_idletasks()
        print('[STARTUP-CHECK] Tk App constructed OK', flush=True)
        app.destroy()
        raise SystemExit(0)
    print('[STARTUP] launching GUI...', flush=True)
    App().mainloop()
