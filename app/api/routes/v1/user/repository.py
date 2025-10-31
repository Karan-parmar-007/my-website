from typing import List
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select as sql_select

from app.api.routes.v1.user.models import Users, UserRole

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def fetch_users(self, limit: int, offset: int):
        """
        Return Users rows (with role relationship loaded) using limit/offset pagination.
        """
        stmt = (
            select(Users)
            .options(selectinload(Users.role))  # Eagerly load the role relationship
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return rows

    async def fetch_user_suggestions(self, query: str, limit: int):
        """
        Search preferred_name and email (case-insensitive) and return merged suggestions.
        Uses .limit() to restrict DB results (5-10 max).
        """
        search_term = f"%{query.lower()}%"
        stmt = (
            select(Users.preferred_name, Users.email)
            .where(
                or_(
                    Users.preferred_name.ilike(search_term),
                    Users.email.ilike(search_term),
                )
            )
            .limit(limit * 3)  # fetch a few extra rows to allow dedupe/filtering
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        # merge names and emails into flat suggestion list and dedupe while preserving content
        suggestions = list(
            {value for row in rows for value in row if value and query.lower() in value.lower()}
        )
        return suggestions[:limit]

    async def search_users(self, query: str, limit: int, offset: int):
        """
        Search users by preferred_name or email (case-insensitive) and return full user details.
        Uses pagination (limit/offset) and eagerly loads role relationship.
        """
        search_term = f"%{query.lower()}%"
        stmt = (
            select(Users)
            .options(selectinload(Users.role))  # Eagerly load the role relationship
            .where(
                or_(
                    Users.preferred_name.ilike(search_term),
                    Users.email.ilike(search_term),
                )
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return rows