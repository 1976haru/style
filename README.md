> Current development build: **v0.6-dev** — Research-Driven Prompt Engine. See `ARCHITECTURE_v06.md`.

# Suno Master Prompt Studio v0.6 — Research-Driven Prompt Engine

## v0.6 핵심

v0.5의 안전한 분석/검증 흐름은 유지하면서, 외부 연구 지식과 장르 호환성 데이터를 이용해 각 곡에 **A_CONTROL / B_GROOVE / C_CHARACTER** 3개의 실제 Suno stylePrompt 후보를 만듭니다. 어느 후보도 음원을 듣기 전에 승자로 선언하지 않습니다.

- A_CONTROL: 현재 장르/보컬 정체성 최대 보존 + 고밀도 재구성
- B_GROOVE: 보컬/스토리/핵심 화성 고정 + groove/secondary tint만 실험
- C_CHARACTER: 장르/tint/groove 고정 + 곡별 performance habit 강화
- v6 + Variety 0 + Strong Style Influence + Max Mode 권장 recipe
- Inspire는 승인곡 3~5곡, Custom Model은 승인곡 6개 이상부터 고려
- Community GitHub 자료는 실험 가설로만 사용하고 공식 Suno 문서를 우선

UI의 기존 JSON 탭에서 `연구 기반 A/B/C 후보`를 누르면 15곡×3안 후보를 확인할 수 있고, `A 저장 / B 저장 / C 저장`으로 원본의 제목·가사·훅·스토리를 그대로 보존한 실험용 JSON을 각각 저장할 수 있습니다.

## v0.5 기존 JSON workflow

기존 JSON의 버전명(v14/v15/v16 등)을 품질 근거로 사용하지 않고 현재 음악 설계 자체를 분석합니다. Title/Lyrics/Hook/Story/Scene/relationship boundaries는 강제 보존하며 BPM, Genre, Vocal Design, Style Prompt, Exclude, Performance Signature, Groove, Instrumentation, Harmony, Bridge, Final, Duration, Generation Hint를 개선 대상으로 다룹니다.

UI의 `현재 프롬프트 분석`은 곡별 약점과 전체 개선 영역을 보여주고, `AI 음악 프롬프트 업그레이드`는 Channel Master + Genre Master + `data/prompt_intelligence_rules.json`을 결합한 10단계 제작 지시문을 생성합니다. 결과 JSON에는 곡별 기존/new stylePrompt, 변경 이유, 예상 개선점이 포함되며 최종 저장 전에 immutable 필드를 원본으로 강제 복원하고 검증합니다.

## v0.4.2 Stable 검증 상태

- Full E2E harness: 기존 directive/JSON → Track Plan → LOCK → 음악 재계산 → 최종 생성 JSON 검증
- 남성 / 여성 / 두사람 STORY fixture 회귀 테스트
- 2,100줄 상당 legacy appendix HYBRID 비재삽입 테스트
- Story / Scene / Title / Hook LOCK 검증
- BPM / vocal / genre / role / structure / Bridge / Final / Anchor Final 검증
- duplicate title/hook, wrong language/gender, generic vocal, legacy leakage 탐지
- Windows SQLite file-handle 회귀 검증
- Local: **23 tests PASS**, `compileall` PASS, `git diff --check` PASS
- GitHub Actions: **Windows 3.11 / 3.12 + Ubuntu 3.11 / 3.12 모두 PASS**
## v0.4 핵심

기존 v0.3의 **2,000줄 지시문 → 15곡 Track Plan 구조화 → Story/Scene LOCK → 최신 마스터 기반 음악 재계산** 흐름에, 실제 Suno 생성 결과를 다시 학습하는 **Feedback DB**를 추가했습니다.

### 새 기능
- `KEEP / MAYBE / REGEN` 판정
- 전체 / 보컬 고유성 / 훅 / 그루브 / 프롬프트 준수도 1~5점
- `generic_vocal`, `too_rnb`, `rap_weak`, `early_ending` 등 실패 태그
- 곡별 Runtime, 메모 저장
- SQLite 로컬 DB (`user_data/feedback.sqlite3`)
- JSON/CSV 백업
- 동일 Market Recipe 평가가 **3개 이상**일 때부터 실제 결과를 Market Recipe Ranking에 반영
- Feedback 가중치는 표본과 함께 증가하지만 최대 55%로 제한
- 다음 ChatGPT 컴파일 시 성공한 performanceSignature와 반복 실패 태그를 **soft prior**로 자동 삽입
- Story/Scene/Title/Hook LOCK은 Feedback에 의해 변경되지 않음

## 권장 작업순서
1. 시장/장르 선택
2. 기존 지시문 또는 새 brief 입력
3. 15곡 Track Plan 파싱
4. 최신 마스터로 BPM/Genre/Vocal/Structure 재계산
5. ChatGPT 최종지시문 생성
6. Suno 생성
7. `7. Suno 결과 Feedback` 탭에서 각 곡 평가
8. 3개 이상 데이터가 쌓이면 다음 추천/컴파일에 실제 결과가 반영됨

## GitHub / Codex 준비
이 버전부터 저장소로 관리하는 것을 권장합니다. `.gitignore`, `AGENTS.md`, `CODEX_TASKS.md`, GitHub Actions 테스트 워크플로가 포함돼 있습니다. 실제 사용자 Feedback DB는 gitignore 처리되어 GitHub에 올라가지 않습니다.

