from pymongo.asynchronous.database import AsyncDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from sqlalchemy import or_
from uuid import UUID
from typing import List, Optional
from app.common.schemas.user_project_link import ProjectMembershipRead, ProjectMembershipCreate, ProjectMembershipWithUserRead
from sqlalchemy.orm import selectinload

from app.common.models.user_project_link import ProjectMembership
from app.api.routes.v1.user.models import Users

# ----------------------------------------
# 🔹 Project Membership
# ----------------------------------------

class ProjectMembershipService:
    def __init__(self, session: AsyncSession, mongo: AsyncDatabase):
        self.session = session
        self.mongo = mongo

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
        query = (
            select(ProjectMembership)
            .options(selectinload(ProjectMembership.project))
            .where(ProjectMembership.user_id == user_id)
        )
        result = await self.session.execute(query)
        memberships = result.scalars().all()
        
        # Build response with project details
        response = []
        for membership in memberships:
            membership_dict = {
                "user_id": membership.user_id,
                "project_id": membership.project_id,
                "project_name": membership.project.name
            }
            response.append(membership_dict)
        
        return response
    
    async def get_project_memberships_by_project_id(self, project_id: UUID) -> List[dict]:
        query = (
            select(ProjectMembership)
            .options(selectinload(ProjectMembership.user))
            .where(ProjectMembership.project_id == project_id)
        )
        result = await self.session.execute(query)
        memberships = result.scalars().all()
        
        # Build response with user details
        response = []
        for membership in memberships:
            membership_dict = {
                "user_id": membership.user_id,
                "project_id": membership.project_id,
                "user_email": membership.user.email,
                "user_preferred_name": membership.user.preferred_name
            }
            response.append(membership_dict)
        
        return response
    
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

    async def search_users_in_project(self, project_id: UUID, query: str) -> List[dict]:
        """
        Search for users within a specific project by name or email.
        Returns memberships where the user matches the search query.
        """
        if not query or not query.strip():
            return []
        
        search_term = f"%{query.lower()}%"
        
        # Join ProjectMembership with Users and filter by project_id and user name/email
        stmt = (
            select(ProjectMembership)
            .join(Users, ProjectMembership.user_id == Users.id)
            .where(
                ProjectMembership.project_id == project_id,
                or_(
                    Users.preferred_name.ilike(search_term),
                    Users.email.ilike(search_term)
                )
            )
        )
        
        result = await self.session.execute(stmt)
        memberships = result.scalars().all()
        return [ProjectMembershipRead.model_validate(pm).model_dump() for pm in memberships]