from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional

from pydantic import EmailStr
from sqlalchemy import ForeignKey
from sqlmodel import Field, Relationship, SQLModel, Column, JSON
from sqlalchemy.dialects import postgresql


# ----------------------------------------
# 🔹 Core Models
# ----------------------------------------

class ProfileInfo(SQLModel, table=True):
    id: UUID = Field(
        sa_column=Column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4)
    )

    name: str = Field(
        max_length=100,
        sa_column=Column(postgresql.VARCHAR(100), nullable=False)
    )

    about: Optional[str] = Field(
        default=None,
        sa_column=Column(postgresql.TEXT, nullable=True)
    )

    headline: Optional[str] = Field(
        default=None,
        sa_column=Column(postgresql.VARCHAR(255), nullable=True)
    )

    email: EmailStr = Field(
        sa_column=Column(postgresql.VARCHAR(255), nullable=False, unique=True)
    )

    phone: Optional[str] = Field(
        default=None,
        sa_column=Column(postgresql.VARCHAR(15), nullable=True)
    )

    location: Optional[str] = Field(
        default=None,
        sa_column=Column(postgresql.VARCHAR(100), nullable=True)
    )

    github_url: Optional[str] = Field(
        default=None,
        sa_column=Column(postgresql.VARCHAR(255), nullable=True)
    )

    linkedin_url: Optional[str] = Field(
        default=None,
        sa_column=Column(postgresql.VARCHAR(255), nullable=True)
    )

    resume_file_id: Optional[str] = Field(
        default=None,
        sa_column=Column(postgresql.VARCHAR(255), nullable=True)
    )

    instagram: Optional[str] = Field(
        default=None,
        sa_column=Column(postgresql.VARCHAR(255), nullable=True)
    )

    profile_image_id: Optional[str] = Field(
        default=None,
        sa_column=Column(postgresql.VARCHAR(255), nullable=True)
    )

class Education(SQLModel, table=True):
    id: UUID = Field(
        sa_column=Column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4)
    )

    sequence: int = Field(
        sa_column=Column(postgresql.INTEGER, nullable=False)
    )


    school: str = Field(
        max_length=100,
        sa_column=Column(postgresql.VARCHAR(100), nullable=False)
    )

    degree: str = Field(
        max_length=100,
        sa_column=Column(postgresql.VARCHAR(100), nullable=False)
    )

    start_year: int = Field(
        sa_column=Column(postgresql.INTEGER, nullable=False)
    )

    end_year: int = Field(
        sa_column=Column(postgresql.INTEGER, nullable=False)
    )

    Score: Optional[float] = Field(
        default=None,
        sa_column=Column(postgresql.FLOAT, nullable=True)
    )

    description: Optional[str] = Field(
        default=None,
        sa_column=Column(postgresql.TEXT, nullable=True)
    )

class WorkExperience(SQLModel, table=True):
    id: UUID = Field(
        sa_column=Column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4)
    )

    sequence: int = Field(
        sa_column=Column(postgresql.INTEGER, nullable=False)
    )

    company: str = Field(
        max_length=100,
        sa_column=Column(postgresql.VARCHAR(100), nullable=False)
    )

    position: str = Field(
        max_length=100,
        sa_column=Column(postgresql.VARCHAR(100), nullable=False)
    )

    description: list[str] = Field(
        sa_column=Column(JSON, nullable=True)
    )

    start_date: datetime = Field(
        sa_column=Column(postgresql.DATE, nullable=False)
    )

    end_date: datetime = Field(
        sa_column=Column(postgresql.DATE, nullable=False)
    )


class SkillCategory(SQLModel, table=True):
    __tablename__ = "skillcategory"

    id: UUID = Field(
        sa_column=Column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4)
    )
    name: str = Field(
        sa_column=Column(postgresql.VARCHAR(100), nullable=False, unique=True)
    )

    # relationship back to skills
    skills: list["Skill"] = Relationship(back_populates="category_obj")


class Skill(SQLModel, table=True):
    __tablename__ = "skill"

    id: UUID = Field(
        sa_column=Column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4)
    )
    name: str = Field(
        sa_column=Column(postgresql.VARCHAR(100), nullable=False, unique=True)
    )

    category_id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("skillcategory.id"),
            nullable=True,
            index=True,
        )
    )

    image_id: Optional[str] = Field(
        default=None,
        sa_column=Column(postgresql.VARCHAR(255), nullable=True)
    )

    # relationship
    category_obj: "SkillCategory" = Relationship(back_populates="skills")




















