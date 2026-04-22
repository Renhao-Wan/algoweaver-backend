"""
FastAPI 应用入口

负责创建 FastAPI 实例、配置中间件、注册路由和 WebSocket 端点。
"""
import os
from contextlib import asynccontextmanager
from uuid import uuid4
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.core.config import get_settings
from app.core.logger import setup_logging, get_logger, request_id_var, user_id_var

# 初始化配置和日志
settings = get_settings()
setup_logging()
logger = get_logger(__name__)

# 配置 LangSmith 追踪
if settings.langsmith_tracing and settings.langsmith_api_key:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
    os.environ["LANGCHAIN_ENDPOINT"] = settings.langsmith_endpoint
    logger.info("LangSmith 追踪已启用")
else:
    logger.info("LangSmith 追踪未启用")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动事件
    logger.info(f"启动 {settings.app_name} v{settings.app_version}")
    logger.info(f"环境: {settings.environment}")
    logger.info(f"调试模式: {settings.debug}")

    yield

    # 关闭事件
    logger.info(f"关闭 {settings.app_name}")


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例"""

    app = FastAPI(
        title=settings.app_name,
        description="AlgoWeaver AI - 智能代码推演与优化系统",
        version=settings.app_version,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan
    )

    # 配置 CORS 中间件
    app.add_middleware(
        cast(Any, CORSMiddleware),
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        """写入请求上下文，供日志过滤器读取。"""
        request_id = request.headers.get("X-Request-Id") or str(uuid4())
        user_id = request.headers.get("X-User-Id")

        request_token = request_id_var.set(request_id)
        user_token = user_id_var.set(user_id)

        try:
            response = await call_next(request)
            response.headers["X-Request-Id"] = request_id
            return response
        finally:
            request_id_var.reset(request_token)
            user_id_var.reset(user_token)

    # 注册路由
    from app.api.routes import chat, websocket

    app.include_router(chat.router)
    app.include_router(websocket.router)

    logger.info("路由注册完成")

    @app.get("/health")
    async def health_check():
        """应用级健康检查端点"""
        return {
            "status": "healthy",
            "service": settings.app_name,
            "description": settings.app_description,
            "version": settings.app_version,
            "environment": settings.environment
        }

    return app

# 创建应用实例
app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        reload_excludes=settings.reload_excludes,
        log_level=settings.log_level.lower()
    )