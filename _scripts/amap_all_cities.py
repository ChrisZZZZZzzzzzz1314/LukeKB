#!/usr/bin/env python3
"""
全国省会城市4A景区批量搜索
31个省会/直辖市 × 5类关键词
"""
import json, subprocess, time, re
from pathlib import Path

AMAP_KEY = "b78a178a71c46c9425d45dab9d5c1a2a"
BASE_DIR = Path.home() / "Documents" / "LukeKB"
OUT_FILE = BASE_DIR / "_scripts" / "4a_all_cities.json"

# 31省会+直辖市 × 5类关键词
CITIES_KEYWORDS = [
    # 华北
    ("北京", ["欢乐谷", "故宫", "长城", "颐和园", "天坛"]),  # 已知的
    ("天津", ["古文化街", "盘山", "黄崖关"]),
    ("石家庄", ["西柏坡", "嶂石岩", "正定古城"]),
    ("太原", ["晋祠", "永祚寺", "蒙山"]),
    ("呼和浩特", ["昭君墓", "大召寺", "希拉穆仁"]),
    # 东北
    ("沈阳", ["故宫", "张氏帅府", "棋盘山"]),
    ("长春", ["伪满皇宫", "净月潭", "长影世纪城"]),
    ("哈尔滨", ["太阳岛", "冰雪大世界", "中央大街"]),
    ("大连", ["老虎滩", "金石滩", "星海广场"]),
    # 华东
    ("上海", ["海昌海洋公园", "野生动物园", "科技馆"]),
    ("南京", ["中山陵", "夫子庙", "总统府"]),
    ("杭州", ["西湖", "宋城", "灵隐寺", "西溪湿地"]),
    ("苏州", ["拙政园", "周庄", "同里", "太湖"]),
    ("无锡", ["灵山大佛", "鼋头渚", "三国城"]),
    ("常州", ["恐龙园", "天目湖", "南山竹海"]),
    ("扬州", ["瘦西湖", "个园", "大明寺"]),
    ("宁波", ["溪口", "东钱湖", "象山"]),
    ("温州", ["雁荡山", "楠溪江"]),
    ("合肥", ["三河古镇", "包公园"]),
    ("黄山", ["黄山", "宏村", "西递"]),
    ("厦门", ["鼓浪屿", "集美学村", "方特"]),
    ("福州", ["三坊七巷", "武夷山", "太姥山"]),
    ("南昌", ["滕王阁", "庐山", "瑶湖"]),
    ("济南", ["趵突泉", "大明湖", "千佛山"]),
    ("青岛", ["崂山", "栈桥", "金沙滩"]),
    ("威海", ["刘公岛", "成山头"]),
    # 华中
    ("武汉", ["黄鹤楼", "东湖", "欢乐谷"]),
    ("长沙", ["岳麓山", "橘子洲", "马王堆"]),
    ("郑州", ["少林寺", "嵩山", "方特"]),
    ("洛阳", ["龙门石窟", "白马寺", "牡丹园"]),
    # 华南
    ("广州", ["长隆", "白云山", "陈家祠"]),
    ("深圳", ["世界之窗", "欢乐谷", "东部华侨城"]),
    ("珠海", ["海洋王国", "情侣路", "横琴"]),
    ("桂林", ["漓江", "阳朔", "象山"]),
    ("南宁", ["青秀山", "德天瀑布"]),
    ("海口", ["假日海滩", "火山口"]),
    ("三亚", ["天涯海角", "南山寺", "亚龙湾"]),
    # 西南
    ("成都", ["大熊猫基地", "青城山", "武侯祠"]),
    ("重庆", ["洪崖洞", "解放碑", "武隆"]),
    ("贵阳", ["黄果树", "黔灵山", "青岩古镇"]),
    ("昆明", ["石林", "滇池", "世博园"]),
    ("丽江", ["古城", "玉龙雪山", "泸沽湖"]),
    ("拉萨", ["布达拉宫", "大昭寺", "纳木错"]),
    # 西北
    ("西安", ["兵马俑", "华清池", "大唐芙蓉园", "城墙"]),
    ("兰州", ["黄河铁桥", "白塔山", "甘肃省博物馆"]),
    ("西宁", ["青海湖", "塔尔寺"]),
    ("银川", ["沙湖", "西夏王陵"]),
    ("乌鲁木齐", ["天山", "大巴扎", "南山"]),
]

CATEGORY_MAP = {
    "主题乐园": ["乐园", "欢乐谷", "方特", "恐龙园", "海洋王国", "世界之窗", "动物园", "嬉戏谷", "休博园"],
    "城市公园": ["公园", "湖", "广场", "湿地", "栈桥"],
    "人文山水": ["古城", "古镇", "文化", "博物馆", "纪念馆", "故居", "遗址", "古迹", "王府", "陵", "石窟", "寺庙", "宫"],
    "自然风光": ["山", "峡", "江", "河", "瀑", "林", "岛", "海", "沙漠", "草原", "冰川"],
    "宗教文化": ["寺", "庙", "观", "塔", "佛", "教", "清真"],
}

