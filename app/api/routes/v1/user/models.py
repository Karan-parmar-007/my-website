from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional, List

from pydantic import EmailStr
from sqlalchemy import ForeignKey
from sqlmodel import Field, SQLModel, Column, Relationship
from sqlalchemy.dialects import postgresql



class UserRole(SQLModel, table=True):
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
    permissions: List["Permission"] = Relationship(
        back_populates="roles",
        link_model="RolePermission"
    )

class Permission(SQLModel, table=True):
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
    roles: List["UserRole"] = Relationship(
        back_populates="permissions",
        link_model="RolePermission"
    )

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

    role_id: UUID = Field(
        sa_column=Column(
            postgresql.UUID(as_uuid=True), 
            ForeignKey("userrole.id"), 
            nullable=False
        )
    )
    role: Optional[UserRole] = Relationship()

    email_verified: bool = Field(
        default=False,
        sa_column=Column(postgresql.BOOLEAN, nullable=False, default=False)
    )

    updated_at: datetime = Field(
        sa_column=Column(postgresql.TIMESTAMP(timezone=True), nullable=False, default=datetime.now, onupdate=datetime.now)
    )

    memberships: list["ProjectMembership"] = Relationship(back_populates="user")




# ----------------------------------------
# 🔹 Many-to-Many Relationship Model
# ----------------------------------------

class RolePermission(SQLModel, table=True):
    role_id: UUID = Field(
        sa_column=Column(postgresql.UUID(as_uuid=True), ForeignKey("userrole.id"), primary_key=True)
    )
    permission_id: UUID = Field(
        sa_column=Column(postgresql.UUID(as_uuid=True), ForeignKey("permission.id"), primary_key=True)
    )




