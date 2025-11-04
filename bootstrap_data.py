import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import select
from uuid import UUID

from app.config import db_settings
from app.api.routes.v1.user.models import UserRole, Permission, RolePermission, Users
from app.api.routes.v1.portfolio.models import ProfileInfo
from app.utils.security import hash_password


async def bootstrap_data():
    """Bootstrap initial data: roles, permissions, super admin user, and portfolio info"""
    
    # Create async engine
    engine = create_async_engine(db_settings.POSTGRES_URL, echo=True)
    
    # Create async session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        try:
            # Check if super_admin role already exists
            result = await session.execute(
                select(UserRole).where(UserRole.name == "super_admin")
            )
            existing_role = result.scalar_one_or_none()
            
            if existing_role:
                print("ℹ️ super_admin role already exists. Skipping bootstrap.")
                print("🎉 Bootstrap check completed - no changes needed!")
                return
            
            # 1. Create super_admin role
            super_admin_role = UserRole(
                name="super_admin",
                description="owner"
            )
            session.add(super_admin_role)
            await session.flush()
            print(f"✅ Created super_admin role: {super_admin_role.id}")
            
            # 2. Define and create permissions
            permissions_data = [
                ("edit_portfolio", "All portfolio access, edit, delete and post"),
                ("edit_work_experience", "All work experience access, edit, delete and post"),
                ("edit_education", "All education access, edit, delete and post"),
                ("edit_skill_categories", "All Skill category access, edit, delete and post"),
                ("edit_skills", "All Skill access, edit, delete and post"),
                ("edit_projects", "edit project permission"),
                ("edit_user", "edit user info with this permission"),
                ("add_permission", "add permissions"),
                ("add_user", "add new user"),
                ("delete_user", "delete user"),
            ]
            
            created_permissions = []
            
            for perm_name, perm_desc in permissions_data:
                permission = Permission(
                    name=perm_name,
                    description=perm_desc
                )
                session.add(permission)
                await session.flush()
                print(f"✅ Created permission: {perm_name}")
                created_permissions.append(permission)
            
            # 3. Create RolePermission relationships
            for permission in created_permissions:
                role_permission = RolePermission(
                    role_id=super_admin_role.id,
                    permission_id=permission.id
                )
                session.add(role_permission)
                print(f"✅ Linked permission '{permission.name}' to super_admin")
            
            # 4. Create super admin user
            hashed_password = hash_password("Karan#01")
            super_admin_user = Users(
                preferred_name="Karan",
                email="karan.ai.engineer@gmail.com",
                password_hash=hashed_password,
                role_id=super_admin_role.id,
                email_verified=True
            )
            session.add(super_admin_user)
            await session.flush()
            print(f"✅ Created super admin user: {super_admin_user.email}")
            
            # 5. Create profile information
            profile_info = ProfileInfo(
                name="Karan Parmar",
                email="karan.ai.engineer@gmail.com",
                phone="+918793759908",
                headline="AI & ML: Engineering the Next-Gen Backend.",
                about=(
                    "AI/ML Engineer who builds and deploys scalable applications using Python, "
                    "FastAPI/Django/Flask, and cloud platforms like AWS. My expertise centers on "
                    "Deep Learning and LLM integration (Llama, OpenAI, Mistral), where I have "
                    "hands-on experience fine-tuning models and integrating APIs like Gemini into "
                    "production systems. I'm passionate about delivering production-ready solutions; "
                    "in my experience, I have improved system efficiency by 1.5x and reduced costs by "
                    "7% through scalable backend automation, and I consistently automate AWS/DigitalOcean "
                    "deployment pipelines using Docker and CI/CD. I am focused on leveraging data-driven "
                    "insights to develop features and tackle complex problems, such as building machine "
                    "learning models for credit card fraud detection and leading full-stack projects that "
                    "significantly boost feature engagement."
                ),
                github_url="https://github.com/Karan-parmar-007",
                linkedin_url="https://www.linkedin.com/in/karan-parmar-715ab7225",
                instagram="https://www.instagram.com/karan_parmar014/"
            )
            session.add(profile_info)
            await session.flush()
            print(f"✅ Created profile information for: {profile_info.name}")
            
            # Commit all changes
            await session.commit()
            print("\n🎉 Bootstrap completed successfully!")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error during bootstrap: {e}")
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(bootstrap_data())