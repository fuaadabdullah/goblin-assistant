-- Task-aware routing audit trail.
-- One append-only row per routing decision/classification so future tuning can
-- analyze which prompts were routed to which logical model group and at what cost.

CREATE TABLE IF NOT EXISTS public.task_routing_decisions (
    decision_id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id                 TEXT        NOT NULL,
    requested_model            TEXT,
    task_class                 TEXT        NOT NULL,
    classifier_source          TEXT        NOT NULL,
    classifier_confidence      REAL        NOT NULL DEFAULT 0.0,
    classifier_reason          TEXT,
    classifier_model           TEXT,
    logical_model              TEXT        NOT NULL,
    backend_provider_id        TEXT,
    backend_model              TEXT,
    prompt_tokens              INTEGER     NOT NULL DEFAULT 0,
    completion_tokens          INTEGER     NOT NULL DEFAULT 0,
    total_tokens               INTEGER     NOT NULL DEFAULT 0,
    cost_usd                   DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    latency_ms                 DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    success                    BOOLEAN     NOT NULL DEFAULT TRUE,
    error_message              TEXT,
    metadata                   JSONB       NOT NULL DEFAULT '{}'::jsonb,
    created_at                 TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS task_routing_decisions_request_created_idx
    ON public.task_routing_decisions (request_id, created_at DESC);

CREATE INDEX IF NOT EXISTS task_routing_decisions_task_class_created_idx
    ON public.task_routing_decisions (task_class, created_at DESC);

CREATE INDEX IF NOT EXISTS task_routing_decisions_logical_model_created_idx
    ON public.task_routing_decisions (logical_model, created_at DESC);

CREATE INDEX IF NOT EXISTS task_routing_decisions_backend_provider_created_idx
    ON public.task_routing_decisions (backend_provider_id, created_at DESC);
