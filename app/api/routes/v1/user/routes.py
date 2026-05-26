from typing import Dict, Any, List, Annotated, Optional, TYPE_CHECKING
from uuid import UUID
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
    Response,
    Request,
    Query,
)
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import security_settings

from app.api.routes.v1.user.models import Users
from app.db.session import get_session
from app.api.routes.v1.user.service import UserService
from app.db.mongo_session import get_mongo_db

if TYPE_CHECKING:
    from app.api.dependencies import UserServiceDep
    from app.api.routes.v1.user.schemas import UserCreate, UserLogin

from app.api.dependencies import UserServiceDep
from app.api.routes.v1.user.schemas import (
    RolePermissionDeleteRequest,
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
    UserCreateResponse,
    UserLoginResponse,
    UserLogin,
    UserBasicUpdate,
    UserAdminUpdate,
    UserDetailRead,
    RoleValidatorRequest,
    RoleValidatorResponse,
    RolePermissionsResponse,
    AdminCreateUser,
    # Password Reset Schemas
    AdminPasswordResetRequest,
    ChangePasswordRequest,
    ForgetPasswordRequest,
    ForgotPasswordResponse,
    VerifyOTPRequest,
    PasswordResetResponse,
)



from app.common.dependencies.jwt_auth import (
    require_auth,
)
from app.common.dependencies.role_and_permission_check_auth import require_permission
from app.utils.security import ACCESS_TOKEN_EXPIRE_SECONDS, decode_access_token
from bson import ObjectId
import base64
from uuid import UUID
from sqlmodel import select

router = APIRouter()

# ----------------------------------------
# 🔹 User Management
# Note: Auth routes (login, logout, register) are now in /api/v1/auth
# ----------------------------------------


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
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="edit_user"))],
):
    """Admin update user - can update all fields including role and verification status"""
    updated = await service.update_user_admin(user_id, data)
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
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    size: int = Query(20, ge=1, le=100, description="Page size (max 100)"),
    # user: Annotated[Dict[str, Any], Depends(require_roles_and_permission(allowed_roles=["super_admin", "admin"], permission_name="view_users"))],
):
    """
    Admin endpoint - fetch all users with full details (password_hash is not returned).
    Supports simple page/size pagination.
    """
    offset = (page - 1) * size
    users = await service.get_all_users(limit=size, offset=offset)
    return users

# New suggestion route
@router.get("/suggestion", response_model=list[str])
async def user_suggestions(
    service: UserServiceDep,
    user: Dict[str, Any] = Depends(require_auth),
    q: str = Query(..., min_length=1, description="Search query for name or email"),
    limit: int = Query(5, ge=1, le=10, description="Max suggestions to return (1-10)"),
):
    """
    Return a small list of user suggestions (preferred_name or email) matching q.
    - DB has indexes on email and preferred_name for faster lookups.
    - Limits results on DB and on response (5-10).
    """
    suggestions = await service.fetch_user_suggestions(query=q, limit=limit)
    return suggestions

# New search route
@router.get("/search", response_model=list[UserDetailRead])
async def search_users(
    service: UserServiceDep,
    user: Dict[str, Any] = Depends(require_auth),
    q: str = Query(..., min_length=1, description="Search query for name or email"),
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    size: int = Query(20, ge=1, le=100, description="Page size (max 100)"),
):
    """
    Search users by preferred_name or email and return full user details with pagination.
    - DB has indexes on email and preferred_name for faster lookups.
    - Returns full UserDetailRead objects (with role info).
    """
    offset = (page - 1) * size
    users = await service.search_users(query=q, limit=size, offset=offset)
    return users

# ----------------------------------------
# 🔹 Permission
# ----------------------------------------

@router.post("/permissions", response_model=PermissionRead, status_code=status.HTTP_201_CREATED)
async def create_permission(
    data: PermissionCreate,
    service: UserServiceDep,  # Top-level: Uses Annotated for type-hinting
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="add_permission"))],
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

@router.delete("/role-permissions", status_code=status.HTTP_204_NO_CONTENT)
async def remove_permission_from_role(
    data: RolePermissionDeleteRequest,  # Take both from body
    service: UserServiceDep,
    user: Dict[str, Any] = Depends(require_auth),
):
    result = await service.delete_role_permission(data.role_id, data.permission_id)
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

