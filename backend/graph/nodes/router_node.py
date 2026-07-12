"""LangGraph 节点 - 将 Agent 包装为 LangGraph 可执行的节点函数.

本文件改为 Planner 节点(Plan-and-execute 的计划阶段入口)。
"""

from backend.agents.router import PlannerAgent
from backend.graph.state import StockSageState


class PlannerNode:
    """计划生成节点 - 调用 PlannerAgent 产出执行 DAG。"""

    def __init__(self) -> None:
        self.agent = PlannerAgent()

    async def __call__(self, state: StockSageState) -> dict:
        """执行计划生成。"""
        result = await self.agent.run(state)
        return {
            "intent": result.get("intent", {}),
            "plan": result.get("plan", {}),
            "active_agents": result.get("active_agents", []),
            "task_status": result.get("task_status", {}),
            "status": result.get("status", "planning"),
        }