def amap_search(city, keyword):
    kw_encoded = keyword.replace(" ", "%20")
    url = f"https://restapi.amap.com/v3/place/text?keywords={kw_encoded}&city={city}&key={AMAP_KEY}&offset=5&output=json"
    r = subprocess.run(["curl", "-s", url], capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except:
        return {}

def geo_code(name):
    url = f"https://restapi.amap.com/v3/geocode/geo?address={name}&key={AMAP_KEY}"
    r = subprocess.run(["curl", "-s", url], capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
        gc = d.get("geocodes", [])
        if gc:
            loc = gc[0].get("location", "").split(",")
            return float(loc[0]) if len(loc) > 0 else 0, float(loc[1]) if len(loc) > 1 else 0
    except:
        pass
    return None, None

def classify(name):
    for cat, kws in CATEGORY_MAP.items():
        for kw in kws:
            if kw in name:
                return cat
    return "其他"

def main():
    seen = {}
    results = []
    count = 0

    print("全国城市4A景区批量搜索")
    print("="*50)

    for city, keywords in CITIES_KEYWORDS:
        for kw in keywords:
            d = amap_search(city, kw)
            pois = d.get("pois", [])
            found = 0
            for p in pois:
                biz = p.get("biz_ext", {}) or {}
                lvl = biz.get("level", "") if isinstance(biz, dict) else ""
                n = p.get("name", "")
                loc_str = p.get("location", "")
                rating = biz.get("rating", "") if isinstance(biz, dict) else ""
                t = p.get("type", "")

                # 过滤4A/5A
                if lvl not in ("AAAA", "AAAAA", "4A", "5A"):
                    continue
                if not n or n in seen:
                    continue

                seen[n] = True
                loc = [float(x) for x in loc_str.split(",")] if loc_str else [0, 0]
                province = p.get("pname", "").replace("市", "")
                cat = classify(n)

                spot = {
                    "name": n,
                    "city": city,
                    "province": province,
                    "level": lvl.replace("AAAA", "4A").replace("AAAAA", "5A"),
                    "location": loc,
                    "rating": rating,
                    "category": cat,
                    "type": t,
                    "ticket": biz.get("cost", "") if isinstance(biz, dict) else "",
                    "tips": f"来源:{city}+{kw}",
                }
                results.append(spot)
                found += 1
                count += 1

            if found:
                print(f"  [{city}] {kw}: +{found} → 累计{count}")
            time.sleep(0.25)

    print(f"\n共找到 {len(results)} 个4A+景区")

    # 去重（同名保留第一个）
    uniq = {}
    for s in results:
        if s["name"] not in uniq:
            uniq[s["name"]] = s
    results = list(uniq.values())
    print(f"去重后: {len(results)} 个")

    # 保存
    OUT_FILE.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"保存: {OUT_FILE}")

    # 写markdown入库
    gen = 0
    for spot in results:
        name = spot["name"]
        cat = spot["category"]
        cat_dir = BASE_DIR / "scenic" / "4A" / cat
        cat_dir.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^\w\u4e00-\u9fff-]", "_", name)
        fp = cat_dir / f"4A-{safe}.md"
        if fp.exists() and len(fp.read_text(errors="ignore")) > 600:
            continue
        ticket = spot.get("ticket", "待查") or "待查"
        loc = spot["location"]
        open_t = spot.get("tips", "全天")
        content = f"""---
name: {name}
level: {spot['level']}
level_year: ""
province: {spot['province']}
city: {spot['city']}
category: {cat}
location: [{loc[0]},{loc[1]}]
coord_src: amap
free: false
ticket: "{ticket}"
open_time: "全天"
rating: "{spot['rating']}"
tags: [{cat},4A]
source: amap-city-scan
status: generated
generated: 2026-06-24
---

# {name}

> 分类：{cat} | 等级：{spot['level']}{f" | 评分：{spot['rating']}" if spot['rating'] else ""} | 省份：{spot['province']}

## 基础信息

| 项目 | 内容 |
|------|------|
| 景区名称 | {name} |
| 等级 | {spot['level']} |
| 所在城市 | {spot['city']} |
| 所属省份 | {spot['province']} |
| 参考票价 | ¥{ticket} |
| 坐标 | {loc[0]:.4f},{loc[1]:.4f} |

## 打卡点推荐

| # | 景点 | 游览时长 | 看点 |
|---|------|----------|------|
| 1 | | 40分钟 | |
| 2 | | 30分钟 | |
| 3 | | 30分钟 | |

## 人文故事

（待补充）

## 核心美食

| 菜品 | 价格 | 推荐理由 |
|------|------|----------|
| | ¥ | |

## 游玩建议

✅ 
⚠️
"""
        fp.write_text(content, encoding="utf-8", errors="ignore")
        gen += 1

    print(f"新增入库: {gen} 个")

    # 分类统计
    by_cat = {}
    for s in results:
        c = s["category"]
        by_cat.setdefault(c, []).append(s["name"])
    print("\n分类统计:")
    for c, names in sorted(by_cat.items(), key=lambda x: -len(x[1])):
        print(f"  {c}: {len(names)}个")

if __name__ == "__main__":
    main()
