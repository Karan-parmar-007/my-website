from typing import Any, Dict, Optional, Annotated
from fastapi import (
    APIRouter,
    HTTPException,
    status,
    UploadFile,
    Response,
    Depends
)

from app.api.dependencies import PortfolioServiceDep
from app.api.routes.v1.portfolio.schemas import (
    ProfileInfoRead,
    ProfileInfoCreate,
    ProfileInfoUpdate,
    ProfileInfoCreateForm,
    ProfileInfoUpdateForm,
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
    SkillCategoryUpdate
)
from app.common.dependencies.role_and_permission_check_auth import require_permission

from bson import ObjectId
import base64
from uuid import UUID


router = APIRouter()


# ----------------------------------------
# 🔹 Profile 
# ----------------------------------------

@router.get("/profile-info", response_model=ProfileInfoRead)
async def get_full_profile(service: PortfolioServiceDep):
    profile = await service.get_profile_info()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    image_data = None
    if profile.profile_image_id:
        try:
            # Use the pre-initialized profile_bucket
            stream = await service.profile_bucket.open_download_stream(ObjectId(profile.profile_image_id))
            profile_image_content: bytes = await stream.read()
            image_data = base64.b64encode(profile_image_content).decode("utf-8")
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving profile image: {str(e)}"
            )

    resume_data = None
    if profile.resume_file_id:
        try:
            # Use the pre-initialized resume_bucket
            stream = await service.resume_bucket.open_download_stream(ObjectId(profile.resume_file_id))
            resume_content: bytes = await stream.read()
            resume_data = base64.b64encode(resume_content).decode("utf-8")
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving resume file: {str(e)}"
            )

    result = profile.model_dump() if hasattr(profile, "dict") else profile.__dict__
    result["profile_image_base64"] = image_data
    result["resume_file_base64"] = resume_data
    return result

@router.get("/profile-image")
async def get_profile_image(service: PortfolioServiceDep):
    profile = await service.get_profile_info()
    if not profile or not profile.profile_image_id:
        raise HTTPException(status_code=404, detail="No image found")

    stream = await service.profile_bucket.open_download_stream(ObjectId(profile.profile_image_id))
    content: bytes = await stream.read()
    return Response(content, media_type=stream.metadata.get("content_type", "image/jpeg"))




@router.post("/profile-info", status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    service: PortfolioServiceDep,
    form_data: Annotated[tuple[ProfileInfoCreateForm, Optional[UploadFile], Optional[UploadFile]], Depends(ProfileInfoCreateForm.as_form)],
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="edit_portfolio"))]
):
    data, profile_image, resume_file = form_data
    profile_exist = await service.get_profile_info()
    if profile_exist:
        raise HTTPException(status_code=400, detail="Profile already exists")
    create_data = ProfileInfoCreate(**data.model_dump() if hasattr(data, "model_dump") else data.__dict__)
    profile = await service.create_profile_info(create_data, profile_image, resume_file)
    return {"message": "Profile created successfully", "profile_id": str(profile.id)}


@router.put("/profile-info", response_model=ProfileInfoRead)
async def update_portfolio(
    service: PortfolioServiceDep,
    form_data: Annotated[tuple[ProfileInfoUpdateForm, Optional[UploadFile], Optional[UploadFile]], Depends(ProfileInfoUpdateForm.as_form)],
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="edit_portfolio"))]
):
    data, profile_image, resume_file = form_data
    profile = await service.get_profile_info()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Convert form data to ProfileInfoUpdate model
    update_data = ProfileInfoUpdate(**data.model_dump() if hasattr(data, "model_dump") else data.__dict__)
    updated_profile = await service.update_profile_info(update_data, profile_image, resume_file)

    image_data = None
    if updated_profile.profile_image_id:
        stream = await service.profile_bucket.open_download_stream(ObjectId(updated_profile.profile_image_id))
        profile_image_content: bytes = await stream.read()
        image_data = base64.b64encode(profile_image_content).decode("utf-8")

    resume_data = None
    if updated_profile.resume_file_id:
        stream = await service.resume_bucket.open_download_stream(ObjectId(updated_profile.resume_file_id))
        resume_content: bytes = await stream.read()
        resume_data = base64.b64encode(resume_content).decode("utf-8")

    result = updated_profile.model_dump() if hasattr(updated_profile, "dict") else updated_profile.__dict__
    result["profile_image_base64"] = image_data
    result["resume_file_base64"] = resume_data
    return result


@router.delete("/profile-info", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    service: PortfolioServiceDep,
    user: Annotated[Dict[str, Any], Depends(require_permission(permission_name="edit_portfolio"))]
):
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
    update_data = SkillUpdate(**data.model_dump() if hasattr(data, "model_dump") else data.__dict__)
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

