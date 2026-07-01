"""启动脚本 - 从 backend 目录或项目根目录均可启动."""

import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径，确保 backend 包可被导入
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 导入并启动 FastAPI
from backend.config import settings

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
        log_level="info",
    )
