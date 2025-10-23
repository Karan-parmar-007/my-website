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
from app.api.routes.v1.user.schemas import UserRead, UserCreate, UserUpdate, UserLogin, ForgetPasswordRequest, ResetPasswordRequest, ChangePasswordRequest
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

        user_data = UserRead.model_validate(user).model_dump()
        return user_data

    async def create_user(self, user_create: UserCreate) -> dict:
        try:
            # Check if user already exists
            query = select(Users).where(Users.email == user_create.email)
            result = await self.session.execute(query)
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                return {
                    "status": "error",
                    "message": "User with this email already exists",
                    "access_token": None,
                    "token_type": None,
                    "access_token_expires_in": None,
                    "user": None,
                }
                
            # Get default role (you might want to create this if it doesn't exist)
            role_query = select(UserRole).where(UserRole.name == "user")
            role_result = await self.session.execute(role_query)
            default_role = role_result.scalar_one_or_none()
            
            if not default_role:
                # Create default role if it doesn't exist
                default_role = UserRole(name="user", description="Default user role")
                self.session.add(default_role)
                await self.session.commit()
                await self.session.refresh(default_role)
            
            # Hash password and create user
            hashed_password = hash_password(user_create.password)
            new_user = Users(
                preferred_name=user_create.preferred_name,
                email=user_create.email,
                password_hash=hashed_password,
                role_id=default_role.id
            )
            
            self.session.add(new_user)
            await self.session.commit()
            await self.session.refresh(new_user)
            
            # Generate JWT token - THIS IS THE KEY PART
            tokens = issue_access_token(str(new_user.id), {"user_id": str(new_user.id)})

            user_data = UserRead.model_validate(new_user).model_dump()

            return {
                "status": "success",
                "message": "User registered successfully",
                **tokens,
                "user": user_data,
            }
            
        except Exception as e:
            await self.session.rollback()
            return {
                "status": "error",
                "message": str(e),
                "access_token": None,
                "token_type": None,
                "access_token_expires_in": None,
                "user": None,
            }

    async def authenticate_user(self, user_login: UserLogin) -> dict:
        try:
            # Find user by email
            query = select(Users).where(Users.email == user_login.email)
            result = await self.session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                return {
                    "status": "error",
                    "message": "Invalid email or password",
                    "access_token": None,
                    "token_type": None,
                    "access_token_expires_in": None,
                    "user": None,
                }
            
            # Verify password
            if not verify_password(user_login.password, user.password_hash):
                return {
                    "status": "error",
                    "message": "Invalid email or password",
                    "access_token": None,
                    "token_type": None,
                    "access_token_expires_in": None,
                    "user": None,
                }
            
            # Generate JWT token - THIS IS THE KEY PART
            tokens = issue_access_token(str(user.id), {"user_id": str(user.id)})

            user_data = UserRead.model_validate(user).model_dump()

            return {
                "status": "success",
                "message": "Login successful",
                **tokens,
                "user": user_data,
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "access_token": None,
                "token_type": None,
                "access_token_expires_in": None,
                "user": None,
            }

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
        try:
            # check duplicate by name first
            query = select(UserRole).where(UserRole.name == user_role_create.name)
            result = await self.session.execute(query)
            existing = result.scalar_one_or_none()
            if existing:
                return {"status": "error", "message": "User role with this name already exists"}

            user_role = UserRole(**user_role_create.model_dump())
            self.session.add(user_role)
            await self.session.commit()
            await self.session.refresh(user_role)
            return UserRoleRead.model_validate(user_role).model_dump()

        except IntegrityError:
            await self.session.rollback()
            return {"status": "error", "message": "Database integrity error: duplicate or invalid data"}
        except Exception as e:
            await self.session.rollback()
            return {"status": "error", "message": f"Error creating user role: {e}"}
    
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
        try:
            # check duplicate by name first
            query = select(Permission).where(Permission.name == permission_create.name)
            result = await self.session.execute(query)
            existing = result.scalar_one_or_none()
            if existing:
                return {"status": "error", "message": "Permission with this name already exists"}

            # create permission (SQLModel defaults applied)
            permission = Permission(**permission_create.model_dump())
            self.session.add(permission)
            await self.session.commit()
            await self.session.refresh(permission)

            permission_data = PermissionRead.model_validate(permission).model_dump()
            return {"status": "success", "permission": permission_data}

        except IntegrityError as e:
            await self.session.rollback()
            return {"status": "error", "message": "Database integrity error: duplicate or invalid data"}
        except Exception as e:
            await self.session.rollback()
            return {"status": "error", "message": f"Error creating permission: {e}"}
    
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















