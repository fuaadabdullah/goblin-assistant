/**
 * This file is generated. Do not edit directly.
 * Re-run: pnpm --filter @goblin/sdk generate
 */

export interface components {
    schemas: {
        /** AgentTaskEvent */
        AgentTaskEvent: {
            /** Event Id */
            event_id: string;
            /** Message */
            message: string;
            /** Metadata */
            metadata?: {
                [key: string]: unknown;
            };
            /** Timestamp */
            timestamp: string;
            /** Type */
            type: string;
        };
        /** AgentTaskEventInput */
        AgentTaskEventInput: {
            /** Message */
            message: string;
            /** Metadata */
            metadata?: {
                [key: string]: unknown;
            };
            /** Phase */
            phase?: string | null;
            /** Result */
            result?: {
                [key: string]: unknown;
            };
            /** Status */
            status?: string | null;
            /** Type */
            type: string;
        };
        /** AgentTaskEventsResponse */
        AgentTaskEventsResponse: {
            /** Events */
            events?: components["schemas"]["AgentTaskEvent"][];
            /** Phase */
            phase: string;
            /** Status */
            status: string;
            /** Task Id */
            task_id: string;
            /**
             * Total
             * @default 0
             */
            total: number;
        };
        /** AgentTaskRecord */
        AgentTaskRecord: {
            /** Aider Mode */
            aider_mode?: string | null;
            /** Architect Model */
            architect_model?: string | null;
            /** Auto Commit Each Change */
            auto_commit_each_change?: boolean | null;
            /** Base Branch */
            base_branch: string;
            /** Branch Name */
            branch_name: string;
            /** Callback Url */
            callback_url?: string | null;
            /** Checkout Ref */
            checkout_ref?: string | null;
            /** Created At */
            created_at: string;
            /** Editor Model */
            editor_model?: string | null;
            /** Events */
            events?: components["schemas"]["AgentTaskEvent"][];
            /** Issue Body */
            issue_body?: string | null;
            /** Issue Number */
            issue_number?: number | null;
            /** Issue Title */
            issue_title?: string | null;
            /** Issue Url */
            issue_url?: string | null;
            /** Metadata */
            metadata?: {
                [key: string]: unknown;
            };
            /** Payload */
            payload?: {
                [key: string]: unknown;
            };
            /** Phase */
            phase: string;
            /** Phase0 Ci Commands */
            phase0_ci_commands?: {
                [key: string]: unknown;
            }[];
            /** Pr Url */
            pr_url?: string | null;
            /** Repair Attempts */
            repair_attempts?: number | null;
            /** Repo Url */
            repo_url: string;
            /** Result */
            result?: {
                [key: string]: unknown;
            };
            /** Source */
            source: string;
            /** Sprite Name */
            sprite_name?: string | null;
            /** Status */
            status: string;
            /** Task */
            task: string;
            /** Task Id */
            task_id: string;
            /** Tests Command */
            tests_command: string;
            /** Updated At */
            updated_at: string;
            /** Worker Error */
            worker_error?: string | null;
            /** Worker Profile */
            worker_profile?: {
                [key: string]: unknown;
            };
            /** Worker Status */
            worker_status?: string | null;
            /** Workspace */
            workspace?: {
                [key: string]: unknown;
            };
            /** Workspace Family */
            workspace_family?: string | null;
            /** Workspace Id */
            workspace_id?: string | null;
            /** Workspace Provider */
            workspace_provider?: string | null;
        };
        /** AgentTaskSubmitRequest */
        AgentTaskSubmitRequest: {
            /** Base Branch */
            base_branch?: string | null;
            /** Branch Name */
            branch_name?: string | null;
            /** Issue Body */
            issue_body?: string | null;
            /** Issue Number */
            issue_number?: number | null;
            /** Issue Title */
            issue_title?: string | null;
            /** Issue Url */
            issue_url?: string | null;
            /** Metadata */
            metadata?: {
                [key: string]: unknown;
            };
            /** Repo Url */
            repo_url?: string | null;
            /**
             * Source
             * @default ui
             */
            source: string;
            /** Task */
            task: string;
            /** Tests Command */
            tests_command?: string | null;
        };
        /** AgentTaskSubmitResponse */
        AgentTaskSubmitResponse: {
            task: components["schemas"]["AgentTaskRecord"];
        };
        /** ApiKeyRequest */
        ApiKeyRequest: {
            /** Key */
            key: string;
        };
        /** ApiKeyResponse */
        ApiKeyResponse: {
            /** Key */
            key?: string | null;
            /** Provider */
            provider: string;
        };
        /** ArtifactInfo */
        ArtifactInfo: {
            /** Created At */
            created_at: string;
            /** Name */
            name: string;
            /** Size */
            size: number;
            /** Url */
            url: string;
        };
        /** ArtifactListResponse */
        ArtifactListResponse: {
            /** Artifacts */
            artifacts: components["schemas"]["ArtifactInfo"][];
        };
        /** Body_get_debug_suggestion_api_v1_debug_suggest_post */
        Body_get_debug_suggestion_api_v1_debug_suggest_post: {
            /**
             * Context
             * @description Context data for the debug task
             */
            context: {
                [key: string]: unknown;
            };
            /**
             * Task
             * @description Debug task type (e.g., 'quick_fix', 'summarize_trace')
             */
            task: string;
        };
        /** Body_upload_file_api_v1_chat_upload_file_post */
        Body_upload_file_api_v1_chat_upload_file_post: {
            /** File */
            file: string;
        };
        /**
         * CacheStatsResponse
         * @description Response with cache statistics
         */
        CacheStatsResponse: {
            /** Cache Stats */
            cache_stats: {
                [key: string]: unknown;
            };
            /** Redis Info */
            redis_info: {
                [key: string]: unknown;
            };
            /** Status */
            status: string;
            /** Timestamp */
            timestamp: string;
        };
        /** CancelJobResponse */
        CancelJobResponse: {
            /** Message */
            message: string;
        };
        /** ChatMessage */
        ChatMessage: {
            /** Content */
            content: string;
            /** Metadata */
            metadata?: {
                [key: string]: unknown;
            } | null;
            /** Role */
            role: string;
            /** Timestamp */
            timestamp?: string | null;
        };
        /** ChatSettingsResponse */
        ChatSettingsResponse: {
            /** Default Model */
            default_model: string | null;
            /** Default Provider */
            default_provider: string | null;
            /** Max Tokens */
            max_tokens: number | null;
            /** Metadata */
            metadata: {
                [key: string]: components["schemas"]["JsonValue"];
            } | null;
            /** Summary Enabled */
            summary_enabled: boolean;
            /** System Prompt */
            system_prompt: string | null;
            /** Temperature */
            temperature: number | null;
            /** User Id */
            user_id: string;
        };
        /** ChatSettingsUpdate */
        ChatSettingsUpdate: {
            /** Default Model */
            default_model?: string | null;
            /** Default Provider */
            default_provider?: string | null;
            /** Max Tokens */
            max_tokens?: number | null;
            /** Metadata */
            metadata?: {
                [key: string]: components["schemas"]["JsonValue"];
            } | null;
            /** Summary Enabled */
            summary_enabled?: boolean | null;
            /** System Prompt */
            system_prompt?: string | null;
            /** Temperature */
            temperature?: number | null;
        };
        /** ColabRegisterRequest */
        ColabRegisterRequest: {
            /** Endpoint */
            endpoint: string;
        };
        /** CollectionsResponse */
        CollectionsResponse: {
            /** Collections */
            collections: string[];
        };
        /**
         * ContextualChatRequest
         * @description Request for contextual chat with advanced context assembly
         */
        ContextualChatRequest: {
            /** Conversation Id */
            conversation_id?: string | null;
            /** Department */
            department?: string | null;
            /**
             * Enable Context Assembly
             * @default true
             */
            enable_context_assembly: boolean;
            /** Message */
            message: string;
            /** Metadata */
            metadata?: {
                [key: string]: unknown;
            } | null;
            /** Mode */
            mode?: string | null;
            /** Model */
            model?: string | null;
            /** Provider */
            provider?: string | null;
            /**
             * Stream
             * @default false
             */
            stream: boolean | null;
            /** User Id */
            user_id?: string | null;
        };
        /**
         * ContextualChatResponse
         * @description Response for contextual chat with context assembly details
         */
        ContextualChatResponse: {
            /** Context Assembly */
            context_assembly?: {
                [key: string]: unknown;
            } | null;
            /** Department */
            department: string;
            /**
             * Department Reason
             * @default
             */
            department_reason: string;
            /** Message Id */
            message_id: string;
            /** Response */
            response: string;
            /** Timestamp */
            timestamp: string;
            /** Token Usage */
            token_usage?: {
                [key: string]: unknown;
            } | null;
            /** Visualizations */
            visualizations?: {
                [key: string]: unknown;
            }[] | null;
        };
        /** ConversationInfo */
        ConversationInfo: {
            /** Category */
            category?: string | null;
            /** Conversation Id */
            conversation_id: string;
            /** Created At */
            created_at: string;
            /** Message Count */
            message_count: number;
            /** Snippet */
            snippet?: string | null;
            /** Title */
            title: string;
            /** Updated At */
            updated_at: string;
            /** User Id */
            user_id: string | null;
        };
        /** CreateConversationRequest */
        CreateConversationRequest: {
            /** Title */
            title?: string | null;
            /** User Id */
            user_id?: string | null;
        };
        /** CreateConversationResponse */
        CreateConversationResponse: {
            /** Conversation Id */
            conversation_id: string;
            /** Created At */
            created_at: string;
            /** Title */
            title: string;
        };
        /**
         * CsrfTokenResponse
         * @description Response for CSRF token endpoint.
         */
        CsrfTokenResponse: {
            /** Csrf Token */
            csrf_token: string;
        };
        /**
         * DecisionMatrixResponse
         * @description Response with decision matrix configuration
         */
        DecisionMatrixResponse: {
            /** Decision Table */
            decision_table: {
                [key: string]: unknown;
            };
            /** Rate Limits */
            rate_limits: {
                [key: string]: unknown;
            };
            /** Timestamp */
            timestamp: string;
        };
        /**
         * DepartmentRouteRequest
         * @description Request to route through a department (not a raw provider).
         */
        DepartmentRouteRequest: {
            /**
             * Department
             * @default general
             */
            department: string;
            /** Payload */
            payload: {
                [key: string]: unknown;
            };
            /**
             * Stream
             * @default false
             */
            stream: boolean | null;
        };
        /** EstimateTokensResponse */
        EstimateTokensResponse: {
            /**
             * Degraded Mode
             * @default false
             */
            degraded_mode: boolean;
            /** Degraded Reason */
            degraded_reason?: string | null;
            /**
             * Department
             * @default general
             */
            department: string;
            /** Estimated Cost Usd */
            estimated_cost_usd: number;
            /** Estimated Output Tokens */
            estimated_output_tokens: number;
            /** Input Tokens */
            input_tokens: number;
            /** Layers */
            layers: components["schemas"]["LayerEstimate"][];
        };
        /** EventEnvelope[dict[str, JsonValue]] */
        EventEnvelope_dict_str__JsonValue__: {
            /** Actor User Id */
            actor_user_id?: string | null;
            /** Correlation Id */
            correlation_id?: string | null;
            /** Event Id */
            event_id: string;
            /**
             * Event Type
             * @enum {string}
             */
            event_type: "chat.message.created" | "chat.message.failed" | "provider.health.updated" | "sandbox.execution.completed" | "memory.item.promoted" | "wti.failed";
            /** Occurred At */
            occurred_at: string;
            /** Payload */
            payload: {
                [key: string]: components["schemas"]["JsonValue"];
            };
            /** Source */
            source: string;
        };
        /** EventLogListResponse */
        EventLogListResponse: {
            /** Events */
            events: components["schemas"]["EventEnvelope_dict_str__JsonValue__"][];
            /** Total */
            total: number;
        };
        /** FeatureFlagUpsert */
        FeatureFlagUpsert: {
            /** Default Value */
            default_value?: {
                [key: string]: unknown;
            } | null;
            /**
             * Enabled
             * @default false
             */
            enabled: boolean;
            /** Metadata */
            metadata?: {
                [key: string]: unknown;
            } | null;
            /** Rollout Percent */
            rollout_percent?: number | null;
            /** Target Roles */
            target_roles?: string[] | null;
            /** Target Users */
            target_users?: string[] | null;
            /** User Overrides */
            user_overrides?: {
                [key: string]: unknown;
            } | null;
        };
        /** FeedbackRequest */
        FeedbackRequest: {
            /** Conversation Id */
            conversation_id?: string | null;
            /** Department */
            department?: string | null;
            /** Message Id */
            message_id?: string | null;
            /** Model */
            model?: string | null;
            /** Provider Id */
            provider_id?: string | null;
            /** Rating */
            rating?: number | null;
            /** Request Id */
            request_id: string;
            /** Signal */
            signal?: string | null;
            /** Task Type */
            task_type?: string | null;
        };
        /** FeedbackResponse */
        FeedbackResponse: {
            /** Ok */
            ok: boolean;
        };
        /** FeedbackStatsResponse */
        FeedbackStatsResponse: {
            /**
             * By Department
             * @default {}
             */
            by_department: {
                [key: string]: unknown;
            };
            /**
             * By Provider
             * @default {}
             */
            by_provider: {
                [key: string]: unknown;
            };
            /**
             * Continue Count
             * @default 0
             */
            continue_count: number;
            /**
             * Copy Count
             * @default 0
             */
            copy_count: number;
            /**
             * Delete Count
             * @default 0
             */
            delete_count: number;
            /**
             * Model Switch Count
             * @default 0
             */
            model_switch_count: number;
            /**
             * Provider Switch Count
             * @default 0
             */
            provider_switch_count: number;
            /**
             * Recent Events
             * @default []
             */
            recent_events: unknown[];
            /**
             * Regenerate Count
             * @default 0
             */
            regenerate_count: number;
            /**
             * Thumbs Down Count
             * @default 0
             */
            thumbs_down_count: number;
            /**
             * Thumbs Up Count
             * @default 0
             */
            thumbs_up_count: number;
            /**
             * Thumbs Up Rate
             * @default 0
             */
            thumbs_up_rate: number;
            /**
             * Total Events
             * @default 0
             */
            total_events: number;
        };
        /** FileUploadResponse */
        FileUploadResponse: {
            /** File Id */
            file_id: string;
            /** Filename */
            filename: string;
            /** Mime Type */
            mime_type: string;
            /** Size Bytes */
            size_bytes: number;
        };
        /** GenerateRequest */
        GenerateRequest: {
            /** Messages */
            messages?: components["schemas"]["SimpleChatMessage"][] | null;
            /** Model */
            model?: string | null;
            /** Prompt */
            prompt?: string | null;
            /** Provider */
            provider?: string | null;
        };
        /** GenerateResponse */
        GenerateResponse: {
            /** Choices */
            choices?: {
                [key: string]: unknown;
            }[] | null;
            /** Content */
            content?: string | null;
            /** Error */
            error?: string | null;
        };
        /** GitHubWebhookResponse */
        GitHubWebhookResponse: {
            /** Accepted */
            accepted: boolean;
            /**
             * Ignored
             * @default false
             */
            ignored: boolean;
            /** Reason */
            reason?: string | null;
            task?: components["schemas"]["AgentTaskRecord"] | null;
        };
        /** GoogleAuthCallback */
        GoogleAuthCallback: {
            /** Code */
            code: string;
            /** State */
            state?: string | null;
        };
        /** GoogleAuthRequest */
        GoogleAuthRequest: {
            /** Token */
            token: string;
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /**
         * HealthResponse
         * @description Response model for secrets health check.
         */
        HealthResponse: {
            /** Backend */
            backend: string;
            /** Cache Stats */
            cache_stats?: {
                [key: string]: unknown;
            } | null;
            /** Details */
            details: {
                [key: string]: unknown;
            };
            /** Status */
            status: string;
            /** Timestamp */
            timestamp?: string | null;
        };
        /** ImportConversationRequest */
        ImportConversationRequest: {
            /** Messages */
            messages: components["schemas"]["ChatMessage"][];
        };
        /** IndexRequest */
        IndexRequest: {
            /** Content */
            content: string;
            /** Metadata */
            metadata?: {
                [key: string]: unknown;
            } | null;
            /** Source Id */
            source_id?: string | null;
            /**
             * Source Type
             * @default document
             */
            source_type: string;
        };
        /** IndexResponse */
        IndexResponse: {
            /** Source Id */
            source_id: string;
            /** Status */
            status: string;
        };
        /** JobLogsResponse */
        JobLogsResponse: {
            /** Logs */
            logs: string;
        };
        /** JobStatus */
        JobStatus: {
            /** Created At */
            created_at: string;
            /** Error */
            error?: string | null;
            /** Exit Code */
            exit_code?: number | null;
            /** Finished At */
            finished_at?: string | null;
            /** Job Id */
            job_id: string;
            /** Started At */
            started_at?: string | null;
            /** Status */
            status: string;
        };
        JsonValue: unknown;
        /** LayerEstimate */
        LayerEstimate: {
            /** Name */
            name: string;
            /** Tokens */
            tokens: number;
        };
        /**
         * LogoutResponse
         * @description Response for logout endpoint.
         */
        LogoutResponse: {
            /** Message */
            message: string;
        };
        /** LogsRequest */
        LogsRequest: {
            /**
             * Max Chars
             * @default 1000
             */
            max_chars: number;
        };
        /** ModelSettings */
        ModelSettings: {
            /**
             * Enabled
             * @default true
             */
            enabled: boolean;
            /** Max Tokens */
            max_tokens?: number | null;
            /** Model Id */
            model_id: string;
            /** Name */
            name: string;
            /** Provider */
            provider: string;
            /**
             * Temperature
             * @default 0.7
             */
            temperature: number | null;
        };
        /** NotificationCreate */
        NotificationCreate: {
            /** Body */
            body: string;
            /** Category */
            category?: string | null;
            /**
             * Channel
             * @default in_app
             */
            channel: string | null;
            /** Metadata */
            metadata?: {
                [key: string]: unknown;
            } | null;
            /** Title */
            title: string;
        };
        /** OrchestrationPlan */
        OrchestrationPlan: {
            /**
             * Complexity
             * @default medium
             */
            complexity: string;
            /**
             * Estimated Duration
             * @default 0
             */
            estimated_duration: number;
            /** Steps */
            steps: components["schemas"]["OrchestrationStep"][];
        };
        /** OrchestrationStep */
        OrchestrationStep: {
            /**
             * Dependencies
             * @default []
             */
            dependencies: string[];
            /** Goblin */
            goblin: string;
            /** Task */
            task: string;
        };
        /** ParseOrchestrationRequest */
        ParseOrchestrationRequest: {
            /** Default Goblin */
            default_goblin?: string | null;
            /** Text */
            text: string;
        };
        /** ParseRequest */
        ParseRequest: {
            /** Default Goblin */
            default_goblin?: string | null;
            /** Text */
            text: string;
        };
        /** PasskeyAuthRequest */
        PasskeyAuthRequest: {
            /** Authenticator Data */
            authenticator_data: string;
            /** Client Data Json */
            client_data_json: string;
            /** Credential Id */
            credential_id: string;
            /**
             * Email
             * Format: email
             */
            email: string;
            /** Signature */
            signature: string;
        };
        /** PasskeyRegistrationRequest */
        PasskeyRegistrationRequest: {
            /** Credential Id */
            credential_id: string;
            /**
             * Email
             * Format: email
             */
            email: string;
            /** Public Key */
            public_key: string;
        };
        /** PreferencesResponse */
        PreferencesResponse: {
            /** Default Model */
            default_model: string | null;
            /** Default Provider */
            default_provider: string | null;
            /**
             * Familymode
             * @default false
             */
            familyMode: boolean;
            /** Language */
            language: string | null;
            /** Notifications Enabled */
            notifications_enabled: boolean;
            /** Other */
            other: {
                [key: string]: components["schemas"]["JsonValue"];
            } | null;
            /**
             * Summaries
             * @default true
             */
            summaries: boolean;
            /** Theme */
            theme: string | null;
        };
        /** PreferencesUpdate */
        PreferencesUpdate: {
            /** Default Model */
            default_model?: string | null;
            /** Default Provider */
            default_provider?: string | null;
            /** Familymode */
            familyMode?: boolean | null;
            /** Language */
            language?: string | null;
            /** Notifications */
            notifications?: boolean | null;
            /** Notifications Enabled */
            notifications_enabled?: boolean | null;
            /** Other */
            other?: {
                [key: string]: components["schemas"]["JsonValue"];
            } | null;
            /** Summaries */
            summaries?: boolean | null;
            /** Theme */
            theme?: string | null;
        };
        /** ProfileResponse */
        ProfileResponse: {
            /** Avatar Url */
            avatar_url: string | null;
            /** Email */
            email: string;
            /** Id */
            id: string;
            /** Name */
            name: string | null;
        };
        /** ProfileUpdate */
        ProfileUpdate: {
            /** Avatar Url */
            avatar_url?: string | null;
            /** Email */
            email?: string | null;
            /** Name */
            name?: string | null;
        };
        /** ProviderConnectionResponse */
        ProviderConnectionResponse: {
            /** Connected */
            connected: boolean;
            /** Message */
            message: string;
            /** Status */
            status: string;
        };
        /** ProviderSettings */
        ProviderSettings: {
            /** Api Key */
            api_key?: string | null;
            /** Base Url */
            base_url?: string | null;
            /**
             * Enabled
             * @default true
             */
            enabled: boolean;
            /** Endpoint */
            endpoint?: string | null;
            /**
             * Models
             * @default []
             */
            models: string[];
            /** Name */
            name: string;
            /** Priority */
            priority?: number | null;
            /** Weight */
            weight?: number | null;
        };
        /**
         * RefreshTokenRequest
         * @description Request to refresh access token.
         */
        RefreshTokenRequest: {
            /** Refresh Token */
            refresh_token?: string | null;
        };
        /** RouteTaskRequest */
        RouteTaskRequest: {
            /**
             * Max Retries
             * @default 2
             */
            max_retries: number | null;
            /** Payload */
            payload: {
                [key: string]: unknown;
            };
            /**
             * Prefer Cost
             * @default false
             */
            prefer_cost: boolean | null;
            /**
             * Prefer Local
             * @default false
             */
            prefer_local: boolean | null;
            /**
             * Stream
             * @default false
             */
            stream: boolean | null;
            /** Task Type */
            task_type: string;
        };
        /** SandboxHealthResponse */
        SandboxHealthResponse: {
            /** Enabled */
            enabled: boolean;
            /** Image Configured */
            image_configured: boolean;
            /** Message */
            message?: string | null;
            /** Queue Depth */
            queue_depth: number;
            /** Redis Connected */
            redis_connected: boolean;
            /** Redis Error */
            redis_error?: string | null;
            /** Status */
            status: string;
        };
        /** SandboxJobSummary */
        SandboxJobSummary: {
            /** Created At */
            created_at: string;
            /** Error */
            error?: string | null;
            /** Exit Code */
            exit_code?: number | null;
            /** Finished At */
            finished_at?: string | null;
            /** Job Id */
            job_id: string;
            /** Language */
            language: string;
            /** Started At */
            started_at?: string | null;
            /** Status */
            status: string;
        };
        /** SandboxJobsResponse */
        SandboxJobsResponse: {
            /** Jobs */
            jobs: components["schemas"]["SandboxJobSummary"][];
            /** Total */
            total: number;
        };
        /** SearchQuery */
        SearchQuery: {
            /** Collection Name */
            collection_name?: string | null;
            /**
             * K
             * @default 10
             */
            k: number;
            /** N Results */
            n_results?: number | null;
            /** Query */
            query: string;
            /** Source Types */
            source_types?: string[] | null;
        };
        /** SearchResponse */
        SearchResponse: {
            /** Results */
            results: components["schemas"]["SearchResult"][];
            /** Total Results */
            total_results: number;
        };
        /** SearchResult */
        SearchResult: {
            /** Document */
            document: string;
            /** Id */
            id: string;
            /** Metadata */
            metadata?: {
                [key: string]: unknown;
            } | null;
            /** Score */
            score?: number | null;
            /** Source Id */
            source_id?: string | null;
            /** Source Type */
            source_type: string;
        };
        /**
         * SecretRequest
         * @description Request model for creating/updating secrets.
         */
        SecretRequest: {
            /**
             * Data
             * @description Secret data as key-value pairs
             */
            data: {
                [key: string]: string;
            };
            /**
             * Metadata
             * @description Optional custom metadata
             */
            metadata?: {
                [key: string]: unknown;
            } | null;
            /**
             * Path
             * @description Secret path within the mount point
             */
            path: string;
            /**
             * Version
             * @description Optional version for conditional updates
             */
            version?: number | null;
        };
        /**
         * SecretResponse
         * @description Response model for secret operations.
         */
        SecretResponse: {
            /** Backend Specific */
            backend_specific?: {
                [key: string]: unknown;
            } | null;
            /** Data */
            data: {
                [key: string]: string;
            };
            /** Metadata */
            metadata?: {
                [key: string]: unknown;
            } | null;
            /** Path */
            path: string;
        };
        /** SemanticSendMessageRequest */
        SemanticSendMessageRequest: {
            /** Department */
            department?: string | null;
            /**
             * Max Age Hours
             * @default 168
             */
            max_age_hours: number;
            /**
             * Max Context Tokens
             * @default 1500
             */
            max_context_tokens: number;
            /** Message */
            message: string;
            /** Metadata */
            metadata?: {
                [key: string]: unknown;
            } | null;
            /** Model */
            model?: string | null;
            /** Provider */
            provider?: string | null;
            /**
             * Retrieval K
             * @default 5
             */
            retrieval_k: number;
            /**
             * Stream
             * @default false
             */
            stream: boolean | null;
            /**
             * Use Semantic Retrieval
             * @default true
             */
            use_semantic_retrieval: boolean;
        };
        /** SemanticSendMessageResponse */
        SemanticSendMessageResponse: {
            /** Context Details */
            context_details?: {
                [key: string]: unknown;
            } | null;
            /** Context Used */
            context_used: boolean;
            /**
             * Department
             * @default general
             */
            department: string;
            /** Message Id */
            message_id: string;
            /** Response */
            response: string;
            /** Timestamp */
            timestamp: string;
        };
        /** SendMessageRequest */
        SendMessageRequest: {
            /** Attachment Ids */
            attachment_ids?: string[] | null;
            /** Department */
            department?: string | null;
            /**
             * Enable Context Assembly
             * @default true
             */
            enable_context_assembly: boolean | null;
            /** Message */
            message: string;
            /** Metadata */
            metadata?: {
                [key: string]: unknown;
            } | null;
            /** Mode */
            mode?: string | null;
            /** Model */
            model?: string | null;
            /** Provider */
            provider?: string | null;
            /**
             * Stream
             * @default false
             */
            stream: boolean | null;
        };
        /** SendMessageResponse */
        SendMessageResponse: {
            /** Correlation Id */
            correlation_id?: string | null;
            /** Cost Usd */
            cost_usd?: number | null;
            /** Department */
            department: string;
            /**
             * Department Reason
             * @default
             */
            department_reason: string;
            /** Message Id */
            message_id: string;
            /** Response */
            response: string;
            /** Timestamp */
            timestamp: string;
            /** Usage */
            usage?: {
                [key: string]: unknown;
            } | null;
            /** Visualizations */
            visualizations?: {
                [key: string]: unknown;
            }[] | null;
        };
        /** SettingsResponse */
        SettingsResponse: {
            /** Default Model */
            default_model?: string | null;
            /** Default Provider */
            default_provider?: string | null;
            /** Models */
            models: components["schemas"]["ModelSettings"][];
            /** Providers */
            providers: components["schemas"]["ProviderSettings"][];
        };
        /** SettingsUpdatedResponse */
        SettingsUpdatedResponse: {
            /** Message */
            message: string;
            /** Scope */
            scope?: string | null;
            /** Settings */
            settings: {
                [key: string]: unknown;
            };
        };
        /** SimpleChatMessage */
        SimpleChatMessage: {
            /** Content */
            content: string;
            /** Role */
            role: string;
        };
        /** SimpleChatRequest */
        SimpleChatRequest: {
            /** Messages */
            messages: components["schemas"]["SimpleChatMessage"][];
            /** Model */
            model?: string | null;
            /** Provider */
            provider?: string | null;
            /**
             * Stream
             * @default false
             */
            stream: boolean | null;
        };
        /** SimpleChatResponse */
        SimpleChatResponse: {
            /** Error */
            error?: string | null;
            /** Model */
            model?: string | null;
            /** Ok */
            ok: boolean;
            /** Provider */
            provider?: string | null;
            /** Result */
            result?: {
                [key: string]: unknown;
            } | null;
        };
        /** StreamChatRequest */
        StreamChatRequest: {
            /** Conversation Id */
            conversation_id: string;
            /** Department */
            department?: string | null;
            /** Message */
            message: string;
            /** Metadata */
            metadata?: {
                [key: string]: unknown;
            } | null;
            /** Model */
            model?: string | null;
            /** Provider */
            provider?: string | null;
        };
        /** SubmitJobRequest */
        SubmitJobRequest: {
            /** Language */
            language: string;
            /**
             * Runtime Args
             * @default
             */
            runtime_args: string | null;
            /** Source */
            source: string;
            /**
             * Timeout
             * @default 10
             */
            timeout: number | null;
        };
        /** SubmitJobResponse */
        SubmitJobResponse: {
            /** Job Id */
            job_id: string;
        };
        /** SuccessEnvelope[AgentTaskEventsResponse] */
        SuccessEnvelope_AgentTaskEventsResponse_: {
            data: components["schemas"]["AgentTaskEventsResponse"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[AgentTaskRecord] */
        SuccessEnvelope_AgentTaskRecord_: {
            data: components["schemas"]["AgentTaskRecord"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[AgentTaskSubmitResponse] */
        SuccessEnvelope_AgentTaskSubmitResponse_: {
            data: components["schemas"]["AgentTaskSubmitResponse"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[ArtifactListResponse] */
        SuccessEnvelope_ArtifactListResponse_: {
            data: components["schemas"]["ArtifactListResponse"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[CancelJobResponse] */
        SuccessEnvelope_CancelJobResponse_: {
            data: components["schemas"]["CancelJobResponse"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[ChatSettingsResponse] */
        SuccessEnvelope_ChatSettingsResponse_: {
            data: components["schemas"]["ChatSettingsResponse"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[CollectionsResponse] */
        SuccessEnvelope_CollectionsResponse_: {
            data: components["schemas"]["CollectionsResponse"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[ContextualChatResponse] */
        SuccessEnvelope_ContextualChatResponse_: {
            data: components["schemas"]["ContextualChatResponse"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[CreateConversationResponse] */
        SuccessEnvelope_CreateConversationResponse_: {
            data: components["schemas"]["CreateConversationResponse"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[Dict[str, Any]] */
        SuccessEnvelope_Dict_str__Any__: {
            /** Data */
            data: {
                [key: string]: unknown;
            };
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[EstimateTokensResponse] */
        SuccessEnvelope_EstimateTokensResponse_: {
            data: components["schemas"]["EstimateTokensResponse"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[EventEnvelope[dict[str, JsonValue]]] */
        SuccessEnvelope_EventEnvelope_dict_str__JsonValue___: {
            data: components["schemas"]["EventEnvelope_dict_str__JsonValue__"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[EventLogListResponse] */
        SuccessEnvelope_EventLogListResponse_: {
            data: components["schemas"]["EventLogListResponse"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[FileUploadResponse] */
        SuccessEnvelope_FileUploadResponse_: {
            data: components["schemas"]["FileUploadResponse"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[GitHubWebhookResponse] */
        SuccessEnvelope_GitHubWebhookResponse_: {
            data: components["schemas"]["GitHubWebhookResponse"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[IndexResponse] */
        SuccessEnvelope_IndexResponse_: {
            data: components["schemas"]["IndexResponse"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[JobLogsResponse] */
        SuccessEnvelope_JobLogsResponse_: {
            data: components["schemas"]["JobLogsResponse"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[JobStatus] */
        SuccessEnvelope_JobStatus_: {
            data: components["schemas"]["JobStatus"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[List[Dict[str, Any]]] */
        SuccessEnvelope_List_Dict_str__Any___: {
            /** Data */
            data: {
                [key: string]: unknown;
            }[];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[LogoutResponse] */
        SuccessEnvelope_LogoutResponse_: {
            data: components["schemas"]["LogoutResponse"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[PreferencesResponse] */
        SuccessEnvelope_PreferencesResponse_: {
            data: components["schemas"]["PreferencesResponse"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[ProfileResponse] */
        SuccessEnvelope_ProfileResponse_: {
            data: components["schemas"]["ProfileResponse"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[ProviderConnectionResponse] */
        SuccessEnvelope_ProviderConnectionResponse_: {
            data: components["schemas"]["ProviderConnectionResponse"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[SandboxHealthResponse] */
        SuccessEnvelope_SandboxHealthResponse_: {
            data: components["schemas"]["SandboxHealthResponse"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[SandboxJobsResponse] */
        SuccessEnvelope_SandboxJobsResponse_: {
            data: components["schemas"]["SandboxJobsResponse"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[SearchResponse] */
        SuccessEnvelope_SearchResponse_: {
            data: components["schemas"]["SearchResponse"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[SendMessageResponse] */
        SuccessEnvelope_SendMessageResponse_: {
            data: components["schemas"]["SendMessageResponse"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[SettingsResponse] */
        SuccessEnvelope_SettingsResponse_: {
            data: components["schemas"]["SettingsResponse"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[SettingsUpdatedResponse] */
        SuccessEnvelope_SettingsUpdatedResponse_: {
            data: components["schemas"]["SettingsUpdatedResponse"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[SubmitJobResponse] */
        SuccessEnvelope_SubmitJobResponse_: {
            data: components["schemas"]["SubmitJobResponse"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[SupportResponse] */
        SuccessEnvelope_SupportResponse_: {
            data: components["schemas"]["SupportResponse"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[TokenValidationResponse] */
        SuccessEnvelope_TokenValidationResponse_: {
            data: components["schemas"]["TokenValidationResponse"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[TokenWithRefresh] */
        SuccessEnvelope_TokenWithRefresh_: {
            data: components["schemas"]["TokenWithRefresh"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[TriageResponse] */
        SuccessEnvelope_TriageResponse_: {
            data: components["schemas"]["TriageResponse"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[User] */
        SuccessEnvelope_User_: {
            data: components["schemas"]["User"];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SuccessEnvelope[list[ConversationInfo]] */
        SuccessEnvelope_list_ConversationInfo__: {
            /** Data */
            data: components["schemas"]["ConversationInfo"][];
            /**
             * Success
             * @default true
             */
            success: boolean;
        };
        /** SupportMessage */
        SupportMessage: {
            /** Attachment Url */
            attachment_url?: string | null;
            /** Category */
            category?: string | null;
            /** Email */
            email?: string | null;
            /** Message */
            message: string;
        };
        /** SupportResponse */
        SupportResponse: {
            /** Id */
            id: string;
            /** Status */
            status: string;
            /** Timestamp */
            timestamp: string;
        };
        /**
         * TestMessageRequest
         * @description Request to test message classification and decision matrix
         */
        TestMessageRequest: {
            /** Content */
            content: string;
            /** Conversation Id */
            conversation_id?: string | null;
            /** Metadata */
            metadata?: {
                [key: string]: unknown;
            } | null;
            /**
             * Role
             * @default user
             */
            role: string;
            /** User Id */
            user_id?: string | null;
        };
        /**
         * TestMessageResponse
         * @description Response from message testing
         */
        TestMessageResponse: {
            /** Classification */
            classification: {
                [key: string]: unknown;
            };
            /** Decision */
            decision: {
                [key: string]: unknown;
            };
            /** Execution */
            execution: {
                [key: string]: unknown;
            };
            /** Message Id */
            message_id: string;
            /** Processed At */
            processed_at: string;
        };
        /** TokenValidationRequest */
        TokenValidationRequest: {
            /** Token */
            token: string;
        };
        /**
         * TokenValidationResponse
         * @description Response for token validation endpoint.
         */
        TokenValidationResponse: {
            user?: components["schemas"]["User"] | null;
            /** Valid */
            valid: boolean;
        };
        /**
         * TokenWithRefresh
         * @description Token response that includes refresh token.
         */
        TokenWithRefresh: {
            /** Access Token */
            access_token: string;
            /** Expires In */
            expires_in: number;
            /** Refresh Token */
            refresh_token: string;
            /** Token Type */
            token_type: string;
            user: components["schemas"]["User"];
        };
        /** TriageRequest */
        TriageRequest: {
            /** Context */
            context?: string | null;
            /** Description */
            description: string;
        };
        /** TriageResponse */
        TriageResponse: {
            /** Id */
            id: string;
            /** Issue Number */
            issue_number?: number | null;
            /** Issue Url */
            issue_url?: string | null;
            triage: components["schemas"]["TriageResult"];
        };
        /** TriageResult */
        TriageResult: {
            /** Affected Service */
            affected_service: string;
            /** Category */
            category: string;
            /** Cleaned Description */
            cleaned_description: string;
            /** Priority */
            priority: string;
            /** Stack Trace */
            stack_trace?: string | null;
            /** Title */
            title: string;
        };
        /** UpdateConversationTitleRequest */
        UpdateConversationTitleRequest: {
            /** Title */
            title: string;
        };
        /** User */
        User: {
            /** Email */
            email: string;
            /** Google Id */
            google_id?: string | null;
            /** Id */
            id: string;
            /** Name */
            name?: string | null;
            /** Passkey Credential Id */
            passkey_credential_id?: string | null;
            /** Passkey Public Key */
            passkey_public_key?: string | null;
        };
        /**
         * UserCreate
         * @description User registration request model with required CSRF token.
         */
        UserCreate: {
            /** Csrf Token */
            csrf_token?: string | null;
            /**
             * Email
             * Format: email
             */
            email: string;
            /** Name */
            name?: string | null;
            /** Password */
            password: string;
        };
        /**
         * UserLogin
         * @description User login request model with required CSRF token.
         */
        UserLogin: {
            /** Csrf Token */
            csrf_token?: string | null;
            /**
             * Email
             * Format: email
             */
            email: string;
            /** Password */
            password: string;
        };
        /** ValidationError */
        ValidationError: {
            /** Context */
            ctx?: Record<string, never>;
            /** Input */
            input?: unknown;
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
        };
        /** StreamTaskRequest */
        api__api_models__StreamTaskRequest: {
            /** Code */
            code?: string | null;
            /** Goblin */
            goblin: string;
            /** Model */
            model?: string | null;
            /** Provider */
            provider?: string | null;
            /** Task */
            task: string;
        };
        /**
         * StreamTaskRequest
         * @description Request model for streaming task execution
         */
        api__stream_router__StreamTaskRequest: {
            /** Messages */
            messages: {
                [key: string]: string;
            }[];
            /** Model */
            model?: string | null;
            /** Provider */
            provider?: string | null;
            /** Task Id */
            task_id: string;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
