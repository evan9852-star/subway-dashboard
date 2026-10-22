#!/usr/bin/env python3
"""
지하철 승하차 대시보드 (부산 | 서울)

- 부산 페이지: '부산데이터' 폴더의 부산교통공사 시간대별 승하차 CSV
- 서울 페이지: 서울 열린데이터광장 '실시간 도시데이터' API (인증키는 '서울키.txt')

실행: '지하철_대시보드_열기.command' 더블클릭 (또는 python3 live.py)
추가 설치 필요 없음 (파이썬 기본 기능만 사용)
"""
import datetime as dt
import json
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
PORT = 8765
SEOUL_TTL = 180  # 서울 자료를 다시 받아오는 간격(초)


# ---------------- 부산 ----------------
def busan_files():
    files = sorted(p for p in DATA_DIR.iterdir() if p.is_file() and p.suffix.lower() == ".csv")
    return [{"name": p.name, "mtime": int(p.stat().st_mtime)} for p in files]


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
    if "error" not in out:
        with _lock:
            _seoul_cache[place] = (time.time(), out)
    return out


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
        if path == "/":
            self.send((HERE / "page.html").read_bytes(), "text/html; charset=utf-8")
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
