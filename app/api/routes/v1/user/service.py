from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from uuid import UUID
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.api.routes.v1.user.models import UserRole, Permission, Users, RolePermission
from app.api.routes.v1.user.schemas import  UserRoleRead, UserRoleCreate, UserRoleUpdate
from app.api.routes.v1.user.schemas import PermissionRead, PermissionCreate, PermissionUpdate, RolePermissionRead, RolePermissionCreate
from app.api.routes.v1.user.schemas import UserRead, UserCreate, UserUpdate, UserLogin
from app.utils.security import hash_password, issue_access_token, verify_password

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
        return UserRead.model_validate(user).model_dump()

    async def _get_or_create_default_role(self) -> UserRole:
        # Try to find a role named "user", otherwise create it
        q = select(UserRole).where(UserRole.name == "user")
        res = await self.session.execute(q)
        role = res.scalar_one_or_none()
        if role:
            return role
        role = UserRole(name="user", description="Default user role")
        self.session.add(role)
        # flush to get role.id without committing yet
        await self.session.flush()
        return role

    async def _get_or_create_role_by_name(self, name: str) -> UserRole:
        """Find a role by name, create it if missing (flush but do not commit)."""
        q = select(UserRole).where(UserRole.name == name)
        res = await self.session.execute(q)
        role = res.scalar_one_or_none()
        if role:
            return role
        role = UserRole(name=name, description=f"{name} role")
        self.session.add(role)
        await self.session.flush()
        return role

    async def create_user(self, user_create: UserCreate) -> dict:
        try:
            # Check if user already exists by email
            query = select(Users).where(
                (Users.email == user_create.email)
            )
            result = await self.session.execute(query)
            existing = result.scalar_one_or_none()
            if existing:
                return {"status": "error", "message": "User with this email already exists"}

            role = await self._get_or_create_default_role()

            user = Users(
                preferred_name=user_create.preferred_name,
                email=user_create.email,
                password_hash=hash_password(user_create.password),
                role_id=role.id,
            )
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)

            token_bundle = issue_access_token(
                subject=str(user.id),
                additional_claims={"user_id": str(user.id), "email": str(user.email)}
            )

            return {
                "status": "success",
                "message": "User registered successfully",
                **token_bundle,
                "user": UserRead.model_validate(user).model_dump(),
            }

        except IntegrityError:
            await self.session.rollback()
            return {"status": "error", "message": "Constraint violation creating user"}
        except Exception as e:
            await self.session.rollback()
            return {"status": "error", "message": f"Failed to create user: {e}"}

    async def authenticate_user(self, user_login: UserLogin) -> dict:
        try:
            query = select(Users).where(Users.email == user_login.email)
            result = await self.session.execute(query)
            user = result.scalar_one_or_none()
            if not user or not verify_password(user_login.password, user.password_hash):
                return {"status": "error", "message": "Invalid email or password"}

            token_bundle = issue_access_token(
                subject=str(user.id),
                additional_claims={"user_id": str(user.id), "email": str(user.email)}
            )

            return {
                "status": "success",
                "message": "Login successful",
                **token_bundle,
                "user": UserRead.model_validate(user).model_dump(),
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to authenticate: {e}"}

    async def update_user(self, user_id: UUID, user_update: UserUpdate) -> Optional[dict]:
        query = select(Users).where(Users.id == user_id)
        result = await self.session.execute(query)
        user = result.scalar_one_or_none()
        if not user:
            return None

        data = user_update.model_dump(exclude_unset=True)
        # handle password separately
        if "password" in data:
            user.password_hash = hash_password(data.pop("password"))

        for key, value in data.items():
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
        roles = result.scalars().all()
        return [UserRoleRead.model_validate(ur).model_dump() for ur in roles]
    
    async def get_user_role_by_id(self, role_id: UUID) -> Optional[dict]:
        query = select(UserRole).where(UserRole.id == role_id)
        result = await self.session.execute(query)
        user_role = result.scalar_one_or_none()
        if not user_role:
            return None
        return UserRoleRead.model_validate(user_role).model_dump()
    
    async def create_user_role(self, user_role_create: UserRoleCreate) -> dict:
        try:
            role = UserRole(**user_role_create.model_dump())
            self.session.add(role)
            await self.session.commit()
            await self.session.refresh(role)
            return UserRoleRead.model_validate(role).model_dump()
        except IntegrityError:
            await self.session.rollback()
            return {"status": "error", "message": "Role name must be unique"}
        except Exception as e:
            await self.session.rollback()
            return {"status": "error", "message": f"Failed to create role: {e}"}
    
    async def update_user_role(self, role_id: UUID, user_role_update: UserRoleUpdate) -> Optional[dict]:
        query = select(UserRole).where(UserRole.id == role_id)
        result = await self.session.execute(query)
        user_role = result.scalar_one_or_none()
        if not user_role:
            return None

        data = user_role_update.model_dump(exclude_unset=True)
        for key, value in data.items():
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
        try:
            # create permission (but don't commit yet so we can also create role-permission in same transaction)
            permission = Permission(**permission_create.model_dump())
            self.session.add(permission)
            await self.session.flush()  # ensure permission.id is available

            # ensure super_admin role exists (create if missing)
            super_role = await self._get_or_create_role_by_name("super_admin")

            # only create role-permission link if it doesn't already exist
            q = select(RolePermission).where(
                RolePermission.role_id == super_role.id,
                RolePermission.permission_id == permission.id
            )
            res = await self.session.execute(q)
            existing_rp = res.scalar_one_or_none()
            if not existing_rp:
                rp = RolePermission(role_id=super_role.id, permission_id=permission.id)
                self.session.add(rp)

            # commit everything together
            await self.session.commit()
            await self.session.refresh(permission)

            return {"status": "success", "permission": PermissionRead.model_validate(permission).model_dump()}
        except IntegrityError:
            await self.session.rollback()
            return {"status": "error", "message": "Permission name must be unique"}
        except Exception as e:
            await self.session.rollback()
            return {"status": "error", "message": f"Failed to create permission: {e}"}
    
    async def update_permission(self, permission_id: UUID, permission_update: PermissionUpdate) -> Optional[dict]:
        query = select(Permission).where(Permission.id == permission_id)
        result = await self.session.execute(query)
        permission = result.scalar_one_or_none()
        if not permission:
            return None

        data = permission_update.model_dump(exclude_unset=True)
        for key, value in data.items():
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
        role_permission = RolePermission(**role_permission_create.model_dump())
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















