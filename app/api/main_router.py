from fastapi import APIRouter
from app.api.routes.v1.portfolio import routes as portfolio_routes
from app.api.routes.v1.user import routes as user_routes
from app.api.routes.v1.project import routes as project_routes
from app.api.routes.v1.auth import routes as auth_routes


api_router = APIRouter()
api_router.include_router(auth_routes.router, prefix="/api/v1/auth", tags=["auth"])
api_router.include_router(portfolio_routes.router, prefix="/api/v1/portfolio", tags=["portfolio"])
api_router.include_router(user_routes.router, prefix="/api/v1/user", tags=["user"])
api_router.include_router(project_routes.router, prefix="/api/v1/project", tags=["project"])




