"""
NotePassing Server - FastAPI应用入口

基于蓝牙近场发现的社交网络服务端
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import (
    device_router,
    temp_id_router,
    presence_router,
    message_router,
    friendship_router,
    websocket_router,
)

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    description="基于蓝牙近场发现的社交网络服务端",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由
app.include_router(device_router, prefix="/api/v1")
app.include_router(temp_id_router, prefix="/api/v1")
app.include_router(presence_router, prefix="/api/v1")
app.include_router(message_router, prefix="/api/v1")
app.include_router(friendship_router, prefix="/api/v1")

# 注册WebSocket路由（无前缀）
app.include_router(websocket_router)


@app.get("/health")
async def health_check():
    """
    健康检查端点
    
    Returns:
        服务状态
    """
    return {
        "status": "ok",
        "version": "0.1.0",
        "service": "notepassing-server"
    }


@app.get("/")
async def root():
    """
    根端点
    
    Returns:
        服务基本信息
    """
    return {
        "name": settings.APP_NAME,
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health"
    }


def main():
    """
    主入口函数
    """
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
