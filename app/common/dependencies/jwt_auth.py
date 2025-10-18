# app/api/dependencies/auth.py
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
from app.utils.security import verify_token

# Security scheme
security = HTTPBearer()

class AuthDependency:
    """Base authentication dependency"""
    
    async def __call__(
        self, 
        request: Request,
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> Dict[str, Any]:
        """Verify JWT token and return user data"""
        try:
            payload = verify_token(credentials.credentials)
            # Store user data in request state for access in route
            request.state.user = payload
            return payload
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        

require_auth = AuthDependency()