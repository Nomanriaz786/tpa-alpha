#!/usr/bin/env python3
"""
Initialize database tables
Run this once to create all tables from SQLAlchemy models
"""
import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine
from models import Base
from config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_db():
    """Create all tables in the database"""
    settings = get_settings()
    
    # Create async engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=True,  # Show SQL statements
    )
    
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✓ Database tables initialized successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize database: {e}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_db())
