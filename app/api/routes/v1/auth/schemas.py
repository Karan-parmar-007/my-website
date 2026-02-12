# app/api/routes/v1/auth/schemas.py
"""
Auth API request/response schemas.
All schemas use camelCase aliases for API consistency.
"""

from datetime import datetime
from uuid import UUID
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field, field_validator


# ----------------------------------------
# 🔹 Request Schemas
# ----------------------------------------

class SignupRequest(BaseModel):
    """User signup request."""
    email: EmailStr = Field(..., alias="email")
    password: str = Field(..., min_length=8, alias="password")
    preferred_name: str = Field(..., min_length=1, max_length=50, alias="preferredName")
    
    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Ensure password has minimum security requirements."""
        errors = []
        if len(v) < 8:
            errors.append("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            errors.append("Password must contain at least one uppercase letter")
        if not any(not c.isalnum() for c in v):
            errors.append("Password must contain at least one special character")
        
        if errors:
            raise ValueError(". ".join(errors))
        return v
    
    class Config:
        populate_by_name = True


class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr = Field(..., alias="email")
    password: str = Field(..., alias="password")
    
    class Config:
        populate_by_name = True


class RefreshTokenRequest(BaseModel):
    """Token refresh request - token comes from httpOnly cookie, not body."""
    pass  # Token is read from cookie, not request body


class ForgotPasswordRequest(BaseModel):
    """Forgot password - initiate OTP flow."""
    email: EmailStr = Field(..., alias="email")
    
    class Config:
        populate_by_name = True


class ResetPasswordRequest(BaseModel):
    """Reset password with OTP verification."""
    otp: str = Field(..., min_length=6, max_length=6, alias="otp")
    new_password: str = Field(..., min_length=8, alias="newPassword")
    logout_all_devices: bool = Field(default=True, alias="logoutAllDevices")
    
    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Ensure password has minimum security requirements."""
        errors = []
        if len(v) < 8:
            errors.append("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            errors.append("Password must contain at least one uppercase letter")
        if not any(not c.isalnum() for c in v):
            errors.append("Password must contain at least one special character")
        
        if errors:
            raise ValueError(". ".join(errors))
        return v
    
    class Config:
        populate_by_name = True


class ChangePasswordRequest(BaseModel):
    """Authenticated change password request."""
    current_password: str = Field(..., alias="currentPassword")
    new_password: str = Field(..., min_length=8, alias="newPassword")
    confirm_password: str = Field(..., min_length=8, alias="confirmPassword")
    logout_all_devices: bool = Field(default=False, alias="logoutAllDevices")

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Ensure password has minimum security requirements."""
        errors = []
        if len(v) < 8:
            errors.append("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            errors.append("Password must contain at least one uppercase letter")
        if not any(not c.isalnum() for c in v):
            errors.append("Password must contain at least one special character")
        
        if errors:
            raise ValueError(". ".join(errors))
        return v

    class Config:
        populate_by_name = True


# ----------------------------------------
# 🔹 Response Schemas
# ----------------------------------------

class TokenResponse(BaseModel):
    """Response after successful login/signup/refresh."""
    access_token_expires_in: int = Field(..., alias="accessTokenExpiresIn")
    message: str = Field(default="Success", alias="message")
    
    class Config:
        populate_by_name = True


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str = Field(..., alias="message")
    
    class Config:
        populate_by_name = True


class SessionInfo(BaseModel):
    """Information about an active session/device."""
    id: UUID = Field(..., alias="id")
    device_info: Optional[str] = Field(None, alias="deviceInfo")
    created_at: datetime = Field(..., alias="createdAt")
    expires_at: datetime = Field(..., alias="expiresAt")
    is_current: bool = Field(default=False, alias="isCurrent")
    
    class Config:
        populate_by_name = True
        from_attributes = True


class SessionsListResponse(BaseModel):
    """List of active sessions."""
    sessions: List[SessionInfo] = Field(..., alias="sessions")
    total_count: int = Field(..., alias="totalCount")
    
    class Config:
        populate_by_name = True


class UserInfoResponse(BaseModel):
    """Basic user info returned after auth."""
    id: UUID = Field(..., alias="id")
    email: EmailStr = Field(..., alias="email")
    preferred_name: str = Field(..., alias="preferredName")
    email_verified: bool = Field(..., alias="emailVerified")
    role_name: Optional[str] = Field(None, alias="roleName")
    
    class Config:
        populate_by_name = True
        from_attributes = True


class AuthResponse(BaseModel):
    """Full auth response with user info and token expiry."""
    user: UserInfoResponse = Field(..., alias="user")
    access_token_expires_in: int = Field(..., alias="accessTokenExpiresIn")
    message: str = Field(default="Success", alias="message")
    
    class Config:
        populate_by_name = True


# ----------------------------------------
# 🔹 Error Response Schemas
# ----------------------------------------

class FieldError(BaseModel):
    """Single field validation error."""
    field: str = Field(..., alias="field")
    message: str = Field(..., alias="message")
    
    class Config:
        populate_by_name = True


class ValidationErrorResponse(BaseModel):
    """Response with multiple field errors (no early escape)."""
    detail: str = Field(default="Validation failed", alias="detail")
    errors: List[FieldError] = Field(..., alias="errors")
    
    class Config:
        populate_by_name = True
