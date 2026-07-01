"""Event Bus - 用于在 Agent 之间传递状态变化事件，并推送到前端 WebSocket."""

import asyncio
from collections.abc import Callable
from typing import Any


class EventBus:
    """内存事件总线，支持订阅/发布模式。"""

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, event_type: str, callback: Callable) -> None:
        """订阅特定类型的事件."""
        async with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)

    async def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """取消订阅."""
        async with self._lock:
            if event_type in self._subscribers and callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)

    async def publish(self, event_type: str, data: Any) -> None:
        """发布事件到所有订阅者."""
        callbacks = []
        async with self._lock:
            callbacks = list(self._subscribers.get(event_type, []))

        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception:
                # 单个订阅者失败不应影响其他订阅者
                pass

    async def publish_agent_status(self, session_id: str, agent_id: str, status: str, data: dict | None = None) -> None:
        """发布 Agent 状态变化事件。"""
        payload = {
            "type": "agent_status",
            "session_id": session_id,
            "agent_id": agent_id,
            "status": status,
            "data": data or {},
        }
        await self.publish(f"session:{session_id}", payload)
        await self.publish("all_sessions", payload)

    async def publish_stream_chunk(self, session_id: str, content: str) -> None:
        """发布流式输出块。"""
        await self.publish(
            f"session:{session_id}",
            {"type": "stream_chunk", "session_id": session_id, "content": content},
        )


# 全局事件总线单例
event_bus = EventBus()
