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
import sys
from pathlib import Path

from PIL import Image

WEB_PHOTOS = {}     # 由 build_data() 填充
LABELS = {}         # 方案 → 地点日期标注
BUILD_NOTE = sys.argv[1] if len(sys.argv) > 1 else "更新"

ROOT = Path(__file__).resolve().parent.parent
REPO = Path(r"D:\Proj\2027-1-au-hu-cz-trip")
PICS_SRC = ROOT / "pictures"
MAX_W, QUALITY = 900, 82
CITY_ZOOM = 11          # < 此缩放显示城市名，>= 显示景点名

places = json.loads((ROOT / "data" / "places.json").read_text(encoding="utf-8"))
photos = json.loads((ROOT / "data" / "photos.json").read_text(encoding="utf-8"))
itins = json.loads((ROOT / "data" / "itineraries.json").read_text(encoding="utf-8"))
_hp = ROOT / "data" / "hotels.json"
HOTELS = json.loads(_hp.read_text(encoding="utf-8")) if _hp.exists() else {}

# 住宿点 → 用来做「城区实景」兜底配图的景点 id
CITY_PHOTO = {"vienna": "st_stephens_cathedral", "st_wolfgang": "st_wolfgang",
              "hallstatt": "hallstatt", "prague": "charles_bridge",
              "budapest": "chain_bridge", "cesky_krumlov": "ck_old_town"}

name2id = {p["name"]: p["id"] for p in places}
name2place = {p["name"]: {"city": p["city"], "lat": p["lat"], "lon": p["lon"]}
               for p in places}
CITY_CN = {"Budapest": "布达佩斯", "Vienna": "维也纳", "Hallstatt": "哈尔施塔特",
           "St. Wolfgang": "圣沃尔夫冈", "Prague": "布拉格", "Cesky Krumlov": "克鲁姆洛夫",
           "Guangzhou": "广州", "Shenzhen": "深圳"}
COLORS = {"Budapest": "#e0605e", "Vienna": "#6ea8fe", "Hallstatt": "#5fc98a",
          "St. Wolfgang": "#5fc98a", "Prague": "#e8a33d", "Cesky Krumlov": "#b08ee8",
          "Guangzhou": "#9aa7b5", "Shenzhen": "#9aa7b5"}
# 城市 → 航班/列车字段里可能出现的写法，用来判断当天是「进入」还是「离开」
CITY_TOKENS = {"Budapest": ["BUD", "Budapest"], "Vienna": ["VIE", "Wien", "Vienna"],
               "Hallstatt": ["Hallstatt"], "St. Wolfgang": ["St. Wolfgang", "St Wolfgang"],
               "Prague": ["PRG", "Praha", "Prague"],
               "Cesky Krumlov": ["Český Krumlov", "Cesky Krumlov", "Krumlov", "CK"],
               "Guangzhou": ["CAN", "Guangzhou"], "Shenzhen": ["SZX", "Shenzhen"]}


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
    hsrc = PICS_SRC / "hotels"
    if hsrc.exists():
        hout = out / "hotels"
        hout.mkdir(exist_ok=True)
        for f in hsrc.glob("*.jpg"):
            with Image.open(f) as im:
                im = im.convert("RGB")
                if im.width > MAX_W:
                    im = im.resize((MAX_W, int(im.height * MAX_W / im.width)), Image.LANCZOS)
                im.save(hout / f.name, "JPEG", quality=QUALITY, optimize=True)
            n += 1
    print(f"  图片 {n} 张 → pics/")


def write_js(rel, var, obj):
    p = REPO / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"window.{var} = " + json.dumps(obj, ensure_ascii=False) + ";", encoding="utf-8")


