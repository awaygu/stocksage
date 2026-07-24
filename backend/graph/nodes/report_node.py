"""报告生成节点 - 整合所有激活 agent 的结果,一次产出含投资结论的 Markdown 报告。

synthesis 已并入本节点: 不再有独立 synthesis 节点,综合与成文在同一份 prompt 内完成。
"""

from backend.core.event_bus import event_bus
from backend.core.llm_provider import get_llm_for_agent
from backend.graph.nodes.common import is_agent_active, skip_agent
from backend.graph.state import StockSageState


class ReportNode:
    """报告生成节点。

    汇总各激活 agent 的摘要,产出结构化 Markdown 报告(含综合投资结论)。
    price_query 场景报告聚焦行情数据;无激活分析 agent 时(chat)直接回应。
    """

    SYSTEM_PROMPT = """你是一位专业的投资报告撰写专家。
将各分析 Agent 的结果整合为结构化的 Markdown 投资报告,并在报告内完成综合判断。

报告格式:
# {股票名称} 研究报告

## 一、投资摘要
{一句话摘要}

## 二、市场数据概览
{K线、报价等数据摘要}

## 三、技术面分析
{技术指标和趋势判断;无则省略}

## 四、基本面分析
{财务数据和估值分析;无则省略}

## 五、综合投资结论
{投资评级和核心逻辑 - 你需要在此综合判断}

## 六、风险提示
{风险因素}

要求:
1. 使用 Markdown 格式
2. 内容客观、数据准确,基于提供的真实数据
3. 结论有理有据
4. 语言简洁专业
5. 价格查询场景,聚焦行情数据,可省略无关章节"""

    async def __call__(self, state: StockSageState) -> dict:
        session_id = state.get("session_id", "")

        if not await is_agent_active(state, "report"):
            return await skip_agent(state, "report")

        await event_bus.publish_agent_status(session_id, "report", "running")

        agent_results = state.get("agent_results", {})
        intent = state.get("intent", {})
        plan = state.get("plan", {})
        query = intent.get("user_query", "") or state.get("current_query", "")

        # 收集所有已完成 agent 的摘要(skipped 的跳过)
        parts: list[str] = []
        for agent_id, result in agent_results.items():
            if not result or result.get("status") != "completed":
                continue
            summary = result.get("summary", "")
            if summary:
                parts.append(f"【{agent_id}】\n{summary}")

        sections_text = "\n\n".join(parts) if parts else "(无专业分析数据)"
        stock_codes = plan.get("stock_codes") or intent.get("stock_codes", [])
        stock_str = ", ".join(stock_codes) if stock_codes else "标的"

        llm = get_llm_for_agent("report")
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"请为 {stock_str} 生成投资研究报告。\n\n"
                    f"用户问题: {query}\n\n"
                    f"各 Agent 分析结果:\n{sections_text}\n\n"
                    f"请生成完整的 Markdown 报告(含综合投资结论)。"
                ),
            },
        ]

        try:
            # 流式生成:逐 token 推流,前端边收边渲染
            report = ""
            async for chunk in llm.astream(messages):
                token = str(chunk.content)
                if token:
                    report += token
                    await event_bus.publish_stream_chunk(session_id, token)
        except Exception:
            # LLM 失败:用拼接报告兜底,也经流式推一次,前端仍能看到内容
            report = self._fallback_report(stock_str, query, sections_text)
            await event_bus.publish_stream_chunk(session_id, report)

        await event_bus.publish_agent_status(session_id, "report", "completed")

        return {
            "report": report,
            "status": "completed",
        }

    def _fallback_report(self, stock_str: str, query: str, sections: str) -> str:
        """LLM 失败时的简单拼接报告。"""
        return f"""# {stock_str} 研究报告

> 用户问题: {query}

---

## 分析结果

{sections}

---

*报告生成于 StockSage 多Agent股票研究系统*
"""
