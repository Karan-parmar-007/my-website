from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from uuid import UUID
from typing import List, Optional


from app.common.schemas.user_project_link import ProjectMembershipRead, ProjectMembershipCreate
from app.common.models.user_project_link import ProjectMembership

# ----------------------------------------
# 🔹 Project Membership
# ----------------------------------------

class ProjectMembershipService:
    def __init__(self, session: AsyncSession, mongo: AsyncIOMotorDatabase):
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