from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from uuid import UUID
from typing import Dict, Any, List, Optional, Any, cast
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload, QueryableAttribute

from app.api.routes.v1.user.models import UserRole, Permission, Users, RolePermission
from app.api.routes.v1.user.schemas import  UserAdminUpdate, UserBasicUpdate, UserRoleRead, UserRoleCreate, UserRoleUpdate
from app.api.routes.v1.user.schemas import PermissionRead, PermissionCreate, PermissionUpdate, RolePermissionRead, RolePermissionCreate
from app.api.routes.v1.user.schemas import UserRead, UserCreate, UserUpdate, UserLogin, UserDetailRead, AdminCreateUser
from app.utils.security import hash_password, issue_access_token, verify_password

# New import for repository
from app.api.routes.v1.user.repository import UserRepository

class UserService:
    def __init__(self, session: AsyncSession, mongo: AsyncIOMotorDatabase):
        self.session = session
        self.mongo = mongo
        self._repo = UserRepository(session)


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
    
    async def update_user_basic(self, user_id: UUID, user_update: "UserBasicUpdate") -> Optional[dict]:
        """Update only name and email for regular users"""
        query = select(Users).where(Users.id == user_id)
        result = await self.session.execute(query)
        user = result.scalar_one_or_none()
        if not user:
            return None

        # Only allow preferred_name and email updates
        data = user_update.model_dump(exclude_unset=True)
        for key, value in data.items():
            if key in ["preferred_name", "email"]:
                setattr(user, key, value)

        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return UserRead.model_validate(user).model_dump()

    async def update_user_admin(self, user_id: UUID, user_update: "UserAdminUpdate") -> Optional[dict]:
        """Admin update - can change all fields including role and verification status"""
        query = select(Users).where(Users.id == user_id)
        result = await self.session.execute(query)
        user = result.scalar_one_or_none()
        if not user:
            return None

        data = user_update.model_dump(exclude_unset=True)
        
        # Handle password separately
        if "password" in data:
            user.password_hash = hash_password(data.pop("password"))

        # Verify role_id exists if provided
        if "role_id" in data:
            role_query = select(UserRole).where(UserRole.id == data["role_id"])
            role_result = await self.session.execute(role_query)
            if not role_result.scalar_one_or_none():
                return None  # Invalid role_id

        for key, value in data.items():
            setattr(user, key, value)

        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return UserRead.model_validate(user).model_dump()

    async def update_user_role_only(self, user_id: UUID, role_id: UUID) -> Optional[dict]:
        """Update only the user's role"""
        # Verify role exists
        role_query = select(UserRole).where(UserRole.id == role_id)
        role_result = await self.session.execute(role_query)
        if not role_result.scalar_one_or_none():
            return None  # Invalid role_id

        # Get and update user
        query = select(Users).where(Users.id == user_id)
        result = await self.session.execute(query)
        user = result.scalar_one_or_none()
        if not user:
            return None

        user.role_id = role_id
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

    async def get_all_users(self, limit: int = 20, offset: int = 0) -> List[dict]:
        """
        Return list of users paginated with full details (without password_hash).
        """
        rows = await self._repo.fetch_users(limit=limit, offset=offset)
        # convert to schema dicts
        return [UserDetailRead.model_validate(u).model_dump() for u in rows]

    async def user_has_role(self, user_id: str, required_role: str) -> bool:
        """
        Returns True if the user with user_id has the required_role.
        """
        from uuid import UUID
        try:
            user_uuid = UUID(user_id)
        except Exception:
            return False

        # Fetch user and role using session
        q_user = select(Users).where(Users.id == user_uuid)
        res = await self.session.execute(q_user)
        user = res.scalar_one_or_none()
        if not user or getattr(user, "role_id", None) is None:
            return False

        q_role = select(UserRole).where(UserRole.id == user.role_id)
        res = await self.session.execute(q_role)
        role = res.scalar_one_or_none()
        if not role:
            return False

        return getattr(role, "name", None) == required_role

    async def user_has_any_role(self, user_id: str, required_roles: list[str]) -> bool:
        """
        Returns True if the user with user_id has any of the required_roles.
        """
        from uuid import UUID
        try:
            user_uuid = UUID(user_id)
        except Exception:
            return False

        q_user = select(Users).where(Users.id == user_uuid)
        res = await self.session.execute(q_user)
        user = res.scalar_one_or_none()
        if not user or getattr(user, "role_id", None) is None:
            return False

        q_role = select(UserRole).where(UserRole.id == user.role_id)
        res = await self.session.execute(q_role)
        role = res.scalar_one_or_none()
        if not role:
            return False

        return getattr(role, "name", None) in required_roles

    async def get_role_permissions_by_role_id(self, role_id: UUID) -> Dict[str, Any]:
        # Fetch the role
        role = await self.session.get(UserRole, role_id)
        if not role:
            raise ValueError("Role not found")
        
        # Fetch all permissions
        all_permissions_result = await self.session.execute(select(Permission))
        all_permissions = all_permissions_result.scalars().all()
        
        # Fetch permissions assigned to this role
        role_permissions_result = await self.session.execute(
            select(RolePermission).where(RolePermission.role_id == role_id)
        )
        role_permission_ids = {rp.permission_id for rp in role_permissions_result.scalars().all()}
        
        # Build the permissions list
        permissions = []
        for perm in all_permissions:
            have = perm.id in role_permission_ids
            permissions.append({
                "permission": perm.model_dump() if hasattr(perm, "model_dump") else perm.__dict__,
                "have": have
            })
        
        return {
            "role_info": role.model_dump() if hasattr(role, "model_dump") else role.__dict__,
            "permissions": permissions
        }

    async def create_user_by_admin(self, admin_user: AdminCreateUser) -> dict:
        """
        Create a user from an admin context.
        - Hashes the password and stores user.
        - Does NOT issue tokens or set cookies.
        - If role_id provided, verifies it exists; otherwise assigns default 'user' role.
        Returns created user as UserDetailRead dict or raises/returns error dict.
        """
        try:
            # check duplicate email
            q = select(Users).where(Users.email == admin_user.email)
            res = await self.session.execute(q)
            existing = res.scalar_one_or_none()
            if existing:
                return {"status": "error", "message": "User with this email already exists"}

            # determine role
            role_obj = None
            if admin_user.role_id:
                q_role = select(UserRole).where(UserRole.id == admin_user.role_id)
                res_role = await self.session.execute(q_role)
                role_obj = res_role.scalar_one_or_none()
                if not role_obj:
                    return {"status": "error", "message": "Provided role_id does not exist"}
            else:
                role_obj = await self._get_or_create_default_role()

            user = Users(
                preferred_name=admin_user.preferred_name,
                email=admin_user.email,
                password_hash=hash_password(admin_user.password),
                role_id=role_obj.id,
                email_verified=bool(admin_user.email_verified),
            )
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)

            return {"status": "success", "user": UserDetailRead.model_validate(user).model_dump()}
        except IntegrityError:
            await self.session.rollback()
            return {"status": "error", "message": "Constraint violation creating user"}
        except Exception as e:
            await self.session.rollback()
            return {"status": "error", "message": f"Failed to create user: {e}"}

    async def fetch_user_suggestions(self, query: str, limit: int = 5) -> List[str]:
        """
        Return suggestions for preferred_name/email matching query.
        Delegates to repository which uses ilike and .limit().
        """
        if not query or not query.strip():
            return []
        suggestions = await self._repo.fetch_user_suggestions(query=query.strip(), limit=limit)
        return suggestions

    async def search_users(self, query: str, limit: int = 20, offset: int = 0) -> List[dict]:
        """
        Search users by preferred_name or email and return full user details with pagination.
        Delegates to repository which uses ilike, .limit() and .offset().
        """
        if not query or not query.strip():
            return []
        rows = await self._repo.search_users(query=query.strip(), limit=limit, offset=offset)
        return [UserDetailRead.model_validate(u).model_dump() for u in rows]










