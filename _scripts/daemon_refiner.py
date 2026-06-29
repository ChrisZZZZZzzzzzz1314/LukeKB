#!/usr/bin/env python3
"""
LukeKB 景区精写守护进程 - 持续循环版
持续处理截断文件，带进程锁防止重复启动
每完成1个输出进度，每50个输出摘要
"""
import os, sys, json, glob, time, subprocess, fcntl, signal

LOCK_FILE  = "/tmp/luke_kb_refiner.lock"
PID_FILE   = "/tmp/luke_kb_refiner.pid"
PROGRESS_FILE = "/Users/chriszhang/Documents/LukeKB/_scripts/fix_progress.json"
BASE_DIR   = "/Users/chriszhang/Documents/LukeKB/scenic"
BATCH_LOG  = "/tmp/luke_kb_batch.log"
STOP_FILE  = "/tmp/luke_kb_refiner_stop"

# 全局停止标志
running = True

def signal_handler(sig, frame):
    global running
    print("\n⚠️  收到停止信号，正在结束当前文件...")
    running = False

signal.signal(signal.SIGINT,  signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def get_api_key():
    env = os.path.expanduser("~/.hermes/profiles/luke/.env")
    if os.path.exists(env):
        for line in open(env):
            if "MINIMAX_CN_API_KEY" in line:
                return line.strip().split("=")[-1].strip().strip('"').strip("'")
    return ""

def call_llm(name, level, category):
    """单次LLM调用，返回text内容（跳过thinking block）"""
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
        "thinking": {"type": "disabled"}
    }
    
    for attempt in range(3):
        try:
            result = subprocess.run(
                ["curl", "-s", "--max-time", "300", "-X", "POST",
                 "https://api.minimaxi.com/anthropic/v1/messages",
                 "-H", f"X-Api-Key: {api_key}",
                 "-H", "Content-Type: application/json",
                 "-d", json.dumps(payload)],
                capture_output=True, text=True, timeout=310
            )
            resp = json.loads(result.stdout)
            if "content" in resp:
                for block in resp["content"]:
                    if block.get("type") == "text" and "text" in block and "thinking" not in block:
                        return block["text"].replace("\\n", "\n")
            err = resp.get("error", {})
            print(f"[LLM错误] {err.get('message', str(err))[:60]}", flush=True)
        except subprocess.TimeoutExpired:
            print(f"[超时 attempt {attempt+1}/3]", flush=True)
        except Exception as e:
            print(f"[异常] {e}", flush=True)
        if attempt < 2:
            time.sleep(2)
    return None

def get_done():
    if os.path.exists(PROGRESS_FILE):
        return set(json.load(open(PROGRESS_FILE)))
    return set()

def add_done(name):
    done = get_done()
    done.add(name)
    json.dump(list(done), open(PROGRESS_FILE, "w"), ensure_ascii=False)

def fix_file(filepath, name, level, cat):
    """生成并写入完整内容"""
    content = call_llm(name, level, cat)
    if not content:
        return False
    
    content = content.strip().strip("```markdown").strip("```").strip()
    
    with open(filepath, "r", encoding="utf-8") as f:
        existing = f.read()
    orig_lines = len(existing.split("\n"))

    lines = existing.split("\n")
    fm_start = fm_end = -1
    for idx, line in enumerate(lines):
        if line.strip() == "---":
            if fm_start == -1: fm_start = idx
            else: fm_end = idx; break
    
    if fm_end != -1:
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
    body_lines = []
    in_body = False
    first_h1_skipped = False
    for line in content.split("\n"):
        if line.startswith("## "):
            in_body = True
            body_lines.append(line)
        elif line.startswith("# ") and not first_h1_skipped:
            first_h1_skipped = True  # 跳过LLM输出的第一个H1标题
        elif in_body:
            body_lines.append(line)
    
    body_text = "\n".join(body_lines) if body_lines else content
    new_content = fm_text + "\n\n" + title + "\n\n" + body_text + "\n"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)
    return True