def build_data():
    global WEB_PHOTOS, LABELS
    write_js("data/places.js", "PLACES", places)
    web = {}
    for pid, rec in photos.items():
        web[pid] = [{"file": "pics/" + Path(f["file"]).name,
                     "author": f.get("author", ""), "license": f.get("license", ""),
                     "page": f.get("page", "")}
                    for f in rec.get("files", [])
                    if (PICS_SRC / Path(f["file"]).name).exists()]
    WEB_PHOTOS = web
    write_js("data/photos.js", "PHOTOS", web)
    if HOTELS:
        write_js("data/hotels.js", "HOTELS", HOTELS)
    for k, itin in itins.items():
        lid = k.lower()
        write_js(f"data/itinerary_{lid}.js", f"ITIN_{k}", itin)
        LABELS[k] = compute_labels(itin)
        write_js(f"data/labels_{lid}.js", f"LABELS_{k}", LABELS[k])
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
.ampm{color:#9aa5b1;font-size:12px}
.hist a{color:var(--accent);text-decoration:none;margin-right:12px;font-size:13px}
.hsec{margin-bottom:24px}
.hsec h3{font-size:14px;margin:0 0 10px;color:var(--text)}
.hcard{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:10px}
.hcard .hn{font-weight:600;font-size:15px}
.hcard .hstars{color:#e8c07a;font-size:12px;margin-left:6px}
.hcard .hm{color:var(--dim);font-size:12px;margin-top:4px}
.hcard .ha{margin-top:8px}
.hcard .ha a{color:var(--accent);text-decoration:none;font-size:12px;margin-right:16px}
.more{color:var(--accent);font-size:12px;cursor:pointer;background:none;border:none;padding:0}
.morelist{display:none;margin-top:10px;font-size:12px;color:var(--dim);line-height:2}
.morelist.on{display:block}
ul{margin:0;padding-left:18px}li{margin:3px 0;font-size:14px}
.thumbs{display:flex;gap:8px;overflow-x:auto;margin-top:10px;padding-bottom:4px}
.thumbs img{height:96px;width:140px;object-fit:cover;border-radius:8px;border:1px solid var(--line);flex:0 0 auto}
.pros{color:#7fd39a}.cons{color:#e08a8a}
.ovw{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:6px 4px;margin-bottom:12px}
.ovw .row{display:flex;align-items:baseline;gap:10px;padding:9px 14px;border-bottom:1px solid var(--line)}
.ovw .row:last-child{border-bottom:0}
.ovw .dt{flex:0 0 auto;min-width:74px;font-weight:700;color:var(--accent);font-size:14px}
.ovw .dt .w{color:var(--dim);font-weight:400;font-size:11px;margin-left:3px}
.ovw .city{flex:0 0 auto;min-width:96px;font-size:13px;color:var(--text)}
.ovw .city.in::before{content:"→ ";color:var(--dim)}.ovw .city.out::after{content:" →";color:var(--dim)}
.ovw .seg{flex:0 0 auto;font-size:12px}
.ovw .seg .ico{margin-right:3px}
.ovw .seg.flt{color:#f0b25a}.ovw .seg.trn{color:#7fb3ff}
.ovw .seg .tn{color:var(--text);font-weight:500}
.ovw .seg .tm{color:var(--dim);margin-left:4px}
.ovw .seg .tm.pending{color:#8a94a1;font-style:italic}
.ovw .sights{flex:1 1 auto;min-width:0;color:var(--dim);font-size:12px;line-height:1.55;text-align:right}
@media(max-width:640px){
.ovw .row{flex-wrap:wrap;gap:4px 10px;padding:10px 14px}
.ovw .sights{text-align:left;width:100%;padding-top:2px;border-top:1px dashed var(--line);margin-top:2px;padding-left:0}}
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
.arlab{position:absolute;transform:translate(-50%,-50%);white-space:nowrap;background:rgba(18,22,28,.9);
 border:1px solid #5a6673;color:#e8ecf1;border-radius:8px;padding:2px 7px;font-size:11px;line-height:1.45;
 box-shadow:0 1px 5px rgba(0,0,0,.45)}
"""

JS_MAP = """
const COLORS=__COLORS__, CITY_CN=__CITYCN__, CITY_ZOOM=__CITYZOOM__;
const LAB=window.__LABELVAR__||{};
const map=L.map("map").setView([47.9,16.5],6);
L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
  {maxZoom:19,attribution:"Tiles &copy; Esri"}).addTo(map);

const groups={},layers={},bounds=[],placeM=[],cityM=[],cityPos={};
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
  cityPos[city]=[lat,lon];
  const cm=L.marker([lat,lon],{icon:L.divIcon({className:"",html:"",iconSize:[0,0]}),interactive:false,keyboard:false})
    .bindTooltip(CITY_CN[city]||city,{permanent:true,direction:"center",className:"clabel",opacity:1});
  cm.addTo(map); cityM.push(cm);
});

// ---------- 日程箭头：按日期从白到黑 ----------
const N2P=__NAME2PLACE__, ITINM=window.__ITINVAR__||{days:[]};
const DAYS=ITINM.days||[], UD=DAYS.map(function(d){return d.date}).filter(function(v,i,a){return a.indexOf(v)===i});
const cityArr=L.layerGroup(), innerArr={}, arrowBox=L.layerGroup().addTo(map);
function grayOf(t){const v=Math.round(242+(13-242)*t);return "rgb("+v+","+v+","+v+")";}
function dayColor(dt){const i=UD.indexOf(dt);return grayOf(UD.length<2?0:i/(UD.length-1));}
const CASE="#3a3f45";
function bearingOf(a,b){const P=Math.PI/180,l1=a[0]*P,l2=b[0]*P,dl=(b[1]-a[1])*P;
  const y=Math.sin(dl)*Math.cos(l2),x=Math.cos(l1)*Math.sin(l2)-Math.sin(l1)*Math.cos(l2)*Math.cos(dl);
  return (Math.atan2(y,x)/P+360)%360;}
// SVG 图形默认朝东，bearing 从正北起算 → CSS 旋转角要减 90
function rotOf(a,b){return bearingOf(a,b)-90;}
function along(a,b,t){return [a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t];}
function kmOf(a,b){const P=Math.PI/180;
  return Math.acos(Math.min(1,Math.sin(a[0]*P)*Math.sin(b[0]*P)+
    Math.cos(a[0]*P)*Math.cos(b[0]*P)*Math.cos((b[1]-a[1])*P)))*6371;}
function svgMark(a,b,d,fill,color,sw){
  return L.divIcon({className:"",iconSize:[18,18],iconAnchor:[9,9],
    html:'<svg width="18" height="18" viewBox="0 0 18 18" style="transform:rotate('+rotOf(a,b)+'deg);display:block">'+
      '<path d="'+d+'" fill="'+fill+'" stroke="'+color+'" stroke-width="'+sw+'" '+
      'stroke-linecap="round" stroke-linejoin="round"/></svg>'});
}
const TRI="M3,9 L13.5,3 L13.5,15 Z", CHEV="M5,3.5 L12,9 L5,14.5";
function drawSeg(lg,a,b,col){
  L.polyline([a,b],{color:CASE,weight:5,opacity:.5,interactive:false}).addTo(lg);
  L.polyline([a,b],{color:col,weight:3.4,opacity:.95,interactive:false}).addTo(lg);
  const long = kmOf(a,b) > 60;
  // 长线段铺 3 个人字箭头（描边 + 主色双层，黑白线都看得清），末端补一个实心三角
  (long?[.50,.66,.82]:[]).forEach(function(t){
    const p=along(a,b,t);
    L.marker(p,{icon:svgMark(a,b,CHEV,"none",CASE,3.6),interactive:false,keyboard:false}).addTo(lg);
    L.marker(p,{icon:svgMark(a,b,CHEV,"none",col,1.8),interactive:false,keyboard:false}).addTo(lg);
  });
  const q=along(a,b,long?.92:.78);
  L.marker(q,{icon:svgMark(a,b,TRI,col,CASE,3.2),interactive:false,keyboard:false}).addTo(lg);
  L.marker(q,{icon:svgMark(a,b,TRI,col,col,1),interactive:false,keyboard:false}).addTo(lg);
}
(function(){
  let prev=null;
  DAYS.forEach(function(d){
    const col=dayColor(d.date);
    // 城际：相邻两天城市变化即一条（洲际航班当天城市不变，天然被排除）
    if(prev && d.city!==prev && cityPos[prev] && cityPos[d.city]){
      const a=cityPos[prev], b=cityPos[d.city], t=d.train||{}, lg=L.layerGroup();
      drawSeg(lg,a,b,col);
      let txt = t.time ? "&#128646; "+t.time : "&#128646;";
      if(t.price && t.price!=="待查") txt += " · "+t.price+(t.price_state==="预估"?"（预估）":"");
      else if(t.time) txt += " · 价格待查";
      if(txt) L.marker(along(a,b,.28),{icon:L.divIcon({className:"",iconSize:[0,0],
        html:'<div class="arlab">'+txt+"</div>"}),interactive:false,keyboard:false}).addTo(lg);
      lg.addTo(cityArr);
    }
    // 城内：当天 items 按城市分组，顺序相连
    const seq=[]; (d.items||[]).forEach(function(nm){const p=N2P[nm]; if(p) seq.push(p);});
    let i=0;
    while(i<seq.length){
      const c=seq[i].city, run=[];
      while(i<seq.length && seq[i].city===c){run.push(seq[i]); i++;}
      // 同一城市（或当天短途外出，如布拉格→CK 当天往返）的连续景点才连箭头
      if(run.length>=2){
        innerArr[c]=innerArr[c]||L.layerGroup();
        const lg2=L.layerGroup();
        for(let j=0;j<run.length-1;j++)
          drawSeg(lg2,[run[j].lat,run[j].lon],[run[j+1].lat,run[j+1].lon],col);
        lg2.addTo(innerArr[c]);
      }
    }
    prev=d.city;
  });
})();
layers["日程箭头"]=arrowBox;
__JSHOTELSLAYER__
L.control.layers({},layers,{collapsed:window.innerWidth<600}).addTo(map);

function nearestCity(ll){
  let best=null,bd=Infinity;
  Object.keys(cityPos).forEach(function(c){
    const p=cityPos[c], d=Math.pow(p[0]-ll.lat,2)+Math.pow(p[1]-ll.lng,2);
    if(d<bd){bd=d;best=c;}
  });
  return best;
}
function applyZoom(){
  const cityMode = map.getZoom() < CITY_ZOOM;
  placeM.forEach(function(m){const t=m.getTooltip();const e=t&&t.getElement();if(e)e.style.display=cityMode?"none":"";});
  cityM.forEach(function(m){const t=m.getTooltip();const e=t&&t.getElement();if(e)e.style.display=cityMode?"":"none";});
  arrowBox.clearLayers();
  if(!map.hasLayer(arrowBox)) return;
  if(cityMode){ arrowBox.addLayer(cityArr); }
  else{
    const c=nearestCity(map.getCenter());
    if(c&&innerArr[c]) arrowBox.addLayer(innerArr[c]);
  }
}
map.on("zoomend",applyZoom);
map.on("moveend",applyZoom);
map.on("overlayadd overlayremove",applyZoom);

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
    const th = ph.length ? '<div class="thumbs">'+ph.slice(0,3).map(function(f){return '<img src="../'+f.file+'" loading="lazy">';}).join("")+"</div>" : "";
    const sess = n<=1 ? "" : (i < (n+1)/2 ? "上午" : "下午");
    const ampm = n>1 ? ' <span class="ampm">'+sess+"</span>" : "";
    return "<li>"+nm+ampm+th+"</li>";
  }).join("");
  return '<div class="day"><div class="hd"><span class="d">'+d.date+
    '</span><span class="w">周'+d.w+'</span><span class="s">住 '+d.stay+'</span></div>'+
    '<div class="bd">'+
    (d.transport?'<div class="tp"><b>'+(d.flight?"&#9992;":"&#128646;")+"</b> "+d.transport+"</div>":"")+
    (items?"<ul>"+items+"</ul>":"")+
    (d.note?'<div class="note">'+d.note+"</div>":"")+
    "</div></div>";
}).join("");
document.getElementById("stats").innerHTML = ITIN.stay.map(function(s){
  return '<div class="stat"><div class="n">'+s[1]+'</div><div class="l">'+s[0]+"</div></div>";
}).join("");
"""

JS_OVERVIEW = """
const CCN=__CITYCN__, CITYTK=__CITYTK__, ITINOV=window.__ITINVAR__;
document.getElementById("overview").innerHTML = ITINOV.days.map(function(d){
  const cA = d.flight||d.train;
  let seg="";
  if(d.flight){
    const f=d.flight;
    const tm=f.route?f.route:(f.dep+' '+f.time+' '+f.arr);
    seg='<span class="seg flt"><span class="ico">&#9992;</span><span class="tn">'+f.no+
      '</span><span class="tm">'+tm+'</span>'+
      (f.price?'<span class="tm"> · '+f.price+'</span>':'')+
      (f.pending?'<span class="tm pending">（'+f.pending+'）</span>':'')+'</span>';
  }else if(d.train){
    const t=d.train;
    const ico = /大巴|Bus|bus/.test(t.no) ? "&#128652;" : "&#128646;";
    seg='<span class="seg trn"><span class="ico">'+ico+'</span><span class="tn">'+t.no+
      '</span><span class="tm">'+t.dep+' '+t.time+' '+t.arr+'</span></span>';
  }
  // 箭头方向：city 是到达地 → 箭头在左（进入）；是出发地 → 箭头在右（离开）
  const tk = (CITYTK[d.city]||[]).map(function(s){return s.toUpperCase()});
  const hit = function(v){return tk.indexOf((v||"").toUpperCase()) >= 0 ||
    tk.some(function(t){return (v||"").toUpperCase().indexOf(t) >= 0});};
  let mv = "";
  if(cA){
    if(hit(cA.arr)) mv = " in";
    else if(hit(cA.dep)) mv = " out";
    else mv = d.flight ? " in" : " out";
  }
  return '<div class="row"><span class="dt">'+d.date+
    '<span class="w">周'+d.w+'</span></span>'+
    '<span class="city'+mv+'">'+(CCN[d.city]||d.city)+'</span>'+
    (seg?'<span class="seg">'+seg+"</span>":"")+
    '<span class="sights">'+d.items.join(" · ")+"</span></div>";
}).join("");
"""


def overview_block():
    """概览数据在客户端渲染；城市中文名复用 CITY_CN"""
    return (JS_OVERVIEW.replace("__CITYCN__", json.dumps(CITY_CN, ensure_ascii=False))
                       .replace("__CITYTK__", json.dumps(CITY_TOKENS, ensure_ascii=False)))


JS_HOTELS_LAYER = """
const hLayer=L.layerGroup(); let hn=0;
if(window.HOTELS){
  Object.keys(window.HOTELS).forEach(function(key){
    const rec=window.HOTELS[key];
    (rec.candidates||[]).forEach(function(h){
      hn++;
      L.circleMarker([h.lat,h.lon],{radius:5,color:"#fff",weight:1,fillColor:"#c98adf",fillOpacity:.85})
        .bindPopup("<b>"+h.name+"</b>"+(h.stars?" ★"+h.stars:"")
          +'<div class="note">'+(h.dist_sights?h.dist_sights+"m · ":"")+(h.website?"有官网":"")+"</div>")
        .addTo(hLayer);
    });
  });
}
layers["酒店 ("+hn+")"]=hLayer;
"""

JS_HOTELS = """
const HH=window.HOTELS||{}, CITYPHOTO=__CITYPHOTO__;
function kindCn(k){return k==="hotel"?"酒店":(k==="guest_house"?"民宿":(k==="hostel"?"青旅":"住宿"));}
function card(h,rec,key){
  const stars=h.stars?new Array(h.stars+1).join("★"):"";
  const addr=[h.street,h.postcode,h.city].filter(Boolean).join(" ");
  let ph="";
  if(h.photos&&h.photos.length){
    ph='<div class="thumbs">'+h.photos.slice(0,3).map(function(p){
      return '<img src="../pics/hotels/'+p.file.split("/").pop()+'" loading="lazy">';}).join("")+"</div>";
  }else{
    const cp=(window.PHOTOS&&window.PHOTOS[CITYPHOTO[key]])||[];
    if(cp.length) ph='<div class="thumbs">'+cp.slice(0,2).map(function(f){
      return '<img src="../'+f.file+'" loading="lazy">';}).join("")+'</div><div class="hm">（城区实景，非该酒店实拍）</div>';
  }
  const site=h.website?'<a href="'+h.website+'" target="_blank" rel="noopener">官网</a>':"";
  const bk='<a href="https://www.booking.com/search.html?ss='+encodeURIComponent(h.name+" "+rec.city)+'" target="_blank" rel="noopener">Booking 看价 →</a>';
  const osm='<a href="https://www.openstreetmap.org/?mlat='+h.lat+'&mlon='+h.lon+'#map=18/'+h.lat+'/'+h.lon+'" target="_blank" rel="noopener">OSM 定位</a>';
  return '<div class="hcard"><div class="hn">'+h.name+'<span class="hstars">'+stars+"</span></div>"
    +'<div class="hm">'+kindCn(h.kind)+(h.dist_sights?" · 距你的景点群 "+h.dist_sights+"m":"")
    +(h.dist_station!=null?" · 距最近车站 "+h.dist_station+"m":"")+"</div>"
    +(addr?'<div class="hm">'+addr+(h.phone?" · "+h.phone:"")+"</div>":"")
    +'<div class="ha">'+site+bk+osm+"</div>"+ph+"</div>";
}
document.getElementById("hotels").innerHTML = Object.keys(HH).map(function(key){
  const rec=HH[key], cands=rec.candidates||[];
  const picks=cands.filter(function(h){return (rec.picks||[]).indexOf(h.name)>=0;});
  const rest=cands.filter(function(h){return (rec.picks||[]).indexOf(h.name)<0;});
  return '<div class="hsec"><h3>'+rec.city+"　OSM 共 "+rec.total+" 家 · 下列 "+cands.length+" 家按位置排序</h3>"
    +picks.map(function(h){return card(h,rec,key);}).join("")
    +(rest.length?'<button class="more" data-k="'+key+'">展开另外 '+rest.length+' 家 ▾</button>'
      +'<div class="morelist" id="ml-'+key+'">'+rest.map(function(h){
        return h.name+(h.stars?" ★"+h.stars:"")+(h.dist_sights?" · "+h.dist_sights+"m":"");}).join("<br>")
      +"</div>":"")
    +"</div>";
}).join("");
Array.prototype.forEach.call(document.querySelectorAll(".more"),function(b){
  b.onclick=function(){document.getElementById("ml-"+b.getAttribute("data-k")).classList.toggle("on");};
});
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
<div class="sub">__HEAD__</div>
<div class="sub" style="margin-top:9px"><span class="badge" id="ver"></span></div></header>
<h2>取舍</h2><div class="card">__TRADEOFF__</div>
<h2>住宿分配</h2><div class="grid" id="stats"></div>
<h2>地图（右上角 ⛶ 可全屏）</h2><div id="map"></div>
<h2>行程一览</h2><div class="ovw" id="overview"></div>
<h2>逐日行程</h2><div id="days"></div><h2>酒店候选（点图层控件可勾选「酒店」）</h2><div id="hotels"></div>
__HIST__
<footer><div id="verfoot"></div><div style="margin-top:6px">__TITLE__ · 草稿</div></footer>
</div>
<script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js"></script>
__DATA__
<script>__JSMAP____JSDAYS____JSOVW____JSHOTELS____JSVER__</script>
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
<h2>航班（方案 C / D）</h2>
<div class="card"><div style="font-weight:600">去程 · 1/23（六）</div>
<div class="sub">广州 CAN 01:55 → 布达佩斯 BUD 07:10 · 南航 CZ649 · 实测直飞 ¥3,287/人</div></div>
<div class="card"><div style="font-weight:600">回程 · 2/1（一）→ 2/2（二）</div>
<div class="sub">布拉格 PRG 13:00 → 北京 PEK 次日 05:15（中转 3h15m）→ 广州 CAN 12:00 ·
海航联程 · <b>携程实测 ¥2,379/人</b></div></div>
<div class="card"><div class="sub" style="color:#9aa5b1">已否决的方案 A / B 用的是另一套：深圳 SZX 01:45 → 维也纳
HU789 ¥3,357 / 布达佩斯 BUD 11:45 → 广州 CZ650 ¥3,313（均为直飞）</div></div>
<footer><div id="verfoot"></div><div style="margin-top:6px">行程草稿 · 地图数据 OpenStreetMap</div></footer>
</div>
<script src="data/version.js"></script>
<script>__JSVER__</script>
</body></html>"""


# ---------- 版本快照 ----------
def git_count():
    import subprocess
    r = subprocess.run(["git", "-C", str(REPO), "rev-list", "--count", "HEAD"],
                       capture_output=True, text=True)
    return int(r.stdout.strip() or 0)


def head_sha():
    import subprocess
    r = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
                       capture_output=True, text=True)
    return r.stdout.strip()


def now_str():
    from datetime import datetime, timedelta, timezone
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")


def data_block(k, lid, inline=False, ver=None, note=""):
    """数据 <script> 片段。inline=True 时把数据烘进页面，用于历史快照（与后续版本解耦）"""
    if inline:
        frozen = {"version": f"v{ver}", "built_at": now_str(),
                  "commit": head_sha(), "note": note}
        return ("\n".join([
            "<script>window.PLACES=" + json.dumps(places, ensure_ascii=False) + ";</script>",
            "<script>window.PHOTOS=" + json.dumps(WEB_PHOTOS, ensure_ascii=False) + ";</script>",
            f"<script>window.LABELS_{k}=" + json.dumps(LABELS[k], ensure_ascii=False) + ";</script>",
            f"<script>window.ITIN_{k}=" + json.dumps(itins[k], ensure_ascii=False) + ";</script>",
            "<script>window.HOTELS=" + json.dumps(HOTELS, ensure_ascii=False) + ";</script>",
            "<script>window.VERSION=" + json.dumps(frozen, ensure_ascii=False) + ";</script>",
        ]))
    return "\n".join([
        '<script src="../data/places.js"></script>',
        '<script src="../data/photos.js"></script>',
        '<script src="../data/hotels.js"></script>',
        f'<script src="../data/labels_{lid}.js"></script>',
        f'<script src="../data/itinerary_{lid}.js"></script>',
        '<script src="../data/version.js"></script>',
    ])


def hist_block(lid):
    """列出该方案已存档的历史版本"""
    files = sorted((REPO / lid).glob("v*.html"),
                   key=lambda p: int(p.stem[1:]) if p.stem[1:].isdigit() else 0,
                   reverse=True)
    if not files:
        return ""
    links = "".join(f'<a href="{p.name}">{p.stem}</a>' for p in files)
    return f'<h2>历史版本</h2><div class="card hist">{links}</div>'


def build_pages():
    ver = git_count() + 1
    note = BUILD_NOTE
    for k, itin in itins.items():
        lid = k.lower()
        trade = "".join(f'<div class="pros">+ {x}</div>' for x in itin["pros"]) + \
                "".join(f'<div class="cons">− {x}</div>' for x in itin["cons"])
        d0, d1 = itin["days"][0]["date"], itin["days"][-1]["date"]
        n = sum(s[1] for s in itin["stay"])
        head = f"<b>{d0} – {d1}</b> · {n} 晚 {n + 1} 天 · {itin['route']}"
        jsmap = (JS_MAP.replace("__COLORS__", json.dumps(COLORS))
                       .replace("__CITYCN__", json.dumps(CITY_CN, ensure_ascii=False))
                       .replace("__CITYZOOM__", str(CITY_ZOOM))
                       .replace("__LABELVAR__", f"LABELS_{k}")
                       .replace("__ITINVAR__", f"ITIN_{k}")
                       .replace("__NAME2PLACE__", json.dumps(name2place, ensure_ascii=False))
                       .replace("__JSHOTELSLAYER__", JS_HOTELS_LAYER))
        jsdays = (JS_DAYS.replace("__NAME2ID__", json.dumps(name2id, ensure_ascii=False))
                         .replace("__ITINVAR__", f"ITIN_{k}"))
        jsovw = overview_block().replace("__ITINVAR__", f"ITIN_{k}")
        jshotels = JS_HOTELS.replace("__CITYPHOTO__", json.dumps(CITY_PHOTO, ensure_ascii=False))

        def render(inline, hist):
            return (PLAN_TPL.replace("__TITLE__", itin["title"])
                            .replace("__SUBTITLE__", itin["subtitle"])
                            .replace("__HEAD__", head)
                            .replace("__TRADEOFF__", trade)
                            .replace("__LID__", lid)
                            .replace("__CSS__", CSS)
                            .replace("__HIST__", hist)
                            .replace("__DATA__", data_block(k, lid, inline, ver, note))
                            .replace("__JSMAP__", jsmap)
                            .replace("__JSDAYS__", jsdays)
                            .replace("__JSOVW__", jsovw)
                            .replace("__JSHOTELS__", jshotels)
                            .replace("__JSVER__", JS_VER))

        d = REPO / lid
        d.mkdir(parents=True, exist_ok=True)
        # 历史快照：数据全部烘进页面，之后改数据也不会影响它
        (d / f"v{ver}.html").write_text(render(True, ""), encoding="utf-8")
        # 最新版
        (d / "index.html").write_text(render(False, hist_block(lid)), encoding="utf-8")
        print(f"  {lid}/index.html  +  {lid}/v{ver}.html（快照）")

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
