from typing import Any, Dict, Optional, Annotated
from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Request,
    status,
    UploadFile,
    Response,
    Depends
)

from app.api.dependencies import UserServiceDep
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
    UserCreateResponse,
    UserLoginResponse,
    UserLogin,
)

from app.common.dependencies.jwt_auth import (
    require_auth,
)
from bson import ObjectId
import base64
from uuid import UUID

router = APIRouter()

# ----------------------------------------
# 🔹 user
# ----------------------------------------

@router.post("/register", response_model=UserCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    service: UserServiceDep,
    data: UserCreate = Depends(),
):
    result = await service.create_user(data)
    
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )

    return result

@router.post("/login", response_model=UserLoginResponse)
async def login_user(
    service: UserServiceDep,
    data: UserLogin = Depends(),
):
    result = await service.authenticate_user(data)
    
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result["message"]
        )
    
    return result


@router.get("/me", response_model=UserRead)
async def get_current_user(
    request: Request,
    service: UserServiceDep,
    user_data: Dict[str, Any] = Depends(require_auth),
):
    """Get current user - requires authentication"""
    user_id = user_data.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: user_id missing"
        )
    user = await service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


# ----------------------------------------
# 🔹 Permission
# ----------------------------------------

@router.post("/permissions", response_model=PermissionRead, status_code=status.HTTP_201_CREATED)
async def create_permission(
    service: UserServiceDep,
    data: PermissionCreate = Depends(require_auth),
):
    result = await service.create_permission(data)
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    return result

@router.get("/permissions/{permission_id}", response_model=PermissionRead)
async def get_permission(
    permission_id: UUID,
    service: UserServiceDep,

):
    permission = await service.get_permission_by_id(permission_id)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )
    return permission

@router.get("/permissions", response_model=list[PermissionRead])
async def list_permissions(
    service: UserServiceDep,
):
    permissions = await service.get_permissions()
    return permissions

@router.put("/permissions/{permission_id}", response_model=PermissionRead)
async def update_permission(
    permission_id: UUID,
    data: PermissionUpdate,
    service: UserServiceDep,  # removed the `= Depends()` default to avoid Annotated+default conflict
):
    """
    Update a permission by ID.
    Expects a PermissionUpdate body and returns the updated PermissionRead.
    """
    try:
        updated = await service.update_permission(permission_id, data)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error updating permission: {e}")
    
@router.delete("/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission(
    permission_id: UUID,
    service: UserServiceDep,
):
    """
    Delete a permission by ID.
    Returns 204 No Content on success.
    """
    try:
        deleted = await service.delete_permission(permission_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error deleting permission: {e}")
    
# ----------------------------------------
# 🔹 User Role
# ----------------------------------------

@router.post("/roles", response_model=UserRoleRead, status_code=status.HTTP_201_CREATED)
async def create_user_role(
    service: UserServiceDep,
    data: UserRoleCreate = Depends(),
):
    result = await service.create_user_role(data)
    # service returns an error dict on duplicate/db error
    if isinstance(result, dict) and result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Error creating user role")
        )
    return result

@router.get("/roles/{role_id}", response_model=UserRoleRead)
async def get_user_role(
    role_id: UUID,
    service: UserServiceDep,
):
    role = await service.get_user_role_by_id(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User role not found"
        )
    return role

@router.get("/roles", response_model=list[UserRoleRead])
async def list_user_roles(
    service: UserServiceDep,
):
    roles = await service.get_user_roles()
    if roles is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No user roles found"
        )
    return roles

@router.put("/roles/{role_id}", response_model=UserRoleRead)
async def update_user_role(
    role_id: UUID,
    data: UserRoleUpdate,
    service: UserServiceDep,
):
    """
    Update a user role by ID.
    Expects a UserRoleUpdate body and returns the updated UserRoleRead.
    """
    try:
        updated = await service.update_user_role(role_id, data)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User role not found")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error updating user role: {e}")
    
@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_role(
    role_id: UUID,
    service: UserServiceDep,
):
    """
    Delete a user role by ID.
    Returns 204 No Content on success.
    """
    try:
        deleted = await service.delete_user_role(role_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User role not found")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error deleting user role: {e}")
    

# ----------------------------------------
# 🔹 Role Permissions
# ----------------------------------------

@router.post("/role-permissions", response_model=RolePermissionRead, status_code=status.HTTP_201_CREATED)
async def assign_permission_to_role(
    service: UserServiceDep,
    data: RolePermissionCreate = Depends(),
):
    result = await service.create_role_permission(data)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Error assigning permission to role")
        )
    return result

@router.get("/role-permissions", response_model=list[RolePermissionRead])
async def list_role_permissions(
    service: UserServiceDep,
):
    role_permissions = await service.get_role_permissions()
    if role_permissions is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No role permissions found"
        )
    return role_permissions



@router.delete("/role-permissions/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_permission_from_role(
    role_id: UUID,
    permission_id: UUID,
    service: UserServiceDep,
):
    result = await service.delete_role_permission(role_id, permission_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error removing permission from role"
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)







