from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.routes.v1.portfolio.models import ProfileInfo, Education, WorkExperience
from app.api.routes.v1.portfolio.schemas import ProfileInfoCreate, ProfileInfoUpdate
from app.api.routes.v1.portfolio.schemas import EducatioCreate, EducationRead, EducationUpdate
from app.api.routes.v1.portfolio.schemas import WorkExperienceCreate, WorkExperienceRead, WorkExperienceUpdate
from app.utils.gridfs_utils import upload_to_gridfs, delete_from_gridfs


class PortfolioService:
    def __init__(self, session: AsyncSession, mongo: AsyncIOMotorDatabase):
        self.session = session
        self.mongo = mongo

# ----------------------------------------
# 🔹 Profile service
# ----------------------------------------

    def _get_gridfs_bucket(self) -> AsyncIOMotorGridFSBucket:
        return AsyncIOMotorGridFSBucket(self.mongo)

    async def get_profile_info(self) -> ProfileInfo | None:
        result = await self.session.execute(select(ProfileInfo).limit(1))
        return result.scalars().first()

    async def create_profile_info(self, data: ProfileInfoCreate, file: UploadFile | None = None) -> ProfileInfo:
        profile = ProfileInfo(**data.model_dump())
        if file:
            profile.profile_image_id = await upload_to_gridfs(self.mongo, file)
        self.session.add(profile)
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def update_profile_info(self, data: ProfileInfoUpdate, file: UploadFile | None = None) -> ProfileInfo:
        profile = await self.get_profile_info()
        if not profile:
            raise ValueError("Profile does not exist")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(profile, field, value)

        if file:
            if profile.profile_image_id:
                await delete_from_gridfs(self.mongo, profile.profile_image_id)
            profile.profile_image_id = await upload_to_gridfs(self.mongo, file)

        self.session.add(profile)
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def delete_profile_info(self) -> None:
        profile = await self.get_profile_info()
        if not profile:
            raise ValueError("Profile does not exist")

        if profile.profile_image_id:
            await delete_from_gridfs(self.mongo, profile.profile_image_id)

        await self.session.delete(profile)
        await self.session.commit()


# ----------------------------------------
# 🔹 education service
# ----------------------------------------


    async def get_education(self) -> list[Education]:
        result = await self.session.execute(select(Education))
        return list(result.scalars().all())

    async def create_education(self, data: EducatioCreate) -> Education:
        education = Education(**data.model_dump())
        self.session.add(education)
        await self.session.commit()
        await self.session.refresh(education)
        return education

    async def update_education(self, data: EducationUpdate) -> Education:
        education = await self.session.get(Education, data.id)
        if not education:
            raise ValueError("Education record does not exist")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(education, field, value)

        self.session.add(education)
        await self.session.commit()
        await self.session.refresh(education)
        return education
    
    async def delete_education(self, education_id ) -> None:
        education = await self.session.get(Education, education_id)
        if not education:
            raise ValueError("Education record does not exist")

        await self.session.delete(education)
        await self.session.commit()


# ----------------------------------------
# 🔹 WorkExperince service
# ----------------------------------------

    async def get_work_experience(self) -> list[WorkExperience]:
        result = await self.session.execute(select(WorkExperience))
        return list(result.scalars().all())
    
    async def create_work_experience(self, data: WorkExperienceCreate) -> WorkExperience:
        work_experience = WorkExperience(**data.model_dump())
        self.session.add(work_experience)
        await self.session.commit()
        await self.session.refresh(work_experience)
        return work_experience
    
    async def update_work_experience(self, data: WorkExperienceUpdate) -> WorkExperience:
        work_experience = await self.session.get(WorkExperience, data.id)
        if not work_experience:
            raise ValueError("Work experience record does not exist")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(work_experience, field, value)

        self.session.add(work_experience)
        await self.session.commit()
        await self.session.refresh(work_experience)
        return work_experience
    
    async def delete_work_experience(self, work_experience_id ) -> None:
        work_experience = await self.session.get(WorkExperience, work_experience_id)
        if not work_experience:
            raise ValueError("Work experience record does not exist")

        await self.session.delete(work_experience)
        await self.session.commit()
    
    