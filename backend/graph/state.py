"""LangGraph State 定义 - 所有 Agent 共享的全局状态."""

from typing import Annotated, Literal, TypedDict

from langgraph.graph.message import add_messages


class IntentResult(TypedDict, total=False):
    """意图解析结果."""

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
    required_agents: list[str]  # 需要调用的 Agent 列表
    confidence: float  # 意图识别置信度
    user_query: str  # 原始用户query


class AgentResult(TypedDict, total=False):
    """单个 Agent 的执行结果."""

    agent_id: str
    status: Literal["running", "completed", "failed", "skipped"]
    data: dict  # Agent 产生的结构化数据
    summary: str  # Agent 产出的文本摘要
    charts: list[str]  # 生成的图表文件名列表
    error: str | None  # 错误信息


class SynthesisResult(TypedDict, total=False):
    """综合分析结果."""

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
    current_query: str  # 当前用户query
    session_id: str  # 会话ID

    # === 意图与路由 ===
    intent: IntentResult  # 意图解析结果
    active_agents: list[str]  # 需要激活的 Agent 列表

    # === Agent 执行结果 ===
    agent_results: Annotated[dict[str, AgentResult], lambda x, y: {**x, **y}]  # 各 Agent 结果

    # === 综合分析与报告 ===
    synthesis: SynthesisResult  # 综合分析结果
    report: str  # 最终报告 (Markdown)

    # === 运行时状态 ===
    status: Literal[
        "idle",
        "routing",
        "collecting",
        "analyzing",
        "synthesizing",
        "reporting",
        "completed",
        "error",
    ]
    error_message: str  # 错误信息


def merge_agent_results(old: dict[str, AgentResult], new: dict[str, AgentResult]) -> dict[str, AgentResult]:
    """合并 Agent 结果，新值覆盖旧值。"""
    return {**old, **new}
