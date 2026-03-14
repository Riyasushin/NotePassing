from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from app.config import get_settings

settings = get_settings()

# Create async engine (lazy initialization for import-time compatibility)
engine = None
AsyncSessionLocal = None

def get_engine():
    """Get or create database engine."""
    global engine
    if engine is None:
        engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            poolclass=NullPool if settings.debug else None,
        )
    return engine

def get_session_factory():
    """Get or create session factory."""
    global AsyncSessionLocal
    if AsyncSessionLocal is None:
        AsyncSessionLocal = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return AsyncSessionLocal

# Base class for models
Base = declarative_base()


async def get_db() -> AsyncSession:
    """Dependency to get database session."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
