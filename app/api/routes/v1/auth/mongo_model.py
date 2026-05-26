
from datetime import datetime, timedelta, timezone
from typing import Optional
from pymongo.asynchronous.database import AsyncDatabase
import logging

from app.config import security_settings

logger = logging.getLogger(__name__)

class AuthRepository:
    """
    Repository for all Auth related MongoDB operations.
    Handles OTPs and Password Change Logs.
    """
    def __init__(self, mongo: AsyncDatabase):
        self.mongo = mongo
        self.otp_collection = self.mongo["password_resets"]
        self.log_collection = self.mongo["password_change_logs"]

    # ----------------------------------------
    # 🔹 OTP Operations
    # ----------------------------------------

    async def save_otp(self, email: str, otp_hash: str) -> None:
        """
        Save or update OTP for an email.
        Increments send count if within valid window.
        """
        now = datetime.now(timezone.utc)
        
        # Check existing
        existing = await self.otp_collection.find_one({"email": email})
        
        if existing:
            # Check resend delay
            last_sent = existing.get("updated_at", existing.get("created_at"))
            # Ensure last_sent is timezone-aware
            if last_sent.tzinfo is None:
                last_sent = last_sent.replace(tzinfo=timezone.utc)
                
            time_diff = (now - last_sent).total_seconds()
            
            if time_diff < security_settings.OTP_RESEND_DELAY_SECONDS:
                raise ValueError(f"Please wait {security_settings.OTP_RESEND_DELAY_SECONDS - int(time_diff)} seconds before resending OTP")
            
            # Check max resends (total sends = existing + 1)
            # send_count starts at 1. If limit is 2 resends, max total is 3.
            # config: OTP_MAX_RESENDS = 2 (implies 2 RE-sends, so 3 total)
            max_sends = security_settings.OTP_MAX_RESENDS + 1
            if existing.get("send_count", 1) >= max_sends:
                 # Optional: block for some time or just fail
                 # For now, we'll just block sending
                 raise ValueError("Max OTP resend limit reached. Please try again later.")

            await self.otp_collection.update_one(
                {"email": email},
                {
                    "$set": {
                        "otp_hash": otp_hash,
                        "updated_at": now,
                        "expires_at": now.timestamp() + 300  # 5 minutes
                    },
                    "$inc": {"send_count": 1}
                }
            )
        else:
            # New OTP
            await self.otp_collection.update_one(
                {"email": email},
                {
                    "$set": {
                        "otp_hash": otp_hash,
                        "created_at": now,
                        "updated_at": now,
                        "expires_at": now.timestamp() + 300,
                        "send_count": 1
                    }
                },
                upsert=True
            )

    async def verify_otp_record(self, email: str) -> dict:
        """
        Retrieve OTP record for verification.
        """
        record = await self.otp_collection.find_one({"email": email})
        if not record:
            raise ValueError("No OTP request found")
        
        if record.get("expires_at") < datetime.now(timezone.utc).timestamp():
            await self.otp_collection.delete_one({"email": email})
            raise ValueError("OTP has expired")
            
        return record

    async def delete_otp(self, email: str) -> None:
        """Delete OTP record after successful use."""
        await self.otp_collection.delete_one({"email": email})

    # ----------------------------------------
    # 🔹 Password Change Limits
    # ----------------------------------------

    async def check_daily_limit(self, email: str, limit_type: str) -> bool:
        """
        Check if user has reached daily limit for an action.
        limit_type allowed values: 'reset_flow', 'logged_in_change'
        """
        # Determine max based on type
        if limit_type == 'reset_flow':
             max_count = security_settings.MAX_PASSWORD_RESETS_PER_DAY
        elif limit_type == 'logged_in_change':
             max_count = security_settings.MAX_PASSWORD_CHANGES_PER_DAY
        else:
             return True # Should not happen

        log = await self.log_collection.find_one({
            "email": email,
            "type": limit_type
        })
        
        if not log:
            return True
        
        # Check expiry (TTL) - logic handled by mongo usually, but we check logic here too
        # If expire_at is in past, we can assume it's reset
        expire_at = log.get("expire_at")
        if expire_at.tzinfo is None:
            expire_at = expire_at.replace(tzinfo=timezone.utc)
            
        if expire_at < datetime.now(timezone.utc):
             return True
             
        return log.get("count", 0) < max_count

    async def record_action(self, email: str, limit_type: str) -> None:
        """
        Record a successful password change/reset.
        """
        now = datetime.now(timezone.utc)
        expire_at = now + timedelta(days=1)
        
        # Update or Insert
        # We need to handle if record exists but is expired (restart count)
        # But for simplicity with TTL approach, we just upsert.
        
        existing = await self.log_collection.find_one({
            "email": email,
            "type": limit_type
        })
        
        existing_expire_at = existing.get("expire_at") if existing else None
        if existing_expire_at and existing_expire_at.tzinfo is None:
            existing_expire_at = existing_expire_at.replace(tzinfo=timezone.utc)
        
        if existing and existing_expire_at > now:
             await self.log_collection.update_one(
                {"_id": existing["_id"]},
                {
                    "$inc": {"count": 1},
                    "$set": {"updated_at": now}
                }
            )
        else:
            # New or expired
            await self.log_collection.update_one(
                {"email": email, "type": limit_type},
                {
                    "$set": {
                        "count": 1,
                        "created_at": now,
                        "updated_at": now,
                        "expire_at": expire_at
                    }
                },
                upsert=True
            )
