#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""临时比价：扫描任意「航线+日期」组合的当天最低价 / 最低直飞价，不写历史。

用法：
    python scan.py                      扫下面 CANDIDATES 里的组合
    python scan.py CAN BUD 2027-01-26   只扫一个组合
"""
import sys
from playwright.sync_api import sync_playwright

from track_price import UA, build_url, fetch, parse

CANDIDATES = [
    ("CAN", "BUD", "2027-01-23"),
    ("CAN", "BUD", "2027-01-24"),
    ("CAN", "BUD", "2027-01-26"),
    ("SZX", "BUD", "2027-01-25"),
    ("BUD", "CAN", "2027-02-02"),
    ("BUD", "SZX", "2027-02-01"),
    ("VIE", "SZX", "2027-01-30"),
    ("VIE", "SZX", "2027-02-03"),
]


def main(items):
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
        print(f"{'航线':<16}{'日期':<13}{'最低':>9}{'最低直飞':>10}  承运 / 信号")
        print("-" * 78)
        for origin, dest, date in items:
            leg = {"origin": origin, "dest": dest, "date": date}
            try:
                text = fetch(page, build_url(leg))
                low, ldir, airline, signal, _ = parse(text)
            except Exception as e:
                print(f"{origin}-{dest}  {date}  失败 {type(e).__name__}: {e}")
                continue
            print(f"{origin}-{dest:<12}{date:<13}"
                  f"{('¥' + format(low, ',') if low else '-'):>9}"
                  f"{('¥' + format(ldir, ',') if ldir else '无直飞'):>10}"
                  f"  {airline[:12]} / {signal}")
        browser.close()


if __name__ == "__main__":
    main([tuple(sys.argv[1:4])] if len(sys.argv) >= 4 else CANDIDATES)
