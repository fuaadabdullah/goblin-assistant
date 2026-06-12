# Database Configuration Guide

This guide covers the database setup, configuration, and management for the Goblin Assistant application.

## Overview

The Goblin Assistant uses SQLAlchemy with async support for database operations. The system supports multiple database backends:

- **SQLite** (default for development)
- **PostgreSQL** (recommended for production)
- **Supabase** (managed PostgreSQL service)

## Quick Start

### 1. Environment Setup

Copy the example environment file and configure your database:

```bash
cp .env.example .env
```

Edit `.env` to set your database configuration:

```bash
# Development (SQLite)
DATABASE_URL=sqlite+aiosqlite:///./goblin_assistant.db

# Production (PostgreSQL)
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/goblin_assistant

# Supabase
DATABASE_URL=postgresql+asyncpg://postgres:your_password@db.your_project.supabase.co:5433/postgres
```

### 2. Initialize Database

Run the database initialization script:

```bash
python init_db.py
```

This will:
- Create the database file (SQLite) or connect to your database
- Create all required tables (users, conversations, messages)
- Display success confirmation

### 3. Validate Setup

Run the validation script to ensure everything is working:

```bash
python scripts/validate_database_config.py
```

### 4. Test Database Operations

Run the comprehensive test suite:

```bash
python scripts/test_database.py
```

## Database Schema

### Tables

1. **users**
   - `id`: Primary key (UUID)
   - `email`: Unique email address
   - `name`: User display name
   - `hashed_password`: Password hash
   - `google_id`: Google OAuth ID (optional)
   - `passkey_credential_id`: WebAuthn credential ID (optional)
   - `created_at`: Creation timestamp
   - `updated_at`: Last update timestamp
   - `last_login`: Last login timestamp
   - `is_active`: Account status

2. **conversations**
   - `conversation_id`: Primary key (UUID)
   - `user_id`: Foreign key to users table
   - `title`: Conversation title
   - `created_at`: Creation timestamp
   - `updated_at`: Last update timestamp
   - `metadata`: JSON metadata

3. **messages**
   - `message_id`: Primary key (UUID)
   - `conversation_id`: Foreign key to conversations table
   - `role`: Message role (user/assistant)
   - `content`: Message content
   - `timestamp`: Message timestamp
   - `metadata`: JSON metadata

### Relationships

- Users have many conversations (one-to-many)
- Conversations have many messages (one-to-many)
- Messages belong to conversations (many-to-one)

## Database Management

### Migrations

The project uses Alembic for database migrations:

```bash
# Generate a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migrations
alembic downgrade -1
```

### Manual Table Management

For development, you can use the initialization script:

```bash
# Recreate all tables (WARNING: This will delete all data!)
python init_db.py
```

## Environment Configuration

### Development Environment

```bash
# Use SQLite for development
DATABASE_URL=sqlite+aiosqlite:///./goblin_assistant.db
ENVIRONMENT=development
DEBUG=true
```

### Production Environment

```bash
# Use PostgreSQL for production
DATABASE_URL=postgresql+asyncpg://user:pass@prod-db:5432/goblin_prod
ENVIRONMENT=production
DEBUG=false

# Enable SSL for production
# Add ?sslmode=require to your DATABASE_URL
```

### Supabase Configuration

```bash
# Supabase connection
DATABASE_URL=postgresql+asyncpg://postgres:your_password@db.your_project.supabase.co:5433/postgres
SUPABASE_URL=https://your_project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SUPABASE_ANON_KEY=your_anon_key
```

## Security Considerations

### Database URL Security

- Never commit database URLs with passwords to version control
- Use environment variables for sensitive information
- Consider using connection pooling for production

### SSL Configuration

For production PostgreSQL connections, ensure SSL is enabled:

```bash
# Enable SSL mode
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db?sslmode=require
```

### Password Security

- Use strong, unique passwords for database users
- Consider using password managers for database credentials
- Rotate passwords regularly

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```
   ImportError: No module named 'api.storage.database'
   ```
   **Solution**: Ensure you're running from the correct directory and Python path is set correctly.

2. **Database Connection Failed**
   ```
   sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) unable to open database file
   ```
   **Solution**: Check file permissions and directory existence.

3. **Table Not Found**
   ```
   sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedTable) relation "users" does not exist
   ```
   **Solution**: Run `python init_db.py` to create tables.

### Debug Commands

```bash
# Check database URL
python -c "import os; print(os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///./goblin_assistant.db'))"

# Test database connection
python -c "from api.storage.database import engine; print(engine.url)"

# List tables
python -c "from api.storage.database import engine; from sqlalchemy import inspect; print(inspect(engine).get_table_names())"
```

## Performance Optimization

### Connection Pooling

For production, configure connection pooling:

```python
# In api/storage/database.py
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,
)
```

### Indexes

Consider adding indexes for frequently queried fields:

```sql
-- Add indexes for better performance
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_timestamp ON messages(timestamp);
```

## Monitoring

### Database Health Checks

Use the validation script for regular health checks:

```bash
# Run validation
python scripts/validate_database_config.py

# Check specific components
python scripts/validate_database_config.py --check-connection
python scripts/validate_database_config.py --check-models
```

### Performance Monitoring

Monitor database performance with:

- Connection pool usage
- Query execution times
- Table sizes and growth
- Index effectiveness

## Backup and Recovery

### SQLite Backup

```bash
# Simple file copy for SQLite
cp goblin_assistant.db goblin_assistant.db.backup

# Or use SQLite backup command
sqlite3 goblin_assistant.db ".backup goblin_assistant.db.backup"
```

### PostgreSQL Backup

```bash
# Using pg_dump
pg_dump -h localhost -U username -d goblin_assistant > backup.sql

# Restore from backup
psql -h localhost -U username -d goblin_assistant < backup.sql
```

## Integration with Application

### FastAPI Integration

The database is automatically initialized in the FastAPI application:

```python
# In api/main.py
@app.on_event("startup")
async def startup_event():
    await init_db()
```

### Dependency Injection

Use the database session in your routes:

```python
from api.storage.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

@app.get("/users")
async def get_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute("SELECT * FROM users")
    return result.fetchall()
```

## Next Steps

1. **Set up monitoring**: Configure database monitoring and alerting
2. **Implement caching**: Add Redis caching for frequently accessed data
3. **Scale horizontally**: Consider read replicas for high-traffic scenarios
4. **Data migration**: Plan for data migration strategies as the schema evolves

## Support

For additional support:
- Check the validation script output
- Review the test suite results
- Consult the SQLAlchemy documentation
- Review PostgreSQL/Supabase documentation for advanced configurations