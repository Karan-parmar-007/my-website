from fastapi import FastAPI
from app.api.main_router import api_router
from app.db.mongo_session import connect_to_mongo, close_mongo_connection
from app.api.middlewares.csrf import CSRFMiddleware
from app.cron.cleanup_tokens import cleanup_expired_tokens
from app.config import security_settings
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
from datetime import datetime, time, timezone

logger = logging.getLogger(__name__)

# Background task for scheduled cleanup
_scheduler_task = None


async def schedule_midnight_cleanup():
    """
    Background task that runs cleanup at the configured hour every day.
    Uses hourly checks for simplicity and reliability.
    """
    last_run_day = None
    
    while True:
        try:
            now = datetime.now(timezone.utc)
            target_hour = security_settings.REFRESH_TOKEN_CLEANUP_HOUR
            
            # Run if it's the target hour and we haven't run today
            if now.hour == target_hour and last_run_day != now.day:
                logger.info("[SCHEDULER] Running scheduled token cleanup")
                await cleanup_expired_tokens()
                last_run_day = now.day
            
            # Sleep for 30 minutes before checking again
            await asyncio.sleep(1800)
        except Exception as e:
            logger.error(f"[SCHEDULER] Error in cleanup scheduler: {e}")
            await asyncio.sleep(60)  # Wait a minute before retrying


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler_task
    
    # Connect to MongoDB
    await connect_to_mongo()
    
    # Run cleanup on startup
    logger.info("[STARTUP] Running initial token cleanup")
    try:
        await cleanup_expired_tokens()
    except Exception as e:
        logger.error(f"[STARTUP] Initial cleanup failed: {e}")
    
    # Start background scheduler
    _scheduler_task = asyncio.create_task(schedule_midnight_cleanup())
    logger.info("[STARTUP] Midnight cleanup scheduler started")
    
    yield
    
    # Cleanup on shutdown
    if _scheduler_task:
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
    
    await close_mongo_connection()

app = FastAPI(title="Karan Parmar", lifespan=lifespan)

app.include_router(api_router)

# Configure CORS with correct origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:4173",
        "http://localhost:5173",
        "https://karanparmar.in",
        "https://www.karanparmar.in",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CSRF Protection Middleware
# Note: Added after CORS so CSRF checks run on authenticated requests
app.add_middleware(CSRFMiddleware)

