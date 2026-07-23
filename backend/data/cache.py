"""数据缓存 - 行情/报价/基础信息的内存缓存,支持 TTL 与按 key 隔离.

为 P0 阻断项实现(SPEC §4.5.1)。满足 test_cache.py 契约:
- get_* 未命中或过期返回 None
- set_* 写入,命中返回同一对象引用(test 里 `first is second`)
- 不同 symbol/market/period 互不干扰
- TTL 过期自动失效

后续 P1-9 可将后端切换为 Redis(定义 CacheBackend 抽象时再重构,保持接口不变)。
"""

import time
from typing import Any


class _Entry:
    """单个缓存条目,带过期时间戳。"""

    __slots__ = ("value", "expire_at")

    def __init__(self, value: Any, expire_at: float | None) -> None:
        self.value = value
        # expire_at 为 None 表示永不过期
        self.expire_at = expire_at


class DataCache:
    """数据缓存。

    三个独立存储空间(kline / quote / basic),各自按 key 隔离。
    所有 get_* 在过期时惰性删除并返回 None。
    """

    # 默认 TTL(秒): K线 1 小时,报价 1 分钟,基础信息 1 天
    DEFAULT_TTL_KLINE: int = 3600
    DEFAULT_TTL_QUOTE: int = 60
    DEFAULT_TTL_BASIC: int = 86400

    def __init__(self) -> None:
        self._kline: dict[tuple[str, str, str], _Entry] = {}
        self._quote: dict[tuple[str, str], _Entry] = {}
        self._basic: dict[tuple[str, str], _Entry] = {}

    @staticmethod
    def _get(store: dict, key: tuple) -> Any:
        """读取并做过期检查,过期则惰性删除返回 None。"""
        entry = store.get(key)
        if entry is None:
            return None
        if entry.expire_at is not None and time.time() > entry.expire_at:
            del store[key]
            return None
        # 直接返回存储的对象引用(满足 `first is second` 契约)
        return entry.value

    @staticmethod
    def _set(store: dict, key: tuple, value: Any, ttl: int | None) -> None:
        # ttl <= 0 视为永不过期
        expire_at = (time.time() + ttl) if (ttl is not None and ttl > 0) else None
        store[key] = _Entry(value, expire_at)

    # ---- K线 ----
    def get_kline(self, code: str, market: str, period: str) -> list[dict] | None:
        return self._get(self._kline, (code, market, period))

    def set_kline(
        self,
        code: str,
        market: str,
        period: str,
        data: list[dict],
        ttl: int | None = DEFAULT_TTL_KLINE,
    ) -> None:
        self._set(self._kline, (code, market, period), data, ttl)

    # ---- 实时报价 ----
    def get_quote(self, code: str, market: str) -> dict | None:
        return self._get(self._quote, (code, market))

    def set_quote(self, code: str, market: str, data: dict, ttl: int | None = DEFAULT_TTL_QUOTE) -> None:
        self._set(self._quote, (code, market), data, ttl)

    # ---- 基础信息 ----
    def get_basic(self, code: str, market: str) -> dict | None:
        return self._get(self._basic, (code, market))

    def set_basic(self, code: str, market: str, data: dict, ttl: int | None = DEFAULT_TTL_BASIC) -> None:
        self._set(self._basic, (code, market), data, ttl)

    # ---- 清空 ----
    def clear(self) -> None:
        """清空所有缓存(测试用)。"""
        self._kline.clear()
        self._quote.clear()
        self._basic.clear()


# 模块级单例,供 MarketDataAgent 使用
data_cache = DataCache()
