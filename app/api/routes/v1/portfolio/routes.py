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
    EducatioCreate,
    EducationRead,
    EducationUpdate,
    WorkExperienceCreate,
    WorkExperienceRead,
    WorkExperienceUpdate,
)
from bson import ObjectId
import base64
from uuid import UUID

router = APIRouter()


@router.get("/profile-info", response_model=ProfileInfoRead)
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




@router.post("/profile-info", status_code=status.HTTP_201_CREATED)
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


@router.put("/profile-info", response_model=ProfileInfoRead)
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


@router.delete("/profile-info", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(service: PortfolioServiceDep):
    profile = await service.get_profile_info()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    await service.delete_profile_info()


@router.get("/education", response_model=list[EducationRead], status_code=status.HTTP_200_OK)
async def get_education(service: PortfolioServiceDep):
    education = await service.get_education()
    if not education:
        raise HTTPException(status_code=404, detail="No education records found")
    return education

@router.post("/education", status_code=status.HTTP_201_CREATED)
async def create_education(service: PortfolioServiceDep, data: EducatioCreate):
    education = await service.create_education(data)
    return {"message": "Education record created successfully", "education_id": str(education.id)}

@router.put("/education", status_code=status.HTTP_200_OK)
async def update_education(service: PortfolioServiceDep, data: EducationUpdate):
    try:
        updated_education = await service.update_education(data)
        if not updated_education:
            raise HTTPException(status_code=404, detail="Education record not found")
        return {"message": "Education record updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.delete("/education/{education_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_education(service: PortfolioServiceDep, education_id: UUID):
    try:
        await service.delete_education(education_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"message": "Education record deleted successfully"}

@router.get("/work-experience", response_model=list[WorkExperienceRead], status_code=status.HTTP_200_OK)
async def get_work_experience(service: PortfolioServiceDep):
    work_experience = await service.get_work_experience()
    if not work_experience:
        raise HTTPException(status_code=404, detail="No work experience records found")
    return work_experience

@router.post("/work-experience", status_code=status.HTTP_201_CREATED)
async def create_work_experience(service: PortfolioServiceDep, data: WorkExperienceCreate):
    work_experience = await service.create_work_experience(data)
    return {"message": "Work experience record created successfully", "work_experience_id": str(work_experience.id)}

@router.put("/work-experience", status_code=status.HTTP_200_OK)
async def update_work_experience(service: PortfolioServiceDep, data: WorkExperienceUpdate):
    try:
        updated_work_experience = await service.update_work_experience(data)
        if not updated_work_experience:
            raise HTTPException(status_code=404, detail="Work experience record not found")
        return {"message": "Work experience record updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.delete("/work-experience/{work_experience_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_work_experience(service: PortfolioServiceDep, work_experience_id: UUID):
    try:
        await service.delete_work_experience(work_experience_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"message": "Work experience record deleted successfully"}   



