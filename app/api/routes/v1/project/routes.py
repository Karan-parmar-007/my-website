from typing import Any, Dict, Optional, Annotated
from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    status,
    UploadFile,
    Response,
    Depends,
    Query,
)
from uuid import UUID

from app.api.dependencies import ProjectAccessLevelServiceDep, ProjectMembershipServiceDep
from app.api.routes.v1.project.schemas import (
    ProjectRead,
    ProjectCreate,
    ProjectUpdate,
    ProjectAdminRead,
    AccessLevelRead,
    AccessLevelCreate,
    AccessLevelUpdate,
)
from app.common.schemas.user_project_link import (
    ProjectMembershipRead,
    ProjectMembershipCreate,
    ProjectMembershipWithUserRead,
    ProjectMembershipWithProjectRead,
)
from app.common.services.user_project_link import ProjectMembershipService
from app.common.dependencies.jwt_auth import require_auth
from app.common.dependencies.role_and_permission_check_auth import require_roles_and_permission
from app.api.dependencies import SessionDep, MongoDBDep

router = APIRouter()


# ----------------------------------------
# 🔹 Projects - Public Routes
# ----------------------------------------

@router.get("/projects/latest", response_model=list[ProjectRead])
async def get_latest_projects_non_interesting(
    service: ProjectAccessLevelServiceDep,
):
    """
    Public endpoint - Fetch latest non-interesting projects (top 6).
    """
    projects = await service.get_latest_non_interesting(limit=6)
    return projects


@router.get("/projects/featured", response_model=list[ProjectRead])
async def get_featured_projects(
    service: ProjectAccessLevelServiceDep,
):
    """
    Public endpoint - Fetch latest featured projects (top 4).
    """
    projects = await service.get_featured_projects(limit=4)
    return projects


# Move these BEFORE /projects/{project_id}
@router.get("/projects/suggestion", response_model=list[str])
async def project_suggestions_public(
    service: ProjectAccessLevelServiceDep,
    q: str = Query(..., min_length=1, description="Search query for project name"),
    limit: int = Query(5, ge=1, le=10, description="Max suggestions to return (1-10)"),
):
    """
    Public endpoint - Return project name suggestions matching query.
    """
    suggestions = await service.fetch_project_suggestions(query=q, limit=limit)
    return suggestions


@router.get("/projects/search", response_model=list[ProjectRead])
async def search_projects_public(
    service: ProjectAccessLevelServiceDep,
    q: str = Query(..., min_length=1, description="Search query for project name"),
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    size: int = Query(20, ge=1, le=100, description="Page size (max 100)"),
):
    """
    Public endpoint - Search projects by name with pagination.
    """
    offset = (page - 1) * size
    projects = await service.search_projects(query=q, limit=size, offset=offset)
    
    # Filter to return only ProjectRead fields (not admin fields)
    return [
        ProjectRead.model_validate(project).model_dump() 
        for project in projects
    ]


@router.get("/projects", response_model=list[ProjectRead])
async def get_all_projects(
    service: ProjectAccessLevelServiceDep,
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    size: int = Query(20, ge=1, le=100, description="Page size (max 100)"),
):
    """
    Public endpoint - Fetch all projects with pagination (no is_live filter).
    """
    offset = (page - 1) * size
    projects = await service.get_projects_paginated(limit=size, offset=offset)
    return projects


# This should come AFTER the specific routes above
@router.get("/projects/{project_id}", response_model=ProjectRead)
async def get_project_by_id(
    project_id: UUID,
    service: ProjectAccessLevelServiceDep,
):
    """
    Public endpoint - Fetch a single project by ID.
    """
    project = await service.get_project_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return project


# ----------------------------------------
# 🔹 Projects - Admin Routes
# ----------------------------------------

@router.get("/admin/projects/suggestion", response_model=list[str])
async def project_suggestions(
    service: ProjectAccessLevelServiceDep,
    user: Annotated[Dict[str, Any], Depends(require_roles_and_permission(
        allowed_roles=["super_admin", "admin"],
        permission_name="edit_projects"
    ))],
    q: str = Query(..., min_length=1, description="Search query for project name"),
    limit: int = Query(5, ge=1, le=10, description="Max suggestions to return (1-10)"),
):
    """
    Admin endpoint - Return project name suggestions matching query.
    """
    suggestions = await service.fetch_project_suggestions(query=q, limit=limit)
    return suggestions


