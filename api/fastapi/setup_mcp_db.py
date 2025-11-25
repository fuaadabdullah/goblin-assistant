"""
Database setup script for MCP tables.
Run this to initialize the MCP database schema.
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_database_url():
    """Get database URL from environment variables."""
    return os.getenv("DATABASE_URL", "sqlite:///./mcp_test.db")


def create_mcp_tables():
    """Create MCP database tables."""
    database_url = get_database_url()
    print(f"Connecting to database: {database_url.replace('password', '***')}")

    engine = create_engine(database_url)

    # SQL statements to create tables
    create_table_statements = [
        """
        CREATE TABLE IF NOT EXISTS mcp_request (
            id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
            user_hash VARCHAR(16) NOT NULL,
            status VARCHAR(20) NOT NULL,
            task_type VARCHAR(50),
            priority INTEGER DEFAULT 50,
            provider_hint VARCHAR(100),
            cost_estimate_usd REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_provider VARCHAR(100),
            attempts INTEGER DEFAULT 0,
            trace_id VARCHAR(32)
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_mcp_request_user_hash ON mcp_request(user_hash);",
        "CREATE INDEX IF NOT EXISTS idx_mcp_request_status ON mcp_request(status);",
        "CREATE INDEX IF NOT EXISTS idx_mcp_request_created_at ON mcp_request(created_at);",
        """
        CREATE TABLE IF NOT EXISTS mcp_event (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT NOT NULL REFERENCES mcp_request(id),
            ts DATETIME DEFAULT CURRENT_TIMESTAMP,
            event_type VARCHAR(50),
            payload TEXT
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_mcp_event_request_id ON mcp_event(request_id);",
        "CREATE INDEX IF NOT EXISTS idx_mcp_event_event_type ON mcp_event(event_type);",
        "CREATE INDEX IF NOT EXISTS idx_mcp_event_ts ON mcp_event(ts);",
        """
        CREATE TABLE IF NOT EXISTS mcp_result (
            request_id TEXT PRIMARY KEY REFERENCES mcp_request(id),
            result TEXT,
            tokens INTEGER,
            cost_usd REAL,
            finished_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """,
    ]

    try:
        with engine.connect() as conn:
            # Execute each SQL statement
            for sql in create_table_statements:
                conn.execute(text(sql))
            conn.commit()
            print("✅ MCP database tables created successfully!")

            # Verify tables exist
            result = conn.execute(
                text("""
                SELECT name
                FROM sqlite_master
                WHERE type='table'
                AND name IN ('mcp_request', 'mcp_event', 'mcp_result')
                ORDER BY name;
            """)
            )

            tables = [row[0] for row in result]
            print(f"✅ Verified tables exist: {', '.join(tables)}")

    except Exception as e:
        print(f"❌ Error creating database tables: {e}")
        sys.exit(1)


if __name__ == "__main__":
    create_mcp_tables()
