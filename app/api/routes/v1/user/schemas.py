from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime
from fastapi import UploadFile, Form, File





# ----------------------------------------
# 🔹 UserRole
# ----------------------------------------

class UserRoleRead(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

class UserRoleCreate(BaseModel):
    name: str
    description: Optional[str] = None

class UserRoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

# ----------------------------------------
# 🔹 Permission
# ----------------------------------------

class PermissionRead(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

class PermissionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    
class PermissionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

# ----------------------------------------
# 🔹 RolePermission
# ----------------------------------------

class RolePermissionRead(BaseModel):
    role_id: UUID
    permission_id: UUID

    class Config:
        from_attributes = True

class RolePermissionCreate(BaseModel):
    role_id: UUID
    permission_id: UUID


# ----------------------------------------
# 🔹 User
# ----------------------------------------

class UserRead(BaseModel):
    id: UUID
    preferred_name: str
    email: EmailStr
    role_id: UUID
    created_at: datetime
    role: Optional["UserRoleRead"] = None  # Forward reference to UserRoleRead

    class Config:
        from_attributes = True
    
class UserCreate(BaseModel):
    preferred_name: str
    email: EmailStr
    password: str
    role_id: UUID

class UserUpdate(BaseModel):
    preferred_name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ForgetPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# Resolve forward references
UserRead.model_rebuild()










