"""LangGraph State 定义 - 所有 Agent 共享的全局状态.

采用 Plan-and-execute 架构:Planner 产出带依赖的任务 DAG,
静态图按拓扑执行,未激活的 Agent 走 skipped 跳过逻辑。
"""

from typing import Annotated, Literal, TypedDict

from langgraph.graph.message import add_messages


class IntentResult(TypedDict, total=False):
    """意图解析结果(Planner 内部使用,不直接驱动图拓扑)."""

    intent_type: Literal[
        "price_query",
        "technical_analysis",
        "fundamental_analysis",
        "news_analysis",
        "comprehensive_research",
        "risk_assessment",
        "industry_comparison",
        "macro_analysis",
        "chat",
    ]
    stock_codes: list[str]  # 解析出的股票代码
    markets: list[Literal["CN", "US", "HK"]]  # 涉及的市场
    timeframe: str  # 时间范围
    confidence: float  # 意图识别置信度
    user_query: str  # 原始用户 query


class TaskItem(TypedDict):
    """计划中的单个任务(粗粒度: 一个 task 对应一个 agent 调用)."""

    id: str  # 任务 ID,如 "T1"
    agent: str  # 目标 agent 标识,如 "market_data"
    depends_on: list[str]  # 依赖的前置任务 ID
    params: dict  # 传给 agent 的参数(如股票代码)


class PlanResult(TypedDict):
    """Planner 产出的执行计划 - 带依赖的任务 DAG."""

    intent_type: str  # 意图类型(冗余存一份,方便下游读取)
    stock_codes: list[str]
    markets: list[str]
    timeframe: str
    tasks: list[TaskItem]  # 拓扑有序的任务列表


class AgentResult(TypedDict, total=False):
    """单个 Agent 的执行结果."""

    agent_id: str
    status: Literal["running", "completed", "failed", "skipped"]
    data: dict  # Agent 产生的结构化数据
    summary: str  # Agent 产出的文本摘要
    charts: list[str]  # 生成的图表文件名列表
    error: str | None  # 错误信息


class SynthesisResult(TypedDict, total=False):
    """综合分析结果(report agent 内部使用,synthesis 已并入 report)."""

    investment_rating: Literal["强买", "买入", "持有", "卖出", "强卖", ""]
    confidence: float
    key_points: list[str]
    risks: list[str]
    opportunities: list[str]
    conclusion: str


class StockSageState(TypedDict, total=False):
    """LangGraph 全局状态定义。

    所有 Agent 通过此状态共享数据。
    使用 Annotated 指定 reducer 函数来处理状态更新。
    """

    # === 对话上下文 ===
    messages: Annotated[list, add_messages]  # 对话历史 (LangGraph 自动合并)
    current_query: str  # 当前用户 query
    session_id: str  # 会话 ID

    # === 意图与计划 (Plan-and-execute) ===
    intent: IntentResult  # 意图解析结果
    plan: PlanResult  # 执行计划(带依赖的任务 DAG)
    active_agents: list[str]  # 需要激活的 agent 列表(dispatcher 写入)
    task_status: Annotated[dict[str, str], lambda x, y: {**x, **y}]  # 任务 ID -> 状态

    # === Agent 执行结果 ===
    agent_results: Annotated[dict[str, AgentResult], lambda x, y: {**x, **y}]  # 各 agent -> 结果

    # === 报告(synthesis 已并入 report) ===
    synthesis: SynthesisResult  # report agent 内部填充
    report: str  # 最终报告 (Markdown)

    # === 运行时状态 ===
    status: Literal[
        "idle",
        "planning",
        "dispatching",
        "collecting",
        "analyzing",
        "reporting",
        "completed",
        "error",
    ]
    error_message: str  # 错误信息


def merge_agent_results(old: dict[str, AgentResult], new: dict[str, AgentResult]) -> dict[str, AgentResult]:
    """合并 Agent 结果,新值覆盖旧值。"""
    return {**old, **new}
