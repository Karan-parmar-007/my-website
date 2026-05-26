# app/api/routes/v1/auth/service.py
"""
Auth Service - handles all authentication business logic.

Features:
- Login with access + refresh token issuance
- Logout with token invalidation
- Token refresh with rotation (prevents token reuse attacks)
- Device session management
- Forgot password with OTP
- Signup logging, Login logging
"""

from datetime import datetime, timezone
from uuid import UUID
from typing import Optional, List, Tuple
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, delete
from pymongo.asynchronous.database import AsyncDatabase

from app.api.routes.v1.auth.models import SignUpLog, LoginLog, RefreshToken
from app.api.routes.v1.user.models import Users, UserRole
from app.api.routes.v1.auth.mongo_model import AuthRepository
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    hash_token,
    verify_refresh_token_hash,
    ACCESS_TOKEN_EXPIRE_SECONDS,
    REFRESH_TOKEN_EXPIRE_SECONDS,
    generate_otp,
    hash_otp,
    verify_otp,
)
from app.utils.email import email_service

logger = logging.getLogger(__name__)


class AuthService:
    """
    Authentication service handling all auth-related operations.
    Uses async database sessions for non-blocking I/O.
    """
    
    def __init__(self, session: AsyncSession, mongo: AsyncDatabase):
        self.session = session
        self.mongo = mongo
        self._repo = AuthRepository(mongo)
    
    # ----------------------------------------
    # 🔹 User Lookup
    # ----------------------------------------
    
    async def get_user_by_email(self, email: str) -> Optional[Users]:
        """Fetch user by email."""
        query = select(Users).where(Users.email == email)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id: UUID) -> Optional[Users]:
        """Fetch user by ID."""
        query = select(Users).where(Users.id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_user_role(self, role_id: UUID) -> Optional[UserRole]:
        """Fetch user role by ID."""
        query = select(UserRole).where(UserRole.id == role_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    # ----------------------------------------
    # 🔹 Login / Logout
    # ----------------------------------------
    
    async def login(
        self, 
        email: str, 
        password: str, 
        device_info: str
    ) -> Tuple[Users, str, str]:
        """
        Authenticate user and issue tokens.
        
        Args:
            email: User email
            password: Plain text password
            device_info: User-Agent or device identifier
        
        Returns:
            Tuple of (user, access_token, refresh_token)
        
        Raises:
            ValueError: If credentials invalid
        """
        # Find user
        user = await self.get_user_by_email(email)
        if not user:
            raise ValueError("Invalid email or password")
        
        # Verify password
        if not verify_password(password, user.password_hash):
            raise ValueError("Invalid email or password")
        
        # Create tokens
        access_token = create_access_token(
            subject=str(user.id),
            additional_claims={"user_id": str(user.id), "email": user.email}
        )
        
        plain_refresh, token_hash, expires_at = create_refresh_token()
        
        # Store refresh token in DB
        refresh_token_record = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            device_info=device_info
        )
        self.session.add(refresh_token_record)
        
        # Log login
        await self._log_login(user.id, user.email)
        
        await self.session.commit()
        
        return user, access_token, plain_refresh
    
    async def logout(self, user_id: UUID, refresh_token: str) -> bool:
        """
        Logout user by invalidating the refresh token.
        
        Args:
            user_id: User ID
            refresh_token: Plain refresh token to invalidate
        
        Returns:
            True if token was found and deleted, False otherwise
        """
        token_hash = hash_token(refresh_token)
        
        query = delete(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.token_hash == token_hash
        )
        result = await self.session.execute(query)
        await self.session.commit()
        
        return result.rowcount > 0
    
    async def logout_all_devices(self, user_id: UUID) -> int:
        """
        Logout from all devices by deleting all refresh tokens.
        
        Args:
            user_id: User ID
        
        Returns:
            Number of sessions revoked
        """
        query = delete(RefreshToken).where(RefreshToken.user_id == user_id)
        result = await self.session.execute(query)
        await self.session.commit()
        
        return result.rowcount
    
    async def logout_other_devices(self, user_id: UUID, current_token: Optional[str] = None) -> int:
        """
        Logout from all devices EXCEPT the current one.
        
        Args:
            user_id: User ID
            current_token: Current refresh token to preserve (optional)
        
        Returns:
            Number of sessions revoked
        """
        if not current_token:
            # No current token provided, logout all
            return await self.logout_all_devices(user_id)
        
        # Find current session by token hash
        current_hash = hash_token(current_token)
        
        # Delete all tokens EXCEPT the current one
        query = delete(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.token_hash != current_hash
        )
        result = await self.session.execute(query)
        await self.session.commit()
        
        return result.rowcount
    
    # ----------------------------------------
    # 🔹 Token Refresh
    # ----------------------------------------
    
    async def refresh_tokens(
        self, 
        refresh_token: str, 
        device_info: str
    ) -> Tuple[Users, str, str]:
        """
        Refresh access token using refresh token with rotation.
        
        Token rotation: Old refresh token is deleted and new one issued.
        This prevents token reuse attacks.
        
        Args:
            refresh_token: Plain refresh token
            device_info: Current device info
        
        Returns:
            Tuple of (user, new_access_token, new_refresh_token)
        
        Raises:
            ValueError: If token invalid or expired
        """
        token_hash = hash_token(refresh_token)
        
        # Find token
        query = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self.session.execute(query)
        token_record = result.scalar_one_or_none()
        
        if not token_record:
            raise ValueError("Invalid refresh token")
        
        # Check expiry
        if token_record.expires_at < datetime.now(timezone.utc):
            # Delete expired token
            await self.session.delete(token_record)
            await self.session.commit()
            raise ValueError("Refresh token expired")
        
        # Get user
        user = await self.get_user_by_id(token_record.user_id)
        if not user:
            raise ValueError("User not found")
        
        # Delete old token (rotation)
        await self.session.delete(token_record)
        
        # Create new tokens
        access_token = create_access_token(
            subject=str(user.id),
            additional_claims={"user_id": str(user.id), "email": user.email}
        )
        
        plain_refresh, new_token_hash, expires_at = create_refresh_token()
        
        # Store new refresh token
        new_token_record = RefreshToken(
            user_id=user.id,
            token_hash=new_token_hash,
            expires_at=expires_at,
            device_info=device_info
        )
        self.session.add(new_token_record)
        
        # Log refresh as login event
        await self._log_login(user.id, user.email)
        
        await self.session.commit()
        
        return user, access_token, plain_refresh
    
    # ----------------------------------------
    # 🔹 Session Management
    # ----------------------------------------
    
    async def get_user_sessions(
        self, 
        user_id: UUID, 
        current_token: Optional[str] = None
    ) -> List[dict]:
        """
        Get all active sessions for a user.
        
        Args:
            user_id: User ID
            current_token: Current refresh token to mark as 'current'
        
        Returns:
            List of session info dicts
        """
        query = select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.expires_at > datetime.now(timezone.utc)
        )
        result = await self.session.execute(query)
        tokens = result.scalars().all()
        
        current_hash = hash_token(current_token) if current_token else None
        
        sessions = []
        for token in tokens:
            sessions.append({
                "id": token.id,
                "device_info": token.device_info,
                "created_at": token.created_at,
                "expires_at": token.expires_at,
                "is_current": token.token_hash == current_hash if current_hash else False
            })
        
        return sessions
    
    async def revoke_session(self, user_id: UUID, session_id: UUID) -> bool:
        """
        Revoke a specific session.
        
        Args:
            user_id: User ID (for security - only revoke own sessions)
            session_id: Session/Token ID to revoke
        
        Returns:
            True if session was found and revoked
        """
        query = delete(RefreshToken).where(
            RefreshToken.id == session_id,
            RefreshToken.user_id == user_id
        )
        result = await self.session.execute(query)
        await self.session.commit()
        
        return result.rowcount > 0
    
    # ----------------------------------------
    # 🔹 Password Reset
    # ----------------------------------------
    
    # ----------------------------------------
    # 🔹 Password Reset
    # ----------------------------------------
    
    async def initiate_forgot_password(self, email: str) -> bool:
        """
        Start forgot password flow - send OTP via email.
        
        Args:
            email: User email
        
        Returns:
            True if OTP sent (always returns True to prevent email enumeration)
        """
        user = await self.get_user_by_email(email)
        
        # Always return True to prevent email enumeration attacks
        if not user:
            # Check if this IP is hitting non-existent emails too often? (Optional)
            # For now, we simulate success for security
            logger.warning(f"Forgot password attempt for non-existent email: {email}")
            return True
        
        # Check daily reset limit
        can_reset = await self._repo.check_daily_limit(email, "reset_flow")
        if not can_reset:
            raise ValueError("Daily password reset limit exceeded")

        # Generate and hash OTP
        otp = generate_otp()
        otp_hash = hash_otp(otp)
        
        # Save OTP using repository (handles rate limiting)
        # This will raise ValueError if rate limit hit
        await self._repo.save_otp(email, otp_hash)
        
        # Send OTP email
        email_service.send(
            to_email=email,
            subject="Password Reset OTP",
            plain_text=f"Your password reset OTP is: {otp}\n\nThis code expires in 5 minutes.",
            html_content=f"""
                <h2>Password Reset</h2>
                <p>Your OTP is: <strong>{otp}</strong></p>
                <p>This code expires in 5 minutes.</p>
            """
        )
        
        return True
    
    async def reset_password(
        self, 
        email: str, 
        otp: str, 
        new_password: str,
        logout_all_devices: bool = True
    ) -> bool:
        """
        Reset password after OTP verification.
        """
        # Get and verify OTP record
        reset_doc = await self._repo.verify_otp_record(email)
        
        # Verify OTP
        if not verify_otp(otp, reset_doc["otp_hash"]):
             # Increment wrong attempts (optional logic for repository)
             raise ValueError("Invalid OTP")
        
        # Get user
        user = await self.get_user_by_email(email)
        if not user:
            raise ValueError("User not found")

        # Check daily limit again (just to be safe)
        can_reset = await self._repo.check_daily_limit(email, "reset_flow")
        if not can_reset:
             raise ValueError("Daily password reset limit exceeded")
        
        # Update password
        user.password_hash = hash_password(new_password)
        self.session.add(user)
        
        # Delete OTP record
        await self._repo.delete_otp(email)
        
        # Record successful reset
        await self._repo.record_action(email, "reset_flow")
        
        # Optionally logout all devices
        if logout_all_devices:
            await self.logout_all_devices(user.id)
        
        # Send confirmation email
        try:
            email_service.send(
                to_email=email,
                subject="Password Reset Successfully",
                plain_text=f"Your password has been reset successfully. If you did not request this, please contact support immediately.",
                html_content="<p>Your password has been reset successfully. If you did not request this, please contact support immediately.</p>"
            )
        except Exception as e:
            logger.warning(f"Failed to send password reset confirmation email: {e}")

        await self.session.commit()
        
        return True
    
    async def change_password(
        self, 
        user_id: UUID, 
        current_password: str, 
        new_password: str, 
        confirm_password: str,
        logout_other_devices: bool = False,
        current_refresh_token: Optional[str] = None
    ) -> dict:
        """
        Logged-in user changes their own password.
        
        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password
            confirm_password: Confirmation of new password
            logout_other_devices: If True, logs out all OTHER sessions (keeps current)
            current_refresh_token: Current session's refresh token to preserve
        
        Returns:
            Success/error dict
        """
        if new_password != confirm_password:
            return {"status": "error", "message": "Passwords do not match"}

        user = await self.get_user_by_id(user_id)
        if not user:
            return {"status": "error", "message": "User not found"}

        if not verify_password(current_password, user.password_hash):
            return {"status": "error", "message": "Current password is incorrect"}

        # Check daily limit
        can_change = await self._repo.check_daily_limit(user.email, "logged_in_change")
        if not can_change:
            return {
                "status": "error",
                "message": "Daily password change limit reached. Please try again tomorrow."
            }

        # Update password
        user.password_hash = hash_password(new_password)
        self.session.add(user)
        
        # Record action
        await self._repo.record_action(user.email, "logged_in_change")
        
        # Logout OTHER devices if requested (keeps current session)
        sessions_revoked = 0
        if logout_other_devices:
            sessions_revoked = await self.logout_other_devices(user_id, current_refresh_token)
        
        # Send confirmation email
        try:
            email_service.send(
                to_email=user.email,
                subject="Password Changed Successfully",
                plain_text=f"Your password has been changed successfully.",
                html_content="<p>Your password has been changed successfully.</p>"
            )
        except Exception as e:
            logger.warning(f"Failed to send email: {e}")

        await self.session.commit()
        
        message = "Password changed successfully"
        if sessions_revoked > 0:
            message += f". Logged out from {sessions_revoked} other device(s)"
        
        return {"status": "success", "message": message}
    
    # ----------------------------------------
    # 🔹 Logging
    # ----------------------------------------
    
    async def _log_signup(self, user_id: UUID, email: str) -> None:
        """Log signup event."""
        log = SignUpLog(user_id=user_id, user_email=email)
        self.session.add(log)
    
    async def _log_login(self, user_id: UUID, email: str) -> None:
        """Log login event."""
        log = LoginLog(user_id=user_id, user_email=email)
        self.session.add(log)
    
    async def log_signup(self, user_id: UUID, email: str) -> None:
        """Public method to log signup from user service."""
        await self._log_signup(user_id, email)
        await self.session.commit()
    
    # ----------------------------------------
    # 🔹 Token Cleanup (for cron job)
    # ----------------------------------------
    
    async def cleanup_expired_tokens(self) -> int:
        """
        Delete all expired refresh tokens.
        Called by cron job at midnight.
        
        Returns:
            Number of tokens deleted
        """
        query = delete(RefreshToken).where(
            RefreshToken.expires_at < datetime.now(timezone.utc)
        )
        result = await self.session.execute(query)
        await self.session.commit()
        
        logger.info(f"Cleaned up {result.rowcount} expired refresh tokens")
        return result.rowcount
