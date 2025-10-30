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
    UserBasicUpdate,
    UserAdminUpdate,
    UserRoleUpdateRequest,
    UserDetailRead,  # added
    RoleValidatorRequest,
    RoleValidatorResponse,
)

from app.api.routes.v1.user.models import (
    Users,
    UserRole,
    Permission,
    RolePermission,
)

from app.common.dependencies.jwt_auth import (
    require_auth,
)
from app.common.dependencies.role_and_permission_check_auth import require_roles_and_permission
from app.utils.security import ACCESS_TOKEN_EXPIRE_SECONDS, decode_access_token
from bson import ObjectId
import base64
from uuid import UUID
from sqlmodel import select

router = APIRouter()

# ----------------------------------------
# 🔹 user
# ----------------------------------------

@router.post("/register", response_model=UserCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    response: Response,
    service: UserServiceDep,
    data: UserCreate,  # read JSON body
):
    result = await service.create_user(data)
    
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    # Set token as HttpOnly cookie
    response.set_cookie(
        key="access_token",
        value=result["access_token"],
        httponly=True,
        secure=True,  # Set to True in production (requires HTTPS)
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_SECONDS,
    )
    
    # Don't send token in response body
    result["access_token"] = None
    return result

@router.post("/login", response_model=UserLoginResponse)
async def login_user(
    response: Response,
    service: UserServiceDep,
    data: UserLogin,  # read JSON body
):
    result = await service.authenticate_user(data)
    
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result["message"]
        )
    
    # Set token as HttpOnly cookie
    response.set_cookie(
        key="access_token",
        value=result["access_token"],
        httponly=True,
        secure=True,  # Set to True in production
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_SECONDS,
    )
    
    result["access_token"] = None
    return result

@router.post("/logout")
async def logout(
    response: Response,
    user: Dict[str, Any] = Depends(require_auth),
):
    response.delete_cookie(key="access_token")
    return {"message": "Logged out successfully"}

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
    # Cast to UUID for DB comparison
    user = await service.get_user_by_id(UUID(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.put("/me", response_model=UserRead)
async def update_current_user_basic(
    data: UserBasicUpdate,
    service: UserServiceDep,
    user_data: Dict[str, Any] = Depends(require_auth),
):
    """Update current user - only name and email (basic edit)"""
    user_id = user_data.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: user_id missing"
        )
    
    updated = await service.update_user_basic(UUID(user_id), data)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return updated

@router.put("/users/{user_id}", response_model=UserRead)
async def update_user_admin(
    user_id: UUID,
    data: UserAdminUpdate,
    service: UserServiceDep,
    user: Annotated[Dict[str, Any], Depends(require_roles_and_permission(allowed_roles=["super_admin", "admin"], permission_name="edit_user"))],
):
    """Admin update user - can update all fields including role and verification status"""
    updated = await service.update_user_admin(user_id, data)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or invalid role_id"
        )
    return updated

@router.patch("/users/{user_id}/role", response_model=UserRead)
async def update_user_role_only(
    user_id: UUID,
    data: UserRoleUpdateRequest,
    service: UserServiceDep,
    user: Dict[str, Any] = Depends(require_auth),
    # user: Annotated[Dict[str, Any], Depends(require_roles_and_permission(allowed_roles=["super_admin", "admin"], permission_name="edit_user_role"))],
):
    """Update only user role - requires admin privileges"""
    updated = await service.update_user_role_only(user_id, data.role_id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or invalid role_id"
        )
    return updated

@router.get("/users", response_model=list[UserDetailRead])
async def fetch_all_users(
    service: UserServiceDep,
    user: Dict[str, Any] = Depends(require_auth),
    # user: Annotated[Dict[str, Any], Depends(require_roles_and_permission(allowed_roles=["super_admin", "admin"], permission_name="view_users"))],
):
    """
    Admin endpoint - fetch all users with full details (password_hash is not returned).
    """
    users = await service.get_all_users()
    return users

# ----------------------------------------
# 🔹 Permission
# ----------------------------------------

@router.post("/permissions", response_model=PermissionRead, status_code=status.HTTP_201_CREATED)
async def create_permission(
    data: PermissionCreate,
    service: UserServiceDep,  # Top-level: Uses Annotated for type-hinting
    user: Annotated[Dict[str, Any], Depends(require_roles_and_permission(allowed_roles=["super_admin"], permission_name="add_permission"))],  # Factory injects roles/perms!
):
    result = await service.create_permission(data)
    if result["status"] == "error":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["message"])
    return result["permission"]

@router.get("/permissions/{permission_id}", response_model=PermissionRead)
async def get_permission(
    permission_id: UUID,
    service: UserServiceDep,
    user: Dict[str, Any] = Depends(require_auth),
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
    user: Dict[str, Any] = Depends(require_auth),
):
    permissions = await service.get_permissions()
    return permissions

@router.put("/permissions/{permission_id}", response_model=PermissionRead)
async def update_permission(
    permission_id: UUID,
    data: PermissionUpdate,
    service: UserServiceDep,
    user: Dict[str, Any] = Depends(require_auth),
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
    user: Dict[str, Any] = Depends(require_auth),
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
    data: UserRoleCreate,
    user: Dict[str, Any] = Depends(require_auth),
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
    user: Dict[str, Any] = Depends(require_auth),
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
    user: Dict[str, Any] = Depends(require_auth),
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
    user: Dict[str, Any] = Depends(require_auth),
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
    user: Dict[str, Any] = Depends(require_auth),
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
    data: RolePermissionCreate,
    user: Dict[str, Any] = Depends(require_auth),
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
    user: Dict[str, Any] = Depends(require_auth),
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
    user: Dict[str, Any] = Depends(require_auth),
):
    result = await service.delete_role_permission(role_id, permission_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error removing permission from role"
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/role-validator", response_model=RoleValidatorResponse)
async def role_validator(
    data: RoleValidatorRequest,
    service: UserServiceDep,
    user_data: Dict[str, Any] = Depends(require_auth),
):
    """
    Validate whether the current user (from JWT) has at least one of the required roles.
    Frontend should POST { required_roles: ["role1", "role2"] } with Authorization header.
    Returns { has_role: true } or { has_role: false }.
    """
    user_id = user_data.get("user_id") or user_data.get("sub")
    if not user_id:
        return {"has_role": False}
    has_role = await service.user_has_any_role(user_id, data.required_roles)
    return {"has_role": has_role}







