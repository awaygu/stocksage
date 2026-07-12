"""基本面分析节点 - 纵切阶段为带跳过逻辑的 stub。

真实财务数据获取与分析待后续接入(tushare 财务接口 + LLM 分析)。
"""

from backend.core.event_bus import event_bus
from backend.core.llm_provider import get_llm_for_agent
from backend.graph.nodes.common import is_agent_active, skip_agent
from backend.graph.state import StockSageState


class FundamentalNode:
    """基本面分析节点(stub)。"""

    SYSTEM_PROMPT = """你是一位专业的基本面分析专家。
基于提供的财务数据,进行基本面分析:
1. 分析盈利能力(ROE、净利润率、毛利率)
2. 分析估值水平(PE、PB、PS)
3. 分析成长性(营收增长、利润增长)
4. 分析财务健康状况(资产负债率、现金流)
5. 给出基本面投资评级和理由

请用中文回答,结构清晰。"""

    async def __call__(self, state: StockSageState) -> dict:
        session_id = state.get("session_id", "")

        if not await is_agent_active(state, "fundamental"):
            return await skip_agent(state, "fundamental")

        await event_bus.publish_agent_status(session_id, "fundamental", "running")

        intent = state.get("intent", {})
        stock_codes = intent.get("stock_codes", [])

        if not stock_codes:
            await event_bus.publish_agent_status(session_id, "fundamental", "skipped")
            return {
                "agent_results": {
                    "fundamental": {
                        "agent_id": "fundamental",
                        "status": "skipped",
                        "data": {},
                        "summary": "无股票代码,跳过基本面分析",
                    }
                }
            }

        # 纵切阶段: 财务数据获取待接入,先用 LLM 基于代码做占位分析
        llm = get_llm_for_agent("fundamental")
        codes_str = ", ".join(stock_codes)
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"请对 {codes_str} 进行基本面分析(纵切阶段数据待接入,可基于公开认知给出框架性结论)。"},
        ]
        try:
            response = await llm.ainvoke(messages)
            summary = str(response.content)
        except Exception as e:
            summary = f"基本面分析失败: {e}"

        await event_bus.publish_agent_status(session_id, "fundamental", "completed")
        return {
            "agent_results": {
                "fundamental": {
                    "agent_id": "fundamental",
                    "status": "completed",
                    "data": {},
                    "summary": summary,
                }
            }
        }
