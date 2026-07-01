"""聊天 API - REST 接口。"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel

from backend.core.event_bus import event_bus
from backend.graph.graph_builder import StockSageGraphBuilder

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    """聊天请求。"""

    query: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    """聊天响应。"""

    session_id: str
    status: str
    report: str | None = None
    error: str | None = None


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request):
    """同步聊天接口。

    发送用户query，等待所有Agent完成后返回报告。
    如需实时状态，请使用 WebSocket。
    """
    session_id = request.session_id or str(uuid.uuid4())
    query = request.query

    # 获取 LangGraph
    graph = req.app.state.graph

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

    try:
        # 执行工作流
        result = await graph.ainvoke(initial_state)

        return ChatResponse(
            session_id=session_id,
            status=result.get("status", "completed"),
            report=result.get("report"),
        )

    except Exception as e:
        return ChatResponse(
            session_id=session_id,
            status="error",
            error=str(e),
        )


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, req: Request):
    """流式聊天接口（SSE）。"""
    from fastapi.responses import StreamingResponse

    session_id = request.session_id or str(uuid.uuid4())
    query = request.query

    graph = req.app.state.graph

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

    async def generate():
        async for event in graph.astream_events(initial_state, version="v2"):
            event_type = event.get("event")
            if event_type == "on_chain_end":
                data = event.get("data", {})
                if "output" in data:
                    output = data["output"]
                    if output.get("report"):
                        yield f"data: {output['report']}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )
