# app/api/dependencies/auth.py
from fastapi import Depends, HTTPException, status, Request, Cookie, Response
from typing import Optional, Dict, Any
from app.utils.security import verify_token

# Cookie names
CSRF_COOKIE_NAME = "csrf_token"


def _clear_all_auth_cookies(response: Response) -> None:
    """Clear all auth-related cookies on security failure."""
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token", path="/api/v1/auth")
    response.delete_cookie(CSRF_COOKIE_NAME)


class AuthDependency:
    """
    Base authentication dependency.
    
    Security: Validates all 3 cookies are present:
    - access_token: JWT for API access
    - csrf_token: CSRF protection token
    
    If any cookie is missing, ALL cookies are cleared to force re-login.
    """
    
    async def __call__(
        self, 
        request: Request,
        response: Response,
        access_token: Optional[str] = Cookie(None),
        csrf_token: Optional[str] = Cookie(None, alias=CSRF_COOKIE_NAME),
    ) -> Dict[str, Any]:
        """Verify JWT token from cookie and return user data"""
        
        # Check if access_token is missing
        if not access_token:
            _clear_all_auth_cookies(response)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if CSRF token is missing (security - prevents cookie manipulation)
        if not csrf_token:
            _clear_all_auth_cookies(response)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Security token missing. Please login again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        try:
            payload = verify_token(access_token)
            request.state.user = payload
            return payload
        except Exception:
            # Remove all cookies when token verification fails
            _clear_all_auth_cookies(response)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

require_auth = AuthDependency()