"""LangGraph 节点 - 将 Agent 包装为 LangGraph 可执行的节点函数."""

from backend.agents.router import IntentRouterAgent
from backend.graph.state import StockSageState


class RouterNode:
    """意图路由节点。"""

    def __init__(self):
        self.agent = IntentRouterAgent()

    async def __call__(self, state: StockSageState) -> dict:
        """执行意图路由。"""
        result = await self.agent.run(state)
        return {
            "intent": result.get("intent", {}),
            "active_agents": result.get("active_agents", []),
            "status": result.get("status", "routing"),
        }
