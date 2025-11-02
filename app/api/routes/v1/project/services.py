from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
from fastapi import UploadFile, HTTPException
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
from app.api.routes.v1.project.repository import ProjectRepository
from sqlalchemy.orm import selectinload  # Add this import
from app.api.routes.v1.user.schemas import UserDetailRead

class ProjectAccessLevelService:

    def __init__(self, session: AsyncSession, mongo: AsyncIOMotorDatabase):
        self.session = session
        self.mongo = mongo
        self.project_bucket = get_gridfs_bucket(mongo, "project_files")
        self._repo = ProjectRepository(session)

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
        access_level = AccessLevel(**access_level_create.model_dump())
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
        query = select(Projects).options(selectinload(getattr(Projects, "access_level"))).where(Projects.is_live)
        result = await self.session.execute(query)
        projects = result.scalars().all()
        
        project_list = []
        for project in projects:
            project_dict = ProjectRead.model_validate(project).model_dump()
            
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
        query = select(Projects).options(selectinload(getattr(Projects, "access_level"))).where(Projects.id == project_id)
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
    
    async def get_project_admin(self, limit: int = 20, offset: int = 0) -> List[dict]:
        """
        Fetch all projects with full admin details using pagination.
        """
        rows = await self._repo.fetch_projects(limit=limit, offset=offset)
        
        project_list = []
        for project in rows:
            project_dict = ProjectAdminRead.model_validate(project).model_dump()
            
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
        query = select(Projects).options(selectinload(getattr(Projects, "access_level"))).where(Projects.id == project_id)
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
        # Check if a project with the same name already exists
        query = select(Projects).where(Projects.name == project_create.name)
        result = await self.session.execute(query)
        existing_project = result.scalar_one_or_none()
        if existing_project:
            raise HTTPException(status_code=409, detail="A project with this name already exists.")
        
        # Build Projects instance from the create schema dict so SQLModel can set defaults
        project = Projects(**project_create.model_dump())
        
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
        
        # ensure access_level relationship is loaded for Pydantic validation
        query = select(Projects).options(selectinload(getattr(Projects, "access_level"))).where(Projects.id == project.id)
        result = await self.session.execute(query)
        project = result.scalar_one()
        
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

        # Only apply fields that were actually provided and are not None.
        # This avoids overwriting existing values with nulls (e.g. access_level_id).
        project_data = project_update.model_dump(exclude_unset=True, exclude_none=True)
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

        # Re-query with selectinload to ensure relationships (access_level) are loaded
        query = select(Projects).options(selectinload(getattr(Projects, "access_level"))).where(Projects.id == project.id)
        result = await self.session.execute(query)
        project = result.scalar_one()
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

    async def fetch_project_suggestions(self, query: str, limit: int = 5) -> List[str]:
        """
        Return suggestions for project names matching query.
        """
        if not query or not query.strip():
            return []
        suggestions = await self._repo.fetch_project_suggestions(query=query.strip(), limit=limit)
        return suggestions

    async def search_projects(self, query: str, limit: int = 20, offset: int = 0) -> List[dict]:
        """
        Search projects by name and return full project details with pagination.
        """
        if not query or not query.strip():
            return []
        rows = await self._repo.search_projects(query=query.strip(), limit=limit, offset=offset)
        # repository should return Projects with access_level eagerly loaded, but guard here if plain instances are returned
        # If your repo returns a plain list of Projects without options, consider adding selectinload there as well.
        
        project_list = []
        for project in rows:
            project_dict = ProjectAdminRead.model_validate(project).model_dump()
            
            if project.project_image_id:
                try:
                    stream = await self.project_bucket.open_download_stream(ObjectId(project.project_image_id))
                    content: bytes = await stream.read()
                    project_dict["project_image_base_six_four"] = base64.b64encode(content).decode("utf-8")
                except Exception:
                    project_dict["project_image_base_six_four"] = None
            
            project_list.append(project_dict)
        
        return project_list

    async def get_projects_paginated(self, limit: int = 20, offset: int = 0) -> List[dict]:
        """
        Return projects paginated (no is_live filter). Ordered by created_at desc.
        """
        query = select(Projects).options(selectinload(getattr(Projects, "access_level"))).order_by(Projects.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        projects = result.scalars().all()
        
        project_list = []
        for project in projects:
            project_dict = ProjectRead.model_validate(project).model_dump()
            
            if project.project_image_id:
                try:
                    stream = await self.project_bucket.open_download_stream(ObjectId(project.project_image_id))
                    content: bytes = await stream.read()
                    project_dict["project_image_base_six_four"] = base64.b64encode(content).decode("utf-8")
                except Exception:
                    project_dict["project_image_base_six_four"] = None
            
            project_list.append(project_dict)
        
        return project_list

    async def get_latest_non_interesting(self, limit: int = 6) -> List[dict]:
        """
        Latest projects where is_interesting_project == False (top `limit`).
        """
        query = select(Projects).options(selectinload(getattr(Projects, "access_level"))).where(Projects.is_interesting_project == False).order_by(Projects.created_at.desc()).limit(limit)
        result = await self.session.execute(query)
        projects = result.scalars().all()

        project_list = []
        for project in projects:
            project_dict = ProjectRead.model_validate(project).model_dump()
            if project.project_image_id:
                try:
                    stream = await self.project_bucket.open_download_stream(ObjectId(project.project_image_id))
                    content: bytes = await stream.read()
                    project_dict["project_image_base_six_four"] = base64.b64encode(content).decode("utf-8")
                except Exception:
                    project_dict["project_image_base_six_four"] = None
            project_list.append(project_dict)
        return project_list

    async def get_featured_projects(self, limit: int = 4) -> List[dict]:
        """
        Latest featured projects (is_interesting_project == True), limited.
        """
        query = select(Projects).options(selectinload(getattr(Projects, "access_level"))).where(Projects.is_interesting_project == True).order_by(Projects.created_at.desc()).limit(limit)
        result = await self.session.execute(query)
        projects = result.scalars().all()

        project_list = []
        for project in projects:
            project_dict = ProjectRead.model_validate(project).model_dump()
            if project.project_image_id:
                try:
                    stream = await self.project_bucket.open_download_stream(ObjectId(project.project_image_id))
                    content: bytes = await stream.read()
                    project_dict["project_image_base_six_four"] = base64.b64encode(content).decode("utf-8")
                except Exception:
                    project_dict["project_image_base_six_four"] = None
            project_list.append(project_dict)
        return project_list

    async def search_users_in_project(self, project_id: UUID, query: str, limit: int = 20) -> List[dict]:
        """
        Search users within a project by name or email.
        Returns user details with membership info.
        """
        if not query or not query.strip():
            return []
        
        rows = await self._repo.search_users_in_project(
            project_id=project_id,
            query=query.strip(),
            limit=limit
        )
        
        user_list = []
        for user, membership in rows:
            user_dict = UserDetailRead.model_validate(user).model_dump()
            user_dict["membership"] = {
                "user_id": membership.user_id,
                "project_id": membership.project_id
            }
            user_list.append(user_dict)
        
        return user_list

