"""
Common MongoDB models used across multiple modules.
"""

from pydantic import BaseModel, Field, EmailStr
from datetime import datetime, timedelta
from typing import Literal


class PasswordChangeLog(BaseModel):
    """
    MongoDB model for tracking password change attempts with TTL-based limits.
    Auto-deletes after 24 hours using MongoDB TTL index.
    Tracks number of password resets per method (max 2 within 24 hours).
    """
    email: EmailStr
    change_method: Literal["forgot_password", "logged_in_reset", "admin_reset"]
    number_of_times: int = 1  # Number of resets within 24-hour window
    expire_at: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(hours=24))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "change_method": "forgot_password",
                "number_of_times": 1,
                "expire_at": "2024-01-16T10:30:00Z",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
