#!/usr/bin/env python3
"""高德批量搜索4A景区POI + 生成入库"""
import json, subprocess, time, re
from pathlib import Path

AMAP_KEY = "b78a178a71c46c9425d45dab9d5c1a2a"
BASE_DIR = Path.home() / "Documents" / "LukeKB"

# 搜索城市+关键词列表
SEARCHES = [
    ("北京", "欢乐谷"), ("北京", "雁栖湖"),
    ("广州", "长隆"), ("广州", "塔"),
    ("深圳", "世界之窗"), ("深圳", "欢乐谷"), ("深圳", "华侨城"),
    ("杭州", "宋城"), ("杭州", "西溪湿地"),
    ("常州", "恐龙园"),
    ("珠海", "海洋王国"),
    ("成都", "欢乐谷"),
    ("重庆", "欢乐谷"),
    ("武汉", "欢乐谷"),
    ("天津", "欢乐谷"),
    ("上海", "海昌海洋公园"),
    ("厦门", "方特"),
    ("宁波", "方特东方神画"),
    ("郑州", "方特"),
    ("沈阳", "方特"),
    ("西安", "大唐芙蓉园"), ("西安", "华清池"),
    ("南京", "欢乐谷"), ("南京", "中山陵"),
    ("苏州", "乐园"), ("苏州", "周庄"),
    ("长沙", "欢乐谷"),
    ("青岛", "乐园"),
    ("大连", "老虎滩"),
    ("哈尔滨", "太阳岛"),
    ("昆明", "石林"),
    ("丽江", "古城"),
    ("三亚", "天涯海角"),
    ("南昌", "滕王阁"),
    ("贵阳", "黄果树"),
    ("太原", "晋祠"),
    ("济南", "趵突泉"),
    ("南宁", "青秀山"),
    ("海口", "假日海滩"),
    ("东莞", "梦幻百花洲"),
    ("佛山", "长鹿"),
]

def amap_search(city, keyword):
    url = f"https://restapi.amap.com/v3/place/text?keywords={keyword}&city={city}&key={AMAP_KEY}&offset=5&output=json"
    r = subprocess.run(["curl", "-s", url], capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except:
        return {}

def get_location(name):
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
    return 0, 0

def classify(name):
    if any(kw in name for kw in ["乐园", "欢乐谷", "方特", "恐龙园", "海洋王国", "世界之窗", "宋城", "动物园"]):
        return "主题乐园"
    if any(kw in name for kw in ["塔", "公园", "湖", "园", "广场", "湿地"]):
        return "城市公园"
    if any(kw in name for kw in ["古城", "古镇", "大唐", "芙蓉园"]):
        return "人文山水"
    return "其他"

def generate_4a_md(spot):
    name = spot["name"]
    city = spot["city"]
    province = spot["province"]
    ticket = spot.get("ticket", "待查")
    open_t = spot.get("open", "08:00-18:00")
    loc = spot.get("location", [0, 0])
    cat = spot.get("category", classify(name))
    level = spot.get("level", "4A")
    tips = spot.get("tips", "")
    rating = spot.get("rating", "")

    cat_dir = BASE_DIR / "scenic" / "4A" / cat
    cat_dir.mkdir(parents=True, exist_ok=True)

    safe = re.sub(r"[^\w\u4e00-\u9fff-]", "_", name)
    fp = cat_dir / f"4A-{safe}.md"

    if fp.exists() and len(fp.read_text(errors="ignore")) > 800:
        return "skipped", name

    content = f"""---
name: {name}
level: {level}
level_year: ""
province: {province}
city: {city}
category: {cat}
location: [{loc[0]},{loc[1]}]
coord_src: amap
free: false
ticket: "{ticket}"
open_time: "{open_t}"
rating: "{rating}"
tags: [{cat},4A]
source: amap-poi
status: generated
generated: 2026-06-24
---

# {name}

> 分类：{cat} | 等级：{level} | 省份：{province}{f" | 评分：{rating}" if rating else ""}

## 基础信息

| 项目 | 内容 |
|------|------|
| 景区名称 | {name} |
| 等级 | {level} |
| 所在城市 | {city} |
| 所属省份 | {province} |
| 参考票价 | ¥{ticket} |
| 开放时间 | {open_t} |
| 坐标 | {loc[0]},{loc[1]} |

{tips}

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
✅ 
⚠️
"""
    fp.write_text(content, encoding="utf-8", errors="ignore")
    return "generated", name

def main():
    all_spots = []
    seen = set()

    print("高德POI批量搜索\n" + "="*50)

    for city, kw in SEARCHES:
        d = amap_search(city, kw)
        pois = d.get("pois", [])
        found = 0
        for p in pois:
            biz = p.get("biz_ext", {}) or {}
            lvl = biz.get("level", "") if isinstance(biz, dict) else ""
            n = p.get("name", "")
            loc_str = p.get("location", "")
            loc = [float(x) for x in loc_str.split(",")] if loc_str else [0, 0]
            rating = biz.get("rating", "") if isinstance(biz, dict) else ""
            t = p.get("type", "")

            # 只取4A/5A级别
            if lvl in ("AAAA", "AAAAA", "4A", "5A") and n not in seen:
                seen.add(n)
                cat = classify(n)
                spot = {
                    "name": n, "city": city,
                    "province": p.get("pname", "").replace("市",""),
                    "level": lvl.replace("AAAA","4A").replace("AAAAA","5A"),
                    "location": loc, "rating": rating,
                    "type": t, "category": cat,
                    "ticket": biz.get("cost", "待查") if isinstance(biz, dict) else "待查",
                    "tips": f"类型: {t[:40]}"
                }
                all_spots.append(spot)
                found += 1

        print(f"[{city}] {kw}: 找到{found}个")
        time.sleep(0.3)

    print(f"\n共找到 {len(all_spots)} 个4A+景区")

    # 生成文件
    gen, skip = 0, 0
    for spot in all_spots:
        status, name = generate_4a_md(spot)
        print(f"  [{status}] {name}")
        if status == "generated": gen += 1
        else: skip += 1

    print(f"\n完成: {gen} 生成, {skip} 跳过")

    # 保存搜索结果
    out = BASE_DIR / "_scripts" / "4a_amap_results.json"
    out.write_text(json.dumps(all_spots, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"结果已保存: {out}")

if __name__ == "__main__":
    main()
