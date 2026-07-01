# StockSage 📈

多 Agent 股票研究系统

## 目录结构

```
stocksage/
├── backend/          # FastAPI + LangGraph 后端
│   ├── run.py        # 后端启动入口
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── .env.example
├── frontend/         # React + Tailwind 前端
│   └── package.json
└── mcp_servers/      # MCP 服务（预留）
```

## 启动方式

### 后端

```bash
cd backend
pip install -r requirements.txt
# 复制 .env.example 为 .env 并填入 OPENAI_API_KEY
python run.py
```

或者直接从项目根目录启动：

```bash
uvicorn backend.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

## 架构

用户 → Orchestrator(LangGraph) → Data Agent → Analysis Agent → Report Agent
