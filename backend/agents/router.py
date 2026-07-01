"""意图路由 Agent - 解析用户 query，确定需要哪些专业 Agent 参与。"""

import json
import re

from backend.agents.base import BaseAgent
from backend.core.event_bus import event_bus
from backend.graph.state import StockSageState


class IntentRouterAgent(BaseAgent):
    """意图路由 Agent。

    分析用户的自然语言 query，识别：
    1. 用户的真实意图（价格查询/技术分析/基本面分析/综合研究等）
    2. 涉及的股票代码
    3. 涉及的市场（A股/美股/港股）
    4. 需要哪些专业 Agent 参与
    """

    SYSTEM_PROMPT = """你是一位股票研究系统的智能路由助手。你的任务是分析用户的 query，识别用户的真实意图，并确定需要哪些专业 Agent 参与。

**可识别的意图类型：**
- price_query: 价格/行情查询（"茅台现在多少钱？"）
- technical_analysis: 技术分析（"分析一下000001的技术面"）
- fundamental_analysis: 基本面分析（"茅台的估值如何？"）
- news_analysis: 新闻/事件分析（"最近有什么利好？"）
- comprehensive_research: 综合研究（"全面分析一下比亚迪"）
- risk_assessment: 风险评估（"这个股票有风险吗？"）
- industry_comparison: 行业对比（"对比一下新能源板块"）
- macro_analysis: 宏观分析（"当前宏观经济对股市的影响"）
- chat: 闲聊/打招呼（"你好"）

**市场代码映射：**
- A股代码: 6位数字，如 000001, 600519, 300750
- 美股代码: 字母，如 AAPL, TSLA, NVDA
- 港股代码: 5位数字，如 00700

**输出格式（严格 JSON）：**
{
    "intent_type": "comprehensive_research",
    "stock_codes": ["000001"],
    "markets": ["CN"],
    "timeframe": "近一个月",
    "required_agents": ["market_data", "technical", "fundamental", "synthesis", "report"],
    "confidence": 0.92,
    "user_query": "原始用户query"
}

**规则：**
1. stock_codes 只包含标准代码，不包含中文名称
2. required_agents 按执行顺序排列
3. 如果 query 不涉及具体股票（如宏观分析），stock_codes 为空数组
4. 置信度 confidence 范围 0-1
5. 如果无法识别，回退到 chat 意图
"""

    def __init__(self):
        super().__init__("router", self.SYSTEM_PROMPT)

    def _default_system_prompt(self) -> str:
        return self.SYSTEM_PROMPT

    def _extract_stock_codes(self, query: str) -> list[str]:
        """从 query 中提取股票代码（简单正则匹配）。"""
        codes = []

        # A股：6位数字
        a_shares = re.findall(r'\b\d{6}\b', query)
        codes.extend(a_shares)

        # 美股：1-5位字母大写
        us_shares = re.findall(r'\b[A-Z]{1,5}\b', query)
        codes.extend(us_shares)

        # 港股：5位数字
        hk_shares = re.findall(r'\b\d{5}\b', query)
        codes.extend(hk_shares)

        return list(set(codes))

    async def run(self, state: StockSageState) -> dict:
        """执行意图路由。"""
        query = state.get("current_query", "")
        session_id = state.get("session_id", "")

        # 发布路由开始事件
        await event_bus.publish_agent_status(session_id, "router", "running")

        # 1. 尝试用 LLM 做意图解析
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"用户query: {query}\n\n请分析并返回JSON格式结果。只返回JSON，不要其他文字。"}
        ]

        try:
            response = await self.call_llm(messages)
            intent = self._parse_llm_response(response, query)
        except Exception:
            # LLM 失败时回退到规则匹配
            intent = self._fallback_intent(query)

        # 发布路由完成事件
        await event_bus.publish_agent_status(
            session_id, "router", "completed",
            {"intent_type": intent.get("intent_type"), "required_agents": intent.get("required_agents", [])},
        )

        return {
            "intent": intent,
            "active_agents": intent.get("required_agents", []),
            "status": "routing",
        }

    def _parse_llm_response(self, response: str, query: str) -> dict:
        """解析 LLM 返回的 JSON 意图。"""
        # 尝试提取 JSON
        try:
            # 找到 JSON 部分
            start = response.find("{")
            end = response.rfind("}")
            if start >= 0 and end > start:
                json_str = response[start:end + 1]
                intent = json.loads(json_str)
                # 确保包含原始 query
                intent["user_query"] = query
                # 如果 LLM 没提取到代码，用正则补充
                if not intent.get("stock_codes"):
                    intent["stock_codes"] = self._extract_stock_codes(query)
                return intent
        except json.JSONDecodeError:
            pass

        # 解析失败，回退
        return self._fallback_intent(query)

    def _fallback_intent(self, query: str) -> dict:
        """回退到规则匹配。"""
        query_lower = query.lower()
        codes = self._extract_stock_codes(query)

        # 简单的关键词匹配
        if any(k in query_lower for k in ["技术", "macd", "kdj", "均线", "rsi"]):
            intent_type = "technical_analysis"
            required = ["market_data", "technical", "synthesis", "report"]
        elif any(k in query_lower for k in ["基本面", "估值", "pe", "pb", "财报", "利润", "营收"]):
            intent_type = "fundamental_analysis"
            required = ["fundamental", "synthesis", "report"]
        elif any(k in query_lower for k in ["新闻", "利好", "利空", "事件"]):
            intent_type = "news_analysis"
            required = ["market_data", "news_sentiment", "synthesis", "report"]
        elif any(k in query_lower for k in ["风险", "危险", "下跌"]):
            intent_type = "risk_assessment"
            required = ["market_data", "fundamental", "risk", "synthesis", "report"]
        elif any(k in query_lower for k in ["行业", "板块", "对比"]):
            intent_type = "industry_comparison"
            required = ["market_data", "industry", "synthesis", "report"]
        elif any(k in query_lower for k in ["宏观", "经济", "gdp", "cpi", "利率"]):
            intent_type = "macro_analysis"
            required = ["macro", "synthesis", "report"]
        elif any(k in query_lower for k in ["全面", "综合", "研究", "分析"]):
            intent_type = "comprehensive_research"
            required = ["market_data", "technical", "fundamental", "news_sentiment", "risk", "synthesis", "report"]
        elif any(k in query_lower for k in ["价格", "多少钱", "行情", "走势", "现在"]):
            intent_type = "price_query"
            required = ["market_data", "synthesis", "report"]
        elif any(k in query_lower for k in ["你好", "hi", "hello", "在吗"]):
            intent_type = "chat"
            required = ["synthesis"]
        else:
            # 默认：如果包含股票代码就综合研究，否则聊天
            if codes:
                intent_type = "comprehensive_research"
                required = ["market_data", "synthesis", "report"]
            else:
                intent_type = "chat"
                required = ["synthesis"]

        # 判断市场
        markets = []
        for code in codes:
            if code.isdigit() and len(code) == 6:
                markets.append("CN")
            elif code.isdigit() and len(code) == 5:
                markets.append("HK")
            elif code.isalpha():
                markets.append("US")
        markets = list(set(markets)) or ["CN"]

        return {
            "intent_type": intent_type,
            "stock_codes": codes,
            "markets": markets,
            "timeframe": "近一个月",
            "required_agents": required,
            "confidence": 0.7,
            "user_query": query,
        }
