"""
MongoDB index creation and TTL setup for password reset collections.
Run this script once during deployment or database initialization.
"""

from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
from app.config import db_settings, email_settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_indexes():
    """
    Create MongoDB indexes for password reset collections.
    """
    client = AsyncIOMotorClient(db_settings.MONGO_URI)
    db = client[db_settings.MONGO_DB_NAME]
    
    logger.info("Creating MongoDB indexes for password reset...")
    
    # OTP Verifications Collection
    otp_collection = db["otp_verifications"]
    
    # 1. Unique index on email
    await otp_collection.create_index("email", unique=True)
    logger.info("✅ Created unique index on 'email' in otp_verifications")
    
    # 2. TTL index on expire_at (auto-delete after expiration)
    await otp_collection.create_index("expire_at", expireAfterSeconds=0)
    logger.info("✅ Created TTL index on 'expire_at' in otp_verifications")
    
    # Password Change Logs Collection
    logs_collection = db["password_change_logs"]
    
    # 1. Compound index on email + change_method for efficient lookups
    await logs_collection.create_index([("email", 1), ("change_method", 1)])
    logger.info("✅ Created compound index on 'email' and 'change_method' in password_change_logs")
    
    # 2. TTL index on expire_at (auto-delete after 24 hours)
    await logs_collection.create_index("expire_at", expireAfterSeconds=0)
    logger.info("✅ Created TTL index on 'expire_at' in password_change_logs")
    
    logger.info("🎉 All indexes created successfully!")
    logger.info("📝 MongoDB will automatically delete expired records using TTL indexes")
    
    client.close()


if __name__ == "__main__":
    # Create indexes
    asyncio.run(create_indexes())
