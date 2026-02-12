# app/common/dependencies/role_and_permission_check_auth.py
"""
Permission checking dependencies with system admin bypass.
System admins (configured in SYSTEM_ADMIN_BYPASS_ROLES) bypass all permission checks.
"""
from typing import Annotated, Dict, Any, Callable, Optional, cast
from uuid import UUID
from fastapi import Depends, HTTPException, status
from sqlmodel import select
from app.common.dependencies.jwt_auth import require_auth
from app.api.dependencies import get_user_service
from app.api.routes.v1.user.models import Users, UserRole, Permission, RolePermission
from app.api.routes.v1.user.service import UserService
from app.config import security_settings


def require_permission(permission_name: str) -> Callable:
    """
    Dependency factory for permission-only checks.
    - permission_name: Required permission name (injected via factory).
    
    This dependency:
    1. Validates the JWT token
    2. Fetches the user from database
    3. Fetches the user's role
    4. **BYPASSES** permission check if role is in SYSTEM_ADMIN_BYPASS_ROLES
    5. Otherwise, checks if the role has the required permission
    
    Returns user payload on success; raises 401/403 on failure.
    """
    async def _dependency(
        user_data: Annotated[Dict[str, Any], Depends(require_auth)],
        service: UserService = Depends(get_user_service),
    ) -> Dict[str, Any]:
        # Extract and validate user_id from token
        user_id_str = user_data.get("user_id") if isinstance(user_data, dict) else None
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid token: user_id missing"
            )

        try:
            user_id = UUID(user_id_str)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid user id in token"
            )

        # Fetch user from database
        q_user = select(Users).where(Users.id == user_id)
        res = await service.session.execute(q_user)
        user = res.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="User not found"
            )

        # Fetch user's role
        q_role = select(UserRole).where(UserRole.id == user.role_id)
        res = await service.session.execute(q_role)
        role = cast(Optional[UserRole], res.scalar_one_or_none())
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="User has no role assigned"
            )

        # 🔹 SYSTEM ADMIN BYPASS: Skip permission checks for configured roles
        bypass_roles = [r.lower() for r in security_settings.SYSTEM_ADMIN_BYPASS_ROLES]
        if role.name.lower() in bypass_roles:
            # System admin bypasses all permission checks
            return user_data

        # Fetch the required permission
        q_perm = select(Permission).where(Permission.name == permission_name)
        res = await service.session.execute(q_perm)
        permission = res.scalar_one_or_none()
        if not permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"Required permission '{permission_name}' does not exist"
            )

        # Check if role has the required permission
        q_rp = select(RolePermission).where(
            RolePermission.role_id == role.id,
            RolePermission.permission_id == permission.id
        )
        res = await service.session.execute(q_rp)
        rp = res.scalar_one_or_none()
        if not rp:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"Access denied: '{permission_name}' permission required"
            )

        return user_data  # Pass user payload downstream

    return _dependency


# Backward compatibility alias (deprecated)
def require_roles_and_permission(allowed_roles: list[str], permission_name: str) -> Callable:
    """
    DEPRECATED: Use require_permission instead.
    This function is kept for backward compatibility but ignores the allowed_roles parameter.
    """
    return require_permission(permission_name)