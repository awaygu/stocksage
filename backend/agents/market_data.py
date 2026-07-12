"""市场数据 Agent - 获取股票的行情、K线等市场数据(基于 tushare)。"""

from backend.agents.base import BaseAgent
from backend.core.event_bus import event_bus
from backend.data.cache import data_cache
from backend.data.providers.tushare_provider import tushare_provider
from backend.graph.state import StockSageState


class MarketDataAgent(BaseAgent):
    """市场数据 Agent。

    负责获取股票的:
    - K线数据(日线)
    - 实时报价
    - 基础信息(名称/行业)
    """

    SYSTEM_PROMPT = """你是一位市场数据专家。
你的职责是获取并整理股票的市场行情数据,为后续分析提供基础数据。
你不需要做分析判断,只需准确获取和描述数据。"""

    def __init__(self) -> None:
        super().__init__("market_data", self.SYSTEM_PROMPT)

    def _default_system_prompt(self) -> str:
        return self.SYSTEM_PROMPT

    async def run(self, state: StockSageState) -> dict:
        """执行市场数据采集。"""
        session_id = state.get("session_id", "")
        intent = state.get("intent", {})
        plan = state.get("plan", {})
        stock_codes = plan.get("stock_codes") or intent.get("stock_codes", [])
        timeframe = plan.get("timeframe") or intent.get("timeframe", "近一个月")

        await event_bus.publish_agent_status(session_id, "market_data", "running")

        results = {}
        summaries = []
        limit = self._timeframe_to_limit(timeframe)

        for code in stock_codes:
            try:
                kline = data_cache.get_kline(code, "CN", "daily")
                if kline is None:
                    kline = await tushare_provider.get_kline(code, period="daily", limit=limit)
                    data_cache.set_kline(code, "CN", "daily", kline)

                quote = data_cache.get_quote(code, "CN")
                if quote is None:
                    quote = await tushare_provider.get_realtime_quote(code)
                    data_cache.set_quote(code, "CN", quote)

                basic = data_cache.get_basic(code, "CN")
                if basic is None:
                    basic = await tushare_provider.get_basic_info(code)
                    data_cache.set_basic(code, "CN", basic)

                results[code] = {
                    "kline": kline,
                    "quote": quote,
                    "basic": basic,
                    "market": "CN",
                }
                summaries.append(self._generate_summary(code, kline, quote, basic))
            except Exception as e:
                results[code] = {"error": str(e)}
                summaries.append(f"{code}: 数据获取失败 - {e}")

        summary_text = "\n".join(summaries) if summaries else "未获取到市场数据"
        await event_bus.publish_agent_status(
            session_id,
            "market_data",
            "completed",
            {"stock_codes": stock_codes},
        )

        return self.create_result(status="completed", data=results, summary=summary_text)

    def _timeframe_to_limit(self, timeframe: str) -> int:
        """时间范围 -> 日线条数。"""
        tf = timeframe.lower()
        if "年" in tf or "year" in tf:
            return 250
        if "季" in tf or "quarter" in tf or "3个月" in tf:
            return 65
        if "周" in tf or "week" in tf:
            return 5
        return 30  # 默认近一个月

    def _generate_summary(self, code: str, kline: list[dict], quote: dict, basic: dict) -> str:
        """生成数据摘要。"""
        name = basic.get("name", "") or quote.get("name", "")
        if not kline:
            return f"{code} ({name}): 无K线数据"

        latest = kline[-1]
        first = kline[0]
        start_price = first.get("close", 0)
        end_price = latest.get("close", 0)
        change_pct = round((end_price - start_price) / start_price * 100, 2) if start_price else 0

        high = max((d.get("high", 0) for d in kline), default=0)
        low = min((d.get("low", 0) for d in kline), default=0)
        total_volume = sum((d.get("volume", 0) for d in kline), 0)

        rt_price = quote.get("price") if quote else None
        price_line = f"实时价: {rt_price}" if rt_price else f"最新收盘: {end_price}"

        return (
            f"股票: {code} ({name})\n"
            f"  {price_line} (区间涨跌幅: {change_pct}%)\n"
            f"  区间: {first.get('date', '')} ~ {latest.get('date', '')}\n"
            f"  最高价: {high}, 最低价: {low}\n"
            f"  总成交量: {total_volume:,.0f} 手"
        )
