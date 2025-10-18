from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from uuid import UUID
from bson import ObjectId
import base64

from app.api.routes.v1.portfolio.models import ProfileInfo, Education, WorkExperience, Skill, SkillCategory
from app.api.routes.v1.portfolio.schemas import ProfileInfoCreate, ProfileInfoUpdate
from app.api.routes.v1.portfolio.schemas import EducationCreate, EducationRead, EducationUpdate
from app.api.routes.v1.portfolio.schemas import WorkExperienceCreate, WorkExperienceRead, WorkExperienceUpdate
from app.api.routes.v1.portfolio.schemas import SkillCreate, SkillRead, SkillUpdate, SkillCreateForm, SkillUpdateForm
from app.api.routes.v1.portfolio.schemas import SkillCategoryCreate, SkillCategoryRead, SkillCategoryUpdate
from app.utils.gridfs_utils import upload_to_gridfs, delete_from_gridfs, get_gridfs_bucket


class PortfolioService:
    def __init__(self, session: AsyncSession, mongo: AsyncIOMotorDatabase):
        self.session = session
        self.mongo = mongo
        self.profile_bucket = get_gridfs_bucket(mongo, "profile_files")
        self.resume_bucket = get_gridfs_bucket(mongo, "resume_files")
        self.skill_bucket = get_gridfs_bucket(mongo, "skill_files")


    # ----------------------------------------
    # 🔹 Profile service
    # ----------------------------------------

    async def get_profile_info_with_files(self) -> dict:
        profile = await self.get_profile_info()
        if not profile:
            return {}

        profile_dict = profile.model_dump() if hasattr(profile, "model_dump") else profile.__dict__

        # Get profile image if exists
        if profile.profile_image_id:
            try:
                stream = await self.profile_bucket.open_download_stream(ObjectId(profile.profile_image_id))
                content: bytes = await stream.read()
                profile_dict["profile_image_base64"] = base64.b64encode(content).decode("utf-8")
            except Exception:
                profile_dict["profile_image_base64"] = None

        # Get resume file if exists
        if profile.resume_file_id:
            try:
                stream = await self.resume_bucket.open_download_stream(ObjectId(profile.resume_file_id))
                content = await stream.read()
                profile_dict["resume_file_base64"] = base64.b64encode(content).decode("utf-8")
            except Exception:
                profile_dict["resume_file_base64"] = None

        return profile_dict


    async def get_profile_info(self) -> ProfileInfo | None:
        result = await self.session.execute(select(ProfileInfo).limit(1))
        if not result:
            return None
        return result.scalars().first()

    async def create_profile_info(
        self,
        data: ProfileInfoCreate,
        profile_image: UploadFile | None = None,
        resume_file: UploadFile | None = None
    ) -> ProfileInfo:
        profile = ProfileInfo(**data.model_dump())
        if profile_image:
            profile.profile_image_id = await upload_to_gridfs(self.profile_bucket, profile_image)
        if resume_file:
            profile.resume_file_id = await upload_to_gridfs(self.resume_bucket, resume_file)

        self.session.add(profile)
        try:
            await self.session.commit()
            await self.session.refresh(profile)
        except Exception as e:
            await self.session.rollback()
            raise ValueError(f"Error creating profile: {str(e)}")
        return profile

    async def update_profile_info(
        self,
        data: ProfileInfoUpdate,
        profile_image: UploadFile | None = None,
        resume_file: UploadFile | None = None
    ) -> ProfileInfo:
        profile = await self.get_profile_info()
        if not profile:
            raise ValueError("Profile does not exist")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(profile, field, value)

        if profile_image:
            if profile.profile_image_id:
                await delete_from_gridfs(self.profile_bucket, profile.profile_image_id)
            profile.profile_image_id = await upload_to_gridfs(self.profile_bucket, profile_image)

        if resume_file:
            if profile.resume_file_id:
                await delete_from_gridfs(self.resume_bucket, profile.resume_file_id)
            profile.resume_file_id = await upload_to_gridfs(self.resume_bucket, resume_file)

        self.session.add(profile)
        try:
            await self.session.commit()
            await self.session.refresh(profile)
        except Exception as e:
            await self.session.rollback()
            raise ValueError(f"Error updating profile: {str(e)}")
        return profile

    async def delete_profile_info(self) -> None:
        profile = await self.get_profile_info()
        if not profile:
            raise ValueError("Profile does not exist")

        if profile.profile_image_id:
            await delete_from_gridfs(self.profile_bucket, profile.profile_image_id)
        if profile.resume_file_id:
            await delete_from_gridfs(self.resume_bucket, profile.resume_file_id)

        await self.session.delete(profile)
        try:
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise ValueError(f"Error deleting profile: {str(e)}")


