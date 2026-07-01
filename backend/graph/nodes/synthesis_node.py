"""综合分析节点 - 整合所有 Agent 结果，形成投资结论。"""

from backend.core.event_bus import event_bus
from backend.core.llm_provider import get_llm_for_agent
from backend.graph.state import StockSageState


class SynthesisNode:
    """综合分析节点。

    整合 Router、MarketData、Technical、Fundamental 等 Agent 的结果，
    形成统一的投资结论。
    """

    SYSTEM_PROMPT = """你是一位资深投资顾问。
你的任务是基于各专业Agent的分析结果，进行综合判断，形成最终投资结论。

要求：
1. 综合技术面和基本面的结论，给出一致的投资评级
2. 列出关键投资逻辑（2-3条核心观点）
3. 指出主要风险点（1-2条）
4. 给出简洁有力的投资结论

输出格式：
- 投资评级: [强买/买入/持有/卖出/强卖]
- 核心观点:
  1. ...
  2. ...
- 风险提示:
  1. ...
- 结论: ...

请用中文回答，客观理性。"""

    async def __call__(self, state: StockSageState) -> dict:
        session_id = state.get("session_id", "")
        await event_bus.publish_agent_status(session_id, "synthesis", "running")

        agent_results = state.get("agent_results", {})
        intent = state.get("intent", {})
        query = intent.get("user_query", "")

        # 收集所有 Agent 的摘要
        summaries = []
        for agent_id, result in agent_results.items():
            if result and result.get("summary"):
                summaries.append(f"【{agent_id}】\n{result['summary']}\n")

        if not summaries:
            # 没有分析结果，可能是聊天场景
            summary_text = f"用户问题: {query}\n(无专业分析数据)"
        else:
            summary_text = "\n".join(summaries)

        # 使用 LLM 综合
        llm = get_llm_for_agent("synthesis")

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"用户问题: {query}\n\n各Agent分析结果:\n\n{summary_text}\n\n请给出综合投资结论。"}
        ]

        try:
            response = await llm.ainvoke(messages)
            conclusion = str(response.content)
        except Exception as e:
            conclusion = f"综合分析失败: {e}"

        await event_bus.publish_agent_status(session_id, "synthesis", "completed")

        return {
            "synthesis": {
                "conclusion": conclusion,
                "key_points": [],
                "risks": [],
                "opportunities": [],
            },
            "status": "synthesizing",
        }
