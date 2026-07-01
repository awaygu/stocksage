"""WebSocket 路由 - 实时推送 Agent 状态。"""

import uuid
from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.core.event_bus import event_bus
from backend.graph.graph_builder import StockSageGraphBuilder

router = APIRouter(tags=["websocket"])

# 活跃的 WebSocket 连接
active_connections: Dict[str, WebSocket] = {}


@router.websocket("/stream/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket 连接 - 实时推送 Agent 状态。"""
    await websocket.accept()
    active_connections[session_id] = websocket

    # 订阅该 session 的事件
    async def event_handler(data):
        try:
            await websocket.send_json(data)
        except Exception:
            pass

    await event_bus.subscribe(f"session:{session_id}", event_handler)

    try:
        while True:
            # 接收前端消息
            message = await websocket.receive_json()

            msg_type = message.get("type")
            if msg_type == "query":
                # 用户发送 query
                query = message.get("content", "")
                await _handle_query(websocket, session_id, query)
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass
    finally:
        # 清理
        await event_bus.unsubscribe(f"session:{session_id}", event_handler)
        active_connections.pop(session_id, None)


async def _handle_query(websocket: WebSocket, session_id: str, query: str):
    """处理用户 query，执行 LangGraph 工作流。"""
    # 获取 LangGraph
    from backend.main import app
    graph = app.state.graph

    # 构建初始状态
    initial_state = {
        "messages": [{"role": "user", "content": query}],
        "current_query": query,
        "session_id": session_id,
        "intent": {},
        "active_agents": [],
        "agent_results": {},
        "synthesis": {},
        "report": "",
        "status": "idle",
        "error_message": "",
    }

    # 发送开始信号
    await websocket.send_json({
        "type": "status",
        "status": "started",
        "session_id": session_id,
    })

    try:
        # 执行工作流
        result = await graph.ainvoke(initial_state)

        # 发送最终报告
        report = result.get("report", "")
        await websocket.send_json({
            "type": "report",
            "content": report,
            "session_id": session_id,
        })

        # 发送完成信号
        await websocket.send_json({
            "type": "status",
            "status": "completed",
            "session_id": session_id,
        })

    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "error": str(e),
            "session_id": session_id,
        })
