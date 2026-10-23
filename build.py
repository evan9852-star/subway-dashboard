#!/usr/bin/env python3
"""
GitHub Actions에서 실행: 웹페이지(_site 폴더)를 만든다.

- index.html, fonts(웹폰트)
- busan.json: '부산데이터' CSV들을 "월 × 요일 × 역 × 시간" 합계로 미리 줄인 자료
  (휴대폰이 CSV 원본 수 MB를 내려받아 직접 계산하지 않도록)
- seoul.json: '서울장소.txt' 장소들의 지금 서울 실시간 도시데이터 (인증키는 SEOUL_KEY 비밀값)
"""
import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor

import live

OUT = live.HERE / "_site"
PLACES_FILE = live.HERE / "서울장소.txt"


def places():
    lines = PLACES_FILE.read_text(encoding="utf-8").splitlines()
    return [s.strip() for s in lines if s.strip() and not s.lstrip().startswith("#")][:20]


def seoul():
    key = os.environ.get("SEOUL_KEY", "").strip()
    if not key:
        return {"needKey": True, "places": []}
    with ThreadPoolExecutor(max_workers=6) as ex:
        return {"needKey": False, "places": list(ex.map(lambda p: live.fetch_place(key, p), places()))}


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    shutil.copy(live.HERE / "index.html", OUT / "index.html")
    shutil.copytree(live.HERE / "fonts", OUT / "fonts")
    live.DATA_DIR.mkdir(exist_ok=True)

    b = live.busan()
    (OUT / "busan.json").write_text(json.dumps(b, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"부산: 파일 {len(b['files'])}개 · 역 {len(b['stations'])}개 · {len(b['months'])}개월")

    data = seoul()
    text = json.dumps(data, ensure_ascii=False)
    key = os.environ.get("SEOUL_KEY", "").strip()
    if key:
        text = text.replace(key, "***")  # 오류 문구에 인증키가 섞여도 공개 페이지에 남지 않게
    (OUT / "seoul.json").write_text(text, encoding="utf-8")
    for p in data["places"]:
        print(f"{p['place']}: {p.get('error') or p.get('level')}")
    if data["needKey"]:
        print("SEOUL_KEY 비밀값이 없어 서울 자료는 비워 둡니다.")


if __name__ == "__main__":
    main()
