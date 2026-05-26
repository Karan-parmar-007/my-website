from pymongo.asynchronous.database import AsyncDatabase
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text, delete, or_
from sqlalchemy.orm import selectinload
from uuid import UUID
from bson import ObjectId
import base64
from typing import List, Optional

from app.api.routes.v1.project.schemas import (
    ProjectRead, ProjectCreate, ProjectUpdate,
    AccessLevelRead, AccessLevelCreate, AccessLevelUpdate,
    PaginatedProjectResponse,
)
from app.api.routes.v1.portfolio.schemas import SkillRead
from app.utils.gridfs_utils import upload_to_gridfs, delete_from_gridfs, get_gridfs_bucket
from app.api.routes.v1.project.models import Projects, AccessLevel
from app.api.routes.v1.portfolio.models import Skill
from app.common.models.project_skill_link import ProjectSkill
from app.api.routes.v1.user.schemas import UserDetailRead
from app.api.routes.v1.user.models import Users
from app.common.models.user_project_link import ProjectMembership


class ProjectAccessLevelService:

    def __init__(self, session: AsyncSession, mongo: AsyncDatabase):
        self.session = session
        self.mongo = mongo
        self.project_bucket = get_gridfs_bucket(mongo, "project_files")

    # ----------------------------------------
    # 🔹 Helpers
    # ----------------------------------------

    async def _load_project_image(self, project_dict: dict, project_image_id: Optional[str]) -> dict:
        """Load project image from GridFS and add base64 to dict."""
        if project_image_id:
            try:
                stream = await self.project_bucket.open_download_stream(ObjectId(project_image_id))
                content: bytes = await stream.read()
                project_dict["project_image_base_six_four"] = base64.b64encode(content).decode("utf-8")
            except Exception:
                project_dict["project_image_base_six_four"] = None
        return project_dict

    async def _build_project_read(self, project: Projects) -> dict:
        """Convert a Projects ORM instance to a ProjectRead dict with skills and image."""
        # Build skill list from project_skills relationship
        skills = []
        for ps in project.project_skills:
            skill = ps.skill
            skill_dict = SkillRead(
                id=skill.id,
                name=skill.name,
                category_id=skill.category_id,
                category_name=skill.category_obj.name if skill.category_obj else None,
            ).model_dump()
            # Load skill image
            if skill.image_id:
                try:
                    skill_bucket = get_gridfs_bucket(self.mongo, "skill_files")
                    stream = await skill_bucket.open_download_stream(ObjectId(skill.image_id))
                    content = await stream.read()
                    skill_dict["image_base64"] = base64.b64encode(content).decode("utf-8")
                except Exception:
                    skill_dict["image_base64"] = None
            skills.append(skill_dict)

        project_dict = ProjectRead.model_validate(project).model_dump()
        project_dict["skills"] = skills
        return await self._load_project_image(project_dict, project.project_image_id)



    def _eager_project_options(self):
        """Common selectinload options for Projects queries."""
        return [
            selectinload(Projects.access_level),
            selectinload(Projects.project_skills).selectinload(ProjectSkill.skill).selectinload(Skill.category_obj),
        ]

    async def _sync_project_skills(self, project_id: UUID, skill_ids: list[UUID]) -> None:
        """Sync the project_skill M2M rows for a project. Validates all skill_ids exist."""
        if not skill_ids:
            # Clear all skill links
            await self.session.execute(
                delete(ProjectSkill).where(ProjectSkill.project_id == project_id)
            )
            return

        # Validate all skill_ids exist
        result = await self.session.execute(
            select(Skill.id).where(Skill.id.in_(skill_ids))
        )
        found_ids = set(result.scalars().all())
        missing = set(skill_ids) - found_ids
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid skill IDs: {[str(m) for m in missing]}"
            )

        # Delete existing links
        await self.session.execute(
            delete(ProjectSkill).where(ProjectSkill.project_id == project_id)
        )

        # Insert new links
        for sid in skill_ids:
            self.session.add(ProjectSkill(project_id=project_id, skill_id=sid))

    # ----------------------------------------
    # 🔹 Access Level
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
    # 🔹 Project CRUD
    # ----------------------------------------

    async def get_projects(self) -> List[dict]:
        query = (
            select(Projects)
            .options(*self._eager_project_options())
            .where(Projects.is_live)
        )
        result = await self.session.execute(query)
        projects = result.scalars().all()
        return [await self._build_project_read(p) for p in projects]

    async def get_project_by_id(self, project_id: UUID) -> Optional[dict]:
        query = (
            select(Projects)
            .options(*self._eager_project_options())
            .where(Projects.id == project_id)
        )
        result = await self.session.execute(query)
        project = result.scalar_one_or_none()
        if not project:
            return None
        return await self._build_project_read(project)



    async def create_project(self, project_create: ProjectCreate, project_image: Optional[UploadFile] = None) -> dict:
        # Check if a project with the same name already exists
        query = select(Projects).where(Projects.name == project_create.name)
        result = await self.session.execute(query)
        existing_project = result.scalar_one_or_none()
        if existing_project:
            raise HTTPException(status_code=409, detail="A project with this name already exists.")

        # Extract skill_ids before building Projects instance
        skill_ids = project_create.skill_ids
        project_data = project_create.model_dump(exclude={"skill_ids"})
        project = Projects(**project_data)

        # Handle project image upload if provided
        if project_image:
            try:
                image_id = await upload_to_gridfs(self.project_bucket, project_image)
                project.project_image_id = image_id
            except Exception:
                project.project_image_id = None

        self.session.add(project)
        await self.session.flush()  # Get the project.id before syncing skills

        # Sync skills
        if skill_ids:
            await self._sync_project_skills(project.id, skill_ids)

        await self.session.commit()
        await self.session.refresh(project)

        # Re-query with eager loading
        query = (
            select(Projects)
            .options(*self._eager_project_options())
            .where(Projects.id == project.id)
        )
        result = await self.session.execute(query)
        project = result.scalar_one()
        return await self._build_project_read(project)

    async def update_project(self, project_id: UUID, project_update: ProjectUpdate, project_image: Optional[UploadFile] = None) -> Optional[dict]:
        query = select(Projects).where(Projects.id == project_id)
        result = await self.session.execute(query)
        project = result.scalar_one_or_none()
        if not project:
            return None

        # Extract skill_ids separately
        skill_ids = project_update.skill_ids
        project_data = project_update.model_dump(exclude_unset=True, exclude_none=True, exclude={"skill_ids"})
        for key, value in project_data.items():
            setattr(project, key, value)

        # Handle project image upload if provided
        if project_image:
            if project.project_image_id:
                try:
                    await delete_from_gridfs(self.project_bucket, project.project_image_id)
                except Exception:
                    pass
            try:
                image_id = await upload_to_gridfs(self.project_bucket, project_image)
                project.project_image_id = image_id
            except Exception:
                project.project_image_id = None

        self.session.add(project)

        # Sync skills if provided
        if skill_ids is not None:
            await self._sync_project_skills(project_id, skill_ids)

        await self.session.commit()
        await self.session.refresh(project)

        # Re-query with eager loading
        query = (
            select(Projects)
            .options(*self._eager_project_options())
            .where(Projects.id == project.id)
        )
        result = await self.session.execute(query)
        project = result.scalar_one()
        return await self._build_project_read(project)

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
                pass

        await self.session.delete(project)
        await self.session.commit()
        return True

    # ----------------------------------------
    # 🔹 Project Search (FTS + Filters + Pagination)
    # ----------------------------------------

    async def search_projects_fts(
        self,
        query_str: Optional[str] = None,
        skill_ids: Optional[list[UUID]] = None,
        sort_by_date: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> dict:
        """
        Full-text search on projects with optional filters and pagination.
        
        Args:
            query_str: FTS query string (searches name, short_description, long_description, skill names)
            skill_ids: Filter by skills - ALL specified skills must be present
            sort_by_date: "asc" or "desc" for created_at ordering. If None, sorts by relevance (when query_str provided)
            page: Page number (1-indexed)
            size: Page size
        """
        offset = (page - 1) * size
        stmt = select(Projects).options(*self._eager_project_options())
        count_stmt = select(func.count(Projects.id))

        # FTS filter
        if query_str and query_str.strip():
            ts_query = func.plainto_tsquery('english', query_str.strip())
            stmt = stmt.where(Projects.search_vector.op('@@')(ts_query))
            count_stmt = count_stmt.where(Projects.search_vector.op('@@')(ts_query))

        # Skills filter: all provided skill_ids must be present
        if skill_ids:
            for sid in skill_ids:
                skill_subq = (
                    select(ProjectSkill.project_id)
                    .where(
                        ProjectSkill.skill_id == sid,
                    )
                )
                stmt = stmt.where(Projects.id.in_(skill_subq))
                count_stmt = count_stmt.where(Projects.id.in_(skill_subq))

        # Sorting
        if sort_by_date == "asc":
            stmt = stmt.order_by(Projects.created_at.asc())
        elif sort_by_date == "desc":
            stmt = stmt.order_by(Projects.created_at.desc())
        elif query_str and query_str.strip():
            # Sort by FTS relevance
            ts_query = func.plainto_tsquery('english', query_str.strip())
            stmt = stmt.order_by(func.ts_rank_cd(Projects.search_vector, ts_query).desc())
        else:
            stmt = stmt.order_by(Projects.created_at.desc())

        # Pagination
        stmt = stmt.limit(size).offset(offset)

        # Execute count query
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        # Execute main query
        result = await self.session.execute(stmt)
        projects = result.scalars().all()

        items = [await self._build_project_read(p) for p in projects]
        return PaginatedProjectResponse.create(
            items=items, total=total, page=page, size=size
        ).model_dump()

    async def fetch_project_suggestions(self, query: str, limit: int = 5) -> List[str]:
        """
        Return suggestions for project names matching query using FTS vector.
        Matches against name, description, and skills (same as main search).
        """
        if not query or not query.strip():
            return []

        search_term = query.strip()
        ts_query = func.plainto_tsquery('english', search_term)
        
        stmt = (
            select(Projects.name)
            .where(Projects.search_vector.op('@@')(ts_query))
            .order_by(func.ts_rank_cd(Projects.search_vector, ts_query).desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_projects_paginated(self, limit: int = 20, offset: int = 0) -> List[dict]:
        """Return projects paginated (no is_live filter). Ordered by created_at desc."""
        query = (
            select(Projects)
            .options(*self._eager_project_options())
            .order_by(Projects.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        projects = result.scalars().all()
        return [await self._build_project_read(p) for p in projects]

    async def get_latest_non_interesting(self, limit: int = 6) -> List[dict]:
        """Latest projects where is_interesting_project == False (top `limit`)."""
        query = (
            select(Projects)
            .options(*self._eager_project_options())
            .where(Projects.is_interesting_project == False)
            .order_by(Projects.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        projects = result.scalars().all()
        return [await self._build_project_read(p) for p in projects]

    async def get_featured_projects(self, limit: int = 4) -> List[dict]:
        """Latest featured projects (is_interesting_project == True), limited."""
        query = (
            select(Projects)
            .options(*self._eager_project_options())
            .where(Projects.is_interesting_project == True)
            .order_by(Projects.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        projects = result.scalars().all()
        return [await self._build_project_read(p) for p in projects]

    # ----------------------------------------
    # 🔹 Project Membership Search
    # ----------------------------------------

    async def search_users_in_project(self, project_id: UUID, query: str, limit: int = 20) -> List[dict]:
        """Search users within a project by name or email using trigram similarity."""
        if not query or not query.strip():
            return []

        search_term = query.strip()
        stmt = (
            select(Users, ProjectMembership)
            .join(ProjectMembership, ProjectMembership.user_id == Users.id)
            .where(
                ProjectMembership.project_id == project_id,
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
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        user_list = []
        for user, membership in rows:
            user_dict = UserDetailRead.model_validate(user).model_dump()
            user_dict["membership"] = {
                "user_id": membership.user_id,
                "project_id": membership.project_id
            }
            user_list.append(user_dict)

        return user_list
