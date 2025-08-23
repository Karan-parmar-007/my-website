from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from fastapi import UploadFile
from datetime import date


# ----------------------------------------
# 🔹 Profile
# ----------------------------------------

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
    profile_image_base64: Optional[str] = None  

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



# ----------------------------------------
# 🔹 Education
# ----------------------------------------

class EducatioCreate(BaseModel):
    school: str
    degree: str
    start_year: int
    end_year: Optional[int] = None
    Score: Optional[float] = None
    description: Optional[str] = None

class EducationUpdate(BaseModel):
    id: UUID
    school: Optional[str] = None
    degree: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    Score: Optional[float] = None
    description: Optional[str] = None

class EducationRead(EducatioCreate):
    id: UUID

    class Config:
        from_attributes = True

# ----------------------------------------
# 🔹 Work Expeerince
# ----------------------------------------


class WorkExperienceCreate(BaseModel):
    company: str
    position: str
    start_date: date
    end_date: Optional[date] = None
    description: Optional[list[str]] = None

class WorkExperienceUpdate(BaseModel):
    id: UUID
    company: Optional[str] = None
    position: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[list[str]] = None

class WorkExperienceRead(WorkExperienceCreate):
    id: UUID

    class Config:
        from_attributes = True


