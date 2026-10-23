#!/usr/bin/env python3
"""
지하철 승하차 대시보드 (부산 | 서울)

- 부산 페이지: '부산데이터' 폴더의 부산교통공사 시간대별 승하차 CSV
- 서울 페이지: 서울 열린데이터광장 '실시간 도시데이터' API (인증키는 '서울키.txt')

실행: '지하철_대시보드_열기.command' 더블클릭 (또는 python3 live.py)
추가 설치 필요 없음 (파이썬 기본 기능만 사용)
"""
import csv
import datetime as dt
import io
import json
import re
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "부산데이터"
KEY_FILE = HERE / "서울키.txt"
PLACES_FILE = HERE / "서울장소.txt"
DEFAULT_PLACES = ["강남역", "서울역", "홍대입구역(2호선)", "잠실역", "광화문·덕수궁", "명동 관광특구"]
PORT = 8765
SEOUL_TTL = 180  # 서울 자료를 다시 받아오는 간격(초)


# ---------------- 부산 ----------------
def busan_files():
    files = sorted(p for p in DATA_DIR.iterdir() if p.is_file() and p.suffix.lower() == ".csv")
    return [{"name": p.name, "mtime": int(p.stat().st_mtime)} for p in files]


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
    for f in sorted(p for p in DATA_DIR.iterdir() if p.is_file() and p.suffix.lower() == ".csv"):
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


_busan_cache = {}


def busan_cached():
    """CSV가 바뀌지 않았으면 이전 계산 결과를 그대로 쓴다."""
    sig = tuple((f["name"], f["mtime"]) for f in busan_files())
    if _busan_cache.get("sig") != sig:
        _busan_cache.update(sig=sig, data=busan())
    return _busan_cache["data"]


# ---------------- 서울 ----------------
_seoul_cache = {}
_lock = threading.Lock()


def seoul_key():
    try:
        return KEY_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""


def find_key(obj, name):
    if isinstance(obj, dict):
        if name in obj:
            return obj[name]
        for v in obj.values():
            r = find_key(v, name)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_key(v, name)
            if r is not None:
                return r
    return None


def fetch_place(key, place, fresh=False):
    with _lock:
        c = _seoul_cache.get(place)
        if c and not fresh and time.time() - c[0] < SEOUL_TTL:
            return c[1]
    url = f"http://openapi.seoul.go.kr:8088/{key}/json/citydata/1/5/{urllib.parse.quote(place)}"
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            raw = json.loads(r.read().decode("utf-8"))
        city = find_key(raw, "CITYDATA")
        if not city:
            res = find_key(raw, "RESULT") or raw
            msg = (res.get("RESULT.MESSAGE") or res.get("MESSAGE")) if isinstance(res, dict) else None
            out = {"place": place, "error": msg or "이 이름의 장소를 찾지 못했습니다"}
        else:
            live = city.get("LIVE_PPLTN_STTS")
            live = live[0] if isinstance(live, list) and live else (live or {})
            if isinstance(live, dict) and "LIVE_PPLTN_STTS" in live:
                live = live["LIVE_PPLTN_STTS"]
            sub = city.get("SUB_STTS") or []
            if isinstance(sub, dict):
                sub = sub.get("SUB_STTS", [sub])
            out = {
                "place": city.get("AREA_NM", place),
                "level": live.get("AREA_CONGEST_LVL"),
                "message": live.get("AREA_CONGEST_MSG"),
                "min": live.get("AREA_PPLTN_MIN"), "max": live.get("AREA_PPLTN_MAX"),
                "time": live.get("PPLTN_TIME"),
                "forecast": [
                    {"time": f.get("FCST_TIME"), "level": f.get("FCST_CONGEST_LVL"),
                     "min": f.get("FCST_PPLTN_MIN"), "max": f.get("FCST_PPLTN_MAX")}
                    for f in (live.get("FCST_PPLTN") or []) if isinstance(f, dict)
                ],
                "subway": sub if isinstance(sub, list) else [],
            }
    except Exception as e:  # noqa: BLE001
        out = {"place": place, "error": f"서울 자료를 받지 못했습니다 ({e})"}
    out["fetched"] = dt.datetime.now().strftime("%H:%M")
    with _lock:
        if "error" not in out:
            _seoul_cache[place] = (time.time(), out)
        elif c:  # 서울 API가 잠깐 안 될 때는 직전 정상 자료를 보여 준다
            return {**c[1], "stale": True}
    return out


def seoul_places():
    try:
        lines = PLACES_FILE.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return DEFAULT_PLACES
    return [s.strip() for s in lines if s.strip() and not s.lstrip().startswith("#")][:20] or DEFAULT_PLACES


def seoul_now(places, fresh=False):
    key = seoul_key()
    if not key:
        return {"needKey": True, "places": []}
    with ThreadPoolExecutor(max_workers=6) as ex:
        return {"needKey": False, "places": list(ex.map(lambda p: fetch_place(key, p, fresh), places))}


# ---------------- 화면 ----------------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body, ctype="application/json; charset=utf-8", code=200):
        b = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        path = urllib.parse.unquote(u.path)
        if path in ("/", "/index.html"):
            # 새 화면(index.html)이 있으면 그것을, 없으면 예전 page.html을 보여 준다
            page = HERE / "index.html" if (HERE / "index.html").is_file() else HERE / "page.html"
            self.send(page.read_bytes(), "text/html; charset=utf-8")
        elif path == "/busan.json":
            self.send(busan_cached())
        elif path == "/seoul.json":
            self.send(seoul_now(seoul_places()))
        elif path.startswith("/fonts/"):
            name = path[len("/fonts/"):]
            f = HERE / "fonts" / name
            if "/" in name or not f.is_file():
                return self.send({"error": "없는 파일"}, code=404)
            self.send(f.read_bytes(), "font/woff2")
        elif path == "/api/files":
            self.send(busan_files())
        elif path.startswith("/data/"):
            name = path[len("/data/"):]
            f = DATA_DIR / name
            if "/" in name or not f.is_file():
                return self.send({"error": "없는 파일"}, code=404)
            self.send(f.read_bytes(), "text/csv")
        elif path == "/api/seoul":
            places = [p.strip() for p in q.get("places", [""])[0].split(",") if p.strip()][:20]
            self.send(seoul_now(places, fresh="fresh" in q))
        else:
            self.send({"error": "없는 주소"}, code=404)


def main():
    DATA_DIR.mkdir(exist_ok=True)
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError:
        print("이미 켜져 있어서 브라우저만 엽니다.")
        webbrowser.open(f"http://localhost:{PORT}")
        return
    print(f"화면 주소: http://localhost:{PORT}")
    print("이 창을 닫으면 화면도 멈춥니다. 끝내려면 Ctrl+C")
    threading.Timer(0.8, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    sys.exit(main())
