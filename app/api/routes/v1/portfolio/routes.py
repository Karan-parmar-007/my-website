from typing import Any, Dict, Optional, Annotated
from fastapi import (
    APIRouter,
    HTTPException,
    status,
    UploadFile,
    File,
    Response,
    Depends
)

from app.api.dependencies import PortfolioServiceDep
from app.api.routes.v1.portfolio.schemas import (
    ProfileInfoRead,
    ProfileInfoCreate,
    ProfileInfoUpdate,
    EducationCreate,
    EducationRead,
    EducationUpdate,
    WorkExperienceCreate,
    WorkExperienceRead,
    WorkExperienceUpdate,
    SkillCreate,
    SkillRead,
    SkillUpdate,
    SkillCreateForm,
    SkillUpdateForm,
    SkillCategoryCreate,
    SkillCategoryRead,
    SkillCategoryUpdate,
    SocialMediaRead,
    SocialMediaCreate,
    SocialMediaUpdate,
)
from app.common.dependencies.role_and_permission_check_auth import require_permission

from bson import ObjectId
from uuid import UUID



router = APIRouter()


# ----------------------------------------
# 🔹 Profile 
# ----------------------------------------

@router.get("/profile-info", response_model=ProfileInfoRead)
async def get_profile_info(service: PortfolioServiceDep):
    """Get profile text data only (no files)."""
    profile = await service.get_profile_info()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    result = profile.model_dump() if hasattr(profile, "model_dump") else profile.__dict__
    result["has_profile_image"] = bool(profile.profile_image_id)
    result["has_resume"] = bool(profile.resume_file_id)
    return result


@router.get("/profile-info/image")
async def get_profile_image(service: PortfolioServiceDep):
    """Stream profile image."""
    profile = await service.get_profile_info()
    if not profile or not profile.profile_image_id:
        raise HTTPException(status_code=404, detail="No image found")

    stream = await service.profile_bucket.open_download_stream(ObjectId(profile.profile_image_id))
    content: bytes = await stream.read()
    return Response(content, media_type=stream.metadata.get("content_type", "image/jpeg"))


@router.get("/profile-info/resume")
async def get_profile_resume(service: PortfolioServiceDep):
    """Stream resume file."""
    profile = await service.get_profile_info()
    if not profile or not profile.resume_file_id:
        raise HTTPException(status_code=404, detail="No resume found")

    stream = await service.resume_bucket.open_download_stream(ObjectId(profile.resume_file_id))
    content: bytes = await stream.read()
    content_type = stream.metadata.get("content_type", "application/pdf")
    filename = stream.metadata.get("filename", "resume.pdf")
    return Response(
        content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.post("/profile-info", status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    service: PortfolioServiceDep,
    data: ProfileInfoCreate,
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="edit_portfolio"))]
):
    """Create profile with text data only."""
    profile_exist = await service.get_profile_info()
    if profile_exist:
        raise HTTPException(status_code=400, detail="Profile already exists")
    profile = await service.create_profile_info(data, None, None)
    return {"message": "Profile created successfully", "profile_id": str(profile.id)}


@router.put("/profile-info", response_model=ProfileInfoRead)
async def update_portfolio(
    service: PortfolioServiceDep,
    data: ProfileInfoUpdate,
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="edit_portfolio"))]
):
    """Update profile text data only."""
    profile = await service.get_profile_info()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    updated_profile = await service.update_profile_info(data, None, None)
    result = updated_profile.model_dump() if hasattr(updated_profile, "model_dump") else updated_profile.__dict__
    result["has_profile_image"] = bool(updated_profile.profile_image_id)
    result["has_resume"] = bool(updated_profile.resume_file_id)
    return result


@router.put("/profile-info/image", status_code=status.HTTP_200_OK)
async def update_profile_image(
    service: PortfolioServiceDep,
    profile_image: UploadFile = File(...),
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="edit_portfolio"))] = None
):
    """Upload/replace profile image. Accepts: jpg, jpeg, png."""
    ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/jpg"}
    if profile_image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: JPG, PNG. Got: {profile_image.content_type}"
        )
    
    profile = await service.get_profile_info()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    await service.update_profile_image(profile_image)
    return {"message": "Profile image updated successfully"}


