#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""给每个景点抓 1-2 张样图到 pictures/。

来源优先级：
  1. Wikimedia Commons（免 Key、真实景点实拍、CC 授权）—— 主力
  2. Unsplash —— 仅在 Commons 抓不到时补位（省 50 次/小时 的额度）

用法：
    python fetch_photos.py            抓全部缺失的
    python fetch_photos.py --force    覆盖重抓
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import winreg
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PLACES = ROOT / "data" / "places.json"
PICS = ROOT / "pictures"
MANIFEST = ROOT / "data" / "photos.json"

UA = "2027-au-hu-cz-trip-planner/1.0 (personal travel planning)"
PER_PLACE = 2
SKIP_WORDS = ("map", "logo", "plan", "diagram", "chart", "coat of arms",
              "banner", "sign", "poster", "stamp", "flag", "icon")


def unsplash_key():
    k = os.environ.get("UNSPLASH_ACCESS_KEY")
    if k:
        return k
    try:  # 本 shell 继承不到新设的用户变量时，从注册表读
        reg = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment")
        return winreg.QueryValueEx(reg, "UNSPLASH_ACCESS_KEY")[0]
    except Exception:
        return ""


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def strip_html(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def commons_search(term, limit=8):
    q = urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f"filetype:bitmap {term}", "gsrnamespace": 6,
        "gsrlimit": limit, "prop": "imageinfo",
        "iiprop": "url|extmetadata|mime", "iiurlwidth": 1600,
    })
    try:
        data = get_json("https://commons.wikimedia.org/w/api.php?" + q)
    except Exception as e:
        print(f"    Commons 请求失败: {e}")
        return []
    out = []
    for page in (data.get("query", {}).get("pages") or {}).values():
        title = page.get("title", "")
        if any(w in title.lower() for w in SKIP_WORDS):
            continue
        info = (page.get("imageinfo") or [{}])[0]
        if not info.get("mime", "").startswith("image/"):
            continue
        url = info.get("thumburl") or info.get("url")
        if not url:
            continue
        meta = info.get("extmetadata", {})
        out.append({
            "url": url,
            "author": strip_html(meta.get("Artist", {}).get("value", "")),
            "license": meta.get("LicenseShortName", {}).get("value", ""),
            "page": info.get("descriptionurl", ""),
            "source": "commons",
        })
    return out


def unsplash_search(term, key, limit=3):
    q = urllib.parse.urlencode({"query": term, "per_page": limit, "client_id": key})
    try:
        data = get_json("https://api.unsplash.com/search/photos?" + q)
    except Exception as e:
        print(f"    Unsplash 请求失败: {e}")
        return []
    return [{
        "url": r["urls"]["regular"],
        "author": r.get("user", {}).get("name", ""),
        "license": "Unsplash License",
        "page": r.get("links", {}).get("html", ""),
        "source": "unsplash",
    } for r in data.get("results", [])]


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    dest.write_bytes(data)
    return len(data)


def main():
    force = "--force" in sys.argv
    places = json.loads(PLACES.read_text(encoding="utf-8"))
    PICS.mkdir(exist_ok=True)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    key = unsplash_key()
    if not key:
        print("! 未找到 UNSPLASH_ACCESS_KEY，只用 Wikimedia Commons\n")

    ok = 0
    for p in places:
        term = p.get("en") or p["query"].split(",")[0].strip()
        city = p["city"].replace(" ", "")
        targets = [(n, PICS / f"{city}_{p['id']}_{n}.jpg") for n in range(1, PER_PLACE + 1)]

        if all(t.exists() for _, t in targets) and not force and p["id"] in manifest:
            ok += 1
            continue

        cands = commons_search(term)
        if not cands and key:
            print(f"  {p['name']}: Commons 无结果 → Unsplash")
            cands = unsplash_search(term, key, limit=PER_PLACE + 1)
        if not cands:
            print(f"  ? {p['name']}: 没抓到")
            continue

        files = []
        for n, dest in targets:
            if n - 1 >= len(cands):
                break
            if dest.exists() and not force:
                old = next((f for f in manifest.get(p["id"], {}).get("files", [])
                            if f["file"].endswith(dest.name)), None)
                files.append(old or {"file": f"pictures/{dest.name}", "source": "",
                                     "author": "", "license": "", "page": ""})
                continue
            src = cands[n - 1]
            try:
                size = download(src["url"], dest)
            except Exception as e:
                print(f"  ! {p['name']} 下载失败: {e}")
                continue
            files.append({"file": f"pictures/{dest.name}", "source": src["source"],
                          "author": src["author"], "license": src["license"],
                          "page": src["page"]})
            print(f"  {p['name']} #{n}  {size // 1024}KB  [{src['source']}] {src['license'][:18]}")
            time.sleep(0.4)

        if files:
            manifest[p["id"]] = {"name": p["name"], "city": p["city"], "files": files}
            ok += 1

    MANIFEST.parent.mkdir(exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(v["files"]) for v in manifest.values())
    print(f"\n完成：{ok}/{len(places)} 个地点，共 {total} 张 → {PICS}")
    print(f"署名清单：{MANIFEST}")


if __name__ == "__main__":
    main()
