from fastapi import FastAPI
from app.api.main_router import api_router
from app.db.mongo_session import connect_to_mongo, close_mongo_connection
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(title="Karan Parmar", lifespan=lifespan)

app.include_router(api_router)