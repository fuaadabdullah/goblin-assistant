-- Audit Triggers Migration for Goblin Assistant
-- Created: 2025-12-06
-- Adds audit triggers to critical tables for compliance logging

-- Create audit triggers for sensitive tables
CREATE TRIGGER audit_app_users
AFTER INSERT OR UPDATE OR DELETE ON app_users
FOR EACH ROW EXECUTE FUNCTION audit_changes();
CREATE TRIGGER audit_user_sessions
AFTER INSERT OR UPDATE OR DELETE ON user_sessions
FOR EACH ROW EXECUTE FUNCTION audit_changes();
CREATE TRIGGER audit_user_role_assignments
AFTER INSERT OR UPDATE OR DELETE ON user_role_assignments
FOR EACH ROW EXECUTE FUNCTION audit_changes();
-- Note: Cannot create triggers on auth.users due to permissions
-- User sync will be handled manually or through application logic

-- Add comments
COMMENT ON TRIGGER audit_app_users ON app_users IS 'Audit all changes to user accounts';
COMMENT ON TRIGGER audit_user_sessions ON user_sessions IS 'Audit session creation, updates, and revocations';
COMMENT ON TRIGGER audit_user_role_assignments ON user_role_assignments IS 'Audit role assignment changes';
