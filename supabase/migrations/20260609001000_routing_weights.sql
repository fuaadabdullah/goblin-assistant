-- Persisted learned weights for the feature-based routing model.
-- One row per task_type; weights are a JSONB object with four keys:
--   w_success_rate, w_latency, w_cost, w_complexity
-- Updated asynchronously after each routing outcome via upsert.

CREATE TABLE IF NOT EXISTS public.routing_weights (
    task_type         TEXT    NOT NULL PRIMARY KEY,
    weights           JSONB   NOT NULL DEFAULT
        '{"w_success_rate": 0.4, "w_latency": 0.3, "w_cost": 0.2, "w_complexity": 0.1}',
    observation_count INTEGER NOT NULL DEFAULT 0,
    last_updated_at   TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.routing_weights ENABLE ROW LEVEL SECURITY;

-- Service role can read and write; no user-level access needed
CREATE POLICY "service_all" ON public.routing_weights FOR ALL USING (true);
