"""
FastAPI 应用入口

负责创建 FastAPI 实例、配置中间件、注册路由和 WebSocket 端点。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
import uvicorn

from app.core.config import get_settings
from app.core.logger import setup_logging

# 初始化配置和日志
settings = get_settings()
setup_logging()

def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例"""
    
    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.SHOW_DOCS else None,
        redoc_url="/redoc" if settings.SHOW_DOCS else None,
    )
    
    # 配置 CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 生产环境强制 HTTPS
    if not settings.DEBUG:
        app.add_middleware(HTTPSRedirectMiddleware)
    
    # TODO: 注册路由
    # from app.api.routes import chat, websocket
    # app.include_router(chat.router, prefix="/api/v1")
    # app.include_router(websocket.router)
    
    @app.get("/health")
    async def health_check():
        """健康检查端点"""
        return {"status": "healthy", "version": settings.APP_VERSION}
    
    return app

# 创建应用实例
app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower()
    )