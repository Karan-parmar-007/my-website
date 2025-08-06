from typing import Optional
from fastapi import (
    APIRouter,
    HTTPException,
    status,
    File,
    Form,
    UploadFile,
    Response
)
from pydantic import EmailStr

from app.api.dependencies import PortfolioServiceDep
from app.api.routes.v1.portfolio.schemas import (
    ProfileInfoRead,
    ProfileInfoCreate,
    ProfileInfoUpdate,
)
from bson import ObjectId
import base64

router = APIRouter()


@router.get("/", response_model=ProfileInfoRead)
async def get_full_profile(service: PortfolioServiceDep):
    profile = await service.get_profile_info()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    image_data = None
    if profile.profile_image_id:
        stream = await service._get_gridfs_bucket().open_download_stream(ObjectId(profile.profile_image_id))
        content: bytes = await stream.read()
        image_data = base64.b64encode(content).decode("utf-8")

    result = profile.model_dump() if hasattr(profile, "dict") else profile.__dict__
    result["profile_image_base64"] = image_data
    return result

@router.get("/profile-image")
async def get_profile_image(service: PortfolioServiceDep):
    profile = await service.get_profile_info()
    if not profile or not profile.profile_image_id:
        raise HTTPException(status_code=404, detail="No image found")

    stream = await service._get_gridfs_bucket().open_download_stream(ObjectId(profile.profile_image_id))
    content: bytes = await stream.read()
    return Response(content, media_type=stream.metadata.get("content_type", "image/jpeg"))




@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    service: PortfolioServiceDep,
    name: str = Form(...),
    email: EmailStr = Form(...),
    about: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    github_url: Optional[str] = Form(None),
    linkedin_url: Optional[str] = Form(None),
    resume_url: Optional[str] = Form(None),
    instagram: Optional[str] = Form(None),
    profile_image: Optional[UploadFile] = File(None),
):
    data = ProfileInfoCreate(
        name=name,
        email=email,
        about=about,
        phone=phone,
        location=location,
        github_url=github_url,
        linkedin_url=linkedin_url,
        resume_url=resume_url,
        instagram=instagram,
    )
    profile_exist = await service.get_profile_info()
    if profile_exist:
        raise HTTPException(status_code=400, detail="Profile already exists")
    profile = await service.create_profile_info(data, profile_image)
    return {"message": "Profile created successfully", "profile_id": str(profile.id)}


@router.put("/", response_model=ProfileInfoRead)
async def update_portfolio(
    service: PortfolioServiceDep,
    name: Optional[str] = Form(None),
    email: Optional[EmailStr] = Form(None),
    about: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    github_url: Optional[str] = Form(None),
    linkedin_url: Optional[str] = Form(None),
    resume_url: Optional[str] = Form(None),
    instagram: Optional[str] = Form(None),
    profile_image: Optional[UploadFile] = File(None),
):
    data = ProfileInfoUpdate(
        name=name,
        email=email,
        about=about,
        phone=phone,
        location=location,
        github_url=github_url,
        linkedin_url=linkedin_url,
        resume_url=resume_url,
        instagram=instagram,
    )
    updated_profile = await service.update_profile_info(data, profile_image)
    if not updated_profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"message": "Profile Updated successfully"}


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(service: PortfolioServiceDep):
    profile = await service.get_profile_info()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    await service.delete_profile_info()
