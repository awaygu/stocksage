"""Dispatcher 节点 - 读取 Planner 产出的 DAG,标记哪些 agent 该激活。

静态图所有 agent 节点都已建好;dispatcher 不决定拓扑,只决定"激活哪些"。
各 agent 节点入口读 active_agents 判断是执行还是跳过(skipped)。
"""

from backend.core.event_bus import event_bus
from backend.graph.state import StockSageState


class DispatcherNode:
    """调度分发节点。

    从 plan.tasks 中提取去重的 agent 列表写入 active_agents,
    并初始化 task_status。不做任何执行决策,只做标记。
    """

    async def __call__(self, state: StockSageState) -> dict:
        session_id = state.get("session_id", "")
        plan = state.get("plan", {})

        # 激活的 agent 去重保序
        active: list[str] = []
        seen: set[str] = set()
        for task in plan.get("tasks", []):
            agent = task["agent"]
            if agent not in seen:
                seen.add(agent)
                active.append(agent)

        await event_bus.publish_agent_status(
            session_id,
            "dispatcher",
            "completed",
            {"active_agents": active, "task_count": len(plan.get("tasks", []))},
        )

        return {
            "active_agents": active,
            "status": "dispatching",
        }
