# 세종 국가유산 상황판 (heritage_sejong)

세종시 「국가유산 지정(등록) 현황」(2026.1.1) 137건을 이모지 지도로 찾고 읽는 공개 상황판.
주소 https://ysong86.github.io/heritage_sejong/ · 대문 목록에서 화재안전 바로 아래.

## 만드는 순서

```
C:\Python313\python.exe collect.py     # HWP 137건 + 국가유산청 Open API(사진·설명·좌표) + 브이월드 주소 좌표 → data/heritage.json
C:\Python313\python.exe analyze.py     # 분류·이모지·시대·걷기 쉬움·3D 건물 → data/analysis.json (b3d.json 도 만들지만 배포 안 함)
C:\Python313\python.exe build.py       # template.html → site/index.html
```
→ gh-pages 에 site/index.html·.nojekyll 한 커밋(공개, 비밀번호 없음).

## 탭
① 유산 찾기(지정·관리 현황 검색) ② 시대의 지층(시간 여행 막대) ③ 이야기 코스 ④ 세시 달력 ⑤ 개발과 유산 ⑥ 누구나 누리는 유산(향유권·물리적 접근). 유산마다 상세 카드(사진·설명·길찾기). 3D 보기는 만들었다가 뺐다(사용자 판단).

## 알아둘 것
- 새 현황표가 오면 assets/ 의 HWP 를 바꾸고 collect.py 의 HWP 경로를 고친다. 파서는 절 머리('1. 보물(4)')와 연번으로 끊는다 — 절별 건수가 표와 맞는지 확인.
- 키: config.json(gitignore) = 읍면 상황판 config 의 포털 키·브이월드 키. 브이월드 배경·위성 타일은 ysong86.github.io 에서만 뜬다(로컬은 CARTO·Esri 로 물러남).
- 이웃 자료: 정류장 ../sejong_town/data/raw/tago.json, 건물 ../sejong_fire/data/raw/bldg_tiles, 행정동 ../sejong_livingzone/assets/sejong_units.json.
- 도로는 OSM(Overpass, data/raw/osm_roads.json) — 표준노드링크엔 마을길이 없어 '길에서 거리'가 부풀었다.
- 이야기 코스·세시 달력 글은 build.py 의 COURSES·CAL. 날짜가 불확실한 행사는 '해마다 확인' 꼬리.
- 디자인: 대문 틀 + 끝에 '말랑 층'(둥근 칩·분류별 파스텔 마커·Jua 제목·이모지, 사용자 요청 2026-10-22).
- 제작 표기(사용자 지정): 세종연구원 세종지역학센터 이재민 센터장 / 세종연구원 송양호 책임연구위원(송양호는 지역학센터 아님), 문의 ysong@sri.re.kr.
