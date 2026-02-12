# app/api/routes/v1/auth/routes.py
"""
Auth API Routes

Endpoints:
- POST /auth/signup - User registration
- POST /auth/login - User login with token issuance
- POST /auth/logout - Logout current session
- POST /auth/refresh - Refresh access token
- POST /auth/forgot-password - Initiate password reset
- POST /auth/reset-password - Complete password reset
- GET /auth/sessions - List active sessions
- DELETE /auth/sessions/{session_id} - Revoke specific session
- DELETE /auth/sessions - Logout all devices
"""

import secrets
from typing import Dict, Any, Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Cookie

from app.api.routes.v1.auth.schemas import (
    SignupRequest,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
    TokenResponse,
    MessageResponse,
    SessionsListResponse,
    SessionInfo,
    AuthResponse,
    UserInfoResponse,
)
from app.api.routes.v1.auth.service import AuthService
from app.api.routes.v1.user.service import UserService
from app.api.routes.v1.user.schemas import UserCreate
from app.api.dependencies import SessionDep, MongoDBDep
from app.common.dependencies.jwt_auth import require_auth
from app.utils.security import (
    ACCESS_TOKEN_EXPIRE_SECONDS,
    REFRESH_TOKEN_EXPIRE_SECONDS,
    create_password_reset_token,
    decode_token,
)

router = APIRouter()

# CSRF token settings
CSRF_COOKIE_NAME = "csrf_token"
CSRF_TOKEN_BYTES = 32


# ----------------------------------------
# 🔹 Dependency for AuthService
# ----------------------------------------

async def get_auth_service(
    session: SessionDep,
    mongo: MongoDBDep
) -> AuthService:
    return AuthService(session=session, mongo=mongo)

async def get_user_service(
    session: SessionDep,
    mongo: MongoDBDep
) -> UserService:
    return UserService(session=session, mongo=mongo)

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]


# ----------------------------------------
# 🔹 Helper Functions
# ----------------------------------------

from app.config import security_settings

def _set_csrf_cookie(response: Response) -> None:
    """Set CSRF token cookie for client to use in subsequent requests."""
    token = secrets.token_hex(CSRF_TOKEN_BYTES)
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=False,  # Must be readable by JavaScript
        secure=(security_settings.ENVIRONMENT == "production"),
        samesite="lax",
        max_age=60 * 60 * 24 * 7  # 7 days
    )


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Set httpOnly cookies for access and refresh tokens, plus CSRF token."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=(security_settings.ENVIRONMENT == "production"),
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_SECONDS
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=(security_settings.ENVIRONMENT == "production"),
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_SECONDS,
        path="/api/v1/auth"  # Only sent to auth endpoints
    )
    # Also set CSRF cookie so client has it for future requests
    _set_csrf_cookie(response)


def _clear_auth_cookies(response: Response) -> None:
    """Clear all auth cookies on logout."""
    response.delete_cookie(
        key="access_token",
        secure=(security_settings.ENVIRONMENT == "production"),
        httponly=True,
        samesite="lax"
    )
    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
        secure=(security_settings.ENVIRONMENT == "production"),
        httponly=True,
        samesite="lax"
    )
    response.delete_cookie(
        key=CSRF_COOKIE_NAME,
        secure=(security_settings.ENVIRONMENT == "production"),
        httponly=False,
        samesite="lax"
    )


def _get_device_info(request: Request) -> str:
    """Extract device info from request headers."""
    user_agent = request.headers.get("User-Agent", "Unknown")
    return user_agent[:500]  # Limit length


# ----------------------------------------
# 🔹 Auth Endpoints
# ----------------------------------------

