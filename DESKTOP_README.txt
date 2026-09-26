Suno Master Prompt Studio v0.5.2 - Windows Desktop

[실행]
1. ZIP 파일을 원하는 폴더에 압축 해제합니다.
2. SunoMasterPromptStudio_v0.5.2.exe 를 실행합니다.
3. 기본 화면은 실제 제작용 Simple Workflow입니다.
4. 처음 실행할 때 Windows SmartScreen 경고가 나오면 파일 출처를 확인한 뒤 실행 여부를 결정하세요.

[데이터 보관]
- 등록한 최신 마스터 경로와 사용자 설정은 EXE 폴더의 user_data에 저장됩니다.
- 프로그램을 새 버전으로 교체할 때 user_data 폴더를 새 버전 폴더로 복사하면 설정을 이어서 사용할 수 있습니다.
- feedback.sqlite3를 사용하는 고급 UI 데이터도 백업을 권장합니다.

[기본 작업]
A. 기존 JSON 업그레이드
- 원본 JSON 불러오기
- 최신 채널 마스터 선택/등록
- 장르 선택
- 현재 프롬프트 분석
- AI 음악 프롬프트 업그레이드 지시문 생성
- ChatGPT/Codex 결과 JSON 불러오기
- QA PASS 확인 후 최종 JSON 저장

B. Haru Studio TXT 신규 제작
- Haru Studio TXT 불러오기
- 채널/보컬 타입 + 장르 선택
- 최신 마스터 선택/등록
- 신규 제작 지시문 생성
- 결과 JSON 불러오기
- QA PASS 확인 후 저장

[v0.5.2 핵심 QA]
Chill Rap 보컬곡은 다음이 실제 stylePrompt에 직접 있어야 PASS합니다.
- Hook money chord progression(s)
- Bridge money chord/harmonic progression(s)
- Bridge audible contrast: 일반곡 2축 이상 / Anchor 3축 이상
- Final Highlight: 일반곡 A+B / Anchor A+B+C 또는 동등한 post-hook
- Final full-pocket/groove return
- root-bass 또는 cadence motion
- Final resolution progression(s)

머니코드는 1개로 제한하지 않습니다.
한 섹션에 하나 또는 복수 progression을 사용할 수 있습니다.

[개발/업데이트]
앞으로 코드 수정은 CODEX_UPGRADE_TEMPLATE.md의 지시문을 Codex에 붙여넣어 진행하는 것을 권장합니다.
업데이트 완료 조건은 pytest + compileall + git diff --check + Windows Desktop Build PASS입니다.
