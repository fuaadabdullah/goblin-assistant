-- Initial schema migration for Goblin Assistant
-- Created: 2025-12-01

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR PRIMARY KEY,
    email VARCHAR NOT NULL UNIQUE,
    password_hash VARCHAR,
    name VARCHAR,
    google_id VARCHAR UNIQUE,
    passkey_credential_id VARCHAR,
    passkey_public_key TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);
-- Create search_collections table
CREATE TABLE IF NOT EXISTS search_collections (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_search_collections_name ON search_collections(name);
-- Create search_documents table
CREATE TABLE IF NOT EXISTS search_documents (
    id SERIAL PRIMARY KEY,
    collection_id INTEGER NOT NULL REFERENCES search_collections(id),
    document_id VARCHAR NOT NULL,
    document TEXT NOT NULL,
    document_metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Create tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR REFERENCES users(id),
    goblin VARCHAR NOT NULL,
    task TEXT NOT NULL,
    code TEXT,
    provider VARCHAR,
    model VARCHAR,
    status VARCHAR,
    result TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Create streams table
CREATE TABLE IF NOT EXISTS streams (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR REFERENCES users(id),
    goblin VARCHAR NOT NULL,
    task TEXT NOT NULL,
    code TEXT,
    provider VARCHAR,
    model VARCHAR,
    status VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Create stream_chunks table
CREATE TABLE IF NOT EXISTS stream_chunks (
    id SERIAL PRIMARY KEY,
    stream_id VARCHAR NOT NULL REFERENCES streams(id),
    content TEXT,
    token_count INTEGER,
    cost_delta FLOAT,
    done BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Add comments
COMMENT ON TABLE users IS 'User accounts with authentication credentials';
COMMENT ON TABLE search_collections IS 'Document collections for RAG search';
COMMENT ON TABLE search_documents IS 'Individual documents in search collections';
COMMENT ON TABLE tasks IS 'Asynchronous task execution records';
COMMENT ON TABLE streams IS 'Streaming response sessions';
COMMENT ON TABLE stream_chunks IS 'Individual chunks from streaming responses';
