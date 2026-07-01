"""市场数据 Agent - 获取股票的行情、K线等市场数据。"""

from backend.agents.base import BaseAgent
from backend.core.event_bus import event_bus
from backend.data.cache import data_cache
from backend.data.providers.akshare_provider import akshare_provider
from backend.data.providers.yfinance_provider import yfinance_provider
from backend.graph.state import StockSageState


class MarketDataAgent(BaseAgent):
    """市场数据 Agent。

    负责获取股票的：
    - K线数据（日线/周线/月线）
    - 实时报价
    - 成交量/成交额
    """

    SYSTEM_PROMPT = """你是一位市场数据专家。
你的职责是获取并整理股票的市场行情数据，为后续分析提供基础数据。
你不需要做分析判断，只需准确获取和描述数据。"""

    def __init__(self):
        super().__init__("market_data", self.SYSTEM_PROMPT)

    def _default_system_prompt(self) -> str:
        return self.SYSTEM_PROMPT

    async def run(self, state: StockSageState) -> dict:
        """执行市场数据采集。"""
        session_id = state.get("session_id", "")
        intent = state.get("intent", {})
        stock_codes = intent.get("stock_codes", [])
        markets = intent.get("markets", ["CN"])
        timeframe = intent.get("timeframe", "近一个月")

        # 发布开始事件
        await event_bus.publish_agent_status(session_id, "market_data", "running")

        results = {}
        summaries = []

        for code in stock_codes:
            market = self._detect_market(code, markets)
            try:
                # 获取K线数据
                kline_data = await self._get_kline_cached(code, market, timeframe)
                # 获取实时报价
                quote_data = await self._get_quote_cached(code, market)

                results[code] = {
                    "kline": kline_data,
                    "quote": quote_data,
                    "market": market,
                }

                # 生成摘要
                summary = self._generate_summary(code, market, kline_data, quote_data)
                summaries.append(summary)

            except Exception as e:
                results[code] = {"error": str(e)}
                summaries.append(f"{code}: 数据获取失败 - {e}")

        # 发布完成事件
        summary_text = "\n".join(summaries) if summaries else "未获取到市场数据"
        await event_bus.publish_agent_status(
            session_id, "market_data", "completed",
            {"stock_codes": stock_codes, "markets": markets},
        )

        return self.create_result(
            status="completed",
            data=results,
            summary=summary_text,
        )

    def _detect_market(self, code: str, markets: list[str]) -> str:
        """根据代码判断市场。"""
        if code.isalpha():
            return "US"
        if len(code) == 5:
            return "HK"
        return "CN"

    async def _get_kline_cached(self, symbol: str, market: str, timeframe: str) -> list[dict]:
        """获取K线数据（带缓存）。"""
        # 尝试从缓存获取
        cached = data_cache.get_kline(symbol, market, "daily")
        if cached:
            return cached

        # 计算时间范围
        period = self._parse_timeframe(timeframe)

        if market == "CN":
            data = await akshare_provider.get_kline(symbol, period="daily")
        else:
            data = await yfinance_provider.get_kline(symbol, period=period)

        # 缓存结果
        data_cache.set_kline(symbol, market, "daily", None, None, data)
        return data

    async def _get_quote_cached(self, symbol: str, market: str) -> dict:
        """获取实时报价（带缓存）。"""
        cached = data_cache.get_quote(symbol, market)
        if cached:
            return cached

        if market == "CN":
            data = await akshare_provider.get_realtime_quote(symbol)
        else:
            data = await yfinance_provider.get_realtime_quote(symbol)

        data_cache.set_quote(symbol, market, data)
        return data

    def _parse_timeframe(self, timeframe: str) -> str:
        """解析时间范围为 yfinance period。"""
        tf = timeframe.lower()
        if "年" in tf or "year" in tf or "y" in tf:
            return "1y"
        if "季" in tf or "quarter" in tf or "3个月" in tf:
            return "3mo"
        if "月" in tf or "month" in tf or "m" in tf:
            return "1mo"
        if "周" in tf or "week" in tf or "w" in tf:
            return "1wk"
        return "1mo"  # 默认1个月

    def _generate_summary(self, code: str, market: str, kline: list[dict], quote: dict) -> str:
        """生成数据摘要。"""
        if not kline:
            return f"{code}: 无K线数据"

        # 最新数据
        latest = kline[-1] if kline else {}
        first = kline[0] if kline else {}

        # 计算涨跌幅
        if latest and first:
            start_price = first.get("close", 0)
            end_price = latest.get("close", 0)
            change_pct = round((end_price - start_price) / start_price * 100, 2) if start_price else 0
        else:
            change_pct = 0

        # 最高最低价
        high = max((d.get("high", 0) for d in kline), default=0)
        low = min((d.get("low", 0) for d in kline), default=0)

        # 成交量
        total_volume = sum((d.get("volume", 0) for d in kline), 0)

        return (
            f"股票: {code} ({market})\n"
            f"  最新价: {latest.get('close', 'N/A')} (涨跌幅: {change_pct}%)\n"
            f"  区间: {first.get('date', '')} ~ {latest.get('date', '')}\n"
            f"  最高价: {high}, 最低价: {low}\n"
            f"  总成交量: {total_volume:,}"
        )
