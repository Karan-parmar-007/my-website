from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from uuid import UUID
from bson import ObjectId
import base64
from typing import List, Optional
from app.api.routes.v1.project.schemas import ProjectRead, ProjectCreate, ProjectUpdate, ProjectAdminRead
from app.utils.gridfs_utils import upload_to_gridfs, delete_from_gridfs, get_gridfs_bucket
from app.api.routes.v1.project.models import Projects, AccessLevel
from app.api.routes.v1.project.schemas import AccessLevelRead, AccessLevelCreate, AccessLevelUpdate


# ----------------------------------------
# 🔹 access level
# ----------------------------------------
class ProjectAccessLevelService:

    def __init__(self, session: AsyncSession, mongo: AsyncIOMotorDatabase):
        self.session = session
        self.mongo = mongo

        self.project_bucket = get_gridfs_bucket(mongo, "project_files")


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
# 🔹 Project
# ----------------------------------------

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
    
    