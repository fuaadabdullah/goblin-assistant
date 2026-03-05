#!/usr/bin/env python3
"""
Database testing script for goblin-assistant.
Tests database connection, CRUD operations, and initialization.
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Add current directory to path
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

async def test_database_connection():
    """Test database connection and basic operations."""
    print("🔍 Testing database connection...")
    
    try:
        from api.storage.database import get_db, engine
        from api.storage.models import UserModel, ConversationModel, MessageModel
        
        # Test connection
        async with get_db() as session:
            # Test a simple query
            result = await session.execute("SELECT 1 as test")
            test_value = result.scalar()
            print(f"   ✅ Database connection successful (test value: {test_value})")
            
            return True
            
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_user_operations():
    """Test user CRUD operations."""
    print("🔍 Testing user operations...")
    
    try:
        from api.storage.database import get_db
        from api.storage.models import UserModel
        import uuid
        
        async with get_db() as session:
            # Create a test user
            test_user = UserModel(
                id=str(uuid.uuid4()),
                email="test@example.com",
                name="Test User",
                hashed_password="test_hash",
                created_at=datetime.utcnow()
            )
            
            session.add(test_user)
            await session.commit()
            print("   ✅ User created successfully")
            
            # Retrieve the user
            result = await session.execute(
                "SELECT * FROM users WHERE email = :email",
                {"email": "test@example.com"}
            )
            user = result.fetchone()
            
            if user:
                print(f"   ✅ User retrieved successfully: {user[1]}")
                
                # Clean up
                await session.execute(
                    "DELETE FROM users WHERE email = :email",
                    {"email": "test@example.com"}
                )
                await session.commit()
                print("   ✅ User cleanup successful")
                return True
            else:
                print("   ❌ User not found after creation")
                return False
                
    except Exception as e:
        print(f"   ❌ User operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_conversation_operations():
    """Test conversation CRUD operations."""
    print("🔍 Testing conversation operations...")
    
    try:
        from api.storage.database import get_db
        from api.storage.models import ConversationModel
        import uuid
        
        async with get_db() as session:
            # Create a test conversation
            test_conversation = ConversationModel(
                conversation_id=str(uuid.uuid4()),
                title="Test Conversation",
                created_at=datetime.utcnow()
            )
            
            session.add(test_conversation)
            await session.commit()
            print("   ✅ Conversation created successfully")
            
            # Retrieve the conversation
            result = await session.execute(
                "SELECT * FROM conversations WHERE title = :title",
                {"title": "Test Conversation"}
            )
            conversation = result.fetchone()
            
            if conversation:
                print(f"   ✅ Conversation retrieved successfully: {conversation[1]}")
                
                # Clean up
                await session.execute(
                    "DELETE FROM conversations WHERE title = :title",
                    {"title": "Test Conversation"}
                )
                await session.commit()
                print("   ✅ Conversation cleanup successful")
                return True
            else:
                print("   ❌ Conversation not found after creation")
                return False
                
    except Exception as e:
        print(f"   ❌ Conversation operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_message_operations():
    """Test message CRUD operations."""
    print("🔍 Testing message operations...")
    
    try:
        from api.storage.database import get_db
        from api.storage.models import MessageModel
        import uuid
        
        async with get_db() as session:
            # Create a test message
            test_message = MessageModel(
                message_id=str(uuid.uuid4()),
                conversation_id=str(uuid.uuid4()),
                role="user",
                content="Test message content",
                timestamp=datetime.utcnow()
            )
            
            session.add(test_message)
            await session.commit()
            print("   ✅ Message created successfully")
            
            # Retrieve the message
            result = await session.execute(
                "SELECT * FROM messages WHERE content = :content",
                {"content": "Test message content"}
            )
            message = result.fetchone()
            
            if message:
                print(f"   ✅ Message retrieved successfully: {message[3]}")
                
                # Clean up
                await session.execute(
                    "DELETE FROM messages WHERE content = :content",
                    {"content": "Test message content"}
                )
                await session.commit()
                print("   ✅ Message cleanup successful")
                return True
            else:
                print("   ❌ Message not found after creation")
                return False
                
    except Exception as e:
        print(f"   ❌ Message operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_relationships():
    """Test model relationships."""
    print("🔍 Testing model relationships...")
    
    try:
        from api.storage.database import get_db
        from api.storage.models import UserModel, ConversationModel, MessageModel
        import uuid
        
        async with get_db() as session:
            # Create a user
            user_id = str(uuid.uuid4())
            test_user = UserModel(
                id=user_id,
                email="rel_test@example.com",
                name="Relationship Test User",
                created_at=datetime.utcnow()
            )
            session.add(test_user)
            await session.commit()
            
            # Create a conversation for the user
            conv_id = str(uuid.uuid4())
            test_conversation = ConversationModel(
                conversation_id=conv_id,
                user_id=user_id,
                title="Relationship Test Conversation",
                created_at=datetime.utcnow()
            )
            session.add(test_conversation)
            await session.commit()
            
            # Create a message for the conversation
            msg_id = str(uuid.uuid4())
            test_message = MessageModel(
                message_id=msg_id,
                conversation_id=conv_id,
                role="user",
                content="Relationship test message",
                timestamp=datetime.utcnow()
            )
            session.add(test_message)
            await session.commit()
            
            # Test relationship queries
            # Get conversation with user
            result = await session.execute(
                "SELECT c.title, u.name FROM conversations c JOIN users u ON c.user_id = u.id WHERE c.conversation_id = :conv_id",
                {"conv_id": conv_id}
            )
            conv_with_user = result.fetchone()
            
            if conv_with_user:
                print(f"   ✅ Relationship query successful: {conv_with_user[0]} by {conv_with_user[1]}")
                
                # Clean up
                await session.execute("DELETE FROM messages WHERE conversation_id = :conv_id", {"conv_id": conv_id})
                await session.execute("DELETE FROM conversations WHERE conversation_id = :conv_id", {"conv_id": conv_id})
                await session.execute("DELETE FROM users WHERE id = :user_id", {"user_id": user_id})
                await session.commit()
                print("   ✅ Relationship cleanup successful")
                return True
            else:
                print("   ❌ Relationship query failed")
                return False
                
    except Exception as e:
        print(f"   ❌ Relationship test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function."""
    print("🚀 Starting database tests...\n")
    
    # Change to the correct directory
    os.chdir(current_dir)
    
    tests = [
        test_database_connection,
        test_user_operations,
        test_conversation_operations,
        test_message_operations,
        test_relationships,
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
            print()
        except Exception as e:
            print(f"   ❌ Test failed with exception: {e}")
            results.append(False)
            print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("=" * 50)
    print(f"Test Summary: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Database is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)