# 阶段 1 进度报告 — 基础设施搭建

**日期**: 2026-06-24
**用时**: ~15 分钟
**执行者**: Luke (Hermes profile: luke)

## ✅ 完成项

### 1. 模型切换
- 默认模型: `minimax-cn/MiniMax-M2.7` (原 M3)
- 实测 API 连通: ✅ 响应 < 2 秒
- Provider: `minimax-cn`, Base URL: `https://api.minimaxi.com/anthropic`

### 2. 知识库目录结构
```
~/Documents/LukeKB/                    (新建)
├── _index/                            (全局索引)
│   └── 5A-Index.md                    (5A 景区索引已生成)
├── _templates/                        (模板)
│   ├── README.md                      (知识库说明)
│   ├── scenic-template.md             (景区 markdown schema)
│   └── scenic-prompt.md               (生成用 prompt)
├── _scripts/                          (构建脚本)
│   ├── 5a_list.json                   (218 个 5A 景区清单)
│   ├── todo_queue.json                (待办队列)
│   └── cron_batch.sh                  (批量生成脚本)
├── _reports/                          (本报告所在)
└── scenic/5A/                         (景区内容,待生成)
    ├── 人文山水/
    ├── 自然风光/
    ├── 古镇水乡/
    ├── 主题乐园/
    ├── 宗教文化/
    ├── 城市公园/
    └── 红色旅游/
```

### 3. Markdown Schema
- Frontmatter 字段: 25+ 项(名称、等级、分类、坐标、票价等)
- 正文结构: 6 大节(背景/人文/美食/实用/玩法/链接)
- Obsidian 友好: 支持 tags、双链、wikilink

### 4. 5A 景区主清单
- **数据源**: GitHub 开源 (hudichao + aeryzhao 两个 repo)
- **数量**: 218 个(已去重)
- **数据日期**: 截至 2016-2018 评定批次
- **字段**: id/name/full_name/province/city/level_year/category/baike_url/status
- **分类分布**:
  - 自然风光: 97
  - 人文山水: 58
  - 城市公园: 27
  - 宗教文化: 16
  - 古镇水乡: 10
  - 红色旅游: 7
  - 主题乐园: 3
- **已知问题**: 部分省份/城市解析有误(如"市"被切到 name 末尾), 需阶段 2 用 LLM 二次清洗

### 5. Cron 批处理脚本
- 位置: `~/Documents/LukeKB/_scripts/cron_batch.sh`
- 单批 5 个景区
- 调用 hermes chat -q 走 M2.7
- 自动归类到 scenic/5A/{category}/

## 📊 关键决策

| 决策点 | 选择 | 原因 |
|--------|------|------|
| 存储介质 | Obsidian 风格 markdown | 用户已有 POP-Knowledge-Vault, 复用习惯 |
| 抓取源 | GitHub 开源数据集 | 实时爬文旅部受反爬限制 |
| 分类标准 | 7 大类(人文山水/自然/古镇/乐园/宗教/城市/红色) | 覆盖 4A/5A 主流类型 |
| 模型 | M2.7 (而非 M3) | 用户明确要求 |
| 首批范围 | 5A 218 个(非 4A 4000+) | 5A 是头部,先打底 |

## ⏭️ 阶段 2 计划(待用户确认启动)

**目标**: 用 LLM 生成 5-10 个样板景区的完整攻略,验证质量

**执行步骤**:
1. 选 8 个分类代表(人文/自然/古镇/乐园/宗教/城市/红色 各 1-2)
2. 调 M2.7 + web 搜索生成 markdown
3. 写入 scenic/5A/{category}/ 目录
4. 用户抽检质量
5. 调优 prompt 与 schema
6. 沉淀成 skill

**预计样板**:
- 腾冲火山热海 (自然)
- 崀山 (自然)
- 三河古镇 (古镇)
- 方特 (乐园)
- 黄山/嵩山/普陀山 (宗教/自然)
- 故宫 (城市公园)
- 韶山 (红色)

**单景区耗时**: 3-5 分钟(LLM) + web 抓取
**总耗时**: 30-50 分钟

## ⚠️ 风险与提示

1. **API Key 安全**: 用户在对话中明文发送过 MiniMax key, 建议**立即去 minimaxi.com 轮换**
2. **数据时效**: 218 个 5A 名单是 2016-2018 批次,新进 5A(2020-2024 批次约 100+)未涵盖
3. **省份解析**: 部分景区 province/city 字段有误,需 LLM 修复
4. **Web 搜索依赖**: Tavily key 未配,需用 hermes 自带 web 工具
5. **TPS 限制**: MiniMax M2.7 RPM 限制未知,需监控

## 📂 关键文件

- 主清单: `~/Documents/LukeKB/_scripts/5a_list.json`
- 待办队列: `~/Documents/LukeKB/_scripts/todo_queue.json`
- Schema 模板: `~/Documents/LukeKB/_templates/scenic-template.md`
- 生成 Prompt: `~/Documents/LukeKB/_templates/scenic-prompt.md`
- 索引: `~/Documents/LukeKB/_index/5A-Index.md`
- 批处理脚本: `~/Documents/LukeKB/_scripts/cron_batch.sh`

---
*阶段 1 完。等待用户确认进入阶段 2。*
