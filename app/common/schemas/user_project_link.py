from uuid import UUID
from pydantic import BaseModel, EmailStr
from typing import Optional


# ----------------------------------------
# 🔹 Project Membership
# ----------------------------------------

class ProjectMembershipRead(BaseModel):
    user_id: UUID
    project_id: UUID

    class Config:
        from_attributes = True

class ProjectMembershipWithUserRead(BaseModel):
    user_id: UUID
    project_id: UUID
    user_email: EmailStr
    user_preferred_name: str

    class Config:
        from_attributes = True

class ProjectMembershipCreate(BaseModel):
    user_id: UUID
    project_id: UUID

class ProjectMembershipWithProjectRead(BaseModel):
    user_id: UUID
    project_id: UUID
    project_name: str

    class Config:
        from_attributes = True
