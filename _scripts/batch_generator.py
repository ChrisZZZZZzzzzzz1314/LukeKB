#!/usr/bin/env python3
"""
批量景点攻略生成引擎
========================
从 5a_list.json 读取未处理的景点，批量生成 Markdown 文件入库。
支持断点续传（已完成的景区跳过）。

用法:
  python3 batch_generator.py [批次大小] [最大批次]
  python3 batch_generator.py 5 10   # 处理前10批，每批5个
"""

import json, os, sys, time, subprocess
from pathlib import Path

KB_DIR = Path.home() / "Documents" / "LukeKB"
SCRIPT_DIR = KB_DIR / "_scripts"
QUEUE_FILE = SCRIPT_DIR / "5a_list.json"
BATCH_LOG = SCRIPT_DIR / "batch_progress.json"
OUTPUT_BASE = KB_DIR / "scenic" / "5A"
TEMPLATE_FILE = SCRIPT_DIR / "prompt_template.py"  # 内嵌

BATCH_SIZE = int(sys.argv[1]) if len(sys.argv) > 1 else 5
MAX_BATCHES = int(sys.argv[2]) if len(sys.argv) > 2 else 9999

# ============ 景区分类映射 ============
CAT_MAP = {
    "人文山水": ["故宫", "天坛", "颐和园", "长城", "陵", "石窟", "寺庙", "书院", "孔庙", "碑林"],
    "自然风光": ["山", "峰", "峡", "湖", "瀑", "海", "岛", "江", "河", "泉", "林", "草原", "沙漠", "地质"],
    "古镇水乡": ["镇", "古城", "古街", "古巷", "水乡", "古镇", "西递", "宏村"],
    "主题乐园": ["乐园", "迪士尼", "欢乐谷", "方特", "海洋", "动物园"],
    "宗教文化": ["寺", "庙", "观", "宫", "佛", "塔", "菩萨", "道场", "佛教"],
    "城市公园": ["公园", "广场", "湖", "园"],
    "红色旅游": ["纪念", "红色", "革命", "主席", "延安", "井冈", "韶山", "红"],
}

def classify(name):
    for cat, keywords in CAT_MAP.items():
        for kw in keywords:
            if kw in name:
                return cat
    return "其他"

# ============ 基础坐标/门票数据（常见景区快速填充）===========
STATIC_DATA = {
    "恭王府景区": {"location":[39.9376,116.3729], "ticket":"40", "open":"09:00-17:00"},
    "天坛公园": {"location":[39.8831,116.4125], "ticket":"34", "open":"06:00-21:00"},
    "颐和园": {"location":[39.9993,116.4654], "ticket":"30", "open":"06:30-19:00"},
    "圆明园遗址公园景区": {"location":[40.0033,116.3043], "ticket":"10", "open":"07:00-20:00"},
    "八达岭-慕田峪长城旅游区": {"location":[40.3656,116.5701], "ticket":"40", "open":"07:00-18:00"},
    "明十三陵景区": {"location":[40.2417,116.2219], "ticket":"40", "open":"08:00-17:30"},
    "承德避暑山庄及周围寺庙景区": {"location":[40.9963,117.9420], "ticket":"130", "open":"07:00-18:00"},
}

# ============ 进度管理 ============
def load_progress():
    if BATCH_LOG.exists():
        return json.loads(BATCH_LOG.read_text())
    return {"done": [], "last_batch": 0, "started_at": time.time()}

def save_progress(pg):
    BATCH_LOG.write_text(json.dumps(pg, ensure_ascii=False, indent=2))

# ============ 加载景点队列 ============
def load_queue():
    return json.loads(QUEUE_FILE.read_text(encoding="utf-8"))

# ============ 生成单景区 Markdown ============
def generate_scenic_md(spot):
    name = spot['name']
    province = spot['province']
    cat = classify(name)
    
    static = STATIC_DATA.get(name, {})
    loc = static.get("location", [0, 0])
    ticket = static.get("ticket", "待查")
    open_t = static.get("open", "08:00-18:00")
    
    # 文件路径
    cat_dir = OUTPUT_BASE / cat
    cat_dir.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r'[^\w\u4e00-\u9fff-]', '_', name)
    file_path = cat_dir / f"5A-{safe_name}.md"
    
    # 如果文件已存在且有实质内容，跳过
    if file_path.exists():
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        if len(content) > 500:
            return "skipped", cat, f"{name} 已存在({len(content)}字)，跳过"
    
    # 生成 frontmatter
    frontmatter = f"""---
name: {name}
pinyin: {pinyin_fallback(name)}
level: 5A
level_year: 2024
province: {province}
category: {cat}
location: [{loc[0]},{loc[1]}]
coord_src: batch-generated
free: false
ticket: {ticket}
open_time: "{open_t}"
tags: [{cat}]
source: Venita-full-358
status: generated
generated: {time.strftime('%Y-%m-%d')}
---

# {name}

> 分类：{cat} | 省份：{province}

## 基础信息

| 项目 | 内容 |
|------|------|
| 景区名称 | {name} |
| 所属省份 | {province} |
| 评定等级 | 5A |
| 参考票价 | ¥{ticket} |
| 建议游览 | 3-4小时 |

"""

    body = f"""
## 核心故事

（待补充：景区历史背景、文化意义、评定历程）

## 打卡点推荐

| # | 景点 | 游览时长 | 看点 |
|---|------|----------|------|
| 1 | | 40分钟 | |
| 2 | | 30分钟 | |
| 3 | | 30分钟 | |

## 人文故事

（待补充：典故/传说/历史事件/名人足迹）

## 核心美食

| 菜品 | 价格 | 推荐理由 |
|------|------|----------|
| | ¥ | |

## 游玩建议

✅ 
✅ 
⚠️
"""
    
    full_content = frontmatter + body
    file_path.write_text(full_content, encoding="utf-8", errors="ignore")
    
    return "generated", cat, f"{name} → {file_path.relative_to(KB_DIR)}"

