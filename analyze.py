# -*- coding: utf-8 -*-
"""data/heritage.json → data/analysis.json

  - 분류·아이콘(이모지)·시대 묶음 — 규칙은 아래 표. 향토유산 시대는 이름으로 짐작한 것만 '(추정)'.
  - 향유·물리적 접근(연구진 추정): 가까운 버스정류장, 차가 다니는 도로에서의 거리·고도차, 산지 지번, 관람 형태.
  - 3D 보기 재료: 유산 둘레 400m 건물 외곽선(화재안전 상황판이 받아 둔 브이월드 건물), 고도는 AWS Terrain Tiles.

이웃 상황판 자료: ../sejong_town/data/raw/tago.json(정류장), ../sejong_fire/data/network.json(도로), ../sejong_fire/data/raw/bldg_tiles.
"""
from __future__ import annotations

import glob
import io
import json
import math
import os
import re
import urllib.request
from collections import Counter, defaultdict

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(HERE, "data", "raw")
KX, KY = 89_500.0, 111_000.0
DEM_Z = 14

# ── 분류: (id, 이름, 기본 아이콘) — 위에서부터 먼저 맞는 규칙
CATS = [
    ("intang", "무형·민속", "🥁"),
    ("nature", "자연유산", "🌳"),
    ("modern", "근대 건축", "🏛️"),
    ("buddha", "불교 유산", "☸️"),
    ("fort", "산성·옛터", "🧱"),
    ("hall", "향교·서원·사당", "🕯️"),
    ("gate", "충·효·열 정려", "🎖️"),
    ("tomb", "무덤·비석", "🪦"),
    ("record", "기록·유물", "📜"),
    ("house", "옛집", "🏡"),
]
CATN = {c[0]: c[1] for c in CATS}


def classify(it):
    n, k = it["name"], it["kind"]
    note = " ".join(it.get("note") or [])
    if k in ("국가무형유산", "무형유산") or re.search(r"(산제|장승제|쌍탑제|주당풀이|지게장인)", n):
        ic = {"가야금": "🎶", "판소리": "🎤", "궁인": "🏹", "강다리기": "🪢", "낙화": "🔥", "동제": "🏮",
              "산제": "⛰️", "장승제": "🏮", "쌍탑제": "🏮", "주당풀이": "🎭", "지게": "🧺"}
        return "intang", next((v for kk, v in ic.items() if kk in n), "🥁")
    if k in ("천연기념물", "자연유산") or re.search(r"(초수|나무)", n):
        return "nature", "🐦" if "백로" in n else ("💧" if "초수" in n else "🌳")
    if k in ("국가등록문화유산", "시등록문화유산") or "초등학교" in n:
        return ("house", "🏡") if "가옥" in n else ("modern", "⛪" if "성당" in n else ("🏭" if "공장" in n else "🏫"))
    if "홍판서댁" in n:
        return "house", "🏡"
    if re.search(r"(부조묘|가묘|보만정)", n):
        return "hall", "🕯️"
    if re.search(r"(불비상|여래|나한|불상|미륵|탱화|탱|도$|도 초본|시왕도|신중도|산신도|독성도|현왕도|칠성도|석탑|승탑|청한당탑|부도|극락보전|선요)", n):
        return "buddha", "🪷" if re.search(r"(여래|나한|불상|미륵|불비상)", n) else ("🪨" if re.search(r"(탑|부도)", n) else "☸️")
    if re.search(r"(산성|성$|^이성|금이성|고분군|고인돌|입석)", n):
        return "fort", "🪨" if re.search(r"(고인돌|入石|입석)", n) else ("⚱️" if "고분" in n else "🧱")
    if "정려" in n or "열녀문" in n or "효자각" in n:
        return "gate", "🎖️"
    if re.search(r"(묘|비$|신도비|척화비|효교비|묘비|장승$|석장승)", n):
        return "tomb", "🗿" if "장승" in n else "🪦"
    if re.search(r"(향교|서원|사$|사우|영당|정$|각$|재$|가묘|부조묘|모인당|숭덕사)", n):
        return "hall", "📚" if re.search(r"(향교|서원)", n) else ("🌿" if re.search(r"(정$|독락정)", n) else "🕯️")
    return "record", "📜"


# ── 시대
ERAS = [("pre", "선사"), ("three", "삼국·백제"), ("unified", "통일신라"), ("goryeo", "고려"), ("joseon", "조선"),
        ("modern", "근대(1876~1950)"), ("living", "지금도 이어지는 무형유산"), ("unknown", "시대 미상")]
ERAN = dict(ERAS)


