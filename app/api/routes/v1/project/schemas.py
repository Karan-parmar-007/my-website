import json
import math
from pydantic import BaseModel, field_validator
from typing import Optional, Union
from uuid import UUID
from datetime import datetime
from fastapi import UploadFile, Form, File

from app.api.routes.v1.portfolio.schemas import SkillRead


# ----------------------------------------
# 🔹 Access Level
# ----------------------------------------

class AccessLevelRead(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

class AccessLevelCreate(BaseModel):
    name: str
    description: Optional[str] = None

class AccessLevelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None



# ----------------------------------------
# 🔹 Projects
# ----------------------------------------

class ProjectRead(BaseModel):
    id: UUID
    name: str
    short_description: Optional[str] = None
    long_description: Optional[str] = None
    skills: list[SkillRead] = []
    access_level_id: UUID
    github_link_backend: Optional[str] = None
    github_link_frontend: Optional[str] = None
    ngrok_url: Optional[str] = None
    docker_image_link_backend: Optional[str] = None
    docker_image_link_frontend: Optional[str] = None
    contributors: Optional[dict] = {}
    is_interesting_project: bool
    is_live: bool
    access_level: Optional["AccessLevelRead"] = None
    project_image_base_six_four: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ProjectCreate(BaseModel):
    name: str
    short_description: str
    long_description: str
    access_level_id: UUID
    skill_ids: list[UUID] = []
    github_link_backend: Optional[str] = None
    github_link_frontend: Optional[str] = None
    ngrok_url: Optional[str] = None
    is_interesting_project: Optional[bool] = False
    is_live: Optional[bool] = False
    docker_image_link_backend: Optional[str] = None
    docker_image_link_frontend: Optional[str] = None
    contributors: Optional[dict] = {}

    @classmethod
    def as_form(
        cls,
        name: str = Form(...),
        short_description: str = Form(...),
        long_description: str = Form(...),
        access_level_id: UUID = Form(...),
        skill_ids: Optional[str] = Form(default="[]"),
        github_link_backend: Optional[str] = Form(default=None),
        github_link_frontend: Optional[str] = Form(default=None),
        ngrok_url: Optional[str] = Form(default=None),
        is_interesting_project: Optional[bool] = Form(default=False),
        is_live: Optional[bool] = Form(default=False),
        docker_image_link_backend: Optional[str] = Form(default=None),
        docker_image_link_frontend: Optional[str] = Form(default=None),
        contributors: Optional[str] = Form(default="{}"),
        project_image: Union[UploadFile, str, None] = File(None),
    ) -> tuple["ProjectCreate", Optional[UploadFile]]:
        try:
            parsed_contributors = json.loads(contributors) if contributors else {}
        except json.JSONDecodeError:
            parsed_contributors = {}

        try:
            parsed_skill_ids = json.loads(skill_ids) if skill_ids else []
            parsed_skill_ids = [UUID(sid) for sid in parsed_skill_ids]
        except (json.JSONDecodeError, ValueError):
            parsed_skill_ids = []

        if isinstance(project_image, str):
            project_image = None

        if project_image and hasattr(project_image, 'filename'):
            if project_image.filename == '':
                project_image = None
            
        return cls(
            name=name,
            short_description=short_description,
            long_description=long_description,
            access_level_id=access_level_id,
            skill_ids=parsed_skill_ids,
            github_link_backend=github_link_backend,
            github_link_frontend=github_link_frontend,
            ngrok_url=ngrok_url,
            is_interesting_project=is_interesting_project,
            is_live=is_live,
            docker_image_link_backend=docker_image_link_backend,
            docker_image_link_frontend=docker_image_link_frontend,
            contributors=parsed_contributors
        ), project_image

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    short_description: Optional[str] = None
    long_description: Optional[str] = None
    access_level_id: Optional[UUID] = None
    skill_ids: Optional[list[UUID]] = None
    github_link_backend: Optional[str] = None
    github_link_frontend: Optional[str] = None
    ngrok_url: Optional[str] = None
    is_interesting_project: Optional[bool] = None
    is_live: Optional[bool] = None
    docker_image_link_backend: Optional[str] = None
    docker_image_link_frontend: Optional[str] = None
    contributors: Optional[dict] = None

    @classmethod
    def as_form(
        cls,
        name: Optional[str] = Form(default=None),
        short_description: Optional[str] = Form(default=None),
        long_description: Optional[str] = Form(default=None),
        access_level_id: Optional[UUID] = Form(default=None),
        skill_ids: Optional[str] = Form(default=None),
        github_link_backend: Optional[str] = Form(default=None),
        github_link_frontend: Optional[str] = Form(default=None),
        ngrok_url: Optional[str] = Form(default=None),
        is_interesting_project: Optional[bool] = Form(default=None),
        is_live: Optional[bool] = Form(default=None),
        docker_image_link_backend: Optional[str] = Form(default=None),
        docker_image_link_frontend: Optional[str] = Form(default=None),
        contributors: Optional[str] = Form(default=None),
        project_image: Union[UploadFile, str, None] = File(None),
    ) -> tuple["ProjectUpdate", Optional[UploadFile]]:
        try:
            parsed_contributors = json.loads(contributors) if contributors else None
        except json.JSONDecodeError:
            parsed_contributors = None

        parsed_skill_ids = None
        if skill_ids is not None:
            try:
                parsed_skill_ids = [UUID(sid) for sid in json.loads(skill_ids)]
            except (json.JSONDecodeError, ValueError):
                parsed_skill_ids = None
        
        # Handle empty string from Swagger UI
        if isinstance(project_image, str):
            project_image = None

        if project_image and hasattr(project_image, 'filename'):
            if project_image.filename == '':
                project_image = None
            
        return cls(
            name=name,
            short_description=short_description,
            long_description=long_description,
            access_level_id=access_level_id,
            skill_ids=parsed_skill_ids,
            github_link_backend=github_link_backend,
            github_link_frontend=github_link_frontend,
            ngrok_url=ngrok_url,
            is_interesting_project=is_interesting_project,
            is_live=is_live,
            docker_image_link_backend=docker_image_link_backend,
            docker_image_link_frontend=docker_image_link_frontend,
            contributors=parsed_contributors
        ), project_image


# ----------------------------------------
# 🔹 Paginated Response
# ----------------------------------------

class PaginatedProjectResponse(BaseModel):
    items: list[ProjectRead] = []
    total: int = 0
    page: int = 1
    size: int = 20
    pages: int = 0

    @classmethod
    def create(cls, items: list, total: int, page: int, size: int):
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=math.ceil(total / size) if size > 0 else 0,
        )
