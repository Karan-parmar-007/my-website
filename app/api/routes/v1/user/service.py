from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from uuid import UUID
from typing import List, Optional

from app.api.routes.v1.user.models import UserRole, Permission, Users, RolePermission
from app.api.routes.v1.user.schemas import  UserRoleRead, UserRoleCreate, UserRoleUpdate
from app.api.routes.v1.user.schemas import PermissionRead, PermissionCreate, PermissionUpdate, RolePermissionRead, RolePermissionCreate
from app.api.routes.v1.user.schemas import UserRead, UserCreate, UserUpdate, UserLogin, LoginResponse, ForgetPasswordRequest, ResetPasswordRequest, ChangePasswordRequest, TokenResponse

class UserService:
    def __init__(self, session: AsyncSession, mongo: AsyncIOMotorDatabase):
        self.session = session
        self.mongo = mongo


# ----------------------------------------
# 🔹 User
# ----------------------------------------


    async def get_user_by_id(self, user_id: UUID) -> dict:
        query = select(Users).where(Users.id == user_id)
        result = await self.session.execute(query)
        user = result.scalar_one_or_none()
        if not user:
            return {}

        user_data = UserRead.model_validate(user).model_dump()
        return user_data

    async def create_user(self, user_create: UserCreate) -> dict:
        user = Users.model_validate(user_create)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return UserRead.model_validate(user).model_dump()
    
    async def update_user(self, user_id: UUID, user_update: UserUpdate) -> Optional[dict]:
        query = select(Users).where(Users.id == user_id)
        result = await self.session.execute(query)
        user = result.scalar_one_or_none()
        if not user:
            return None

        user_data = user_update.model_dump(exclude_unset=True)
        for key, value in user_data.items():
            setattr(user, key, value)

        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return UserRead.model_validate(user).model_dump()
    
    async def delete_user(self, user_id: UUID) -> bool:
        query = select(Users).where(Users.id == user_id)
        result = await self.session.execute(query)
        user = result.scalar_one_or_none()
        if not user:
            return False

        await self.session.delete(user)
        await self.session.commit()
        return True
    


    
# ----------------------------------------
# 🔹 User Role
# ----------------------------------------

    async def get_user_roles(self) -> List[dict]:
        query = select(UserRole)
        result = await self.session.execute(query)
        user_roles = result.scalars().all()
        return [UserRoleRead.model_validate(ur).model_dump() for ur in user_roles]
    
    async def get_user_role_by_id(self, role_id: UUID) -> Optional[dict]:
        query = select(UserRole).where(UserRole.id == role_id)
        result = await self.session.execute(query)
        user_role = result.scalar_one_or_none()
        if not user_role:
            return None
        return UserRoleRead.model_validate(user_role).model_dump()
    
    async def create_user_role(self, user_role_create: UserRoleCreate) -> dict:
        user_role = UserRole.model_validate(user_role_create)
        self.session.add(user_role)
        await self.session.commit()
        await self.session.refresh(user_role)
        return UserRoleRead.model_validate(user_role).model_dump()
    
    async def update_user_role(self, role_id: UUID, user_role_update: UserRoleUpdate) -> Optional[dict]:
        query = select(UserRole).where(UserRole.id == role_id)
        result = await self.session.execute(query)
        user_role = result.scalar_one_or_none()
        if not user_role:
            return None

        user_role_data = user_role_update.model_dump(exclude_unset=True)
        for key, value in user_role_data.items():
            setattr(user_role, key, value)

        self.session.add(user_role)
        await self.session.commit()
        await self.session.refresh(user_role)
        return UserRoleRead.model_validate(user_role).model_dump()
    
    async def delete_user_role(self, role_id: UUID) -> bool:
        query = select(UserRole).where(UserRole.id == role_id)
        result = await self.session.execute(query)
        user_role = result.scalar_one_or_none()
        if not user_role:
            return False

        await self.session.delete(user_role)
        await self.session.commit()
        return True
    
# ----------------------------------------
# 🔹 Permission
# ----------------------------------------

    async def get_permissions(self) -> List[dict]:
        query = select(Permission)
        result = await self.session.execute(query)
        permissions = result.scalars().all()
        return [PermissionRead.model_validate(p).model_dump() for p in permissions]
    
    async def get_permission_by_id(self, permission_id: UUID) -> Optional[dict]:
        query = select(Permission).where(Permission.id == permission_id)
        result = await self.session.execute(query)
        permission = result.scalar_one_or_none()
        if not permission:
            return None
        return PermissionRead.model_validate(permission).model_dump()
    
    async def create_permission(self, permission_create: PermissionCreate) -> dict:
        permission = Permission.model_validate(permission_create)
        self.session.add(permission)
        await self.session.commit()
        await self.session.refresh(permission)
        return PermissionRead.model_validate(permission).model_dump()
    
    async def update_permission(self, permission_id: UUID, permission_update: PermissionUpdate) -> Optional[dict]:
        query = select(Permission).where(Permission.id == permission_id)
        result = await self.session.execute(query)
        permission = result.scalar_one_or_none()
        if not permission:
            return None

        permission_data = permission_update.model_dump(exclude_unset=True)
        for key, value in permission_data.items():
            setattr(permission, key, value)

        self.session.add(permission)
        await self.session.commit()
        await self.session.refresh(permission)
        return PermissionRead.model_validate(permission).model_dump()
    
    async def delete_permission(self, permission_id: UUID) -> bool:
        query = select(Permission).where(Permission.id == permission_id)
        result = await self.session.execute(query)
        permission = result.scalar_one_or_none()
        if not permission:
            return False

        await self.session.delete(permission)
        await self.session.commit()
        return True
    
# ----------------------------------------
# 🔹 RolePermission
# ----------------------------------------

    async def get_role_permissions(self) -> List[dict]:
        query = select(RolePermission)
        result = await self.session.execute(query)
        role_permissions = result.scalars().all()
        return [RolePermissionRead.model_validate(rp).model_dump() for rp in role_permissions]
    
    async def get_role_permission_by_id(self, role_id: UUID, permission_id: UUID) -> Optional[dict]:
        query = select(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id
        )
        result = await self.session.execute(query)
        role_permission = result.scalar_one_or_none()
        if not role_permission:
            return None
        return RolePermissionRead.model_validate(role_permission).model_dump()
    
    async def get_role_permissions_by_role_id(self, role_id: UUID) -> List[dict]:
        query = select(RolePermission).where(RolePermission.role_id == role_id)
        result = await self.session.execute(query)
        role_permissions = result.scalars().all()
        return [RolePermissionRead.model_validate(rp).model_dump() for rp in role_permissions]
    
    async def get_role_permissions_by_permission_id(self, permission_id: UUID) -> List[dict]:
        query = select(RolePermission).where(RolePermission.permission_id == permission_id)
        result = await self.session.execute(query)
        role_permissions = result.scalars().all()
        return [RolePermissionRead.model_validate(rp).model_dump() for rp in role_permissions]
    
    async def create_role_permission(self, role_permission_create: RolePermissionCreate) -> dict:
        role_permission = RolePermission.model_validate(role_permission_create)
        self.session.add(role_permission)
        await self.session.commit()
        await self.session.refresh(role_permission)
        return RolePermissionRead.model_validate(role_permission).model_dump()

    async def delete_role_permission(self, role_id: UUID, permission_id: UUID) -> bool:
        query = select(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id
        )
        result = await self.session.execute(query)
        role_permission = result.scalar_one_or_none()
        if not role_permission:
            return False

        await self.session.delete(role_permission)
        await self.session.commit()
        return True
    














