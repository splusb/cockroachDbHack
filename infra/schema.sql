-- =============================================================
-- Incident Memory Agent — CockroachDB Schema
-- =============================================================
-- Run these in CockroachDB SQL console ONE AT A TIME.
-- =============================================================

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
  status STRING NOT NULL DEFAULT 'pending',
  confidence STRING,
  embedding VECTOR(1536) NOT NULL
);

-- Create the distributed vector index (cosine similarity)
CREATE VECTOR INDEX IF NOT EXISTS idx_incidents_embedding
  ON incidents (embedding vector_cosine_ops);
