# app/cron/cleanup_tokens.py
"""
Cron job for cleaning up expired refresh tokens.
Runs at midnight (configurable via REFRESH_TOKEN_CLEANUP_HOUR in config).

Usage:
    This script can be run:
    1. As a standalone script: `python -m app.cron.cleanup_tokens`
    2. Via cron/systemd timer at midnight
    3. Via APScheduler if integrated into the main app
"""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import delete

from app.config import db_settings, security_settings
from app.api.routes.v1.auth.models import RefreshToken

logger = logging.getLogger(__name__)


async def cleanup_expired_tokens() -> int:
    """
    Delete all expired refresh tokens from the database.
    
    Returns:
        Number of tokens deleted
    """
    # Create async engine
    engine = create_async_engine(db_settings.POSTGRES_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Delete expired tokens
        query = delete(RefreshToken).where(
            RefreshToken.expires_at < datetime.now(timezone.utc)
        )
        result = await session.execute(query)
        await session.commit()
        
        deleted_count = result.rowcount
        logger.info(f"[CRON] Cleaned up {deleted_count} expired refresh tokens")
        return deleted_count
    
    await engine.dispose()


async def main():
    """Main entry point for the cleanup script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    logger.info(f"[CRON] Starting expired token cleanup at {datetime.now(timezone.utc)}")
    
    try:
        count = await cleanup_expired_tokens()
        logger.info(f"[CRON] Cleanup complete. Deleted {count} tokens.")
    except Exception as e:
        logger.error(f"[CRON] Cleanup failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
