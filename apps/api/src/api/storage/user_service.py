"""
User service for database operations
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from typing import Optional, List
from .models import UserModel
from pydantic import BaseModel


class UserCreateData(BaseModel):
    email: str
    name: Optional[str] = None
    hashed_password: Optional[str] = None
    google_id: Optional[str] = None
    passkey_credential_id: Optional[str] = None
    passkey_public_key: Optional[str] = None


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_user(self, user_data: UserCreateData, flush_only: bool = False) -> Optional[UserModel]:
        """Create a new user"""
        try:
            user = UserModel(
                email=user_data.email,
                name=user_data.name,
                hashed_password=user_data.hashed_password,
                google_id=user_data.google_id,
                passkey_credential_id=user_data.passkey_credential_id,
                passkey_public_key=user_data.passkey_public_key,
            )
            self.session.add(user)
            if flush_only:
                await self.session.flush()
            else:
                await self.session.commit()
            await self.session.refresh(user)
            return user
        except IntegrityError:
            await self.session.rollback()
            return None

    async def get_user_by_id(self, user_id: str) -> Optional[UserModel]:
        """Get user by ID"""
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[UserModel]:
        """Get user by email"""
        result = await self.session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        return result.scalar_one_or_none()

    async def get_user_by_google_id(self, google_id: str) -> Optional[UserModel]:
        """Get user by Google ID"""
        result = await self.session.execute(
            select(UserModel).where(UserModel.google_id == google_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_passkey_credential_id(
        self, credential_id: str
    ) -> Optional[UserModel]:
        """Get user by passkey credential ID"""
        result = await self.session.execute(
            select(UserModel).where(UserModel.passkey_credential_id == credential_id)
        )
        return result.scalar_one_or_none()

    async def update_user_last_login(self, user_id: str, flush_only: bool = False) -> bool:
        """Update user's last login timestamp"""
        try:
            from sqlalchemy import func

            result = await self.session.execute(
                update(UserModel)
                .where(UserModel.id == user_id)
                .values(last_login=func.now())
            )
            if flush_only:
                await self.session.flush()
            else:
                await self.session.commit()
            return result.rowcount > 0
        except Exception:
            await self.session.rollback()
            return False

    async def update_user(self, user_id: str, flush_only: bool = False, **kwargs) -> Optional[UserModel]:
        """Update user fields"""
        try:
            result = await self.session.execute(
                update(UserModel)
                .where(UserModel.id == user_id)
                .values(**kwargs)
                .returning(UserModel)
            )
            if flush_only:
                await self.session.flush()
            else:
                await self.session.commit()
            return result.scalar_one_or_none()
        except Exception:
            await self.session.rollback()
            return None

    async def delete_user(self, user_id: str) -> bool:
        """Delete user"""
        try:
            user = await self.get_user_by_id(user_id)
            if user:
                await self.session.delete(user)
                await self.session.commit()
                return True
            return False
        except Exception:
            await self.session.rollback()
            return False

    async def get_all_users(self) -> List[UserModel]:
        """Get all users (admin function)"""
        result = await self.session.execute(select(UserModel))
        return result.scalars().all()
