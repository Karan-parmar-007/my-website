from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from uuid import UUID
from typing import Dict, Any, List, Optional, cast
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload, QueryableAttribute
from sqlalchemy import func, or_
from datetime import datetime, timedelta
import logging

from app.api.routes.v1.user.models import UserRole, Permission, Users, RolePermission
from app.api.routes.v1.user.schemas import  UserAdminUpdate, UserBasicUpdate, UserRoleRead, UserRoleCreate, UserRoleUpdate
from app.api.routes.v1.user.schemas import PermissionRead, PermissionCreate, PermissionUpdate, RolePermissionRead, RolePermissionCreate
from app.api.routes.v1.user.schemas import UserRead, UserCreate, UserUpdate, UserLogin, UserDetailRead, AdminCreateUser
from app.utils.security import (
    hash_password, issue_access_token, verify_password,
    generate_otp, hash_otp, verify_otp, create_password_reset_token, verify_token
)
from app.utils.email import email_service

logger = logging.getLogger(__name__)

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

    async def create_user(self, user_create: UserCreate) -> Users:
        """
        Create a new user.
        Returns the created Users object or raises HTTPException.
        """
        try:
            # Check if user already exists by email
            query = select(Users).where(
                (Users.email == user_create.email)
            )
            result = await self.session.execute(query)
            existing = result.scalar_one_or_none()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User with this email already exists"
                )

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

            return user

        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Constraint violation creating user"
            )
        except HTTPException:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create user: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )

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
        # Password updates removed - use dedicated password reset endpoints

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
        
        # Password updates removed - use dedicated password reset endpoints

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
        query = (
            select(Users)
            .options(selectinload(Users.role))
            .order_by(Users.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        rows = result.scalars().all()
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
        Return suggestions for preferred_name/email matching query using trigram similarity.
        Returns a list of matching preferred_names and emails.
        """
        if not query or not query.strip():
            return []

        search_term = query.strip()
        # Fetch matching names
        name_stmt = (
            select(Users.preferred_name)
            .where(func.similarity(Users.preferred_name, search_term) > 0.1)
            .order_by(func.similarity(Users.preferred_name, search_term).desc())
            .limit(limit)
        )
        name_result = await self.session.execute(name_stmt)
        names = [row[0] for row in name_result.all()]

        # Fetch matching emails
        email_stmt = (
            select(Users.email)
            .where(func.similarity(Users.email, search_term) > 0.1)
            .order_by(func.similarity(Users.email, search_term).desc())
            .limit(limit)
        )
        email_result = await self.session.execute(email_stmt)
        emails = [row[0] for row in email_result.all()]

        # Merge and deduplicate, keeping order
        seen = set()
        suggestions = []
        for item in names + emails:
            if item not in seen:
                seen.add(item)
                suggestions.append(item)
        return suggestions[:limit]

    async def search_users(self, query: str, limit: int = 20, offset: int = 0) -> List[dict]:
        """
        Search users by preferred_name or email using trigram similarity.
        Returns full user details with pagination, ranked by relevance.
        """
        if not query or not query.strip():
            return []

        search_term = query.strip()
        stmt = (
            select(Users)
            .options(selectinload(Users.role))
            .where(
                or_(
                    func.similarity(Users.preferred_name, search_term) > 0.1,
                    func.similarity(Users.email, search_term) > 0.1,
                )
            )
            .order_by(
                func.greatest(
                    func.similarity(Users.preferred_name, search_term),
                    func.similarity(Users.email, search_term),
                ).desc()
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [UserDetailRead.model_validate(u).model_dump() for u in rows]

    # ----------------------------------------
    # 🔹 Password Reset Methods
    # ----------------------------------------

    async def _check_daily_password_limit(self, email: str, change_method: str, max_changes: int = 2) -> bool:
        """
        Check if user has exceeded password change limit within 24-hour window.
        
        Args:
            email: User email
            change_method: Method of password change
            max_changes: Maximum allowed changes per 24 hours (default: 2)
        
        Returns:
            True if user CAN change password (limit NOT exceeded), False otherwise
        """
        # Find existing log for this email and method
        existing_log = await self.mongo["password_change_logs"].find_one({
            "email": email,
            "change_method": change_method
        })
        
        if not existing_log:
            return True  # No previous changes, can proceed
        
        # Check if number_of_times has reached the limit
        return existing_log.get("number_of_times", 0) < max_changes
    
    async def _record_password_change(self, email: str, change_method: str) -> None:
        """
        Record a password change in MongoDB with TTL-based tracking.
        If record exists, increments number_of_times and resets expire_at to 24h from now.
        If record doesn't exist, creates new record with number_of_times=1.
        
        Args:
            email: User email
            change_method: Method of password change
        """
        try:
            # Try to find existing log
            existing_log = await self.mongo["password_change_logs"].find_one({
                "email": email,
                "change_method": change_method
            })
            
            now = datetime.utcnow()
            
            if existing_log:
                # Update existing log: increment counter and reset expiry
                await self.mongo["password_change_logs"].update_one(
                    {"email": email, "change_method": change_method},
                    {
                        "$inc": {"number_of_times": 1},
                        "$set": {
                            "expire_at": now + timedelta(hours=24),
                            "updated_at": now
                        }
                    }
                )
            else:
                # Create new log
                log_doc = {
                    "email": email,
                    "change_method": change_method,
                    "number_of_times": 1,
                    "expire_at": now + timedelta(hours=24),
                    "created_at": now,
                    "updated_at": now
                }
                await self.mongo["password_change_logs"].insert_one(log_doc)
        except Exception as e:
            logger.error(f"Failed to record password change for {email}: {e}")
            # Don't raise - this is a non-critical operation

    async def admin_reset_password(self, email: str, new_password: str) -> dict:
        """
        Admin/Super Admin resets any user's password.
        No daily limits apply to admin resets.
        
        Args:
            email: User email address
            new_password: New password
        
        Returns:
            Success/error dictionary
        """
        try:
            # Find user by email
            query = select(Users).where(Users.email == email)
            result = await self.session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                return {"status": "error", "message": "User not found"}
            
            # Update password
            user.password_hash = hash_password(new_password)
            self.session.add(user)
            await self.session.commit()
            
            # Record change (non-blocking)
            await self._record_password_change(email, "admin_reset")
            
            # Send confirmation email (non-blocking)
            try:
                email_service.send(
                    to_email=email,
                    subject="Password Reset by Administrator",
                    plain_text=f"Your password has been reset by an administrator.\n\nIf you did not request this change, please contact support immediately.",
                    html_content=f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #333;">Password Reset by Administrator</h2>
                        <p>Your password has been reset by an administrator.</p>
                        <p><strong>If you did not request this change, please contact support immediately.</strong></p>
                        <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                        <p style="color: #888; font-size: 12px;">This is an automated message, please do not reply.</p>
                    </body>
                    </html>
                    """
                )
            except Exception as e:
                logger.warning(f"Failed to send password reset confirmation email to {email}: {e}")
            
            return {
                "status": "success",
                "message": "Password reset successfully by administrator"
            }
        except Exception as e:
            await self.session.rollback()
            return {"status": "error", "message": f"Failed to reset password: {e}"}

    async def change_password(self, user_id: UUID, current_password: str, new_password: str, confirm_password: str) -> dict:
        """
        Logged-in user changes their own password.
        Requires old password verification and enforces daily limits (2 per day).
        
        Args:
            user_id: User UUID
            current_password: Current password for verification
            new_password: New password
            confirm_password: Password confirmation
        
        Returns:
            Success/error dictionary
        """
        try:
            # Validate passwords match
            if new_password != confirm_password:
                return {"status": "error", "message": "Passwords do not match"}
            
            # Fetch user
            query = select(Users).where(Users.id == user_id)
            result = await self.session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                return {"status": "error", "message": "User not found"}
            
            # Verify current password
            if not verify_password(current_password, user.password_hash):
                return {"status": "error", "message": "Current password is incorrect"}
            
            # Check daily limit (returns True if CAN change)
            can_change = await self._check_daily_password_limit(user.email, "logged_in_reset")
            if not can_change:
                return {
                    "status": "error",
                    "message": "Daily password change limit reached (2 per day). Please try again tomorrow."
                }
            
            # Update password
            user.password_hash = hash_password(new_password)
            self.session.add(user)
            await self.session.commit()
            
            # Record change
            await self._record_password_change(user.email, "logged_in_reset")
            
            # Send confirmation email
            try:
                email_service.send(
                    to_email=user.email,
                    subject="Password Changed Successfully",
                    plain_text=f"Your password has been changed successfully.\n\nIf you did not make this change, please contact support immediately.",
                    html_content=f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #333;">Password Changed Successfully</h2>
                        <p>Your password has been changed successfully.</p>
                        <p><strong>If you did not make this change, please contact support immediately.</strong></p>
                        <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                        <p style="color: #888; font-size: 12px;">This is an automated message, please do not reply.</p>
                    </body>
                    </html>
                    """
                )
            except Exception as e:
                logger.warning(f"Failed to send password change confirmation email: {e}")
            
            return {
                "status": "success",
                "message": "Password changed successfully"
            }
        except Exception as e:
            await self.session.rollback()
            return {"status": "error", "message": f"Failed to change password: {e}"}

    async def forgot_password_initiate(self, email: str) -> dict:
        """
        Initiate forgot password flow - generate OTP and send via email.
        This is the ONLY function that sends OTP (handles both initial and resend).
        Enforces rate limiting and blocking rules:
        - 30 second delay between requests
        - More than 3 send attempts result in 30 minute block
        - 2 successful password resets per 24 hours
        
        Args:
            email: User email address
        
        Returns:
            Success/error dictionary with token
        """
        try:
            # Verify user exists
            query = select(Users).where(Users.email == email)
            result = await self.session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                # Don't reveal if email exists or not for security
                # But still return success-like response to prevent enumeration
                return {
                    "status": "success",
                    "message": "If the email exists, an OTP has been sent",
                    "email": email,
                    "token": create_password_reset_token(email)  # Dummy token
                }
            
            # Check password reset limit (2 per 24 hours) - returns True if CAN proceed
            can_reset = await self._check_daily_password_limit(email, "forgot_password")
            if not can_reset:
                return {
                    "status": "error",
                    "message": "Password reset limit reached (2 per 24 hours). Please try again later."
                }
            
            collection = self.mongo["otp_verifications"]
            now = datetime.utcnow()
            
            # Check if OTP record exists
            otp_record = await collection.find_one({"email": email})
            
            if otp_record:
                # Check if blocked
                if otp_record.get("blocked") and otp_record.get("retry_time"):
                    if now < otp_record["retry_time"]:
                        remaining = int((otp_record["retry_time"] - now).total_seconds() / 60)
                        return {
                            "status": "error",
                            "message": f"Too many attempts. Please try again in {remaining} minutes."
                        }
                    else:
                        # Block time has passed, reset the record
                        await collection.delete_one({"email": email})
                        otp_record = None
                
                if otp_record:
                    # Check 30-second delay
                    last_update = otp_record.get("updated_at")
                    if last_update and (now - last_update).total_seconds() < 30:
                        wait_time = 30 - int((now - last_update).total_seconds())
                        return {
                            "status": "error",
                            "message": f"Please wait {wait_time} seconds before requesting another OTP"
                        }
                    
                    # Check if already sent more than 3 times
                    times_sent = otp_record.get("number_of_times_sent", 0)
                    if times_sent >= 3:
                        # Block for 30 minutes
                        await collection.update_one(
                            {"email": email},
                            {
                                "$set": {
                                    "blocked": True,
                                    "retry_time": now + timedelta(minutes=30),
                                    "updated_at": now
                                }
                            }
                        )
                        return {
                            "status": "error",
                            "message": "Too many OTP requests. Please try again in 30 minutes."
                        }
            
            # Generate OTP
            otp = generate_otp()
            otp_hashed = hash_otp(otp)
            expire_at = now + timedelta(minutes=5)
            
            # Send OTP email FIRST (before updating DB)
            email_sent = email_service.send(
                to_email=email,
                subject="Your Password Reset OTP",
                plain_text=f"You requested to reset your password.\n\nYour OTP is: {otp}\n\nThis OTP will expire in 5 minutes.\n\nIf you didn't request this, please ignore this email.",
                html_content=f"""
                <html>
                <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #333;">Password Reset Request</h2>
                    <p>You requested to reset your password. Use the following OTP to complete the process:</p>
                    <div style="background-color: #f4f4f4; padding: 15px; border-radius: 5px; text-align: center; margin: 20px 0;">
                        <h1 style="color: #4CAF50; letter-spacing: 5px; margin: 0;">{otp}</h1>
                    </div>
                    <p><strong>This OTP will expire in 5 minutes.</strong></p>
                    <p>If you didn't request this password reset, please ignore this email.</p>
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    <p style="color: #888; font-size: 12px;">This is an automated message, please do not reply.</p>
                </body>
                </html>
                """
            )
            
            if not email_sent:
                return {"status": "error", "message": "Failed to send OTP email. Please try again."}
            
            # Email sent successfully, now update/create OTP record
            if otp_record:
                # Increment times_sent
                new_times_sent = otp_record.get("number_of_times_sent", 0) + 1
                update_data = {
                    "otp_hash": otp_hashed,
                    "expire_at": expire_at,
                    "number_of_times_sent": new_times_sent,
                    "number_of_wrong_attempts": 0,
                    "blocked": False,
                    "retry_time": None,
                    "updated_at": now
                }
                
                # Block if this is more than 3rd send
                if new_times_sent > 3:
                    update_data["blocked"] = True
                    update_data["retry_time"] = now + timedelta(minutes=30)
                
                await collection.update_one(
                    {"email": email},
                    {"$set": update_data}
                )
            else:
                # Create new record
                await collection.insert_one({
                    "email": email,
                    "otp_hash": otp_hashed,
                    "expire_at": expire_at,
                    "number_of_times_sent": 1,
                    "number_of_wrong_attempts": 0,
                    "retry_time": None,
                    "blocked": False,
                    "created_at": now,
                    "updated_at": now
                })
            
            # Create short-lived token (5 minutes)
            token = create_password_reset_token(email)
            
            return {
                "status": "success",
                "message": "OTP sent to your email address",
                "email": email,
                "token": token
            }
        except Exception as e:
            logger.error(f"Failed to initiate forgot password for {email}: {e}")
            return {"status": "error", "message": "An error occurred. Please try again."}

    async def forgot_password_verify(self, token: str, otp: str, new_password: str) -> dict:
        """
        Verify OTP and reset password.
        
        Args:
            token: JWT token from HTTP-only cookie
            otp: 6-digit OTP from email
            new_password: New password
        
        Returns:
            Success/error dictionary
        """
        email = None
        try:
            # Verify token
            try:
                payload = verify_token(token, expected_type="password_reset")
                email = payload.get("email")
                if not email:
                    return {"status": "error", "message": "Invalid token"}
            except HTTPException as e:
                return {"status": "error", "message": str(e.detail)}
            
            # Fetch OTP record
            collection = self.mongo["otp_verifications"]
            otp_record = await collection.find_one({"email": email})
            
            if not otp_record:
                return {"status": "error", "message": "OTP not found or expired. Please request a new one."}
            
            now = datetime.utcnow()
            
            # Check if blocked
            if otp_record.get("blocked"):
                retry_time = otp_record.get("retry_time")
                if retry_time and now < retry_time:
                    remaining = int((retry_time - now).total_seconds() / 60)
                    return {"status": "error", "message": f"Account temporarily blocked. Please try again in {remaining} minutes."}
                else:
                    # Block expired, but still need valid OTP
                    pass
            
            # Check expiration
            if now > otp_record.get("expire_at"):
                await collection.delete_one({"email": email})
                return {"status": "error", "message": "OTP has expired. Please request a new one."}
            
            # Verify OTP
            if not verify_otp(otp, otp_record.get("otp_hash")):
                # Increment wrong attempts
                wrong_attempts = otp_record.get("number_of_wrong_attempts", 0) + 1
                update_data = {
                    "number_of_wrong_attempts": wrong_attempts,
                    "updated_at": now
                }
                
                # Block after 3 wrong attempts
                if wrong_attempts >= 3:
                    update_data["blocked"] = True
                    update_data["retry_time"] = now + timedelta(minutes=30)
                
                await collection.update_one(
                    {"email": email},
                    {"$set": update_data}
                )
                
                if wrong_attempts >= 3:
                    return {"status": "error", "message": "Too many incorrect attempts. Please try again in 30 minutes."}
                
                return {"status": "error", "message": f"Invalid OTP. {3 - wrong_attempts} attempts remaining."}
            
            # OTP is valid - Update password
            query = select(Users).where(Users.email == email)
            result = await self.session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                return {"status": "error", "message": "User not found"}
            
            user.password_hash = hash_password(new_password)
            self.session.add(user)
            await self.session.commit()
            
            # Record password change for daily limit tracking
            await self._record_password_change(email, "forgot_password")
            
            # Delete OTP verification record
            await collection.delete_one({"email": email})
            
            # Send confirmation email
            try:
                email_service.send(
                    to_email=email,
                    subject="Password Reset Successful",
                    plain_text=f"Your password has been successfully reset.\n\nIf you did not make this change, please contact support immediately.",
                    html_content=f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #333;">Password Reset Successful</h2>
                        <div style="background-color: #d4edda; border: 2px solid #28a745; border-radius: 5px; padding: 20px; margin: 20px 0;">
                            <p style="margin: 0;"><strong>✓ Your password has been successfully reset.</strong></p>
                        </div>
                        <p>If you did not make this change, please contact support immediately.</p>
                        <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                        <p style="color: #888; font-size: 12px;">This is an automated message, please do not reply.</p>
                    </body>
                    </html>
                    """
                )
            except Exception as e:
                logger.warning(f"Failed to send password reset confirmation email to {email}: {e}")
            
            return {
                "status": "success",
                "message": "Password reset successfully. You can now login with your new password."
            }
        except Exception as e:
            logger.error(f"Failed to verify OTP for {email}: {e}")
            await self.session.rollback()
            return {"status": "error", "message": "Failed to reset password. Please try again."}

    async def resend_otp(self, email: str) -> dict:
        """
        Resend OTP for forgot password flow.
        This method just calls forgot_password_initiate since the logic is the same.
        
        Args:
            email: User email address
        
        Returns:
            Success/error dictionary
        """
        return await self.forgot_password_initiate(email)










