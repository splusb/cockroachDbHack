-- =============================================================
-- Incident Memory Agent — CockroachDB Schema
-- =============================================================
-- Run via: python infra/create_table.py
-- Or paste into CockroachDB Cloud SQL console ONE AT A TIME.
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
  status STRING NOT NULL DEFAULT 'confirmed',
  confidence STRING,
  reasoning STRING,
  embedding VECTOR(1024) NOT NULL
);

-- Create the distributed vector index (cosine similarity)
CREATE VECTOR INDEX IF NOT EXISTS idx_incidents_embedding
  ON incidents (embedding vector_cosine_ops);

-- Index on status for filtering pending vs confirmed
CREATE INDEX IF NOT EXISTS idx_incidents_status
  ON incidents (status);
