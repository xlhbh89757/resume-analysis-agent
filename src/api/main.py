"""FastAPI 应用入口"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.core.database import init_db
from src.core.redis import close_redis
from src.api.routes import resume_router, match_router, health_router
from src.api.routes.jobs import router as jobs_router

# 配置日志
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info(f"Starting {settings.app_name}...")
    
    # 初始化数据库
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    
    yield
    
    # 关闭时
    logger.info("Shutting down...")
    await close_redis()


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.app_name,
    description="""
## 简历分析 Agent API

智能简历分析系统，支持：
- 📄 PDF/DOCX 简历上传与解析
- 🤖 LLM 智能信息提取
- 🎯 JD 职位匹配评分
- 🔍 语义搜索候选人
- ⚡ 批量处理能力

### 快速开始

1. 上传简历: `POST /api/v1/resumes/upload`
2. 创建职位: `POST /api/v1/jobs/`
3. 匹配分析: `POST /api/v1/match/analyze`
4. 搜索候选人: `POST /api/v1/resumes/search`
""",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health_router)
app.include_router(resume_router, prefix=settings.api_prefix)
app.include_router(match_router, prefix=settings.api_prefix)
app.include_router(jobs_router, prefix=settings.api_prefix)

# 静态文件服务
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

# 确保 static 目录存在
import os
static_dir = os.path.join(os.path.dirname(__file__), "../static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def root():
    """根路径重定向到 UI"""
    if os.path.exists(os.path.join(static_dir, "index.html")):
        return FileResponse(os.path.join(static_dir, "index.html"))
    return RedirectResponse(url="/docs")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
