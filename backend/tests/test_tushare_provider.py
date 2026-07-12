"""Tushare provider 测试 - 真实调用 tushare API 验证数据获取。

需要配置 TUSHARE_TOKEN (backend/.env)。使用茅台 600519 作为样本。
"""

import asyncio

import pytest

from backend.config import settings
from backend.data.providers.tushare_provider import TushareProvider, to_ts_code


# 跳过条件: 未配置 tushare token
pytestmark = pytest.mark.skipif(
    not settings.tushare_token or settings.tushare_token == "your-tushare-token-here",
    reason="未配置 TUSHARE_TOKEN,跳过真实数据测试",
)

SAMPLE_CODE = "600519"  # 贵州茅台


def test_to_ts_code_a_shares():
    """A 股代码应正确映射到交易所后缀。"""
    assert to_ts_code("600519") == "600519.SH"  # 沪市
    assert to_ts_code("000001") == "000001.SZ"  # 深市
    assert to_ts_code("300750") == "300750.SZ"  # 创业板
    assert to_ts_code("600519.SH") == "600519.SH"  # 已带后缀不变


def test_to_ts_code_non_a_share():
    """非 A 股代码(字母/已带后缀)原样返回。"""
    assert to_ts_code("AAPL") == "AAPL"
    assert to_ts_code("00700") == "00700"  # 5位港股不匹配规则


def test_get_kline_returns_ascending_daily():
    """日线 K 线应按日期升序返回,含 OHLCV 字段。"""
    provider = TushareProvider()
    kline = asyncio.run(provider.get_kline(SAMPLE_CODE, period="daily", limit=5))

    assert len(kline) == 5, "应返回 5 条日线"
    # 升序检查
    dates = [k["date"] for k in kline]
    assert dates == sorted(dates), "日期应升序"
    # 字段完整性
    first = kline[0]
    for field in ("date", "open", "high", "low", "close", "volume"):
        assert field in first, f"缺少字段 {field}"
        assert isinstance(first[field], (str, float, int))
    # 价格合理性(茅台股价应在数百到数千元)
    assert 100 < first["close"] < 5000, f"茅台收盘价异常: {first['close']}"


def test_get_realtime_quote():
    """实时报价应返回名称、价格等字段。"""
    provider = TushareProvider()
    quote = asyncio.run(provider.get_realtime_quote(SAMPLE_CODE))

    assert quote["name"] == "贵州茅台"
    assert quote["ts_code"] == "600519.SH"
    for field in ("price", "open", "high", "low", "pre_close"):
        assert field in quote
    assert 100 < quote["price"] < 5000, f"实时价格异常: {quote['price']}"


def test_get_basic_info():
    """基础信息应返回名称和行业。"""
    provider = TushareProvider()
    info = asyncio.run(provider.get_basic_info(SAMPLE_CODE))

    assert info["ts_code"] == "600519.SH"
    assert info["name"] == "贵州茅台"
    assert info["industry"]  # 行业非空


def test_get_kline_basic_has_pe_pb():
    """日线指标应包含 PE/PB。"""
    provider = TushareProvider()
    basic = asyncio.run(provider.get_kline_basic(SAMPLE_CODE, limit=3))

    assert len(basic) == 3
    first = basic[-1]  # 最新一条
    assert "pe" in first
    assert "pb" in first
    # 茅台 PE 应在个位到几十倍
    assert first["pe"] is not None and 5 < first["pe"] < 100
