from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from uuid import UUID
from bson import ObjectId
import base64
from typing import List, Optional

from app.common.models import AccessLevel, UserRole, Permission, Users, Projects, RolePermission, ProjectMembership
from app.common.schemas import AccessLevelRead, AccessLevelCreate, AccessLevelUpdate
from app.common.schemas import  UserRoleRead, UserRoleCreate, UserRoleUpdate
from app.common.schemas import PermissionRead, PermissionCreate, PermissionUpdate, RolePermissionRead, RolePermissionCreate
from app.common.schemas import UserRead, UserCreate, UserUpdate, UserLogin, LoginResponse, ForgetPasswordRequest, ResetPasswordRequest, ChangePasswordRequest, TokenResponse
from app.common.schemas import ProjectMembershipRead, ProjectMembershipCreate
from app.common.schemas import ProjectRead, ProjectCreate, ProjectUpdate, ProjectAdminRead
from app.utils.gridfs_utils import upload_to_gridfs, delete_from_gridfs, get_gridfs_bucket


class UserService:
    def __init__(self, session: AsyncSession, mongo: AsyncIOMotorDatabase):
        self.session = session
        self.mongo = mongo

        # Use get_gridfs_bucket utility function instead of direct instantiation
        self.profile_bucket = get_gridfs_bucket(mongo, "profile_files")
        self.resume_bucket = get_gridfs_bucket(mongo, "resume_files")
        self.skill_bucket = get_gridfs_bucket(mongo, "skill_files")

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
# 🔹 access level
# ----------------------------------------

    async def get_access_levels(self) -> List[dict]:
        query = select(AccessLevel)
        result = await self.session.execute(query)
        access_levels = result.scalars().all()
        return [AccessLevelRead.model_validate(al).model_dump() for al in access_levels]

    async def get_access_level_by_id(self, access_level_id: UUID) -> Optional[dict]:
        query = select(AccessLevel).where(AccessLevel.id == access_level_id)
        result = await self.session.execute(query)
        access_level = result.scalar_one_or_none()
        if not access_level:
            return None
        return AccessLevelRead.model_validate(access_level).model_dump()

    async def create_access_level(self, access_level_create: AccessLevelCreate) -> dict:
        access_level = AccessLevel.model_validate(access_level_create)
        self.session.add(access_level)
        await self.session.commit()
        await self.session.refresh(access_level)
        return AccessLevelRead.model_validate(access_level).model_dump()

    async def update_access_level(self, access_level_id: UUID, access_level_update: AccessLevelUpdate) -> Optional[dict]:
        query = select(AccessLevel).where(AccessLevel.id == access_level_id)
        result = await self.session.execute(query)
        access_level = result.scalar_one_or_none()
        if not access_level:
            return None

        access_level_data = access_level_update.model_dump(exclude_unset=True)
        for key, value in access_level_data.items():
            setattr(access_level, key, value)

        self.session.add(access_level)
        await self.session.commit()
        await self.session.refresh(access_level)
        return AccessLevelRead.model_validate(access_level).model_dump() 

    async def delete_access_level(self, access_level_id: UUID) -> bool:
        query = select(AccessLevel).where(AccessLevel.id == access_level_id)
        result = await self.session.execute(query)
        access_level = result.scalar_one_or_none()
        if not access_level:
            return False

        await self.session.delete(access_level)
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
    