def era_of(it, cat):
    if cat == "intang":
        return "living", False
    if "은행나무" in it["name"] or "향나무" in it["name"]:
        return "joseon", False        # 약 400~600년 전 심긴 나무(조선 초·중기)
    toks = list(it.get("note") or []) + [(it.get("khs") or {}).get("era", "")]
    s = " ".join(toks)
    m = re.search(r"(\d{3,4})\s*년?", s)
    yrs = [int(y) for y in re.findall(r"(?<!\d)(\d{3,4})(?!\d|㎡|㎝|\.\d)", " ".join(t for t in toks if not re.search(r"[㎡㎝×]|지정|보호|^\d{1,3}(,\d{3})+$", t)))]
    yrs = [y for y in yrs if 500 <= y <= 1990]
    if re.search(r"통신|통일신라", s):
        return "unified", False
    if "백제" in s or "삼국" in s:
        return "three", False
    if "고려" in s:
        return "goryeo", False
    if re.search(r"조선.{0,3}~", s):
        return "joseon", False        # '조선후기~일제강점기' 는 시작 시대로
    if "일제" in s or "1930년대" in s:
        return "modern", False
    if yrs:
        y = min(yrs)
        return ("three" if y <= 668 else "unified" if y <= 935 else "goryeo" if y <= 1392 else "joseon" if y < 1876 else "modern"), False
    if "조선" in s or re.search(r"세기", s):
        return "joseon", False
    if "약 400년" in s or "약 600년" in s:
        return "joseon", False        # 나무가 심긴 때
    if it["grade"] == "향토":
        n = it["name"]
        if re.search(r"(고인돌|입석)", n):
            return "pre", True
        if cat in ("gate", "hall", "tomb"):
            return "joseon", True
    return "unknown", False


def view_of(it, cat):
    a = it["addr"]
    note = " ".join(it.get("note") or [])
    if it.get("stored"):
        return "stored", "해체 보관 중 — 지금은 볼 수 없음"
    if "시립민속박물관" in note or "금사리 75" in a:
        return "museum", "세종시립민속박물관 소장 — 실내 전시·관람"
    if "국세청" in a:
        return "office", "국세청(나성동) 소장 — 상시 공개 여부 확인 필요"
    if cat == "intang":
        return "event", "행사·시연 때 만남(보유자·보존회)"
    if cat == "buddha" and re.search(r"(도|탱화|선요|복장|나한|아미타|여래좌상|팔상도)", it["name"]) and not re.search(r"(탑|부도)", it["name"]) and "마애" not in it["name"] and "석조" not in it["name"]:
        return "temple", "사찰 안 소장 — 법당 공개 여부는 사찰 문의"
    if re.search(r"(문서|일기|호패|교지|지석|초상|유물|연성지)", it["name"]):
        return "family", "문중·개인 소장 — 공개 여부 확인 필요"
    return "outdoor", "야외 — 상시 볼 수 있음"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def dist(a, b):
    return math.hypot((a[0] - b[0]) * KX, (a[1] - b[1]) * KY)


# ── 고도(AWS Terrain Tiles, terrarium) — 타일은 data/raw/dem 캐시
def _tile(z, x, y):
    p = os.path.join(RAW, "dem", "%d_%d_%d.png" % (z, x, y))
    if not os.path.exists(p):
        os.makedirs(os.path.dirname(p), exist_ok=True)
        u = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/%d/%d/%d.png" % (z, x, y)
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as r:
            open(p, "wb").write(r.read())
    return Image.open(p).convert("RGB")


_cache = {}


def elev(lon, lat):
    z = DEM_Z
    n = 2 ** z
    fx = (lon + 180) / 360 * n
    fy = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    tx, ty = int(fx), int(fy)
    k = (tx, ty)
    if k not in _cache:
        _cache[k] = _tile(z, tx, ty)
    im = _cache[k]
    px, py = min(255, int((fx - tx) * 256)), min(255, int((fy - ty) * 256))
    r, g, b = im.getpixel((px, py))
    return r * 256 + g + b / 256 - 32768


