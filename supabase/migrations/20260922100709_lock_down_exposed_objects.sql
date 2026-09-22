BEGIN;

DO $tables$
DECLARE
    object_name text;
BEGIN
    FOREACH object_name IN ARRAY ARRAY[
        'users',
        'tasks',
        'provider_credentials',
        'support_messages',
        'sandbox_runs',
        'department_routing_weights',
        'provider_metrics',
        'models',
        'provider_policies',
        'routing_audit_log',
        'routing_requests',
        'search_collections',
        'search_documents',
        'streams',
        'stream_chunks',
        'user_roles'
    ]
    LOOP
        IF to_regclass(format('public.%I', object_name)) IS NOT NULL THEN
            EXECUTE format(
                'ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',
                object_name
            );
            EXECUTE format(
                'REVOKE ALL PRIVILEGES ON TABLE public.%I FROM anon, authenticated',
                object_name
            );
        END IF;
    END LOOP;
END
$tables$;

DO $provider_status$
BEGIN
    IF to_regclass('public.provider_status') IS NOT NULL THEN
        ALTER TABLE public.provider_status ENABLE ROW LEVEL SECURITY;
        REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
            ON TABLE public.provider_status FROM anon, authenticated;
        GRANT SELECT ON TABLE public.provider_status TO anon, authenticated;

        IF NOT EXISTS (
            SELECT 1
            FROM pg_policies
            WHERE schemaname = 'public'
              AND tablename = 'provider_status'
              AND policyname = 'authenticated_read_provider_status'
        ) THEN
            CREATE POLICY authenticated_read_provider_status
                ON public.provider_status
                FOR SELECT
                TO authenticated
                USING (true);
        END IF;
    END IF;
END
$provider_status$;

DO $views$
DECLARE
    object_name text;
BEGIN
    FOREACH object_name IN ARRAY ARRAY[
        'routing_cost_daily',
        'routing_cost_by_provider'
    ]
    LOOP
        IF to_regclass(format('public.%I', object_name)) IS NOT NULL THEN
            EXECUTE format(
                'ALTER VIEW public.%I SET (security_invoker = true)',
                object_name
            );
            EXECUTE format(
                'REVOKE ALL PRIVILEGES ON TABLE public.%I FROM anon, authenticated',
                object_name
            );
        END IF;
    END LOOP;
END
$views$;

DO $functions$
DECLARE
    function_name text;
    function_oid regprocedure;
BEGIN
    FOREACH function_name IN ARRAY ARRAY[
        'public.audit_changes()',
        'public.check_token_version(uuid,integer)',
        'public.cleanup_expired_conversations()',
        'public.cleanup_expired_sessions()',
        'public.get_user_data_summary(uuid)',
        'public.revoke_user_sessions(uuid,text)',
        'public.sync_app_user()',
        'public.update_rag_updated_at()'
    ]
    LOOP
        function_oid := to_regprocedure(function_name);
        IF function_oid IS NOT NULL THEN
            EXECUTE format(
                'ALTER FUNCTION %s SET search_path = pg_catalog, public',
                function_oid
            );
            EXECUTE format(
                'REVOKE ALL PRIVILEGES ON FUNCTION %s FROM PUBLIC, anon, authenticated',
                function_oid
            );
            EXECUTE format(
                'GRANT EXECUTE ON FUNCTION %s TO service_role',
                function_oid
            );
        END IF;
    END LOOP;
END
$functions$;

COMMIT;
