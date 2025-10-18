from uuid import UUID
from sqlalchemy import ForeignKey, Column
from sqlalchemy.dialects import postgresql
from sqlmodel import SQLModel, Field, Relationship
from typing import TYPE_CHECKING, List



if TYPE_CHECKING:
    from app.api.routes.v1.user.models import Users  # only for type hints
    from app.api.routes.v1.project.models import Projects

class ProjectMembership(SQLModel, table=True):
    user_id: UUID = Field(
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("users.id"),
            primary_key=True
        )
    )
    project_id: UUID = Field(
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("projects.id"),
            primary_key=True
        )
    )

    user: "Users" = Relationship(back_populates="memberships")
    project: "Projects" = Relationship(back_populates="members")

