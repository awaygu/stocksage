"""宏观分析节点 - 纵切阶段 stub(带跳过逻辑)。"""

from backend.core.event_bus import event_bus
from backend.core.llm_provider import get_llm_for_agent
from backend.graph.nodes.common import is_agent_active, skip_agent
from backend.graph.state import StockSageState


class MacroNode:
    """宏观分析节点(stub)。"""

    SYSTEM_PROMPT = """你是一位宏观经济分析专家。
分析当前宏观经济环境对股市的影响(GDP、CPI、利率、流动性等)。
请用中文回答,结构清晰。"""

    async def __call__(self, state: StockSageState) -> dict:
        session_id = state.get("session_id", "")

        if not await is_agent_active(state, "macro"):
            return await skip_agent(state, "macro")

        await event_bus.publish_agent_status(session_id, "macro", "running")

        intent = state.get("intent", {})
        query = intent.get("user_query", "")

        llm = get_llm_for_agent("macro")
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"请分析当前宏观经济对股市的影响。用户问题: {query}(纵切阶段数据待接入)"},
        ]
        try:
            response = await llm.ainvoke(messages)
            summary = str(response.content)
        except Exception as e:
            summary = f"宏观分析失败: {e}"

        await event_bus.publish_agent_status(session_id, "macro", "completed")
        return {
            "agent_results": {
                "macro": {"agent_id": "macro", "status": "completed", "data": {}, "summary": summary}
            }
        }
