# GitHub + Codex 운영 가이드

## 언제 GitHub에 올리나?
**v0.4부터** 권장합니다. 이유는 이제 핵심 아키텍처(Track Plan Lock, Master recompute, Feedback DB)가 잡혔고, 이후 작업은 기능 단위 개선/테스트/버그수정 비중이 커지기 때문입니다.

## 첫 업로드
1. 이 폴더를 새 GitHub 저장소의 루트로 사용합니다.
2. `user_data/feedback.sqlite3`는 업로드하지 않습니다. `.gitignore`에 이미 제외되어 있습니다.
3. 첫 커밋 메시지 예: `Initial v0.4 closed-loop prompt studio`
4. GitHub Actions의 `tests`가 통과하는지 확인합니다.

## Codex를 쓰기 좋은 시점
- GitHub 첫 커밋 직후부터.
- 한 번에 한 기능씩: 예) “15곡 Feedback 일괄입력 UI 추가”, “Track Plan parser edge case 테스트 추가”.
- 버그가 재현될 때: 에러 메시지 + 재현파일 + 기대동작을 Issue/작업지시로 줍니다.
- 코드가 여러 파일에 걸쳐 바뀌지만 요구사항이 명확할 때.

## ChatGPT에서 계속 하는 것이 좋은 일
- 새 채널/장르의 음악 전략 설계
- 마스터 프롬프트의 발성/음악적 판단
- 시장조사와 레시피 정의
- Story/POV/관계 경계 설계
- Feedback 점수 체계 자체를 바꿀지 결정하는 고수준 설계

## Codex에 바로 맡기지 말아야 할 변경
- Story/Scene LOCK 의미 변경
- Feedback 최소표본 3개 규칙 변경
- 점수 가중치 대폭 변경
- 외부 자료 복사/저작권 정책 변경
- Compiler priority stack 변경

이런 변경은 먼저 ChatGPT에서 설계를 확정한 다음 Codex에 구현을 맡기는 것이 안전합니다.

## 권장 Codex 요청 예시
`AGENTS.md와 ARCHITECTURE_v04.md를 먼저 읽어. core/track_plan.py의 JSON+Markdown 혼합 파싱 edge case에 대한 테스트를 추가하고, 기존 Story/Scene Lock semantics는 변경하지 마. python -m pytest -q와 compileall을 실행한 뒤 변경 요약을 알려줘.`
