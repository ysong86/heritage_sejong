# -*- coding: utf-8 -*-
"""수집: 시 현황표(HWP) 137건 + 국가유산청 공개 API(사진·설명·시대·좌표) + 브이월드 주소 좌표 → data/heritage.json

  C:\\Python313\\python.exe collect.py            # 받은 것은 data/raw 캐시를 다시 쓴다
  C:\\Python313\\python.exe collect.py --refresh  # 국가유산청 상세를 새로 받는다(지정 변경 반영)
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import hwp_list

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "data", "raw")
HWP = os.path.join(HERE, "assets", "sejong_heritage_20260101.hwp")
KHS = "https://www.khs.go.kr/cha/"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def load(p, default=None):
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, d):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


def get(url, referer=None):
    h = {"User-Agent": "Mozilla/5.0 (sejong-heritage dashboard)"}
    if referer:
        h["Referer"] = referer
    for k in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=25, context=CTX) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            if k == 2:
                raise
            time.sleep(1.5)


def key(name: str) -> str:
    n = re.sub(r"^(세종시|세종특별자치시|세종)\s+", "", name)
    return re.sub(r"[\s·()（）]", "", n)


def txt(e, tag):
    v = e.findtext(tag)
    return re.sub(r"\s+", " ", v or "").strip()


def khs(refresh=False):
    """국가유산청 국가유산 검색 Open API(키 없음). 세종(ccbaCtcd=45) 목록 → 항목별 상세."""
    cache = os.path.join(RAW, "khs.json")
    old = load(cache, {}) if not refresh else {}
    lst_xml = get(KHS + "SearchKindOpenapiList.do?ccbaCtcd=45&pageUnit=300")
    with open(os.path.join(RAW, "khs_list.xml"), "w", encoding="utf-8") as f:
        f.write(lst_xml)
    out = {}
    for it in ET.fromstring(lst_xml).findall("item"):
        if txt(it, "ccbaCncl") == "Y":        # 지정 해제
            continue
        kd, asno = txt(it, "ccbaKdcd"), txt(it, "ccbaAsno")
        k = kd + "-" + asno
        if k in old:
            out[k] = old[k]
            continue
        q = "ccbaKdcd=%s&ccbaAsno=%s&ccbaCtcd=45" % (kd, asno)
        d = ET.fromstring(get(KHS + "SearchKindOpenapiDt.do?" + q))
        item = d.find("item")
        imgs = []
        try:
            im = ET.fromstring(get(KHS + "SearchImageOpenapi.do?" + q))
            for u, desc in zip(im.iter("imageUrl"), im.iter("ccimDesc")):
                if (u.text or "").strip():
                    imgs.append({"url": u.text.strip().replace("http://", "https://"), "desc": (desc.text or "").strip()})
        except Exception:
            pass
        lon, lat = float(txt(d, "longitude") or 0), float(txt(d, "latitude") or 0)
        out[k] = {"kd": kd, "asno": asno, "name": txt(item, "ccbaMnm1"), "hanja": txt(item, "ccbaMnm2"),
                  "kind": txt(item, "ccmaName"), "cls": [txt(item, t) for t in ("gcodeName", "bcodeName", "mcodeName", "scodeName")],
                  "quan": txt(item, "ccbaQuan"), "asdt": txt(item, "ccbaAsdt"), "addr": txt(item, "ccbaLcad"),
                  "era": txt(item, "ccceName"), "owner": txt(item, "ccbaPoss"), "admin": txt(item, "ccbaAdmin"),
                  "image": (txt(item, "imageUrl") or "").replace("http://", "https://"), "images": imgs[:6],
                  "content": (item.findtext("content") or "").strip(),
                  "lon": lon if 120 < lon < 135 else None, "lat": lat if 30 < lat < 40 else None,
                  "cpno": txt(it, "ccbaCpno"),
                  "url": "https://www.heritage.go.kr/heri/cul/culSelectDetail.do?ccbaCpno=" + txt(it, "ccbaCpno")}
        time.sleep(0.25)
        print("  국가유산청", out[k]["name"])
    save(cache, out)
    return out


def clean_addr(a: str) -> list[str]:
    """시 표의 소재지 → 브이월드에 넣을 후보 주소(도로명, 지번 순)."""
    a = a.replace("세종시 ", "").replace("전통면", "전동면")
    a = re.sub(r"([가-힣])\d리", r"리", a)          # 용호1리 → 용호리(행정리 번호는 지번 주소에 없다)
    cands = []
    m = re.search(r"\(([^()]*[리동]\s?[\d산][^()]*)\)", a)
    road = re.sub(r"\(.*?\)", "", a)
    for s in ([road] + ([m.group(1)] if m else [])):
        s = re.sub(r"(외\s*\d*\s*필지?|외\s*\d*필|\s외$|번지|일원|\s*및.*$)", " ", s)
        s = re.sub(r",.*$", "", s)
        s = re.sub(r"(\d)\s+(\d)", r"\1-\2", s.strip())
        s = re.sub(r"산\s+(\d)", r"산\1", s)
        s = re.sub(r"\s+", " ", s).strip()
        s = re.sub(r"(\d+(?:-\d+)?)[^\d\s-].*$", r"\1", s)
        if s:
            emd = s.split()[0]
            if emd.endswith("리") and m is not None:
                pass
            # 동 지역 지번은 '나성동 59-14' 처럼 동 이름이 곧 법정동
            cands.append("세종특별자치시 " + s)
    return cands


def vworld(addr_cands, vkey, cache):
    for a in addr_cands:
        if a in cache:
            if cache[a]:
                return cache[a]
            continue
        hit = None
        for typ in ("ROAD", "PARCEL") if re.search(r"(로|길)\s?\d", a) else ("PARCEL", "ROAD"):
            u = ("https://api.vworld.kr/req/address?service=address&request=getcoord&version=2.0&crs=epsg:4326"
                 "&format=json&type=%s&key=%s&address=%s" % (typ, vkey, urllib.parse.quote(a)))
            try:
                r = json.loads(get(u, "https://ysong86.github.io/"))["response"]
            except Exception:
                continue
            if r.get("status") == "OK":
                p = r["result"]["point"]
                hit = {"lon": float(p["x"]), "lat": float(p["y"]), "by": "브이월드 " + ("도로명" if typ == "ROAD" else "지번"), "q": a}
                break
        cache[a] = hit
        time.sleep(0.15)
        if hit:
            return hit
    return None


def vworld_place(q, vkey, cache):
    k = "place:" + q
    if k in cache:
        return cache[k]
    u = ("https://api.vworld.kr/req/search?service=search&request=search&version=2.0&crs=EPSG:4326&size=5&page=1"
         "&type=place&format=json&key=%s&query=%s" % (vkey, urllib.parse.quote(q)))
    hit = None
    try:
        r = json.loads(get(u, "https://ysong86.github.io/"))["response"]
        for it in (r.get("result") or {}).get("items") or []:
            if "세종" in (it.get("address") or {}).get("parcel", "") + (it.get("address") or {}).get("road", ""):
                p = it["point"]
                hit = {"lon": float(p["x"]), "lat": float(p["y"]), "by": "브이월드 장소검색", "q": q, "title": it.get("title")}
                break
    except Exception:
        pass
    cache[k] = hit
    return hit


def vworld_area(addr, vkey, cache):
    """번지가 안 잡히면 리·동 단위 중심점(대략 위치)."""
    m = re.match(r"^(?:세종시\s)?(\S+[읍면동])(?:\s(\S+리))?", addr.replace("전통면", "전동면"))
    if not m:
        return None
    q = " ".join(x for x in m.groups() if x)
    q = re.sub(r"([가-힣])\d리", r"리", q)
    k = "area:" + q
    if k in cache:
        return cache[k]
    hit = None
    for cat in ("L4", "L3"):
        u = ("https://api.vworld.kr/req/search?service=search&request=search&version=2.0&crs=EPSG:4326&size=5&page=1"
             "&type=district&category=%s&format=json&key=%s&query=%s" % (cat, vkey, urllib.parse.quote(q)))
        try:
            r = json.loads(get(u, "https://ysong86.github.io/"))["response"]
            for it in (r.get("result") or {}).get("items") or []:
                if it.get("title", "").startswith("세종"):
                    p = it["point"]
                    hit = {"lon": float(p["x"]), "lat": float(p["y"]), "by": "리·동 중심(대략)", "q": it["title"], "approx": True}
                    break
        except Exception:
            pass
        if hit:
            break
    cache[k] = hit
    return hit


# 행복도시 편입으로 리 이름이 사라진 곳 → 지금 동(중심점, 대략)
MOVED = {"연동면 용호": "세종 용호동", "연기면 양화": "세종 세종동", "아름동 산": "세종 아름동"}


def vworld_dong(q, vkey, cache):
    k = "dong:" + q
    if k not in cache:
        u = ("https://api.vworld.kr/req/search?service=search&request=search&version=2.0&crs=EPSG:4326&size=3&page=1"
             "&type=district&category=L4&format=json&key=%s&query=%s" % (vkey, urllib.parse.quote(q)))
        hit = None
        try:
            for it in json.loads(get(u, "https://ysong86.github.io/"))["response"]["result"]["items"]:
                if it["title"].startswith("세종"):
                    hit = {"lon": float(it["point"]["x"]), "lat": float(it["point"]["y"]), "q": it["title"]}
                    break
        except Exception:
            pass
        cache[k] = hit
    return cache[k]


def main():
    cfg = load(os.path.join(HERE, "config.json"), {})
    vkey = ((cfg.get("site") or {}).get("basemap") or {}).get("key", "")
    os.makedirs(RAW, exist_ok=True)
    hw = hwp_list.parse(HWP)
    items = hw["items"]
    kh = khs("--refresh" in sys.argv)
    by = {}
    for k, v in kh.items():
        by.setdefault(key(v["name"]), []).append(k)
    gcache = load(os.path.join(RAW, "geocode_cache.json"), {})
    unmatched_khs = set(kh)
    for i, it in enumerate(items):
        it["id"] = "h%03d" % (i + 1)
        # 이름 정리(표 칸 쪼개짐)
        it["note"] = [n for n in it["note"] if not n.startswith("□")]
        if it["addr"] and not re.search(r"\d", it["addr"].split("(")[0]) and it["note"] and re.match(r"^\d", it["note"][-1]):
            it["addr"] += " " + it["note"].pop()          # 홍판서댁: '용포동촌길' + '43-19(부강리 385 외)'
        m = re.match(r"^(.*?[가-힣)])\s+([\u4e00-\u9fff].*)$", it["name"])
        if m:
            it["name"], it["hanja"] = m.group(1), m.group(2) + ("(" + it["hanja"] + ")" if it["hanja"] else "")
        cand = by.get(key(it["name"])) or []
        if not cand:   # 이름 표기가 조금 다른 것(띄어쓰기·'세종' 접두·및/과)
            kk = key(it["name"])
            cand = [k for k, v in kh.items() if key(v["name"]) in kk or kk in key(v["name"])]
        if it["grade"] != "향토" and cand:
            k = cand[0]
            unmatched_khs.discard(k)
            it["khs"] = kh[k]
    # 위치
    for it in items:
        k = it.get("khs") or {}
        loc = None
        if k.get("lon"):
            loc = {"lon": k["lon"], "lat": k["lat"], "by": "국가유산청"}
        a = it["addr"]
        stored = "해체보관" in a
        it["stored"] = stored
        if not loc and not stored and "관내" not in a:
            loc = vworld(clean_addr(a), vkey, gcache)
        if not loc and not stored and "관내" not in a:
            loc = vworld_place(re.sub(r"^(세종|연기|전의|전동|연서|연동|금남|부강|장군|소정|조치원)\s", "", it["name"]), vkey, gcache)
        if not loc and not stored and "관내" not in a:
            # 번지가 안 잡히면 본번만 → 같은 리의 다른 번지(대략 위치)
            base = [re.sub(r"-\d+$", "", c) for c in clean_addr(a)]
            loc = vworld(base, vkey, gcache)
            if not loc:
                m = re.match(r"^(세종특별자치시 \S+[읍면] \S+리)", base[0]) if base else None
                if m:
                    loc = vworld([m.group(1) + " " + str(n) for n in (1, 2, 3, 5, 10, 50, 100, 200)], vkey, gcache)
            if loc:
                loc = dict(loc, approx=True, by=loc["by"] + "(대략)")
        if not loc and not stored:
            for pre, dong in MOVED.items():
                if a.replace(" ", "").startswith(pre.replace(" ", "")):
                    h = vworld_dong(dong, vkey, gcache)
                    if h:
                        loc = dict(h, by="지금 %s 중심(대략) — 옛 %s" % (dong.split()[1], a.split()[1]), approx=True)
        if not loc and "관내(조치원)" in a:
            loc = {"lon": 127.2963, "lat": 36.6013, "by": "전승지 조치원읍(대략)", "approx": True}
        it["loc"] = loc
        save(os.path.join(RAW, "geocode_cache.json"), gcache)
    # 그래도 없으면 같은 리에 있는 다른 유산 자리(대략)
    def ri(a):
        m = re.match(r"^(\S+[읍면])\s(\S+?)\d?리", a)
        return m and m.groups()
    for it in items:
        if not it["loc"] and not it["stored"] and ri(it["addr"]):
            for o in items:
                if o is not it and o["loc"] and not o["loc"].get("approx") and ri(o["addr"]) == ri(it["addr"]):
                    it["loc"] = {"lon": o["loc"]["lon"], "lat": o["loc"]["lat"], "approx": True, "by": "같은 리 %s 자리(대략)" % o["name"]}
                    break
    n_loc = sum(1 for it in items if it["loc"])
    print("유산 %d건, 국가유산청 연결 %d건, 좌표 %d건" % (len(items), sum(1 for it in items if it.get("khs")), n_loc))
    for it in items:
        if not it["loc"]:
            print("  좌표 없음:", it["kind"], it["name"], "|", it["addr"])
    if unmatched_khs:
        print("  국가유산청에만 있는 항목:", [kh[k]["name"] for k in unmatched_khs])
    save(os.path.join(HERE, "data", "heritage.json"),
         {"items": items, "counts": hw["counts"], "as_of": "2026-01-01", "collected": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
          "source_hwp": os.path.basename(HWP), "khs_n": len(kh)})


if __name__ == "__main__":
    main()
