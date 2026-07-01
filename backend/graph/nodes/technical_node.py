"""技术分析节点（MVP 阶段简化版）。"""

from backend.core.event_bus import event_bus
from backend.core.llm_provider import get_llm_for_agent
from backend.graph.state import StockSageState


class TechnicalNode:
    """技术分析节点。"""

    SYSTEM_PROMPT = """你是一位专业的技术分析专家。
基于提供的市场数据，进行技术分析：
1. 计算并分析主要技术指标（MA、MACD、RSI、KDJ等）
2. 判断当前趋势（上涨/下跌/震荡）
3. 识别关键支撑位和压力位
4. 给出技术面结论

请用中文回答，结构清晰。"""

    async def __call__(self, state: StockSageState) -> dict:
        session_id = state.get("session_id", "")
        await event_bus.publish_agent_status(session_id, "technical", "running")

        # 获取市场数据结果
        agent_results = state.get("agent_results", {})
        market_data = agent_results.get("market_data", {}).get("data", {})

        if not market_data:
            await event_bus.publish_agent_status(session_id, "technical", "skipped")
            return {
                "agent_results": {
                    "technical": {
                        "agent_id": "technical",
                        "status": "skipped",
                        "data": {},
                        "summary": "无市场数据，跳过技术分析",
                    }
                }
            }

        # 使用 LLM 进行技术分析
        llm = get_llm_for_agent("technical")

        # 构建分析提示
        kline_summary = self._summarize_kline(market_data)

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"请对以下股票进行技术分析：\n\n{kline_summary}\n\n请给出详细的技术分析结论。"}
        ]

        try:
            response = await llm.ainvoke(messages)
            summary = str(response.content)
        except Exception as e:
            summary = f"技术分析失败: {e}"

        await event_bus.publish_agent_status(session_id, "technical", "completed")

        return {
            "agent_results": {
                "technical": {
                    "agent_id": "technical",
                    "status": "completed",
                    "data": market_data,
                    "summary": summary,
                }
            }
        }

    def _summarize_kline(self, market_data: dict) -> str:
        """将K线数据摘要化，减少LLM token消耗。"""
        summaries = []
        for code, data in market_data.items():
            kline = data.get("kline", [])
            quote = data.get("quote", {})
            if kline:
                latest = kline[-1]
                first = kline[0]
                summaries.append(
                    f"股票 {code}:\n"
                    f"  最新价: {latest.get('close')} (日期: {latest.get('date')})\n"
                    f"  区间: {first.get('date')} ~ {latest.get('date')}\n"
                    f"  区间最高: {max(d.get('high', 0) for d in kline)}\n"
                    f"  区间最低: {min(d.get('low', 0) for d in kline)}\n"
                    f"  当前PE: {quote.get('pe', 'N/A')}\n"
                    f"  当前PB: {quote.get('pb', 'N/A')}"
                )
        return "\n\n".join(summaries)
