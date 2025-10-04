from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime
from fastapi import UploadFile, Form, File


# ----------------------------------------
# 🔹 Accsslevel
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
    skills_used: Optional[list[str]] = []
    github_link_backend: Optional[str] = None
    github_link_frontend: Optional[str] = None
    docker_image_link_backend: Optional[str] = None
    docker_image_link_frontend: Optional[str] = None
    contributors: Optional[dict] = {}
    project_image_base_six_four: Optional[str] = None

    class Config:
        from_attributes = True

class ProjectAdminRead(ProjectRead):
    access_level_id: UUID
    is_interesting_project: bool
    is_live: bool
    created_at: datetime
    updated_at: datetime
    ngrok_url: Optional[str] = None
    access_level: Optional["AccessLevelRead"] = None

class ProjectCreate(BaseModel):
    name: str
    short_description: str
    long_description: str
    access_level_id: UUID
    skills_used: Optional[list[str]] = []
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
        skills_used: Optional[list[str]] = Form(default=[]),
        github_link_backend: Optional[str] = Form(default=None),
        github_link_frontend: Optional[str] = Form(default=None),
        ngrok_url: Optional[str] = Form(default=None),
        is_interesting_project: Optional[bool] = Form(default=False),
        is_live: Optional[bool] = Form(default=False),
        docker_image_link_backend: Optional[str] = Form(default=None),
        docker_image_link_frontend: Optional[str] = Form(default=None),
        contributors: Optional[dict] = Form(default={}),
        project_image: Optional[UploadFile] = File(default=None)
    ) -> tuple["ProjectCreate", Optional[UploadFile]]:
        return cls(
            name=name,
            short_description=short_description,
            long_description=long_description,
            access_level_id=access_level_id,
            skills_used=skills_used,
            github_link_backend=github_link_backend,
            github_link_frontend=github_link_frontend,
            ngrok_url=ngrok_url,
            is_interesting_project=is_interesting_project,
            is_live=is_live,
            docker_image_link_backend=docker_image_link_backend,
            docker_image_link_frontend=docker_image_link_frontend,
            contributors=contributors
        ), project_image

class ProjectUpdate(BaseModel):
    id: UUID
    name: Optional[str] = None
    short_description: Optional[str] = None
    long_description: Optional[str] = None
    access_level_id: Optional[UUID] = None
    skills_used: Optional[list[str]] = None
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
        id: UUID = Form(...),
        name: Optional[str] = Form(default=None),
        short_description: Optional[str] = Form(default=None),
        long_description: Optional[str] = Form(default=None),
        access_level_id: Optional[UUID] = Form(default=None),
        skills_used: Optional[list[str]] = Form(default=None),
        github_link_backend: Optional[str] = Form(default=None),
        github_link_frontend: Optional[str] = Form(default=None),
        ngrok_url: Optional[str] = Form(default=None),
        is_interesting_project: Optional[bool] = Form(default=None),
        is_live: Optional[bool] = Form(default=None),
        docker_image_link_backend: Optional[str] = Form(default=None),
        docker_image_link_frontend: Optional[str] = Form(default=None),
        contributors: Optional[dict] = Form(default=None),
        project_image: Optional[UploadFile] = File(default=None)
    ) -> tuple["ProjectUpdate", Optional[UploadFile]]:
        return cls(
            id=id,
            name=name,
            short_description=short_description,
            long_description=long_description,
            access_level_id=access_level_id,
            skills_used=skills_used,
            github_link_backend=github_link_backend,
            github_link_frontend=github_link_frontend,
            ngrok_url=ngrok_url,
            is_interesting_project=is_interesting_project,
            is_live=is_live,
            docker_image_link_backend=docker_image_link_backend,
            docker_image_link_frontend=docker_image_link_frontend,
            contributors=contributors
        ), project_image











