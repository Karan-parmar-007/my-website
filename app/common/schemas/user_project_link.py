from uuid import UUID
from pydantic import BaseModel


# ----------------------------------------
# 🔹 Project Membership
# ----------------------------------------

class ProjectMembershipRead(BaseModel):
    user_id: UUID
    project_id: UUID

    class Config:
        from_attributes = True

class ProjectMembershipCreate(BaseModel):
    user_id: UUID
    project_id: UUID
