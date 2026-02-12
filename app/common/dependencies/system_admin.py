# app/common/dependencies/system_admin.py
"""
System admin specific dependencies.
These dependencies restrict access to system admin roles only.
"""
from typing import Annotated, Dict, Any, Callable, Optional, cast, List
from uuid import UUID
from fastapi import Depends, HTTPException, status
from sqlmodel import select
from app.common.dependencies.jwt_auth import require_auth
from app.api.dependencies import get_user_service
from app.api.routes.v1.user.models import Users, UserRole
from app.api.routes.v1.user.service import UserService
from app.config import security_settings


def require_system_admin() -> Callable:
    """
    Dependency that requires the user to be a system admin.
    Only users with roles in SYSTEM_ADMIN_BYPASS_ROLES can access.
    
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

        # Check if user is a system admin
        bypass_roles = [r.lower() for r in security_settings.SYSTEM_ADMIN_BYPASS_ROLES]
        if role.name.lower() not in bypass_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="System admin access required"
            )

        return user_data

    return _dependency


def require_roles(allowed_roles: List[str]) -> Callable:
    """
    Dependency that requires the user to have one of the allowed roles.
    System admins are always allowed regardless of the allowed_roles list.
    
    Args:
        allowed_roles: List of role names that are allowed access
    
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

        # System admins always have access
        bypass_roles = [r.lower() for r in security_settings.SYSTEM_ADMIN_BYPASS_ROLES]
        if role.name.lower() in bypass_roles:
            return user_data
        
        # Check if user has one of the allowed roles
        allowed_lower = [r.lower() for r in allowed_roles]
        if role.name.lower() not in allowed_lower:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"Access denied: requires one of {allowed_roles}"
            )

        return user_data

    return _dependency
