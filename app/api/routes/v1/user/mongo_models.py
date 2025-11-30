"""
MongoDB models for OTP verification tracking (user-specific).
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class OTPVerification(BaseModel):
    """
    MongoDB document for OTP verification tracking.
    Collection: otp_verifications
    
    Indexes:
    - email (unique)
    - expire_at (TTL index for auto-deletion)
    """
    email: EmailStr = Field(..., description="User email (indexed, unique)")
    otp_hash: str = Field(..., description="Hashed OTP for secure storage")
    expire_at: datetime = Field(..., description="OTP expiration time (5 minutes from creation)")
    number_of_times_sent: int = Field(default=1, description="Count of OTP send attempts")
    number_of_wrong_attempts: int = Field(default=0, description="Count of failed verification attempts")
    retry_time: Optional[datetime] = Field(default=None, description="Time when user can retry after being blocked")
    blocked: bool = Field(default=False, description="True if user exceeded limits")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Record creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "otp_hash": "$2b$12$...",
                "expire_at": "2024-01-01T12:05:00Z",
                "number_of_times_sent": 1,
                "number_of_wrong_attempts": 0,
                "retry_time": None,
                "blocked": False,
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-01T12:00:00Z"
            }
        }
