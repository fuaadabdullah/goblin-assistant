-- Consolidated Auth Schema Migration for Goblin Assistant
-- Created: 2025-12-06
-- Implements Supabase Auth consolidation with RBAC, session management, and audit logging

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- Central users table (mirrors Supabase auth.users as source of truth)
-- This table contains minimal profile fields and RBAC information
CREATE TABLE IF NOT EXISTS app_users (
    id uuid PRIMARY KEY,           -- same as auth.users.id
    email text UNIQUE NOT NULL,
    name text,
    role text DEFAULT 'user',      -- simple role; expand to RBAC later
    token_version int DEFAULT 0,   -- for token revocation on password reset/role change
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
-- Add index on email for fast lookups
CREATE INDEX IF NOT EXISTS ix_app_users_email ON app_users(email);
CREATE INDEX IF NOT EXISTS ix_app_users_role ON app_users(role);
-- Central session store for refresh token management and device control
CREATE TABLE IF NOT EXISTS user_sessions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    refresh_token_id text UNIQUE NOT NULL,     -- opaque server-side refresh token ID
    device_info text,                          -- device/browser fingerprint
    ip_address text,                           -- client IP for security tracking
    user_agent text,                           -- browser/client user agent
    created_at timestamptz DEFAULT now(),
    last_active timestamptz DEFAULT now(),
    expires_at timestamptz,                    -- when refresh token expires
    revoked boolean DEFAULT false,             -- emergency revocation flag
    revoked_at timestamptz,                    -- when session was revoked
    revoked_reason text                        -- why session was revoked
);
-- Indexes for session management performance
CREATE INDEX IF NOT EXISTS ix_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS ix_user_sessions_refresh_token_id ON user_sessions(refresh_token_id);
CREATE INDEX IF NOT EXISTS ix_user_sessions_revoked ON user_sessions(revoked);
CREATE INDEX IF NOT EXISTS ix_user_sessions_expires_at ON user_sessions(expires_at);
-- Audit logging table for compliance and security monitoring
CREATE TABLE IF NOT EXISTS audit_logs (
    id bigserial PRIMARY KEY,
    actor_id uuid,                             -- who performed the action (references app_users.id)
    action text NOT NULL,                      -- what happened (INSERT, UPDATE, DELETE, LOGIN, LOGOUT, etc.)
    object_table text,                         -- which table was affected
    object_id text,                            -- which record was affected
    old_values jsonb,                          -- previous state (for updates/deletes)
    new_values jsonb,                          -- new state (for inserts/updates)
    metadata jsonb,                            -- additional context (IP, user agent, etc.)
    ip_address text,                           -- client IP
    user_agent text,                           -- client user agent
    created_at timestamptz DEFAULT now()
);
-- Indexes for audit log queries
CREATE INDEX IF NOT EXISTS ix_audit_logs_actor_id ON audit_logs(actor_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS ix_audit_logs_object_table ON audit_logs(object_table);
CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs(created_at DESC);
-- RBAC: Role definitions table (extensible for future role management)
CREATE TABLE IF NOT EXISTS user_roles (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text UNIQUE NOT NULL,                 -- role name (admin, user, moderator, etc.)
    description text,                          -- human-readable description
    permissions jsonb DEFAULT '{}',            -- granular permissions as JSON
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
-- Insert default roles
INSERT INTO user_roles (name, description, permissions) VALUES
    ('admin', 'Full system access', '{"all": true}'),
    ('user', 'Standard user access', '{"read": true, "write": true}'),
    ('viewer', 'Read-only access', '{"read": true}')
ON CONFLICT (name) DO NOTHING;
-- User role assignments (many-to-many relationship)
CREATE TABLE IF NOT EXISTS user_role_assignments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    role_id uuid NOT NULL REFERENCES user_roles(id) ON DELETE CASCADE,
    assigned_by uuid REFERENCES app_users(id), -- who assigned this role
    assigned_at timestamptz DEFAULT now(),
    expires_at timestamptz,                    -- optional role expiration
    UNIQUE(user_id, role_id)                   -- prevent duplicate assignments
);
-- Indexes for role assignment queries
CREATE INDEX IF NOT EXISTS ix_user_role_assignments_user_id ON user_role_assignments(user_id);
CREATE INDEX IF NOT EXISTS ix_user_role_assignments_role_id ON user_role_assignments(role_id);
-- Function to sync users from Supabase auth.users to app_users
CREATE OR REPLACE FUNCTION sync_app_user()
RETURNS trigger AS $$
BEGIN
    -- Insert or update app_users when auth.users changes
    INSERT INTO app_users (id, email, name, created_at, updated_at)
    VALUES (NEW.id, NEW.email, COALESCE(NEW.raw_user_meta_data->>'name', NEW.raw_user_meta_data->>'full_name'), NEW.created_at, NEW.updated_at)
    ON CONFLICT (id) DO UPDATE SET
        email = EXCLUDED.email,
        name = COALESCE(EXCLUDED.name, app_users.name),
        updated_at = EXCLUDED.updated_at;

    -- Log the user creation/update
    INSERT INTO audit_logs (actor_id, action, object_table, object_id, new_values, metadata)
    VALUES (
        NEW.id,
        CASE WHEN TG_OP = 'INSERT' THEN 'USER_CREATED' ELSE 'USER_UPDATED' END,
        'app_users',
        NEW.id::text,
        jsonb_build_object('email', NEW.email, 'name', COALESCE(NEW.raw_user_meta_data->>'name', NEW.raw_user_meta_data->>'full_name')),
        jsonb_build_object('source', 'supabase_auth_sync', 'operation', TG_OP)
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
-- Function for audit logging on critical tables
CREATE OR REPLACE FUNCTION audit_changes()
RETURNS trigger AS $$
DECLARE
    actor_id uuid;
    old_json jsonb;
    new_json jsonb;
BEGIN
    -- Try to get actor from JWT claims (set by PostgREST/Supabase)
    BEGIN
        actor_id := current_setting('request.jwt.claims.sub')::uuid;
    EXCEPTION WHEN OTHERS THEN
        -- Fallback: try to get from session context or leave null
        actor_id := NULL;
    END;

    -- Convert OLD/NEW records to JSONB
    old_json := CASE WHEN TG_OP != 'INSERT' THEN row_to_json(OLD)::jsonb ELSE NULL END;
    new_json := CASE WHEN TG_OP != 'DELETE' THEN row_to_json(NEW)::jsonb ELSE NULL END;

    -- Insert audit log entry
    INSERT INTO audit_logs (
        actor_id,
        action,
        object_table,
        object_id,
        old_values,
        new_values,
        metadata
    ) VALUES (
        actor_id,
        TG_OP,
        TG_TABLE_NAME,
        COALESCE(NEW.id::text, OLD.id::text),
        old_json,
        new_json,
        jsonb_build_object(
            'timestamp', extract(epoch from now()),
            'schema', TG_TABLE_SCHEMA,
            'operation_type', TG_OP
        )
    );

    RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
-- Function to check token version for revocation
CREATE OR REPLACE FUNCTION check_token_version(user_uuid uuid, token_ver int)
RETURNS boolean AS $$
DECLARE
    current_version int;
BEGIN
    SELECT token_version INTO current_version
    FROM app_users
    WHERE id = user_uuid;

    RETURN current_version = token_ver;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
-- Function to revoke user sessions (for emergency logout)
CREATE OR REPLACE FUNCTION revoke_user_sessions(user_uuid uuid, reason text DEFAULT 'Emergency revocation')
RETURNS int AS $$
DECLARE
    revoked_count int;
BEGIN
    UPDATE user_sessions
    SET revoked = true, revoked_at = now(), revoked_reason = reason
    WHERE user_id = user_uuid AND revoked = false;

    GET DIAGNOSTICS revoked_count = ROW_COUNT;
    RETURN revoked_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
-- Function to clean up expired sessions
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS int AS $$
DECLARE
    deleted_count int;
BEGIN
    DELETE FROM user_sessions
    WHERE expires_at < now() OR (revoked = true AND revoked_at < now() - interval '30 days');

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
-- Row Level Security (RLS) Policies

-- Enable RLS on sensitive tables
ALTER TABLE app_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_role_assignments ENABLE ROW LEVEL SECURITY;
-- Users can read their own data
CREATE POLICY "users_read_own" ON app_users
    FOR SELECT USING (id = current_setting('request.jwt.claims.sub')::uuid);
-- Admins can read all users
CREATE POLICY "admins_read_all_users" ON app_users
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM user_role_assignments ura
            JOIN user_roles ur ON ura.role_id = ur.id
            WHERE ura.user_id = current_setting('request.jwt.claims.sub')::uuid
            AND ur.name = 'admin'
        )
    );
