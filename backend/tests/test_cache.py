"""数据缓存测试 - 纯单元测试,不依赖网络。"""

import time

from backend.data.cache import DataCache


def test_cache_set_get_kline():
    """kline 缓存应能存取。"""
    cache = DataCache()
    cache.clear()
    assert cache.get_kline("600519", "CN", "daily") is None

    data = [{"date": "2026-07-10", "close": 1204.98}]
    cache.set_kline("600519", "CN", "daily", data)
    assert cache.get_kline("600519", "CN", "daily") == data


def test_cache_set_get_quote():
    """quote 缓存应能存取。"""
    cache = DataCache()
    cache.clear()
    assert cache.get_quote("600519", "CN") is None

    quote = {"name": "贵州茅台", "price": 1204.98}
    cache.set_quote("600519", "CN", quote)
    assert cache.get_quote("600519", "CN") == quote


def test_cache_ttl_expiry():
    """缓存应在 TTL 后过期。"""
    cache = DataCache()
    cache.clear()
    cache.set_kline("600519", "CN", "daily", [{"close": 1}], ttl=1)
    assert cache.get_kline("600519", "CN", "daily") is not None

    time.sleep(1.1)
    assert cache.get_kline("600519", "CN", "daily") is None


def test_cache_different_keys_isolated():
    """不同 symbol/market 的缓存应隔离。"""
    cache = DataCache()
    cache.clear()
    cache.set_quote("600519", "CN", {"price": 1204})
    cache.set_quote("AAPL", "US", {"price": 200})

    assert cache.get_quote("600519", "CN")["price"] == 1204
    assert cache.get_quote("AAPL", "US")["price"] == 200
