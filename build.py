# -*- coding: utf-8 -*-
"""data/analysis.json + template.html → site/index.html (+ site/b3d.json)

  C:\\Python313\\python.exe build.py

이야기 코스·세시 달력 글은 여기(COURSES·CAL)에서 고친다. 사실 확인이 덜 된 시기·행사는 '해마다 확인' 꼬리를 단다.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "site")

# 코스: stops 는 이름에 들어가는 낱말(순서대로 선을 잇는다). line=False 면 묶음만 보여 준다.
COURSES = [
    {"id": "baekje", "icon": "🏯", "title": "백제의 마지막 기억",
     "q": "백제가 무너진 뒤, 이 땅은 무엇을 기억했나",
     "body": ["세종 서북쪽 전의·연서·전동 일대에는 백제 멸망(660년) 뒤를 기억하는 유산이 모여 있습니다. "
              "연화사의 두 불비상은 무인년(678년)에 만든 것으로, 백제 유민이 조성한 것으로 알려져 있습니다.",
              "비암사에서 나온 계유명 전씨 아미타불비상(국보)은 지금 국립청주박물관에 있고, "
              "비암사에서는 해마다 백제 유민을 기리는 제(백제대제)가 열립니다(관련 행사, 날짜는 해마다 확인).",
              "운주산성·이성·금이성·남성골산성은 금강 북쪽 고갯길과 물길을 지키던 삼국 시대 성입니다. "
              "행복도시 한가운데의 한솔동 고분군(5세기 백제)은 2025년 사적이 되었습니다."],
     "stops": ["한솔동 고분군", "부강 남성골산성", "연화사 무인명", "연화사 칠존", "운주산성", "이성", "금이성", "비암사 극락보전", "비암사 삼층석탑"],
     "line": True},
    {"id": "modern", "icon": "🏭", "title": "조치원·부강 근대 산책",
     "q": "철길과 뱃길이 만든 근대 세종",
     "body": ["경부선 조치원역과 금강 뱃길의 부강 포구는 근대 세종의 두 관문이었습니다.",
              "조치원에는 1927년 무렵 지은 산일제사 공장(누에고치에서 실을 뽑던 제사 공장)이 등록문화유산으로 남아 있고, "
              "부강에는 성당(1934년)·초등학교 강당(1926년)·근대 한옥 김재식 가옥, 그보다 앞선 홍판서댁(1866년)이 한 동네에 모여 있습니다.",
              "조치원 관음암의 불화 두 점(1935년)도 같은 시기 조치원의 모습을 보여 주는 유산입니다."],
     "stops": ["산일제사", "관음암 현왕도", "관음암 지장시왕도", "봉산영당", "부강초등학교", "부강성당", "김재식 가옥", "홍판서댁"],
     "line": True},
    {"id": "temple", "icon": "☸️", "title": "절집에 깃든 그림과 불상",
     "q": "산사 열 곳에 흩어진 불교미술",
     "body": ["세종 지정유산 가운데 불화·불상·석탑이 스무 건이 넘습니다. 전의면 비암사 한 곳에만 국가·시 지정유산 여섯 건이 모여 있습니다"
              "(극락보전·소조아미타여래좌상·삼층석탑·괘불탱화·청한당탑·승탑).",
              "불화와 복장유물은 대개 법당 안이나 수장고에 있어 늘 볼 수 있는 것은 아닙니다. 찾아가기 전 사찰에 공개 여부를 묻는 편이 좋습니다.",
              "장군면 영평사는 가을 구절초로도 이름난 절입니다(관련 행사, 해마다 확인)."],
     "stops": ["비암사 극락보전", "비암사 소조", "비암사 영산회", "비암사 삼층", "비암사 청한당", "비암사 승탑", "청안사", "학림사", "연화사 무인명",
               "황룡사", "영평사 목조나한", "고봉화상선요", "보광사 산신도", "보광사 독성도", "보광사 칠성도", "송림사", "관음암 현왕도", "관음암 지장"],
     "line": False},
    {"id": "fort", "icon": "⛰️", "title": "산성 따라 금강 북쪽 능선",
     "q": "왜 이 고장에는 산성이 이렇게 많을까",
     "body": ["시 기념물 산성 넷에 향토유산 산성 여섯(부강면)이 더해져 세종에는 이름 붙은 옛 성이 열 곳이 넘습니다.",
              "금강과 미호천이 만나는 물길, 충청 내륙으로 드는 고갯길이 겹치는 자리라 성이 촘촘했던 것으로 봅니다.",
              "대부분 산 위에 있어 걷기에 좋지만 휠체어·유모차로는 닿기 어렵습니다 — '누구나 누리는 유산' 탭의 3D 보기로 지형을 먼저 살펴보세요."],
     "stops": ["운주산성", "금이성", "이성", "부강 남성골산성", "테뫼산성", "성재산성", "화봉산성", "복두산성", "성산성", "노고봉산성"],
     "line": False},
    {"id": "gate", "icon": "🎖️", "title": "충·효·열, 마을이 기억한 사람들",
     "q": "향토유산의 절반, 정려는 무엇을 말하나",
     "body": ["향토유산 73건 가운데 서른 곳이 넘는 것이 정려(旌閭)입니다. 나라가 충신·효자·열녀를 기려 마을 어귀에 세우게 한 붉은 문과 비각으로, "
              "대부분 조선 시대에 내려졌고 문중이 지켜 왔습니다.",
              "마을마다 하나씩 있다 할 만큼 흔해 하나하나는 작지만, 모아 보면 세종 읍면 마을의 내력을 한눈에 보여 줍니다. "
              "열녀 정려처럼 오늘의 가치관과 어긋나는 대목도 함께 읽어야 하는 유산입니다.",
              "행복도시 건설로 해체해 보관 중인 정려가 세 곳 있습니다('개발과 유산' 탭)."],
     "stops": ["@gate"], "line": False},
    {"id": "seonbi", "icon": "📚", "title": "향교·서원·정자의 선비",
     "q": "조선의 시골 학교와 사당",
     "body": ["조선의 지방 교육은 관이 세운 향교와 사림이 세운 서원이 맡았습니다. 세종에는 옛 연기현·전의현의 향교 두 곳이 그대로 남아 있습니다.",
              "연기향교 앞의 척화비(1871년)는 흥선대원군이 전국에 세우게 한 비석 가운데 하나입니다. 금강가 정자(독락정·보만정)와 영당·사당은 "
              "문중이 조상과 스승을 기리던 자리입니다."],
     "stops": ["연기향교", "연기 척화비", "전의향교", "합호서원", "숭덕사", "독락정", "보만정", "봉산영당", "남산영당", "문절사", "모인당", "덕천군사우"],
     "line": False},
]

# 세시 달력: months 는 1~12, 'all' 은 연중. 맞는 유산 이름 낱말, 아니면 related(지정유산이 아닌 관련 행사).
CAL = [
    {"m": [1, 2], "title": "정월대보름 무렵 마을 제의·놀이", "names": ["용암강다리기", "대곡리 장승제", "등곡리동제", "쌍탑제"],
     "txt": "마을 공동체의 강다리기·장승제·동제·탑제는 대개 정월대보름 앞뒤로 열려 왔습니다(해마다 날짜 확인)."},
    {"m": [3, 4, 5, 6, 7, 8, 9], "title": "백로가 머무는 철", "names": ["백로 서식지"],
     "txt": "백로는 봄에 와서 가을에 떠나는 여름 철새입니다. 번식기에는 가까이 다가가지 않고 멀리서 보는 것이 예의입니다."},
    {"m": [4], "title": "비암사 백제대제", "names": ["비암사 극락보전"], "related": True,
     "txt": "백제 유민을 기리는 제례(지정유산 아님, 관련 행사). 날짜는 해마다 확인."},
    {"m": [5], "title": "초파일 무렵 낙화법 시연", "names": ["불교 낙화법"],
     "txt": "숯가루 등을 한지에 싼 낙화봉을 줄에 매달아 불을 붙이면 불꽃이 비처럼 떨어집니다. 시연 시기·장소는 해마다 확인."},
    {"m": [10], "title": "영평사 구절초", "names": ["영평사 목조나한", "고봉화상선요"], "related": True,
     "txt": "장군면 영평사의 가을 구절초(관련 행사). 절에 있는 시 지정유산 두 건과 함께 볼 수 있습니다."},
    {"m": [10, 11], "title": "노거수 단풍", "names": ["임난수 은행나무", "봉산동 향나무"],
     "txt": "약 600년 된 임난수 은행나무는 늦가을 노랗게 물듭니다. 400년 향나무는 사철 푸릅니다."},
    {"m": ["all"], "title": "보유자·보존회 공연과 시연", "names": ["가야금산조", "판소리 흥보가", "전의 궁인", "주당풀이", "지게장인"],
     "txt": "무형유산은 사람이 이어 갑니다. 공연·시연·전수 행사는 연중 수시로 열립니다(일정은 보존회·시 문화예술과 확인)."},
    {"m": ["all"], "title": "날짜가 알려지지 않은 산제", "names": ["용호산제", "원수산제"],
     "txt": "마을 산신제 두 건. 정해진 날짜를 공개 자료에서 찾지 못했습니다."},
]


def main():
    A = json.load(open(os.path.join(HERE, "data", "analysis.json"), encoding="utf-8"))
    cfg = json.load(open(os.path.join(HERE, "config.json"), encoding="utf-8"))
    site = cfg.get("site") or {}
    S = A["sites"]

    def find(word):
        if word.startswith("@"):
            return [o["id"] for o in S if o["cat"] == word[1:]]
        w = word.replace(" ", "")
        return [o["id"] for o in S if w in o["name"].replace(" ", "")]

    courses = []
    for c in COURSES:
        ids = []
        for w in c["stops"]:
            for i in find(w):
                if i not in ids:
                    ids.append(i)
        miss = [w for w in c["stops"] if not find(w)]
        if miss:
            print("코스", c["id"], "못 찾음:", miss)
        courses.append(dict(c, ids=ids, stops=None))
    cal = []
    for e in CAL:
        ids = [i for w in e["names"] for i in find(w)]
        if not ids:
            print("달력 못 찾음:", e["title"])
        cal.append(dict(e, ids=ids, names=None))
    key = ((site.get("basemap") or {}).get("key") or "").strip()
    base = {"vworld": bool(key),
            "light": "https://api.vworld.kr/req/wmts/1.0.0/%s/white/{z}/{y}/{x}.png" % key,
            "dark": "https://api.vworld.kr/req/wmts/1.0.0/%s/midnight/{z}/{y}/{x}.png" % key,
            "sat": "https://api.vworld.kr/req/wmts/1.0.0/%s/Satellite/{z}/{y}/{x}.jpeg" % key,
            "fb_light": "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
            "fb_dark": "https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
            "fb_sat": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            "dem": "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"}
    units = {"outline": A["units"]["outline"],
             "units": [{"name": u["name"], "kind": u["kind"], "rings": [[[round(p[0], 5), round(p[1], 5)] for p in r] for r in u["rings"]]}
                       for u in A["units"]["units"]]}
    payload = {"sites": S, "cats": A["cats"], "eras": A["eras"], "counts": A["counts"], "as_of": A["as_of"],
               "collected": A["collected"], "courses": courses, "cal": cal, "units": units, "base": base,
               "n_stops": A["n_stops"], "osm_at": A.get("osm_at"), "khs_n": A["khs_n"],
               "built": dt.datetime.now().strftime("%Y-%m-%d")}
    data_js = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    # 제작 표기(사용자 지정 2026-10-22): 이재민 센터장은 세종지역학센터, 송양호 책임연구위원은 센터 소속 아님 — 줄을 나눠 구분
    foot = ('<footer class="foot"><dl class="credit"><dt>제작</dt><dd><b>세종연구원 세종지역학센터</b><span>이재민 센터장</span>'
            '<b>세종연구원</b><span>송양호 책임연구위원</span></dd>'
            '<dt>문의</dt><dd><a href="mailto:ysong@sri.re.kr">ysong@sri.re.kr</a> 로 연락 주시기 바랍니다.</dd></dl>%s</footer>'
            % (
               '<span class="hits"><img alt="조회수" src="https://hits.sh/ysong86.github.io/heritage_sejong.svg?view=today-total&amp;style=flat-square'
               '&amp;label=%EC%A1%B0%ED%9A%8C%EC%88%98&amp;color=1d5c7c&amp;labelColor=64748b" onerror="this.parentNode.style.display=\'none\'"></span>'
               if "--no-hits" not in os.sys.argv else ""))
    t = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    t = t.replace("/*__DATA__*/null", data_js).replace("<!--__FOOT__-->", foot)
    os.makedirs(SITE, exist_ok=True)
    open(os.path.join(SITE, "index.html"), "w", encoding="utf-8").write(t)
    shutil.copyfile(os.path.join(HERE, "data", "b3d.json"), os.path.join(SITE, "b3d.json"))
    print("site/index.html %.0f KB, b3d.json %.1f MB" % (os.path.getsize(os.path.join(SITE, "index.html")) / 1024,
                                                         os.path.getsize(os.path.join(SITE, "b3d.json")) / 1e6))


if __name__ == "__main__":
    main()
