from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional, List, TYPE_CHECKING

from pydantic import EmailStr
from sqlalchemy import ForeignKey
from sqlmodel import Field, SQLModel, Column, Relationship
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import TSVECTOR

from app.common.models.user_project_link import ProjectMembership

if TYPE_CHECKING:
    from app.common.models.project_skill_link import ProjectSkill


class AccessLevel(SQLModel, table=True):
    id: UUID = Field(
        sa_column=Column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4)
    )
    name: str = Field(
        sa_column=Column(postgresql.VARCHAR(50), nullable=False, unique=True)
    )
    description: str = Field(
        sa_column=Column(postgresql.TEXT, nullable=True)
    )
    created_at: datetime = Field(
        sa_column=Column(postgresql.TIMESTAMP(timezone=True), nullable=False, default=datetime.now)
    )
    updated_at: datetime = Field(
        sa_column=Column(postgresql.TIMESTAMP(timezone=True), nullable=False, default=datetime.now, onupdate=datetime.now)
    )


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

    access_level_id: UUID = Field(
        sa_column=Column(
            postgresql.UUID(as_uuid=True), 
            ForeignKey("accesslevel.id"), 
            nullable=False
        )
    )
    access_level: Optional[AccessLevel] = Relationship()

    project_skills: list["ProjectSkill"] = Relationship(back_populates="project")

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

    project_image_id: Optional[str] = Field(
        default=None,
        sa_column=Column(postgresql.VARCHAR(255), nullable=True)
    )

    search_vector: Optional[str] = Field(
        default=None,
        sa_column=Column(TSVECTOR, nullable=True),
        exclude=True,
    )


# Ensure ProjectSkill is imported so SQLAlchemy can resolve the relationship
from app.common.models.project_skill_link import ProjectSkill  # noqa: E402, F401