@router.delete("/profile-info/image", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile_image(
    service: PortfolioServiceDep,
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="edit_portfolio"))]
):
    """Delete profile image."""
    profile = await service.get_profile_info()
    if not profile or not profile.profile_image_id:
        raise HTTPException(status_code=404, detail="No image to delete")

    await service.delete_profile_image()


@router.put("/profile-info/resume", status_code=status.HTTP_200_OK)
async def update_profile_resume(
    service: PortfolioServiceDep,
    resume_file: UploadFile = File(...),
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="edit_portfolio"))] = None
):
    """Upload/replace resume file. Accepts: pdf, docx."""
    ALLOWED_RESUME_TYPES = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # docx
        "application/msword"  # doc
    }
    if resume_file.content_type not in ALLOWED_RESUME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: PDF, DOCX. Got: {resume_file.content_type}"
        )
    
    profile = await service.get_profile_info()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    await service.update_profile_resume(resume_file)
    return {"message": "Resume updated successfully"}


@router.delete("/profile-info/resume", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile_resume(
    service: PortfolioServiceDep,
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="edit_portfolio"))]
):
    """Delete resume file."""
    profile = await service.get_profile_info()
    if not profile or not profile.resume_file_id:
        raise HTTPException(status_code=404, detail="No resume to delete")

    await service.delete_profile_resume()


@router.delete("/profile-info", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    service: PortfolioServiceDep,
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="edit_portfolio"))]
):
    """Delete entire profile including files."""
    profile = await service.get_profile_info()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    await service.delete_profile_info()



# ----------------------------------------
# 🔹 Education
# ----------------------------------------

@router.get("/education", response_model=list[EducationRead], status_code=status.HTTP_200_OK)
async def get_education(service: PortfolioServiceDep):
    education = await service.get_education()
    if not education:
        raise HTTPException(status_code=404, detail="No education records found")
    return education

@router.post("/education", status_code=status.HTTP_201_CREATED)
async def create_education(
    service: PortfolioServiceDep,
    data: EducationCreate,
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="edit_education"))]
):
    education = await service.create_education(data)
    return {"message": "Education record created successfully", "education_id": str(education.id)}

@router.put("/education", status_code=status.HTTP_200_OK)
async def update_education(
    service: PortfolioServiceDep,
    data: EducationUpdate,
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="edit_education"))]
):
    try:
        updated_education = await service.update_education(data)
        if not updated_education:
            raise HTTPException(status_code=404, detail="Education record not found")
        return {"message": "Education record updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.delete("/education/{education_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_education(
    service: PortfolioServiceDep,
    education_id: UUID,
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="edit_education"))]
):
    try:
        await service.delete_education(education_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"message": "Education record deleted successfully"}



# ----------------------------------------
# 🔹 Wrok Experience
# ----------------------------------------

@router.get("/work-experience", response_model=list[WorkExperienceRead], status_code=status.HTTP_200_OK)
async def get_work_experience(service: PortfolioServiceDep):
    work_experience = await service.get_work_experience()
    if not work_experience:
        raise HTTPException(status_code=404, detail="No work experience records found")
    return work_experience

@router.post("/work-experience", status_code=status.HTTP_201_CREATED)
async def create_work_experience(
    service: PortfolioServiceDep, 
    data: WorkExperienceCreate,
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="edit_work_experience"))]
):
    work_experience = await service.create_work_experience(data)
    return {"message": "Work experience record created successfully", "work_experience_id": str(work_experience.id)}

@router.put("/work-experience", status_code=status.HTTP_200_OK)
async def update_work_experience(
    service: PortfolioServiceDep,
    data: WorkExperienceUpdate,
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="edit_work_experience"))]
):
    try:
        updated_work_experience = await service.update_work_experience(data)
        if not updated_work_experience:
            raise HTTPException(status_code=404, detail="Work experience record not found")
        return {"message": "Work experience record updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.delete("/work-experience/{work_experience_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_work_experience(
    service: PortfolioServiceDep,
    work_experience_id: UUID,
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="edit_work_experience"))]
):
    try:
        await service.delete_work_experience(work_experience_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"message": "Work experience record deleted successfully"}



# ----------------------------------------
# 🔹 Skill Category
# ----------------------------------------


# Skill Category Routes
@router.get("/skill-categories", response_model=list[SkillCategoryRead])
async def get_skill_categories(
    service: PortfolioServiceDep):
    categories = await service.get_skill_categories()
    return categories

