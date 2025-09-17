from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import EmailStr
from sqlalchemy import ForeignKey
from sqlmodel import Field, SQLModel, Column, Relationship
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import Optional

# ----------------------------------------
# 🔹 Enums
# ----------------------------------------

class AccessLevel(str, Enum):
    PUBLIC = "public"
    ADMIN = "admin"
    LOGGED_IN_USERS = "logged_in_users"
    SPECIAL_ACCESS_USERS = "special_access_users"
    NOT_LIVE = "not_live"
    SUPERADMIN = "superadmin"

    async def tag(self, session: AsyncSession) -> Optional["AccessLevelTag"]:
        return await session.scalar(
            select(AccessLevelTag).where(AccessLevelTag.name == self.value)
        )


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    SUBADMIN = "subadmin"
    FAMILY = "family"
    SPECIAL_USER = "special_user"

    async def tag(self, session: AsyncSession) -> Optional["RoleTag"]:
        return await session.scalar(
            select(RoleTag).where(RoleTag.name == self.value)
        )

# ----------------------------------------
# 🔹 Tag Models
# ---------------------------------------- 

class AccessLevelTag(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)


class RoleTag(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)


# ----------------------------------------
# 🔹 Core Models
# ----------------------------------------

class Users(SQLModel, table=True):
    id: UUID = Field(
        sa_column=Column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4)
    )

    created_at: datetime = Field(
        sa_column=Column(postgresql.TIMESTAMP(timezone=True), nullable=False, default=datetime.now)
    )

    preferred_name: str = Field(
        max_length=50,
        sa_column=Column(postgresql.VARCHAR(50), nullable=False, unique=True)
    )

    email: EmailStr = Field(
        sa_column=Column(postgresql.VARCHAR(255), nullable=False, unique=True)
    )

    password_hash: str = Field(
        sa_column=Column(postgresql.VARCHAR(255), nullable=False)
    )

    role: UserRole = Field(
        sa_column=Column(postgresql.ENUM(UserRole, name="userrole"), nullable=False, default=UserRole.USER)
    )

    email_verified: bool = Field(
        default=False,
        sa_column=Column(postgresql.BOOLEAN, nullable=False, default=False)
    )

    updated_at: datetime = Field(
        sa_column=Column(postgresql.TIMESTAMP(timezone=True), nullable=False, default=datetime.now, onupdate=datetime.now)
    )

    memberships: list["ProjectMembership"] = Relationship(back_populates="user")



class Projects(SQLModel, table=True):
    id: UUID = Field(
        sa_column=Column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4)
    )

    created_at: datetime = Field(
        sa_column=Column(postgresql.TIMESTAMP(timezone=True), nullable=False, default=datetime.now)
    )

    name: str = Field(
        max_length=100,
        sa_column=Column(postgresql.VARCHAR(100), nullable=False, unique=True)
    )

    short_description: str = Field(sa_column=Column(postgresql.TEXT, nullable=False))
    long_description: str = Field(sa_column=Column(postgresql.TEXT, nullable=False))

    access_level: AccessLevel = Field(
        sa_column=Column(postgresql.ENUM(AccessLevel, name="accesslevel"), nullable=False, default=AccessLevel.NOT_LIVE)
    )

    skills_used: list[str] = Field(
        default=[],
        sa_column=Column(postgresql.ARRAY(postgresql.VARCHAR), nullable=True)
    )

    github_link_backend: str | None = Field(
        default=None,
        sa_column=Column(postgresql.VARCHAR(255), nullable=True)
    )

    github_link_frontend: str | None = Field(
        default=None,
        sa_column=Column(postgresql.VARCHAR(255), nullable=True)
    )

    ngrok_url: str | None = Field(
        default=None,
        sa_column=Column(postgresql.VARCHAR(255), nullable=True)
    )

    is_interesting_project: bool = Field(
        default=False,
        sa_column=Column(postgresql.BOOLEAN, nullable=False, default=False)
    )

    is_live: bool = Field(
        default=False,
        sa_column=Column(postgresql.BOOLEAN, nullable=False, default=False)
    )

    docker_image_link_backend: str | None = Field(
        default=None,
        sa_column=Column(postgresql.VARCHAR(255), nullable=True)
    )

    docker_image_link_frontend: str | None = Field(
        default=None,
        sa_column=Column(postgresql.VARCHAR(255), nullable=True)
    )

    contributors: dict = Field(
        default={},
        sa_column=Column(postgresql.JSONB, nullable=True)
    )

    updated_at: datetime = Field(
        sa_column=Column(postgresql.TIMESTAMP(timezone=True), nullable=False, default=datetime.now, onupdate=datetime.now)
    )

    members: list["ProjectMembership"] = Relationship(back_populates="project")



# ----------------------------------------
# 🔹 Association Table (User ↔ Project)
# ----------------------------------------

class ProjectMembership(SQLModel, table=True):
    user_id: UUID = Field(
        sa_column=Column(postgresql.UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    )
    project_id: UUID = Field(
        sa_column=Column(postgresql.UUID(as_uuid=True), ForeignKey("projects.id"), primary_key=True)
    )

    user: "Users" = Relationship(back_populates="memberships")
    project: "Projects" = Relationship(back_populates="members")



