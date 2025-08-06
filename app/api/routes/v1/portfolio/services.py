from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.routes.v1.portfolio.models import ProfileInfo
from app.api.routes.v1.portfolio.schemas import ProfileInfoCreate, ProfileInfoUpdate
from app.utils.gridfs_utils import upload_to_gridfs, delete_from_gridfs



class PortfolioService:
    def __init__(self, session: AsyncSession, mongo: AsyncIOMotorDatabase):
        self.session = session
        self.mongo = mongo

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
