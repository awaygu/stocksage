"""Planner Agent - 解析用户 query,生成带依赖的执行计划 DAG。

混合策略: LLM 解析意图 + 股票代码,规则模板(build_plan)生成 DAG 拓扑。
LLM 不直接产 DAG(避免幻觉 agent 名/循环依赖),只产意图与代码。
"""

import json
import re

from backend.agents.base import BaseAgent
from backend.core.event_bus import event_bus
from backend.graph.router import build_plan
from backend.graph.state import StockSageState


class PlannerAgent(BaseAgent):
    """计划生成 Agent。

    分析用户的自然语言 query,识别意图与股票代码,生成执行 DAG。
    """

    SYSTEM_PROMPT = """你是一位股票研究系统的智能路由助手。你的任务是分析用户的 query,识别用户的真实意图。

**可识别的意图类型(只输出 intent_type 和 stock_codes):**
- price_query: 价格/行情查询("茅台现在多少钱?")
- technical_analysis: 技术分析("分析一下000001的技术面")
- fundamental_analysis: 基本面分析("茅台的估值如何?")
- news_analysis: 新闻/事件分析("最近有什么利好?")
- comprehensive_research: 综合研究("全面分析一下比亚迪")
- risk_assessment: 风险评估("这个股票有风险吗?")
- industry_comparison: 行业对比("对比一下新能源板块")
- macro_analysis: 宏观分析("当前宏观经济对股市的影响")
- chat: 闲聊/打招呼("你好")

**市场代码映射:**
- A股代码: 6位数字,如 000001, 600519, 300750
- 美股代码: 字母,如 AAPL, TSLA, NVDA
- 港股代码: 5位数字,如 00700

**输出格式(严格 JSON,只含以下字段):**
{
    "intent_type": "comprehensive_research",
    "stock_codes": ["600519"],
    "timeframe": "近一个月"
}

**规则:**
1. stock_codes 只包含标准代码,不包含中文名称
2. 如果 query 不涉及具体股票(如宏观分析),stock_codes 为空数组
3. 如果无法识别意图,回退到 chat
"""

    def __init__(self, llm: object | None = None) -> None:
        super().__init__("planner", self.SYSTEM_PROMPT, llm=llm)

    def _default_system_prompt(self) -> str:
        return self.SYSTEM_PROMPT

    def _extract_stock_codes(self, query: str) -> list[str]:
        """从 query 中提取股票代码(正则匹配)。"""
        codes: list[str] = []
        # A股: 6位数字
        codes.extend(re.findall(r"\b\d{6}\b", query))
        # 美股: 1-5位字母大写(排除常见英文单词误判, 要求全大写且<=5)
        us = re.findall(r"\b[A-Z]{1,5}\b", query)
        codes.extend(us)
        # 港股: 5位数字
        codes.extend(re.findall(r"\b\d{5}\b", query))
        # 去重保序
        seen: set[str] = set()
        unique: list[str] = []
        for c in codes:
            if c not in seen:
                seen.add(c)
                unique.append(c)
        return unique

    async def run(self, state: StockSageState) -> dict:
        """执行计划生成。"""
        query = state.get("current_query", "")
        session_id = state.get("session_id", "")

        await event_bus.publish_agent_status(session_id, "planner", "running")

        # 1. LLM 解析意图与代码
        intent_type = "chat"
        stock_codes: list[str] = []
        timeframe = "近一个月"

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"用户query: {query}\n\n请分析并返回JSON。只返回JSON。"},
        ]
        try:
            response = await self.call_llm(messages)
            parsed = self._parse_llm_response(response)
            intent_type = parsed.get("intent_type", "chat")
            stock_codes = parsed.get("stock_codes", [])
            timeframe = parsed.get("timeframe", "近一个月")
        except Exception:
            # LLM 失败时回退到规则匹配
            intent_type, stock_codes = self._fallback_intent(query)

        # LLM 没提取到代码时用正则补充
        if not stock_codes:
            stock_codes = self._extract_stock_codes(query)

        # 判断市场
        markets = self._detect_markets(stock_codes)

        # 2. 规则模板生成 DAG(关键: 不让 LLM 产拓扑)
        plan = build_plan(intent_type, stock_codes, markets, timeframe, query)

        await event_bus.publish_agent_status(
            session_id,
            "planner",
            "completed",
            {"intent_type": intent_type, "task_count": len(plan["tasks"])},
        )

        return {
            "intent": {
                "intent_type": intent_type,
                "stock_codes": stock_codes,
                "markets": markets,
                "timeframe": timeframe,
                "confidence": 0.0,
                "user_query": query,
            },
            "plan": plan,
            "active_agents": list({t["agent"] for t in plan["tasks"]}),
            "task_status": {t["id"]: "pending" for t in plan["tasks"]},
            "status": "planning",
        }

    def _parse_llm_response(self, response: str) -> dict:
        """解析 LLM 返回的 JSON。"""
        start = response.find("{")
        end = response.rfind("}")
        if start >= 0 and end > start:
            return json.loads(response[start : end + 1])
        raise ValueError("LLM 响应无 JSON")

    def _detect_markets(self, codes: list[str]) -> list[str]:
        """根据代码判断市场。"""
        markets: list[str] = []
        for code in codes:
            if code.isdigit() and len(code) == 6:
                markets.append("CN")
            elif code.isdigit() and len(code) == 5:
                markets.append("HK")
            elif code.isalpha():
                markets.append("US")
        return list(dict.fromkeys(markets)) or ["CN"]

    def _fallback_intent(self, query: str) -> tuple[str, list[str]]:
        """LLM 失败时回退到规则匹配(只判意图+代码,DAG 仍由 build_plan 生成)。"""
        q = query.lower()
        codes = self._extract_stock_codes(query)

        if any(k in q for k in ["技术", "macd", "kdj", "均线", "rsi"]):
            return "technical_analysis", codes
        if any(k in q for k in ["基本面", "估值", "pe", "pb", "财报", "利润", "营收"]):
            return "fundamental_analysis", codes
        if any(k in q for k in ["新闻", "利好", "利空", "事件"]):
            return "news_analysis", codes
        if any(k in q for k in ["风险", "危险", "下跌"]):
            return "risk_assessment", codes
        if any(k in q for k in ["行业", "板块", "对比"]):
            return "industry_comparison", codes
        if any(k in q for k in ["宏观", "经济", "gdp", "cpi", "利率"]):
            return "macro_analysis", codes
        if any(k in q for k in ["全面", "综合", "研究"]):
            return "comprehensive_research", codes
        if any(k in q for k in ["价格", "多少钱", "行情", "走势", "现在"]):
            return "price_query", codes
        if any(k in q for k in ["你好", "hi", "hello", "在吗"]):
            return "chat", codes
        # 默认: 有代码就综合研究,否则聊天
        return ("comprehensive_research" if codes else "chat"), codes