@router.get("/admin/projects/search", response_model=list[ProjectAdminRead])
async def search_projects(
    service: ProjectAccessLevelServiceDep,
    user: Annotated[Dict[str, Any], Depends(require_roles_and_permission(
        allowed_roles=["super_admin", "admin"],
        permission_name="edit_projects"
    ))],
    q: str = Query(..., min_length=1, description="Search query for project name"),
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    size: int = Query(20, ge=1, le=100, description="Page size (max 100)"),
):
    """
    Admin endpoint - Search projects by name with pagination.
    Returns full project details.
    """
    offset = (page - 1) * size
    projects = await service.search_projects(query=q, limit=size, offset=offset)
    return projects


@router.get("/admin/projects", response_model=list[ProjectAdminRead])
async def get_all_projects_admin(
    service: ProjectAccessLevelServiceDep,
    user: Annotated[Dict[str, Any], Depends(require_roles_and_permission(
        allowed_roles=["super_admin", "admin"],
        permission_name="edit_projects"
    ))],
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    size: int = Query(20, ge=1, le=100, description="Page size (max 100)"),
):
    """
    Admin endpoint - Fetch all projects with full details (including non-live) with pagination.
    """
    offset = (page - 1) * size
    projects = await service.get_project_admin(limit=size, offset=offset)
    return projects


@router.get("/admin/projects/{project_id}", response_model=ProjectAdminRead)
async def get_project_by_id_admin(
    project_id: UUID,
    service: ProjectAccessLevelServiceDep,
    user: Annotated[Dict[str, Any], Depends(require_roles_and_permission(
        allowed_roles=["super_admin", "admin"],
        permission_name="edit_projects"
    ))],
):
    """
    Admin endpoint - Fetch a single project by ID with full details.
    """
    project = await service.get_project_admin_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return project


@router.post("/admin/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    service: ProjectAccessLevelServiceDep,
    user: Annotated[Dict[str, Any], Depends(require_roles_and_permission(
        allowed_roles=["super_admin", "admin"],
        permission_name="edit_projects"
    ))],
    data: tuple[ProjectCreate, Optional[UploadFile]] = Depends(ProjectCreate.as_form),
):
    """
    Admin endpoint - Create a new project.
    Supports file upload for project image.
    """
    project_data, project_image = data
    project = await service.create_project(project_data, project_image)
    return project


@router.put("/admin/projects/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: UUID,
    service: ProjectAccessLevelServiceDep,
    user: Annotated[Dict[str, Any], Depends(require_roles_and_permission(
        allowed_roles=["super_admin", "admin"],
        permission_name="edit_projects"
    ))],
    data: tuple[ProjectUpdate, Optional[UploadFile]] = Depends(ProjectUpdate.as_form),
):
    """
    Admin endpoint - Update a project.
    Can update all fields including image.
    """
    project_data, project_image = data
    updated_project = await service.update_project(project_id, project_data, project_image)
    if not updated_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return updated_project


@router.delete("/admin/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    service: ProjectAccessLevelServiceDep,
    user: Annotated[Dict[str, Any], Depends(require_roles_and_permission(
        allowed_roles=["super_admin", "admin"],
        permission_name="edit_projects"
    ))],
):
    """
    Admin endpoint - Delete a project by ID.
    Also deletes associated image from GridFS.
    """
    deleted = await service.delete_project(project_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ----------------------------------------
# 🔹 Access Levels
# ----------------------------------------

@router.get("/access-levels", response_model=list[AccessLevelRead])
async def get_all_access_levels(
    service: ProjectAccessLevelServiceDep,
    user: Dict[str, Any] = Depends(require_auth),
):
    """
    Fetch all access levels.
    Requires authentication.
    """
    access_levels = await service.get_access_levels()
    return access_levels


@router.get("/access-levels/{access_level_id}", response_model=AccessLevelRead)
async def get_access_level_by_id(
    access_level_id: UUID,
    service: ProjectAccessLevelServiceDep,
    user: Dict[str, Any] = Depends(require_auth),
):
    """
    Fetch a single access level by ID.
    """
    access_level = await service.get_access_level_by_id(access_level_id)
    if not access_level:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Access level not found"
        )
    return access_level


@router.post("/access-levels", response_model=AccessLevelRead, status_code=status.HTTP_201_CREATED)
async def create_access_level(
    data: AccessLevelCreate,
    service: ProjectAccessLevelServiceDep,
    user: Annotated[Dict[str, Any], Depends(require_roles_and_permission(
        allowed_roles=["super_admin"],
        permission_name="edit_projects"
    ))],
):
    """
    Admin endpoint - Create a new access level.
    """
    access_level = await service.create_access_level(data)
    return access_level


