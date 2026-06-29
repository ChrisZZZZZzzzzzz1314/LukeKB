#!/usr/bin/env python3
"""极速版 v5：X-Api-Key + thinking=disabled → 1.6秒/次"""
import os, json, sys, time, glob, subprocess

PROGRESS_FILE = "/Users/chriszhang/Documents/LukeKB/_scripts/fix_progress.json"

def get_api_key():
    env_file = os.path.expanduser("~/.hermes/profiles/luke/.env")
    if os.path.exists(env_file):
        for line in open(env_file):
            if "MINIMAX_CN_API_KEY" in line:
                return line.strip().split("=")[-1].strip().strip('"').strip("'")
    return ""

def get_llm_content(name, level, category, retry=2):
    prompt = f"""为景区「{name}」生成完整Markdown内容，包含以下五部分，每部分内容要充实完整：

## 一、核心故事（150字背景介绍）
## 二、八大打卡点
## 三、五条人文故事
## 四、美食矩阵（7个菜品，含人均价格）
## 五、游玩攻略（交通/最佳季节/建议时长/实用tips各3-5条）

不要省略任何部分，不要代码块标记。"""
    
    api_key = get_api_key()
    payload = {
        "model": "MiniMax-M2.7",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 5000,
        "thinking": {"type": "disabled"}   # 极速关键！
    }
    
    for attempt in range(retry + 1):
        try:
            result = subprocess.run(
                ["curl", "-s", "--max-time", "90", "-X", "POST",
                 "https://api.minimaxi.com/anthropic/v1/messages",
                 "-H", f"X-Api-Key: {api_key}",
                 "-H", "Content-Type: application/json",
                 "-d", json.dumps(payload)],
                capture_output=True, text=True, timeout=100
            )
            resp = json.loads(result.stdout)
            if "content" in resp:
                for block in resp["content"]:
                    if block.get("type") == "text" and "text" in block and "thinking" not in block:
                        return block["text"].replace("\\n", "\n")
            err = resp.get("error", {})
            print(f"  LLM错误({attempt+1}): {err.get('message', str(err))[:60]}")
        except subprocess.TimeoutExpired:
            print(f"  超时({attempt+1}/{retry+1})")
        except Exception as e:
            print(f"  异常({attempt+1}): {e}")
        if attempt < retry:
            time.sleep(1)
    return None

def get_done():
    if os.path.exists(PROGRESS_FILE):
        return set(json.load(open(PROGRESS_FILE)))
    return set()

def add_done(name):
    done = get_done()
    done.add(name)
    json.dump(list(done), open(PROGRESS_FILE,"w"), ensure_ascii=False)

def fix_file(filepath, name, level, cat):
    content = get_llm_content(name, level, cat)
    if not content:
        return False
    
    content = content.strip().strip("```markdown").strip("```").strip()
    
    with open(filepath, "r", encoding="utf-8") as f:
        existing = f.read()
    
    lines = existing.split("\n")
    fm_start = fm_end = -1
    for idx, line in enumerate(lines):
        if line.strip() == "---":
            if fm_start == -1: fm_start = idx
            else: fm_end = idx; break
    
    fm_text = "\n".join(lines[fm_start:fm_end+1]) if fm_end != -1 else f"""---
name: "{name}"
level: "{level}"
category: "{cat}"
tags: ["{cat}"]
status: refined
refined: {time.strftime("%Y-%m-%d")}
---"""
    
    title = f"# {name}"
    body_lines = []
    in_body = False
    for line in content.split("\n"):
        if line.startswith("## ") or line.startswith("# "):
            in_body = True
        if in_body:
            body_lines.append(line)
    
    body_text = "\n".join(body_lines) if body_lines else content
    new_content = fm_text + "\n\n" + title + "\n\n" + body_text + "\n"
    
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
        time.sleep(0.5)  # 0.5秒足够
    
    print(f"\n🎉 修复完成: {success}/{processed}个")
    print(f"总待修复: {total}个 (已完成{len(get_done())}个)")

if __name__ == "__main__":
    main()
