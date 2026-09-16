#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""给网站打版本号 + 更新时间，写入仓库 data/version.js / version.json。

每次提交前跑一次：
    python version.py "这次改了什么"
"""
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(r"D:\Proj\2027-1-au-hu-cz-trip")
NOTE = sys.argv[1] if len(sys.argv) > 1 else "更新"


def git(*args):
    r = subprocess.run(["git", "-C", str(REPO), *args],
                       capture_output=True, text=True)
    return r.stdout.strip()


count = int(git("rev-list", "--count", "HEAD") or 0)
sha = git("rev-parse", "--short", "HEAD")
now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")

v = {"version": f"v{count + 1}", "built_at": now, "commit": sha, "note": NOTE}

(REPO / "data").mkdir(exist_ok=True)
(REPO / "data" / "version.js").write_text(
    "window.VERSION = " + json.dumps(v, ensure_ascii=False) + ";", encoding="utf-8")
(REPO / "version.json").write_text(
    json.dumps(v, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"{v['version']}  {v['built_at']}  {sha}  {NOTE}")
