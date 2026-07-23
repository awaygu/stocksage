"""Tushare 数据源 Provider - A 股行情/报价/基础信息/日线指标.

为 P0 阻断项实现(SPEC §4.5.2)。满足 test_tushare_provider.py 契约:
- to_ts_code: 600xxx→.SH, 000xxx/300xxx→.SZ, 其余原样返回
- get_kline: 日线 OHLCV,按日期升序,字段 date/open/high/low/close/volume
- get_realtime_quote: 字段 name/ts_code/price/open/high/low/pre_close
- get_basic_info: 字段 ts_code/name/industry
- get_kline_basic: 日线指标含 pe/pb

接口适配说明:
- realtime_quote 接口需较高积分;2159 积分无法调用。
  get_realtime_quote 退化为取 daily 最新交易日行情,close 作为 price。
  对"实时价"语义略打折扣,但保证字段契约与价格合理性。
  (后续积分提升或换源后,可在此处替换为真正的实时接口。)
- 成交量字段: tushare daily 的 vol 单位为"手",直接透传。
"""

from typing import Any

import asyncio

import tushare as ts

from backend.config import settings


def to_ts_code(code: str) -> str:
    """A 股代码映射到 tushare ts_code。

    - 600xxx / 688xxx → .SH(沪市 / 科创板)
    - 000xxx / 001xxx / 002xxx / 300xxx / 301xxx → .SZ(深市 / 创业板)
    - 已带后缀(如 600519.SH)原样返回
    - 港股(5 位数字)/ 美股(字母)原样返回(非 A 股,不做映射)
    """
    if not code or "." in code:
        return code

    # 仅处理 6 位纯数字 A 股代码
    if len(code) == 6 and code.isdigit():
        if code[0] in ("6", "9"):  # 600/601/603/605/688/900
            return f"{code}.SH"
        return f"{code}.SZ"  # 000/001/002/003/300/301

    # 港股(5 位)/ 美股(字母)等非 A 股,原样返回
    return code


class TushareProvider:
    """Tushare Pro 数据源。

    通过 settings.tushare_token 初始化 pro_api。每次调用按需取数,
    缓存由上层 MarketDataAgent / DataCache 负责。
    """

    def __init__(self, token: str | None = None) -> None:
        token = token or settings.tushare_token
        if not token or token == "your-tushare-token-here":
            raise ValueError("未配置 TUSHARE_TOKEN,无法初始化 Tushare 数据源")
        self._api = ts.pro_api(token)

    async def get_kline(self, code: str, period: str = "daily", limit: int = 30) -> list[dict]:
        """获取日线 K 线(OHLCV),按日期升序。

        tushare daily 返回按交易日降序,这里翻转成升序以符合契约。
        period 目前仅支持 daily(tushare weekly/monthly 走另一接口,后续按需扩展)。
        tushare 调用是同步阻塞的(requests),放线程池避免阻塞事件循环。
        """
        return await asyncio.to_thread(self._get_kline_sync, code, period, limit)

    def _get_kline_sync(self, code: str, period: str, limit: int) -> list[dict]:
        ts_code = to_ts_code(code)
        df = self._api.daily(ts_code=ts_code, limit=limit)
        if df is None or len(df) == 0:
            return []

        # 降序 → 升序
        df = df.sort_values("trade_date", ascending=True).reset_index(drop=True)

        kline: list[dict] = []
        for _, row in df.iterrows():
            kline.append(
                {
                    "date": str(row["trade_date"]),  # YYYYMMDD
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["vol"]),  # 单位: 手
                }
            )
        return kline

    async def get_realtime_quote(self, code: str) -> dict:
        """获取"实时"报价(退化为最新交易日行情)。

        返回字段: name, ts_code, price, open, high, low, pre_close。
        price 取最新交易日 close。
        """
        return await asyncio.to_thread(self._get_realtime_quote_sync, code)

    def _get_realtime_quote_sync(self, code: str) -> dict:
        ts_code = to_ts_code(code)

        # 取最新一条日线作为报价(不传 limit 时 tushare 默认返回最近若干条,取首条=最新)
        df = self._api.daily(ts_code=ts_code, limit=1)
        if df is None or len(df) == 0:
            return {}

        row = df.iloc[0]
        name = self._fetch_name(ts_code)

        return {
            "name": name,
            "ts_code": ts_code,
            "price": float(row["close"]),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "pre_close": float(row["pre_close"]),
        }

    async def get_basic_info(self, code: str) -> dict:
        """获取基础信息(名称、行业、上市日期等)。"""
        return await asyncio.to_thread(self._get_basic_info_sync, code)

    def _get_basic_info_sync(self, code: str) -> dict:
        ts_code = to_ts_code(code)
        df = self._api.stock_basic(ts_code=ts_code)
        if df is None or len(df) == 0:
            return {"ts_code": ts_code, "name": "", "industry": ""}

        row = df.iloc[0]
        return {
            "ts_code": ts_code,
            "name": str(row["name"]),
            "industry": str(row.get("industry", "")),
            "area": str(row.get("area", "")),
            "list_date": str(row.get("list_date", "")),
        }

    async def get_kline_basic(self, code: str, limit: int = 30) -> list[dict]:
        """获取日线指标(含 PE/PB/换手率/总市值等),按日期升序。"""
        return await asyncio.to_thread(self._get_kline_basic_sync, code, limit)

    def _get_kline_basic_sync(self, code: str, limit: int) -> list[dict]:
        ts_code = to_ts_code(code)
        df = self._api.daily_basic(ts_code=ts_code, limit=limit)
        if df is None or len(df) == 0:
            return []

        df = df.sort_values("trade_date", ascending=True).reset_index(drop=True)

        result: list[dict] = []
        for _, row in df.iterrows():
            result.append(
                {
                    "date": str(row["trade_date"]),
                    "close": self._safe_float(row.get("close")),
                    "pe": self._safe_float(row.get("pe")),
                    "pe_ttm": self._safe_float(row.get("pe_ttm")),
                    "pb": self._safe_float(row.get("pb")),
                    "ps": self._safe_float(row.get("ps")),
                    "turnover_rate": self._safe_float(row.get("turnover_rate")),
                    "total_mv": self._safe_float(row.get("total_mv")),
                    "circ_mv": self._safe_float(row.get("circ_mv")),
                }
            )
        return result

    def _fetch_name(self, ts_code: str) -> str:
        """获取股票名称(get_realtime_quote 复用)。"""
        df = self._api.stock_basic(ts_code=ts_code)
        if df is None or len(df) == 0:
            return ""
        return str(df.iloc[0]["name"])

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        """NaN/None 安全转 float。"""
        if value is None:
            return None
        try:
            f = float(value)
        except (TypeError, ValueError):
            return None
        # pandas NaN
        if f != f:  # noqa: PLR0124
            return None
        return f


# 模块级单例,供 MarketDataAgent 使用。
# 懒初始化: import 时若未配置 token 也不报错,真实调用方法时才校验
# (便于无 token 环境下 import 链路通过)。
_provider_instance: TushareProvider | None = None


def _get_provider() -> TushareProvider:
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = TushareProvider()
    return _provider_instance


class _LazyProvider:
    """懒加载代理: 首次调用任意方法时才真正初始化 TushareProvider。

    避免 import 时因缺 token 报错,阻断 import 链路。
    """

    def __getattr__(self, name: str) -> Any:
        # 转发到真实实例
        return getattr(_get_provider(), name)


tushare_provider = _LazyProvider()
