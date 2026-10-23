# 인수인계: 지하철 대시보드 (부산 | 서울)

이 문서를 새 Claude 세션(맥에서 실행되는 세션)에 그대로 붙여 넣으면 이어서 작업할 수 있다.

## 나에 대해
- 개발자가 아니다. **한국어, 쉬운 말**로 설명해 줘. 전문 용어는 풀어서.
- 답변·화면 문구에서 "~해 주세요", "손쉽게" 같은 AI 말투는 빼 줘.
- **main 브랜치에 올리는 것(= 공개 사이트 배포)은 내가 "main 반영"이라고 할 때만.** 그 전에는 다른 브랜치에 올리고 화면을 보여 줘.
- 디자인을 바꿀 때는 후보를 **실제 화면으로 찍어서 나란히** 보여 주고 고르게 해 줘.

## 이 프로젝트
- GitHub: `evan9852-star/subway-dashboard` (공개 저장소)
- 사이트: https://evan9852-star.github.io/subway-dashboard/ (휴대폰용, GitHub Pages)
- 맥 프로그램: 맥 폴더의 `지하철_대시보드_열기.command` → `live.py`가 http://localhost:8765 를 띄운다.

### 파일
| 파일 | 역할 |
|---|---|
| `index.html` | 화면(웹·맥 공통) |
| `live.py` | 맥 프로그램. `index.html`이 있으면 새 화면, 없으면 예전 `page.html`. 부산 합산(`busan()`), 서울 실시간(`fetch_place`) 코드도 여기 있다 |
| `build.py` | GitHub Actions에서 실행. `_site/`에 `index.html`, `fonts/`, `busan.json`(부산 CSV 합산), `seoul.json`(서울 실시간) 생성 |
| `.github/workflows/update.yml` | 단축어 버튼(workflow_dispatch) · main push · 매시 7분(한국시간 06~24시) 실행 → Pages 배포 |
| `부산데이터/*.csv` | 부산교통공사 시간대별 승하차 CSV (UTF-8, 1월~그달 누적 파일) |
| `서울장소.txt` | 서울에서 볼 장소 이름 (서울시 주요 장소 120곳 공식 이름) |
| `fonts/` | `kopub-dotum-medium/bold.woff2`(본문), `suit-extrabold.woff2`(제목·큰 숫자), 라이선스 |
| `docs/skills/clean-ui/SKILL.md` | 내가 다른 작업에도 쓰는 디자인 규칙 |

### 비밀값 (파일에 쓰거나 출력하지 말 것)
- 서울 인증키: 웹은 GitHub Secrets `SEOUL_KEY`, 맥은 폴더의 `서울키.txt` (저장소에 올리지 않음)
- 단축어용 GitHub 토큰: 휴대폰 단축어 안에만 있음

## 지금까지 한 일 (모두 main에 반영·배포됨)
1. 코드 리뷰 → 문구 정리, 그래프를 실제 화면 폭으로 그려 휴대폰 글자 크기 확보, 터치로 수치 표시
2. Uber DESIGN.md 기반 디자인: 흑백 바탕, 회색 패널(모서리 16px), 알약 버튼, 색은 데이터에만
3. 머리띠를 검은 역 안내판 모양 + 노선색 띠(부산 1호선 주황 `#f06a00`, 서울 2호선 초록 `#00a84d`)
4. 카드 강약: 후보 역 중 순위가 가장 높은 역 / 서울에서 가장 붐비는 장소를 전체 폭으로 크게
5. 폰트: 본문 KoPubWorld 돋움, 제목·큰 숫자 **SUIT ExtraBold** (Black Han Sans는 너무 무겁고 KoPub Bold는 얇아서 교체). 자주 쓰는 한글 2,350자만 남긴 웹폰트
6. 부산 자료를 `build.py`/`live.py`에서 미리 합산 → 휴대폰이 CSV 6.8MB 대신 약 0.5MB만 받음(로딩 약 4초 → 0.25초). 같은 날짜가 겹치면 파일 이름 순으로 나중 파일 값
7. 접근성: 대비 3:1·4.5:1, 누르는 영역 44px, 선 그래프 선 무늬, 혼잡도 글 요약, 간격 4의 배수
8. 맥 프로그램도 새 화면을 띄우도록 `live.py` 수정

## 지금 맥에서 할 일 (이 세션에 부탁할 것)
1. 맥의 대시보드 폴더(`지하철_대시보드_열기.command`가 있는 곳)에 GitHub main의 최신 파일을 덮어쓰기
   - `live.py`, `index.html`, `fonts/` 폴더(통째로)
   - **건드리지 말 것**: `서울키.txt`, `부산데이터/`, `page.html`
   - 예: `curl -fsSL https://github.com/evan9852-star/subway-dashboard/archive/refs/heads/main.tar.gz | tar xz --strip-components=1 subway-dashboard-main/live.py subway-dashboard-main/index.html subway-dashboard-main/fonts`
   - `fonts/blackhansans.woff2`가 남아 있으면 지워도 됨(이제 안 씀)
2. 켜져 있던 대시보드를 끄고(`live.py` 종료) `지하철_대시보드_열기.command`로 다시 열기
3. http://localhost:8765 에서 부산·서울 탭이 새 디자인으로 나오는지, 서울 자료가 받아지는지 확인하고 화면을 보여 줘
4. (선택) `docs/skills/clean-ui/SKILL.md`를 `~/.claude/skills/clean-ui/SKILL.md`에 복사해 두면 다른 프로젝트에서도 자동으로 참고

## 남은 일 (아직 안 함, 우선순위 순)
1. **GitHub Actions 버전 올리기**: Node 20 지원 종료 경고가 나온다(지금은 Node 24로 강제 실행되어 동작은 함). `update.yml`에서 checkout·configure-pages·upload-pages-artifact·deploy-pages를 최신 주 버전으로 올리고, `setup-python`은 빼도 된다(파이썬 기본 기능만 사용). 바꾸기 전에 각 액션의 최신 버전을 확인할 것.
2. **서울 자료 시각에 날짜 표시**: 지금은 "21:30 기준"처럼 시각만 나와서, 자동 갱신이 멈추면 며칠 전 자료가 오늘 것처럼 보인다. 날짜를 같이 보이거나 2시간 넘게 지나면 "오래된 자료" 표시.
3. **서울 API가 잠깐 고장 나면** 정상 자료를 오류 카드로 덮어쓴다. 직전 정상 자료를 유지하는 방법 검토.
4. **예약 실행 60일 규칙**: 공개 저장소에 60일 동안 커밋이 없으면 매시 자동 갱신이 꺼진다. 매달 CSV를 올리면 괜찮다.
5. 단축어 토큰 만료일 확인(1년 이내 권장).

## 확인 방법
- 화면을 바꾸면 휴대폰 폭(360·375px)과 PC 폭(1100px), 밝은/어두운 모드에서 찍어 보고 가로 넘침이 없는지 확인
- 부산 숫자 검증용: 목·금, 10~20시, 승차+하차 기준 연산 40,875 / 부산역 37,113 / 서면 101,150 (2026-01~08 CSV)
