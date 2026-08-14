"""
Retrieval module - searches CockroachDB for similar past incidents using vector similarity.

Uses a direct psycopg connection to run cosine distance queries against the vector index.

Usage:
    from agent.retrieve import retrieve_similar_incidents
    results = retrieve_similar_incidents(embedding_vector)
"""

try:
    import psycopg2 as psycopg
except ImportError:
    import psycopg
from typing import List, Dict, Any

from agent.config import COCKROACHDB_URL, TOP_K_RESULTS


def retrieve_similar_incidents(
    embedding: List[float],
    top_k: int = TOP_K_RESULTS,
    exclude_id: str = None,
) -> List[Dict[str, Any]]:
    """
    Search for the most similar past incidents using cosine distance.

    Args:
        embedding: The 1024-dim vector to search against.
        top_k: Number of results to return (default: 5).
        exclude_id: Optional incident ID to exclude (e.g., skip self-match).

    Returns:
        List of dicts, each containing:
            - id, service, symptoms, root_cause, fix, distance
    """
    if not COCKROACHDB_URL:
        print("[retrieve] WARNING: COCKROACHDB_URL not set, returning empty results")
        return []

    vector_str = "[" + ",".join(str(v) for v in embedding) + "]"

    try:
        with psycopg.connect(COCKROACHDB_URL) as conn:
            with conn.cursor() as cur:
                if exclude_id:
                    cur.execute(
                        """
                        SELECT id, service, symptoms, root_cause, fix,
                               embedding <=> %s::vector AS distance
                        FROM incidents
                        WHERE id != %s
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                        """,
                        (vector_str, exclude_id, vector_str, top_k),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, service, symptoms, root_cause, fix,
                               embedding <=> %s::vector AS distance
                        FROM incidents
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                        """,
                        (vector_str, vector_str, top_k),
                    )

                rows = cur.fetchall()
                results = []
                for row in rows:
                    results.append({
                        "id": str(row[0]),
                        "service": row[1],
                        "symptoms": row[2],
                        "root_cause": row[3],
                        "fix": row[4],
                        "distance": float(row[5]),
                    })
                return results

    except Exception as e:
        print(f"[retrieve] ERROR: Database query failed: {e}")
        return []
