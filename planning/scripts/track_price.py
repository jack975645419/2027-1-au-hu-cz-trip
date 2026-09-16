#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""奥匈捷之旅 · 机票价格追踪（Google Flights）

用法：
    python track_price.py                              抓一次，写入 data/prices.csv + site/data.json
    python track_price.py --show                       只看历史，不抓
    python track_price.py --manual <leg_id> <价格>     被反爬挡住时手工补录
"""
import csv
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "data"
SNAP = ROOT / "snapshots"
SITE = ROOT / "site"
CSV_PATH = DATA / "prices.csv"
JSON_PATH = SITE / "data.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
CURRENCY = "CNY"

FIELDS = ["checked_at", "leg_id", "label", "date", "currency", "lowest",
          "lowest_direct", "direct_airline", "signal", "flights", "target",
          "source", "url", "snapshot"]

# 每条结果的开头形如 "09:20 – 19:10"
BLOCK_RE = re.compile(r"\d{1,2}:\d{2}\s*[–-]\s*\d{1,2}:\d{2}(?:\+\d)?")
PRICE_RE = re.compile(r"[¥￥]\s?([0-9][0-9,]{2,7})")


def build_url(leg):
    q = f"Flights to {leg['dest']} from {leg['origin']} on {leg['date']} oneway"
    return ("https://www.google.com/travel/flights?q=" + quote(q)
            + f"&curr={CURRENCY}&hl=zh-CN&gl=CN")


def fetch(page, url, timeout=30):
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    deadline = time.time() + timeout
    text = ""
    while time.time() < deadline:
        text = re.sub(r"\s+", " ", page.inner_text("body"))
        if "价格最低" in text:
            break
        page.wait_for_timeout(2000)
    return text


def parse(text):
    """从结果列表里解析出每条航班，并汇总最低价 / 最低直飞价 / Google 价格信号。"""
    flights = []
    marks = list(BLOCK_RE.finditer(text))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        block = text[m.start():end]
        prices = [int(v.replace(",", "")) for v in PRICE_RE.findall(block)]
        prices = [p for p in prices if 800 <= p <= 60000]
        if not prices:
            continue
        flights.append({
            "time": m.group(0),
            "direct": "直达" in block,
            "price": min(prices),
            "airline": block[:block.find("CAN")][:24].strip() if "CAN" in block else "",
        })

    lowest = None
    m = re.search(r"价格最低\s*[¥￥]\s?([0-9][0-9,]*)", text)
    if m:
        lowest = int(m.group(1).replace(",", ""))
    elif flights:
        lowest = min(f["price"] for f in flights)

    directs = [f for f in flights if f["direct"]]
    lowest_direct = min((f["price"] for f in directs), default=None)
    direct_airline = min(directs, key=lambda f: f["price"])["airline"] if directs else ""

    signal = ""
    ms = re.search(r"价格分析(.{0,20})", text)
    if ms:
        signal = re.sub(r"(查看历史票价|跟踪票价).*", "", ms.group(1)).strip()

    return lowest, lowest_direct, direct_airline, signal, flights


def append_row(row):
    DATA.mkdir(exist_ok=True)
    new = not CSV_PATH.exists()
    with open(CSV_PATH, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)


def read_history():
    if not CSV_PATH.exists():
        return []
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def refresh_site_json(cfg):
    rows = read_history()
    legs = []
    for leg in cfg["legs"]:
        mine = [r for r in rows if r["leg_id"] == leg["id"]]
        series = {}
        for key, col in (("any", "lowest"), ("direct", "lowest_direct")):
            pts = [{"t": r["checked_at"][:10], "price": int(r[col])}
                   for r in mine if r[col]]
            if pts:
                series[key] = pts
        if series:
            legs.append({"id": leg["id"], "label": leg["label"], "date": leg["date"],
                         "target": leg.get("target"), "series": series})
    SITE.mkdir(exist_ok=True)
    JSON_PATH.write_text(json.dumps(
        {"updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
         "currency": CURRENCY, "legs": legs},
        ensure_ascii=False, indent=2), encoding="utf-8")


def show_history(cfg):
    rows = read_history()
    if not rows:
        print("还没有数据，先跑一次 python track_price.py")
        return
    for leg in cfg["legs"]:
        mine = [r for r in rows if r["leg_id"] == leg["id"]]
        if not mine:
            continue
        last = mine[-1]
        print(f"\n{leg['label']}  {leg['date']}   目标 ¥{leg.get('target')}")
        print(f"  最新 {last['checked_at']}  {last['signal']}")
        for tag, col in (("直飞", "lowest_direct"), ("含中转", "lowest")):
            pts = [(r["checked_at"][5:10], int(r[col])) for r in mine if r[col]]
            if not pts:
                continue
            arrow = ""
            if len(pts) >= 2:
                d = pts[-1][1] - pts[-2][1]
                arrow = f"   (较上次 {'↑+' if d > 0 else '↓'}{abs(d)})"
            print(f"  [{tag}] " + "  ".join(f"{t} ¥{p:,}" for t, p in pts[-8:]) + arrow)
        if last["direct_airline"]:
            print(f"  最低直飞承运: {last['direct_airline']}")


def run(cfg):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(user_agent=UA, locale="zh-CN",
                                  timezone_id="Asia/Shanghai",
                                  viewport={"width": 1440, "height": 950})
        ctx.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
        page = ctx.new_page()
        SNAP.mkdir(exist_ok=True)

        for leg in cfg["legs"]:
            url = build_url(leg)
            try:
                text = fetch(page, url)
                lowest, ldirect, airline, signal, flights = parse(text)
            except Exception as e:
                print(f"  ! {leg['id']} 抓取失败: {type(e).__name__} {e}")
                continue
            snap = SNAP / f"{now[:10]}_{leg['id']}.png"
            page.screenshot(path=str(snap))
            print(f"  {leg['label']}: 直飞 ¥{ldirect or '-'} / 最低 ¥{lowest or '-'}  {signal}")
            append_row({
                "checked_at": now, "leg_id": leg["id"], "label": leg["label"],
                "date": leg["date"], "currency": CURRENCY,
                "lowest": lowest or "", "lowest_direct": ldirect or "",
                "direct_airline": airline, "signal": signal,
                "flights": json.dumps(flights[:12], ensure_ascii=False),
                "target": leg.get("target", ""), "source": "google-flights",
                "url": url, "snapshot": snap.name,
            })
        browser.close()


def manual(leg_id, price, direct=""):
    cfg = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    leg = next((l for l in cfg["legs"] if l["id"] == leg_id), None)
    if not leg:
        print(f"未知 leg_id: {leg_id}")
        return
    append_row({
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "leg_id": leg_id, "label": leg["label"], "date": leg["date"],
        "currency": CURRENCY, "lowest": price, "lowest_direct": direct,
        "direct_airline": "", "signal": "", "flights": "",
        "target": leg.get("target", ""), "source": "manual", "url": "", "snapshot": "",
    })
    print(f"已补录 {leg_id} ¥{price}")


if __name__ == "__main__":
    cfg = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    a = sys.argv[1:]
    if a and a[0] == "--show":
        show_history(cfg)
    elif a and a[0] == "--manual":
        manual(a[1], int(a[2]), a[3] if len(a) > 3 else "")
        refresh_site_json(cfg)
    else:
        run(cfg)
        refresh_site_json(cfg)
        show_history(cfg)
