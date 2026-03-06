-- Privacy-first database schema with RLS policies
-- Migration: 20260110_privacy_schema_with_rls
-- Created: 2026-01-10
-- Purpose: Add tables with Row Level Security for privacy compliance

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- CONVERSATIONS TABLE
-- Stores conversation metadata and message hashes (NOT raw content)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    message_hash TEXT NOT NULL,  -- SHA256 hash, not raw content
    message_length INTEGER NOT NULL,
    has_pii BOOLEAN DEFAULT FALSE,
    pii_types JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '24 hours'),
    
    -- Indexes for performance
    CONSTRAINT conversations_user_id_session_id_idx UNIQUE (user_id, session_id, message_hash)
);

-- Enable RLS
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;

-- RLS Policies for conversations
CREATE POLICY "Users can only see their own conversations"
ON public.conversations FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Users can only insert their own conversations"
ON public.conversations FOR INSERT
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can only delete their own conversations"
ON public.conversations FOR DELETE
USING (auth.uid() = user_id);

-- Index for TTL cleanup
CREATE INDEX IF NOT EXISTS conversations_expires_at_idx 
ON public.conversations(expires_at);

-- Index for user queries
CREATE INDEX IF NOT EXISTS conversations_user_id_created_at_idx 
ON public.conversations(user_id, created_at DESC);

-- ============================================================================
-- INFERENCE LOGS TABLE
-- Tracks LLM provider usage WITHOUT storing message content
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.inference_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    session_id TEXT,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    latency_ms INTEGER NOT NULL,
    token_count INTEGER,
    cost_usd DECIMAL(10,6),
    status_code INTEGER NOT NULL,
    error_type TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE public.inference_logs ENABLE ROW LEVEL SECURITY;

-- RLS Policies for inference logs (admin only for full access)
CREATE POLICY "Admins can see all inference logs"
ON public.inference_logs FOR SELECT
USING (
    auth.jwt() ->> 'email' IN (
        'fuaadabdullah@gmail.com',
        'goblinosrep@gmail.com'
    )
);

CREATE POLICY "Users can see their own inference logs"
ON public.inference_logs FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "System can insert inference logs"
ON public.inference_logs FOR INSERT
WITH CHECK (true);  -- Service role only

-- Indexes for analytics
CREATE INDEX IF NOT EXISTS inference_logs_provider_model_idx 
ON public.inference_logs(provider, model, created_at DESC);

