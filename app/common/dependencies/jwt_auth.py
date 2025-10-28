# app/api/dependencies/auth.py
from fastapi import Depends, HTTPException, status, Request, Cookie, Response
from typing import Optional, Dict, Any
from app.utils.security import verify_token

class AuthDependency:
    """Base authentication dependency"""
    
    async def __call__(
        self, 
        request: Request,
        response: Response,
        access_token: Optional[str] = Cookie(None)
    ) -> Dict[str, Any]:
        """Verify JWT token from cookie and return user data"""
        if not access_token:
            # ensure cookie is removed if missing/invalid
            response.delete_cookie("access_token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        try:
            payload = verify_token(access_token)
            request.state.user = payload
            return payload
        except Exception:
            # remove cookie when token verification fails
            response.delete_cookie("access_token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

require_auth = AuthDependency()