# ----------------------------------------
# 🔹 education service
# ----------------------------------------


    async def get_education(self) -> list[Education]:
        result = await self.session.execute(select(Education))
        return list(result.scalars().all())

    async def create_education(self, data: EducationCreate) -> Education:
        education = Education(**data.model_dump())
        self.session.add(education)
        try:
            await self.session.commit()
            await self.session.refresh(education)
        except Exception as e:
            await self.session.rollback()
            raise ValueError(f"Error creating education: {str(e)}")
        return education

    async def update_education(self, data: EducationUpdate) -> Education:
        education = await self.session.get(Education, data.id)
        if not education:
            raise ValueError("Education record does not exist")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(education, field, value)

        self.session.add(education)
        try:
            await self.session.commit()
            await self.session.refresh(education)
        except Exception as e:
            await self.session.rollback()
            raise ValueError(f"Error updating education: {str(e)}")
        return education
    
    async def delete_education(self, education_id ) -> None:
        education = await self.session.get(Education, education_id)
        if not education:
            raise ValueError("Education record does not exist")

        await self.session.delete(education)
        try:
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise ValueError(f"Error deleting education: {str(e)}")


# ----------------------------------------
# 🔹 WorkExperince service
# ----------------------------------------

    async def get_work_experience(self) -> list[WorkExperience]:
        result = await self.session.execute(select(WorkExperience))
        return list(result.scalars().all())
    
    async def create_work_experience(self, data: WorkExperienceCreate) -> WorkExperience:
        work_experience = WorkExperience(**data.model_dump())
        self.session.add(work_experience)
        try:
            await self.session.commit()
            await self.session.refresh(work_experience)
        except Exception as e:
            await self.session.rollback()
            raise ValueError(f"Error creating work experience: {str(e)}")
        return work_experience
    
    async def update_work_experience(self, data: WorkExperienceUpdate) -> WorkExperience:
        work_experience = await self.session.get(WorkExperience, data.id)
        if not work_experience:
            raise ValueError("Work experience record does not exist")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(work_experience, field, value)

        self.session.add(work_experience)
        try:
            await self.session.commit()
            await self.session.refresh(work_experience)
        except Exception as e:
            await self.session.rollback()
            raise ValueError(f"Error updating work experience: {str(e)}")
        return work_experience
    
    async def delete_work_experience(self, work_experience_id ) -> None:
        work_experience = await self.session.get(WorkExperience, work_experience_id)
        if not work_experience:
            raise ValueError("Work experience record does not exist")

        await self.session.delete(work_experience)
        try:
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise ValueError(f"Error deleting work experience: {str(e)}")


# ----------------------------------------
# 🔹 skill category service
# ----------------------------------------

    async def get_skill_categories(self) -> list[SkillCategory]:
        result = await self.session.execute(select(SkillCategory))
        return list(result.scalars().all())

    async def create_skill_category(self, data: SkillCategoryCreate) -> SkillCategory:
        category = SkillCategory(name=data.name)
        self.session.add(category)
        try:
            await self.session.commit()
            await self.session.refresh(category)
        except Exception as e:
            await self.session.rollback()
            raise ValueError(f"Error creating category: {str(e)}")
        return category

    async def update_skill_category(self, data: SkillCategoryUpdate) -> SkillCategory:
        category = await self.session.get(SkillCategory, data.id)
        if not category:
            raise ValueError("Skill category record does not exist")
        category.name = data.name
        self.session.add(category)
        try:
            await self.session.commit()
            await self.session.refresh(category)
        except Exception as e:
            await self.session.rollback()
            raise ValueError(f"Error updating category: {str(e)}")
        return category

    async def delete_skill_category(self, category_id: UUID) -> None:
        category = await self.session.get(SkillCategory, category_id)
        if not category:
            raise ValueError("Skill category record does not exist")
        # Set category_id to None for all skills in this category
        skills = await self.session.execute(select(Skill).where(Skill.category_id == category_id))
        for skill in skills.scalars().all():
            skill.category_id = None 
            self.session.add(skill)
        await self.session.delete(category)
        try:
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise ValueError(f"Error deleting category: {str(e)}")


