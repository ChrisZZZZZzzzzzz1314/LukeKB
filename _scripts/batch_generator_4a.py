#!/usr/bin/env python3
"""
批量景点攻略生成引擎 — 4A/知名景区专版
从 4a_notable.json 读取景区，生成 Markdown 入库
"""
import json, os, sys, time, re
from pathlib import Path

KB_DIR = Path.home() / "Documents" / "LukeKB"
SCRIPT_DIR = KB_DIR / "_scripts"
NOTABLE_FILE = SCRIPT_DIR / "4a_notable.json"
OUTPUT_BASE = KB_DIR / "scenic" / "4A"

BATCH_SIZE = int(sys.argv[1]) if len(sys.argv) > 1 else 20
MAX_BATCHES = int(sys.argv[2]) if len(sys.argv) > 2 else 9999

def load_queue():
    return json.loads(NOTABLE_FILE.read_text(encoding="utf-8"))

def classify(name):
    cat_keywords = {
        "主题乐园": ["乐园", "欢乐谷", "方特", "恐龙园", "海洋王国", "世界之窗", "宋城", "动物园", "长隆"],
        "城市公园": ["塔", "公园", "湖", "园", "广场"],
        "自然风光": ["湿地", "山", "峡", "林"],
        "人文山水": ["古城", "古镇", "大唐", "芙蓉园", "历史"],
        "宗教文化": ["寺", "庙", "观", "佛", "宫"],
    }
    for cat, kws in cat_keywords.items():
        for kw in kws:
            if kw in name:
                return cat
    return "其他"

def pinyin_fallback(name):
    PINYIN = {
        "北":"bei","广":"guang","深":"shen","杭":"hang","常":"chang",
        "成":"cheng","重":"zhong","武":"wu","天":"tian","珠":"zhu",
        "上":"shang","厦":"xia","宁":"ning","郑":"zheng","沈":"shen",
        "西":"xi","北":"bei","大":"da","温":"wen","济":"ji","南":"nan",
    }
    first = name[0] if name else 'x'
    return PINYIN.get(first, 'x') + '-' + str(abs(hash(name)))[:4]

def generate_md(spot):
    name = spot["name"]
    cat = spot.get("category", classify(name))
    province = spot.get("province", "")
    ticket = spot.get("ticket", "待查")
    open_t = spot.get("open", "08:00-18:00")
    tips = spot.get("tips", "")

    # 分类目录
    cat_dir = OUTPUT_BASE / cat
    cat_dir.mkdir(parents=True, exist_ok=True)

    safe = re.sub(r"[^\w\u4e00-\u9fff-]", "_", name)
    file_path = cat_dir / f"4A-{safe}.md"

    # 已有内容则跳过
    if file_path.exists() and len(file_path.read_text(errors="ignore")) > 500:
        return "skipped", name

    content = f"""---
name: {name}
level: {spot.get("level","4A")}
level_year: "{spot.get("level_year","")}"
province: {province}
city: {spot.get("city","")}
category: {cat}
location: [0, 0]
coord_src: batch-generated
free: false
ticket: "{ticket}"
open_time: "{open_t}"
tags: [{cat}]
source: notable-4A-list
status: generated
generated: {time.strftime("%Y-%m-%d")}
---

# {name}

> 分类：{cat} | 等级：{spot.get("level","4A")} | 省份：{province}

## 基础信息

| 项目 | 内容 |
|------|------|
| 景区名称 | {name} |
| 等级 | {spot.get("level","4A")} |
| 所在城市 | {spot.get("city","")} |
| 所属省份 | {province} |
| 参考票价 | ¥{ticket} |
| 开放时间 | {open_t} |

## 景区简介

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
    file_path.write_text(content, encoding="utf-8", errors="ignore")
    return "generated", name

def main():
    queue = load_queue()
    print(f"4A景区批量生成 — 共 {len(queue)} 个")
    print(f"批次大小: {BATCH_SIZE}, 最大批次: {MAX_BATCHES}\n")

    gen_count = 0
    skip_count = 0

    for i in range(0, min(len(queue), BATCH_SIZE * MAX_BATCHES), BATCH_SIZE):
        batch = queue[i:i+BATCH_SIZE]
        print(f"批次 {i//BATCH_SIZE+1} | {len(batch)} 个")
        for spot in batch:
            try:
                status, name = generate_md(spot)
                print(f"  [{status}] {name}")
                if status == "generated":
                    gen_count += 1
                else:
                    skip_count += 1
            except Exception as e:
                print(f"  [ERROR] {spot.get('name','?')}: {e}")
            time.sleep(0.3)

    print(f"\n完成: {gen_count} 生成, {skip_count} 跳过")

if __name__ == "__main__":
    main()
