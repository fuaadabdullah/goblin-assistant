-- Sync user_sessions to match the application ORM schema (Alembic 005_add_user_sessions)
-- The consolidated_auth_schema migration (20251206163006) created a user_sessions table
-- that uses a UUID id + refresh_token_id design. The application's FastAPI backend uses
-- a different, simpler schema (session_id text PK, is_revoked boolean).
--
-- This migration ensures the app-facing user_sessions table exists with the columns
-- the backend ORM expects, using IF NOT EXISTS / IF NOT EXISTS guards throughout.

-- If the previous user_sessions table exists with the old schema (id uuid PK),
-- we rename it to preserve audit history and create the new one.
DO $$
BEGIN
  -- Check if user_sessions already has session_id as primary key (app schema)
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'user_sessions'
      AND column_name = 'session_id'
  ) THEN
    -- Rename old table so history is not lost
    IF EXISTS (
      SELECT 1 FROM information_schema.tables
      WHERE table_name = 'user_sessions'
    ) THEN
      ALTER TABLE user_sessions RENAME TO user_sessions_legacy;
    END IF;

    -- Create app-schema user_sessions
    CREATE TABLE user_sessions (
      session_id  TEXT        PRIMARY KEY,
      user_id     TEXT        NOT NULL,
      is_revoked  BOOLEAN     NOT NULL DEFAULT FALSE,
      created_at  TIMESTAMPTZ DEFAULT NOW(),
      expires_at  TIMESTAMPTZ
    );

    CREATE INDEX IF NOT EXISTS ix_user_sessions_user_id
      ON user_sessions (user_id);

    CREATE INDEX IF NOT EXISTS ix_user_sessions_expires_at
      ON user_sessions (expires_at);
  END IF;
END;
$$;

-- RLS: users can read their own sessions; service role can read/write all
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE tablename = 'user_sessions' AND policyname = 'users_read_own_app_sessions'
  ) THEN
    CREATE POLICY "users_read_own_app_sessions"
      ON user_sessions FOR SELECT
      USING (auth.uid()::text = user_id);
  END IF;
END;
$$;