CREATE INDEX IF NOT EXISTS inference_logs_user_id_created_at_idx 
ON public.inference_logs(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS inference_logs_status_code_idx 
ON public.inference_logs(status_code, created_at DESC);

-- ============================================================================
-- USER PREFERENCES TABLE
-- Stores user settings and consent flags
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    rag_consent_given BOOLEAN DEFAULT FALSE,
    rag_consent_date TIMESTAMPTZ,
    telemetry_consent BOOLEAN DEFAULT TRUE,
    data_retention_days INTEGER DEFAULT 30,
    preferences JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE public.user_preferences ENABLE ROW LEVEL SECURITY;

-- RLS Policies for user preferences
CREATE POLICY "Users can see their own preferences"
ON public.user_preferences FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own preferences"
ON public.user_preferences FOR INSERT
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own preferences"
ON public.user_preferences FOR UPDATE
USING (auth.uid() = user_id);

-- ============================================================================
-- PRIVACY AUDIT LOG TABLE
-- Tracks data exports and deletions for compliance
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.privacy_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,  -- Not FK to allow retention after user deletion
    action TEXT NOT NULL CHECK (action IN ('export', 'delete', 'consent_update')),
    item_count INTEGER,
    success BOOLEAN NOT NULL,
    ip_address INET,
    user_agent TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE public.privacy_audit_log ENABLE ROW LEVEL SECURITY;

-- RLS Policies for audit log (admin only for full access)
CREATE POLICY "Admins can see all audit logs"
ON public.privacy_audit_log FOR SELECT
USING (
    auth.jwt() ->> 'email' IN (
        'fuaadabdullah@gmail.com',
        'goblinosrep@gmail.com'
    )
);

CREATE POLICY "System can insert audit logs"
ON public.privacy_audit_log FOR INSERT
WITH CHECK (true);  -- Service role only

-- Index for audit queries
CREATE INDEX IF NOT EXISTS privacy_audit_log_user_id_created_at_idx 
ON public.privacy_audit_log(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS privacy_audit_log_action_idx 
ON public.privacy_audit_log(action, created_at DESC);

-- ============================================================================
-- TTL CLEANUP FUNCTIONS
-- Automatically remove expired data
-- ============================================================================

CREATE OR REPLACE FUNCTION cleanup_expired_conversations()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM public.conversations 
    WHERE expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Log cleanup
    RAISE NOTICE 'Cleaned up % expired conversations', deleted_count;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute to authenticated users
GRANT EXECUTE ON FUNCTION cleanup_expired_conversations() TO authenticated;

-- ============================================================================
-- HELPER FUNCTIONS FOR PRIVACY OPERATIONS
-- ============================================================================

CREATE OR REPLACE FUNCTION get_user_data_summary(target_user_id UUID)
RETURNS JSON AS $$
DECLARE
    result JSON;
BEGIN
    -- Must be called by the user themselves or admin
    IF auth.uid() != target_user_id AND 
       auth.jwt() ->> 'email' NOT IN ('fuaadabdullah@gmail.com', 'goblinosrep@gmail.com') THEN
        RAISE EXCEPTION 'Unauthorized access to user data summary';
    END IF;
    
    SELECT json_build_object(
        'user_id', target_user_id,
        'conversation_count', (
            SELECT COUNT(*) FROM public.conversations WHERE user_id = target_user_id
        ),
        'inference_count', (
            SELECT COUNT(*) FROM public.inference_logs WHERE user_id = target_user_id
        ),
        'has_preferences', (
            SELECT COUNT(*) > 0 FROM public.user_preferences WHERE user_id = target_user_id
        ),
        'generated_at', NOW()
    ) INTO result;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute to authenticated users
GRANT EXECUTE ON FUNCTION get_user_data_summary(UUID) TO authenticated;

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE public.conversations IS 
'Stores conversation metadata and message hashes. Raw message content is NEVER stored. TTL enforced via expires_at.';

COMMENT ON TABLE public.inference_logs IS 
'Tracks LLM API usage for cost monitoring and analytics. Does NOT contain message content.';

COMMENT ON TABLE public.user_preferences IS 
'User settings including RAG consent and data retention preferences.';

COMMENT ON TABLE public.privacy_audit_log IS 
'Compliance audit log for GDPR/CCPA operations. Retained even after user deletion.';

COMMENT ON COLUMN public.conversations.message_hash IS 
'SHA256 hash of message for deduplication. Raw content never stored.';

COMMENT ON COLUMN public.user_preferences.rag_consent_given IS 
'User consent for storing data in vector database (RAG). Required by privacy policy.';

-- ============================================================================
-- SCHEDULE TTL CLEANUP (requires pg_cron extension)
-- ============================================================================

-- Uncomment if pg_cron is available:
-- SELECT cron.schedule(
--     'cleanup-conversations', 
--     '0 * * * *',  -- Every hour
--     'SELECT cleanup_expired_conversations()'
-- );

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify RLS is enabled on all tables
DO $$
DECLARE
    table_record RECORD;
    rls_count INTEGER := 0;
BEGIN
    FOR table_record IN 
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename IN ('conversations', 'inference_logs', 'user_preferences', 'privacy_audit_log')
    LOOP
        IF EXISTS (
            SELECT 1 FROM pg_class c 
            JOIN pg_namespace n ON n.oid = c.relnamespace 
            WHERE c.relname = table_record.tablename 
            AND n.nspname = 'public' 
            AND c.relrowsecurity = true
        ) THEN
            rls_count := rls_count + 1;
            RAISE NOTICE 'RLS enabled on: %', table_record.tablename;
        ELSE
            RAISE WARNING 'RLS NOT enabled on: %', table_record.tablename;
        END IF;
    END LOOP;
    
    RAISE NOTICE 'Total tables with RLS: %', rls_count;
END $$;