-- Users can read their own sessions
CREATE POLICY "users_read_own_sessions" ON user_sessions
    FOR SELECT USING (user_id = current_setting('request.jwt.claims.sub')::uuid);
-- Users can manage their own sessions
CREATE POLICY "users_manage_own_sessions" ON user_sessions
    FOR ALL USING (user_id = current_setting('request.jwt.claims.sub')::uuid);
-- Admins can read all sessions
CREATE POLICY "admins_read_all_sessions" ON user_sessions
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM user_role_assignments ura
            JOIN user_roles ur ON ura.role_id = ur.id
            WHERE ura.user_id = current_setting('request.jwt.claims.sub')::uuid
            AND ur.name = 'admin'
        )
    );
-- Only admins can read audit logs
CREATE POLICY "admins_read_audit_logs" ON audit_logs
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM user_role_assignments ura
            JOIN user_roles ur ON ura.role_id = ur.id
            WHERE ura.user_id = current_setting('request.jwt.claims.sub')::uuid
            AND ur.name = 'admin'
        )
    );
-- Users can read their own role assignments
CREATE POLICY "users_read_own_roles" ON user_role_assignments
    FOR SELECT USING (user_id = current_setting('request.jwt.claims.sub')::uuid);
-- Admins can manage all role assignments
CREATE POLICY "admins_manage_roles" ON user_role_assignments
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM user_role_assignments ura
            JOIN user_roles ur ON ura.role_id = ur.id
            WHERE ura.user_id = current_setting('request.jwt.claims.sub')::uuid
            AND ur.name = 'admin'
        )
    );
-- Add comments for documentation
COMMENT ON TABLE app_users IS 'Central user table mirroring Supabase auth.users with RBAC extensions';
COMMENT ON TABLE user_sessions IS 'Server-controlled session store for refresh token management and device tracking';
COMMENT ON TABLE audit_logs IS 'Comprehensive audit trail for compliance and security monitoring';
COMMENT ON TABLE user_roles IS 'RBAC role definitions with granular permissions';
COMMENT ON TABLE user_role_assignments IS 'Many-to-many user-role assignments with expiration support';
COMMENT ON FUNCTION sync_app_user() IS 'Syncs users from Supabase auth.users to app_users table';
COMMENT ON FUNCTION audit_changes() IS 'Generic audit logging function for database changes';
COMMENT ON FUNCTION check_token_version(uuid, int) IS 'Validates token version for revocation checking';
COMMENT ON FUNCTION revoke_user_sessions(uuid, text) IS 'Emergency session revocation for security incidents';
COMMENT ON FUNCTION cleanup_expired_sessions() IS 'Maintenance function to remove expired/revoked sessions';