# ----------------------------------------
# 🔹 Project Membershi
# ----------------------------------------

    async def get_project_memberships(self) -> List[dict]:
        query = select(ProjectMembership)
        result = await self.session.execute(query)
        memberships = result.scalars().all()
        return [ProjectMembershipRead.model_validate(pm).model_dump() for pm in memberships]
    
    async def get_project_membership_by_id(self, user_id: UUID, project_id: UUID) -> Optional[dict]:
        query = select(ProjectMembership).where(
            ProjectMembership.user_id == user_id,
            ProjectMembership.project_id == project_id
        )
        result = await self.session.execute(query)
        membership = result.scalar_one_or_none()
        if not membership:
            return None
        return ProjectMembershipRead.model_validate(membership).model_dump()
    
    async def get_project_memberships_by_user_id(self, user_id: UUID) -> List[dict]:
        query = select(ProjectMembership).where(ProjectMembership.user_id == user_id)
        result = await self.session.execute(query)
        memberships = result.scalars().all()
        return [ProjectMembershipRead.model_validate(pm).model_dump() for pm in memberships]
    
    async def get_project_memberships_by_project_id(self, project_id: UUID) -> List[dict]:
        query = select(ProjectMembership).where(ProjectMembership.project_id == project_id)
        result = await self.session.execute(query)
        memberships = result.scalars().all()
        return [ProjectMembershipRead.model_validate(pm).model_dump() for pm in memberships]
    
    async def create_project_membership(self, project_membership_create: ProjectMembershipCreate) -> dict:
        membership = ProjectMembership.model_validate(project_membership_create)
        self.session.add(membership)
        await self.session.commit()
        await self.session.refresh(membership)
        return ProjectMembershipRead.model_validate(membership).model_dump()
    
    async def delete_project_membership(self, user_id: UUID, project_id: UUID) -> bool:
        query = select(ProjectMembership).where(
            ProjectMembership.user_id == user_id,
            ProjectMembership.project_id == project_id
        )
        result = await self.session.execute(query)
        membership = result.scalar_one_or_none()
        if not membership:
            return False

        await self.session.delete(membership)
        await self.session.commit()
        return True


# ----------------------------------------
# 🔹 Project
# ----------------------------------------


