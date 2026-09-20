# 2027-1 奥匈捷之旅 · 行程规划站

2027 年 1–2 月「我和灯灯」的中欧行程规划 + 可视化网站。
纯静态站点，GitHub Pages 托管。

- 线上地址：https://jack975645419.github.io/2027-1-au-hu-cz-trip/
- 现行方案：`/d/` —— 广州 → 布达佩斯 2 晚 → 维也纳 3 晚 → 克鲁姆洛夫 1 晚 → 布拉格 3 晚 → 广州（9 晚 10 天）
- 需求与规划文档母文件夹：`D:\2026年我和灯灯\2027-1奥匈捷之旅\`（本仓库 `/planning/` 是它的归档副本）

---

## 一、技术栈

### 前端（站点本体）

| 层 | 选型 | 说明 |
|---|---|---|
| 地图库 | **Leaflet 1.9.4** | 经 **jsdelivr** CDN 引入（`leaflet.css` + `leaflet.js`）；不用 unpkg，国内不稳 |
| 底图瓦片 | **Esri World Street Map**<br>`https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}` | **免 Key、免费额度**；v12 起固定这一层，**不提供底图切换** |
| 框架 | **无**（原生 HTML + CSS + 内联 JS） | 无 React/Vue、无打包器、无 npm 依赖 |
| 数据加载 | `data/*.js` 以全局变量注入<br>（`window.PLACES` / `PHOTOS` / `HOTELS` / `LABELS` / `ITINERARY` / `TRANSIT` / `VERSION`） | 不用 `fetch` 读 JSON：本地 `file://` 打开也不受 CORS 限制 |
| 箭头/标记 | 自绘 SVG + `L.divIcon` | 没引 `polylineDecorator` 等插件，零额外依赖、零 CDN 失败风险 |

**为什么底图是 Esri 而不是 OSM**：`tile.openstreetmap.org` 在国内被墙，CARTO 时好时坏，Esri 最稳。这是踩过坑后定下来的，别改回去。

### 构建侧（脚本）

- **Python 3.10**（实测 3.10.4），尽量只用标准库
- **Pillow**：把景点图压到宽 900px / quality 82
- **Playwright（Python，Chromium）**：两处用到
  1. `track_price.py` / `scan.py` 抓 Google Flights 比价
  2. 每次构建后跑冒烟校验（检查 `pageerror`、地图元素数量）
- 无 `requests`：所有 HTTP 用 `urllib.request`

### 数据来源（外部接口）

| 用途 | 接口 | Key |
|---|---|---|
| 景点坐标 | **Nominatim**（`nominatim.openstreetmap.org/search`） | 免 Key，需带 UA，限速 1 req/s |
| 酒店候选、地铁站 | **Overpass API**（`overpass-api.de` → `overpass.kumi.systems` → `maps.mail.ru` 镜像依次兜底） | 免 Key |
| 景点配图 | **Wikimedia Commons API**（`commons.wikimedia.org/w/api.php`）为主 | 免 Key，会 403 限流 |
| 配图补位 | **Unsplash**（`api.unsplash.com/search/photos`） | 需 Access Key，存 Windows 用户环境变量 `UNSPLASH_ACCESS_KEY`，**不进仓库** |
| 机票比价 | **Google Flights**（`google.com/travel/flights`，Playwright 抓页面） | 免 Key，非官方接口，页面改版即失效 |

---

## 二、目录结构

```
2027-1-au-hu-cz-trip/
├── index.html          方案选择页（现只链 /d/）
├── d/index.html        ★ 现行唯一方案页（v22），v14~v22 历史快照同目录留存
├── a/ b/ c/ e/         历史方案页（已停止更新，仅存档）
├── data/               渲染产物，全部是 .js 全局变量
│   ├── places.js       40 个景点（坐标 / 简介 / 建议时长 / 预约信息）
│   ├── photos.js       76 张图的署名与授权
│   ├── hotels.js       OSM 抓的酒店候选（每城推荐 6 家）
│   ├── itinerary_*.js  逐日行程（按方案分文件）
│   ├── labels_*.js     地图标注（日期 + 上下午）
│   ├── transit.js      机场 / 火车站 / 大巴站 / 相关地铁站
│   └── version.js      版本号 · 更新时间 · commit · 改动说明
├── pics/               压缩后的景点图（宽 900px）
├── version.json        版本信息（JSON 版，供脚本读）
└── planning/           规划档归档：md 文档 + scripts/ + data/ + pictures/ + snapshots/
```

> `planning/` 是**源**，`data/` + `pics/` + `*.html` 是**产物**。改数据改 `planning/data/`，再跑 `build_site.py` 重新渲染，不要手改产物。

---

## 三、脚本

全部在 `planning/scripts/`：

| 脚本 | 作用 |
|---|---|
| `build_site.py` | 渲染整站 → 仓库根目录（含图片压缩） |
| `build_transit.py` | 生成 `transit.json`（机场/车站 + Overpass 挑相关地铁站） |
| `geocode.py` | Nominatim 把景点名转坐标 → `places.json` |
| `fetch_photos.py` | Commons 抓图，限流时降级 Unsplash → `pictures/` + `photos.json` |
| `fetch_hotels.py` | Overpass 抓酒店候选 → `hotels.json` |
| `track_price.py` | 每周抓价，写 `data/prices.csv` |
| `scan.py` | 临时比价，不写历史 |
| `version.py` | 生成版本号 + 时间戳（**提交前跑**） |
| `config.json` | 要追踪的航段配置 |

```bash
cd D:\Proj\2027-1-au-hu-cz-trip\planning\scripts
python build_site.py "改动说明"     # 重建整站
python version.py "改动说明"         # 打版本号
python track_price.py               # 抓一次机票价
python track_price.py --show        # 看价格历史
python scan.py CAN BUD 2027-01-26   # 临时查某一天
python fetch_photos.py              # 补抓缺失的图
```

**发版流程**：改 `planning/data/` → `build_site.py` → Playwright 冒烟验证 → `version.py "说明"` → `git add/commit/push`

---

## 四、地图实现要点

- **缩放分级**：阈值 `CITY_ZOOM = 11`。`< 11` 显示城市名 + 城际箭头；`≥ 11` 显示景点名 + 当前城市城内箭头。
- **日程箭头**：城际段按 `itineraries.json` 相邻两天城市变化连线；城内段按当天 `items` 顺序连线。洲际航班（CAN⇄欧洲）**不画连线**，只在城市点旁挂 ✈ 标。
- **每日一色**：12 天取 12 色循环（`#d81e5b` … `#ae3ec9`），箭头、地图小卡片、城内连线共用；底色深浅自动切换文字颜色保证可读。早期用过白→黑灰阶，用户反馈不好看，已废弃。
- **箭头朝向**：旋转角 = 方位角 − 90（漏减会整体歪 90°）。
- **交通点**：机场 / 火车站 / 大巴站常显；相关地铁站缩放到城市级别才显示。
- **图层开关**两项：「交通站点」（机场/火车站/大巴站/地铁站，默认开）+「推荐酒店」（默认关）；景点层、日程箭头常开。
- 连线是**示意直线**，非真实路径规划。

---

## 五、已知坑

- 一个 `<script>` 块里一处语法错误 → **整页白屏**。所以每次构建后必须 Playwright 验证再推送。
- Wikimedia Commons 会 403 限流，脚本已自动降级 Unsplash。
- Nominatim 会把小镇名匹配到行政中心，偏几公里（哈尔施塔特/圣沃尔夫冈曾偏 4km 落在湖面），需手工校正。
- Overpass 镜像覆盖不全（`overpass.osm.ch` 只有瑞士），已加多镜像兜底 + 与旧数据**合并而非覆盖**。
- Unsplash Demo 模式限 50 次/小时；Application ID / Secret Key 都不需要，也别存。
- OSM 酒店数据**没有价格和评分**，只有名称/坐标/星级/官网，下单需自己去 Booking 看。

---

## 六、待办

详见 `planning/旅行需求.md` 第七节。近期几项：

- [ ] 补 CK 两张缺图（Egon Schiele 艺术中心、Seidel 照相馆）
- [ ] 2026-10：查维也纳→CK、CK→布拉格冬季大巴班次（首末班车时刻是关键）
- [ ] 回程联程票尽快下单（春运高峰），出票后补记前后程航班号
- [ ] 11 月：冬季列车/大巴开票后把票价从「预估」改「实测」
- [ ] 12 月初：金色大厅 1 月场次开售即抢（musikverein.at，不可退）
