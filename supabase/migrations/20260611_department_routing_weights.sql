-- Learned department routing weights
-- One row per (department_id, feature_name) pair.
-- Upserted on every gradient update by learned_department_router.py.

CREATE TABLE IF NOT EXISTS department_routing_weights (
  department_id     TEXT        NOT NULL,
  feature_name      TEXT        NOT NULL,
  weight            FLOAT       NOT NULL DEFAULT 0.0,
  observation_count INT         NOT NULL DEFAULT 0,
  last_updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (department_id, feature_name)
);

-- Learned router output columns on the existing audit log.
-- department_confidence: softmax probability of the winning department (0 when rule-based).
-- department_router_shadow: what the learned router *would* have picked when shadow mode is on.

ALTER TABLE routing_audit_log
  ADD COLUMN IF NOT EXISTS department_confidence    FLOAT,
  ADD COLUMN IF NOT EXISTS department_router_shadow TEXT;
