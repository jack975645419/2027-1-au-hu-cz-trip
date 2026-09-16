#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""用 OpenStreetMap Nominatim 把景点名转成经纬度，写入 data/places.json。

免费、无需 Key。Nominatim 要求：自定义 User-Agent、限 1 req/s（脚本已限速）。
    python geocode.py
"""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "data" / "places.json"
UA = "2027-au-hu-cz-trip-planner/1.0 (personal travel planning)"

# (id, 中文名, 当地名/查询词, 城市, 备注)
PLACES = [
    # ---------- 布达佩斯 ----------
    ("nyc_cafe", "纽约咖啡厅", "New York Cafe, Budapest", "Budapest", "号称世界最美咖啡厅，早去排队"),
    ("szechenyi_bath", "塞切尼温泉浴场", "Szechenyi Thermal Bath, Budapest", "Budapest", "户外温泉，冬季泡汤极爽"),
    ("heroes_square", "英雄广场", "Hosok tere, Budapest", "Budapest", "紧邻塞切尼浴场"),
    ("chain_bridge", "塞切尼链桥", "Szechenyi Lanchid, Budapest", "Budapest", "连接布达与佩斯"),
    ("fishermans_bastion", "渔人堡", "Halaszbastya, Budapest", "Budapest", "9点前免费且人少"),
    ("matthias_church", "马加什教堂", "Matyas-templom, Budapest", "Budapest", "与渔人堡同一广场"),
    ("parliament_view", "国会大厦观景点", "Batthyany ter, Budapest", "Budapest", "对岸拍国会大厦经典机位"),
    ("buda_castle", "布达堡", "Budai Var, Budapest", "Budapest", "布达王宫区"),
    ("danube_cruise", "多瑙河游船码头", "Vigado ter, Budapest", "Budapest", "夜游多瑙河登船点"),
    ("state_opera", "匈牙利国家歌剧院", "Magyar Allami Operahaz, Budapest", "Budapest", "可听歌剧或参加导览"),
    ("st_stephens", "圣伊什特万圣殿", "Szent Istvan Bazilika, Budapest", "Budapest", "登顶可俯瞰全城"),
    ("liberty_bridge", "自由桥", "Szabadsag hid, Budapest", "Budapest", "绿色桥身，电车穿行"),
    ("parliament", "匈牙利国会大厦", "Orszaghaz, Budapest", "Budapest", "需提前订导览票"),

    # ---------- 维也纳 ----------
    ("st_stephens_cathedral", "斯蒂芬大教堂", "Stephansdom, Wien", "Vienna", ""),
    ("hofburg", "霍夫堡宫", "Hofburg, Wien", "Vienna", ""),
    ("karlskirche", "卡尔教堂", "Karlskirche, Wien", "Vienna", ""),
    ("cafe_mozart", "莫扎特咖啡馆", "Albertinaplatz, Wien", "Vienna", ""),
    ("zollamtssteg", "绿桥（爱在黎明破晓前）", "Zollamtssteg, Wien", "Vienna", "电影打卡点"),
    ("josefsplatz", "约瑟夫广场", "Josefsplatz, Wien", "Vienna", "霍夫堡旁"),
    ("graben", "格拉本大街", "Graben, Wien", "Vienna", "商业步行街"),
    ("belvedere", "美景宫", "Schloss Belvedere, Wien", "Vienna", "藏有克里姆特《吻》"),
    ("kunsthistorisches", "艺术史博物馆", "Kunsthistorisches Museum, Wien", "Vienna", "周一闭馆"),
    ("schonbrunn", "美泉宫", "Schloss Schonbrunn, Wien", "Vienna", "需预留半天"),
    ("musikverein", "金色大厅", "Musikverein, Wien", "Vienna", "音乐会场地"),

    # ---------- 湖区 ----------
    ("hallstatt", "哈尔施塔特", "Hallstatt, Oberosterreich", "Hallstatt", "火车站需换渡船过湖"),
    ("st_wolfgang", "圣沃尔夫冈", "St. Wolfgang im Salzkammergut", "St. Wolfgang", "沙夫山齿轨火车"),

    # ---------- 布拉格（草案，待确认）----------
    ("old_town_square", "老城广场（天文钟）", "Staromestske namesti, Praha", "Prague", "待确认"),
    ("charles_bridge", "查理大桥", "Charles Bridge, Prague", "Prague", "待确认"),
    ("prague_castle", "布拉格城堡", "Prazsky hrad, Praha", "Prague", "待确认"),
    ("st_vitus", "圣维特大教堂", "Katedrala svateho Vita, Praha", "Prague", "待确认"),
    ("lenon_wall", "列侬墙", "Lennonova zed, Praha", "Prague", "待确认"),
    ("dancing_house", "跳舞的房子", "Tancici dum, Praha", "Prague", "待确认"),
]


def geocode(query):
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": query, "format": "json", "limit": 1})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
    if not data:
        return None
    return float(data[0]["lat"]), float(data[0]["lon"]), data[0].get("display_name", "")


def main():
    out = []
    for pid, zh, query, city, note in PLACES:
        try:
            g = geocode(query)
        except Exception as e:
            print(f"  ! {zh}: {e}")
            g = None
        if g:
            lat, lon, disp = g
            print(f"  {zh:<12} {lat:.5f}, {lon:.5f}")
            out.append({"id": pid, "name": zh, "query": query, "city": city,
                        "lat": lat, "lon": lon, "note": note})
        else:
            print(f"  ? {zh}: 未找到")
        time.sleep(1.1)  # Nominatim 限速 1 req/s
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n写入 {OUT}  ({len(out)}/{len(PLACES)})")


if __name__ == "__main__":
    main()