---

## v0.3 이전 문서


## 목적
기존 Haru Studio/Claude/ChatGPT용 2,000줄 지시문을 그대로 최종 프롬프트에 넣는 대신, 먼저 **15곡 Track Plan으로 구조화**하고 **스토리/장면/제목/훅은 LOCK**, **BPM/장르/보컬/음악 역할/구조/퍼포먼스 시그니처는 최신 마스터 기준으로 재계산**하는 범용 Suno 제작 도구입니다.

## v0.3 핵심 흐름
1. 시장/장르 레시피 선택
2. 필요하면 외부 Reference DNA 입력
3. 기존 2,000줄 지시문 TXT/JSON 불러오기
4. `지시문 → Track Plan 파싱`
5. 15곡 표에서 원본 음악값과 NEW 음악값 비교
6. 현재 최신 마스터 TXT를 불러오기
7. `최신 마스터로 음악 재계산`
8. Story / Scene / Title / Hook은 기본 LOCK 유지
9. 특정 트랙만 BPM / Genre / MusicRole 수동 Override 가능
10. Track Plan이 포함된 ChatGPT 최종지시문 생성
11. 결과 JSON QA 검증

## Track Plan에서 자동 추출하는 것
- trackNo/order
- title / hookPhrase
- storyAct / storyActLabel / storyArcRole
- listenerSituation / scene / emotionArc
- 기존 BPM / Genre / Vocal / Structure / Intro / TrackRole

지원 입력:
- JSON `songs` / `tracks` / `preassignedSongs`
- Markdown `| Track | Genre | BPM | ... |` 표
- `- T1: Act 1 ... title="..." hook="..."` Story Arc Map
- `Track 1: ... / emotional turn: ...` Lyric Scene 블록

## 기본 LOCK
다음은 콘텐츠 원본으로 취급하며 자동 재계산하지 않습니다.
- Story
- Scene / listenerSituation
- Title
- Hook

## 기본 RECOMPUTE
다음만 최신 마스터/시장 레시피로 갱신합니다.
- BPM
- Genre
- Vocal identity / phonation
- MusicRole: Core / Memory / Anchor
- Structure
- performanceSignature

## 최신 마스터 자동 읽기
불러온 마스터 안에 다음 형식이 있으면 우선 사용합니다.
- `Core 92~100`
- `Flagship 96~104`
- `Memory 84~92`
- `[FIXED VOICE FINGERPRINT ...]`
- `[PHRASING FINGERPRINT]`
- `핵심 장르: ...`

즉 프리셋 고정값뿐 아니라 현재 사용 중인 최신 마스터의 BPM 범위와 보컬 지문을 Track Plan에 직접 반영할 수 있습니다.

## 2,000줄 지시문 처리 방식
### HYBRID / MASTER_FIRST
원본 지시문을 ChatGPT 최종 프롬프트 뒤에 다시 통째로 붙이지 않습니다.

대신 다음만 능동 문맥으로 넘깁니다.
- Structured 15-track plan
- POV / episode / concept
- 관계/스토리 경계
- alreadyUsedTitles / Hooks / Scenes 등 사용 이력
- 현재 마스터
- 현재 시장/채널 레시피

오래된 BPM/보컬/장르/구조 규칙은 최종 능동 문맥에서 제외합니다.

### PRESERVE
기존 지시문을 가능한 그대로 유지해야 할 때만 전체 원문을 포함합니다.

## 화면의 Old → New 비교 예
- `74 BPM → 104 BPM`
- `Lo-fi Hip-Hop Study → Chill Rap / lo-fi tint`
- `soft male whisper → current FIXED VOICE FINGERPRINT`
- `T4 → Anchor Final A+B+C + Bridge >=3 axes + 8-bar turnaround`

## Reference DNA
외부 TXT/JSON을 참조할 때 가사 문장을 복사하지 않고 다음만 추출합니다.
- BPM 분포
- 장르/프로덕션 요소
- 보컬 유형
- Section 구조
- StylePrompt 기술 요소
- Exclude 요소

## 실행
Windows:
```text
run_windows.bat
```

Python:
```bash
python main.py
```

CLI 예:
```bash
python main.py --cli \
  --directive old_instruction.txt \
  --master male_master_v15.txt \
  --preset chili_male \
  --market JP \
  --goal vocal_story \
  --out compiled.txt \
  --track-plan-out structured_track_plan.json
```

## 패키지 저장 결과
- `compiled_chatgpt_instruction.txt`
- `compile_manifest.json`
- `structured_track_plan.json`
- `selected_market_recipe.json`
- `selected_channel_preset.json`
- `reference_dna.json`

## QA
v0.3 테스트: 8 tests PASS
- 15-track extraction
- Story/Scene lock
- legacy BPM replacement
- recurring vocal identity replacement
- master BPM override
- master FIXED VOICE FINGERPRINT extraction
- structured plan injection
- HYBRID raw legacy directive non-reinjection

## 주의
시장 점수는 실험 우선순위용이며 수익을 보장하지 않습니다. Suno 출력은 확률적이므로 KEEP/REGEN 결과를 v0.4 Feedback DB에 누적하는 구조로 확장하기 좋습니다.
