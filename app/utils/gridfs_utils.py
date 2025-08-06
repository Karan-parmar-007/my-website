from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
from fastapi import UploadFile
from bson import ObjectId


def get_gridfs_bucket(mongo: AsyncIOMotorDatabase) -> AsyncIOMotorGridFSBucket:
    return AsyncIOMotorGridFSBucket(mongo)


async def upload_to_gridfs(mongo: AsyncIOMotorDatabase, file: UploadFile) -> str:
    fs = get_gridfs_bucket(mongo)
    filename = file.filename or "default_filename"
    contents = await file.read()
    file_id = await fs.upload_from_stream(
        filename, contents, metadata={"content_type": file.content_type}
    )
    return str(file_id)


async def delete_from_gridfs(mongo: AsyncIOMotorDatabase, file_id: str) -> None:
    fs = get_gridfs_bucket(mongo)
    try:
        await fs.delete(ObjectId(file_id))
    except Exception:
        pass  # Optionally log the error
