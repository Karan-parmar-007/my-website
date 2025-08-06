from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from fastapi import UploadFile


class ProfileInfoRead(BaseModel):
    id: UUID
    name: str
    about: Optional[str]
    email: EmailStr
    phone: Optional[str]
    location: Optional[str]
    github_url: Optional[str]
    linkedin_url: Optional[str]
    resume_url: Optional[str]
    instagram: Optional[str]
    profile_image_base64: Optional[str] = None  # <-- Add this line

    class Config:
        from_attributes = True

class ProfileInfoCreate(BaseModel):
    name: str
    about: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None
    location: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    resume_url: Optional[str] = None
    instagram: Optional[str] = None


class ProfileInfoUpdate(BaseModel):
    name: Optional[str] = None
    about: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    resume_url: Optional[str] = None
    instagram: Optional[str] = None



class ProfileInfoCreateForm(ProfileInfoCreate):
    profile_image: Optional[UploadFile] = None

class ProfileInfoUpdateForm(ProfileInfoUpdate):
    profile_image: Optional[UploadFile] = None