#!/usr/bin/env python3
"""
Simple authentication service for Goblin Assistant
Bypasses complex dependencies to provide basic auth functionality
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional
import jwt
import bcrypt
import sqlite3
import os
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

# Simple in-memory user store for development
users_db = {}

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    id: str
    email: str
    name: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

# JWT Configuration
SECRET_KEY = "d83658baa582a323a3485480c063b4f32d32dfbd13a09af3172f07ff5e5350ec"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting Simple Auth Server...")
    yield
    # Shutdown
    print("🛑 Shutting down Simple Auth Server...")

app = FastAPI(
    title="Goblin Assistant Auth",
    description="Simple authentication service",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3002", "http://127.0.0.1:3002"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Goblin Assistant Auth API", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "auth"}

@app.post("/auth/register", response_model=Token)
async def register(user_data: UserCreate):
    # Check if user already exists
    if user_data.email in users_db:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create new user
    user_id = f"user_{len(users_db) + 1}"
    hashed_password = hash_password(user_data.password)
    
    users_db[user_data.email] = {
        "id": user_id,
        "email": user_data.email,
        "name": user_data.name,
        "hashed_password": hashed_password
    }

    # Create user object
    user = User(id=user_id, email=user_data.email, name=user_data.name)

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_id}, expires_delta=access_token_expires
    )

    return Token(access_token=access_token, token_type="bearer", user=user)

@app.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin):
    # Find user by email
    user_record = users_db.get(user_data.email)
    if not user_record:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Verify password
    if not verify_password(user_data.password, user_record["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Create user object
    user = User(
        id=user_record["id"],
        email=user_record["email"],
        name=user_record["name"]
    )

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_record["id"]}, expires_delta=access_token_expires
    )

    return Token(access_token=access_token, token_type="bearer", user=user)

@app.get("/auth/me", response_model=User)
async def get_current_user():
    # For demo purposes, return the first user
    if users_db:
        first_user = next(iter(users_db.values()))
        return User(id=first_user["id"], email=first_user["email"], name=first_user["name"])
    else:
        raise HTTPException(status_code=404, detail="No users found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)