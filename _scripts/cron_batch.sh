#!/bin/bash
# 阶段 2 启动脚本: 5A 景区攻略批量生成
# 触发方式: hermes cron 或手动调用
# 单次处理: 5 个景区,每个景区 3-5 分钟
# 频率: 每 2 小时

set -e
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
KB_DIR="$HOME/Documents/LukeKB"
LIST_FILE="$KB_DIR/_scripts/5a_list.json"
TODO_FILE="$KB_DIR/_scripts/todo_queue.json"
TEMPLATE="$KB_DIR/_templates/scenic-template.md"

BATCH_SIZE=5
PROFILE="luke"

# 读待办
PENDING=$(python3 -c "
import json
with open('$TODO_FILE') as f: d = json.load(f)
print(','.join(q['id'] for q in d['queue'][:$BATCH_SIZE] if True))
")

if [ -z "$PENDING" ]; then
  echo "✅ 所有任务已完成"
  exit 0
fi

echo "📋 本轮处理: $PENDING"

# 对每个景区调 LLM 生成
for ID in $(echo $PENDING | tr ',' ' '); do
  NAME=$(python3 -c "
import json
with open('$LIST_FILE') as f: d = json.load(f)
for x in d:
    if x['id'] == '$ID':
        print(x['name']); break
")
  PROV=$(python3 -c "
import json
with open('$LIST_FILE') as f: d = json.load(f)
for x in d:
    if x['id'] == '$ID':
        print(x['province']); break
")
  CITY=$(python3 -c "
import json
with open('$LIST_FILE') as f: d = json.load(f)
for x in d:
    if x['id'] == '$ID':
        print(x.get('city','')); break
")
  CAT=$(python3 -c "
import json
with open('$LIST_FILE') as f: d = json.load(f)
for x in d:
    if x['id'] == '$ID':
        print(x.get('category','')); break
")

  echo "🛠️ 生成: [$ID] $NAME ($PROV·$CITY, $CAT)"

  OUT="$KB_DIR/scenic/5A/$CAT/${ID}-${NAME}.md"
  mkdir -p "$KB_DIR/scenic/5A/$CAT"

  # 调 LLM (hermes 单条)
  PROMPT="你是 Luke,中国头部景区知识库构建专家。生成 $NAME (位于 $PROV 省 $CITY, 5A 级) 的完整攻略。
严格按模板格式输出 markdown (含 frontmatter):
$TEMPLATE

要求:
- web_search 至少 3 次: 历史背景 / 人文故事 / 必吃美食
- 数据真实,无编造
- 每节 100-300 字
- 直接输出 markdown 内容,不要解释"

  hermes chat -q "$PROMPT" -m "minimax-cn/MiniMax-M2.7" -p "$PROFILE" --quiet > "$OUT" 2>&1
  echo "  ✓ 已写入: $OUT"
done

echo "📊 阶段报告:"
ls -la "$KB_DIR/scenic/5A"/*/ | tail -20
