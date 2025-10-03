from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
from fastapi import UploadFile
from bson import ObjectId


def get_gridfs_bucket(mongo: AsyncIOMotorDatabase, bucket_name: str = "fs") -> AsyncIOMotorGridFSBucket:
    return AsyncIOMotorGridFSBucket(mongo, bucket_name=bucket_name)


async def upload_to_gridfs(bucket: AsyncIOMotorGridFSBucket, file: UploadFile) -> str:
    filename = file.filename or "default_filename"
    contents = await file.read()
    file_id = await bucket.upload_from_stream(
        filename, contents, metadata={"content_type": file.content_type}
    )
    return str(file_id)


async def delete_from_gridfs(bucket: AsyncIOMotorGridFSBucket, file_id: str) -> None:
    try:
        await bucket.delete(ObjectId(file_id))
    except Exception:
        pass  # Optionally log the error
