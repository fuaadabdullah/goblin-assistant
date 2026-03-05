---
title: "STORAGE MIGRATION"
description: "Storage Migration: In-Memory to Database"
---

# Storage Migration: In-Memory to Database

## Overview

This document tracks the migration of goblin-assistant from in-memory storage to persistent database storage using SQLAlchemy and SQLite (with PostgreSQL support).

## Migration Status

### ✅ Completed Migrations

1. **Task Execution (`api/execute_router.py`)**
   - **Before**: `TASKS = {}` dictionary
   - **After**: `Task` database model
   - **Fields**: id, user_id, goblin, task, code, provider, model, status, result, created_at, updated_at

2. **Streaming Tasks (`api/api_router.py`)**
   - **Before**: `ACTIVE_STREAMS = {}` dictionary
   - **After**: `Stream` and `StreamChunk` database models
   - **Fields**:
     - Stream: id, user_id, goblin, task, code, provider, model, status, created_at
     - StreamChunk: id, stream_id, content, token_count, cost_delta, done, created_at

3. **Search Collections (`api/search_router.py`)**
   - **Before**: `COLLECTIONS = {}` dictionary
   - **After**: `SearchCollection` and `SearchDocument` database models
   - **Fields**:
     - SearchCollection: id, name, created_at
     - SearchDocument: id, collection_id, document_id, document, document_metadata, created_at

### 🔄 In Progress

4. **User Authentication (`api/auth/router.py`)**
   - **Before**: `users_db = {}` dictionary
   - **After**: `User` database model (already exists in models_base.py)
   - **Status**: Needs migration - auth router still uses in-memory dict
   - **Fields**: id, email, password_hash, name, google_id, passkey_credential_id, passkey_public_key, created_at, updated_at

## Database Models Location

All models are defined in:

- `/apps/goblin-assistant/backend/models_base.py`

Database configuration:

- `/apps/goblin-assistant/backend/database.py`

## Database Setup

### Current Configuration

- **Development**: SQLite (`goblin_assistant.db`)
- **Production**: PostgreSQL (configurable via `DATABASE_URL` env var)

### Initialize Database

```bash
cd apps/goblin-assistant
python init_db.py
```

This will create all necessary tables based on the models in `models_base.py`.

## Next Steps

1. ✅ ~~Migrate execute_router.py to use Task model~~
2. ✅ ~~Migrate api_router.py to use Stream/StreamChunk models~~
3. ✅ ~~Migrate search_router.py to use SearchCollection/SearchDocument models~~
4. 🔄 Migrate auth/router.py to use User model from database
5. Run database migration to create tables
6. Test all endpoints with persistent storage
7. Update documentation and deployment guides

## Benefits of Database Storage

✅ **Persistence**: Data survives server restarts
✅ **Scalability**: Can handle concurrent requests safely
✅ **Querying**: Rich query capabilities with SQLAlchemy
✅ **Relationships**: Proper foreign keys and relationships
✅ **Migration Path**: Easy to migrate from SQLite to PostgreSQL
✅ **Audit Trail**: Timestamps on all records

## Notes

- All routers now use dependency injection with `db: Session = Depends(get_db)`
- Async background tasks use `SessionLocal()` for their own database sessions
- Import linting errors are expected since we're dynamically adding backend to path
- User authentication (user_id) is currently set to None - needs proper auth integration

## Last Updated

December 1, 2025
