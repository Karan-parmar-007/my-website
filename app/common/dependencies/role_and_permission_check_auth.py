# app/common/dependencies/role_and_permission_check_auth.py (updated)
from typing import Annotated, List, Dict, Any, Callable, Optional, cast
from uuid import UUID
from fastapi import Depends, HTTPException, status
from sqlmodel import select
from app.common.dependencies.jwt_auth import require_auth
from app.api.dependencies import get_user_service  # Import the callable!
from app.api.routes.v1.user.models import Users, UserRole, Permission, RolePermission
from app.api.routes.v1.user.service import UserService

def require_roles_and_permission(allowed_roles: List[str], permission_name: str) -> Callable:
    """
    Dependency factory for role/permission checks.
    - allowed_roles: List of allowed role names (injected via factory).
    - permission_name: Required permission name (injected via factory).
    Returns user payload on success; raises 401/403 on failure.
    """
    async def _dependency(
        user_data: Annotated[Dict[str, Any], Depends(require_auth)],
        service: UserService = Depends(get_user_service),  # Use the callable here!
    ) -> Dict[str, Any]:
        # Your existing logic remains unchanged...
        user_id_str = user_data.get("user_id") if isinstance(user_data, dict) else None
        if not user_id_str:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: user_id missing")

        try:
            user_id = UUID(user_id_str)
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user id in token")

        # Fetch user...
        q_user = select(Users).where(Users.id == user_id)
        res = await service.session.execute(q_user)
        user = res.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        # Fetch role...
        q_role = select(UserRole).where(UserRole.id == user.role_id)
        res = await service.session.execute(q_role)
        # Cast the DB result to UserRole for static check and use getattr to safely access attributes
        role = cast(Optional[UserRole], res.scalar_one_or_none())
        if role is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User has no role assigned")

        if getattr(role, "name", None) not in allowed_roles:  # Uses injected allowed_roles!
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User does not have required role")

        # Fetch permission by injected name...
        q_perm = select(Permission).where(Permission.name == permission_name)
        res = await service.session.execute(q_perm)
        permission = res.scalar_one_or_none()
        if not permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Required permission does not exist")

        # Check role-permission link...
        q_rp = select(RolePermission).where(
            RolePermission.role_id == role.id,
            RolePermission.permission_id == permission.id
        )
        res = await service.session.execute(q_rp)
        rp = res.scalar_one_or_none()
        if not rp:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User role lacks required permission")

        return user_data  # Pass user payload downstream

    return _dependency