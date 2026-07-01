"""FastAPI 入口 - 应用主入口。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.chat import router as chat_router
from backend.api.ws import router as websocket_router
from backend.graph.graph_builder import StockSageGraphBuilder


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    # 启动时初始化
    print("StockSage starting...")
    app.state.graph = StockSageGraphBuilder().get_graph()
    print("LangGraph workflow loaded")
    yield
    # 关闭时清理
    print("StockSage shutting down...")


app = FastAPI(
    title="StockSage API",
    description="多Agent股票研究系统",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat_router, prefix="/api")
app.include_router(websocket_router, prefix="/ws")


@app.get("/health")
async def health_check():
    """健康检查。"""
    return {"status": "ok", "version": "1.0.0", "service": "StockSage"}


@app.get("/")
async def root():
    """根路径。"""
    return {
        "name": "StockSage",
        "description": "多Agent股票研究系统",
        "version": "1.0.0",
        "docs": "/docs",
    }
