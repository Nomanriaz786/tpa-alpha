"""
Database configuration and async session management
"""
import logging
from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from contextlib import asynccontextmanager
from config import get_settings
from models import Base

logger = logging.getLogger(__name__)

# Global engine and session factory
_engine = None
_async_session_maker = None


async def init_db():
    """Initialize database engine and session factory"""
    global _engine, _async_session_maker
    
    settings = get_settings()
    
    # Create async engine
    _engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,  # Set to True for SQL logging
        poolclass=NullPool,  # Better for serverless
    )
    
    # Create all tables
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Lightweight additive migrations for existing databases.
        await conn.execute(text('ALTER TABLE IF EXISTS pending_payments ADD COLUMN IF NOT EXISTS tx_hash_proof VARCHAR(255)'))
        await conn.execute(text('ALTER TABLE IF EXISTS pending_payments ADD COLUMN IF NOT EXISTS discord_username VARCHAR(255)'))
        await conn.execute(text('ALTER TABLE IF EXISTS payments ADD COLUMN IF NOT EXISTS pending_payment_id UUID'))
        await conn.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS uq_payment_pending_payment_id ON payments (pending_payment_id) WHERE pending_payment_id IS NOT NULL'))
        await conn.execute(text('CREATE INDEX IF NOT EXISTS idx_pending_payment_tx_hash_proof ON pending_payments (tx_hash_proof)'))
        await conn.execute(text('ALTER TABLE IF EXISTS affiliates ALTER COLUMN discord_id DROP NOT NULL'))
        await conn.execute(text('ALTER TABLE IF EXISTS guild_settings ADD COLUMN IF NOT EXISTS payment_logs_channel_id VARCHAR(30)'))
    
    # Create session factory
    _async_session_maker = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    
    logger.info("✓ Database initialized with all tables")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session (use with async context manager)"""
    if _async_session_maker is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    async with _async_session_maker() as session:
        yield session


@asynccontextmanager
async def get_session():
    """Context manager for database sessions"""
    global _async_session_maker
    
    # If not initialized, try to initialize now
    if _async_session_maker is None:
        try:
            await init_db()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise RuntimeError("Database not initialized. Call init_db() first.")
    
    async with _async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db():
    """Close database engine"""
    global _engine
    if _engine:
        await _engine.dispose()
        logger.info("✓ Database connection closed")


async def verify_db_connection():
    """Verify database connection on startup"""
    try:
        async with get_session() as session:
            await session.execute(text("SELECT 1"))
        logger.info("✓ Database connection verified")
        return True
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        return False
