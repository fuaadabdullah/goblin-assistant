-- Phase 3 hardening: Supabase Auth + RLS normalization, LLM usage rollups.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS vector;

-- -----------------------------------------------------------------------------
-- User-owned application tables
-- -----------------------------------------------------------------------------

ALTER TABLE IF EXISTS public.conversations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS conversations_user_select_own ON public.conversations;
CREATE POLICY conversations_user_select_own
    ON public.conversations
    FOR SELECT
    USING (auth.uid()::text = user_id::text);
DROP POLICY IF EXISTS conversations_user_insert_own ON public.conversations;
CREATE POLICY conversations_user_insert_own
    ON public.conversations
    FOR INSERT
    WITH CHECK (auth.uid()::text = user_id::text);
DROP POLICY IF EXISTS conversations_user_delete_own ON public.conversations;
CREATE POLICY conversations_user_delete_own
    ON public.conversations
    FOR DELETE
    USING (auth.uid()::text = user_id::text);

ALTER TABLE IF EXISTS public.user_preferences ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS user_preferences_user_select_own ON public.user_preferences;
CREATE POLICY user_preferences_user_select_own
    ON public.user_preferences
    FOR SELECT
    USING (auth.uid()::text = user_id::text);
DROP POLICY IF EXISTS user_preferences_user_insert_own ON public.user_preferences;
CREATE POLICY user_preferences_user_insert_own
    ON public.user_preferences
    FOR INSERT
    WITH CHECK (auth.uid()::text = user_id::text);
DROP POLICY IF EXISTS user_preferences_user_update_own ON public.user_preferences;
CREATE POLICY user_preferences_user_update_own
    ON public.user_preferences
    FOR UPDATE
    USING (auth.uid()::text = user_id::text)
    WITH CHECK (auth.uid()::text = user_id::text);

ALTER TABLE IF EXISTS public.user_sessions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS user_sessions_user_select_own ON public.user_sessions;
CREATE POLICY user_sessions_user_select_own
    ON public.user_sessions
    FOR SELECT
    USING (auth.uid()::text = user_id::text);

ALTER TABLE IF EXISTS public.routing_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS routing_events_user_select_own ON public.routing_events;
CREATE POLICY routing_events_user_select_own
    ON public.routing_events
    FOR SELECT
    USING (auth.uid() = user_id);
DROP POLICY IF EXISTS routing_events_service_insert ON public.routing_events;
CREATE POLICY routing_events_service_insert
    ON public.routing_events
    FOR INSERT
    WITH CHECK (auth.role() = 'service_role');
DROP POLICY IF EXISTS routing_events_service_update ON public.routing_events;
CREATE POLICY routing_events_service_update
    ON public.routing_events
    FOR UPDATE
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

ALTER TABLE IF EXISTS public.inference_logs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS inference_logs_user_select_own ON public.inference_logs;
CREATE POLICY inference_logs_user_select_own
    ON public.inference_logs
    FOR SELECT
    USING (auth.uid() = user_id);
DROP POLICY IF EXISTS inference_logs_service_all ON public.inference_logs;
CREATE POLICY inference_logs_service_all
    ON public.inference_logs
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');
DROP POLICY IF EXISTS "Admins can see all inference logs" ON public.inference_logs;
DROP POLICY IF EXISTS "Users can see their own inference logs" ON public.inference_logs;
DROP POLICY IF EXISTS "System can insert inference logs" ON public.inference_logs;

ALTER TABLE IF EXISTS public.privacy_audit_log ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS privacy_audit_log_service_all ON public.privacy_audit_log;
CREATE POLICY privacy_audit_log_service_all
    ON public.privacy_audit_log
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

ALTER TABLE IF EXISTS public.task_routing_decisions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS task_routing_decisions_service_all ON public.task_routing_decisions;
CREATE POLICY task_routing_decisions_service_all
    ON public.task_routing_decisions
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- -----------------------------------------------------------------------------
-- Usage / analytics tables
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.usage_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    request_id TEXT,
    route TEXT,
    conversation_id TEXT,
    message_id TEXT,
    provider TEXT,
    model TEXT,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    latency_ms DOUBLE PRECISION,
    status_code INTEGER,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS usage_events_user_created_idx
    ON public.usage_events (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS usage_events_provider_model_created_idx
    ON public.usage_events (provider, model, created_at DESC);
CREATE INDEX IF NOT EXISTS usage_events_request_id_idx
    ON public.usage_events (request_id);

CREATE TABLE IF NOT EXISTS public.usage_daily_aggregates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    usage_date DATE NOT NULL,
    event_count INTEGER NOT NULL DEFAULT 0,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    total_cost_usd DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, usage_date)
);