@router.get("/roles/{role_id}/permissions", response_model=RolePermissionsResponse)
async def get_role_permissions(
    role_id: UUID,
    service: UserServiceDep,
    user: Dict[str, Any] = Depends(require_auth),
    # user: Annotated[Dict[str, Any], Depends(require_roles_and_permission(allowed_roles=["super_admin"], permission_name="view_roles"))]
):
    try:
        return await service.get_role_permissions_by_role_id(role_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/admin/users", response_model=UserDetailRead, status_code=status.HTTP_201_CREATED)
async def create_user_by_admin(
    data: AdminCreateUser,
    service: UserServiceDep,
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="add_user"))],
):
    """
    Admin endpoint to create a normal user.
    - Hashes and stores the password (no JWT / no cookie issued).
    - If role_id provided, verifies it exists; otherwise assigns default 'user' role.
    """
    result = await service.create_user_by_admin(data)
    if isinstance(result, dict) and result.get("status") == "error":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("message", "Error creating user"))
    # service returns {"status":"success","user": {...}}
    return result["user"]

# New: allow user to delete their own account
@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    service: UserServiceDep,
    user_data: Dict[str, Any] = Depends(require_auth),
):
    """
    Delete the currently authenticated user's account.
    """
    user_id = user_data.get("user_id") or user_data.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: user_id missing")
    from uuid import UUID as _UUID
    deleted = await service.delete_user(_UUID(user_id))
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# New: admin deletes a user by id
@router.delete("/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_by_admin(
    user_id: UUID,
    service: UserServiceDep,
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="delete_user"))],
):
    """
    Admin endpoint to delete a user by id.
    """
    deleted = await service.delete_user(user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ----------------------------------------
# 🔹 Password Reset Routes
# ----------------------------------------

@router.post("/password/admin-reset", response_model=PasswordResetResponse)
async def admin_reset_user_password(
    data: AdminPasswordResetRequest,
    service: UserServiceDep,
    user: Annotated[Dict[str, Any], Depends(require_permission(
        permission_name="reset_user_password"
    ))],
):
    """
    Admin/Super Admin endpoint to reset any user's password.
    Requires super_admin or admin role with reset_user_password permission.
    No daily limits apply to admin resets.
    """
    result = await service.admin_reset_password(data.email, data.new_password)
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    return result


@router.post("/password/change", response_model=PasswordResetResponse)
async def change_user_password(
    data: ChangePasswordRequest,
    service: UserServiceDep,
    user_data: Dict[str, Any] = Depends(require_auth),
):
    """
    Logged-in user changes their own password.
    Requires current password verification.
    Subject to daily limit (2 changes per day).
    """
    user_id = user_data.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: user_id missing"
        )
    
    result = await service.change_password(
        UUID(user_id),
        data.current_password,
        data.new_password,
        data.confirm_password
    )
    
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    return result


@router.post("/password/forgot", response_model=ForgotPasswordResponse)
async def forgot_password(
    response: Response,
    data: ForgetPasswordRequest,
    service: UserServiceDep,
):
    """
    Initiate forgot password flow OR resend OTP - generates OTP and sends via email.
    Sets JWT token as HTTP-only cookie for verification step.
    
    This is the ONLY endpoint for sending OTP (handles both initial and resend).
    
    Rate Limiting:
    - 30 second delay between requests
    - More than 3 send attempts result in 30 minute block
    - 2 successful password resets per 24 hours
    """
    result = await service.forgot_password_initiate(data.email)
    
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    


    # Set token as HTTP-only cookie
    token = result.pop("token")  # Remove token from response
    response.set_cookie(
        key="password_reset_token",
        value=token,
        httponly=True,
        secure=(security_settings.ENVIRONMENT == "production"),  # Set to True in production (requires HTTPS)
        samesite="lax",
        max_age=300,  # 5 minutes (same as token expiry)
    )
    
    return result


@router.post("/password/verify-otp", response_model=PasswordResetResponse)
async def verify_otp_and_reset(
    request: Request,
    response: Response,
    data: VerifyOTPRequest,
    service: UserServiceDep,
):
    """
    Verify OTP and reset password.
    Reads JWT token from HTTP-only cookie set during forgot password step.
    
    Rate Limiting:
    - 3 wrong OTP attempts result in 30 minute block
    - Subject to daily limit (2 forgot password resets per day)
    """
    # Get token from cookie
    token = request.cookies.get("password_reset_token")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Password reset token not found. Please request a new OTP."
        )
    
    result = await service.forgot_password_verify(
        token,
        data.otp,
        data.new_password,
    )
    
    if result["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    # Delete the password reset cookie after successful verification
    response.delete_cookie(key="password_reset_token")
    
    return result







