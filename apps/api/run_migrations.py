#!/usr/bin/env python3
"""
Database migration script for semantic retrieval layer
Run this script to apply all necessary migrations for the vector database setup
"""

import os
import sys
import asyncio
import subprocess
from pathlib import Path


def check_environment():
    """Check if the environment is properly configured"""
    print("🔍 Checking environment...")
    
    # Check if we're in the right directory
    if not os.path.exists("alembic.ini"):
        print("❌ Error: Not in the goblin-assistant directory")
        print("Please run this script from the apps/goblin-assistant directory")
        return False
    
    # Check for database URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("⚠️  Warning: DATABASE_URL not set")
        print("Using default: sqlite+aiosqlite:///./goblin_assistant.db")
        os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./goblin_assistant.db"
    
    # Check for OpenAI API key
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("⚠️  Warning: OPENAI_API_KEY not set")
        print("Embedding generation will not work without this key")
    
    print("✅ Environment check complete")
    return True


def run_alembic_command(command: str):
    """Run an alembic command"""
    try:
        result = subprocess.run(
            ["alembic"] + command.split(),
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✅ Alembic command succeeded: {' '.join(command.split())}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Alembic command failed: {' '.join(command.split())}")
        print(f"Error: {e.stderr}")
        return False


async def create_initial_migration():
    """Create the initial migration if it doesn't exist"""
    print("\n📝 Checking for existing migrations...")
    
    versions_dir = Path("alembic/versions")
    if not versions_dir.exists():
        print("Creating alembic versions directory...")
        versions_dir.mkdir(parents=True)
    
    migration_files = list(versions_dir.glob("*.py"))
    
    if not migration_files:
        print("📋 No existing migrations found. Creating initial migration...")
        success = run_alembic_command("revision --autogenerate -m 'Initial database setup'")
        if not success:
            print("❌ Failed to create initial migration")
            return False
    else:
        print(f"📋 Found {len(migration_files)} existing migrations")
    
    return True


async def apply_migrations():
    """Apply all pending migrations"""
    print("\n🔄 Applying database migrations...")
    
    # Check current migration status
    print("Checking migration status...")
    success = run_alembic_command("current")
    
    # Apply migrations
    print("Applying migrations...")
    success = run_alembic_command("upgrade head")
    
    if success:
        print("✅ All migrations applied successfully")
    else:
        print("❌ Migration failed")
        return False
    
    return True


async def verify_vector_setup():
    """Verify that the vector setup is correct"""
    print("\n🔍 Verifying vector database setup...")
    
    try:
        # Import and test the vector models
        sys.path.insert(0, os.path.dirname(__file__))
        
        from api.storage.database import get_db, init_db
        from api.storage.vector_models import EmbeddingModel, ConversationSummaryModel, MemoryFactModel
        
        await init_db()
        
        async with get_db() as session:
            # Check if vector tables exist
            result = await session.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('embeddings', 'conversation_summaries', 'memory_facts')
            """)
            tables = [row[0] for row in result.fetchall()]
            
            expected_tables = {'embeddings', 'conversation_summaries', 'memory_facts'}
            found_tables = set(tables)
            
            if expected_tables.issubset(found_tables):
                print("✅ Vector tables verified")
            else:
                missing = expected_tables - found_tables
                print(f"❌ Missing vector tables: {missing}")
                return False
            
            # Check pgvector extension (only for PostgreSQL)
            if 'postgresql' in os.getenv("DATABASE_URL", ""):
                result = await session.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_extension WHERE extname = 'vector'
                    ) as has_vector
                """)
                has_vector = result.fetchone()[0]
                
                if has_vector:
                    print("✅ pgvector extension verified")
                else:
                    print("❌ pgvector extension not found")
                    print("Please install pgvector: CREATE EXTENSION vector;")
                    return False
            else:
                print("ℹ️  Using SQLite - pgvector extension not applicable")
            
            print("✅ Vector database setup verification complete")
            return True
            
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


def print_next_steps():
    """Print instructions for next steps"""
    print("\n🎯 Next Steps:")
    print("=" * 50)
    print("1. Test the semantic retrieval layer:")
    print("   python test_semantic_retrieval.py")
    print()
    print("2. Start the backend server:")
    print("   python api/main.py")
    print()
    print("3. Test the API endpoints:")
    print("   curl -X POST http://localhost:8000/semantic-chat/conversations/{conversation_id}/messages \\")
    print("        -H 'Content-Type: application/json' \\")
    print("        -d '{\"message\": \"Hello, test the semantic retrieval!\"}'")
    print()
    print("4. Monitor the embedding worker and background tasks in logs")
    print()
    print("📚 API Documentation:")
    print("- Semantic Chat: /docs#/semantic-chat")
    print("- Context Retrieval: /semantic-chat/conversations/{id}/context")
    print("- Memory Management: /semantic-chat/users/{id}/memory")


async def main():
    """Main migration runner"""
    print("🚀 Semantic Retrieval Layer - Database Migration")
    print("=" * 60)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Create initial migration if needed
    if not await create_initial_migration():
        sys.exit(1)
    
    # Apply migrations
    if not await apply_migrations():
        sys.exit(1)
    
    # Verify setup
    if not await verify_vector_setup():
        print("\n⚠️  Setup verification failed, but migrations may still be correct")
    
    # Print next steps
    print_next_steps()
    
    print("\n🎉 Migration complete! The semantic retrieval layer is ready to use.")


if __name__ == "__main__":
    asyncio.run(main())