# -*- coding: utf-8 -*-
"""세종시 '국가유산 지정(등록) 현황' HWP → 유산 목록(137건).

HWP 5.0 본문(BodyText/Section*)의 문단 글자(PARA_TEXT)만 읽어 표 칸을 한 줄씩 늘어놓은 뒤,
절 머리('1. 보물(4)', '□ 향토유산(73)')와 연번으로 끊는다. 칸 순서가 표마다 조금씩 달라
이름·지정일·소재지만 규칙으로 집고, 나머지 칸은 note 로 남긴다.
"""
from __future__ import annotations

import re
import struct
import zlib

import olefile

EMD = ["조치원읍", "연기면", "연동면", "부강면", "금남면", "장군면", "연서면", "전의면", "전동면", "소정면",
       "한솔동", "새롬동", "나성동", "다정동", "도담동", "어진동", "해밀동", "아름동", "종촌동", "고운동",
       "보람동", "대평동", "소담동", "반곡동", "세종동", "산울동", "합강동", "집현동", "용호동"]

# 절 이름 → (등급 묶음, 종목)
SECTIONS = {
    "보물": ("국가지정", "보물"), "사적": ("국가지정", "사적"), "천연기념물": ("국가지정", "천연기념물"),
    "국가무형유산": ("국가지정", "국가무형유산"), "국가민속문화유산": ("국가지정", "국가민속문화유산"),
    "유형문화유산": ("시지정", "유형문화유산"), "무형유산": ("시지정", "무형유산"), "기념물": ("시지정", "기념물"),
    "자연유산": ("시지정", "자연유산"), "시문화유산자료": ("문화유산자료", "문화유산자료"),
    "국가등록문화유산": ("등록", "국가등록문화유산"), "시등록문화유산": ("등록", "시등록문화유산"),
    "향토유산": ("향토", "향토유산"),
}
DATE = re.compile(r"^[‘’'`]\s?(\d{2})\.\s?(\d{1,2})\.\s?(\d{1,2})\.?$")


def paragraphs(path: str) -> list[str]:
    f = olefile.OleFileIO(path)
    compressed = f.openstream("FileHeader").read()[36] & 1
    secs = sorted([s for s in f.listdir() if s[0] == "BodyText"], key=lambda s: int(s[1][7:]))
    out = []
    for s in secs:
        d = f.openstream(s).read()
        if compressed:
            d = zlib.decompress(d, -15)
        i = 0
        while i < len(d):
            h = struct.unpack_from("<I", d, i)[0]
            i += 4
            tag, size = h & 0x3FF, (h >> 20) & 0xFFF
            if size == 0xFFF:
                size = struct.unpack_from("<I", d, i)[0]
                i += 4
            rec = d[i:i + size]
            i += size
            if tag != 67:          # HWPTAG_PARA_TEXT
                continue
            t, j = [], 0
            while j < len(rec):
                c = struct.unpack_from("<H", rec, j)[0]
                if c < 32:     # 제어 문자: 글자형(2바이트)과 확장형(16바이트)
                    j += 2 if c in (0, 10, 13, 24, 25, 26, 27, 28, 29, 30, 31) else 16
                    continue
                t.append(chr(c))
                j += 2
            out.append("".join(t).strip())
    return out


def _date(tok):
    m = DATE.match(tok.strip())
    if not m:
        return None
    yy, mm, dd = (int(x) for x in m.groups())
    return "%d-%02d-%02d" % (1900 + yy if yy > 50 else 2000 + yy, mm, dd)


def _addr(tok):
    t = tok.strip()
    if any(t.startswith(e) or t.startswith("세종시 " + e) for e in EMD) or t.startswith(("세종시", "LH", "나성길", "전통면")):
        return t
    return None


def parse(path: str) -> dict:
    ps = paragraphs(path)
    start = next(i for i, p in enumerate(ps) if p.startswith("□ 국가지정유산"))
    items, sec, nxt, cur = [], None, 1, None
    for p in ps[start:]:
        m = re.match(r"^(?:□\s*|\d\.\s*)([가-힣]+)\((\d+)\)$", p)
        if m and m.group(1) in SECTIONS:
            sec, nxt, cur = SECTIONS[m.group(1)] + (int(m.group(2)),), 1, None
            continue
        if sec is None or not p:
            continue
        if p == str(nxt):
            cur = {"grade": sec[0], "kind": sec[1], "no": nxt, "toks": []}
            items.append(cur)
            nxt += 1
            continue
        if cur is not None:
            cur["toks"].append(p)
    out = []
    for it in items:
        toks = it.pop("toks")
        name = toks[0]
        hanja = ""
        rest = toks[1:]
        if rest and rest[0].startswith("("):
            hanja, rest = rest[0], rest[1:]
        m = re.match(r"^(.*?)\s*\(([^()]*[一-鿿][^()]*)\)\s*$", name)   # 이름(漢字) 한 칸
        if m:
            name, hanja = m.group(1), "(" + m.group(2) + ")"
        date = addr = None
        note = []
        for t in rest:
            if date is None and _date(t):
                date = _date(t)
            elif addr is None and date and _addr(t):
                addr = t
            elif addr and t.startswith("(") and re.search(r"[리동]\s?\d", t):
                addr += " " + t       # 도로명 뒤 (지번)
            else:
                note.append(t)
        it.update(name=re.sub(r"\s+", " ", name).strip(), hanja=hanja.strip("() ").strip(), date=date,
                  addr=re.sub(r"\s+", " ", addr or "").strip(), note=[n for n in note if n])
        out.append(it)
    counts = {}
    for it in out:
        counts[it["kind"]] = counts.get(it["kind"], 0) + 1
    expect = {v[1]: None for v in SECTIONS.values()}
    return {"items": out, "counts": counts, "expect": expect}


if __name__ == "__main__":
    import json
    import sys
    r = parse(sys.argv[1])
    for it in r["items"]:
        print(it["grade"], it["kind"], it["no"], it["name"], "|", it["hanja"], "|", it["date"], "|", it["addr"], "|", it["note"])
    print(json.dumps(r["counts"], ensure_ascii=False))
