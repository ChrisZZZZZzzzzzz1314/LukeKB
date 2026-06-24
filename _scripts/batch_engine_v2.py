#!/usr/bin/env python3
"""
Luke景区KB全量生成引擎 v2
==================
统一队列: 5A(363) + 4A(123+) = 全部景区
统一脚本: 搜索+生成入库一体

用法:
  python3 batch_engine_v2.py [批次大小] [最大批次]
  默认: 50个/批, 无限循环直到队列空
"""
import json, os, sys, time, re
from pathlib import Path

KB_DIR = Path.home() / "Documents" / "LukeKB"
QUEUE_FILE = KB_DIR / "_scripts" / "all_attractions_queue.json"
PROGRESS_FILE = KB_DIR / "_scripts" / "batch_progress_v2.json"
AMAP_KEY = "b78a178a71c46c9425d45dab9d5c1a2a"

BATCH_SIZE = int(sys.argv[1]) if len(sys.argv) > 1 else 50
MAX_BATCHES = int(sys.argv[2]) if len(sys.argv) > 2 else 9999

CATEGORY_MAP = {
    "主题乐园": ["乐园", "欢乐谷", "方特", "恐龙园", "海洋王国", "世界之窗", "动物园", "嬉戏谷", "休博园", "极地", "探险"],
    "城市公园": ["公园", "广场", "塔", "湖", "湿地"],
    "人文山水": ["古城", "古镇", "文化", "博物馆", "纪念馆", "故居", "遗址", "古迹", "王府", "陵", "宫"],
    "自然风光": ["山", "峡", "江", "河", "瀑", "林", "岛", "海", "沙漠", "草原", "冰川", "地质"],
    "宗教文化": ["寺", "庙", "观", "塔", "佛", "教", "清真", "石窟"],
    "红色旅游": ["革命", "纪念馆", "红色", "长征", "延安", "井冈山", "西柏坡"],
}

def classify(name):
    for cat, kws in CATEGORY_MAP.items():
        for kw in kws:
            if kw in name:
                return cat
    return "其他"

def amap_geocode(name):
    import subprocess
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

def get_progress():
    if Path(PROGRESS_FILE).exists():
        return json.loads(Path(PROGRESS_FILE).read_text())
    return {"done": [], "failed": []}

def save_progress(progress):
    Path(PROGRESS_FILE).write_text(json.dumps(progress, ensure_ascii=False, indent=2))

def generate_md(spot):
    name = spot["name"]
    level = spot.get("level", "4A")
    province = spot.get("province", "")
    city = spot.get("city", "")
    cat = spot.get("category", classify(name))
    source = spot.get("source", "")

    # 分类目录
    level_dir = "5A" if level == "5A" else "4A"
    cat_dir = KB_DIR / "scenic" / level_dir / cat
    cat_dir.mkdir(parents=True, exist_ok=True)

    safe = re.sub(r"[^\w\u4e00-\u9fff-]", "_", name)
    file_path = cat_dir / f"{level_dir}-{safe}.md"

    # 已有内容则跳过（已精细化的不覆盖）
    if file_path.exists():
        existing = file_path.read_text(errors="ignore")
        if len(existing) > 1000 and ("打卡点" in existing or "## 人文故事" in existing):
            return "skipped", name

    # 坐标
    loc = spot.get("location", [0, 0])
    if not loc or loc[0] == 0:
        loc = [None, None]

    ticket = spot.get("ticket", "待查") or "待查"
    open_t = spot.get("open_time", "08:00-18:00") or "全天"
    rating = spot.get("rating", "") or ""

    tags = f"[{cat}]" if cat != "其他" else "[其他]"
    if level == "5A":
        tags += ",5A"
    else:
        tags += ",4A"

    province_display = province if province else ""
    rating_display = f" | 评分：{rating}" if rating else ""

    content = f"""---
name: {name}
level: "{level}"
level_year: ""
province: "{province_display}"
city: "{city}"
category: {cat}
location: [{loc[0] or 0},{loc[1] or 0}]
coord_src: {"amap" if loc[0] else "pending"}
free: false
ticket: "{ticket}"
open_time: "{open_t}"
rating: "{rating}"
tags: [{tags.strip(",")}]
source: {source}
status: generated
generated: {time.strftime("%Y-%m-%d")}
---

# {name}

> 分类：{cat} | 等级：{level}{rating_display} | 省份：{province_display}

## 基础信息

| 项目 | 内容 |
|------|------|
| 景区名称 | {name} |
| 等级 | {level} |
| 所在城市 | {city} |
| 所属省份 | {province_display} |
| 参考票价 | ¥{ticket} |
| 开放时间 | {open_t} |
| 坐标 | {f"{loc[0]:.4f},{loc[1]:.4f}" if loc[0] else "待定位"} |

## 打卡点推荐

| # | 景点 | 游览时长 | 看点 |
|---|------|----------|------|
| 1 | | 40分钟 | |
| 2 | | 30分钟 | |
| 3 | | 30分钟 | |
| 4 | | 20分钟 | |
| 5 | | 20分钟 | |

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
    file_path.write_text(content, encoding="utf-8", errors="ignore")
    return "generated", name

def main():
    print(f"Luke景区KB全量生成引擎 v2")
    print(f"  批次: {BATCH_SIZE} | 最大批次: {MAX_BATCHES}")
    print(f"  队列: {QUEUE_FILE}\n")

    progress = get_progress()
    done_set = set(progress.get("done", []))
    failed_set = set(progress.get("failed", []))

    if not Path(QUEUE_FILE).exists():
        print(f"队列文件不存在: {QUEUE_FILE}")
        return

    all_spots = json.loads(Path(QUEUE_FILE).read_text(encoding="utf-8"))
    total = len(all_spots)
    remaining = [s for s in all_spots if s["name"] not in done_set and s["name"] not in failed_set]

    print(f"总队列: {total} | 已完成: {len(done_set)} | 剩余: {len(remaining)}\n")

    gen_count, skip_count, fail_count = 0, 0, 0
    batch_num = 0

    while remaining and batch_num < MAX_BATCHES:
        batch_num += 1
        batch = remaining[:BATCH_SIZE]
        remaining = remaining[BATCH_SIZE:]

        print(f"批次 {batch_num} | {len(batch)} 个景区")
        print("=" * 50)

        for spot in batch:
            name = spot["name"]
            try:
                status, n = generate_md(spot)
                print(f"  [{status}] {name}")
                if status == "generated":
                    gen_count += 1
                    done_set.add(name)
                else:
                    skip_count += 1
                time.sleep(0.1)
            except Exception as e:
                print(f"  [ERROR] {name}: {e}")
                failed_set.add(name)
                fail_count += 1

        # 保存进度
        progress["done"] = list(done_set)
        progress["failed"] = list(failed_set)
        save_progress(progress)

        print(f"  本批: +{gen_count}生成, {skip_count}跳过, {fail_count}失败")
        print(f"  累计: {len(done_set)}/{total} 完成\n")

    print(f"\n🎉 本轮完成: +{gen_count} 生成, {skip_count} 跳过")
    print(f"   总累计: {len(done_set)}/{total} 完成")
    if remaining:
        print(f"   剩余: {len(remaining)} 个（下次cron继续）")
    else:
        print(f"   ✅ 队列已全部处理完毕！")

if __name__ == "__main__":
    main()
