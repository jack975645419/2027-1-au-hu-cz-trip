#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""用 Overpass API（OpenStreetMap，免费无 Key）抓各住宿点的酒店候选。

    python fetch_hotels.py          抓候选 + 给推荐酒店配图
    python fetch_hotels.py --noimg  只抓候选，不抓图

产出：data/hotels.json（候选 + 推荐 + 配套图片）
"""
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PLACES = ROOT / "data" / "places.json"
OUT = ROOT / "data" / "hotels.json"
PICS = ROOT / "pictures" / "hotels"

UA = "2027-au-hu-cz-trip-planner/1.0 (personal travel planning)"
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

# (key, 中文名, 中心纬度, 中心经度, 搜索半径m, 所属 places.city)
STOPS = [
    ("vienna", "维也纳", 48.20849, 16.37313, 2500, "Vienna"),
    ("st_wolfgang", "圣沃尔夫冈", 47.74975, 13.50269, 1500, "St. Wolfgang"),
    ("hallstatt", "哈尔施塔特", 47.53479, 13.59889, 1200, "Hallstatt"),
    ("prague", "布拉格", 50.08745, 14.42097, 1800, "Prague"),
    ("budapest", "布达佩斯", 47.50078, 19.05397, 2200, "Budapest"),
]

PICK = 3  # 每个住宿点推荐几家


def overpass(query):
    body = urllib.parse.urlencode({"data": query}).encode()
    for ep in ENDPOINTS:
        try:
            req = urllib.request.Request(ep, data=body, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8")), ep
        except Exception as e:
            print(f"    {ep.split('/')[2]} 失败: {type(e).__name__}")
            continue
    return None, None


def hotels_around(lat, lon, radius):
    q = f"""[out:json][timeout:120];
(
  node["tourism"~"^(hotel|guest_house|hostel)$"](around:{radius},{lat},{lon});
  way["tourism"~"^(hotel|guest_house|hostel)$"](around:{radius},{lat},{lon});
);
out center tags;"""
    data, ep = overpass(q)
    if not data:
        return []
    out = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        name = tags.get("name") or tags.get("name:en")
        if not name:
            continue
        la = el.get("lat") or (el.get("center") or {}).get("lat")
        lo = el.get("lon") or (el.get("center") or {}).get("lon")
        if la is None:
            continue
        out.append({
            "osm_id": f"{el['type']}/{el['id']}",
            "name": name,
            "kind": tags.get("tourism", ""),
            "lat": la, "lon": lo,
            "stars": int(tags["stars"]) if tags.get("stars", "").isdigit() else None,
            "website": tags.get("website") or tags.get("contact:website") or "",
            "phone": tags.get("phone") or tags.get("contact:phone") or "",
            "street": " ".join(filter(None, [tags.get("addr:street", ""),
                                            tags.get("addr:housenumber", "")])).strip(),
            "city": tags.get("addr:city", ""),
            "postcode": tags.get("addr:postcode", ""),
        })
    print(f"    经 {ep.split('/')[2]} 取到 {len(out)} 家")
    return out


def stations_around(lat, lon, radius):
    q = f"""[out:json][timeout:120];
(
  node["railway"~"^(station|halt|subway_entrance)$"](around:{radius},{lat},{lon});
  node["public_transport"="station"](around:{radius},{lat},{lon});
);
out body;"""
    data, _ = overpass(q)
    if not data:
        return []
    return [(e["lat"], e["lon"]) for e in data.get("elements", [])
            if e.get("lat") is not None]


def haversine(a, b, c, d):
    R = 6371000.0
    p1, p2 = math.radians(a), math.radians(c)
    dp, dl = math.radians(c - a), math.radians(d - b)
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))


def main():
    noimg = "--noimg" in sys.argv
    places = json.loads(PLACES.read_text(encoding="utf-8"))

    result = {}
    for key, cn, lat, lon, radius, city in STOPS:
        print(f"\n{cn}（半径 {radius}m）")
        spots = [p for p in places if p["city"] == city] or [{"lat": lat, "lon": lon}]
        clat = sum(p["lat"] for p in spots) / len(spots)
        clon = sum(p["lon"] for p in spots) / len(spots)

        cands = hotels_around(lat, lon, radius)
        stas = stations_around(lat, lon, min(radius, 1500))
        for h in cands:
            h["dist_sights"] = round(haversine(h["lat"], h["lon"], clat, clon))
            h["dist_station"] = (round(min((haversine(h["lat"], h["lon"], s[0], s[1])
                                            for s in stas), default=0))
                                 if stas else None)
            h["score"] = (h["dist_sights"]
                          - (h["stars"] or 0) * 150
                          - (200 if h["website"] else 0)
                          - (0 if h["kind"] == "hotel" else 400))
        cands.sort(key=lambda h: h["score"])

        picks = cands[:PICK]
        print(f"  候选 {len(cands)} 家，推荐 {len(picks)} 家：" +
              "、".join(h["name"] for h in picks))
        result[key] = {"city": cn, "center": [lat, lon], "sight_center": [clat, clon],
                       "candidates": cands, "picks": [h["name"] for h in picks]}
        time.sleep(1.5)

    # 给推荐酒店配图（只认 Commons 上能搜到该酒店名的，搜不到就不配，避免张冠李戴）
    if not noimg:
        sys.path.insert(0, str(HERE))
        from fetch_photos import commons_search, download
        PICS.mkdir(parents=True, exist_ok=True)
        for key, rec in result.items():
            for h in [c for c in rec["candidates"] if c["name"] in rec["picks"]]:
                slug = "".join(ch if ch.isalnum() else "_" for ch in h["name"])[:40]
                got = []
                for i, cand in enumerate(commons_search(h["name"], limit=4)[:3], 1):
                    dest = PICS / f"{key}_{slug}_{i}.jpg"
                    if dest.exists():
                        got.append(cand)
                        continue
                    try:
                        download(cand["url"], dest)
                        got.append({**cand, "file": f"pictures/hotels/{dest.name}"})
                    except Exception:
                        pass
                    time.sleep(0.4)
                if got:
                    h["photos"] = got
                    print(f"  {h['name']}: {len(got)} 张")
                else:
                    print(f"  {h['name']}: 无图")

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(v["candidates"]) for v in result.values())
    print(f"\n完成：5 个住宿点，共 {total} 家候选 → {OUT}")


if __name__ == "__main__":
    main()
