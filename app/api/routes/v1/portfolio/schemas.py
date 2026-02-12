from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from fastapi import UploadFile, Form, File
from datetime import date


# ----------------------------------------
# 🔹 Profile
# ----------------------------------------

class ProfileInfoRead(BaseModel):
    id: UUID
    name: str
    about: Optional[str]
    headline: Optional[str]
    email: EmailStr
    phone: Optional[str]
    location: Optional[str]
    has_profile_image: bool = False
    has_resume: bool = False

    class Config:
        from_attributes = True

class ProfileInfoCreate(BaseModel):
    name: str
    about: Optional[str] = None
    headline: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None
    location: Optional[str] = None

class ProfileInfoUpdate(BaseModel):
    name: Optional[str] = None
    about: Optional[str] = None
    headline: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    location: Optional[str] = None

class ProfileInfoCreateForm(BaseModel):
    name: str
    email: EmailStr
    about: Optional[str] = None
    headline: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None

    @classmethod
    def as_form(
        cls,
        name: str = Form(...),
        email: EmailStr = Form(...),
        about: Optional[str] = Form(None),
        headline: Optional[str] = Form(None),
        phone: Optional[str] = Form(None),
        location: Optional[str] = Form(None),
        profile_image: Optional[UploadFile] = File(None),
        resume_file: Optional[UploadFile] = File(None)
    ) -> tuple["ProfileInfoCreateForm", Optional[UploadFile], Optional[UploadFile]]:
        return cls(
            name=name,
            email=email,
            about=about,
            headline=headline,
            phone=phone,
            location=location
        ), profile_image, resume_file

class ProfileInfoUpdateForm(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    about: Optional[str] = None
    headline: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None


# ----------------------------------------
# 🔹 Social Media
# ----------------------------------------

class SocialMediaRead(BaseModel):
    id: UUID
    name: str
    link: str

    class Config:
        from_attributes = True

class SocialMediaCreate(BaseModel):
    name: str
    link: str

class SocialMediaUpdate(BaseModel):
    name: Optional[str] = None
    link: Optional[str] = None



# ----------------------------------------
# 🔹 Education
# ----------------------------------------

class EducationCreate(BaseModel):
    sequence: Optional[int] = None
    school: str
    degree: str
    start_year: int
    end_year: Optional[int] = None
    Score: Optional[float] = None
    description: Optional[str] = None

class EducationUpdate(BaseModel):
    id: UUID
    sequence: Optional[int] = None
    school: Optional[str] = None
    degree: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    Score: Optional[float] = None
    description: Optional[str] = None

class EducationRead(EducationCreate):
    id: UUID

    class Config:
        from_attributes = True

# ----------------------------------------
# 🔹 Work Expeerince
# ----------------------------------------


class WorkExperienceCreate(BaseModel):
    company: str
    sequence: int
    position: str
    start_date: date
    end_date: Optional[date] = None
    description: Optional[list[str]] = None

class WorkExperienceUpdate(BaseModel):
    id: UUID
    sequence: Optional[int] = None
    company: Optional[str] = None
    position: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[list[str]] = None

class WorkExperienceRead(WorkExperienceCreate):
    id: UUID

    class Config:
        from_attributes = True



# ----------------------------------------
# 🔹 Skill Category
# ----------------------------------------

class SkillCategoryRead(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True

class SkillCategoryCreate(BaseModel):
    name: str

class SkillCategoryUpdate(BaseModel):
    id: UUID
    name: str

# ----------------------------------------
# 🔹 Skills
# ----------------------------------------


class SkillRead(BaseModel):
    id: UUID
    name: str
    category_id: Optional[UUID] = None
    category_name: Optional[str] = None
    image_base64: Optional[str] = None

    class Config:
        from_attributes = True

class SkillCreate(BaseModel):
    name: str
    category_id: UUID

class SkillUpdate(BaseModel):
    id: UUID
    name: Optional[str] = None
    category_id: Optional[UUID] = None

class SkillCreateForm(SkillCreate):
    @classmethod
    def as_form(
        cls,
        name: str = Form(...),
        category_id: UUID = Form(...),
        skill_image: Optional[UploadFile] = File(None)
    ) -> tuple["SkillCreateForm", Optional[UploadFile]]:
        return cls(
            name=name,
            category_id=category_id
        ), skill_image

class SkillUpdateForm(SkillUpdate):
    @classmethod
    def as_form(
        cls,
        id: UUID = Form(...),
        name: Optional[str] = Form(None),
        category_id: Optional[UUID] = Form(None),
        skill_image: Optional[UploadFile] = File(None)
    ) -> tuple["SkillUpdateForm", Optional[UploadFile]]:
        data = {'id': id}
        if name is not None: data['name'] = name
        if category_id is not None: data['category_id'] = category_id
        
        return cls(**data), skill_image
