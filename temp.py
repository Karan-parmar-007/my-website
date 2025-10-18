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

class RoleRequiredDependency:
    """Check if user has required role"""
    
    def __init__(self, required_roles: list[str]):
        self.required_roles = required_roles
    
    async def __call__(
        self,
        request: Request,
        user_data: Dict[str, Any] = Depends(AuthDependency())
    ) -> Dict[str, Any]:
        """Check if user has required role"""
        user_roles = user_data.get("roles", [])
        if not any(role in user_roles for role in self.required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return user_data

class PermissionRequiredDependency:
    """Check if user has required permissions"""
    
    def __init__(self, required_permissions: list[str]):
        self.required_permissions = required_permissions
    
    async def __call__(
        self,
        request: Request,
        user_data: Dict[str, Any] = Depends(AuthDependency())
    ) -> Dict[str, Any]:
        """Check if user has required permissions"""
        user_permissions = user_data.get("permissions", [])
        if not all(perm in user_permissions for perm in self.required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return user_data

# Create reusable dependency instances
require_auth = AuthDependency()
require_admin = RoleRequiredDependency(["admin"])
require_moderator = RoleRequiredDependency(["admin", "moderator"])

# Factory function for custom role requirements
def require_roles(*roles: str):
    return RoleRequiredDependency(list(roles))

def require_permissions(*permissions: str):
    return PermissionRequiredDependency(list(permissions))

# ----------------------------------------
# Additional middleware dependencies
# ----------------------------------------

class RateLimitDependency:
    """Rate limiting middleware"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # In production, use Redis or similar for distributed rate limiting
        self.request_counts: Dict[str, list] = {}
    
    async def __call__(self, request: Request) -> None:
        """Check rate limit"""
        from datetime import datetime, timedelta
        
        client_ip = request.client.host
        now = datetime.now()
        window_start = now - timedelta(seconds=self.window_seconds)
        
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = []
        
        # Clean old requests
        self.request_counts[client_ip] = [
            timestamp for timestamp in self.request_counts[client_ip]
            if timestamp > window_start
        ]
        
        if len(self.request_counts[client_ip]) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
        
        self.request_counts[client_ip].append(now)

class LoggingDependency:
    """Logging middleware for audit trails"""
    
    async def __call__(
        self, 
        request: Request,
        user_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log request details"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Request: {request.method} {request.url.path}")
        if user_data:
            logger.info(f"User: {user_data.get('user_id', 'Unknown')}")
        
        # You can add more logging logic here
        # e.g., log to database, send to monitoring service, etc.

# ----------------------------------------
# Usage in routes.py
# ----------------------------------------

from typing import Optional, Annotated
from fastapi import (
    APIRouter,
    HTTPException,
    status,
    Depends,
    Request
)
from app.api.dependencies.auth import (
    require_auth,
    require_admin,
    require_roles,
    require_permissions,
    RateLimitDependency,
    LoggingDependency
)

router = APIRouter()

# Create instances of middleware
rate_limiter = RateLimitDependency(max_requests=10, window_seconds=60)
logger_dep = LoggingDependency()

# ----------------------------------------
# Public route - no authentication
# ----------------------------------------
@router.post("/register")
async def create_user(
    service: UserServiceDep,
    data: UserCreate,
    _: None = Depends(rate_limiter)  # Only rate limiting
):
    """Public registration endpoint with rate limiting"""
    result = await service.create_user(data)
    return result

@router.post("/login")
async def login_user(
    service: UserServiceDep,
    data: UserLogin,
    _: None = Depends(rate_limiter)  # Only rate limiting
):
    """Public login endpoint with rate limiting"""
    result = await service.authenticate_user(data)
    return result

# ----------------------------------------
# Protected route - requires authentication
# ----------------------------------------
@router.get("/me")
async def get_current_user(
    request: Request,
    service: UserServiceDep,
    user_data: Dict[str, Any] = Depends(require_auth),  # Auth middleware
    _: None = Depends(logger_dep)  # Logging middleware
):
    """Get current user - requires authentication"""
    user_id = user_data.get("user_id")
    user = await service.get_user_by_id(user_id)
    return user

# ----------------------------------------
# Admin only routes
# ----------------------------------------
@router.get("/admin/users")
async def list_all_users(
    service: UserServiceDep,
    user_data: Dict[str, Any] = Depends(require_admin),  # Admin role required
    _: None = Depends(logger_dep)  # Logging
):
    """List all users - admin only"""
    users = await service.get_all_users()
    return users

# ----------------------------------------
# Multiple middleware example
# ----------------------------------------
@router.delete("/admin/user/{user_id}")
async def delete_user(
    user_id: str,
    service: UserServiceDep,
    user_data: Dict[str, Any] = Depends(require_roles("admin", "super_admin")),
    _: None = Depends(require_permissions("user:delete")),
    __: None = Depends(logger_dep),
    ___: None = Depends(rate_limiter)
):
    """Delete user - requires admin role AND delete permission"""
    await service.delete_user(user_id)
    return {"message": "User deleted successfully"}

# ----------------------------------------
# Using middleware in router groups
# ----------------------------------------

# Create a router with common dependencies
admin_router = APIRouter(
    prefix="/admin",
    dependencies=[
        Depends(require_admin),
        Depends(logger_dep)
    ]
)

@admin_router.get("/dashboard")
async def admin_dashboard():
    """All routes in admin_router automatically have admin and logging middleware"""
    return {"message": "Admin dashboard"}

@admin_router.get("/stats")
async def admin_stats():
    """This also has admin and logging middleware automatically"""
    return {"stats": "..."}

# ----------------------------------------
# Custom middleware chain example
# ----------------------------------------

from typing import List, Callable

def chain_middleware(*middlewares):
    """Helper to chain multiple middleware"""
    def combined_middleware(request: Request):
        results = []
        for middleware in middlewares:
            result = middleware(request)
            results.append(result)
        return results
    return combined_middleware

# Usage with custom chain
@router.get("/complex-route")
async def complex_route(
    request: Request,
    # Chain multiple middleware in specific order
    auth_data: Dict[str, Any] = Depends(require_auth),
    _: None = Depends(rate_limiter),
    __: None = Depends(logger_dep),
):
    """Route with multiple middleware in specific order"""
    return {"message": "Complex route executed"}

# ----------------------------------------
# Conditional middleware example
# ----------------------------------------

class ConditionalAuthDependency:
    """Apply auth only if certain conditions are met"""
    
    def __init__(self, require_auth_for_methods: List[str] = ["POST", "PUT", "DELETE"]):
        self.require_auth_for_methods = require_auth_for_methods
    
    async def __call__(self, request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
        if request.method in self.require_auth_for_methods:
            if not credentials:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required for this method"
                )
            return await AuthDependency()(request, credentials)
        return None

conditional_auth = ConditionalAuthDependency()

@router.get("/public-or-private")
async def public_or_private_route(
    auth_data: Optional[Dict[str, Any]] = Depends(conditional_auth)
):
    """GET is public, POST/PUT/DELETE require auth"""
    if auth_data:
        return {"message": "Authenticated access", "user": auth_data}
    return {"message": "Public access"}