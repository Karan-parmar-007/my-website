from fastapi import FastAPI
from app.api.main_router import api_router
from app.db.mongo_session import connect_to_mongo, close_mongo_connection
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
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
        "http://168.220.236.230",      # Fixed: removed .com
        "https://karanparmar.in",
        "https://www.karanparmar.in"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)