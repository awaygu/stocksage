"""聊天 API - REST 接口。

- POST /api/chat       同步整篇返回报告(等待所有 Agent 完成)
- POST /api/chat/stream SSE 流式:桥接 event_bus,实时推 agent_status 与报告 token

实时状态统一走 SSE;WebSocket(/ws/stream)留作备用。
"""

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.core.event_bus import event_bus

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


def _initial_state(session_id: str, query: str) -> dict:
    """构造 LangGraph 初始状态(供同步与流式端点共用)。"""
    return {
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


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request):
    """同步聊天接口。

    发送用户query，等待所有Agent完成后返回报告。
    如需实时状态与流式报告，请使用 POST /chat/stream。
    """
    session_id = request.session_id or str(uuid.uuid4())
    query = request.query

    # 获取 LangGraph
    graph = req.app.state.graph

    try:
        # 执行工作流
        result = await graph.ainvoke(_initial_state(session_id, query))

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


def _sse(payload: dict) -> str:
    """格式化一条 SSE 事件(data 帧)。"""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, req: Request):
    """流式聊天接口(SSE)。

    桥接 event_bus:订阅 session:{id} 事件,把 agent_status / stream_chunk /
    error 透传到这条 SSE 连接;后台并行执行 LangGraph,started/completed 由
    端点自己发。一条连接即承载全部实时事件。
    """
    session_id = request.session_id or str(uuid.uuid4())
    query = request.query
    graph = req.app.state.graph

    async def event_stream() -> AsyncGenerator[str, None]:
        queue: asyncio.Queue[dict | None] = asyncio.Queue()

        async def on_event(data: dict) -> None:
            await queue.put(data)

        await event_bus.subscribe(f"session:{session_id}", on_event)

        # 后台跑图:事件经 event_bus 流入 queue,异常也以 error 帧入队
        async def run() -> None:
            try:
                await graph.ainvoke(_initial_state(session_id, query))
            except Exception as e:  # noqa: BLE001
                await queue.put(
                    {"type": "error", "error": str(e), "session_id": session_id}
                )
            finally:
                await queue.put(None)  # 哨兵:执行结束

        task = asyncio.create_task(run())

        yield _sse({"type": "status", "status": "started", "session_id": session_id})

        try:
            while True:
                data = await queue.get()
                if data is None:
                    break
                yield _sse(data)  # agent_status / stream_chunk / error
        finally:
            await event_bus.unsubscribe(f"session:{session_id}", on_event)
            await task  # 回收后台任务,传播可能的异常

        yield _sse(
            {"type": "status", "status": "completed", "session_id": session_id}
        )
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 防 Nginx 缓冲
            "Connection": "keep-alive",
        },
    )
