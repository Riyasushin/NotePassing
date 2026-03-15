"""NotePassing API main application."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.utils.exceptions import setup_exception_handlers
from app.routers import device, temp_id, message, friendship, block, presence, websocket as ws_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - create tables on startup."""
    # Startup: Create all tables
    from app.database import get_engine, Base
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created")
    
    yield
    
    # Shutdown: cleanup if needed
    pass


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        description="NotePassing - Anonymous nearby messaging API",
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )
    
    # Setup exception handlers
    setup_exception_handlers(app)
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure properly for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    upload_root = Path(settings.upload_root_dir)
    upload_root.mkdir(parents=True, exist_ok=True)
    Path(settings.avatar_upload_dir).mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(upload_root)), name="uploads")
    
    # Include routers
    app.include_router(device.router, prefix="/api/v1")
    app.include_router(temp_id.router, prefix="/api/v1")
    app.include_router(message.router, prefix="/api/v1")
    app.include_router(friendship.router, prefix="/api/v1")
    app.include_router(block.router, prefix="/api/v1")
    app.include_router(presence.router, prefix="/api/v1")
    
    # Include WebSocket router
    app.include_router(ws_router.router)
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "ok", "version": "1.0.0"}
    
    @app.get("/")
    async def root():
        return {
            "app": settings.app_name,
            "version": "1.0.0",
            "docs": "/docs",
        }
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
