# app/db/mongo_session.py

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional

from app.config import db_settings  # assuming you store MONGO_URI and DB name in config

class MongoSession:
    client: Optional[AsyncIOMotorClient] = None

mongo_session = MongoSession()

async def connect_to_mongo() -> None:
    mongo_session.client = AsyncIOMotorClient(db_settings.MONGO_URI)
    print("✅ Connected to MongoDB")

async def close_mongo_connection() -> None:
    if mongo_session.client:
        mongo_session.client.close()
        print("🛑 MongoDB connection closed")

def get_mongo_db() -> AsyncIOMotorDatabase:
    if not mongo_session.client:
        raise RuntimeError("MongoDB client not initialized")
    return mongo_session.client[db_settings.MONGO_DB_NAME]