def pinyin_fallback(name):
    """简单拼音 fallback（真实场景应接入拼音API）"""
    import re
    # 只取首字拼音演示
    PINYIN_MAP = {
        "恭":"gong","天":"tian","颐":"yi","圆":"yuan","八":"ba","明":"ming",
        "承":"cheng","避":"bi","山":"shan","白":"bai","石":"shi","西":"xi",
        "金":"jin","清":"qing","南":"nan","开":"kai","唐":"tang","秦":"qin",
        "北":"bei","济":"ji","蓬":"peng","莱":"lai","蓬":"peng","泰":"tai",
    }
    first = name[0] if name else 'x'
    return PINYIN_MAP.get(first, 'x') + '-' + str(hash(name))[:4]

import re

def run_batch(batch_num, spots):
    print(f"\n{'='*50}")
    print(f"批次 {batch_num} | {len(spots)} 个景区")
    print(f"{'='*50}")
    
    results = []
    for i, spot in enumerate(spots):
        name = spot['name']
        print(f"[{i+1}/{len(spots)}] 处理: {name} ...", end=" ", flush=True)
        try:
            status, cat, msg = generate_scenic_md(spot)
            print(f"✅ {msg}")
            results.append({"name": name, "status": status, "cat": cat, "msg": msg})
        except Exception as e:
            print(f"❌ 错误: {e}")
            results.append({"name": name, "status": "error", "msg": str(e)})
        
        # 防限速
        time.sleep(0.5)
    
    return results

# ============ 主循环 ============
def main():
    pg = load_progress()
    done_names = set(pg.get("done", []))
    queue = load_queue()
    
    # 过滤未完成的
    pending = [s for s in queue if s['name'] not in done_names]
    total_remaining = len(pending)
    
    print(f"🎯 5A景区批量生成引擎")
    print(f"   总队列: {len(queue)} | 已完成: {len(done_names)} | 待处理: {total_remaining}")
    print(f"   批次大小: {BATCH_SIZE} | 最大批次: {MAX_BATCHES}")
    print()
    
    if total_remaining == 0:
        print("✅ 全部景区已生成完毕!")
        return
    
    batch_count = 0
    total_generated = 0
    
    for i in range(0, min(len(pending), BATCH_SIZE * MAX_BATCHES), BATCH_SIZE):
        batch = pending[i:i+BATCH_SIZE]
        batch_num = pg.get("last_batch", 0) + 1
        
        results = run_batch(batch_num, batch)
        
        # 更新已完成的名称
        for r in results:
            if r['status'] in ("generated", "skipped"):
                pg["done"].append(r["name"])
                pg["done"] = list(set(pg["done"]))  # 去重
        pg["last_batch"] = batch_num
        save_progress(pg)
        
        batch_count += 1
        total_generated += len([r for r in results if r['status'] == 'generated'])
        
        print(f"\n📊 批次 {batch_num} 完成: {len([r for r in results if r['status']=='generated'])} 生成, {len([r for r in results if r['status']=='skipped'])} 跳过, {len([r for r in results if r['status']=='error'])} 失败")
        
        if batch_count >= MAX_BATCHES:
            print(f"\n已达最大批次 {MAX_BATCHES}，退出")
            break
        
        # 每批次间稍作暂停
        time.sleep(2)
    
    elapsed = time.time() - pg.get("started_at", time.time())
    print(f"\n{'🎉'*20}")
    print(f"本轮完成: {batch_count} 批, 新增 {total_generated} 个文件")
    print(f"累计完成: {len(pg['done'])}/{len(queue)} 个景区")
    print(f"用时: {elapsed/60:.1f} 分钟")
    print(f"剩余: {len(queue)-len(pg['done'])} 个")

if __name__ == "__main__":
    main()
