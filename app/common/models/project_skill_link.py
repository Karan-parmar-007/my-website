from uuid import UUID
from sqlalchemy import ForeignKey, Column
from sqlalchemy.dialects import postgresql
from sqlmodel import SQLModel, Field, Relationship
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from app.api.routes.v1.project.models import Projects
    from app.api.routes.v1.portfolio.models import Skill


class ProjectSkill(SQLModel, table=True):
    __tablename__ = "project_skill"

    project_id: UUID = Field(
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("projects.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    skill_id: UUID = Field(
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("skill.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )

    project: "Projects" = Relationship(back_populates="project_skills")
    skill: "Skill" = Relationship(back_populates="project_skills")


# Ensure related model modules are imported so their classes are registered with SQLAlchemy
try:
    import app.api.routes.v1.project.models  # noqa: F401
    import app.api.routes.v1.portfolio.models  # noqa: F401
except Exception:
    pass
