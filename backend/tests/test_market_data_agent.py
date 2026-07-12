"""MarketData Agent 测试 - 真实 tushare 数据采集与摘要生成。"""

import asyncio

import pytest

from backend.agents.market_data import MarketDataAgent
from backend.config import settings
from backend.data.cache import data_cache
from backend.graph.state import StockSageState

pytestmark = pytest.mark.skipif(
    not settings.tushare_token or settings.tushare_token == "your-tushare-token-here",
    reason="未配置 TUSHARE_TOKEN",
)


def _make_state(code: str) -> StockSageState:
    return {
        "messages": [{"role": "user", "content": code}],
        "current_query": code,
        "session_id": "test-md",
        "intent": {},
        "plan": {"stock_codes": [code], "timeframe": "近一个月"},
        "active_agents": ["market_data"],
        "task_status": {},
        "agent_results": {},
    }


def test_market_data_collects_kline_and_quote():
    """agent 应真实获取 K线、报价、基础信息并生成摘要。"""
    data_cache.clear()  # 确保走真实取数
    agent = MarketDataAgent()
    result = asyncio.run(agent.run(_make_state("600519")))

    md = result["market_data"]
    assert md["status"] == "completed"
    data = md["data"]["600519"]

    # K 线数据
    kline = data["kline"]
    assert len(kline) > 0
    assert "close" in kline[-1]
    # 实时报价
    quote = data["quote"]
    assert quote["name"] == "贵州茅台"
    assert 100 < quote["price"] < 5000
    # 基础信息
    assert data["basic"]["name"] == "贵州茅台"


def test_market_data_summary_contains_price():
    """摘要应含股票名称、价格与涨跌幅。"""
    data_cache.clear()
    agent = MarketDataAgent()
    result = asyncio.run(agent.run(_make_state("600519")))

    summary = result["market_data"]["summary"]
    assert "贵州茅台" in summary
    assert "600519" in summary
    # 摘要应含价格数字与涨跌幅百分比
    assert "%" in summary


def test_market_data_caches_second_call():
    """第二次调用应命中缓存(不再发网络请求)。"""
    data_cache.clear()
    agent = MarketDataAgent()

    # 第一次: 真实取数
    asyncio.run(agent.run(_make_state("600519")))
    first = data_cache.get_kline("600519", "CN", "daily")
    assert first is not None

    # 第二次: 缓存命中
    asyncio.run(agent.run(_make_state("600519")))
    second = data_cache.get_kline("600519", "CN", "daily")
    assert first is second  # 同一对象引用,说明命中缓存


def test_market_data_handles_invalid_code():
    """错误代码应捕获异常,不影响整体状态。"""
    agent = MarketDataAgent()
    state = _make_state("999999")
    state["plan"] = {"stock_codes": ["999999"], "timeframe": "近一个月"}
    result = asyncio.run(agent.run(state))

    md = result["market_data"]
    # 即使该代码无数据,agent 也应完成(不抛异常)
    assert md["status"] == "completed"
