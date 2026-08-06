-- =============================================================
-- Incident Memory Agent — CockroachDB Schema
-- =============================================================
-- Run these in the CockroachDB Cloud SQL console.
-- On free-tier clusters, skip the SET CLUSTER SETTING (it may
-- already be enabled). Run the CREATE TABLE first, then the index.
-- =============================================================

-- Optional: Only needed if vector indexes aren't enabled by default.
-- This will FAIL on free-tier clusters (safe to skip).
-- SET CLUSTER SETTING feature.vector_index.enabled = true;

-- Create the incidents table
CREATE TABLE IF NOT EXISTS incidents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  service STRING NOT NULL,
  symptoms STRING NOT NULL,
  root_cause STRING,
  fix STRING,
  runbook_url STRING,
  resolved BOOLEAN NOT NULL DEFAULT false,
  embedding VECTOR(1536) NOT NULL
);

-- Create the distributed vector index (cosine similarity)
CREATE VECTOR INDEX IF NOT EXISTS idx_incidents_embedding
  ON incidents (embedding vector_cosine_ops);

-- =============================================================
-- Test: Insert a dummy row to verify everything works
-- =============================================================
-- INSERT INTO incidents (service, symptoms, root_cause, fix, embedding)
-- VALUES (
--   'auth-service',
--   'JWT validation failing, 401s spiking, user sessions expiring prematurely',
--   'Secret key rotated without redeploying auth-service',
--   'Redeploy auth-service to pick up new JWT signing key from secrets manager',
--   ('[' || repeat('0.1,', 1535) || '0.1]')::vector
-- );
--
-- Verify:
-- SELECT id, service, symptoms, root_cause, created_at FROM incidents;
