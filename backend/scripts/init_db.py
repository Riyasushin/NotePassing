#!/usr/bin/env python3
"""Initialize database with tables and seed data."""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings
from app.database import Base


async def init_db():
    """Create all tables."""
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        # Create tables
        await conn.run_sync(Base.metadata.create_all)
    
    await engine.dispose()
    print("✅ Database initialized!")


if __name__ == "__main__":
    asyncio.run(init_db())