class ProjectService:
    def __init__(self, session: AsyncSession, mongo: AsyncIOMotorDatabase):
        self.session = session
        self.mongo = mongo

        # Use get_gridfs_bucket utility function instead of direct instantiation
        self.project_bucket = get_gridfs_bucket(mongo, "project_files")

    async def get_projects(self) -> List[dict]:
        query = select(Projects)
        result = await self.session.execute(query)
        projects = result.scalars().all()
        
        project_list = []
        for project in projects:
            # Convert project to dict using Pydantic model
            project_dict = ProjectRead.model_validate(project).model_dump()
            
            # If project has an image_id, fetch and convert to base64
            if project.project_image_id:
                try:
                    stream = await self.project_bucket.open_download_stream(ObjectId(project.project_image_id))
                    content: bytes = await stream.read()
                    project_dict["project_image_base_six_four"] = base64.b64encode(content).decode("utf-8")
                except Exception:
                    project_dict["project_image_base_six_four"] = None
            
            project_list.append(project_dict)
        
        return project_list

    async def get_project_by_id(self, project_id: UUID) -> Optional[dict]:
        query = select(Projects).where(Projects.id == project_id)
        result = await self.session.execute(query)
        project = result.scalar_one_or_none()
        if not project:
            return None

        project_dict = ProjectRead.model_validate(project).model_dump()
        
        # If project has an image_id, fetch and convert to base64
        if project.project_image_id:
            try:
                stream = await self.project_bucket.open_download_stream(ObjectId(project.project_image_id))
                content: bytes = await stream.read()
                project_dict["project_image_base_six_four"] = base64.b64encode(content).decode("utf-8")
            except Exception:
                project_dict["project_image_base_six_four"] = None
        
        return project_dict
    
    async def get_project_admin(self) -> List[dict]:
        query = select(Projects)
        result = await self.session.execute(query)
        projects = result.scalars().all()
        
        project_list = []
        for project in projects:
            # Convert project to dict using Pydantic model
            project_dict = ProjectAdminRead.model_validate(project).model_dump()
            
            # If project has an image_id, fetch and convert to base64
            if project.project_image_id:
                try:
                    stream = await self.project_bucket.open_download_stream(ObjectId(project.project_image_id))
                    content: bytes = await stream.read()
                    project_dict["project_image_base_six_four"] = base64.b64encode(content).decode("utf-8")
                except Exception:
                    project_dict["project_image_base_six_four"] = None
            
            project_list.append(project_dict)
        
        return project_list
    
    async def get_project_admin_by_id(self, project_id: UUID) -> Optional[dict]:
        query = select(Projects).where(Projects.id == project_id)
        result = await self.session.execute(query)
        project = result.scalar_one_or_none()
        if not project:
            return None

        project_dict = ProjectAdminRead.model_validate(project).model_dump()
        
        # If project has an image_id, fetch and convert to base64
        if project.project_image_id:
            try:
                stream = await self.project_bucket.open_download_stream(ObjectId(project.project_image_id))
                content: bytes = await stream.read()
                project_dict["project_image_base_six_four"] = base64.b64encode(content).decode("utf-8")
            except Exception:
                project_dict["project_image_base_six_four"] = None
        
        return project_dict
    
    async def create_project(self, project_create: ProjectCreate, project_image: Optional[UploadFile] = None) -> dict:
        project = Projects.model_validate(project_create)
        
        # Handle project image upload if provided
        if project_image:
            try:
                image_id = await upload_to_gridfs(self.project_bucket, project_image)
                project.project_image_id = image_id
            except Exception:
                project.project_image_id = None
        
        self.session.add(project)
        await self.session.commit()
        await self.session.refresh(project)
        
        project_dict = ProjectRead.model_validate(project).model_dump()
        
        # If project has an image_id, fetch and convert to base64
        if project.project_image_id:
            try:
                stream = await self.project_bucket.open_download_stream(ObjectId(project.project_image_id))
                content: bytes = await stream.read()
                project_dict["project_image_base_six_four"] = base64.b64encode(content).decode("utf-8")
            except Exception:
                project_dict["project_image_base_six_four"] = None
        
        return project_dict

    async def update_project(self, project_id: UUID, project_update: ProjectUpdate, project_image: Optional[UploadFile] = None) -> Optional[dict]:
        query = select(Projects).where(Projects.id == project_id)
        result = await self.session.execute(query)
        project = result.scalar_one_or_none()
        if not project:
            return None

        project_data = project_update.model_dump(exclude_unset=True)
        for key, value in project_data.items():
            setattr(project, key, value)
        
        # Handle project image upload if provided
        if project_image:
            # Delete old image if exists
            if project.project_image_id:
                try:
                    await delete_from_gridfs(self.project_bucket, project.project_image_id)
                except Exception:
                    pass  # Optionally log the error
            
            # Upload new image
            try:
                image_id = await upload_to_gridfs(self.project_bucket, project_image)
                project.project_image_id = image_id
            except Exception:
                project.project_image_id = None

        self.session.add(project)
        await self.session.commit()
        await self.session.refresh(project)
        
        project_dict = ProjectRead.model_validate(project).model_dump()
        
        # If project has an image_id, fetch and convert to base64
        if project.project_image_id:
            try:
                stream = await self.project_bucket.open_download_stream(ObjectId(project.project_image_id))
                content: bytes = await stream.read()
                project_dict["project_image_base_six_four"] = base64.b64encode(content).decode("utf-8")
            except Exception:
                project_dict["project_image_base_six_four"] = None
        
        return project_dict
    
    async def delete_project(self, project_id: UUID) -> bool:
        query = select(Projects).where(Projects.id == project_id)
        result = await self.session.execute(query)
        project = result.scalar_one_or_none()
        if not project:
            return False

        # Delete project image from GridFS if exists
        if project.project_image_id:
            try:
                await delete_from_gridfs(self.project_bucket, project.project_image_id)
            except Exception:
                pass  # Optionally log the error

        await self.session.delete(project)
        await self.session.commit()
        return True
    
    










