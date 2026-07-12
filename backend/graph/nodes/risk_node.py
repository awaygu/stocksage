"""风险评估节点 - 纵切阶段 stub(带跳过逻辑)。"""

from backend.core.event_bus import event_bus
from backend.core.llm_provider import get_llm_for_agent
from backend.graph.nodes.common import is_agent_active, skip_agent
from backend.graph.state import StockSageState


class RiskNode:
    """风险评估节点(stub)。"""

    SYSTEM_PROMPT = """你是一位风险评估专家。
综合技术面、基本面与市场环境,评估标的主要风险点与下行风险。
请用中文回答,结构清晰。"""

    async def __call__(self, state: StockSageState) -> dict:
        session_id = state.get("session_id", "")

        if not await is_agent_active(state, "risk"):
            return await skip_agent(state, "risk")

        await event_bus.publish_agent_status(session_id, "risk", "running")

        intent = state.get("intent", {})
        codes = intent.get("stock_codes", [])
        agent_results = state.get("agent_results", {})

        # 汇总上游分析结果
        upstream = []
        for aid in ("technical", "fundamental"):
            s = agent_results.get(aid, {}).get("summary", "")
            if s:
                upstream.append(f"【{aid}】{s}")

        codes_str = ", ".join(codes) if codes else "标的"
        llm = get_llm_for_agent("risk")
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"请评估 {codes_str} 的风险。\n上游分析:\n{chr(10).join(upstream)}(纵切阶段部分数据待接入)"},
        ]
        try:
            response = await llm.ainvoke(messages)
            summary = str(response.content)
        except Exception as e:
            summary = f"风险评估失败: {e}"

        await event_bus.publish_agent_status(session_id, "risk", "completed")
        return {
            "agent_results": {
                "risk": {"agent_id": "risk", "status": "completed", "data": {}, "summary": summary}
            }
        }
