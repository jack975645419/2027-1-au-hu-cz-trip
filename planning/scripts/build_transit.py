#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成 data/transit.json：机场 / 火车站 / 大巴站，以及"和行程相关"的地铁站。

    python build_transit.py

- 机场、火车站、大巴站：固定清单（坐标由 Nominatim 查得，见文件内 POINTS）
- 地铁站：Overpass 抓全城的 subway 站点，再挑出"离机场 / 车站 / 每天景点群中心最近"的那几个
"""
import json
import math
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "data" / "transit.json"
UA = "2027-au-hu-cz-trip-planner/1.0 (personal travel planning)"
ENDPOINTS = ["https://overpass-api.de/api/interpreter",
             "https://overpass.kumi.systems/api/interpreter",
             "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]

# kind, 中文名, 当地名/备注, 城市, lat, lon
POINTS = [
    ("airport", "布达佩斯李斯特·费伦茨机场", "BUD · 落地与去程", "Budapest", 47.435273, 19.253511),
    ("airport", "维也纳国际机场", "VIE · 备用 / 参考", "Vienna", 48.104997, 16.584899),
    ("airport", "布拉格瓦茨拉夫·哈韦尔机场", "PRG · 2/1 回程起飞", "Prague", 50.102045, 14.270566),
    ("train", "布达佩斯东站", "Budapest-Keleti · 1/25 去维也纳", "Budapest", 47.500480, 19.083940),
    ("train", "维也纳中央车站", "Wien Hbf · 1/25 到达 / 去布拉格", "Vienna", 48.184988, 16.377939),
    ("train", "布拉格中央车站", "Praha hl.n. · 城际到达", "Prague", 50.082963, 14.436094),
    ("bus", "维也纳国际大巴站", "Wien Erdberg VIB · 1/28 去克鲁姆洛夫", "Vienna", 48.190587, 16.412949),
    ("bus", "克鲁姆洛夫大巴站", "Český Krumlov AN · 1/28 到达 / 1/29 出发", "Cesky Krumlov", 48.811468, 14.322612),
    ("bus", "布拉格 Na Knížecí 大巴站", "Anděl · 1/29 CK 回布拉格", "Prague", 50.068790, 14.405183),
]

CITY_CENTER = {"Budapest": (47.50078, 19.05397), "Vienna": (48.20849, 16.37313),
               "Prague": (50.08745, 14.42097), "Cesky Krumlov": (48.8106, 14.3150)}
HAS_METRO = ("Budapest", "Vienna", "Prague")
MAX_METRO_PER_CITY = 8


def overpass(q):
    body = urllib.parse.urlencode({"data": q}).encode()
    for ep in ENDPOINTS:
        try:
            req = urllib.request.Request(ep, data=body, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            print(f"    {ep.split('/')[2]} 失败: {type(e).__name__}")
            continue
    return None


def metro_stations(lat, lon, r=13000):
    q = f"""[out:json][timeout:120];
(
  node["railway"="station"]["station"="subway"](around:{r},{lat},{lon});
  way["railway"="station"]["station"="subway"](around:{r},{lat},{lon});
);
out center tags;"""
    data = overpass(q)
    if not data:
        return []
    out = []
    for el in data.get("elements", []):
        t = el.get("tags", {})
        name = t.get("name") or t.get("name:en")
        la = el.get("lat") or (el.get("center") or {}).get("lat")
        lo = el.get("lon") or (el.get("center") or {}).get("lon")
        if name and la is not None:
            out.append({"name": name, "lat": la, "lon": lo})
    print(f"    地铁站点 {len(out)} 个")
    return out


def hav(a, b, c, d):
    R = 6371000.0
    p1, p2 = math.radians(a), math.radians(c)
    dp, dl = math.radians(c - a), math.radians(d - b)
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))


def main():
    places = json.loads((ROOT / "data" / "places.json").read_text(encoding="utf-8"))
    itins = json.loads((ROOT / "data" / "itineraries.json").read_text(encoding="utf-8"))
    days = list(itins.values())[0]["days"]

    # 每天景点群中心（按城市归类）
    anchors = {c: [] for c in CITY_CENTER}
    for p in POINTS:
        if p[3] in anchors:
            anchors[p[3]].append({"label": p[1], "lat": p[4], "lon": p[5], "from": "交通点"})
    for d in days:
        pts = [p for p in places if p["name"] in d["items"]]
        if not pts:
            continue
        by = {}
        for p in pts:
            by.setdefault(p["city"], []).append(p)
        for c, arr in by.items():
            if c in anchors:
                anchors[c].append({"label": f"{d['date']} 景点群",
                                   "lat": sum(x["lat"] for x in arr) / len(arr),
                                   "lon": sum(x["lon"] for x in arr) / len(arr), "from": "day"})

    metro = {}
    for c in HAS_METRO:
        la, lo = CITY_CENTER[c]
        print(f"  {c} 抓地铁…")
        metro[c] = metro_stations(la, lo)
        time.sleep(1.5)

    picked = []
    for c, sts in metro.items():
        if not sts:
            continue
        used, cnt = set(), 0
        for an in sorted(anchors[c], key=lambda a: 0 if a["from"] == "交通点" else 1):
            best = min(sts, key=lambda s: hav(an["lat"], an["lon"], s["lat"], s["lon"]))
            if best["name"] in used:
                continue
            used.add(best["name"])
            picked.append({"city": c, "name": best["name"], "lat": best["lat"], "lon": best["lon"],
                           "dist": round(hav(an["lat"], an["lon"], best["lat"], best["lon"])),
                           "for": an["label"]})
            cnt += 1
            if cnt >= MAX_METRO_PER_CITY:
                break

    data = {
        "points": [{"kind": k, "name": n, "note": note, "city": c, "lat": la, "lon": lo}
                   for k, n, note, c, la, lo in POINTS],
        "metro": picked,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n写入 {OUT}：交通点 {len(data['points'])} 个 · 地铁站 {len(picked)} 个")
    for m in picked:
        print(f"    {m['city']:<14}{m['name']:<28}≈{m['dist']}m  → {m['for']}")


if __name__ == "__main__":
    main()
