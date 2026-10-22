# 지하철 승하차 대시보드 (부산 | 서울) · 휴대폰용

페이지 주소: **https://evan9852-star.github.io/subway-dashboard/**

- **부산**: `부산데이터` 폴더의 부산교통공사 시간대별 승하차 CSV
- **서울**: 서울 실시간 도시데이터 (`서울장소.txt` 의 장소들)
- 서울 자료는 **휴대폰 단축어 버튼**을 누를 때, 그리고 1시간마다(06~24시) 새로 받습니다.
- 페이지는 열려 있는 동안 1분마다 새 자료가 있는지 확인합니다.

Mac에서 쓰던 `지하철_대시보드_열기.command` / `live.py` 는 그대로 쓰면 됩니다.

## 처음 한 번만 할 일

1. **서울 인증키 넣기**: 저장소 Settings → Secrets and variables → Actions → New repository secret
   - Name: `SEOUL_KEY`
   - Secret: Mac 폴더 `서울키.txt` 안의 글자 그대로
2. **페이지 켜기**: Settings → Pages → Build and deployment → Source 를 **GitHub Actions** 로
3. **첫 실행**: Actions 탭 → 대시보드 갱신 → Run workflow (1~2분 뒤 위 주소가 열립니다)

## 버튼용 GitHub 토큰 만들기

GitHub → 오른쪽 위 프로필 → Settings → Developer settings → Personal access tokens →
**Fine-grained tokens** → Generate new token

- Repository access: **Only select repositories** → `subway-dashboard`
- Permissions → Repository permissions → **Actions: Read and write** (다른 건 손대지 않기)
- 만들어진 `github_pat_...` 글자를 복사해 둡니다 (다시 볼 수 없음)

이 토큰은 이 저장소의 작업 실행만 할 수 있습니다. 단축어 안에만 넣고 다른 곳에 올리지 마세요.

## 아이폰: 단축어

단축어 앱 → + → 아래 동작을 순서대로 추가

1. **URL** : `https://api.github.com/repos/evan9852-star/subway-dashboard/actions/workflows/update.yml/dispatches`
2. **URL 내용 가져오기**
   - 방법: `POST`
   - 헤더: `Authorization` = `Bearer github_pat_...(토큰)` / `Accept` = `application/vnd.github+json`
   - 요청 본문: `JSON` → 키 `ref`, 텍스트 `main`
3. **URL** : `https://evan9852-star.github.io/subway-dashboard/#seoul`
4. **URL 열기**

이름을 '지하철 대시보드'로 하고, 공유 버튼 → 홈 화면에 추가.
누르면 페이지가 바로 열리고, 1~2분 뒤 새 서울 자료로 저절로 바뀝니다.

## 안드로이드: HTTP Shortcuts 앱

Play 스토어에서 **HTTP Shortcuts** 설치 → + → Regular Shortcut

- Basic Request Settings: Method `POST`,
  URL `https://api.github.com/repos/evan9852-star/subway-dashboard/actions/workflows/update.yml/dispatches`
- Request Headers: `Authorization` = `Bearer github_pat_...(토큰)` / `Accept` = `application/vnd.github+json`
- Request Body / Parameters: Body Type `Custom Text`, Content Type `application/json`, 내용 `{"ref":"main"}`
- Response Handling: 성공 시 화면 표시 안 함(또는 Toast)
- Scripting → Run after success: `openUrl("https://evan9852-star.github.io/subway-dashboard/#seoul");`

저장 후 단축어를 길게 눌러 **Place on home screen** (또는 위젯 추가).

## 자료 바꾸기

- **부산 새 달 CSV**: 공공데이터포털에서 받아 이 저장소 `부산데이터` 폴더에 Add file → Upload files. 1~2분 뒤 반영
- **서울 장소**: `서울장소.txt` 를 고칩니다 (연필 아이콘 → Commit). 서울시 주요 장소 이름 그대로
- 자동 갱신 시간을 바꾸려면 `.github/workflows/update.yml` 의 `cron` 줄을 고치거나 지웁니다.

## 공개 범위

이 저장소와 페이지는 누구나 볼 수 있습니다. 서울 인증키(`SEOUL_KEY`)와 버튼용 토큰은 공개되지 않습니다.
`서울키.txt` 파일은 이 저장소에 올리지 마세요.
