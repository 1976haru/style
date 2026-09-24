# Market & Prompt Research Notes — 2026-09-23

## 시장 관찰
- 한국: YouTube/YouTube Music의 음악 이용 영향력이 커졌고, 한국 플레이리스트 소비에서 계절형 감성 발라드가 반복적으로 강하게 나타난다.
- 한국 YouTube에는 7080/올드팝 감성, 카페/휴식/드라이브 결합형 오리지널 플레이리스트 채널과 2026 신규 업로드가 계속 존재한다.
- 일본: 作業用BGM/勉強用BGM/睡眠用BGM이라는 **용도 중심 검색 문법**이 매우 중요하다.
- 일본 YouTube에는 Japanese Chill Pop/R&B/Lo-fi/Chill Rap을 作業用BGM·night listening으로 묶는 현재 업로드가 확인된다.
- 일본 플레이리스트 랭킹에는 다시간 수면 피아노/힐링 BGM이 상위 노출되고, 전용 수면 채널도 대규모 누적 조회를 보유한다.
- Cafe Jazz/Bossa, Deep House/Night Drive는 한국·일본 모두 long-session 배경음악 용도로 지속성이 있다.
- City Pop/Retro는 evergreen 성격이 있으나 공급과 경쟁도 높다.
- Showa-inspired original music은 broad mass market보다 nostalgia niche로 취급한다.

## 수익성 점수에 대한 주의
프로그램의 marketScore는 CPM/RPM 예측이 아니다. 실제 수익은 국가, 광고수요, 영상 길이, 시청자 연령, YPP 상태, 저작권/재사용 정책, 세션시간 등에 좌우된다. 점수는 **어디부터 실험할지 정하는 우선순위**다.

## Prompt-engineering 관찰
- Dominant genre와 핵심 보컬/그루브 특성을 앞에 둔다.
- tag soup보다 구조화된 기술적 프롬프트를 선호한다.
- Lyrics / Style / Exclude를 분리한다.
- 커뮤니티 메타태그는 확률적이지 절대명령이 아니다.
- 반복 보컬 정체성이 중요하면 text prompt만이 아니라 Persona/Voice/reference를 병행한다.
- 외부 참조는 구조와 technical prompt atoms만 재사용하고 가사/멜로디를 복사하지 않는다.
