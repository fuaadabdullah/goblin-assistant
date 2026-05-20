#!/usr/bin/env python3
"""
Database initialization script for goblin-assistant.
Creates all database tables defined in models.py.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add the current directory to the Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Set up environment
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///./goblin_assistant.db')

try:
    # Import database components
    from api.storage.database import engine
    from api.storage.models import Base, UserModel, ConversationModel, MessageModel
    
    async def init_database():
        """Create all database tables."""
        try:
            print("Creating database tables...")
            print(f"Using database URL: {os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///./goblin_assistant.db')}")
            
            # For async engines, we need to use async operations
            # Create a synchronous engine for table creation
            from sqlalchemy import create_engine
            sync_url = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///./goblin_assistant.db')
            
            # Convert async URL to sync URL if needed
            if sync_url.startswith('sqlite+aiosqlite://'):
                sync_url = sync_url.replace('sqlite+aiosqlite://', 'sqlite://')
            elif sync_url.startswith('postgresql+asyncpg://'):
                sync_url = sync_url.replace('postgresql+asyncpg://', 'postgresql://')
            
            sync_engine = create_engine(sync_url)
            
            # Create tables
            Base.metadata.create_all(bind=sync_engine)
            print("✅ Database tables created successfully!")
            print("Tables created:")
            print("  - users")
            print("  - conversations") 
            print("  - messages")
            return True
        except Exception as e:
            print(f"❌ Error creating database tables: {e}")
            import traceback
            traceback.print_exc()
            return False

    def main():
        """Main function."""
        try:
            success = asyncio.run(init_database())
            return 0 if success else 1
        except ImportError as e:
            print(f"❌ Import error: {e}")
            print("Make sure you're running this from the goblin-assistant directory")
            print("Required modules: api.storage.database, api.storage.models")
            return 1

    if __name__ == "__main__":
        exit_code = main()
        sys.exit(exit_code)
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the goblin-assistant directory")
    print("Required modules: api.storage.database, api.storage.models")
    sys.exit(1)