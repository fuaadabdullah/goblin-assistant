"""
Supabase integration for PostgreSQL database and authentication
"""

import os
import json
from typing import Dict, Any, Optional, List
import asyncio
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from contextlib import asynccontextmanager
from typing import AsyncGenerator


# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# Database URL construction for Supabase
if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
    # Use Supabase connection string with service role key
    DATABASE_URL = f"postgresql+asyncpg://postgres:{SUPABASE_SERVICE_ROLE_KEY}@{SUPABASE_URL.replace('https://', '').replace('http://', '')}:5432/postgres"
else:
    DATABASE_URL = os.getenv(
        "DATABASE_URL", "sqlite+aiosqlite:///./goblin_assistant.db"
    )


class SupabaseAuth:
    """Supabase Authentication management"""

    def __init__(self):
        self.url = SUPABASE_URL
        self.anon_key = SUPABASE_ANON_KEY
        self.service_role_key = SUPABASE_SERVICE_ROLE_KEY
        self.api_url = f"{self.url}/auth/v1" if self.url else None

    async def create_user(
        self, email: str, password: str, metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create a new user"""
        if not self.api_url or not self.service_role_key:
            return {"error": "Supabase configuration missing"}

        headers = {
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
            "apikey": self.service_role_key,
        }

        data = {
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": metadata or {},
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.api_url}/admin/users",
                    headers=headers,
                    json=data,
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"Supabase API error: {response.status_code}"}
            except Exception as e:
                return {"error": f"Failed to create user: {str(e)}"}

    async def get_user(self, user_id: str) -> Dict[str, Any]:
        """Get user information"""
        if not self.api_url or not self.service_role_key:
            return {"error": "Supabase configuration missing"}

        headers = {
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
            "apikey": self.service_role_key,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.api_url}/admin/users/{user_id}",
                    headers=headers,
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"Supabase API error: {response.status_code}"}
            except Exception as e:
                return {"error": f"Failed to get user: {str(e)}"}

    async def verify_jwt_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token"""
        if not self.api_url or not self.anon_key:
            return {"error": "Supabase configuration missing"}

        headers = {
            "Authorization": f"Bearer {token}",
            "apikey": self.anon_key,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.api_url}/user",
                    headers=headers,
                )

                if response.status_code == 200:
                    return {"valid": True, "user": response.json()}
                else:
                    return {
                        "valid": False,
                        "error": f"Invalid token: {response.status_code}",
                    }
            except Exception as e:
                return {"valid": False, "error": f"Token verification failed: {str(e)}"}


class SupabaseDatabase:
    """Supabase Database operations"""

    def __init__(self):
        self.url = SUPABASE_URL
        self.service_role_key = SUPABASE_SERVICE_ROLE_KEY
        self.anon_key = SUPABASE_ANON_KEY
        self.rest_url = f"{self.url}/rest/v1" if self.url else None

    async def execute_query(self, table: str, query: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a raw SQL query"""
        if not self.rest_url or not self.service_role_key:
            return {"error": "Supabase configuration missing"}

        headers = {
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
            "apikey": self.service_role_key,
            "Prefer": "return=minimal",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.rest_url}/{table}",
                    headers=headers,
                    params=query,
                )

                if response.status_code == 200:
                    return {"data": response.json()}
                else:
                    return {"error": f"Supabase API error: {response.status_code}"}
            except Exception as e:
                return {"error": f"Query execution failed: {str(e)}"}

    async def insert_data(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert data into a table"""
        if not self.rest_url or not self.service_role_key:
            return {"error": "Supabase configuration missing"}

        headers = {
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
            "apikey": self.service_role_key,
            "Prefer": "return=representation",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.rest_url}/{table}",
                    headers=headers,
                    json=data,
                )

                if response.status_code == 201:
                    return {"data": response.json()}
                else:
                    return {"error": f"Supabase API error: {response.status_code}"}
            except Exception as e:
                return {"error": f"Insert failed: {str(e)}"}

    async def update_data(
        self, table: str, data: Dict[str, Any], filter_field: str, filter_value: str
    ) -> Dict[str, Any]:
        """Update data in a table"""
        if not self.rest_url or not self.service_role_key:
            return {"error": "Supabase configuration missing"}

        headers = {
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
            "apikey": self.service_role_key,
            "Prefer": "return=representation",
        }

        params = {f"{filter_field}=eq.{filter_value}": ""}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.patch(
                    f"{self.rest_url}/{table}",
                    headers=headers,
                    params=params,
                    json=data,
                )

                if response.status_code == 200:
                    return {"data": response.json()}
                else:
                    return {"error": f"Supabase API error: {response.status_code}"}
            except Exception as e:
                return {"error": f"Update failed: {str(e)}"}

    async def delete_data(
        self, table: str, filter_field: str, filter_value: str
    ) -> Dict[str, Any]:
        """Delete data from a table"""
        if not self.rest_url or not self.service_role_key:
            return {"error": "Supabase configuration missing"}

        headers = {
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
            "apikey": self.service_role_key,
            "Prefer": "return=minimal",
        }

        params = {f"{filter_field}=eq.{filter_value}": ""}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.delete(
                    f"{self.rest_url}/{table}",
                    headers=headers,
                    params=params,
                )

                if response.status_code == 204:
                    return {"success": True}
                else:
                    return {"error": f"Supabase API error: {response.status_code}"}
            except Exception as e:
                return {"error": f"Delete failed: {str(e)}"}


class SupabaseStorage:
    """Supabase Storage management"""

    def __init__(self):
        self.url = SUPABASE_URL
        self.service_role_key = SUPABASE_SERVICE_ROLE_KEY
        self.storage_url = f"{self.url}/storage/v1" if self.url else None

    async def upload_file(
        self,
        bucket: str,
        path: str,
        file_data: bytes,
        content_type: str = "application/octet-stream",
    ) -> Dict[str, Any]:
        """Upload a file to storage"""
        if not self.storage_url or not self.service_role_key:
            return {"error": "Supabase configuration missing"}

        headers = {
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": content_type,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.storage_url}/object/{bucket}/{path}",
                    headers=headers,
                    content=file_data,
                )

                if response.status_code == 200:
                    return {"data": response.json()}
                else:
                    return {"error": f"Supabase Storage error: {response.status_code}"}
            except Exception as e:
                return {"error": f"Upload failed: {str(e)}"}

    async def get_file_url(self, bucket: str, path: str) -> Dict[str, Any]:
        """Get public URL for a file"""
        if not self.storage_url:
            return {"error": "Supabase configuration missing"}

        # Generate signed URL for private files or return public URL
        return {
            "url": f"{self.storage_url}/object/public/{bucket}/{path}",
            "bucket": bucket,
            "path": path,
        }


# Create database engine
if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
    # Use Supabase with connection pooling
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
    )
else:
    # Fallback to local SQLite
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )


# Create session factory
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional scope around a series of operations."""
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def init_db():
    """Initialize database tables"""
    from .models import Base

    async with engine.begin() as conn:
        # Create tables if they don't exist
        await conn.run_sync(Base.metadata.create_all)


# Global instances
supabase_auth = SupabaseAuth()
supabase_db = SupabaseDatabase()
supabase_storage = SupabaseStorage()


def get_supabase_config() -> Dict[str, Any]:
    """Get Supabase configuration"""
    return {
        "url": bool(SUPABASE_URL),
        "service_role_key": bool(SUPABASE_SERVICE_ROLE_KEY),
        "anon_key": bool(SUPABASE_ANON_KEY),
        "database_url": bool(DATABASE_URL),
        "enabled": bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY),
    }
