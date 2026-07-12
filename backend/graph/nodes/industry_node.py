"""行业对比分析节点 - 纵切阶段 stub(带跳过逻辑)。"""

from backend.core.event_bus import event_bus
from backend.core.llm_provider import get_llm_for_agent
from backend.graph.nodes.common import is_agent_active, skip_agent
from backend.graph.state import StockSageState


class IndustryNode:
    """行业对比分析节点(stub)。"""

    SYSTEM_PROMPT = """你是一位行业研究专家。
对比分析指定行业/板块内的代表性公司,给出行业景气度与竞争格局判断。
请用中文回答,结构清晰。"""

    async def __call__(self, state: StockSageState) -> dict:
        session_id = state.get("session_id", "")

        if not await is_agent_active(state, "industry"):
            return await skip_agent(state, "industry")

        await event_bus.publish_agent_status(session_id, "industry", "running")

        intent = state.get("intent", {})
        codes = intent.get("stock_codes", [])
        query = intent.get("user_query", "")
        codes_str = ", ".join(codes) if codes else "相关板块"

        llm = get_llm_for_agent("industry")
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"请对比分析 {codes_str} 所在行业。用户问题: {query}(纵切阶段数据待接入)"},
        ]
        try:
            response = await llm.ainvoke(messages)
            summary = str(response.content)
        except Exception as e:
            summary = f"行业分析失败: {e}"

        await event_bus.publish_agent_status(session_id, "industry", "completed")
        return {
            "agent_results": {
                "industry": {"agent_id": "industry", "status": "completed", "data": {}, "summary": summary}
            }
        }
