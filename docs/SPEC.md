# StockSage 软件设计规格文档 (SDD)

> 版本: 1.0.0 · 更新: 2026-07-23 · 状态: 早期纵切阶段(P0 阻断已解除,price_query 链路跑通,37 测试通过)

本文档驱动后续开发 (SDD-driven): 每个任务完成后须更新本文档对应章节的进度状态与完成证据,保持文档与代码一致。

---

## 0. 阅读顺序

1. [§1 产品概述](#1-产品概述) — 这是什么、给谁用
2. [§2 系统架构](#2-系统架构) — 架构图与组件职责
3. [§3 数据流与状态](#3-数据流与状态) — 一次请求的完整流转
4. [§4 组件规格](#4-组件规格) — 每个模块的行为契约(开发依据)
5. [§5 任务计划与进度](#5-任务计划与进度) — 带状态的任务清单(SDD 驱动核心)
6. [§6 待实现规格](#6-待实现规格) — 未完成模块的目标规格
7. [§7 技术约束与决策](#7-技术约束与决策)

---

## 1. 产品概述

### 1.1 定位

StockSage 是一个**多 Agent 股票研究系统**。用户用自然语言提问(如"分析一下贵州茅台"、"宁德时代技术面如何"),后端多个专业 AI Agent 协作分析,最终产出一份结构化 Markdown 投资研究报告(含投资评级、市场数据、技术面、基本面、综合结论、风险提示)。前端通过 WebSocket 实时展示各 Agent 执行状态,报告最终一次性返回。

### 1.2 目标用户

个人投资者 / 股票研究者,希望通过 AI 协作快速获得结构化、有依据的标的分析,而非单一 LLM 的笼统回答。

### 1.3 核心价值

- **多视角综合**:技术面、基本面、新闻、宏观、行业、风险多 Agent 各司其职,再汇合成报告,比单 prompt 更全面。
- **有依据**:报告章节对应真实数据源(行情、财务),而非凭空生成。
- **可观测**:用户能看到哪些 Agent 在跑、哪些被跳过、执行状态实时更新。

### 1.4 MVP 边界(当前阶段)

- A 股为主(Tushare 数据源),港股/美股代码识别但数据获取待接入。
- 文字报告为主,图表生成尚未实现。
- 单会话、无历史持久化(内存事件总线)。

---

## 2. 系统架构

### 2.1 架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         前端 (Vue 3 + TS + Tailwind 4)              │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────────┐  │
│  │ ChatInput    │  │ ChatContainer │→ │ AgentStatus(实时状态面板) │  │
│  └──────┬───────┘  └───────┬───────┘  └──────────────────────────┘  │
│         │ query            │ WebSocket /ws/stream/{session_id}      │
│         │                  │ (agent_status / report / status / error)│
└─────────┼──────────────────┼──────────────────────────────────────┘
          │ REST POST /api/chat (同步) | /api/chat/stream (SSE)
          ▼                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      后端 (FastAPI + uvicorn)                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  api/chat.py    api/ws.py    main.py(lifespan 加载 graph)    │  │
│  └─────────────────────────────┬────────────────────────────────┘  │
│                                │ graph.ainvoke / astream_events    │
│                                ▼                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              LangGraph 静态多 Agent 工作流                    │  │
│  │                                                                │  │
│  │  ┌─────────┐    ┌────────────┐                                  │  │
│  │  │ planner │───→│ dispatcher │ (标记 active_agents)             │  │
│  │  └─────────┘    └─────┬──────┘                                  │  │
│  │  (LLM 解析意图+代码    │ 并行扇出(LangGraph 多边 join 语义)      │  │
│  │   规则模板产 DAG)      │                                         │  │
│  │      ┌────────────────┼────────────────────┐                   │  │
│  │      ▼        ▼       ▼       ▼     ▼      ▼                   │  │
│  │  market_data technical fundamental news macro industry risk   │  │
│  │  (Tushare)  (stub)   (stub)   (stub)(stub)(stub)(stub)          │  │
│  │      │        │       │       │     │      │            │     │  │
│  │      └────────┴───────┴───┬───┴─────┴────────────┘            │  │
│  │                            ▼                                   │  │
│  │                        ┌──────┐                                │  │
│  │                        │report│ (汇总摘要+LLM 产报告+兜底)     │  │
│  │                        └──┬───┘                                │  │
│  │                           └──→ END                             │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         ▲ 事件                  ▲ 数据                              │
│  ┌──────┴────────┐    ┌──────────┴───────────────────────────────┐  │
│  │ core/event_bus│    │ data/ (cache + tushare provider)         │  │
│  │ (内存发布订阅)│    │   cache.py · providers/tushare_provider  │  │
│  └──────────────┘    └──────────────────────────────────────────┘  │
│         ▲                          ▲                               │
│  ┌──────┴───────┐          ┌────────┴─────────────────────────┐   │
│  │ core/        │          │ LLM (langchain-openai / MockLLM)  │   │
│  │ llm_provider │          │ Tushare Pro API (A股, 2159 积分)   │   │
│  └──────────────┘          └──────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
        ▲                                                ▲
        │ (预留, 当前空壳)                                │
┌───────┴──────────┐                            ┌────────┴────────┐
│ mcp_servers/     │                            │  Redis (规划,   │
│ market_data      │                            │  当前未接入)    │
│ news_mcp         │                            └─────────────────┘
│ analysis_tools   │
│ visualization    │
└──────────────────┘
```

### 2.2 架构风格:Plan-and-execute(静态图 + 跳过逻辑)

核心特征:
- **静态图一次建好所有候选 agent 节点**,dispatcher 不改变拓扑,只决定"激活哪些"。
- 各 agent 节点入口读 `active_agents`,未激活走 `skip_agent` 产出 skipped 结果。
- LangGraph 的多边扇出/汇入天然提供并行与 join 语义,无需手动管理线程/任务调度。
- LLM **不产生拓扑**:LLM 只做意图识别 + 股票代码提取,DAG 由纯规则模板(`graph/router.py:build_plan`)生成,避免 LLM 幻构 agent 名或循环依赖。

### 2.3 分层职责

| 层 | 目录 | 职责 | 状态 |
|---|---|---|---|
| API 层 | `backend/api/` | REST/SSE/WebSocket 入口,序列化 | ✅ 完成 |
| 工作流层 | `backend/graph/` | LangGraph 图、节点、DAG 模板、状态定义 | ✅ 完成(骨架) |
| Agent 层 | `backend/agents/` | 可复用 Agent 业务逻辑(当前仅 planner、market_data) | ⚠️ 部分 |
| 核心层 | `backend/core/` | LLM provider、事件总线 | ✅ 完成 |
| 数据层 | `backend/data/` | 缓存、数据源 provider | ✅ 完成(P0) |
| 前端 | `frontend/` | 聊天 UI、Agent 状态可视化 | ✅ 完成 |
| MCP | `mcp_servers/` | 外部工具服务(预留) | ❌ 空壳 |

---

## 3. 数据流与状态

### 3.1 一次请求的完整流转(以"分析一下 600519"为例)

```
用户输入 → ChatInput.sendQuery → WebSocket {type:query, content:"分析一下 600519"}
  → ws._handle_query → graph.ainvoke(initial_state)
  → planner: LLM 解析 → intent={type:comprehensive_research, codes:["600519"]}
              + build_plan 产 DAG: T1 market_data → (T2 tech, T3 fund, T4 news) → T5 report
  → dispatcher: active_agents = [market_data, technical, fundamental, news, report]
  → 并行扇出:
      market_data: 走真实 Tushare,获 K线/报价/基础信息 → emit agent_status:completed
      technical:   读取 market_data 结果,把 K 线摘要喂 LLM(无真算指标) → completed
      fundamental: LLM 凭代码给框架性结论(无财务数据) → completed
      news:        LLM 凭代码给情绪分析(无新闻数据) → completed
      (macro/industry/risk 未激活 → skipped)
  → report: 汇总 4 个 completed agent 摘要 → LLM 产 Markdown 报告 → emit completed
  → ws 发送 {type:report, content:报告} + {type:status, status:completed}
  → 前端 report ref 更新 → ChatMessage 渲染 Markdown
```

### 3.2 全局状态 (StockSageState)

`backend/graph/state.py` 定义,LangGraph reducer 处理合并:

| 字段 | 类型 | 合并策略 | 用途 |
|---|---|---|---|
| `messages` | list | `add_messages` | 对话历史 |
| `current_query` | str | 覆盖 | 当前用户 query |
| `session_id` | str | 覆盖 | 会话标识 |
| `intent` | IntentResult | 覆盖 | 意图解析结果 |
| `plan` | PlanResult | 覆盖 | 执行计划(带依赖 DAG) |
| `active_agents` | list | 覆盖 | 需激活的 agent |
| `task_status` | dict | `{**x, **y}` | 任务 ID → 状态 |
| `agent_results` | dict | `{**x, **y}` | 各 agent → 结果 |
| `report` | str | 覆盖 | 最终 Markdown 报告 |
| `status` | Literal | 覆盖 | 运行时状态机 |

### 3.3 意图 → DAG 模板映射

`graph/router.py:build_plan` 的规则表:

| 意图 | 任务序列(依赖) |
|---|---|
| `price_query` | market_data → report |
| `technical_analysis` | market_data → technical → report |
| `fundamental_analysis` | market_data → fundamental → report |
| `news_analysis` | market_data → news → report |
| `risk_assessment` | market_data → (technical, fundamental) → risk → report |
| `comprehensive_research` | market_data → (technical, fundamental, news) → report |
| `industry_comparison` | market_data → industry → report |
| `macro_analysis` | macro → report |
| `chat` / 未知 | report (单任务) |

---

## 4. 组件规格

> 每个组件给出"职责 / 输入 / 输出 / 当前状态"。开发依据此契约;`✅ 已实现 / ⚠️ 部分 / ❌ 待实现`。

### 4.1 API 层

#### 4.1.1 `backend/api/chat.py` — REST/SSE 接口 ✅
- **职责**: 提供同步与流式两种调用方式
- **POST /api/chat**: 构建初始 state → `graph.ainvoke` → 返回 `{session_id, status, report}`
- **POST /api/chat/stream**: SSE,基于 `graph.astream_events(v2)`,在 `on_chain_end` 且 `output.report` 存在时推送
- **已知问题**: SSE 当前仅在 `on_chain_end` 推送 report,缺乏真正的逐 token 流式(见 §6.3)

#### 4.1.2 `backend/api/ws.py` — WebSocket 接口 ✅
- **职责**: 实时推送 Agent 状态与最终报告
- **流程**: accept → 订阅 `session:{session_id}` 事件 → 收到 `{type:query}` 触发 `_handle_query` → `graph.ainvoke` → 推送 `{type:report}` + `{type:status:completed}`
- **依赖**: EventBus 把 agent 状态推到订阅者
- **已知问题**: agent 状态通过 EventBus 自动推送,但 report 是 invoke 结束后**单次发送**,非流式(见 §6.3)

### 4.2 工作流层

#### 4.2.1 `backend/graph/state.py` — 全局状态定义 ✅
- 见 §3.2。`AgentResult` 含 `status: running|completed|failed|skipped`、`data`、`summary`、`charts`、`error`。

#### 4.2.2 `backend/graph/graph_builder.py` — 静态图构建 ✅
- **拓扑**: planner → dispatcher → [7 分析 agent] → report → END
- `ANALYSIS_AGENTS = [market_data, technical, fundamental, news, macro, industry, risk]`
- dispatcher 扇出到全部 7 个;各 agent 自行判断激活/跳过;report 汇合所有前驱

#### 4.2.3 `backend/graph/router.py` — DAG 模板表 ✅
- `build_plan(intent, codes, markets, timeframe, query) -> PlanResult`
- `validate_plan(plan) -> list[str]`: 校验 agent 名合法、依赖存在、无循环依赖(DFS)
- **设计原则**: 拓扑由规则生成,与 LLM 解耦,可纯单测

#### 4.2.4 `backend/graph/nodes/dispatcher_node.py` — 调度分发 ✅
- 读 `plan.tasks`,去重保序提取 agent 写入 `active_agents`,初始化 `task_status`
- 不做执行决策,只做标记

#### 4.2.5 `backend/graph/nodes/common.py` — 跳过逻辑 ✅
- `is_agent_active(state, agent_id)`: 判断 agent 是否在 active_agents
- `skip_agent(state, agent_id, reason)`: 产出 skipped 结果 + 发布事件

### 4.3 Agent 层

#### 4.3.1 `backend/agents/base.py` — Agent 基类 ✅
- 抽象基类,提供 `call_llm`(走 `get_llm_for_agent`)、`create_result`(标准 AgentResult)
- 子类实现 `_default_system_prompt` + `run`

#### 4.3.2 `backend/agents/router.py` — PlannerAgent ✅
- **混合策略**: LLM 解析意图+代码(JSON 输出) → LLM 失败走 `_fallback_intent`(关键词规则) → 无代码用正则补充 `_extract_stock_codes`
- `_detect_markets`: 6位数字→CN, 5位数字→HK, 字母→US
- 产出 `intent` + `plan`(调 `build_plan`) + `active_agents` + `task_status`
- **已知限制**: 纯名称(如"贵州茅台")无数字串可提取,fallback 时 `stock_codes` 为空(测试已记录此预期行为);需 LLM 或名称映射补充

#### 4.3.3 `backend/agents/market_data.py` — MarketDataAgent ✅
- **职责**: 获取 K 线(daily)、实时报价、基础信息(名称/行业)
- **流程**: 读 `plan.stock_codes` → 缓存命中则取缓存,否则 `tushare_provider` 取数 → 缓存 → 生成摘要(名称、价格、涨跌幅、区间高低、成交量)
- `_timeframe_to_limit`: 年→250, 季→65, 周→5, 默认→30
- **状态**: data 层就位后链路打通,4 项测试通过(含缓存命中 `first is second`、错误代码兜底)

### 4.4 核心层

#### 4.4.1 `backend/core/llm_provider.py` — LLM Provider ✅
- `get_llm(model, temperature)`: 有 API key 用 ChatOpenAI(max_retries=3),无则 MockLLM
- `get_llm_for_agent(agent_id)`: planner/router 温度 0.05, report 0.3, 其余 0.1
- **MockLLM**: 按消息关键词返回预设模拟响应(路由/技术/基本面/综合/报告),支持离线演示与测试
- **已知问题**: `get_llm` 用 `@lru_cache`,模型名作为缓存的 key 但函数只接受 model/temperature,意味着不同 agent_id 调用会复用同温度的实例——实际依赖 `get_llm_for_agent` 的温度差异化,逻辑可用但缓存粒度需注意

#### 4.4.2 `backend/core/event_bus.py` — 事件总线 ✅
- 内存发布订阅,`asyncio.Lock` 保护订阅者列表
- `publish_agent_status`: 推 `{type:agent_status, session_id, agent_id, status, data}` 到 `session:{id}` 和 `all_sessions`
- `publish_stream_chunk`: 推流式输出块(当前无人调用,为未来流式报告预留)

### 4.5 数据层 ✅(P0 完成)

> 以下为组件契约(已实现)。实现时依据测试文件反推的接口契约。

#### 4.5.1 `backend/data/cache.py` — 数据缓存 ✅
- **类**: `DataCache`
- **单例**: `data_cache`(模块级)
- **方法**(依据 test_cache.py):
  - `get_kline(code, market, period) -> list[dict] | None`
  - `set_kline(code, market, period, data, ttl=?)`
  - `get_quote(code, market) -> dict | None`
  - `set_quote(code, market, data, ttl=?)`
  - `get_basic(code, market) -> dict | None`
  - `set_basic(code, market, data, ttl=?)`
  - `clear()`
- **契约**: TTL 过期失效(惰性删除);不同 symbol/market/period 隔离;命中返回同一对象引用(`first is second`);默认 TTL:K线 1h/报价 1min/基础 1d;`ttl<=0` 视为永不过期
- **实现**: `_Entry(value, expire_at)` + 三组独立 dict(kline/quote/basic);`_get`/`_set` 静态方法复用

#### 4.5.2 `backend/data/providers/tushare_provider.py` — Tushare 数据源 ✅
- **类**: `TushareProvider` + 懒加载单例 `tushare_provider`(`_LazyProvider` 代理,首次调用才初始化,避免无 token 时 import 失败)
- **函数**: `to_ts_code(code) -> str`: 沪市 `600/688/9xx→.SH`, 深市/创业板 `000/001/002/003/300/301→.SZ`, 已带后缀/港股/美股原样返回
- **方法**(依据 test_tushare_provider.py,**均为 async**,同步实现经 `asyncio.to_thread` 放线程池):
  - `get_kline(code, period="daily", limit=30) -> list[dict]`: 字段 `date, open, high, low, close, volume`,按日期升序(daily 降序翻转)
  - `get_realtime_quote(code) -> dict`: 字段 `name, ts_code, price, open, high, low, pre_close`。⚠️ **退化实现**: `realtime_quote` 接口需较高积分(2159 不可用),取 `daily` 最新交易日,`close` 作为 `price`
  - `get_basic_info(code) -> dict`: 字段 `ts_code, name, industry, area, list_date`(走 stock_basic)
  - `get_kline_basic(code, limit) -> list[dict]`: 字段 `date, close, pe, pe_ttm, pb, ps, turnover_rate, total_mv, circ_mv`(走 daily_basic)
- **依赖**: `tushare` 包;`settings.tushare_token`

### 4.6 前端 ✅

#### 4.6.1 `frontend/src/composables/useWebSocket.ts`
- 连接 `ws://host/ws/stream/{sessionId}`,维护 `isConnected / isLoading / agentStatuses / report / error`
- 消息处理: `status`(started 重置 / completed)、`agent_status`(更新状态表)、`report`(写入报告)、`error`
- **已知问题**: `sessionId = crypto.randomUUID()` 在组件挂载时生成,每次刷新换新——无会话恢复

#### 4.4.2 前端组件
- `App.vue`: 深色主题布局,头部 + ChatContainer
- `ChatContainer.vue`: 消息列表、Agent 状态面板、错误提示、加载动画、示例问题
- `ChatMessage.vue`: 用户/助手气泡,助手消息走 `vue-markdown-render` 渲染 Markdown
- `AgentStatus.vue`: Agent 状态徽章(图标 + 标签 + 颜色 + 脉冲动画)
- **已知问题**: `agentLabels`/`agentIcons` 用 `router`/`news_sentiment`/`synthesis`,后端实际是 `planner`/`news`/无 synthesis → 部分状态显示为默认图标与原始 key

---

## 5. 任务计划与进度

> 状态图例: `[x]` 完成 · `[~]` 进行中/部分 · `[ ]` 待办 · `[!]` 阻断

### 5.1 P0 — 阻断项(✅ 已全部完成,后端可启动)

| # | 任务 | 状态 | 证据/说明 |
|---|---|---|---|
| P0-1 | 实现 `backend/data/cache.py` | `[x]` | ✅ 已实现 DataCache + data_cache 单例;test_cache.py 4 项全过(TTL/隔离/引用相等) |
| P0-2 | 实现 `backend/data/providers/tushare_provider.py` | `[x]` | ✅ 已实现 to_ts_code + TushareProvider(4 方法,async + asyncio.to_thread);test_tushare_provider.py 6 项全过(真实 API) |
| P0-3 | 安装缺失依赖(langgraph/tushare 等) | `[x]` | ✅ tushare/pandas/fastapi/langchain_openai 已存在;langgraph 已安装;import 链路打通 |
| P0-4 | 验证后端可启动 + price_query 链路端到端跑通 | `[x]` | ✅ `from backend.main import app` 成功;test_graph.py price_query 端到端用例通过(真实 Tushare);全套 37 测试通过 |

**阻断链路(已解除)**: ~~market_data.py import data 层 → import 失败~~ → 现已修复,data 层就位,后端可启动。`realtime_quote` 接口受积分限制(2159 不可用),`get_realtime_quote` 退化为 daily 最新交易日 close 作为 price,字段契约不变。

### 5.2 P1 — 核心链路真实化

| # | 任务 | 状态 | 证据/说明 |
|---|---|---|---|
| P1-1 | technical agent 接入真实指标计算(MA/MACD/RSI/KDJ) | `[ ]` | 当前仅把 K 线摘要丢 LLM,无真算;见 §6.1.1 |
| P1-2 | fundamental agent 接入 Tushare 财务接口 | `[ ]` | 当前 LLM 凭代码给框架结论,无财务数据;见 §6.1.2 |
| P1-3 | news agent 接入新闻数据源 | `[ ]` | 当前纯 LLM 情绪分析,无新闻数据;见 §6.1.3 |
| P1-4 | macro agent 接入宏观数据源 | `[ ]` | 当前纯 stub;见 §6.1.4 |
| P1-5 | industry agent 接入行业数据 + 同业对比 | `[ ]` | 当前纯 stub;见 §6.1.5 |
| P1-6 | risk agent 接入风险量化指标 | `[ ]` | 当前汇总上游摘要,无独立风险量化;见 §6.1.6 |

### 5.3 P1 — 一致性 / 健壮性

| # | 任务 | 状态 | 证据/说明 |
|---|---|---|---|
| P1-7 | 修复前端 AgentStatus label/icon 与后端 agent_id 对齐 | `[ ]` | 前端用 `router`/`news_sentiment`/`synthesis`,后端是 `planner`/`news`/无;见 §6.4.1 |
| P1-8 | Planner 纯名称 query 的股票代码解析 | `[ ]` | "贵州茅台"无数字,fallback 时 codes 为空;需 LLM 名称映射或代码字典;见 §6.2.1 |
| P1-9 | 缓存层接入 Redis(替换/补充内存缓存) | `[ ]` | config 有 REDIS_URL 但未用;见 §6.5.1 |
| P1-10 | 图表生成能力 | `[ ]` | state 有 `charts` 字段但无 agent 产出;见 §6.6 |

### 5.4 P2 — 增强 / 工程化

| # | 任务 | 状态 | 证据/说明 |
|---|---|---|---|
| P2-1 | MCP 服务落地(4 个空壳目录) | `[ ]` | mcp_servers/ 下 4 个空 __init__.py;见 §6.7 |
| P2-2 | 会话历史持久化 + 恢复 | `[ ]` | 当前内存 EventBus,刷新即丢;sessionId 每次 randomUUID;见 §6.5.2 |
| P2-3 | 报告真正流式输出(token 级) | `[ ]` | report 单次发送,非逐 token;EventBus 有 `publish_stream_chunk` 但无调用;见 §6.3 |
| P2-4 | 港股/美股数据源接入 | `[ ]` | 代码识别但无取数;requirements 有 yfinance;见 §6.1.7 |
| P2-5 | README 与实际技术栈对齐(React→Vue) | `[ ]` | README 写 React+Tailwind,实际是 Vue 3 |
| P2-6 | 依赖锁定与 lockfile(pip-tools / uv lock) | `[ ]` | 仅有 requirements.txt 宽版本 |
| P2-7 | CI / 预提交钩子(ruff/black/mypy/pytest) | `[ ]` | pyproject 有配置但无 CI 配置文件 |

### 5.5 进度汇总

```
完成度概览 (按模块):
  API 层       ████████████████████ 100%  (REST/SSE/WS)
  工作流层     ███████████████████░  90%  (骨架完整,stub agent 待真实化)
  核心层       ████████████████████ 100%  (LLM provider + EventBus)
  数据层       ████████████████████ 100%  (cache + tushare provider,P0 完成)
  前端         ████████████████████ 100%  (聊天 UI + 状态可视化)
  MCP          ░░░░░░░░░░░░░░░░░░░░   0%  (空壳)

关键链路打通情况:
  price_query (market_data → report)         [x] 已跑通 (真实 Tushare, 37 测试通过)
  technical_analysis                          [~] 骨架在,指标未真算
  fundamental/news/macro/industry/risk        [~] 骨架在,数据未接
  chat (report 单任务)                         [x] 可跑 (MockLLM 下)
```

---

## 6. 待实现规格

> 此节是 P1/P2 任务的**目标行为契约**,作为开发依据。完成时回写 §5 进度并附完成证据。

### 6.1 各 Agent 真实化

#### 6.1.1 technical agent — 技术指标计算(P1-1)
- **输入**: `agent_results.market_data.data[code].kline`
- **应做**:
  - 用 pandas / pandas-ta 或自实现计算 MA(5/10/20/60)、MACD(12,26,9)、RSI(14)、KDJ(9,3,3)
  - 判断趋势(均线多空排列)、识别支撑/压力位(近期高低点)
  - 产出**结构化指标数据**写入 `data`,summary 用文字描述关键指标与结论
- **输出**: `data = {code: {ma: {...}, macd: {...}, rsi: ..., kdj: {...}, trend: "...", support: ..., resistance: ...}}`
- **验收**: 对已知 K 线序列,MA/MACD 计算结果与参考值一致(可单测固定数据)

#### 6.1.2 fundamental agent — 财务数据接入(P1-2)
- **应做**: 调 Tushare 财务接口(income/balancesheet/cashflow/daily_basic)取营收、净利润、ROE、毛利率、PE/PB、资产负债率、现金流
- **输出**: `data = {code: {roe, pe, pb, revenue_growth, ...}}`,summary 含估值判断
- **验收**: 对 600519 取真实财务数据,字段非空且合理

#### 6.1.3 news agent — 新闻情感(P1-3)
- **应做**: 接入新闻源(Tushare 新闻接口 / 外部新闻 API),按 stock_code 拉取近期新闻,LLM 做情感打分与事件影响分析
- **输出**: `data = {code: [{title, date, sentiment: pos/neg/neu, impact}]}`,summary 含整体情绪与关键事件
- **待定**: 新闻源选型(见 §7.3)

#### 6.1.4 macro agent — 宏观数据(P1-4)
- **应做**: 接入宏观指标(GDP/CPI/利率/流动性),分析对股市影响
- **数据源**: Tushare 宏观接口或央行/统计局公开数据
- **输出**: `data = {gdp_growth, cpi, ...}`,summary 含宏观环境判断

#### 6.1.5 industry agent — 行业对比(P1-5)
- **应做**: 按 stock_code 查询所属行业,拉同业代表公司,对比估值/成长/景气度
- **输出**: `data = {industry, peers: [...], comparison: {...}}`

#### 6.1.6 risk agent — 风险量化(P1-6)
- **应做**: 综合技术面波动率、基本面财务风险、估值高位风险,给出下行风险量化
- **输出**: `data = {volatility, max_drawdown, debt_risk, valuation_risk}`,summary 含风险等级

#### 6.1.7 港股/美股数据源(P2-4)
- **应做**: 港股用 Tushare 港股接口或第三方,美股用 yfinance(已在 requirements)
- `_detect_markets` 已能识别市场,需在 market_data 按 market 路由到不同 provider

### 6.2 Planner 增强

#### 6.2.1 纯名称 → 股票代码解析(P1-8)
- **问题**: "贵州茅台现在多少钱" 无数字串,`_extract_stock_codes` 返回空
- **方案选项**:
  - A. LLM 在解析意图时一并输出 stock_codes(当前 prompt 已要求,但 fallback 路径失效)
  - B. 维护名称→代码字典(常见蓝筹)作为 fallback
  - C. Tushare 股票列表做模糊匹配
- **推荐**: A + C 组合,LLM 为主,字典/模糊匹配兜底

### 6.3 报告流式输出(P2-3)
- **现状**: `graph.ainvoke` 同步等全部完成,report 单次发送;SSE 的 `astream_events` 仅在 on_chain_end 推
- **目标**: report agent 用 `llm.astream` 逐 token 产报告,每个 chunk 经 `event_bus.publish_stream_chunk` 推到前端,前端增量渲染
- **影响**: report_node 需改流式;ws/chat_stream 需转发 stream_chunk;前端 ChatMessage 需支持增量拼接

### 6.4 一致性修复

#### 6.4.1 前端 Agent 状态对齐(P1-7)
- **问题**: `AgentStatus.vue` 的 `agentLabels`/`agentIcons` key 与后端 agent_id 不一致
- **修复**: 对齐为后端实际 id:`planner, market_data, technical, fundamental, news, macro, industry, risk, report`(移除 `router`/`news_sentiment`/`synthesis` 或保留兼容映射)

### 6.5 持久化

#### 6.5.1 Redis 缓存(P1-9)
- **现状**: config 有 REDIS_URL,代码未用;DataCache 当前未实现,若实现为内存版则重启失效
- **目标**: DataCache 支持后端可切换(内存 / Redis),行情数据 TTL(如日线 1 天、报价 1 分钟)
- **设计**: 定义 `CacheBackend` 抽象,`MemoryCache` 与 `RedisCache` 实现,配置选择

#### 6.5.2 会话历史(P2-2)
- **现状**: 内存 EventBus,sessionId 每次刷新 randomUUID,无历史
- **目标**: 持久化 messages + report,支持刷新恢复、多会话切换

### 6.6 图表生成(P1-10)
- **现状**: state 有 `charts` 字段,无 agent 产出,前端无渲染
- **目标**: technical agent 产出 K 线 + 指标图(如 plotly/matplotlib → png/base64),前端 ChatMessage 渲染图片
- **关联**: mcp_servers/visualization(§6.7)可作为图表服务

### 6.7 MCP 服务(P2-1)
- **现状**: 4 个空目录(market_data / news_mcp / analysis_tools / visualization)
- **目标**: 将数据获取与工具能力封装为 MCP 服务,供 Agent 通过标准协议调用,解耦数据与逻辑
- **优先级**: P2,在 Agent 真实化(P1)稳定后再抽象为 MCP,避免过早抽象

---

## 7. 技术约束与决策

### 7.1 关键设计决策

| 决策 | 理由 | 位置 |
|---|---|---|
| LLM 不产拓扑,规则模板产 DAG | 避免 LLM 幻构 agent 名 / 循环依赖;可纯单测 | router.py:build_plan |
| 静态图 + 跳过逻辑(非动态建图) | LangGraph 多边扇出/汇入天然并行与 join;一次建图复用 | graph_builder.py |
| MockLLM 降级 | 无 API key 也能跑/演示/测试,不阻塞开发 | llm_provider.py |
| 测试默认 MockLLM,数据保持真实 | 单测不依赖网络,真实 LLM 走 @pytest.mark.integration | conftest.py |
| synthesis 并入 report | 减少节点,综合与成文在同一 prompt 完成 | report_node.py |

### 7.2 技术栈约束

- Python ≥ 3.11,black/isort/ruff/mypy 已配(line-length 100)
- pytest-asyncio `asyncio_mode=auto`,testpaths=tests
- 前端 Vue 3 + Vite 6 + Tailwind 4(非 README 所写 React)
- LLM 走 OpenAI 兼容 API(可接 OpenAI / 国内兼容服务,通过 OPENAI_BASE_URL 配置)

### 7.3 待定决策(需用户确认)

| 项 | 选项 | 影响 |
|---|---|---|
| 新闻数据源 | Tushare 新闻接口 / 第三方财经 API / 网页爬取 | news agent 实现方式与成本 |
| 缓存后端 | 纯内存 / Redis / 可切换 | P1-9 实现范围 |
| 图表方案 | plotly(交互) / matplotlib(静态) / 前端 ECharts 渲染 | P1-10 实现与前端工作量 |
| 是否上 MCP | 现在抽象 vs Agent 稳定后再抽 | P2-1 时机 |

---

## 附录 A: 文件清单与状态

| 路径 | 状态 | 说明 |
|---|---|---|
| backend/main.py | ✅ | FastAPI 入口,lifespan 加载 graph |
| backend/config.py | ✅ | Pydantic Settings,env 读取 |
| backend/api/chat.py | ✅ | REST/SSE |
| backend/api/ws.py | ✅ | WebSocket |
| backend/agents/base.py | ✅ | Agent 基类 |
| backend/agents/router.py | ✅ | PlannerAgent |
| backend/agents/market_data.py | ✅ | 代码完成,数据层就位后链路打通 |
| backend/core/llm_provider.py | ✅ | LLM + MockLLM |
| backend/core/event_bus.py | ✅ | 内存事件总线 |
| backend/graph/state.py | ✅ | 全局状态 |
| backend/graph/graph_builder.py | ✅ | 静态图 |
| backend/graph/router.py | ✅ | DAG 模板 + 校验 |
| backend/graph/nodes/*.py | ✅ | 10 个节点(7 stub + planner/dispatcher/report) |
| backend/data/cache.py | ✅ | 已实现(DataCache + data_cache,TTL/隔离/引用相等) |
| backend/data/providers/tushare_provider.py | ✅ | 已实现(async + to_thread,realtime_quote 退化) |
| backend/tests/*.py | ✅ | 7 个测试文件,全套 37 测试通过 |
| frontend/src/** | ✅ | Vue 3 聊天 UI |
| mcp_servers/*/__init__.py | ❌ | 空壳 |

---

## 附录 B: 验证检查清单(开发完成时勾选)

- [ ] `python -c "from backend.main import app"` 不报错(依赖 P0-1~3)
- [ ] `uvicorn backend.main:app` 启动,`GET /health` 返回 ok
- [ ] `pytest`(不带 token)通过 planner/graph/state/config 测试
- [ ] 配置 TUSHARE_TOKEN 后 `pytest tests/test_tushare_provider.py` 通过
- [ ] 前端 `npm run dev` + 后端启动,WebSocket 连接成功
- [ ] 输入"600519 现在多少钱",price_query 链路返回含真实价格的报告
- [ ] 前端 AgentStatus 正确显示 planner/market_data/report 状态,无默认 fallback 图标
- [ ] 每完成一个任务,回写 §5 状态并附 commit/证据
