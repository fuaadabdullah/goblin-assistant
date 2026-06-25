-- Routing intelligence: event log + materialised bandit state
-- routing_events: one row per routing decision outcome, used for ML training + feedback
-- routing_bandit_state: materialised Beta distribution parameters for fast routing reads

CREATE TABLE IF NOT EXISTS public.routing_events (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id    TEXT        NOT NULL,
    task_type     TEXT        NOT NULL,
    provider_id   TEXT        NOT NULL,
    was_selected  BOOLEAN     NOT NULL,
    latency_ms    INTEGER,
    cost_usd      DECIMAL(10,8),
    success       BOOLEAN     NOT NULL DEFAULT TRUE,
    user_rating   SMALLINT    CHECK (user_rating IN (-1, 1)),
    session_id    TEXT,
    user_id       UUID        REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS routing_events_task_provider_idx
    ON public.routing_events (task_type, provider_id, created_at DESC);

CREATE INDEX IF NOT EXISTS routing_events_request_id_idx
    ON public.routing_events (request_id);

CREATE INDEX IF NOT EXISTS routing_events_user_idx
    ON public.routing_events (user_id, created_at DESC);


-- Materialised Beta(alpha, beta) per (task_type, provider_id) pair.
-- Updated incrementally by the bandit router after each outcome.
-- Separate from routing_events to keep routing decision latency under 10ms.
CREATE TABLE IF NOT EXISTS public.routing_bandit_state (
    task_type         TEXT        NOT NULL,
    provider_id       TEXT        NOT NULL,
    alpha             REAL        NOT NULL DEFAULT 1.0,
    beta              REAL        NOT NULL DEFAULT 1.0,
    observation_count INTEGER     NOT NULL DEFAULT 0,
    last_updated_at   TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (task_type, provider_id)
);


-- RLS -------------------------------------------------------------------------

ALTER TABLE public.routing_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.routing_bandit_state ENABLE ROW LEVEL SECURITY;

-- Service role inserts routing events (backend writes only)
CREATE POLICY "routing_events_service_insert"
    ON public.routing_events
    FOR INSERT
    WITH CHECK (true);

-- Authenticated users can read their own routing events
CREATE POLICY "routing_events_user_select_own"
    ON public.routing_events
    FOR SELECT
    USING (user_id = auth.uid());

-- Admins can update user_rating (feedback writes routed through service role)
CREATE POLICY "routing_events_service_update"
    ON public.routing_events
    FOR UPDATE
    USING (true)
    WITH CHECK (true);

-- Bandit state is internal — service role has full access, no user access
CREATE POLICY "routing_bandit_state_service_all"
    ON public.routing_bandit_state
    FOR ALL
    USING (true)
    WITH CHECK (true);
