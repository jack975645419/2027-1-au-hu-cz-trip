#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把母文件夹里的数据渲染成静态站点，输出到 Git 仓库。

    python build_site.py

产出：
    仓库/index.html          方案选择页
    仓库/a/index.html        方案 A
    仓库/b/index.html        方案 B
    仓库/data/*.js           地点 / 图片 / 行程 / 标注 / 版本
    仓库/pics/*.jpg          压缩后的景点图
"""
import json
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
REPO = Path(r"D:\Proj\2027-1-au-hu-cz-trip")
PICS_SRC = ROOT / "pictures"
MAX_W, QUALITY = 900, 82
CITY_ZOOM = 11          # < 此缩放显示城市名，>= 显示景点名

places = json.loads((ROOT / "data" / "places.json").read_text(encoding="utf-8"))
photos = json.loads((ROOT / "data" / "photos.json").read_text(encoding="utf-8"))
itins = json.loads((ROOT / "data" / "itineraries.json").read_text(encoding="utf-8"))

name2id = {p["name"]: p["id"] for p in places}
CITY_CN = {"Budapest": "布达佩斯", "Vienna": "维也纳", "Hallstatt": "哈尔施塔特",
           "St. Wolfgang": "圣沃尔夫冈", "Prague": "布拉格"}
COLORS = {"Budapest": "#e0605e", "Vienna": "#6ea8fe", "Hallstatt": "#5fc98a",
          "St. Wolfgang": "#5fc98a", "Prague": "#e8a33d"}


def session_of(i, n):
    if n <= 1:
        return "全天"
    return "上午" if i < (n + 1) // 2 else "下午"


def compute_labels(itin):
    """地点 → ['1/26 下午', ...]，用于地图标注上的日期信息"""
    lab = {}
    for d in itin["days"]:
        items = d["items"]
        for i, nm in enumerate(items):
            lab.setdefault(nm, []).append(f"{d['date']} {session_of(i, len(items))}")
    return lab


# ---------- 图片 ----------
def build_pics():
    out = REPO / "pics"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    n = 0
    for rec in photos.values():
        for f in rec.get("files", []):
            src = ROOT / f["file"]
            if not src.exists():
                continue
            with Image.open(src) as im:
                im = im.convert("RGB")
                if im.width > MAX_W:
                    im = im.resize((MAX_W, int(im.height * MAX_W / im.width)), Image.LANCZOS)
                im.save(out / src.name, "JPEG", quality=QUALITY, optimize=True)
            n += 1
    print(f"  图片 {n} 张 → pics/")


def write_js(rel, var, obj):
    p = REPO / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"window.{var} = " + json.dumps(obj, ensure_ascii=False) + ";", encoding="utf-8")


def build_data():
    write_js("data/places.js", "PLACES", places)
    web = {}
    for pid, rec in photos.items():
        web[pid] = [{"file": "pics/" + Path(f["file"]).name,
                     "author": f.get("author", ""), "license": f.get("license", ""),
                     "page": f.get("page", "")}
                    for f in rec.get("files", [])
                    if (PICS_SRC / Path(f["file"]).name).exists()]
    write_js("data/photos.js", "PHOTOS", web)
    for k, itin in itins.items():
        lid = k.lower()
        write_js(f"data/itinerary_{lid}.js", f"ITIN_{k}", itin)
        write_js(f"data/labels_{lid}.js", f"LABELS_{k}", compute_labels(itin))
    print("  数据 → data/")


# ---------- 样式 ----------
CSS = """
:root{--bg:#12161c;--card:#1b212b;--line:#2a323e;--text:#e8ecf1;--dim:#9aa5b1;--accent:#6ea8fe}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",Segoe UI,sans-serif;line-height:1.6;-webkit-text-size-adjust:100%}
.wrap{max-width:900px;margin:0 auto;padding:16px}
header{padding:16px 0 8px;border-bottom:1px solid var(--line);margin-bottom:16px}
h1{margin:6px 0;font-size:22px}
h2{font-size:15px;margin:26px 0 10px;color:var(--accent)}
.sub{color:var(--dim);font-size:13px}.sub b{color:var(--text)}
.badge{display:inline-block;background:#222b36;border:1px solid var(--line);color:var(--dim);border-radius:999px;padding:3px 11px;font-size:11px}
.badge b{color:var(--accent)}
a.back{color:var(--dim);font-size:12px;text-decoration:none}
#map{height:56vh;min-height:300px;border-radius:12px;border:1px solid var(--line);background:#0e1218;z-index:1}
#map:fullscreen{height:100vh!important;width:100vw!important;border-radius:0;border:0;position:fixed;inset:0;z-index:9999}
#map:-webkit-full-screen{height:100vh!important;width:100vw!important;border-radius:0;position:fixed;inset:0;z-index:9999}
.fsbtn a{display:flex!important;align-items:center;justify-content:center;width:32px!important;height:32px!important;line-height:32px!important;font-size:15px;color:#222;text-decoration:none;background:#fff;border-radius:4px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:12px}
.day{background:var(--card);border:1px solid var(--line);border-radius:12px;margin-bottom:12px;overflow:hidden}
.day .hd{display:flex;align-items:baseline;gap:10px;padding:12px 16px;background:#202832;border-bottom:1px solid var(--line)}
.day .d{font-size:17px;font-weight:700;color:var(--accent)}
.day .w{color:var(--dim);font-size:12px}
.day .s{margin-left:auto;color:var(--dim);font-size:12px}
.day .bd{padding:12px 16px}
.tp{color:var(--dim);font-size:12px;margin-bottom:8px}.tp b{color:var(--text);font-weight:500}
.note{color:#e8c07a;font-size:12px;margin-top:8px}
ul{margin:0;padding-left:18px}li{margin:3px 0;font-size:14px}
.thumbs{display:flex;gap:8px;overflow-x:auto;margin-top:10px;padding-bottom:4px}
.thumbs img{height:96px;width:140px;object-fit:cover;border-radius:8px;border:1px solid var(--line);flex:0 0 auto}
.pros{color:#7fd39a}.cons{color:#e08a8a}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.stat .n{font-size:22px;font-weight:600}.stat .l{color:var(--dim);font-size:12px}
.pick{display:block;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:12px;color:var(--text);text-decoration:none}
.pick:hover{border-color:var(--accent)}
.pick .t{font-size:17px;font-weight:600;margin-bottom:4px}
.pick .s{color:var(--dim);font-size:13px}
footer{color:var(--dim);font-size:12px;text-align:center;padding:24px 0 40px}
.plabel{background:rgba(20,25,33,.92);border:1px solid #39434f;color:#e8ecf1;border-radius:6px;padding:3px 7px;font-size:11px;box-shadow:0 1px 4px rgba(0,0,0,.4)}
.plabel::before{display:none!important}
.plabel .lb{color:#6ea8fe;font-size:10px;margin-top:2px}
.plabel .nt{color:#9aa5b1;font-size:10px}
.clabel{background:rgba(15,19,25,.9);border:1px solid #46525f;color:#fff;border-radius:9px;padding:5px 12px;font-size:15px;font-weight:700;box-shadow:0 2px 8px rgba(0,0,0,.5)}
.clabel::before{display:none!important}
.leaflet-popup-content-wrapper{background:#1b212b;color:#e8ecf1;border-radius:10px}
.leaflet-popup-tip{background:#1b212b}
.leaflet-popup-content{margin:10px 12px;font-size:13px}
.leaflet-popup-content .note{color:#9aa5b1;font-size:12px;margin-top:4px}
"""

JS_MAP = """
const COLORS=__COLORS__, CITY_CN=__CITYCN__, CITY_ZOOM=__CITYZOOM__;
const LAB=window.__LABELVAR__||{};
const map=L.map("map").setView([47.9,16.5],6);
const bases={
 "暗色 CARTO":L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
   {maxZoom:19,subdomains:"abcd",attribution:"&copy; OpenStreetMap &copy; CARTO"}),
 "亮色 CARTO":L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
   {maxZoom:19,subdomains:"abcd",attribution:"&copy; OpenStreetMap &copy; CARTO"}),
 "Esri 街道":L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
   {maxZoom:19,attribution:"Tiles &copy; Esri"})
};
const DEF="暗色 CARTO"; bases[DEF].addTo(map);
let te=0; bases[DEF].on("tileerror",function(){ if(++te>4&&map.hasLayer(bases[DEF])){map.removeLayer(bases[DEF]);bases["Esri 街道"].addTo(map);} });

const groups={},layers={},bounds=[],placeM=[],cityM=[];
window.PLACES.forEach(p=>(groups[p.city]=groups[p.city]||[]).push(p));

Object.entries(groups).forEach(function(kv){
  const city=kv[0], items=kv[1], c=COLORS[city]||"#888", lg=L.layerGroup();
  items.forEach(function(p){
    const labArr=LAB[p.name]||[];
    const html="<b>"+p.name+"</b>"
      +(labArr.length?'<div class="lb">'+labArr.join(" / ")+"</div>":"")
      +(p.note?'<div class="nt">'+p.note+"</div>":"");
    const m=L.circleMarker([p.lat,p.lon],{radius:8,color:"#fff",weight:2,fillColor:c,fillOpacity:.95})
      .bindPopup("<b>"+p.name+"</b>"+(labArr.length?'<div class="lb">'+labArr.join(" / ")+"</div>":"")
        +(p.note?'<div class="note">'+p.note+"</div>":""))
      .bindTooltip(html,{permanent:true,direction:"top",className:"plabel",opacity:1,offset:[0,-6]})
      .addTo(lg);
    placeM.push(m); bounds.push([p.lat,p.lon]);
  });
  lg.addTo(map); layers[(CITY_CN[city]||city)+" ("+items.length+")"]=lg;

  const lat=items.reduce((s,p)=>s+p.lat,0)/items.length, lon=items.reduce((s,p)=>s+p.lon,0)/items.length;
  const cm=L.marker([lat,lon],{icon:L.divIcon({className:"",html:"",iconSize:[0,0]}),interactive:false,keyboard:false})
    .bindTooltip(CITY_CN[city]||city,{permanent:true,direction:"center",className:"clabel",opacity:1});
  cm.addTo(map); cityM.push(cm);
});
L.control.layers(bases,layers,{collapsed:window.innerWidth<600}).addTo(map);

function applyZoom(){
  const cityMode = map.getZoom() < CITY_ZOOM;
  placeM.forEach(function(m){const t=m.getTooltip();const e=t&&t.getElement();if(e)e.style.display=cityMode?"none":"";});
  cityM.forEach(function(m){const t=m.getTooltip();const e=t&&t.getElement();if(e)e.style.display=cityMode?"":"none";});
}
map.on("zoomend",applyZoom);

function toggleFs(){
  const el=document.getElementById("map");
  const req=el.requestFullscreen||el.webkitRequestFullscreen||el.msRequestFullscreen;
  const ext=document.exitFullscreen||document.webkitExitFullscreen||document.msExitFullscreen;
  if(!document.fullscreenElement&&!document.webkitFullscreenElement){ if(req) req.call(el); }
  else if(ext){ ext.call(document); }
}
const FsCtl=L.control({position:"topright"});
FsCtl.onAdd=function(){
  const d=L.DomUtil.create("div","leaflet-bar fsbtn");
  d.innerHTML='<a href="#" title="全屏" aria-label="全屏">&#9974;</a>';
  L.DomEvent.disableClickPropagation(d);
  L.DomEvent.on(d,"click",function(e){L.DomEvent.stop(e);toggleFs();});
  return d;
};
FsCtl.addTo(map);
document.addEventListener("fullscreenchange",function(){setTimeout(function(){map.invalidateSize();applyZoom();},120);});
document.addEventListener("webkitfullscreenchange",function(){setTimeout(function(){map.invalidateSize();applyZoom();},120);});

if(bounds.length){ map.fitBounds(bounds,{padding:[40,40]}); }
applyZoom();
"""

JS_DAYS = """
const P=window.PHOTOS||{}, NAME2ID=__NAME2ID__, ITIN=window.__ITINVAR__;
document.getElementById("days").innerHTML = ITIN.days.map(function(d){
  const n=d.items.length;
  const items = d.items.map(function(nm,i){
    const id=NAME2ID[nm], ph=(id&&P[id])||[];
    const th = ph.length ? '<div class="thumbs">'+ph.slice(0,3).map(f=>'<img src="../'+f.file+'" loading="lazy">').join("")+"</div>" : "";
    return "<li>"+nm+(n>1?' <span style=\\"color:#9aa5b1;font-size:12px\\">'+__SESSJS__+"</span>":"")+th+"</li>";
  }).join("");
  return '<div class="day"><div class="hd"><span class="d">'+d.date+
    '</span><span class="w">周'+d.w+'</span><span class="s">住 '+d.stay+'</span></div>'+
    '<div class="bd">'+
    (d.transport?'<div class="tp"><b>🚆</b> '+d.transport+"</div>":"")+
    (items?"<ul>"+items+"</ul>":"")+
    (d.note?'<div class="note">'+d.note+"</div>":"")+
    "</div></div>";
}).join("");
document.getElementById("stats").innerHTML = ITIN.stay.map(function(s){
  return '<div class="stat"><div class="n">'+s[1]+'</div><div class="l">'+s[0]+"</div></div>";
}).join("");
"""

JS_VER = """
const V=window.VERSION||{};
document.getElementById("ver").innerHTML="版本 <b>"+(V.version||"-")+"</b> · 更新于 "+(V.built_at||"-")+(V.note?" · "+V.note:"");
document.getElementById("verfoot").textContent=(V.version||"")+" · "+(V.built_at||"")+" · commit "+(V.commit||"")+" · "+(V.note||"");
"""

PLAN_TPL = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=5">
<title>__TITLE__ · 2027-1 奥匈捷之旅</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css">
<style>__CSS__</style></head><body><div class="wrap">
<header><a class="back" href="../index.html">← 全部方案</a>
<h1>__TITLE__</h1><div class="sub">__SUBTITLE__</div>
<div class="sub"><b>01.23 – 02.02</b> · 10 晚 11 天 · 深圳 → 维也纳 / 布达佩斯 → 广州</div>
<div class="sub" style="margin-top:9px"><span class="badge" id="ver"></span></div></header>
<h2>取舍</h2><div class="card">__TRADEOFF__</div>
<h2>住宿分配</h2><div class="grid" id="stats"></div>
<h2>地图（右上角 ⛶ 可全屏）</h2><div id="map"></div>
<h2>逐日行程</h2><div id="days"></div>
<footer><div id="verfoot"></div><div style="margin-top:6px">__TITLE__ · 草稿</div></footer>
</div>
<script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="../data/places.js"></script>
<script src="../data/photos.js"></script>
<script src="../data/labels__LID__.js"></script>
<script src="../data/itinerary__LID__.js"></script>
<script src="../data/version.js"></script>
<script>__JSMAP____JSDAYS____JSVER__</script>
</body></html>"""

INDEX_TPL = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=5">
<title>2027-1 奥匈捷之旅</title>
<style>__CSS__</style></head><body><div class="wrap">
<header><h1>2027-1 奥匈捷之旅</h1>
<div class="sub"><b>01.23 – 02.02</b> · 10 晚 11 天 · 深圳 → 维也纳 / 布达佩斯 → 广州</div>
<div class="sub" style="margin-top:9px"><span class="badge" id="ver"></span></div></header>
<h2>选择方案</h2>__PICKS__
<h2>航班（两个方案相同）</h2>
<div class="card"><div style="font-weight:600">去程 · 1/23（六）</div>
<div class="sub">深圳 SZX 01:45 → 维也纳 VIE · 海航 HU789 · 实测直飞 ¥3,357</div></div>
<div class="card"><div style="font-weight:600">回程 · 2/2（二）</div>
<div class="sub">布达佩斯 BUD 11:45 → 广州 CAN · 南航 CZ650 · 实测直飞 ¥3,313</div></div>
<footer><div id="verfoot"></div><div style="margin-top:6px">行程草稿 · 地图数据 OpenStreetMap</div></footer>
</div>
<script src="data/version.js"></script>
<script>__JSVER__</script>
</body></html>"""


def build_pages():
    for k, itin in itins.items():
        lid = k.lower()
        trade = "".join(f'<div class="pros">+ {x}</div>' for x in itin["pros"]) + \
                "".join(f'<div class="cons">− {x}</div>' for x in itin["cons"])
        jsmap = (JS_MAP.replace("__COLORS__", json.dumps(COLORS))
                       .replace("__CITYCN__", json.dumps(CITY_CN, ensure_ascii=False))
                       .replace("__CITYZOOM__", str(CITY_ZOOM))
                       .replace("__LABELVAR__", f"LABELS_{k}"))
        jsdays = (JS_DAYS.replace("__NAME2ID__", json.dumps(name2id, ensure_ascii=False))
                         .replace("__ITINVAR__", f"ITIN_{k}")
                         .replace("__SESSJS__", '"+(n<=1?"":((i<(n+1)/2)?"上午":"下午"))+"'))
        html = (PLAN_TPL.replace("__TITLE__", itin["title"])
                        .replace("__SUBTITLE__", itin["subtitle"])
                        .replace("__TRADEOFF__", trade)
                        .replace("__LID__", lid)
                        .replace("__CSS__", CSS)
                        .replace("__JSMAP__", jsmap)
                        .replace("__JSDAYS__", jsdays)
                        .replace("__JSVER__", JS_VER))
        d = REPO / lid
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(html, encoding="utf-8")
        print(f"  {lid}/index.html")

    picks = "".join(
        f'<a class="pick" href="{k.lower()}/index.html"><div class="t">{itins[k]["title"]}</div>'
        f'<div class="s">{itins[k]["subtitle"]}</div>'
        f'<div class="s" style="margin-top:6px">住宿：'
        + " · ".join(f"{c} {n}晚" for c, n in itins[k]["stay"]) + "</div></a>"
        for k in itins)
    (REPO / "index.html").write_text(
        INDEX_TPL.replace("__CSS__", CSS).replace("__PICKS__", picks).replace("__JSVER__", JS_VER),
        encoding="utf-8")
    print("  index.html（选择页）")


if __name__ == "__main__":
    print("构建站点 →", REPO)
    build_pics()
    build_data()
    build_pages()
    print("完成")
