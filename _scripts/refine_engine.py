#!/usr/bin/env python3
"""
Luke景区KB精写引擎 - 只精写骨架文件（5A + 主题乐园）
每次处理N个，直到队列清空
"""
import sys, os, glob, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from refine_prompt import build_refine_prompt

def get_skeleton_files():
    """找出所有骨架文件（<100行）"""
    base = "/Users/chriszhang/Documents/LukeKB/scenic"
    skeletons = []
    for level in ["5A", "4A"]:
        level_dir = f"{base}/{level}"
        if not os.path.exists(level_dir):
            continue
        for cat_dir in glob.glob(f"{level_dir}/*/"):
            cat = os.path.basename(cat_dir.rstrip("/"))
            for f in glob.glob(f"{cat_dir}*.md"):
                lines = len(open(f).readlines())
                name = os.path.basename(f).replace(f"{level}-","").replace(".md","")
                if lines < 100:
                    # 跳过停车票/卫生间等无意义词
                    skip_words = ["停车场","停车点","售票处","卫生间","厕所","公厕",
                                  "游客中心","管理委员会","酒店","宾馆","民宿","餐厅",
                                  "餐厅","商店","小卖部","售票厅"]
                    if any(w in name for w in skip_words):
                        continue
                    skeletons.append({
                        "file": f,
                        "name": name,
                        "level": level,
                        "category": cat,
                        "lines": lines
                    })
    return skeletons

def process_skeleton(item, api_key):
    """精写单个骨架文件"""
    from minimax_client import chat_minimax
    
    prompt = build_refine_prompt(item["name"], item["level"], item["category"])
    
    response = chat_minimax(
        api_key=api_key,
        prompt=prompt,
        model="MiniMax-M2.7"
    )
    
    if not response:
        return False, "API失败"
    
    # 解析markdown输出
    lines = response.strip().split("\n")
    if len(lines) < 10:
        return False, "内容过短"
    
    # 组装完整内容
    content = response
    
    # 写文件
    try:
        with open(item["file"], "w", encoding="utf-8") as f:
            f.write(content)
        return True, f"写入{len(lines)}行"
    except Exception as e:
        return False, str(e)

def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    
    api_key = os.environ.get("MINIMAX_CN_API_KEY", "")
    if not api_key:
        # 尝试从env文件读取
        env_file = os.path.expanduser("~/.hermes/profiles/luke/.env")
        if os.path.exists(env_file):
            for line in open(env_file):
                if "MINIMAX_CN_API_KEY" in line and "=" in line:
                    api_key = line.split("=",1)[1].strip().strip('"').strip("'")
                    break
    
    skeletons = get_skeleton_files()
    print(f"发现骨架文件: {len(skeletons)}个")
    
    if not skeletons:
        print("✅ 全部骨架已精写完毕！")
        return
    
    to_process = skeletons[:count]
    print(f"本批精写: {len(to_process)}个")
    
    success = 0
    failed = []
    
    for i, item in enumerate(to_process, 1):
        print(f"[{i}/{len(to_process)}] 精写: {item['name']} ({item['level']})")
        ok, msg = process_skeleton(item, api_key)
        if ok:
            success += 1
            print(f"  ✅ {msg}")
        else:
            failed.append((item['name'], msg))
            print(f"  ❌ {msg}")
        time.sleep(1)  # 避免API限流
    
    print(f"\n本批完成: {success}/{len(to_process)}成功")
    if failed:
        print(f"失败: {[n for n,_ in failed]}")

if __name__ == "__main__":
    main()