def main():
    H = load(os.path.join(HERE, "data", "heritage.json"))
    items = H["items"]
    stops = [(s["gpslong"], s["gpslati"], s["nodenm"]) for s in load(os.path.join(ROOT, "sejong_town", "data", "raw", "tago.json"))["items"]]
    # 차가 들어가는 길: OSM(마을 안길·농로 포함, 임도 track·고속도로 제외). 표준노드링크는 마을길이 없어 쓰지 않는다.
    osm = load(os.path.join(RAW, "osm_roads.json"))
    road = defaultdict(list)          # 100m 격자 → 도로 점
    for w in osm["elements"]:
        hw = (w.get("tags") or {}).get("highway", "")
        if hw in ("track", "motorway", "motorway_link") or not w.get("geometry"):
            continue
        pts = [(g["lon"], g["lat"]) for g in w["geometry"]]
        dense = []
        for a, b in zip(pts, pts[1:]):
            n = max(1, int(dist(a, b) / 40))
            dense += [(a[0] + (b[0] - a[0]) * t / n, a[1] + (b[1] - a[1]) * t / n) for t in range(n)]
        dense.append(tuple(pts[-1]))
        for p in dense:
            road[(int(p[0] * KX / 100), int(p[1] * KY / 100))].append(p)

    def near_road(x, y):
        gx, gy = int(x * KX / 100), int(y * KY / 100)
        best, bd = None, 1e9
        for r in range(0, 30):
            for i in range(gx - r, gx + r + 1):
                for j in range(gy - r, gy + r + 1):
                    if max(abs(i - gx), abs(j - gy)) != r:
                        continue
                    for p in road.get((i, j), ()):
                        d = dist(p, (x, y))
                        if d < bd:
                            best, bd = p, d
            if best and bd < r * 100:
                break
        return best, bd

    sites = []
    for it in items:
        cat, ic = classify(it)
        era, guess = era_of(it, cat)
        vk, vtxt = view_of(it, cat)
        k = it.get("khs") or {}
        o = {"id": it["id"], "name": it["name"], "hanja": it["hanja"], "grade": it["grade"], "kind": it["kind"],
             "date": it["date"], "addr": it["addr"], "note": it.get("note") or [], "cat": cat, "icon": ic,
             "era": era, "era_guess": guess, "era_txt": k.get("era") or next((t for t in it.get("note") or [] if re.search(r"(조선|고려|통신|삼국|백제|일제|\d{4}|세기)", t)), ""),
             "view": vk, "view_txt": vtxt, "stored": it.get("stored", False),
             "img": k.get("image") or "", "imgs": [i["url"] for i in k.get("images") or []][:4],
             "desc": (k.get("content") or "")[:1200], "url": k.get("url") or "", "quan": k.get("quan") or "",
             "owner": k.get("owner") or "", "admin": k.get("admin") or "", "cls": [c for c in k.get("cls") or [] if c]}
        loc = it.get("loc")
        if loc:
            x, y = loc["lon"], loc["lat"]
            o.update(lon=round(x, 6), lat=round(y, 6), approx=bool(loc.get("approx")), loc_by=loc.get("by", ""))
            ds = sorted((dist((sx, sy), (x, y)), nm) for sx, sy, nm in stops)
            o["stop_m"], o["stop_nm"] = round(ds[0][0]), ds[0][1]
            o["stops500"] = sum(1 for d, _ in ds if d <= 500)
            rp, rd = near_road(x, y)
            o["road_m"] = round(rd)
            try:
                e0, e1 = elev(x, y), elev(*rp)
                o["elev"], o["rise"] = round(e0), round(e0 - e1)
            except Exception as ex:
                print("고도 실패", it["name"], ex)
            o["mount"] = bool(re.search(r"(^|\s)산\s?\d", it["addr"])) or "일원" in it["addr"]
        sites.append(o)
    # 걷기 쉬움(연구진 추정): 휠체어·유모차·고령자 기준의 대략 분류
    for o in sites:
        if o.get("lon") is None or o["view"] in ("stored",):
            o["ease"] = None
            continue
        if o["view"] in ("museum",):
            o["ease"] = "easy"
            continue
        if o["view"] == "event" or o.get("approx"):
            o["ease"] = None
            continue
        hard = o.get("mount") or (o.get("rise") or 0) >= 25 or o["road_m"] >= 400
        mid = (o.get("rise") or 0) >= 8 or o["road_m"] >= 120 or o["stop_m"] >= 1000
        o["ease"] = "hard" if hard else ("mid" if mid else "easy")
    # 3D 재료: 둘레 400m 건물
    located = [(o["lon"], o["lat"], o["id"]) for o in sites if o.get("lon") and not o.get("approx")]
    grid = defaultdict(list)
    for x, y, sid in located:
        grid[(int(x * KX / 400), int(y * KY / 400))].append((x, y, sid))
    bld = defaultdict(list)
    tiles = glob.glob(os.path.join(ROOT, "sejong_fire", "data", "raw", "bldg_tiles", "*.json"))
    seen = set()
    for fn in tiles:
        feats = load(fn)
        for f in feats:
            if f["id"] in seen:
                continue
            g = f["geometry"]["coordinates"]
            ring = g[0][0] if f["geometry"]["type"] == "MultiPolygon" else g[0]
            cx = sum(p[0] for p in ring) / len(ring)
            cy = sum(p[1] for p in ring) / len(ring)
            gx, gy = int(cx * KX / 400), int(cy * KY / 400)
            for i in (gx - 1, gx, gx + 1):
                for j in (gy - 1, gy, gy + 1):
                    for x, y, sid in grid.get((i, j), ()):
                        if dist((cx, cy), (x, y)) <= 400:
                            seen.add(f["id"])
                            p = f["properties"]
                            h = p.get("height") or ((p.get("grnd_flr") or 0) * 3.3) or 4
                            bld[sid].append({"r": [[round((q[0] - x) * KX, 1), round((q[1] - y) * KY, 1)] for q in ring],
                                             "h": round(min(h, 150), 1)})
    # 3D 는 같은 자리(같은 좌표)를 여러 유산이 함께 쓴다 → 좌표 묶음 하나에 건물 한 벌
    spots = {}
    for o in sites:
        if o["id"] in bld:
            spots[o["id"]] = bld[o["id"]]
    for o in sites:
        o["b3d"] = o["id"] in spots
    # 같은 자리 묶음(비암사·박물관 등)
    place = defaultdict(list)
    for o in sites:
        if o.get("lon"):
            place[(round(o["lon"], 3), round(o["lat"], 3))].append(o["id"])
    units = load(os.path.join(ROOT, "sejong_livingzone", "assets", "sejong_units.json"))

    def inside(x, y, ring):
        c, j = False, len(ring) - 1
        for i in range(len(ring)):
            (xi, yi), (xj, yj) = ring[i], ring[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                c = not c
            j = i
        return c
    EMD_TXT = [u["name"] for u in units["units"]]
    for o in sites:
        # 읍면동: 시 표 주소 첫 낱말이 먼저(옛 리 이름은 읍면 소속), 동 지역은 좌표로
        w = o["addr"].replace("세종시 ", "").split(" ")[0] if o["addr"] else ""
        w = {"전통면": "전동면", "나성길": "나성동"}.get(w, w)
        u = w if w in EMD_TXT else None
        if u is None and o.get("lon"):
            u = next((x["name"] for x in units["units"] if any(inside(o["lon"], o["lat"], r) for r in x["rings"])), None)
        if "관내(조치원)" in o["addr"]:
            u = "조치원읍"
        o["unit"] = u
        o["urban"] = bool(u and u.endswith("동"))
        # 시간 여행 막대에 놓을 해(대략): 적힌 해가 있으면 그 해, 없으면 시대 가운데
        ytok = [o["era_txt"]] + [t for t in o["note"] if re.fullmatch(r"[(]?\d{3,4}(년|~|년\))?[)]?,?", t.strip()) or ("년" in t and "약" not in t)]
        yrs = [int(y) for y in re.findall(r"(?<![\d.,])(\d{3,4})(?![\d,])", " ".join(ytok)) if 500 <= int(y) <= 1990]
        mid = {"pre": -800, "three": 450, "unified": 750, "goryeo": 1150, "joseon": 1600, "modern": 1910, "living": 2026, "unknown": None}
        y = min(yrs) if yrs and o["era"] not in ("living",) else mid[o["era"]]
        if o["era"] == "three" and "5세기" in " ".join(o["note"]):
            y = 450
        if "16C" in " ".join(o["note"]) or "16세기" in o["era_txt"]:
            y = 1550
        if "18C" in " ".join(o["note"]):
            y = 1720
        if "은행나무" in o["name"]:
            y = 1400
        if "향나무" in o["name"]:
            y = 1600
        o["year"] = y
        o["year_exact"] = bool(yrs) and o["era"] not in ("living",)
    out = {"sites": sites, "cats": CATS, "eras": ERAS, "as_of": H["as_of"], "collected": H["collected"],
           "counts": H["counts"], "khs_n": H["khs_n"], "units": units, "n_stops": len(stops),
           "bld_n": sum(len(v) for v in spots.values()), "osm_at": osm["osm3s"]["timestamp_osm_base"][:10]}
    json.dump(out, open(os.path.join(HERE, "data", "analysis.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump(spots, open(os.path.join(HERE, "data", "b3d.json"), "w", encoding="utf-8"), separators=(",", ":"))
    print("분류", Counter(o["cat"] for o in sites))
    print("시대", Counter(o["era"] for o in sites))
    print("관람", Counter(o["view"] for o in sites))
    print("걷기", Counter(o["ease"] for o in sites))
    print("3D 건물", out["bld_n"], "개,", len(spots), "곳")


if __name__ == "__main__":
    main()
