#!/usr/bin/env python3
"""
LukeKB 精准精写脚本
只精写5A骨架(473个) + 主题乐园(21个)
每个文件生成100-200行完整内容
"""
import os, json, sys, time, subprocess
from pathlib import Path

AMAP_KEY = "b78a178a71c46c9425d45dab9d5c1a2a"
MINIMAX_KEY = os.environ.get("MINIMAX_CN_API_KEY", "")
BASE = "/Users/chriszhang/Documents/LukeKB/scenic"

PROMPT_TPL = """你是一个中国景区知识库专家。请为以下景区生成完整的Markdown知识条目。

景区信息：
- 名称：{name}
- 等级：{level}
- 分类：{category}

要求输出完整的Markdown文件：

```markdown
---
name: {name}
level: "{level}"
level_year: "创建年份"
province: "省份"
city: "城市"
category: {category}
location: [经度,纬度]
coord_src: amap
free: false
ticket: "门票价格"
open_time: "开放时间"
rating: "评分"
tags: [标签1,标签2,标签3]
source: refined
status: completed
generated: {date}
---

# {name}

> 分类：{category} | 等级：{level}

## 一、核心故事（150字背景介绍）

## 二、八大打卡点
| # | 打卡点 | 类型 | 看点 |

## 三、五条人文故事
### 故事1：
### 故事2：
### 故事3：
### 故事4：
### 故事5：

## 四、美食矩阵
| 菜品 | 类型 | 人均 | 推荐理由 |

## 五、游玩攻略
- 交通：
- 最佳季节：
- 建议时长：
- 实用tips：
```

请直接输出完整的Markdown内容，全部填满不要留"待查"。
"""

def get_llm_content(name, level, category):
    """调用MiniMax生成内容"""
    prompt = PROMPT_TPL.format(
        name=name, level=level, category=category,
        date="2026-06-24"
    )
    
    payload = {
        "model": "MiniMax-M2.7",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 5000,
    }
    
    cmd = [
        "curl", "-s", "-X", "POST",
        "https://api.minimaxi.com/anthropic/v1/messages",
        "-H", f"Authorization: Bearer {MINIMAX_KEY}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(payload)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        resp = json.loads(result.stdout)
        if "content" in resp:
            for block in resp["content"]:
                if block.get("type") == "text":
                    return block["text"]
    except Exception as e:
        print(f"  LLM错误: {e}", file=sys.stderr)
    return None

def refine_file(filepath, name, level, category):
    """精写单个文件"""
    content = get_llm_content(name, level, category)
    if content and len(content) > 200:
        # 去掉LLM输出的```markdown包裹
        lines = content.strip().split("\n")
        if lines and lines[0].strip() == "```markdown":
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False

def main():
    # 支持命令行参数：本批处理多少个
    batch_limit = int(sys.argv[1]) if len(sys.argv) > 1 else 999999
    
    files_to_refine = []
    
    # 1. 所有5A骨架文件(<100行)
    base5a = f"{BASE}/5A"
    for cat_dir in glob(f"{base5a}/*/"):
        cat = os.path.basename(cat_dir.rstrip("/"))
        for f in glob(f"{cat_dir}*.md"):
            lines = len(open(f).readlines())
            name = os.path.basename(f).replace("5A-","").replace(".md","")
            if lines < 100:
                files_to_refine.append((f, name, "5A", cat))
    
    # 2. 主题乐园(4A)骨架文件
    base4a = f"{BASE}/4A"
    theme_parks = []
    for f in glob(f"{base4a}/主题乐园/*.md"):
        lines = len(open(f).readlines())
        name = os.path.basename(f).replace("4A-","").replace(".md","")
        theme_parks.append((f, name, "4A", "主题乐园"))
        if lines < 100:
            if (f, name, "4A", "主题乐园") not in files_to_refine:
                files_to_refine.append((f, name, "4A", "主题乐园"))
    
    print(f"精写任务: {len(files_to_refine)}个文件")
    print(f"  5A骨架: {sum(1 for x in files_to_refine if x[2]=='5A')}个")
    print(f"  主题乐园: {sum(1 for x in files_to_refine if x[2]=='4A')}个")
    
    # 读取进度
    progress_file = "/Users/chriszhang/Documents/LukeKB/_scripts/refine_progress.json"
    done = set()
    if os.path.exists(progress_file):
        done = set(json.load(open(progress_file)))
    
    total = len(files_to_refine)
    done_count = len(done)
    skip_count = 0
    processed_this_run = 0
    
    for i, (filepath, name, level, cat) in enumerate(files_to_refine):
        if name in done:
            skip_count += 1
            continue
        
        if processed_this_run >= batch_limit:
            print(f"本批Limit={batch_limit}已达，退出")
            break
        
        print(f"[{i+1}/{total}] 精写: {name}...", end=" ", flush=True)
        ok = refine_file(filepath, name, level, cat)
        if ok:
            done.add(name)
            json.dump(list(done), open(progress_file,"w"))
            done_count += 1
            processed_this_run += 1
            print("✅")
        else:
            print("❌ 失败，跳过")
        
        # 限速：每分钟20个
        time.sleep(3)
        
        if (i+1) % 10 == 0:
            print(f"\n📊 进度: {done_count}/{total} ({done_count/total*100:.1f}%)")
    
    print(f"\n🎉 精写完成: {done_count}/{total} 个文件")

if __name__ == "__main__":
    from glob import glob
    main()
