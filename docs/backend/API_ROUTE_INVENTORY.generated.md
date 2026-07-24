---
title: "API Route Inventory"
description: "Generated backend route inventory from the checked-in route manifest and OpenAPI schema"
---

# API Route Inventory

Generated from `packages/sdk/openapi/routes.json` and `packages/sdk/openapi/openapi.json`.

## Snapshot

- **Mounted paths**: 191
- **Operations**: 204
- **OpenAPI paths**: 191
- **Versioned operations (`/api/v1`)**: 200
- **Legacy dual-mount operations**: 1
- **Deprecated operations**: 4
- **Hidden manifest operations**: 1

## Route groups

| Group | Operations |
| --- | ---: |
| `/api/v1` | 200 |
| `/` | 1 |
| `/health` | 1 |
| `/metrics` | 1 |
| `/test` | 1 |

## Versioned public routes

The `/api/v1` routes are the canonical public API surface.

| Method | Path | Logical Path | Status | Replaced By | Summary | Tags | Operation ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GET | /api/v1/account/chat-settings | /account/chat-settings | stable | - | Get Chat Settings | account | get_chat_settings_api_v1_account_chat_settings_get |
| PUT | /api/v1/account/chat-settings | /account/chat-settings | stable | - | Save Chat Settings | account | save_chat_settings_api_v1_account_chat_settings_put |
| GET | /api/v1/account/preferences | /account/preferences | stable | - | Get Preferences | account | get_preferences_api_v1_account_preferences_get |
| PUT | /api/v1/account/preferences | /account/preferences | stable | - | Save Preferences | account | save_preferences_api_v1_account_preferences_put |
| GET | /api/v1/account/profile | /account/profile | stable | - | Get Profile | account | get_profile_api_v1_account_profile_get |
| PUT | /api/v1/account/profile | /account/profile | stable | - | Save Profile | account | save_profile_api_v1_account_profile_put |
| POST | /api/v1/agent/task | /agent/task | stable | - | Submit Agent Task | agent | submit_agent_task_api_v1_agent_task_post |
| POST | /api/v1/agent/task/github-webhook | /agent/task/github-webhook | stable | - | Submit Github Issue Webhook | agent | submit_github_issue_webhook_api_v1_agent_task_github_webhook_post |
| GET | /api/v1/agent/task/{task_id} | /agent/task/{task_id} | stable | - | Get Agent Task | agent | get_agent_task_api_v1_agent_task__task_id__get |
| GET | /api/v1/agent/task/{task_id}/events | /agent/task/{task_id}/events | stable | - | Get Agent Task Events | agent | get_agent_task_events_api_v1_agent_task__task_id__events_get |
| POST | /api/v1/agent/task/{task_id}/events | /agent/task/{task_id}/events | stable | - | Append Agent Task Event | agent | append_agent_task_event_api_v1_agent_task__task_id__events_post |
| DELETE | /api/v1/api-keys/{provider} | /api-keys/{provider} | stable | - | Delete Api Key | api-keys | delete_api_key_api_v1_api_keys__provider__delete |
| GET | /api/v1/api-keys/{provider} | /api-keys/{provider} | stable | - | Get Api Key | api-keys | get_api_key_api_v1_api_keys__provider__get |
| POST | /api/v1/api-keys/{provider} | /api-keys/{provider} | stable | - | Store Api Key | api-keys | store_api_key_api_v1_api_keys__provider__post |
| POST | /api/v1/api/chat | /api/chat | stable | - | Simple Chat | api | simple_chat_api_v1_api_chat_post |
| GET | /api/v1/api/feedback/stats | /api/feedback/stats | stable | - | Get Feedback Stats | api, routing | get_feedback_stats_api_v1_api_feedback_stats_get |
| POST | /api/v1/api/generate | /api/generate | stable | - | Generate | api | generate_api_v1_api_generate_post |
| GET | /api/v1/api/goblins | /api/goblins | stable | - | Get Goblins | api | get_goblins_api_v1_api_goblins_get |
| GET | /api/v1/api/history/{goblin_id} | /api/history/{goblin_id} | stable | - | Get Goblin History | api | get_goblin_history_api_v1_api_history__goblin_id__get |
| POST | /api/v1/api/orchestrate/execute | /api/orchestrate/execute | stable | - | Execute Orchestration | api | execute_orchestration_api_v1_api_orchestrate_execute_post |
| POST | /api/v1/api/orchestrate/parse | /api/orchestrate/parse | stable | - | Parse Orchestration | api | parse_orchestration_api_v1_api_orchestrate_parse_post |
| GET | /api/v1/api/orchestrate/plans/{plan_id} | /api/orchestrate/plans/{plan_id} | stable | - | Get Orchestration Plan | api | get_orchestration_plan_api_v1_api_orchestrate_plans__plan_id__get |
| POST | /api/v1/api/privacy/consent/rag | /api/privacy/consent/rag | stable | - | Update Rag Consent | privacy, gdpr, ccpa | update_rag_consent_api_v1_api_privacy_consent_rag_post |
| GET | /api/v1/api/privacy/data-summary | /api/privacy/data-summary | stable | - | Get Data Summary | privacy, gdpr, ccpa | get_data_summary_api_v1_api_privacy_data_summary_get |
| DELETE | /api/v1/api/privacy/delete | /api/privacy/delete | stable | - | Delete User Data | privacy, gdpr, ccpa | delete_user_data_api_v1_api_privacy_delete_delete |
| POST | /api/v1/api/privacy/export | /api/privacy/export | stable | - | Export User Data | privacy, gdpr, ccpa | export_user_data_api_v1_api_privacy_export_post |
| POST | /api/v1/api/route_task | /api/route_task | stable | - | Route Task | api | route_task_api_v1_api_route_task_post |
| POST | /api/v1/api/route_task_stream_cancel/{stream_id} | /api/route_task_stream_cancel/{stream_id} | stable | - | Cancel Stream Task | api | cancel_stream_task_api_v1_api_route_task_stream_cancel__stream_id__post |
| GET | /api/v1/api/route_task_stream_poll/{stream_id} | /api/route_task_stream_poll/{stream_id} | stable | - | Poll Stream Task | api | poll_stream_task_api_v1_api_route_task_stream_poll__stream_id__get |
| POST | /api/v1/api/route_task_stream_start | /api/route_task_stream_start | stable | - | Start Stream Task | api | start_stream_task_api_v1_api_route_task_stream_start_post |
| POST | /api/v1/api/routing/feedback | /api/routing/feedback | stable | - | Submit Routing Feedback | api, routing | submit_routing_feedback_api_v1_api_routing_feedback_post |
| GET | /api/v1/api/stats/{goblin_id} | /api/stats/{goblin_id} | stable | - | Get Goblin Stats | api | get_goblin_stats_api_v1_api_stats__goblin_id__get |
| GET | /api/v1/auth/csrf-token | /auth/csrf-token | stable | - | Get Csrf Token | auth | get_csrf_token_api_v1_auth_csrf_token_get |
| GET | /api/v1/auth/csrf/token | /auth/csrf/token | stable | - | Get Csrf Token Legacy | auth | get_csrf_token_legacy_api_v1_auth_csrf_token_get |
| POST | /api/v1/auth/google | /auth/google | stable | - | Google Auth | auth | google_auth_api_v1_auth_google_post |
| POST | /api/v1/auth/google/callback | /auth/google/callback | stable | - | Google Auth Callback | auth | google_auth_callback_api_v1_auth_google_callback_post |
| GET | /api/v1/auth/google/url | /auth/google/url | stable | - | Get Google Auth Url | auth | get_google_auth_url_api_v1_auth_google_url_get |
| POST | /api/v1/auth/login | /auth/login | stable | - | Login | auth | login_api_v1_auth_login_post |
| POST | /api/v1/auth/logout | /auth/logout | stable | - | Logout | auth | logout_api_v1_auth_logout_post |
| GET | /api/v1/auth/me | /auth/me | stable | - | Get Current User Info | auth | get_current_user_info_api_v1_auth_me_get |
| POST | /api/v1/auth/passkey/auth | /auth/passkey/auth | stable | - | Authenticate Passkey | auth | authenticate_passkey_api_v1_auth_passkey_auth_post |
| POST | /api/v1/auth/passkey/challenge | /auth/passkey/challenge | stable | - | Get Passkey Challenge | auth | get_passkey_challenge_api_v1_auth_passkey_challenge_post |
| POST | /api/v1/auth/passkey/register | /auth/passkey/register | stable | - | Register Passkey | auth | register_passkey_api_v1_auth_passkey_register_post |
| POST | /api/v1/auth/refresh | /auth/refresh | stable | - | Refresh Token Endpoint | auth | refresh_token_endpoint_api_v1_auth_refresh_post |
| POST | /api/v1/auth/register | /auth/register | stable | - | Register | auth | register_api_v1_auth_register_post |
| GET | /api/v1/auth/validate | /auth/validate | stable | - | Validate Token Legacy | auth | validate_token_legacy_api_v1_auth_validate_get |
| POST | /api/v1/auth/validate | /auth/validate | stable | - | Validate Token | auth | validate_token_api_v1_auth_validate_post |
| POST | /api/v1/chat/contextual-chat | /chat/contextual-chat | stable | - | Contextual Chat | chat | contextual_chat_api_v1_chat_contextual_chat_post |
| GET | /api/v1/chat/conversations | /chat/conversations | stable | - | List Conversations | chat | list_conversations_api_v1_chat_conversations_get |
| POST | /api/v1/chat/conversations | /chat/conversations | stable | - | Create Conversation | chat | create_conversation_api_v1_chat_conversations_post |
| DELETE | /api/v1/chat/conversations/{conversation_id} | /chat/conversations/{conversation_id} | stable | - | Delete Conversation | chat | delete_conversation_api_v1_chat_conversations__conversation_id__delete |
| GET | /api/v1/chat/conversations/{conversation_id} | /chat/conversations/{conversation_id} | stable | - | Get Conversation | chat | get_conversation_api_v1_chat_conversations__conversation_id__get |
| POST | /api/v1/chat/conversations/{conversation_id}/import | /chat/conversations/{conversation_id}/import | stable | - | Import Conversation Messages | chat | import_conversation_messages_api_v1_chat_conversations__conversation_id__import_post |
| POST | /api/v1/chat/conversations/{conversation_id}/messages | /chat/conversations/{conversation_id}/messages | stable | - | Send Message | chat | send_message_api_v1_chat_conversations__conversation_id__messages_post |
| PUT | /api/v1/chat/conversations/{conversation_id}/title | /chat/conversations/{conversation_id}/title | stable | - | Update Conversation Title | chat | update_conversation_title_api_v1_chat_conversations__conversation_id__title_put |
| GET | /api/v1/chat/debug/context-assembly | /chat/debug/context-assembly | stable | - | Debug Context Assembly | chat | debug_context_assembly_api_v1_chat_debug_context_assembly_get |
| POST | /api/v1/chat/estimate-tokens | /chat/estimate-tokens | stable | - | Estimate Tokens | chat | estimate_tokens_api_v1_chat_estimate_tokens_post |
| GET | /api/v1/chat/files/{file_id} | /chat/files/{file_id} | stable | - | Download File | chat | download_file_api_v1_chat_files__file_id__get |
| POST | /api/v1/chat/stream | /chat/stream | stable | - | Stream Chat | chat | stream_chat_api_v1_chat_stream_post |
| POST | /api/v1/chat/upload-file | /chat/upload-file | stable | - | Upload File | chat | upload_file_api_v1_chat_upload_file_post |
| GET | /api/v1/debug/api/migration-metrics | /debug/api/migration-metrics | stable | - | Get Api Migration Metrics | debug | get_api_migration_metrics_api_v1_debug_api_migration_metrics_get |
| GET | /api/v1/debug/context/health/{user_id} | /debug/context/health/{user_id} | stable | - | Get Context Health | debug | get_context_health_api_v1_debug_context_health__user_id__get |
| GET | /api/v1/debug/context/history | /debug/context/history | stable | - | Get Context History | debug | get_context_history_api_v1_debug_context_history_get |
| GET | /api/v1/debug/context/replay/{request_id} | /debug/context/replay/{request_id} | stable | - | Replay Context | debug | replay_context_api_v1_debug_context_replay__request_id__get |
| GET | /api/v1/debug/context/snapshot/{request_id} | /debug/context/snapshot/{request_id} | stable | - | Get Context Snapshot | debug | get_context_snapshot_api_v1_debug_context_snapshot__request_id__get |
| GET | /api/v1/debug/events | /debug/events | stable | - | List Domain Events | debug | list_domain_events_api_v1_debug_events_get |
| GET | /api/v1/debug/events/{event_id} | /debug/events/{event_id} | stable | - | Get Domain Event | debug | get_domain_event_api_v1_debug_events__event_id__get |
| GET | /api/v1/debug/memory/health/{user_id} | /debug/memory/health/{user_id} | stable | - | Get Memory Health | debug | get_memory_health_api_v1_debug_memory_health__user_id__get |
| GET | /api/v1/debug/memory/promotions/search | /debug/memory/promotions/search | stable | - | Search Memory Promotions | debug | search_memory_promotions_api_v1_debug_memory_promotions_search_get |
| GET | /api/v1/debug/memory/promotions/stats | /debug/memory/promotions/stats | stable | - | Get Memory Promotion Stats | debug | get_memory_promotion_stats_api_v1_debug_memory_promotions_stats_get |
| GET | /api/v1/debug/memory/user/{user_id} | /debug/memory/user/{user_id} | stable | - | Get User Memory | debug | get_user_memory_api_v1_debug_memory_user__user_id__get |
| GET | /api/v1/debug/model-usage | /debug/model-usage | stable | - | Get Model Usage | debug | get_model_usage_api_v1_debug_model_usage_get |
| GET | /api/v1/debug/retrieval-metrics/cache-hit-rate | /debug/retrieval-metrics/cache-hit-rate | stable | - | Get Cache Hit Rate | observability, retrieval-metrics | get_cache_hit_rate_api_v1_debug_retrieval_metrics_cache_hit_rate_get |
| GET | /api/v1/debug/retrieval-metrics/embedding-dedup | /debug/retrieval-metrics/embedding-dedup | stable | - | Get Embedding Dedup | observability, retrieval-metrics | get_embedding_dedup_api_v1_debug_retrieval_metrics_embedding_dedup_get |
| GET | /api/v1/debug/retrieval-metrics/failures | /debug/retrieval-metrics/failures | stable | - | Get Failure Summary | observability, retrieval-metrics | get_failure_summary_api_v1_debug_retrieval_metrics_failures_get |
| GET | /api/v1/debug/retrieval-metrics/report | /debug/retrieval-metrics/report | stable | - | Get Full Report | observability, retrieval-metrics | get_full_report_api_v1_debug_retrieval_metrics_report_get |
| GET | /api/v1/debug/retrieval-metrics/tier-latency | /debug/retrieval-metrics/tier-latency | stable | - | Get Tier Latency Breakdown | observability, retrieval-metrics | get_tier_latency_breakdown_api_v1_debug_retrieval_metrics_tier_latency_get |
| GET | /api/v1/debug/retrieval-metrics/token-accuracy | /debug/retrieval-metrics/token-accuracy | stable | - | Get Token Budget Accuracy | observability, retrieval-metrics | get_token_budget_accuracy_api_v1_debug_retrieval_metrics_token_accuracy_get |
| GET | /api/v1/debug/retrieval/history | /debug/retrieval/history | stable | - | Get Retrieval History | debug | get_retrieval_history_api_v1_debug_retrieval_history_get |
| GET | /api/v1/debug/retrieval/quality/{user_id} | /debug/retrieval/quality/{user_id} | stable | - | Get Retrieval Quality | debug | get_retrieval_quality_api_v1_debug_retrieval_quality__user_id__get |
| GET | /api/v1/debug/retrieval/stats | /debug/retrieval/stats | stable | - | Get Retrieval Stats | debug | get_retrieval_stats_api_v1_debug_retrieval_stats_get |
| GET | /api/v1/debug/retrieval/trace/{request_id} | /debug/retrieval/trace/{request_id} | stable | - | Get Retrieval Trace | debug | get_retrieval_trace_api_v1_debug_retrieval_trace__request_id__get |
| POST | /api/v1/debug/suggest | /debug/suggest | stable | - | Get Debug Suggestion | debug-suggestions | get_debug_suggestion_api_v1_debug_suggest_post |
| POST | /api/v1/debug/system/observability/clear-cache | /debug/system/observability/clear-cache | stable | - | Clear Observability Cache | debug | clear_observability_cache_api_v1_debug_system_observability_clear_cache_post |
| GET | /api/v1/debug/system/observability/health | /debug/system/observability/health | stable | - | Get System Health | debug | get_system_health_api_v1_debug_system_observability_health_get |
| POST | /api/v1/debug/system/observability/reset-counters | /debug/system/observability/reset-counters | stable | - | Reset Observability Counters | debug | reset_observability_counters_api_v1_debug_system_observability_reset_counters_post |
| GET | /api/v1/debug/system/observability/summary | /debug/system/observability/summary | stable | - | Get Observability Summary | debug | get_observability_summary_api_v1_debug_system_observability_summary_get |
| GET | /api/v1/debug/tool-trace/conversation/{conversation_id} | /debug/tool-trace/conversation/{conversation_id} | stable | - | Get Conversation Tool Traces | debug | get_conversation_tool_traces_api_v1_debug_tool_trace_conversation__conversation_id__get |
| GET | /api/v1/debug/tool-trace/stats | /debug/tool-trace/stats | stable | - | Get Tool Trace Stats | debug | get_tool_trace_stats_api_v1_debug_tool_trace_stats_get |
| GET | /api/v1/debug/tool-trace/{request_id} | /debug/tool-trace/{request_id} | stable | - | Get Tool Trace | debug | get_tool_trace_api_v1_debug_tool_trace__request_id__get |
| GET | /api/v1/debug/write/decisions/search | /debug/write/decisions/search | stable | - | Search Write Decisions | debug | search_write_decisions_api_v1_debug_write_decisions_search_get |
| GET | /api/v1/debug/write/decisions/stats | /debug/write/decisions/stats | stable | - | Get Write Decision Stats | debug | get_write_decision_stats_api_v1_debug_write_decisions_stats_get |
| GET | /api/v1/debug/write/decisions/{conversation_id} | /debug/write/decisions/{conversation_id} | stable | - | Get Write Decisions | debug | get_write_decisions_api_v1_debug_write_decisions__conversation_id__get |
| GET | /api/v1/feature-flags/{flag_key} | /feature-flags/{flag_key} | stable | - | Get Feature Flag | feature-flags | get_feature_flag_api_v1_feature_flags__flag_key__get |
| PUT | /api/v1/feature-flags/{flag_key} | /feature-flags/{flag_key} | stable | - | Upsert Feature Flag | feature-flags | upsert_feature_flag_api_v1_feature_flags__flag_key__put |
| GET | /api/v1/health | /health | stable | - | Health | health | health_check_api_v1_health_get |
| GET | /api/v1/health/all | /health/all | stable | - | Health All | health | health_all_api_v1_health_all_get |
| GET | /api/v1/health/chroma/status | /health/chroma/status | stable | - | Health Chroma | health | health_chroma_api_v1_health_chroma_status_get |
| GET | /api/v1/health/cost-tracking | /health/cost-tracking | stable | - | Health Cost Tracking | health | health_cost_tracking_api_v1_health_cost_tracking_get |
| GET | /api/v1/health/latency-history/{service} | /health/latency-history/{service} | stable | - | Health Latency History | health | health_latency_history_api_v1_health_latency_history__service__get |
| GET | /api/v1/health/live | /health/live | stable | - | Liveness Check | health | liveness_check_api_v1_health_live_get |
| GET | /api/v1/health/mcp/status | /health/mcp/status | stable | - | Health Mcp | health | health_mcp_api_v1_health_mcp_status_get |
| GET | /api/v1/health/raptor/status | /health/raptor/status | stable | - | Health Raptor | health | health_raptor_api_v1_health_raptor_status_get |
| GET | /api/v1/health/ready | /health/ready | stable | - | Readiness Check | health | readiness_check_api_v1_health_ready_get |
| POST | /api/v1/health/retest/{service} | /health/retest/{service} | stable | - | Health Retest | health | health_retest_api_v1_health_retest__service__post |
| GET | /api/v1/health/routing | /health/routing | stable | - | Health Routing | health | health_routing_api_v1_health_routing_get |
| GET | /api/v1/health/sandbox/status | /health/sandbox/status | stable | - | Health Sandbox | health | health_sandbox_api_v1_health_sandbox_status_get |
| GET | /api/v1/health/service-errors/{service} | /health/service-errors/{service} | stable | - | Health Service Errors | health | health_service_errors_api_v1_health_service_errors__service__get |
| GET | /api/v1/health/stream | /health/stream | stable | - | Health Stream | health | health_stream_api_v1_health_stream_get |
| GET | /api/v1/health/streaming | /health/streaming | stable | - | Health Streaming | health | health_streaming_api_v1_health_streaming_get |
| GET | /api/v1/health/{component} | /health/{component} | stable | - | Health Component | health | health_component_api_v1_health__component__get |
| GET | /api/v1/notifications/ | /notifications/ | stable | - | List Notifications | notifications | list_notifications_api_v1_notifications__get |
| POST | /api/v1/notifications/ | /notifications/ | stable | - | Create Notification | notifications | create_notification_api_v1_notifications__post |
| PATCH | /api/v1/notifications/{notification_id}/read | /notifications/{notification_id}/read | stable | - | Mark Notification Read | notifications | mark_notification_read_api_v1_notifications__notification_id__read_patch |
| GET | /api/v1/ops/aggregated | /ops/aggregated | stable | - | Get Aggregated Metrics | operations | get_aggregated_metrics_api_v1_ops_aggregated_get |
| GET | /api/v1/ops/audit/log | /ops/audit/log | stable | - | Get Audit Log | operations | get_audit_log_api_v1_ops_audit_log_get |
| GET | /api/v1/ops/circuit-breakers | /ops/circuit-breakers | stable | - | Circuit Breakers Status | operations | circuit_breakers_status_api_v1_ops_circuit_breakers_get |
| POST | /api/v1/ops/circuit-breakers/{provider_name}/reset | /ops/circuit-breakers/{provider_name}/reset | stable | - | Reset Circuit Breaker | operations | reset_circuit_breaker_api_v1_ops_circuit_breakers__provider_name__reset_post |
| POST | /api/v1/ops/gcs/colab/register | /ops/gcs/colab/register | stable | - | Register Colab Backend | operations | register_colab_backend_api_v1_ops_gcs_colab_register_post |
| GET | /api/v1/ops/gcs/colab/status | /ops/gcs/colab/status | stable | - | Gcs Colab Status | operations | gcs_colab_status_api_v1_ops_gcs_colab_status_get |
| GET | /api/v1/ops/health/summary | /ops/health/summary | stable | - | Ops Health Summary | operations | ops_health_summary_api_v1_ops_health_summary_get |
| GET | /api/v1/ops/health/trends | /ops/health/trends | stable | - | Get Health Trends | operations | get_health_trends_api_v1_ops_health_trends_get |
| GET | /api/v1/ops/metrics/history | /ops/metrics/history | stable | - | Metrics History | operations | metrics_history_api_v1_ops_metrics_history_get |
| GET | /api/v1/ops/performance/snapshot | /ops/performance/snapshot | stable | - | Performance Snapshot | operations | performance_snapshot_api_v1_ops_performance_snapshot_get |
| GET | /api/v1/ops/providers/status | /ops/providers/status | stable | - | Ops Providers Status | operations | ops_providers_status_api_v1_ops_providers_status_get |
| GET | /api/v1/ops/queues/snapshot | /ops/queues/snapshot | stable | - | Queues Snapshot | operations | queues_snapshot_api_v1_ops_queues_snapshot_get |
| GET | /api/v1/ops/recommendations | /ops/recommendations | stable | - | Get System Recommendations | operations | get_system_recommendations_api_v1_ops_recommendations_get |
| POST | /api/v1/ops/rovo-dev/health | /ops/rovo-dev/health | stable | - | Rovo Dev Health Probe | operations | rovo_dev_health_probe_api_v1_ops_rovo_dev_health_post |
| GET | /api/v1/ops/rovo-dev/status | /ops/rovo-dev/status | stable | - | Rovo Dev Status | operations | rovo_dev_status_api_v1_ops_rovo_dev_status_get |
| GET | /api/v1/ops/security/status | /ops/security/status | stable | - | Get Security Status | operations | get_security_status_api_v1_ops_security_status_get |
| POST | /api/v1/ops/sentry-webhook | /ops/sentry-webhook | stable | - | Sentry Webhook | operations | sentry_webhook_api_v1_ops_sentry_webhook_post |
| GET | /api/v1/ops/streaming/analysis | /ops/streaming/analysis | stable | - | Get Streaming Analysis | operations | get_streaming_analysis_api_v1_ops_streaming_analysis_get |
| POST | /api/v1/parse/ | /parse/ | stable | - | Parse Orchestration | parse | parse_orchestration_api_v1_parse__post |
| GET | /api/v1/providers/models | /providers/models | stable | - | Get Provider Models | providers | get_provider_models_api_v1_providers_models_get |
| GET | /api/v1/raptor/demo/{value} | /raptor/demo/{value} | stable | - | Raptor Demo | raptor | raptor_demo_api_v1_raptor_demo__value__get |
| POST | /api/v1/raptor/logs | /raptor/logs | stable | - | Raptor Logs | raptor | raptor_logs_api_v1_raptor_logs_post |
| POST | /api/v1/raptor/start | /raptor/start | stable | - | Raptor Start | raptor | raptor_start_api_v1_raptor_start_post |
| GET | /api/v1/raptor/status | /raptor/status | stable | - | Raptor Status | raptor | raptor_status_api_v1_raptor_status_get |
| POST | /api/v1/raptor/stop | /raptor/stop | stable | - | Raptor Stop | raptor | raptor_stop_api_v1_raptor_stop_post |
| GET | /api/v1/routing/audit | /routing/audit | stable | - | Get Routing Audit | routing-analytics | get_routing_audit_api_v1_routing_audit_get |
| GET | /api/v1/routing/costs | /routing/costs | stable | - | Get Cost Tracking | routing-analytics | get_cost_tracking_api_v1_routing_costs_get |
| GET | /api/v1/routing/departments | /routing/departments | stable | - | List Departments | routing | list_departments_api_v1_routing_departments_get |
| GET | /api/v1/routing/departments/{department_id} | /routing/departments/{department_id} | stable | - | Get Department | routing | get_department_api_v1_routing_departments__department_id__get |
| GET | /api/v1/routing/explain/{routing_id} | /routing/explain/{routing_id} | stable | - | Explain Routing Decision | routing | explain_routing_decision_api_v1_routing_explain__routing_id__get |
| GET | /api/v1/routing/health | /routing/health | stable | - | Get Provider Health | routing-analytics | get_provider_health_api_v1_routing_health_get |
| GET | /api/v1/routing/health/{provider_id} | /routing/health/{provider_id} | stable | - | Get Provider Health Detail | routing-analytics | get_provider_health_detail_api_v1_routing_health__provider_id__get |
| GET | /api/v1/routing/observability | /routing/observability | stable | - | Get Routing Observability | routing-analytics | get_routing_observability_api_v1_routing_observability_get |
| GET | /api/v1/routing/providers | /routing/providers | deprecated | /api/v1/providers/models | Get Available Providers | routing | get_available_providers_api_v1_routing_providers_get |
| GET | /api/v1/routing/providers/analytics | /routing/providers/analytics | stable | - | List Available Providers | routing-analytics | list_available_providers_api_v1_routing_providers_analytics_get |
| GET | /api/v1/routing/providers/{capability} | /routing/providers/{capability} | deprecated | /api/v1/providers/models | Get Providers For Capability | routing | get_providers_for_capability_api_v1_routing_providers__capability__get |
| POST | /api/v1/routing/route | /routing/route | deprecated | /api/v1/api/route_task | Route Through Department | routing | route_through_department_api_v1_routing_route_post |
| GET | /api/v1/routing/status | /routing/status | stable | - | Get Routing Status | routing-analytics | get_routing_status_api_v1_routing_status_get |
| GET | /api/v1/routing/strategies | /routing/strategies | stable | - | List Routing Strategies | routing-analytics | list_routing_strategies_api_v1_routing_strategies_get |
| POST | /api/v1/routing/test/{provider_id} | /routing/test/{provider_id} | stable | - | Test Provider | routing-analytics | test_provider_api_v1_routing_test__provider_id__post |
| GET | /api/v1/routing/weight | /routing/weight | stable | - | Get Routing Weight | routing-analytics | get_routing_weight_api_v1_routing_weight_get |
| GET | /api/v1/sandbox/artifacts/{job_id} | /sandbox/artifacts/{job_id} | stable | - | List Job Artifacts | sandbox | list_job_artifacts_api_v1_sandbox_artifacts__job_id__get |
| GET | /api/v1/sandbox/artifacts/{job_id}/download/{filename} | /sandbox/artifacts/{job_id}/download/{filename} | stable | - | Download Artifact | sandbox | download_artifact_api_v1_sandbox_artifacts__job_id__download__filename__get |
| POST | /api/v1/sandbox/cancel/{job_id} | /sandbox/cancel/{job_id} | stable | - | Cancel Job | sandbox | cancel_job_api_v1_sandbox_cancel__job_id__post |
| GET | /api/v1/sandbox/health | /sandbox/health | stable | - | Sandbox Health Legacy | sandbox | sandbox_health_legacy_api_v1_sandbox_health_get |
| GET | /api/v1/sandbox/health/status | /sandbox/health/status | stable | - | Sandbox Health | sandbox | sandbox_health_api_v1_sandbox_health_status_get |
| GET | /api/v1/sandbox/jobs | /sandbox/jobs | stable | - | List Sandbox Jobs | sandbox | list_sandbox_jobs_api_v1_sandbox_jobs_get |
| GET | /api/v1/sandbox/jobs/{job_id} | /sandbox/jobs/{job_id} | stable | - | Get Job Status Alias | sandbox | get_job_status_alias_api_v1_sandbox_jobs__job_id__get |
| GET | /api/v1/sandbox/jobs/{job_id}/logs | /sandbox/jobs/{job_id}/logs | stable | - | Get Job Logs Alias | sandbox | get_job_logs_alias_api_v1_sandbox_jobs__job_id__logs_get |
| GET | /api/v1/sandbox/logs/{job_id} | /sandbox/logs/{job_id} | stable | - | Get Job Logs | sandbox | get_job_logs_api_v1_sandbox_logs__job_id__get |
| GET | /api/v1/sandbox/metrics | /sandbox/metrics | stable | - | Sandbox Metrics | sandbox | sandbox_metrics_api_v1_sandbox_metrics_get |
| POST | /api/v1/sandbox/run | /sandbox/run | stable | - | Run Sandbox Code | sandbox | run_sandbox_code_api_v1_sandbox_run_post |
| GET | /api/v1/sandbox/status/{job_id} | /sandbox/status/{job_id} | stable | - | Get Job Status | sandbox | get_job_status_api_v1_sandbox_status__job_id__get |
| POST | /api/v1/sandbox/submit | /sandbox/submit | stable | - | Submit Job | sandbox | submit_job_api_v1_sandbox_submit_post |
| GET | /api/v1/search/collections | /search/collections | stable | - | List Collections | search | list_collections_api_v1_search_collections_get |
| POST | /api/v1/search/collections/{collection_name}/add | /search/collections/{collection_name}/add | stable | - | Add Document Compat | search | add_document_compat_api_v1_search_collections__collection_name__add_post |
| GET | /api/v1/search/collections/{collection_name}/documents | /search/collections/{collection_name}/documents | stable | - | Get Collection Documents | search | get_collection_documents_api_v1_search_collections__collection_name__documents_get |
| POST | /api/v1/search/index | /search/index | stable | - | Index Content | search | index_content_api_v1_search_index_post |
| POST | /api/v1/search/query | /search/query | stable | - | Search Query | search | search_query_api_v1_search_query_post |
| GET | /api/v1/secrets/ | /secrets/ | stable | - | List Secrets | secrets | list_secrets_api_v1_secrets__get |
| GET | /api/v1/secrets/health | /secrets/health | stable | - | Secrets Health | secrets | secrets_health_api_v1_secrets_health_get |
| DELETE | /api/v1/secrets/{path:path} | /secrets/{path:path} | stable | - | Delete a secret. Args: path: Secret path version: Optional specific version to delete adapter: The secrets adapter instance | secrets | delete_secret |
| GET | /api/v1/secrets/{path:path} | /secrets/{path:path} | stable | - | Retrieve a secret by path. Args: path: Secret path version: Optional specific version adapter: The secrets adapter instance Returns: Secret data and metadata | secrets | get_secret |
| PUT | /api/v1/secrets/{path:path} | /secrets/{path:path} | stable | - | Create or update a secret. Args: path: Secret path request: Secret data and metadata adapter: The secrets adapter instance Returns: Stored secret information | secrets | put_secret |
| POST | /api/v1/secrets/{path:path}/rotate | /secrets/{path:path}/rotate | stable | - | Rotate a secret value. Args: path: Secret path adapter: The secrets adapter instance Returns: New secret value | secrets | rotate_secret |
| GET | /api/v1/semantic-chat/conversations/{conversation_id}/context | /semantic-chat/conversations/{conversation_id}/context | stable | - | Get Context Bundle | semantic-chat | get_context_bundle_api_v1_semantic_chat_conversations__conversation_id__context_get |
| POST | /api/v1/semantic-chat/conversations/{conversation_id}/messages | /semantic-chat/conversations/{conversation_id}/messages | stable | - | Semantic Send Message | semantic-chat | semantic_send_message_api_v1_semantic_chat_conversations__conversation_id__messages_post |
| POST | /api/v1/semantic-chat/conversations/{conversation_id}/summarize | /semantic-chat/conversations/{conversation_id}/summarize | stable | - | Summarize Conversation | semantic-chat | summarize_conversation_api_v1_semantic_chat_conversations__conversation_id__summarize_post |
| POST | /api/v1/semantic-chat/users/{user_id}/memory | /semantic-chat/users/{user_id}/memory | stable | - | Add Memory Fact | semantic-chat | add_memory_fact_api_v1_semantic_chat_users__user_id__memory_post |
| GET | /api/v1/semantic-chat/users/{user_id}/memory/search | /semantic-chat/users/{user_id}/memory/search | stable | - | Search Memory Facts | semantic-chat | search_memory_facts_api_v1_semantic_chat_users__user_id__memory_search_get |
| GET | /api/v1/settings/ | /settings/ | stable | - | Get Settings | settings | get_settings_api_v1_settings__get |
| PUT | /api/v1/settings/models/{model_name} | /settings/models/{model_name} | stable | - | Update Model Settings | settings | update_model_settings_api_v1_settings_models__model_name__put |
| PUT | /api/v1/settings/providers/{provider_name} | /settings/providers/{provider_name} | stable | - | Update Provider Settings | settings | update_provider_settings_api_v1_settings_providers__provider_name__put |
| POST | /api/v1/settings/test-connection | /settings/test-connection | stable | - | Test Provider Connection | settings | test_provider_connection_api_v1_settings_test_connection_post |
| PATCH | /api/v1/settings/{key} | /settings/{key} | stable | - | Update Global Setting | settings | update_global_setting_api_v1_settings__key__patch |
| POST | /api/v1/stream | /stream | stable | - | Stream Task | stream | stream_task_api_v1_stream_post |
| POST | /api/v1/support/message | /support/message | stable | - | Send Support Message | support | send_support_message_api_v1_support_message_post |
| POST | /api/v1/support/triage | /support/triage | stable | - | Triage Issue | support | triage_issue_api_v1_support_triage_post |
| POST | /api/v1/write-time/cache/cleanup | /write-time/cache/cleanup | stable | - | Cleanup Cache | write-time | cleanup_cache_api_v1_write_time_cache_cleanup_post |
| POST | /api/v1/write-time/cache/clear | /write-time/cache/clear | stable | - | Clear Cache | write-time | clear_cache_api_v1_write_time_cache_clear_post |
| GET | /api/v1/write-time/cache/stats | /write-time/cache/stats | stable | - | Get Cache Stats | write-time | get_cache_stats_api_v1_write_time_cache_stats_get |
| GET | /api/v1/write-time/matrix/config | /write-time/matrix/config | stable | - | Get Decision Matrix Config | write-time | get_decision_matrix_config_api_v1_write_time_matrix_config_get |
| GET | /api/v1/write-time/metrics | /write-time/metrics | stable | - | Get Write Time Metrics | write-time | get_write_time_metrics_api_v1_write_time_metrics_get |
| POST | /api/v1/write-time/test | /write-time/test | stable | - | Test Message Processing | write-time | test_message_processing_api_v1_write_time_test_post |
| POST | /api/v1/write-time/test/batch | /write-time/test/batch | stable | - | Test Batch Messages | write-time | test_batch_messages_api_v1_write_time_test_batch_post |
| GET | /api/v1/write-time/test/examples | /write-time/test/examples | stable | - | Get Test Examples | write-time | get_test_examples_api_v1_write_time_test_examples_get |

## Legacy dual mounts

These routes are mounted both at their canonical path and at one or more compatibility aliases.

| Method | Path | Logical Path | Aliases | Status | Replaced By | Summary | Tags | Operation ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | /health | /health | /api/v1/health | deprecated | /api/v1/health | Health | health | health_check_api_v1_health_get |

## Notes

- Regenerate this file after changing FastAPI routes, the route manifest, or the OpenAPI export.
- The route inventory is intentionally grouped by mounted path prefix so frontend contract work can spot mismatches quickly.
- Route summaries come from the OpenAPI schema when available, with manifest values used as a fallback.