def get_pending():
    """获取待处理文件列表（优先处理最需精写的，支持未达标重试）"""
    done = get_done()
    pending = []
    for level in ["5A", "4A"]:
        dir_path = f"{BASE_DIR}/{level}"
        if not os.path.exists(dir_path): continue
        for cat_dir in glob.glob(f"{dir_path}/*/"):
            cat = os.path.basename(cat_dir.rstrip("/"))
            for f in glob.glob(f"{cat_dir}*.md"):
                name = os.path.basename(f).replace(f"{level}-", "").replace(".md", "")
                lines = len(open(f, encoding="utf-8").readlines())
                if lines < 100:
                    # name in done说明处理过但未达标 → 算重试
                    # 允许重试3次：检查_retry:{name}计数
                    retry_count = sum(1 for d in done if d == f"_retry:{name}")
                    if name in done and retry_count == 0:
                        # 首次重试
                        pending.append((f, name, level, cat, 1))
                    elif retry_count > 0 and retry_count < 3:
                        pending.append((f, name, level, cat, retry_count + 1))
                    elif name not in done:
                        pending.append((f, name, level, cat, 0))
    # 按行数升序（越短越优先）
    pending.sort(key=lambda x: len(open(x[0], encoding="utf-8").readlines()))
    return pending

def log_batch(msg):
    """写批次日志"""
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(BATCH_LOG, "a") as f:
        f.write(line + "\n")

def main():
    global running
    
    # 进程锁
    lock_fd = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        print("⚠️  已有实例在运行，退出")
        sys.exit(0)
    
    with open(PID_FILE, "w") as pf:
        pf.write(str(os.getpid()))
    
    print(f"🚀 LukeKB精写守护进程启动 [PID={os.getpid()}]")
    print(f"⏰ {time.strftime('%Y-%m-%d %H:%M:%S')}")
    log_batch(f"守护进程启动 PID={os.getpid()}")
    
    # 清理停止文件
    if os.path.exists(STOP_FILE):
        os.unlink(STOP_FILE)
    
    t0 = time.time()
    total_run = 0
    success_run = 0
    fail_run = 0
    
    while running:
        pending = get_pending()
        remaining = len(pending)
        
        if remaining == 0:
            log_batch("✅ 全部处理完毕！守护进程退出")
            break
        
        # 每轮显示摘要
        if total_run % 50 == 0 and total_run > 0:
            elapsed = time.time() - t0
            rate = success_run / elapsed * 3600 if elapsed > 0 else 0
            eta_h = remaining / rate if rate > 0 else 0
            log_batch(f"📊 进度: {success_run}成功/{fail_run}失败, 剩余{remaining}个, 速率{rate:.1f}个/时, 预计{eta_h:.1f}小时")
        
        # 取队首（5元素: filepath, name, level, cat, retry_round）
        item = pending[0]
        filepath, name, level, cat = item[0], item[1], item[2], item[3]
        retry_round = item[4] if len(item) > 4 else 0
        
        retry_tag = f" [重试{retry_round}]" if retry_round > 0 else ""
        print(f"[{remaining} remaining] {name}{retry_tag}...", end=" ", flush=True)
        
        t1 = time.time()
        ok = fix_file(filepath, name, level, cat)
        elapsed = time.time() - t1
        
        if ok:
            lines = len(open(filepath, encoding="utf-8").readlines())
            if lines >= 100:
                add_done(name)  # 真正完成
                success_run += 1
                print(f"✅ ({elapsed:.0f}s, {lines}行)", flush=True)
            else:
                # 未达标，重试标记（最多3次）
                if retry_round < 3:
                    add_done(f"_retry:{name}")
                    print(f"↻ ({elapsed:.0f}s, {lines}行, 继续精写)", flush=True)
                else:
                    # 重试3次仍不达标，放弃
                    add_done(name)
                    print(f"⚠️ ({elapsed:.0f}s, {lines}行, 放弃)", flush=True)
        else:
            fail_run += 1
            print(f"❌ ({elapsed:.0f}s)", flush=True)
        
        total_run += 1
        time.sleep(0.5)  # 防止QPS过载
    
    total_time = time.time() - t0
    log_batch(f"🏁 守护进程结束: {success_run}成功/{fail_run}失败, 总耗时{total_time:.0f}秒")
    
    fcntl.flock(lock_fd, fcntl.LOCK_UN)
    os.unlink(LOCK_FILE)
    os.unlink(PID_FILE)
    print("👋 守护进程已退出")

if __name__ == "__main__":
    main()
