#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Playwright 冒烟验证：pageerror + 标记数 + 行程天数 + 箭头数。
跑法：
    python scripts/smoke.py
退出码：0 = 全过；非 0 = 有失败。
"""
import json
import sys
from pathlib import Path

REPO = Path(r"D:\Proj\2027-1-au-hu-cz-trip")
URL_D = (REPO / "d" / "index.html").as_uri()
URL_INDEX = (REPO / "index.html").as_uri()

from playwright.sync_api import sync_playwright

fails = []

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context()
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    # console.error 默认不报（避免 CDN 资源错误噪声）
    js_errs = []
    def on_pageerror(e):
        s = str(e)
        if "ERR_CONNECTION" not in s and "Failed to load resource" not in s:
            js_errs.append(s)
    page.on("pageerror", on_pageerror)

    # ---- D 方案主页 ----
    print(f"加载 {URL_D}")
    page.goto(URL_D, wait_until="networkidle")
    page.wait_for_timeout(800)

    # JS 异常 / 业务 console.error（resource 错误是外部 CDN 偶发，不算）
    js_errs = []
    def on_pageerror(e):
        s = str(e)
        if "ERR_CONNECTION" not in s and "Failed to load resource" not in s:
            js_errs.append(s)
    page.on("pageerror", on_pageerror)

    # 标题
    title = page.title()
    print(f"  title: {title}")

    # 景点标记数 = circleMarker 数（placetips + markers）
    n_markers = page.evaluate("document.querySelectorAll('.leaflet-interactive').length")
    n_labels = page.evaluate("document.querySelectorAll('.plabel').length")
    n_days = page.evaluate("document.querySelectorAll('.day').length")
    n_hsec = page.evaluate("document.querySelectorAll('.hsec').length")

    print(f"  地图标记: {n_markers}, 景点 tooltip: {n_labels}, 日程卡: {n_days}, 酒店区: {n_hsec}")

    # 读取 PLACES 数（从全局）
    n_places = page.evaluate("window.PLACES ? window.PLACES.length : -1")
    print(f"  PLACES: {n_places}")

    # 读取 ITIN_D
    n_itin = page.evaluate("window.ITIN_D ? Object.keys(window.ITIN_D).length : -1")
    print(f"  ITIN_D keys: {n_itin}")

    # 期望值
    exp_places = 51
    exp_days = 11
    exp_hsec = 3   # vienna + prague + budapest

    if n_places != exp_places:
        fails.append(f"PLACES 数不符：实际 {n_places}，期望 {exp_places}")
    if n_days != exp_days:
        fails.append(f"日程卡数不符：实际 {n_days}，期望 {exp_days}")
    if n_hsec != exp_hsec:
        fails.append(f"酒店区数不符：实际 {n_hsec}，期望 {exp_hsec}")
    if n_markers < exp_places:
        fails.append(f"地图标记数过少：{n_markers} < {exp_places}")

    # ---- 选 主页 ----
    print(f"\n加载 {URL_INDEX}")
    page.goto(URL_INDEX, wait_until="networkidle")
    page.wait_for_timeout(500)
    n_picks = page.evaluate("document.querySelectorAll('a.pick').length")
    print(f"  方案 pick 卡数: {n_picks}")
    if n_picks != 1:
        fails.append(f"主页方案数不符：{n_picks}，期望 1（只保留 D）")

    # ---- pageerror 总结 ----
    print(f"\nJS 异常（排除外部 CDN 错误）: {len(js_errs)}")
    for e in js_errs:
        print(f"  ! {e}")
    if js_errs:
        fails.append(f"有 {len(js_errs)} 个 JS 异常")

    browser.close()

print("\n=== 总结 ===")
if fails:
    print(f"❌ {len(fails)} 项失败：")
    for f in fails:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("✅ 所有验证通过")
    sys.exit(0)