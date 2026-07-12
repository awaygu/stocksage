"""新闻情感分析节点 - 纵切阶段 stub(带跳过逻辑)。

真实新闻获取待后续接入(tushare 新闻接口 / 外部新闻 API)。
"""

from backend.core.event_bus import event_bus
from backend.core.llm_provider import get_llm_for_agent
from backend.graph.nodes.common import is_agent_active, skip_agent
from backend.graph.state import StockSageState


class NewsNode:
    """新闻情感分析节点(stub)。"""

    SYSTEM_PROMPT = """你是一位新闻情感分析专家。
基于市场数据与近期新闻,分析市场情绪与事件影响。
请用中文回答,结构清晰。"""

    async def __call__(self, state: StockSageState) -> dict:
        session_id = state.get("session_id", "")

        if not await is_agent_active(state, "news"):
            return await skip_agent(state, "news")

        await event_bus.publish_agent_status(session_id, "news", "running")

        intent = state.get("intent", {})
        codes = intent.get("stock_codes", [])
        codes_str = ", ".join(codes) if codes else "市场"

        llm = get_llm_for_agent("news")
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"请分析 {codes_str} 近期新闻与市场情绪(纵切阶段数据待接入)。"},
        ]
        try:
            response = await llm.ainvoke(messages)
            summary = str(response.content)
        except Exception as e:
            summary = f"新闻分析失败: {e}"

        await event_bus.publish_agent_status(session_id, "news", "completed")
        return {
            "agent_results": {
                "news": {"agent_id": "news", "status": "completed", "data": {}, "summary": summary}
            }
        }
