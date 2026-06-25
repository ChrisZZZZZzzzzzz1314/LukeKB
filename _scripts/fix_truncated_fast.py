#!/usr/bin/env python3
"""修复被截断的景区文件 - 极速版 v3
关键修复:
1. 跳过thinking block，正确提取text block
2. 把字面字符串\\n替换成真正换行符
3. 正确提取frontmatter字段并保留
4. sleep 3s→1s，加重试机制
"""
import os, json, sys, time, glob, subprocess, re

PROGRESS_FILE = "/Users/chriszhang/Documents/LukeKB/_scripts/fix_progress.json"

def get_api_key():
    env_file = os.path.expanduser("~/.hermes/profiles/luke/.env")
    if os.path.exists(env_file):
        for line in open(env_file):
            if "MINIMAX_CN_API_KEY" in line:
                return line.strip().split("=")[-1].strip().strip('"').strip("'")
    return ""

def get_llm_content(name, level, category, retry=2):
    """调用MiniMax生成内容，跳过thinking block"""
    prompt = f"""为景区「{name}」生成完整的Markdown内容。

景区信息：
- 名称：{name}
- 等级：{level}
- 分类：{category}

请生成包含以下五个部分的完整Markdown，直接输出全部内容不要省略：

## 一、核心故事（150字背景介绍）
## 二、八大打卡点
## 三、五条人文故事
## 四、美食矩阵（7个菜品，含人均价格）
## 五、游玩攻略（交通/最佳季节/建议时长/实用tips各3-5条）

每个部分内容要充实完整，不要省略任何部分。不要输出代码块标记。
"""
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
    
    for attempt in range(retry + 1):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
            resp = json.loads(result.stdout)
            if "content" in resp:
                for block in resp["content"]:
                    # 关键修复：跳过含thinking的block
                    if block.get("type") == "text" and "text" in block and "thinking" not in block:
                        raw = block["text"]
                        # 关键修复：把字面\\n替换成真正换行符
                        raw = raw.replace("\\n", "\n")
                        return raw
                # fallback：取最后一个text block
                for block in reversed(resp["content"]):
                    if block.get("type") == "text" and "text" in block:
                        raw = block["text"]
                        raw = raw.replace("\\n", "\n")
                        return raw
            err = resp.get("error", {})
            print(f"  LLM错误(attempt {attempt+1}): {err.get('message', str(err))[:80]}")
        except subprocess.TimeoutExpired:
            print(f"  超时(attempt {attempt+1}/{retry+1})")
        except Exception as e:
            print(f"  异常(attempt {attempt+1}): {e}")
        if attempt < retry:
            time.sleep(2)
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
    """重新生成完整内容，保留原frontmatter"""
    content = get_llm_content(name, level, cat)
    if not content:
        return False
    
    # 清理代码块标记
    content = content.strip().strip("```markdown").strip("```").strip()
    
    # 读取现有frontmatter
    with open(filepath, "r", encoding="utf-8") as f:
        existing = f.read()
    
    # 正确提取frontmatter（找第一对---）
    fm_start = -1
    fm_end = -1
    lines = existing.split("\n")
    for idx, line in enumerate(lines):
        if line.strip() == "---":
            if fm_start == -1:
                fm_start = idx
            else:
                fm_end = idx
                break
    
    if fm_start != -1 and fm_end != -1:
        fm_lines = lines[fm_start:fm_end+1]
        fm_text = "\n".join(fm_lines)
    else:
        # 没有frontmatter则创建
        fm_text = f"""---
name: "{name}"
level: "{level}"
category: "{cat}"
tags: ["{cat}"]
status: refined
refined: {time.strftime("%Y-%m-%d")}
---"""
    
    # 提取body：跳过标题行直到有##或正文
    body_lines = []
    in_body = False
    for line in content.split("\n"):
        if line.startswith("## ") or line.startswith("# "):
            in_body = True
        if in_body:
            body_lines.append(line)
    
    body_text = "\n".join(body_lines) if body_lines else content
    
    # 组装：frontmatter + 空行 + 标题 + body
    title = f"# {name}"
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

    print(f"待修复截断文件: {len(to_fix)}个")
    
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