CREATE INDEX IF NOT EXISTS usage_daily_aggregates_user_date_idx
    ON public.usage_daily_aggregates (user_id, usage_date);

CREATE TABLE IF NOT EXISTS public.model_usage_daily_aggregates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    usage_date DATE NOT NULL,
    request_count INTEGER NOT NULL DEFAULT 0,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    total_cost_usd DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    total_latency_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (provider, model, usage_date)
);

CREATE INDEX IF NOT EXISTS model_usage_daily_aggregates_provider_model_date_idx
    ON public.model_usage_daily_aggregates (provider, model, usage_date);

CREATE TABLE IF NOT EXISTS public.memory_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    source_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL DEFAULT 0,
    chunk_text TEXT NOT NULL,
    chunk_embedding vector(1536),
    chunk_hash TEXT NOT NULL,
    repository TEXT,
    commit_sha TEXT,
    run_id TEXT,
    session_id TEXT,
    conversation_id TEXT REFERENCES public.conversations(conversation_id) ON DELETE SET NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, source_kind, source_id, chunk_hash)
);

CREATE INDEX IF NOT EXISTS memory_entries_user_kind_idx
    ON public.memory_entries (user_id, source_kind);
CREATE INDEX IF NOT EXISTS memory_entries_user_created_idx
    ON public.memory_entries (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS memory_entries_repository_idx
    ON public.memory_entries (repository);
CREATE INDEX IF NOT EXISTS memory_entries_commit_sha_idx
    ON public.memory_entries (commit_sha);
CREATE INDEX IF NOT EXISTS memory_entries_run_id_idx
    ON public.memory_entries (run_id);
CREATE INDEX IF NOT EXISTS memory_entries_session_id_idx
    ON public.memory_entries (session_id);
CREATE INDEX IF NOT EXISTS memory_entries_chunk_embedding_hnsw_idx
    ON public.memory_entries
    USING hnsw (chunk_embedding vector_cosine_ops);

ALTER TABLE IF EXISTS public.usage_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS usage_events_user_select_own ON public.usage_events;
CREATE POLICY usage_events_user_select_own
    ON public.usage_events
    FOR SELECT
    USING (auth.uid()::text = user_id);
DROP POLICY IF EXISTS usage_events_service_all ON public.usage_events;
CREATE POLICY usage_events_service_all
    ON public.usage_events
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

ALTER TABLE IF EXISTS public.usage_daily_aggregates ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS usage_daily_aggregates_user_select_own ON public.usage_daily_aggregates;
CREATE POLICY usage_daily_aggregates_user_select_own
    ON public.usage_daily_aggregates
    FOR SELECT
    USING (auth.uid()::text = user_id);
DROP POLICY IF EXISTS usage_daily_aggregates_service_all ON public.usage_daily_aggregates;
CREATE POLICY usage_daily_aggregates_service_all
    ON public.usage_daily_aggregates
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

ALTER TABLE IF EXISTS public.model_usage_daily_aggregates ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS model_usage_daily_aggregates_service_all ON public.model_usage_daily_aggregates;
CREATE POLICY model_usage_daily_aggregates_service_all
    ON public.model_usage_daily_aggregates
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

ALTER TABLE IF EXISTS public.memory_entries ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS memory_entries_user_select_own ON public.memory_entries;
CREATE POLICY memory_entries_user_select_own
    ON public.memory_entries
    FOR SELECT
    USING (auth.uid()::text = user_id);
DROP POLICY IF EXISTS memory_entries_service_all ON public.memory_entries;
CREATE POLICY memory_entries_service_all
    ON public.memory_entries
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- -----------------------------------------------------------------------------
-- Verification helper
-- -----------------------------------------------------------------------------

DO $$
DECLARE
    target_table TEXT;
    tables TEXT[] := ARRAY[
        'conversations',
        'user_preferences',
        'user_sessions',
        'routing_events',
        'inference_logs',
        'privacy_audit_log',
        'task_routing_decisions',
        'usage_events',
        'usage_daily_aggregates',
        'model_usage_daily_aggregates',
        'memory_entries'
    ];
BEGIN
    FOREACH target_table IN ARRAY tables LOOP
        IF EXISTS (
            SELECT 1
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relname = target_table
              AND c.relrowsecurity = true
        ) THEN
            RAISE NOTICE 'RLS enabled: %', target_table;
        ELSE
            RAISE WARNING 'RLS missing: %', target_table;
        END IF;
    END LOOP;
END $$;