@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    request: Request,
    response: Response,
    data: SignupRequest,
    auth_service: AuthServiceDep,
    user_service: UserServiceDep,
):
    """
    Register a new user.
    
    - Creates user account
    - Logs signup event
    - Issues access and refresh tokens
    """
    # Check if email already exists
    existing = await auth_service.get_user_by_email(data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Create user via user service
    user_create = UserCreate(
        email=data.email,
        password=data.password,
        preferred_name=data.preferred_name
    )
    user = await user_service.create_user(user_create)
    
    # Log signup
    await auth_service.log_signup(user.id, user.email)
    
    # Login the user (issue tokens)
    device_info = _get_device_info(request)
    user, access_token, refresh_token = await auth_service.login(
        email=data.email,
        password=data.password,
        device_info=device_info
    )
    
    # Set cookies
    _set_auth_cookies(response, access_token, refresh_token)
    
    # Get role name
    role = await auth_service.get_user_role(user.role_id) if user.role_id else None
    
    return AuthResponse(
        user=UserInfoResponse(
            id=user.id,
            email=user.email,
            preferred_name=user.preferred_name,
            email_verified=user.email_verified,
            role_name=role.name if role else None
        ),
        access_token_expires_in=ACCESS_TOKEN_EXPIRE_SECONDS,
        message="Signup successful"
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: Request,
    response: Response,
    data: LoginRequest,
    service: AuthServiceDep,
):
    """
    Login user with email and password.
    
    - Validates credentials
    - Logs login event
    - Issues access and refresh tokens in httpOnly cookies
    """
    try:
        device_info = _get_device_info(request)
        user, access_token, refresh_token = await service.login(
            email=data.email,
            password=data.password,
            device_info=device_info
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    
    # Set cookies
    _set_auth_cookies(response, access_token, refresh_token)
    
    # Get role name
    role = await service.get_user_role(user.role_id) if user.role_id else None
    
    return AuthResponse(
        user=UserInfoResponse(
            id=user.id,
            email=user.email,
            preferred_name=user.preferred_name,
            email_verified=user.email_verified,
            role_name=role.name if role else None
        ),
        access_token_expires_in=ACCESS_TOKEN_EXPIRE_SECONDS,
        message="Login successful"
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    service: AuthServiceDep,
    user_data: Dict[str, Any] = Depends(require_auth),
    refresh_token: str = Cookie(None),
):
    """
    Logout current session.
    
    - Invalidates refresh token
    - Clears auth cookies
    """
    user_id = UUID(user_data.get("user_id"))
    
    if refresh_token:
        await service.logout(user_id, refresh_token)
    
    _clear_auth_cookies(response)
    
    return MessageResponse(message="Logged out successfully")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    service: AuthServiceDep,
    refresh_token: str = Cookie(None),
):
    """
    Refresh access token using refresh token.
    
    - Validates refresh token
    - Rotates refresh token (old one invalidated, new one issued)
    - Issues new access token
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing"
        )
    
    try:
        device_info = _get_device_info(request)
        user, access_token, new_refresh_token = await service.refresh_tokens(
            refresh_token=refresh_token,
            device_info=device_info
        )
    except ValueError as e:
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    
    # Set new cookies
    _set_auth_cookies(response, access_token, new_refresh_token)
    
    return TokenResponse(
        access_token_expires_in=ACCESS_TOKEN_EXPIRE_SECONDS,
        message="Token refreshed successfully"
    )


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    response: Response,
    data: ForgotPasswordRequest,
    service: AuthServiceDep,
    access_token: Optional[str] = Cookie(None),
    refresh_token: Optional[str] = Cookie(None),
):
    """
    Initiate forgot password flow.
    
    - If user is logged in (has cookies), logs them out first
    - Sends OTP to email
    - Sets temporary forgot_password_token in httpOnly cookie
    - Always returns success (prevents email enumeration)
    """
    # Auto-logout if cookies present
    if access_token or refresh_token:
        # We don't have user_id easily here without validating, 
        # but the intention is to clear the session for this device
        _clear_auth_cookies(response)

    # Initiate flow (send OTP)
    try:
        await service.initiate_forgot_password(data.email)
    except ValueError as e:
        # Expose rate limit errors
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e)
        )
    
    # Generate and set reset token cookie
    reset_token = create_password_reset_token(data.email)
    response.set_cookie(
        key="forgot_password_token",
        value=reset_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=300  # 5 minutes
    )
    
    return MessageResponse(
        message="If the email exists, an OTP has been sent"
    )


@router.post("/forgot-password/complete", response_model=MessageResponse)
async def complete_forgot_password(
    response: Response,
    data: ResetPasswordRequest,
    service: AuthServiceDep,
    forgot_password_token: Optional[str] = Cookie(None),
):
    """
    Complete password reset with OTP verification.
    
    - Verifies forgot_password_token from cookie
    - Verifies OTP
    - Updates password
    - Clears reset token cookie
    - Optionally logs out all devices
    """
    if not forgot_password_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing password reset token"
        )
        
    payload = decode_token(forgot_password_token)
    if not payload or payload.get("type") != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired reset token"
        )
    
    email = payload.get("email")
    if not email:
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    try:
        await service.reset_password(
            email=email,
            otp=data.otp,
            new_password=data.new_password,
            logout_all_devices=data.logout_all_devices
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Clear cookies
    response.delete_cookie(key="forgot_password_token")
    if data.logout_all_devices:
        _clear_auth_cookies(response)
    
    return MessageResponse(message="Password reset successful")


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    data: ChangePasswordRequest,
    auth_service: AuthServiceDep,
    user_data: Dict[str, Any] = Depends(require_auth),
    refresh_token: Optional[str] = Cookie(None),
):
    """
    Change password for authenticated user.
    
    - Verifies current password
    - Updates to new password
    - Enforces password history/limits
    - Optionally logs out all OTHER devices (keeps current session)
    """
    user_id = UUID(user_data.get("user_id"))
    
    result = await auth_service.change_password(
        user_id=user_id,
        current_password=data.current_password,
        new_password=data.new_password,
        confirm_password=data.confirm_password,
        logout_other_devices=data.logout_all_devices,
        current_refresh_token=refresh_token
    )
    
    if result["status"] == "error":
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
        
    return MessageResponse(message=result["message"])


@router.get("/sessions", response_model=SessionsListResponse)
async def get_sessions(
    service: AuthServiceDep,
    user_data: Dict[str, Any] = Depends(require_auth),
    refresh_token: str = Cookie(None),
):
    """
    List all active sessions for current user.
    
    - Shows device info for each session
    - Marks current session
    """
    user_id = UUID(user_data.get("user_id"))
    
    sessions = await service.get_user_sessions(user_id, refresh_token)
    
    return SessionsListResponse(
        sessions=[SessionInfo(**s) for s in sessions],
        total_count=len(sessions)
    )


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
async def revoke_session(
    session_id: UUID,
    service: AuthServiceDep,
    user_data: Dict[str, Any] = Depends(require_auth),
):
    """
    Revoke a specific session.
    
    - Logs out the device associated with the session
    """
    user_id = UUID(user_data.get("user_id"))
    
    success = await service.revoke_session(user_id, session_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    return MessageResponse(message="Session revoked")


@router.delete("/sessions", response_model=MessageResponse)
async def logout_other_devices(
    service: AuthServiceDep,
    user_data: Dict[str, Any] = Depends(require_auth),
    refresh_token: Optional[str] = Cookie(None),
):
    """
    Logout from all OTHER devices (keeps current session).
    
    - Revokes all refresh tokens except current one
    - Current session remains active
    """
    user_id = UUID(user_data.get("user_id"))
    
    count = await service.logout_other_devices(user_id, refresh_token)
    
    return MessageResponse(message=f"Logged out from {count} other device(s)")