@router.put("/access-levels/{access_level_id}", response_model=AccessLevelRead)
async def update_access_level(
    access_level_id: UUID,
    data: AccessLevelUpdate,
    service: ProjectAccessLevelServiceDep,
    user: Annotated[Dict[str, Any], Depends(require_roles_and_permission(
        allowed_roles=["super_admin"],
        permission_name="edit_projects"
    ))],
):
    """
    Admin endpoint - Update an access level.
    """
    updated_access_level = await service.update_access_level(access_level_id, data)
    if not updated_access_level:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Access level not found"
        )
    return updated_access_level


@router.delete("/access-levels/{access_level_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_access_level(
    access_level_id: UUID,
    service: ProjectAccessLevelServiceDep,
    user: Annotated[Dict[str, Any], Depends(require_roles_and_permission(
        allowed_roles=["super_admin"],
        permission_name="edit_projects"
    ))],
):
    """
    Admin endpoint - Delete an access level by ID.
    """
    deleted = await service.delete_access_level(access_level_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Access level not found"
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ----------------------------------------
# 🔹 Project Membership
# ----------------------------------------

@router.get("/memberships/search")
async def search_users_in_project(
    service: ProjectAccessLevelServiceDep,
    user: Annotated[Dict[str, Any], Depends(require_roles_and_permission(
        allowed_roles=["super_admin", "admin"],
        permission_name="edit_projects"
    ))],
    project_id: UUID = Query(..., description="Project ID to search users in"),
    q: str = Query(..., min_length=1, description="Search query for user name or email"),
    limit: int = Query(20, ge=1, le=100, description="Max results to return"),
):
    """
    Admin endpoint - Search users within a specific project by name or email.
    Returns user details with membership info.
    """
    users = await service.search_users_in_project(project_id=project_id, query=q, limit=limit)
    return users


@router.get("/memberships", response_model=list[ProjectMembershipRead])
async def get_all_memberships(
    service: ProjectMembershipServiceDep,
    user: Annotated[Dict[str, Any], Depends(require_roles_and_permission(
        allowed_roles=["super_admin", "admin"],
        permission_name="edit_projects"
    ))],
):
    """
    Admin endpoint - Fetch all project memberships.
    """
    memberships = await service.get_project_memberships()
    return memberships


@router.get("/memberships/user/{user_id}", response_model=list[ProjectMembershipWithProjectRead])
async def get_memberships_by_user(
    user_id: UUID,
    service: ProjectMembershipServiceDep,
    user: Dict[str, Any] = Depends(require_auth),
):
    """
    Fetch all project memberships for a specific user with project details.
    Returns membership info along with project name.
    Users can view their own memberships.
    """
    memberships = await service.get_project_memberships_by_user_id(user_id)
    return memberships


@router.get("/memberships/project/{project_id}", response_model=list[ProjectMembershipWithUserRead])
async def get_memberships_by_project(
    project_id: UUID,
    service: ProjectMembershipServiceDep,
    user: Dict[str, Any] = Depends(require_auth),
):
    """
    Fetch all memberships for a specific project with user details.
    Returns membership info along with user email and preferred name.
    """
    memberships = await service.get_project_memberships_by_project_id(project_id)
    return memberships


@router.post("/memberships", response_model=ProjectMembershipRead, status_code=status.HTTP_201_CREATED)
async def create_membership(
    data: ProjectMembershipCreate,
    service: ProjectMembershipServiceDep,
    user: Annotated[Dict[str, Any], Depends(require_roles_and_permission(
        allowed_roles=["super_admin", "admin"],
        permission_name="edit_projects"
    ))],
):
    """
    Admin endpoint - Add a user to a project (create membership).
    """
    membership = await service.create_project_membership(data)
    return membership


@router.delete("/memberships", status_code=status.HTTP_204_NO_CONTENT)
async def remove_membership(
    service: ProjectMembershipServiceDep,
    user: Annotated[Dict[str, Any], Depends(require_roles_and_permission(
        allowed_roles=["super_admin", "admin"],
        permission_name="edit_projects"
    ))],
    user_id: UUID = Query(...),
    project_id: UUID = Query(...),
):
    """
    Admin endpoint - Remove a user from a project (delete membership).
    """
    deleted = await service.delete_project_membership(user_id, project_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found"
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)