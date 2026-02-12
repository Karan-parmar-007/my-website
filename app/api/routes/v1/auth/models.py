# app/api/routes/v1/auth/models.py
"""
Auth-related database models for:
- SignUpLog: Tracks user signup events
- LoginLog: Tracks user login events  
- RefreshToken: Stores refresh tokens with device info for session management
"""

from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional

from pydantic import EmailStr
from sqlalchemy import ForeignKey
from sqlmodel import Field, SQLModel, Column
from sqlalchemy.dialects import postgresql


class SignUpLog(SQLModel, table=True):
    """Log of user signup events for audit trail."""
    __tablename__ = "signuplog"
    
    id: UUID = Field(
        sa_column=Column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4)
    )
    user_email: EmailStr = Field(
        sa_column=Column(postgresql.VARCHAR(255), nullable=False, index=True),
        alias="userEmail"
    )
    user_id: UUID = Field(
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True
        ),
        alias="userId"
    )
    created_at: datetime = Field(
        sa_column=Column(postgresql.TIMESTAMP(timezone=True), nullable=False, default=datetime.now),
        alias="createdAt"
    )

    class Config:
        populate_by_name = True


class LoginLog(SQLModel, table=True):
    """Log of user login events for audit trail."""
    __tablename__ = "loginlog"
    
    id: UUID = Field(
        sa_column=Column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4)
    )
    user_email: EmailStr = Field(
        sa_column=Column(postgresql.VARCHAR(255), nullable=False, index=True),
        alias="userEmail"
    )
    user_id: UUID = Field(
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True
        ),
        alias="userId"
    )
    created_at: datetime = Field(
        sa_column=Column(postgresql.TIMESTAMP(timezone=True), nullable=False, default=datetime.now),
        alias="createdAt"
    )

    class Config:
        populate_by_name = True


class RefreshToken(SQLModel, table=True):
    """
    Stores refresh tokens with device info for session management.
    - Token is hashed before storage for security
    - Device info tracks which device/browser the session belongs to
    - Used for: token rotation, logout all devices, session management
    """
    __tablename__ = "refreshtoken"
    
    id: UUID = Field(
        sa_column=Column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4)
    )
    user_id: UUID = Field(
        sa_column=Column(
            postgresql.UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True
        ),
        alias="userId"
    )
    token_hash: str = Field(
        sa_column=Column(postgresql.VARCHAR(256), nullable=False),
        alias="tokenHash"
    )
    expires_at: datetime = Field(
        sa_column=Column(postgresql.TIMESTAMP(timezone=True), nullable=False, index=True),
        alias="expiresAt"
    )
    created_at: datetime = Field(
        sa_column=Column(postgresql.TIMESTAMP(timezone=True), nullable=False, default=datetime.now),
        alias="createdAt"
    )
    updated_at: datetime = Field(
        sa_column=Column(
            postgresql.TIMESTAMP(timezone=True), 
            nullable=False, 
            default=datetime.now, 
            onupdate=datetime.now
        ),
        alias="updatedAt"
    )
    device_info: str = Field(
        sa_column=Column(postgresql.VARCHAR(500), nullable=True),
        alias="deviceInfo"
    )

    class Config:
        populate_by_name = True
