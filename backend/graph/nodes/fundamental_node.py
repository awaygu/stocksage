"""基本面分析节点（MVP 阶段简化版）。"""

from backend.core.event_bus import event_bus
from backend.core.llm_provider import get_llm_for_agent
from backend.data.providers.akshare_provider import akshare_provider
from backend.data.providers.yfinance_provider import yfinance_provider
from backend.graph.state import StockSageState


class FundamentalNode:
    """基本面分析节点。"""

    SYSTEM_PROMPT = """你是一位专业的基本面分析专家。
基于提供的财务数据，进行基本面分析：
1. 分析盈利能力（ROE、净利润率、毛利率）
2. 分析估值水平（PE、PB、PS）
3. 分析成长性（营收增长、利润增长）
4. 分析财务健康状况（资产负债率、现金流）
5. 给出基本面投资评级和理由

请用中文回答，结构清晰。"""

    async def __call__(self, state: StockSageState) -> dict:
        session_id = state.get("session_id", "")
        await event_bus.publish_agent_status(session_id, "fundamental", "running")

        intent = state.get("intent", {})
        stock_codes = intent.get("stock_codes", [])
        markets = intent.get("markets", [])

        if not stock_codes:
            await event_bus.publish_agent_status(session_id, "fundamental", "skipped")
            return {
                "agent_results": {
                    "fundamental": {
                        "agent_id": "fundamental",
                        "status": "skipped",
                        "data": {},
                        "summary": "无股票代码，跳过基本面分析",
                    }
                }
            }

        # 获取财务数据
        financial_data = {}
        summaries = []

        for code in stock_codes:
            market = "CN" if code.isdigit() and len(code) == 6 else "US"
            try:
                if market == "CN":
                    income = await akshare_provider.get_financial_report(code, "income")
                    financial_data[code] = {"income": income}
                    if income:
                        latest = income[0] if income else {}
                        summaries.append(f"{code}(A股): 最新财报 - {latest}")
                else:
                    financials = await yfinance_provider.get_financials(code)
                    financial_data[code] = financials
                    summaries.append(f"{code}(美股): 财务数据已获取")
            except Exception as e:
                summaries.append(f"{code}: 财务数据获取失败 - {e}")

        # 使用 LLM 分析
        llm = get_llm_for_agent("fundamental")

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"请对以下股票进行基本面分析：\n\n{'\n'.join(summaries)}\n\n请给出详细的基本面分析结论。"}
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
                    "data": financial_data,
                    "summary": summary,
                }
            }
        }
