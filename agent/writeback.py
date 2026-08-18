"""
Write-back module - stores new incidents in CockroachDB to build memory over time.

This is the critical "memory loop" - every investigation makes future investigations smarter.

Usage:
    from agent.writeback import write_incident
    incident_id = write_incident(service, symptoms, root_cause, fix, embedding)
"""

import json
try:
    import psycopg2 as psycopg
except ImportError:
    import psycopg
from typing import List, Optional

from agent.config import COCKROACHDB_URL

FALLBACK_FILE = "/tmp/failed_writebacks.jsonl"


def write_incident(
    service: str,
    symptoms: str,
    root_cause: str,
    fix: str,
    embedding: List[float],
    runbook_url: Optional[str] = None,
    status: str = "pending",
    confidence: Optional[str] = None,
) -> Optional[str]:
    """
    Write a new incident record to CockroachDB with its embedding.

    Args:
        service: The service name.
        symptoms: Raw alert/symptom text.
        root_cause: Proposed or confirmed root cause.
        fix: Proposed or confirmed fix.
        embedding: Vector from embedding model.
        runbook_url: Optional link to runbook.
        status: "pending", "confirmed", or "auto_healed".
        confidence: LLM confidence level ("high", "medium", "low").

    Returns:
        The UUID of the inserted incident, or None if the write failed.
    """
    if not COCKROACHDB_URL:
        print("[writeback] WARNING: COCKROACHDB_URL not set")
        _write_fallback(service, symptoms, root_cause, fix, embedding, runbook_url)
        return None

    vector_str = "[" + ",".join(str(v) for v in embedding) + "]"

    try:
        with psycopg.connect(COCKROACHDB_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO incidents (service, symptoms, root_cause, fix, runbook_url, embedding, status, confidence, resolved)
                    VALUES (%s, %s, %s, %s, %s, %s::vector, %s, %s, %s)
                    RETURNING id
                    """,
                    (service, symptoms, root_cause, fix, runbook_url, vector_str, status, confidence, status == "auto_healed"),
                )
                result = cur.fetchone()
                conn.commit()

                incident_id = str(result[0])
                print(f"[writeback] Incident written successfully: {incident_id} (status={status})")
                return incident_id

    except Exception as e:
        print(f"[writeback] ERROR: Write failed: {e}")
        _write_fallback(service, symptoms, root_cause, fix, embedding, runbook_url)
        return None


def _write_fallback(
    service: str,
    symptoms: str,
    root_cause: str,
    fix: str,
    embedding: List[float],
    runbook_url: Optional[str],
) -> None:
    """Log the failed write to a local JSONL file for later retry."""
    record = {
        "service": service,
        "symptoms": symptoms,
        "root_cause": root_cause,
        "fix": fix,
        "runbook_url": runbook_url,
        "embedding_length": len(embedding),
    }
    try:
        with open(FALLBACK_FILE, "a") as f:
            f.write(json.dumps(record) + "\n")
        print(f"[writeback] Fallback logged to {FALLBACK_FILE}")
    except Exception as e:
        print(f"[writeback] CRITICAL: Could not write fallback: {e}")
