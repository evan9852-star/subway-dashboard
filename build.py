#!/usr/bin/env python3
"""
GitHub Actions에서 실행: 웹페이지(_site 폴더)를 만든다.

- index.html, fonts(웹폰트)
- busan.json: '부산데이터' CSV들을 "월 × 요일 × 역 × 시간" 합계로 미리 줄인 자료
  (휴대폰이 CSV 원본 수 MB를 내려받아 직접 계산하지 않도록)
- seoul.json: '서울장소.txt' 장소들의 지금 서울 실시간 도시데이터 (인증키는 SEOUL_KEY 비밀값)
"""
import csv
import datetime as dt
import io
import json
import os
import re
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


# ---------------- 부산 ----------------
HOUR_RES = [re.compile(r"^t_?(\d{2})(\d{2})$", re.I), re.compile(r"^(\d{1,2})(시|:00)?[-~]"),
            re.compile(r"^(\d{1,2})시"), re.compile(r"^(\d{2})(\d{2})$")]


def hour_of(name):
    s = re.sub(r"\s", "", name).lstrip("﻿")
    for r in HOUR_RES:
        m = r.match(s)
        if m:
            v = int(m.group(1))
            return None if v > 24 else v % 24  # '24시-01시' → 0시 칸
    return None


def find_col(hdr, keys):
    for i, c in enumerate(hdr):
        n = re.sub(r"\s", "", c).lower()
        if any(k in n for k in keys):
            return i
    return -1


def to_num(v):
    try:
        return int(float(str(v).replace(",", "")))
    except ValueError:
        return 0


def read_csv(path):
    """한 파일 → {(날짜, 역): [승차 24칸, 하차 24칸]}. 같은 파일 안 같은 역명(환승역 호선별 행)은 더한다."""
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp949")
    rows = [r for r in csv.reader(io.StringIO(text)) if any(x.strip() for x in r)]
    hi = next((i for i, r in enumerate(rows) if find_col(r, ["역명", "역이름", "sta_nm", "station"]) >= 0), -1)
    if hi < 0:
        raise ValueError("역 이름 열을 찾지 못했습니다")
    hdr = [c.lstrip("﻿").strip() for c in rows[hi]]
    c_st, c_date, c_g = find_col(hdr, ["역명", "역이름", "sta_nm", "station"]), find_col(hdr, ["년월일", "일자", "날짜", "ymd", "date"]), find_col(hdr, ["구분", "gubn"])
    hour_cols = [(i, h) for i, h in ((i, hour_of(c)) for i, c in enumerate(hdr)) if h is not None]
    if c_date < 0 or c_g < 0 or not hour_cols:
        raise ValueError("날짜·구분·시간대 열을 찾지 못했습니다. 열 목록: " + ", ".join(hdr))
    out = {}
    for r in rows[hi + 1:]:
        if len(r) <= max(c_st, c_date, c_g):
            continue
        d = re.sub(r"\D", "", r[c_date])
        st = r[c_st].strip()
        g = r[c_g]
        side = 0 if "승" in g else 1 if "하" in g else None  # '합계' 같은 행은 건너뛴다(두 번 세지 않게)
        if len(d) < 8 or not st or side is None:
            continue
        date = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
        cell = out.setdefault((date, st), [[0] * 24, [0] * 24])
        for i, h in hour_cols:
            if i < len(r):
                cell[side][h] += to_num(r[i])
    if not out:
        raise ValueError("읽을 수 있는 행이 없습니다")
    return out


def busan():
    """CSV들을 파일 이름 순으로 읽어, 같은 날짜·역이 겹치면 나중 파일 값으로 덮어쓴다(더하지 않음)."""
    merged, files = {}, []
    for f in sorted(p for p in live.DATA_DIR.iterdir() if p.is_file() and p.suffix.lower() == ".csv"):
        try:
            one = read_csv(f)
        except Exception as e:  # noqa: BLE001
            files.append({"name": f.name, "error": str(e)})
            print(f"부산 {f.name}: {e}")
            continue
        dates = sorted({d for d, _ in one})
        files.append({"name": f.name, "from": dates[0], "to": dates[-1], "days": len(dates), "stations": len({s for _, s in one})})
        merged.update(one)
    if not merged:
        return {"files": files, "stations": [], "months": [], "days": {}, "data": {}}

    stations = sorted({s for _, s in merged})
    si = {s: i for i, s in enumerate(stations)}
    dates = sorted({d for d, _ in merged})
    months = sorted({d[:7] for d in dates})
    days = {m: [0] * 7 for m in months}
    for d in dates:
        days[d[:7]][dt.date.fromisoformat(d).weekday()] += 1  # 0 = 월요일
    # data[월][요일] = [역0 0시 승차, 역0 0시 하차, 역0 1시 승차, …] (요일에 날짜가 없으면 null)
    data = {m: [None] * 7 for m in months}
    for (d, st), (on, off) in merged.items():
        m, w = d[:7], dt.date.fromisoformat(d).weekday()
        a = data[m][w]
        if a is None:
            a = data[m][w] = [0] * (len(stations) * 48)
        base = si[st] * 48
        for h in range(24):
            a[base + 2 * h] += on[h]
            a[base + 2 * h + 1] += off[h]
    return {"files": files, "from": dates[0], "to": dates[-1], "stations": stations, "months": months, "days": days, "data": data}


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    shutil.copy(live.HERE / "index.html", OUT / "index.html")
    shutil.copytree(live.HERE / "fonts", OUT / "fonts")
    live.DATA_DIR.mkdir(exist_ok=True)

    b = busan()
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