# ----------------------------------------
# 🔹 skills service
# ----------------------------------------

    async def create_skill(self, data: SkillCreate, skill_image: UploadFile | None) -> Skill:
        skill = Skill(
            name=data.name,
            category_id=data.category_id
        )
        if skill_image:
            skill.image_id = await upload_to_gridfs(self.skill_bucket, skill_image)
        self.session.add(skill)
        try:
            await self.session.commit()
            await self.session.refresh(skill)
        except Exception as e:
            await self.session.rollback()
            raise ValueError(f"Error creating skill: {str(e)}")
        return skill

    async def update_skill(self, data: SkillUpdate, skill_image: UploadFile | None) -> Skill:
        skill = await self.session.get(Skill, data.id)
        if not skill:
            raise ValueError("Skill record does not exist")

        update_data = data.model_dump(exclude_unset=True)
        if "name" in update_data:
            skill.name = update_data["name"]
        if "category_id" in update_data:
            skill.category_id = update_data["category_id"]

        if skill_image:
            if skill.image_id:
                await delete_from_gridfs(self.skill_bucket, skill.image_id)
            skill.image_id = await upload_to_gridfs(self.skill_bucket, skill_image)

        self.session.add(skill)
        try:
            await self.session.commit()
            await self.session.refresh(skill)
        except Exception as e:
            await self.session.rollback()
            raise ValueError(f"Error updating skill: {str(e)}")
        return skill

    async def delete_skill(self, skill_id: UUID) -> None:
        skill = await self.session.get(Skill, skill_id)
        if not skill:
            raise ValueError("Skill record does not exist")

        if skill.image_id:
            await delete_from_gridfs(self.skill_bucket, skill.image_id)

        await self.session.delete(skill)
        try:
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise ValueError(f"Error deleting skill: {str(e)}")

    async def get_skill_with_details(self, skill: Skill) -> dict:
        image_data = None
        if skill.image_id:
            try:
                stream = await self.skill_bucket.open_download_stream(ObjectId(skill.image_id))
                content: bytes = await stream.read()
                image_data = base64.b64encode(content).decode("utf-8")
            except Exception:
                image_data = None

        category_name = None
        if skill.category_id:
            category = await self.session.get(SkillCategory, skill.category_id)
            if category:
                category_name = category.name

        skill_dict = skill.model_dump() if hasattr(skill, "model_dump") else skill.__dict__
        skill_dict["image_base64"] = image_data
        skill_dict["category_name"] = category_name
        return skill_dict

    async def get_skills_with_details(self) -> list[dict]:
        """Get all skills with their category details and images."""
        try:
            # Get all skills with joined category information
            query = select(Skill)
            result = await self.session.execute(query)
            skills = result.scalars().all()

            # Process each skill to include category name and image
            skills_with_details = []
            for skill in skills:
                skill_details = await self.get_skill_with_details(skill)
                skills_with_details.append(skill_details)

            return skills_with_details

        except Exception as e:
            raise ValueError(f"Error fetching skills: {str(e)}")

    async def get_skill_by_id(self, skill_id: UUID) -> Optional[Skill]:
        """Get a skill by its ID."""
        try:
            skill = await self.session.get(Skill, skill_id)
            return skill
        except Exception as e:
            raise ValueError(f"Error fetching skill: {str(e)}")

