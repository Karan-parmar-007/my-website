from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
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

class RolePermissionDeleteRequest(BaseModel):
    role_id: UUID
    permission_id: UUID


# ----------------------------------------
# 🔹 User
# ----------------------------------------

class UserRead(BaseModel):
    preferred_name: str
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True
    
class UserCreate(BaseModel):
    preferred_name: str
    email: EmailStr
    password: str

# New: admin create user schema (used by admin API)
class AdminCreateUser(BaseModel):
    preferred_name: str
    email: EmailStr
    password: str
    role_id: Optional[UUID] = None
    email_verified: Optional[bool] = False

class UserCreateResponse(BaseModel):
    status: str
    message: str
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    access_token_expires_in: Optional[int] = None
    user: Optional[UserRead] = None

class UserUpdate(BaseModel):
    preferred_name: Optional[str] = None
    email: Optional[EmailStr] = None

class UserBasicUpdate(BaseModel):
    """Basic user update - only name and email"""
    preferred_name: Optional[str] = None
    email: Optional[EmailStr] = None

class UserAdminUpdate(BaseModel):
    """Admin user update - all fields except password"""
    preferred_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role_id: Optional[UUID] = None
    email_verified: Optional[bool] = None


# New: full user detail read schema (do NOT expose password_hash)
class UserDetailRead(BaseModel):
    id: UUID
    preferred_name: str
    email: EmailStr
    role_id: UUID
    role: Optional[UserRoleRead] = None
    email_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserLoginResponse(BaseModel):
    status: str
    message: str
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    access_token_expires_in: Optional[int] = None
    user: Optional[UserRead] = None


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


# ----------------------------------------
# 🔹 Password Reset Schemas
# ----------------------------------------

class AdminPasswordResetRequest(BaseModel):
    """Admin/Super Admin resets any user's password"""
    email: EmailStr
    new_password: str


class ForgotPasswordResponse(BaseModel):
    """Response for forgot password initiation"""
    status: str
    message: str
    email: str
    # Token is set as HTTP-only cookie, not in response


class VerifyOTPRequest(BaseModel):
    """Verify OTP and reset password"""
    otp: str
    new_password: str
    # No confirm_password - simplified


class ResendOTPRequest(BaseModel):
    """Request to resend OTP"""
    email: EmailStr


class PasswordResetResponse(BaseModel):
    """Generic password reset response"""
    status: str
    message: str


# New schema for role validator
class RoleValidatorRequest(BaseModel):
    required_roles: List[str]

class RoleValidatorResponse(BaseModel):
    has_role: bool

class PermissionWithHave(BaseModel):
    permission: Dict[str, Any]  # Assuming Permission model has fields like id, name, etc.
    have: bool

class RolePermissionsResponse(BaseModel):
    role_info: Dict[str, Any]  # Assuming UserRole model has fields like id, name, etc.
    permissions: List[PermissionWithHave]

# Resolve forward references
UserRead.model_rebuild()










