# app/api/routes/v1/portfolio/dependencies.py

from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.session import get_session
from app.db.mongo_session import get_mongo_db

from app.api.routes.v1.user.service import UserService
from app.api.routes.v1.portfolio.services import PortfolioService

# DB Dependencies
SessionDep = Annotated[AsyncSession, Depends(get_session)]
MongoDBDep = Annotated[AsyncIOMotorDatabase, Depends(get_mongo_db)]

# Service Dependency - make it async
async def get_portfolio_service(
    session: SessionDep,
    mongo: MongoDBDep
) -> PortfolioService:
    return PortfolioService(session=session, mongo=mongo)


async def get_user_service(
    session: SessionDep,
    mongo: MongoDBDep
) -> UserService:
    return UserService(session=session, mongo=mongo)

PortfolioServiceDep = Annotated[PortfolioService, Depends(get_portfolio_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]

