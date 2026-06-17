/**
 * This file is generated. Do not edit directly.
 * Re-run: pnpm --filter @goblin/sdk generate
 */
import type { operations } from "./operations";

export interface paths {
    "/account/preferences": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * Save Preferences
         * @description Save user preferences
         */
        put: operations["save_preferences_api_v1_account_preferences_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/account/profile": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * Save Profile
         * @description Save user profile information
         */
        put: operations["save_profile_api_v1_account_profile_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api-keys/{provider}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Api Key
         * @description Get an API key for a provider
         */
        get: operations["get_api_key_api_v1_api_keys__provider__get"];
        put?: never;
        /**
         * Store Api Key
         * @description Store an API key for a provider
         */
        post: operations["store_api_key_api_v1_api_keys__provider__post"];
        /**
         * Delete Api Key
         * @description Delete an API key for a provider
         */
        delete: operations["delete_api_key_api_v1_api_keys__provider__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/chat": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Simple Chat */
        post: operations["simple_chat_api_v1_api_chat_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/feedback/stats": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Feedback Stats
         * @description Return aggregated feedback statistics for the last N days.
         *
         *     Used by the ops dashboard to monitor user satisfaction across
         *     departments, providers, and signal types.
         */
        get: operations["get_feedback_stats_api_v1_api_feedback_stats_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/generate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Generate */
        post: operations["generate_api_v1_api_generate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/goblins": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Goblins */
        get: operations["get_goblins_api_v1_api_goblins_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/history/{goblin_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Goblin History */
        get: operations["get_goblin_history_api_v1_api_history__goblin_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/orchestrate/execute": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Execute Orchestration */
        post: operations["execute_orchestration_api_v1_api_orchestrate_execute_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/orchestrate/parse": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Parse Orchestration */
        post: operations["parse_orchestration_api_v1_api_orchestrate_parse_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/orchestrate/plans/{plan_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Orchestration Plan */
        get: operations["get_orchestration_plan_api_v1_api_orchestrate_plans__plan_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/privacy/consent/rag": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Update Rag Consent
         * @description Update user consent for RAG (vector store) storage.
         *
         *     Users must explicitly consent before their data can be
         *     stored in the vector database for RAG.
         *
         *     Args:
         *         consent_given: True to grant consent, False to revoke
         *         user_id: Authenticated user ID
         *
         *     Returns:
         *         Dictionary with consent status
         */
        post: operations["update_rag_consent_api_v1_api_privacy_consent_rag_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/privacy/data-summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Data Summary
         * @description Get summary of stored user data (GDPR Article 15 - Right of Access).
         *
         *     Returns counts and metadata about stored data without returning
         *     the actual data (use /export for full data).
         *
         *     Args:
         *         user_id: Authenticated user ID
         *
         *     Returns:
         *         Dictionary with data summary
         *
         *     Example:
         *         GET /api/privacy/data-summary
         *         Authorization: Bearer <token>
         *
         *         Response:
         *         {
         *             "user_id": "user_123",
         *             "data_summary": {
         *                 "vectors": {"count": 15, "total_size_kb": 245},
         *                 "conversations": {"count": 42, "oldest": "2025-12-01T..."},
         *                 "preferences": {"count": 1}
         *             }
         *         }
         */
        get: operations["get_data_summary_api_v1_api_privacy_data_summary_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/privacy/delete": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /**
         * Delete User Data
         * @description Delete all user data (GDPR Article 17 - Right to Erasure).
         *
         *     This is a DESTRUCTIVE operation that:
         *     - Deletes all vector store documents
         *     - Deletes conversation history
         *     - Deletes user preferences
         *     - Marks account for deletion
         *
         *     Args:
         *         user_id: Authenticated user ID
         *         confirm: Must be True to proceed (safety check)
         *
         *     Returns:
         *         Dictionary with deletion status
         *
         *     Example:
         *         DELETE /api/privacy/delete?confirm=true
         *         Authorization: Bearer <token>
         *
         *         Response:
         *         {
         *             "success": true,
         *             "deleted_at": "2026-01-10T12:00:00Z",
         *             "deleted_items": {
         *                 "vectors": 15,
         *                 "conversations": 42,
         *                 "preferences": 1
         *             }
         *         }
         */
        delete: operations["delete_user_data_api_v1_api_privacy_delete_delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/privacy/export": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Export User Data
         * @description Export all user data (GDPR Article 20 - Right to Data Portability).
         *
         *     Returns a comprehensive export of all data stored about the user:
         *     - Vector store documents (RAG data)
         *     - Conversation history
         *     - User preferences
         *     - Account metadata
         *
         *     Args:
         *         user_id: Authenticated user ID
         *         include_vectors: Include vector store documents
         *         include_conversations: Include conversation history
         *         include_preferences: Include user preferences
         *
         *     Returns:
         *         Dictionary with all user data
         *
         *     Example:
         *         POST /api/privacy/export
         *         Authorization: Bearer <token>
         *
         *         Response:
         *         {
         *             "user_id": "user_123",
         *             "exported_at": "2026-01-10T12:00:00Z",
         *             "data": {
         *                 "vectors": [...],
         *                 "conversations": [...],
         *                 "preferences": {...}
         *             }
         *         }
         */
        post: operations["export_user_data_api_v1_api_privacy_export_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/route_task": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Route Task */
        post: operations["route_task_api_v1_api_route_task_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/route_task_stream_cancel/{stream_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Cancel Stream Task */
        post: operations["cancel_stream_task_api_v1_api_route_task_stream_cancel__stream_id__post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/route_task_stream_poll/{stream_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Poll Stream Task */
        get: operations["poll_stream_task_api_v1_api_route_task_stream_poll__stream_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/route_task_stream_start": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Start Stream Task */
        post: operations["start_stream_task_api_v1_api_route_task_stream_start_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/routing/feedback": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Submit Routing Feedback
         * @description Record a user's thumbs-up (+1) or thumbs-down (-1) for a routed response.
         *
         *     The request_id links back to the routing_events row created when the
         *     provider was selected. If provider_id / task_type are not supplied,
         *     this endpoint queries Supabase to look them up from the request_id.
         */
        post: operations["submit_routing_feedback_api_v1_api_routing_feedback_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/stats/{goblin_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Goblin Stats */
        get: operations["get_goblin_stats_api_v1_api_stats__goblin_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/csrf-token": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Csrf Token
         * @description Get a CSRF token for form submissions. Required for /register and /login.
         */
        get: operations["get_csrf_token_api_v1_auth_csrf_token_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/google": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Google Auth */
        post: operations["google_auth_api_v1_auth_google_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/google/callback": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Google Auth Callback
         * @description Handle Google OAuth callback.
         */
        post: operations["google_auth_callback_api_v1_auth_google_callback_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/google/url": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Google Auth Url
         * @description Get Google OAuth authorization URL.
         */
        get: operations["get_google_auth_url_api_v1_auth_google_url_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/login": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Login */
        post: operations["login_api_v1_auth_login_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/logout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Logout
         * @description Logout user and revoke session.
         */
        post: operations["logout_api_v1_auth_logout_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Current User Info */
        get: operations["get_current_user_info_api_v1_auth_me_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/passkey/auth": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Authenticate Passkey */
        post: operations["authenticate_passkey_api_v1_auth_passkey_auth_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/passkey/challenge": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Get Passkey Challenge
         * @description Get a challenge for passkey registration/authentication.
         */
        post: operations["get_passkey_challenge_api_v1_auth_passkey_challenge_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/passkey/register": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Register Passkey */
        post: operations["register_passkey_api_v1_auth_passkey_register_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/refresh": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Refresh Token Endpoint
         * @description Exchange refresh token for new access and refresh tokens.
         */
        post: operations["refresh_token_endpoint_api_v1_auth_refresh_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/register": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Register */
        post: operations["register_api_v1_auth_register_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/validate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Validate Token
         * @description Validate JWT token.
         */
        post: operations["validate_token_api_v1_auth_validate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/chat/contextual-chat": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Contextual Chat
         * @description Chat with the new fixed-order retrieval stack + strict token budgeting.
         *
         *     Differs from /messages by NOT requiring a conversation_id upfront and by
         *     returning context-assembly diagnostics alongside the assistant reply.
         */
        post: operations["contextual_chat_api_v1_chat_contextual_chat_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/chat/conversations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Conversations
         * @description List conversations for the authenticated user.
         *
         *     Returns metadata only (not message history). Ordered by updated_at desc.
         */
        get: operations["list_conversations_api_v1_chat_conversations_get"];
        put?: never;
        /**
         * Create Conversation
         * @description Create a new conversation.
         *
         *     Auto-generates UUID + title when not provided; user_id comes from
         *     the authenticated principal (multi-tenant).
         */
        post: operations["create_conversation_api_v1_chat_conversations_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/chat/conversations/{conversation_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Conversation
         * @description Get a conversation with paginated messages.
         *
         *     Query Parameters:
         *     - offset: messages to skip (default 0)
         *     - limit: max messages to return (default 50, capped at 500)
         */
        get: operations["get_conversation_api_v1_chat_conversations__conversation_id__get"];
        put?: never;
        post?: never;
        /**
         * Delete Conversation
         * @description Delete a conversation permanently (no soft-delete).
         */
        delete: operations["delete_conversation_api_v1_chat_conversations__conversation_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/chat/conversations/{conversation_id}/import": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Import Conversation Messages */
        post: operations["import_conversation_messages_api_v1_chat_conversations__conversation_id__import_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/chat/conversations/{conversation_id}/messages": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Send Message
         * @description Send a message and receive an AI response.
         *
         *     On stream=True, returns SSE via streaming.generate_chat_stream.
         *     Provider selection is delegated to the dispatcher; tool-calling is
         *     run inline.
         *
         *     Pipeline: WTI → attachments → context assembly → provider dispatch →
         *     tool loop → normalize → persist → respond.
         */
        post: operations["send_message_api_v1_chat_conversations__conversation_id__messages_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/chat/conversations/{conversation_id}/title": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * Update Conversation Title
         * @description Update conversation title (preserves messages + bumps updated_at).
         */
        put: operations["update_conversation_title_api_v1_chat_conversations__conversation_id__title_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/chat/debug/context-assembly": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Debug Context Assembly
         * @description Debug endpoint to inspect context assembly configuration.
         */
        get: operations["debug_context_assembly_api_v1_chat_debug_context_assembly_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/chat/estimate-tokens": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Estimate Tokens
         * @description Estimate token usage and cost for a message without invoking the provider.
         *
         *     Runs the same context-assembly pipeline as send_message so the estimate
         *     reflects what the real call would consume. Output tokens are a fixed
         *     OUTPUT_TOKEN_RATIO heuristic; this is a UI hint, not a guarantee.
         */
        post: operations["estimate_tokens_api_v1_chat_estimate_tokens_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/chat/files/{file_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Download File
         * @description Download an uploaded file. Only the owning user can access it.
         */
        get: operations["download_file_api_v1_chat_files__file_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/chat/stream": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Stream Chat
         * @description Stream chat response using Server-Sent Events.
         */
        post: operations["stream_chat_api_v1_chat_stream_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/chat/upload-file": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Upload File
         * @description Upload a file for later attachment to a chat message.
         */
        post: operations["upload_file_api_v1_chat_upload_file_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/api/migration-metrics": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Api Migration Metrics
         * @description Get runtime counters for API compatibility migration progress.
         */
        get: operations["get_api_migration_metrics_api_v1_debug_api_migration_metrics_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/context/health/{user_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Context Health
         * @description Get comprehensive context assembly health report
         */
        get: operations["get_context_health_api_v1_debug_context_health__user_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/context/history": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Context History
         * @description Get context assembly history with filtering
         */
        get: operations["get_context_history_api_v1_debug_context_history_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/context/replay/{request_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Replay Context
         * @description Replay context assembly for debugging purposes
         */
        get: operations["replay_context_api_v1_debug_context_replay__request_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/context/snapshot/{request_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Context Snapshot
         * @description Get context assembly snapshot for a specific request
         */
        get: operations["get_context_snapshot_api_v1_debug_context_snapshot__request_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Domain Events */
        get: operations["list_domain_events_api_v1_debug_events_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/events/{event_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Domain Event */
        get: operations["get_domain_event_api_v1_debug_events__event_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/memory/health/{user_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Memory Health
         * @description Get comprehensive memory health report
         */
        get: operations["get_memory_health_api_v1_debug_memory_health__user_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/memory/promotions/search": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Search Memory Promotions
         * @description Search memory promotions with advanced filtering
         */
        get: operations["search_memory_promotions_api_v1_debug_memory_promotions_search_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/memory/promotions/stats": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Memory Promotion Stats
         * @description Get memory promotion statistics for monitoring
         */
        get: operations["get_memory_promotion_stats_api_v1_debug_memory_promotions_stats_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/memory/user/{user_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get User Memory
         * @description Get long-term memory items for a user with full metadata
         */
        get: operations["get_user_memory_api_v1_debug_memory_user__user_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/retrieval-metrics/cache-hit-rate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Cache Hit Rate
         * @description Q3: What is the application-level Redis cache hit rate?
         *
         *     Reads in-process counters (not Redis server-global keyspace_hits).
         *     Reset on process restart.
         */
        get: operations["get_cache_hit_rate_api_v1_debug_retrieval_metrics_cache_hit_rate_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/retrieval-metrics/embedding-dedup": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Embedding Dedup
         * @description Q5: How much duplicate embedding work is being prevented?
         *
         *     Shows duplicates prevented by process-level content hash cache and DB source_id pre-check.
         */
        get: operations["get_embedding_dedup_api_v1_debug_retrieval_metrics_embedding_dedup_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/retrieval-metrics/failures": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Failure Summary
         * @description Q4: How often does context assembly fail and in what ways?
         *
         *     Failure types: embedding_unavailable, layer_skipped, truncation_triggered, assembly_error.
         *     Layer skip detail distinguishes skip_budget_exhausted from skip_no_data.
         */
        get: operations["get_failure_summary_api_v1_debug_retrieval_metrics_failures_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/retrieval-metrics/report": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Full Report
         * @description All five retrieval health questions in a single response.
         */
        get: operations["get_full_report_api_v1_debug_retrieval_metrics_report_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/retrieval-metrics/tier-latency": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Tier Latency Breakdown
         * @description Q2: How long does each retrieval tier take?
         *
         *     Returns per-tier (long_term, summary, index, messages, recent) avg/p50/p95 latency
         *     in milliseconds, plus total assembly latency.
         */
        get: operations["get_tier_latency_breakdown_api_v1_debug_retrieval_metrics_tier_latency_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/retrieval-metrics/token-accuracy": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Token Budget Accuracy
         * @description Q1: How accurate is the token budget prediction?
         *
         *     Returns avg_delta (positive = assembly produced more tokens than predicted,
         *     typically due to unbudgeted format-string headers), p95_abs_delta, and
         *     pct_within_5pct over the rolling window.
         */
        get: operations["get_token_budget_accuracy_api_v1_debug_retrieval_metrics_token_accuracy_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/retrieval/history": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Retrieval History
         * @description Get retrieval history with filtering
         */
        get: operations["get_retrieval_history_api_v1_debug_retrieval_history_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/retrieval/quality/{user_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Retrieval Quality
         * @description Get comprehensive retrieval quality report
         */
        get: operations["get_retrieval_quality_api_v1_debug_retrieval_quality__user_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/retrieval/stats": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Retrieval Stats
         * @description Get retrieval statistics for monitoring
         */
        get: operations["get_retrieval_stats_api_v1_debug_retrieval_stats_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/retrieval/trace/{request_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Retrieval Trace
         * @description Get full retrieval trace for a specific request
         */
        get: operations["get_retrieval_trace_api_v1_debug_retrieval_trace__request_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/suggest": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Get Debug Suggestion
         * @description Get intelligent debugging suggestions from model routing system.
         *
         *     Routes specialized tasks to Raptor model; other tasks to fallback model.
         *
         *     Request body:
         *     - task: str — Task identifier from RAPTOR_TASKS or other
         *     - context: dict — Contextual data (error, code, traces, etc.)
         *
         *     Returns:
         *     - model: str — Model used ('raptor' or 'fallback')
         *     - suggestion: str — The suggestion text
         *     - confidence: optional float — Confidence score if available
         *     - task: str — Echo of requested task
         *     - timestamp: str — Response timestamp
         *     - raw: optional dict — Raw model response for debugging
         */
        post: operations["get_debug_suggestion_api_v1_debug_suggest_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/system/observability/clear-cache": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Clear Observability Cache
         * @description Clear all observability caches for debugging
         */
        post: operations["clear_observability_cache_api_v1_debug_system_observability_clear_cache_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/system/observability/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get System Health
         * @description Get comprehensive system health report
         */
        get: operations["get_system_health_api_v1_debug_system_observability_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/system/observability/reset-counters": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Reset Observability Counters
         * @description Reset observability counters for debugging
         */
        post: operations["reset_observability_counters_api_v1_debug_system_observability_reset_counters_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/system/observability/summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Observability Summary
         * @description Get comprehensive observability summary across all systems
         */
        get: operations["get_observability_summary_api_v1_debug_system_observability_summary_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/tool-trace/conversation/{conversation_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Conversation Tool Traces
         * @description Get all tool execution traces for a conversation
         */
        get: operations["get_conversation_tool_traces_api_v1_debug_tool_trace_conversation__conversation_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/tool-trace/stats": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Tool Trace Stats
         * @description Get tool execution statistics for monitoring
         */
        get: operations["get_tool_trace_stats_api_v1_debug_tool_trace_stats_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/tool-trace/{request_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Tool Trace
         * @description Get full tool execution trace for a specific request
         */
        get: operations["get_tool_trace_api_v1_debug_tool_trace__request_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/write/decisions/search": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Search Write Decisions
         * @description Search write decisions with advanced filtering
         */
        get: operations["search_write_decisions_api_v1_debug_write_decisions_search_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/write/decisions/stats": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Write Decision Stats
         * @description Get write decision statistics for monitoring
         */
        get: operations["get_write_decision_stats_api_v1_debug_write_decisions_stats_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/debug/write/decisions/{conversation_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Write Decisions
         * @description Get message-by-message write decisions for a conversation
         */
        get: operations["get_write_decisions_api_v1_debug_write_decisions__conversation_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Health Check
         * @description Unified health endpoint covering all subsystems.
         *
         *     Strategy: Prioritizes fast response times over comprehensive validation.
         *     Optional components (database, Redis) use graceful degradation patterns.
         *     Provider monitoring runs asynchronously to avoid blocking health endpoints.
         */
        get: operations["health_check_api_v1_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health/all": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Health All
         * @description Return a detailed health summary for all subsystems.
         */
        get: operations["health_all_api_v1_health_all_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health/chroma/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health Chroma */
        get: operations["health_chroma_api_v1_health_chroma_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health/cost-tracking": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health Cost Tracking */
        get: operations["health_cost_tracking_api_v1_health_cost_tracking_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health/latency-history/{service}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health Latency History */
        get: operations["health_latency_history_api_v1_health_latency_history__service__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health/live": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Liveness Check
         * @description Liveness probe for Fly.io - returns 200 if app is alive.
         */
        get: operations["liveness_check_api_v1_health_live_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health/mcp/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health Mcp */
        get: operations["health_mcp_api_v1_health_mcp_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health/raptor/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health Raptor */
        get: operations["health_raptor_api_v1_health_raptor_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health/ready": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Readiness Check
         * @description Readiness probe for Fly.io - returns 200 if app is ready to serve traffic.
         */
        get: operations["readiness_check_api_v1_health_ready_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health/retest/{service}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Health Retest */
        post: operations["health_retest_api_v1_health_retest__service__post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health/routing": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Health Routing
         * @description Check routing subsystem health
         */
        get: operations["health_routing_api_v1_health_routing_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health/sandbox/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health Sandbox */
        get: operations["health_sandbox_api_v1_health_sandbox_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health/service-errors/{service}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health Service Errors */
        get: operations["health_service_errors_api_v1_health_service_errors__service__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health/stream": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Health Stream
         * @description Streaming health check endpoint (legacy compatibility)
         */
        get: operations["health_stream_api_v1_health_stream_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health/streaming": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Health Streaming
         * @description Check streaming capability health (alias for /health/stream)
         */
        get: operations["health_streaming_api_v1_health_streaming_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ops/aggregated": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Aggregated Metrics */
        get: operations["get_aggregated_metrics_api_v1_ops_aggregated_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ops/audit/log": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Audit Log */
        get: operations["get_audit_log_api_v1_ops_audit_log_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ops/circuit-breakers": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Circuit Breakers Status */
        get: operations["circuit_breakers_status_api_v1_ops_circuit_breakers_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ops/circuit-breakers/{provider_name}/reset": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Reset Circuit Breaker */
        post: operations["reset_circuit_breaker_api_v1_ops_circuit_breakers__provider_name__reset_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ops/gcs/colab/register": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Register Colab Backend
         * @description Register a new Colab tunnel URL and hot-reload the GCS colab backend.
         */
        post: operations["register_colab_backend_api_v1_ops_gcs_colab_register_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ops/gcs/colab/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Gcs Colab Status
         * @description Return the current colab backend endpoint (in-memory and DB).
         */
        get: operations["gcs_colab_status_api_v1_ops_gcs_colab_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ops/health/summary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Ops Health Summary */
        get: operations["ops_health_summary_api_v1_ops_health_summary_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ops/health/trends": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Health Trends */
        get: operations["get_health_trends_api_v1_ops_health_trends_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ops/metrics/history": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Metrics History */
        get: operations["metrics_history_api_v1_ops_metrics_history_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ops/performance/snapshot": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Performance Snapshot */
        get: operations["performance_snapshot_api_v1_ops_performance_snapshot_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ops/providers/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Ops Providers Status */
        get: operations["ops_providers_status_api_v1_ops_providers_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ops/queues/snapshot": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Queues Snapshot */
        get: operations["queues_snapshot_api_v1_ops_queues_snapshot_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ops/recommendations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get System Recommendations */
        get: operations["get_system_recommendations_api_v1_ops_recommendations_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ops/rovo-dev/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Rovo Dev Health Probe
         * @description Run an on-demand health probe against the Atlassian MCP endpoint.
         */
        post: operations["rovo_dev_health_probe_api_v1_ops_rovo_dev_health_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ops/rovo-dev/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Rovo Dev Status
         * @description Return Rovo Dev configuration state and circuit breaker snapshot.
         */
        get: operations["rovo_dev_status_api_v1_ops_rovo_dev_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ops/security/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Security Status */
        get: operations["get_security_status_api_v1_ops_security_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ops/sentry-webhook": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Sentry Webhook
         * @description Receive a Sentry issue alert, summarize it with AI, and post to Slack.
         */
        post: operations["sentry_webhook_api_v1_ops_sentry_webhook_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ops/streaming/analysis": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Streaming Analysis */
        get: operations["get_streaming_analysis_api_v1_ops_streaming_analysis_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/parse/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Parse Orchestration
         * @description Parse natural language text into an orchestration plan
         */
        post: operations["parse_orchestration_api_v1_parse__post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/providers/models": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Provider Models */
        get: operations["get_provider_models_api_v1_providers_models_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/raptor/demo/{value}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Raptor Demo
         * @description Demo endpoint for testing raptor
         */
        get: operations["raptor_demo_api_v1_raptor_demo__value__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/raptor/logs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Raptor Logs
         * @description Get raptor logs
         */
        post: operations["raptor_logs_api_v1_raptor_logs_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/raptor/start": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Raptor Start
         * @description Start raptor monitoring
         */
        post: operations["raptor_start_api_v1_raptor_start_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/raptor/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Raptor Status
         * @description Get raptor status
         */
        get: operations["raptor_status_api_v1_raptor_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/raptor/stop": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Raptor Stop
         * @description Stop raptor monitoring
         */
        post: operations["raptor_stop_api_v1_raptor_stop_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/routing/audit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Routing Audit
         * @description Return the most recent routing decision + outcome audit records.
         */
        get: operations["get_routing_audit_api_v1_routing_audit_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/routing/costs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Cost Tracking */
        get: operations["get_cost_tracking_api_v1_routing_costs_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/routing/departments": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Departments
         * @description List all available brain departments (no provider details).
         */
        get: operations["list_departments_api_v1_routing_departments_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/routing/departments/{department_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Department
         * @description Get details about a specific department.
         */
        get: operations["get_department_api_v1_routing_departments__department_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/routing/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Provider Health */
        get: operations["get_provider_health_api_v1_routing_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/routing/health/{provider_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Provider Health Detail */
        get: operations["get_provider_health_detail_api_v1_routing_health__provider_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/routing/providers": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Available Providers */
        get: operations["list_available_providers_api_v1_routing_providers_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/routing/providers/{capability}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Providers For Capability
         * @description [Deprecated] Use /routing/departments instead — returns departments.
         */
        get: operations["get_providers_for_capability_api_v1_routing_providers__capability__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/routing/route": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Route Through Department
         * @description Route a request through a brain department.
         *
         *     The department dispatcher selects the best internal provider
         *     based on the department's policy chain.
         */
        post: operations["route_through_department_api_v1_routing_route_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/routing/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Routing Status */
        get: operations["get_routing_status_api_v1_routing_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/routing/strategies": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Routing Strategies */
        get: operations["list_routing_strategies_api_v1_routing_strategies_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/routing/test/{provider_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Test Provider */
        post: operations["test_provider_api_v1_routing_test__provider_id__post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/routing/weight": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Routing Weight
         * @description Return the current HybridRouter cost/latency weight split.
         */
        get: operations["get_routing_weight_api_v1_routing_weight_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/sandbox/artifacts/{job_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Job Artifacts
         * @description List artifacts for a completed sandbox job
         */
        get: operations["list_job_artifacts_api_v1_sandbox_artifacts__job_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/sandbox/artifacts/{job_id}/download/{filename}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Download Artifact
         * @description Download a specific artifact file via presigned URL
         */
        get: operations["download_artifact_api_v1_sandbox_artifacts__job_id__download__filename__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/sandbox/cancel/{job_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Cancel Job
         * @description Cancel a running sandbox job
         */
        post: operations["cancel_job_api_v1_sandbox_cancel__job_id__post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/sandbox/health/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Sandbox Health
         * @description Get sandbox service health status
         */
        get: operations["sandbox_health_api_v1_sandbox_health_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/sandbox/jobs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Sandbox Jobs
         * @description Get list of sandbox jobs from Redis.
         */
        get: operations["list_sandbox_jobs_api_v1_sandbox_jobs_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/sandbox/jobs/{job_id}/logs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Job Logs Alias
         * @description Alias for /logs/{job_id} - Get job execution logs
         */
        get: operations["get_job_logs_alias_api_v1_sandbox_jobs__job_id__logs_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/sandbox/logs/{job_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Job Logs
         * @description Get logs for a completed sandbox job
         */
        get: operations["get_job_logs_api_v1_sandbox_logs__job_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/sandbox/metrics": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Sandbox Metrics
         * @description Get Prometheus metrics for sandbox operations
         */
        get: operations["sandbox_metrics_api_v1_sandbox_metrics_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/sandbox/run": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Run Sandbox Code
         * @description Alias for /submit - Execute code in sandbox
         */
        post: operations["run_sandbox_code_api_v1_sandbox_run_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/sandbox/status/{job_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Job Status
         * @description Get the status of a sandbox job
         */
        get: operations["get_job_status_api_v1_sandbox_status__job_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/sandbox/submit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Submit Job
         * @description Submit a job for sandbox execution
         */
        post: operations["submit_job_api_v1_sandbox_submit_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/search/collections": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Collections
         * @description List all source_types (indexes) that have content for the current user.
         */
        get: operations["list_collections_api_v1_search_collections_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/search/collections/{collection_name}/add": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Add Document Compat
         * @description Backward-compatible shim — maps collection_name to source_type.
         */
        post: operations["add_document_compat_api_v1_search_collections__collection_name__add_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/search/collections/{collection_name}/documents": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Collection Documents
         * @description List the most recently indexed items in a collection (non-semantic, recency order).
         */
        get: operations["get_collection_documents_api_v1_search_collections__collection_name__documents_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/search/index": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Index Content
         * @description Index any content into the named source_type for later semantic retrieval.
         *
         *     Fire-and-forget: returns immediately; embedding happens in the background.
         */
        post: operations["index_content_api_v1_search_index_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/search/query": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Search Query
         * @description Semantic search across one or more indexes using pgvector cosine similarity.
         */
        post: operations["search_query_api_v1_search_query_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/secrets/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Secrets
         * @description List secrets under a given prefix.
         *
         *     Args:
         *         prefix: Path prefix to filter secrets
         *         limit: Maximum number of secrets to return
         *         adapter: The secrets adapter instance
         *
         *     Returns:
         *         List of secret paths
         */
        get: operations["list_secrets_api_v1_secrets__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/secrets/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Secrets Health
         * @description Check the health of the secrets adapter.
         *
         *     Args:
         *         adapter: The secrets adapter instance
         *
         *     Returns:
         *         Health status and details
         */
        get: operations["secrets_health_api_v1_secrets_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/secrets/{path}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Secret
         * @description Retrieve a secret by path.
         *
         *     Args:
         *         path: Secret path
         *         version: Optional specific version
         *         adapter: The secrets adapter instance
         *
         *     Returns:
         *         Secret data and metadata
         */
        get: operations["get_secret_api_v1_secrets__path__get"];
        /**
         * Put Secret
         * @description Create or update a secret.
         *
         *     Args:
         *         path: Secret path
         *         request: Secret data and metadata
         *         adapter: The secrets adapter instance
         *
         *     Returns:
         *         Stored secret information
         */
        put: operations["put_secret_api_v1_secrets__path__put"];
        post?: never;
        /**
         * Delete Secret
         * @description Delete a secret.
         *
         *     Args:
         *         path: Secret path
         *         version: Optional specific version to delete
         *         adapter: The secrets adapter instance
         */
        delete: operations["delete_secret_api_v1_secrets__path__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/secrets/{path}/rotate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Rotate Secret
         * @description Rotate a secret value.
         *
         *     Args:
         *         path: Secret path
         *         adapter: The secrets adapter instance
         *
         *     Returns:
         *         New secret value
         */
        post: operations["rotate_secret_api_v1_secrets__path__rotate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/semantic-chat/conversations/{conversation_id}/context": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Context Bundle
         * @description Retrieve semantic context for a conversation and query
         */
        get: operations["get_context_bundle_api_v1_semantic_chat_conversations__conversation_id__context_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/semantic-chat/conversations/{conversation_id}/messages": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Semantic Send Message
         * @description Send a message with semantic retrieval and context-aware responses
         *
         *     Enhanced message processing flow:
         *     1. Validate conversation exists
         *     2. Add user message to conversation history
         *     3. Retrieve relevant context using semantic search
         *     4. Build contextual prompt with retrieved information
         *     5. Invoke AI provider with enhanced context
         *     6. Store embeddings asynchronously
         *     7. Return response with context details
         */
        post: operations["semantic_send_message_api_v1_semantic_chat_conversations__conversation_id__messages_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/semantic-chat/conversations/{conversation_id}/summarize": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Summarize Conversation
         * @description Generate and store a summary of the conversation
         */
        post: operations["summarize_conversation_api_v1_semantic_chat_conversations__conversation_id__summarize_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/semantic-chat/users/{user_id}/memory": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Add Memory Fact
         * @description Add a long-term memory fact for a user
         */
        post: operations["add_memory_fact_api_v1_semantic_chat_users__user_id__memory_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/semantic-chat/users/{user_id}/memory/search": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Search Memory Facts
         * @description Search user's memory facts using semantic similarity
         */
        get: operations["search_memory_facts_api_v1_semantic_chat_users__user_id__memory_search_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/settings/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Settings */
        get: operations["get_settings_api_v1_settings__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/settings/models/{model_name}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Update Model Settings */
        put: operations["update_model_settings_api_v1_settings_models__model_name__put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/settings/providers/{provider_name}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Update Provider Settings */
        put: operations["update_provider_settings_api_v1_settings_providers__provider_name__put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/settings/test-connection": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Test Provider Connection */
        post: operations["test_provider_connection_api_v1_settings_test_connection_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/stream": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Stream Task
         * @description Stream task execution results using Server-Sent Events with real provider
         */
        post: operations["stream_task_api_v1_stream_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/support/message": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Send Support Message
         * @description Submit a support message
         */
        post: operations["send_support_message_api_v1_support_message_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/support/triage": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Triage Issue
         * @description AI-powered bug report triage: categorise, prioritise, and optionally file a GitHub issue.
         */
        post: operations["triage_issue_api_v1_support_triage_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/write-time/cache/cleanup": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Cleanup Cache
         * @description Clean up expired cache entries
         */
        post: operations["cleanup_cache_api_v1_write_time_cache_cleanup_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/write-time/cache/clear": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Clear Cache
         * @description Clear all cache data (use with caution)
         */
        post: operations["clear_cache_api_v1_write_time_cache_clear_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/write-time/cache/stats": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Cache Stats
         * @description Get cache statistics and health information
         */
        get: operations["get_cache_stats_api_v1_write_time_cache_stats_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/write-time/matrix/config": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Decision Matrix Config
         * @description Get the current decision matrix configuration
         */
        get: operations["get_decision_matrix_config_api_v1_write_time_matrix_config_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/write-time/metrics": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Write Time Metrics
         * @description Get Write-Time Intelligence metrics and statistics
         */
        get: operations["get_write_time_metrics_api_v1_write_time_metrics_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/write-time/test": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Test Message Processing
         * @description Test message processing through Write-Time Intelligence
         *
         *     This endpoint allows you to test how a message would be processed
         *     by the Write-Time Decision Matrix without actually storing it.
         */
        post: operations["test_message_processing_api_v1_write_time_test_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/write-time/test/batch": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Test Batch Messages
         * @description Test multiple messages at once
         */
        post: operations["test_batch_messages_api_v1_write_time_test_batch_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/write-time/test/examples": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Test Examples
         * @description Get example messages for testing different classification types
         */
        get: operations["get_test_examples_api_v1_write_time_test_examples_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
