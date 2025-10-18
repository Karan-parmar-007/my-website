from fastapi import APIRouter
from app.api.routes.v1.portfolio import routes as portfolio_routes
from app.api.routes.v1.user import routes as user_routes


api_router = APIRouter()
api_router.include_router(portfolio_routes.router, prefix="/api/v1/portfolio", tags=["portfolio"])
api_router.include_router(user_routes.router, prefix="/api/v1/user", tags=["user"])



