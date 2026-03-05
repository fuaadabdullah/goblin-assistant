#!/usr/bin/env python3
"""
Database configuration validation script for goblin-assistant.
Validates database setup, models, and environment configuration.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

def validate_environment():
    """Validate environment configuration."""
    print("🔍 Validating environment configuration...")
    
    # Check if .env file exists
    env_file = current_dir / ".env"
    if not env_file.exists():
        print("⚠️  No .env file found. Using default configuration.")
        print("   Consider copying .env.example to .env and customizing it.")
    
    # Validate database URL
    database_url = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///./goblin_assistant.db')
    print(f"   Database URL: {database_url}")
    
    # Check for common issues
    if "password" in database_url.lower() and "@" in database_url:
        print("⚠️  Warning: Database URL contains password. Ensure this is not logged in production.")
    
    if database_url.startswith("postgres://"):
        print("⚠️  Warning: Using deprecated postgres:// URL. Consider using postgresql+asyncpg://")
    
    return True

def validate_imports():
    """Validate that all required modules can be imported."""
    print("🔍 Validating imports...")
    
    try:
        from api.storage.database import engine, get_db
        print("   ✅ Database module imported successfully")
    except ImportError as e:
        print(f"   ❌ Failed to import database module: {e}")
        return False
    
    try:
        from api.storage.models import Base, UserModel, ConversationModel, MessageModel
        print("   ✅ Models imported successfully")
    except ImportError as e:
        print(f"   ❌ Failed to import models: {e}")
        return False
    
    try:
        from api.storage.conversations import ConversationStore
        print("   ✅ Conversation store imported successfully")
    except ImportError as e:
        print(f"   ⚠️  Failed to import conversation store: {e}")
        print("   This may be expected if the file doesn't exist yet.")
    
    return True

def validate_database_connection():
    """Validate database connection and table creation."""
    print("🔍 Validating database connection...")
    
    try:
        from api.storage.database import engine
        from sqlalchemy import inspect
        
        # Test connection using async context manager
        async def check_connection():
            async with engine.connect() as conn:
                print("   ✅ Database connection successful")
                
                # Check if tables exist using a simple query instead of inspector
                from sqlalchemy import text
                result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                tables = [row[0] for row in result]
                print(f"   Tables found: {tables}")
                
                # Expected tables
                expected_tables = ['users', 'conversations', 'messages']
                missing_tables = [table for table in expected_tables if table not in tables]
                
                if missing_tables:
                    print(f"   ⚠️  Missing tables: {missing_tables}")
                    print("   Run init_db.py to create missing tables")
                else:
                    print("   ✅ All expected tables are present")
        
        # Run the async function
        import asyncio
        asyncio.run(check_connection())
        return True
        
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        return False

async def validate_async_operations():
    """Validate async database operations."""
    print("🔍 Validating async operations...")
    
    try:
        from api.storage.database import get_db
        from api.storage.models import UserModel
        
        async with get_db() as session:
            # Test a simple query
            result = await session.execute("SELECT 1")
            print("   ✅ Async database operations working")
            return True
            
    except Exception as e:
        print(f"   ❌ Async operations failed: {e}")
        return False

def validate_models():
    """Validate database models."""
    print("🔍 Validating database models...")
    
    try:
        from api.storage.models import Base, UserModel, ConversationModel, MessageModel
        
        # Check if models are properly defined
        models = [UserModel, ConversationModel, MessageModel]
        
        for model in models:
            table_name = model.__tablename__
            print(f"   ✅ Model {model.__name__} has table name: {table_name}")
            
            # Check for primary key
            primary_keys = [col.name for col in model.__table__.primary_key.columns]
            if primary_keys:
                print(f"      Primary key: {primary_keys}")
            else:
                print("      ⚠️  No primary key found")
        
        # Check relationships
        conversation_model = ConversationModel
        if hasattr(conversation_model, 'user') and hasattr(conversation_model, 'messages'):
            print("   ✅ Relationships are properly defined")
        else:
            print("   ⚠️  Some relationships may be missing")
            
        return True
        
    except Exception as e:
        print(f"   ❌ Model validation failed: {e}")
        return False

def main():
    """Main validation function."""
    print("🚀 Starting database configuration validation...\n")
    
    # Change to the correct directory
    os.chdir(current_dir)
    
    validations = [
        validate_environment,
        validate_imports,
        validate_models,
        validate_database_connection,
    ]
    
    results = []
    for validation in validations:
        try:
            result = validation()
            results.append(result)
            print()
        except Exception as e:
            print(f"   ❌ Validation failed with exception: {e}")
            results.append(False)
            print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("=" * 50)
    print(f"Validation Summary: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All validations passed! Database configuration is ready.")
        return 0
    else:
        print("⚠️  Some validations failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)