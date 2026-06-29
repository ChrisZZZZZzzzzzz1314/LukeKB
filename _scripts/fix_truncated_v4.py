#!/usr/bin/env python3
"""
修复被截断的景区文件 - 分批生成版 v4
核心思路：拆成3个并行LLM调用，每个独立5000 tokens
调用1: 核心故事 + 八大打卡点
调用2: 五条人文故事 + 美食矩阵
调用3: 游玩攻略
然后组装成一个完整文件
"""
import os, json, sys, time, glob, subprocess, re
from concurrent.futures import ThreadPoolExecutor, as_completed

PROGRESS_FILE = "/Users/chriszhang/Documents/LukeKB/_scripts/fix_progress.json"

def get_api_key():
    env_file = os.path.expanduser("~/.hermes/profiles/luke/.env")
    if os.path.exists(env_file):
        for line in open(env_file):
            if "MINIMAX_CN_API_KEY" in line:
                return line.strip().split("=")[-1].strip().strip('"').strip("'")
    return ""

def call_minimax(prompt, timeout=180):
    """调用MiniMax，返回纯text内容（跳过thinking block）"""
    api_key = get_api_key()
    payload = {
        "model": "MiniMax-M2.7",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 5000,
    }
    cmd = [
        "curl", "-s", "-X", "POST",
        "https://api.minimaxi.com/anthropic/v1/messages",
        "-H", f"X-Api-Key: {api_key}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(payload)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        resp = json.loads(result.stdout)
        if "content" in resp:
            for block in resp["content"]:
                if block.get("type") == "text" and "text" in block and "thinking" not in block:
                    return block["text"].replace("\\n", "\n")
            # fallback
            for block in reversed(resp.get("content", [])):
                if block.get("type") == "text" and "text" in block:
                    return block["text"].replace("\\n", "\n")
        err = resp.get("error", {})
        print(f"    API错误: {err.get('message', str(err))[:60]}")
    except subprocess.TimeoutExpired:
        print(f"    超时({timeout}s)")
    except Exception as e:
        print(f"    异常: {e}")
    return None

def generate_part1(name):
    """生成 核心故事 + 打卡点"""
    prompt = f"""为景区「{name}」生成Markdown内容，包含以下两个部分，每个部分内容要充实完整（每部分至少80字）：

## 一、核心故事（150字背景介绍）
[生成景区背景、历史、人文底蕴介绍]

## 二、八大打卡点
[列出8个必打卡景点/地点，每个包含景点名称和50字以上描述]

直接输出，不要代码块标记。"""
    return call_minimax(prompt)

def generate_part2(name):
    """生成 人文故事 + 美食"""
    prompt = f"""为景区「{name}」生成Markdown内容，包含以下两个部分，每个部分内容要充实完整（每部分至少80字）：

## 三、五条人文故事
[讲述5个与该景区相关的历史典故、民间传说或名人故事，每个故事至少60字]

## 四、美食矩阵（7个菜品）
[列出7种当地特色美食/菜品，每个包含名称、特点和参考价格]

直接输出，不要代码块标记。"""
    return call_minimax(prompt)

def generate_part3(name):
    """生成 游玩攻略"""
    prompt = f"""为景区「{name}」生成Markdown游玩攻略，包含以下四个方面，每个方面至少4条（内容要充实完整）：

## 五、游玩攻略

### 交通指南
[提供到达景区的交通方式：公共交通、自驾、周边城市出发建议]

### 最佳季节
[说明四季特色和最佳游览时间]

### 建议时长
[根据不同游览深度给出1日/2日/3日等时长建议]

### 实用tips
[提供4-6条实用建议，如门票预约、穿着、必备物品、注意事项等]

直接输出，不要代码块标记。"""
    return call_minimax(prompt)

def get_done():
    if os.path.exists(PROGRESS_FILE):
        return set(json.load(open(PROGRESS_FILE)))
    return set()

def add_done(name):
    done = get_done()
    done.add(name)
    json.dump(list(done), open(PROGRESS_FILE,"w"), ensure_ascii=False)

def fix_file(filepath, name, level, cat):
    """3路并行生成，然后组装"""
    print("  并行生成3个部分...", flush=True)
    
    # 并行调用
    results = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(generate_part1, name): "part1",
            executor.submit(generate_part2, name): "part2", 
            executor.submit(generate_part3, name): "part3",
        }
        for future in as_completed(futures, timeout=240):
            part_name = futures[future]
            try:
                results[part_name] = future.result()
                print(f"  {part_name}: {'✅' if results[part_name] else '❌'}", flush=True)
            except Exception as e:
                print(f"  {part_name}: 异常({e})", flush=True)
                results[part_name] = None
    
    # 验证3个部分都有内容
    if not all(results.values()):
        missing = [k for k, v in results.items() if not v]
        print(f"  部分缺失: {missing}")
        return False
    
    # 组装
    with open(filepath, "r", encoding="utf-8") as f:
        existing = f.read()
    
    # 提取frontmatter
    lines = existing.split("\n")
    fm_start = fm_end = -1
    for idx, line in enumerate(lines):
        if line.strip() == "---":
            if fm_start == -1: fm_start = idx
            else: fm_end = idx; break
    
    if fm_start != -1 and fm_end != -1:
        fm_text = "\n".join(lines[fm_start:fm_end+1])
    else:
        fm_text = f"""---
name: "{name}"
level: "{level}"
category: "{cat}"
tags: ["{cat}"]
status: refined
refined: {time.strftime("%Y-%m-%d")}
---"""
    
    title = f"# {name}"
    body = f"\n\n{title}\n\n"
    for part in [results["part1"], results["part2"], results["part3"]]:
        body += part.strip() + "\n\n"
    
    new_content = fm_text + body
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)
    return True

def main():
    batch_limit = int(sys.argv[1]) if len(sys.argv) > 1 else 999999
    
    base = "/Users/chriszhang/Documents/LukeKB/scenic"
    to_fix = []
    for level in ["5A", "4A"]:
        base_dir = f"{base}/{level}"
        if not os.path.exists(base_dir): continue
        for cat_dir in glob.glob(f"{base_dir}/*/"):
            cat = os.path.basename(cat_dir.rstrip("/"))
            for f in glob.glob(f"{cat_dir}*.md"):
                lines = len(open(f).readlines())
                name = os.path.basename(f).replace(f"{level}-","").replace(".md","")
                if lines < 200:
                    to_fix.append((f, name, level, cat))

    print(f"待修复: {len(to_fix)}个")
    
    done = get_done()
    total = len(to_fix)
    processed = 0
    success = 0
    
    for i, (filepath, name, level, cat) in enumerate(to_fix):
        if name in done:
            continue
        if processed >= batch_limit:
            break
        
        print(f"[{i+1}/{total}] 修复: {name}...", end=" ", flush=True)
        ok = fix_file(filepath, name, level, cat)
        if ok:
            add_done(name)
            success += 1
            print("✅")
        else:
            print("❌")
        processed += 1
        time.sleep(1)
    
    print(f"\n🎉 修复完成: {success}/{processed}个")
    print(f"总待修复: {total}个 (已完成{len(get_done())}个)")

if __name__ == "__main__":
    main()
