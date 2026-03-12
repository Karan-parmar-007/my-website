# app/api/middlewares/csrf.py
"""
CSRF Protection Middleware

Security Features:
- Validates CSRF token on state-changing requests (POST, PUT, PATCH, DELETE)
- Skips GET, HEAD, OPTIONS requests (safe methods)
- Skips configurable exempt paths (e.g., auth endpoints)
- Token is stored in httpOnly cookie and validated against X-CSRF-Token header

Usage:
    app.add_middleware(CSRFMiddleware)
"""

import secrets
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import security_settings

# Safe HTTP methods that don't require CSRF protection
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

# CSRF token cookie and header names
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"

# Token length in bytes (32 bytes = 64 hex chars)
CSRF_TOKEN_BYTES = 32


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection middleware for FastAPI.
    
    Security features:
    1. Validates CSRF token on unsafe requests (POST, PUT, PATCH, DELETE)
    2. Detects tampering: forces logout if access_token exists without csrf_token
    3. CSRF tokens are ONLY generated during login/signup (not in middleware)
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        method = request.method.upper()
        path = request.url.path
        
        # Check for tampering: has access_token but missing csrf_token
        # This indicates someone may have a fake/stolen access_token
        has_access_token = "access_token" in request.cookies
        has_csrf_token = CSRF_COOKIE_NAME in request.cookies
        
        if has_access_token and not has_csrf_token:
            # Force logout - clear all auth cookies and return 401
            cookie_domain = ".karanparmar.in" if security_settings.ENVIRONMENT == "production" else None
            response = JSONResponse(
                status_code=401,
                content={"detail": "Session invalid. Please login again."}
            )
            response.delete_cookie("access_token", domain=cookie_domain)
            response.delete_cookie("refresh_token", path="/api/v1/auth", domain=cookie_domain)
            response.delete_cookie(CSRF_COOKIE_NAME, domain=cookie_domain)
            return response
        
        # Skip safe methods - they don't change state
        if method in SAFE_METHODS:
            return await call_next(request)
        
        # Skip exempt paths (e.g., login, signup, refresh) and Swagger UI
        if self._is_exempt_path(path, request):
            return await call_next(request)
        
        # Validate CSRF token for unsafe methods
        if not self._validate_csrf_token(request):
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token missing or invalid. Include X-CSRF-Token header."}
            )
        
        return await call_next(request)
    
    def _is_exempt_path(self, path: str, request: Request) -> bool:
        """Check if path is in the exempt list or request is from Swagger UI."""
        exempt_paths = security_settings.CSRF_EXEMPT_PATHS
        
        # Check direct path exemption
        if any(path.startswith(exempt_path) for exempt_path in exempt_paths):
            return True
        
        # Check if request is coming from Swagger UI (Referer header)
        referer = request.headers.get("referer", "")
        if "/docs" in referer or "/redoc" in referer:
            return True
        
        return False
    
    def _validate_csrf_token(self, request: Request) -> bool:
        """
        Validate CSRF token from header against cookie.
        
        Security: Uses constant-time comparison to prevent timing attacks.
        """
        cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
        header_token = request.headers.get(CSRF_HEADER_NAME)
        
        if not cookie_token or not header_token:
            return False
        
        # Use secrets.compare_digest for timing-attack resistant comparison
        return secrets.compare_digest(cookie_token, header_token)


def generate_csrf_token() -> str:
    """
    Generate a new CSRF token.
    Can be used manually if needed outside the middleware.
    
    Returns:
        Secure random token string
    """
    return secrets.token_hex(CSRF_TOKEN_BYTES)