@router.post("/skill-categories", status_code=status.HTTP_201_CREATED)
async def create_skill_category(
    service: PortfolioServiceDep, 
    data: SkillCategoryCreate,
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="edit_skill_categories"))]
):
    try:
        category = await service.create_skill_category(data)
        return {"message": "Skill category created successfully", "category_id": str(category.id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/skill-categories", status_code=status.HTTP_200_OK)
async def update_skill_category(
    service: PortfolioServiceDep, 
    data: SkillCategoryUpdate,
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="edit_skill_categories"))]
):
    try:
        await service.update_skill_category(data)
        return {"message": "Skill category updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/skill-categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill_category(
    service: PortfolioServiceDep, 
    category_id: UUID,
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="edit_skill_categories"))]
):
    try:
        await service.delete_skill_category(category_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"message": "Skill category deleted successfully"}


# ----------------------------------------
# 🔹 skill
# ----------------------------------------


@router.get("/skills", response_model=list[SkillRead])
async def get_skills(service: PortfolioServiceDep):
    return await service.get_skills_with_details()

@router.post("/skills", status_code=status.HTTP_201_CREATED)
async def create_skill(
    service: PortfolioServiceDep,
    form_data: Annotated[tuple[SkillCreateForm, Optional[UploadFile]], Depends(SkillCreateForm.as_form)],
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="edit_skills"))]
):
    data, skill_image = form_data
    create_data = SkillCreate(**data.model_dump() if hasattr(data, "model_dump") else data.__dict__)
    skill = await service.create_skill(create_data, skill_image)
    if not skill:
        raise HTTPException(status_code=400, detail="Failed to create skill")
    return {"message": "Skill created successfully", "skill_id": str(skill.id)}

@router.put("/skills", status_code=status.HTTP_200_OK, response_model=SkillRead)
async def update_skill(
    service: PortfolioServiceDep,
    form_data: Annotated[tuple[SkillUpdateForm, Optional[UploadFile]], Depends(SkillUpdateForm.as_form)],
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="edit_skills"))]
):
    data, skill_image = form_data
    update_data = SkillUpdate(**data.model_dump(exclude_unset=True) if hasattr(data, "model_dump") else data.__dict__)
    try:
        updated_skill = await service.update_skill(update_data, skill_image)
        return await service.get_skill_with_details(updated_skill)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    service: PortfolioServiceDep,
    skill_id: UUID,
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="edit_skills"))]
):
    try:
        await service.delete_skill(skill_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"message": "Skill deleted successfully"}

@router.get("/skills/{skill_id}/image")
async def get_skill_image(
    service: PortfolioServiceDep, 
    skill_id: UUID,
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="edit_skills"))]
):
    skill = await service.get_skill_by_id(skill_id)
    if not skill or not skill.image_id:
        raise HTTPException(status_code=404, detail="No image found for this skill")
    stream = await service.skill_bucket.open_download_stream(ObjectId(skill.image_id))
    content: bytes = await stream.read()
    return Response(content, media_type=stream.metadata.get("content_type", "image/jpeg"))


# ----------------------------------------
# 🔹 Social Media
# ----------------------------------------

@router.get("/social-media", response_model=list[SocialMediaRead])
async def get_social_media(service: PortfolioServiceDep):
    """
    Get all social media links.
    Public endpoint - no authentication required.
    """
    return await service.get_social_media_list()


@router.post("/social-media", response_model=SocialMediaRead, status_code=status.HTTP_201_CREATED)
async def create_social_media(
    service: PortfolioServiceDep,
    data: SocialMediaCreate,
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="edit_portfolio"))]
):
    """
    Create a new social media link.
    Requires edit_portfolio permission.
    """
    try:
        return await service.create_social_media(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/social-media/{social_media_id}", response_model=SocialMediaRead)
async def update_social_media(
    service: PortfolioServiceDep,
    social_media_id: UUID,
    data: SocialMediaUpdate,
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="edit_portfolio"))]
):
    """
    Update an existing social media link.
    Requires edit_portfolio permission.
    """
    try:
        return await service.update_social_media(social_media_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/social-media/{social_media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_social_media(
    service: PortfolioServiceDep,
    social_media_id: UUID,
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="edit_portfolio"))]
):
    """
    Delete a social media link.
    Requires edit_portfolio permission.
    """
    try:
        await service.delete_social_media(social_media_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

