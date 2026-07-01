"""报告生成节点 - 生成最终的 Markdown 报告。"""

from backend.core.event_bus import event_bus
from backend.core.llm_provider import get_llm_for_agent
from backend.graph.state import StockSageState


class ReportNode:
    """报告生成节点。

    将综合分析结果格式化为 Markdown 报告。
    """

    SYSTEM_PROMPT = """你是一位专业的投资报告撰写专家。
将综合分析结果整理为结构化的 Markdown 投资报告。

报告格式：
# {股票名称} 研究报告

## 一、投资摘要
{一句话摘要}

## 二、市场数据概览
{K线、报价等数据摘要}

## 三、技术面分析
{技术指标和趋势判断}

## 四、基本面分析
{财务数据和估值分析}

## 五、综合投资结论
{投资评级和核心逻辑}

## 六、风险提示
{风险因素}

要求：
1. 使用 Markdown 格式
2. 内容客观、数据准确
3. 结论有理有据
4. 语言简洁专业"""

    async def __call__(self, state: StockSageState) -> dict:
        session_id = state.get("session_id", "")
        await event_bus.publish_agent_status(session_id, "report", "running")

        synthesis = state.get("synthesis", {})
        agent_results = state.get("agent_results", {})
        intent = state.get("intent", {})
        query = intent.get("user_query", "")

        # 收集所有数据用于报告
        market_summary = agent_results.get("market_data", {}).get("summary", "")
        tech_summary = agent_results.get("technical", {}).get("summary", "")
        fund_summary = agent_results.get("fundamental", {}).get("summary", "")
        synthesis_conclusion = synthesis.get("conclusion", "")

        # 使用 LLM 生成报告
        llm = get_llm_for_agent("report")

        stock_codes = intent.get("stock_codes", [])
        stock_str = ", ".join(stock_codes) if stock_codes else "股票"

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"""请为 {stock_str} 生成一份投资研究报告。

用户问题: {query}

市场数据:
{market_summary}

技术面分析:
{tech_summary}

基本面分析:
{fund_summary}

综合结论:
{synthesis_conclusion}

请生成完整的 Markdown 报告。"""}
        ]

        try:
            response = await llm.ainvoke(messages)
            report = str(response.content)
        except Exception:
            # 回退到简单拼接
            report = self._generate_fallback_report(
                stock_str, query, market_summary, tech_summary,
                fund_summary, synthesis_conclusion,
            )

        await event_bus.publish_agent_status(session_id, "report", "completed")

        return {
            "report": report,
            "status": "completed",
        }

    def _generate_fallback_report(
        self,
        stock_str: str,
        query: str,
        market: str,
        tech: str,
        fund: str,
        synthesis: str,
    ) -> str:
        """当 LLM 失败时，生成简单的回退报告。"""
        return f"""# {stock_str} 研究报告

> 用户问题: {query}

---

## 一、市场数据

{market}

## 二、技术面分析

{tech}

## 三、基本面分析

{fund}

## 四、综合结论

{synthesis}

---

*报告生成于 StockSage 多Agent股票研究系统*
"""
