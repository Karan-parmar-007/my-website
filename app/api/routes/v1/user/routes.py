from typing import Optional, Annotated
from fastapi import (
    APIRouter,
    HTTPException,
    status,
    UploadFile,
    Response,
    Depends
)

from app.api.dependencies import PortfolioServiceDep
from app.api.routes.v1.user.schemas import (
    UserRoleRead,
    UserRoleCreate,
    UserRoleUpdate,
    PermissionRead,
    PermissionCreate,
    PermissionUpdate,
    RolePermissionRead,
    RolePermissionCreate,
    UserRead,
    UserCreate,
    UserUpdate,
)
from bson import ObjectId
import base64
from uuid import UUID

router = APIRouter()

# ----------------------------------------
# 🔹 user
# ----------------------------------------




