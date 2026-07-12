"""Agent 节点公共工具 - 跳过逻辑、状态更新辅助。

所有 agent 节点共享的"判断是否激活"与"产出 skipped 结果"逻辑。
"""

from backend.core.event_bus import event_bus
from backend.graph.state import StockSageState


async def is_agent_active(state: StockSageState, agent_id: str) -> bool:
    """判断该 agent 是否在当前计划中被激活。"""
    return agent_id in state.get("active_agents", [])


async def skip_agent(state: StockSageState, agent_id: str, reason: str = "") -> dict:
    """产出 skipped 结果并发布事件,不执行任何真实逻辑。

    Args:
        state: 当前状态
        agent_id: 被跳过的 agent 标识
        reason: 跳过原因摘要

    Returns:
        符合 agent_results reducer 的字典
    """
    session_id = state.get("session_id", "")
    await event_bus.publish_agent_status(session_id, agent_id, "skipped")
    return {
        "agent_results": {
            agent_id: {
                "agent_id": agent_id,
                "status": "skipped",
                "data": {},
                "summary": reason or f"{agent_id} 未激活,跳过",
            }
        }
    }
