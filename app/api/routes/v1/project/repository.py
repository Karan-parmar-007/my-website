from typing import List
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.routes.v1.project.models import Projects, AccessLevel
from app.api.routes.v1.user.models import Users
from app.common.models.user_project_link import ProjectMembership
from uuid import UUID

class ProjectRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def fetch_projects(self, limit: int, offset: int):
        """
        Return Projects rows (with access_level relationship loaded) using limit/offset pagination.
        """
        stmt = (
            select(Projects)
            .options(selectinload(Projects.access_level))
            .order_by(Projects.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return rows

    async def fetch_project_suggestions(self, query: str, limit: int) -> List[str]:
        """
        Search project names (case-insensitive) and return suggestions.
        Uses .limit() to restrict DB results.
        """
        search_term = f"%{query.lower()}%"
        stmt = (
            select(Projects.name)
            .where(Projects.name.ilike(search_term))
            .limit(limit * 2)  # fetch extra rows for filtering
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        suggestions = [name for name in rows if query.lower() in name.lower()]
        return suggestions[:limit]

    async def search_projects(self, query: str, limit: int, offset: int) -> List[Projects]:
        """
        Search projects by name (case-insensitive) and return full project details.
        Uses pagination (limit/offset) and eagerly loads relationships.
        """
        search_term = f"%{query.lower()}%"
        stmt = (
            select(Projects)
            .options(selectinload(Projects.access_level))
            .where(Projects.name.ilike(search_term))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return rows

    async def fetch_featured_projects(self) -> List[Projects]:
        """
        Fetch all projects where is_interesting_project is True and is_live is True.
        """
        stmt = (
            select(Projects)
            .options(selectinload(Projects.access_level))
            .where(Projects.is_interesting_project == True, Projects.is_live == True)
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return rows

    async def search_users_in_project(self, project_id: UUID, query: str, limit: int = 20) -> List:
        """
        Search for users within a specific project by preferred_name or email.
        Returns list of Users with their membership info.
        """
        search_term = f"%{query.lower()}%"
        stmt = (
            select(Users, ProjectMembership)
            .join(ProjectMembership, ProjectMembership.user_id == Users.id)
            .where(
                ProjectMembership.project_id == project_id,
                or_(
                    Users.preferred_name.ilike(search_term),
                    Users.email.ilike(search_term)
                )
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        return rows