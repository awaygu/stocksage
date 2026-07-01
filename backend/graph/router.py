"""LangGraph 条件路由逻辑 - 根据意图决定工作流走向。"""

from backend.graph.state import StockSageState


def route_by_intent(state: StockSageState) -> str:
    """根据意图路由到下一个节点。

    返回下一个节点的名称。
    """
    intent = state.get("intent", {})
    intent_type = intent.get("intent_type", "chat")
    required_agents = intent.get("required_agents", [])

    # 聊天场景：直接到 synthesis
    if intent_type == "chat":
        return "synthesis"

    # 价格查询：只需要 market_data
    if intent_type == "price_query":
        return "market_data"

    # 技术分析：需要 market_data -> technical
    if intent_type == "technical_analysis":
        return "market_data"

    # 基本面分析：直接到 fundamental
    if intent_type == "fundamental_analysis":
        return "fundamental"

    # 新闻分析
    if intent_type == "news_analysis":
        return "market_data"

    # 综合研究/风险评估：从 market_data 开始
    return "market_data"


def should_continue(state: StockSageState) -> str:
    """判断是否继续执行。"""
    status = state.get("status", "")
    if status == "error":
        return "end"
    return "continue"
