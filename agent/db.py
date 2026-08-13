"""
Database connection pool - shared across agent modules.

Uses psycopg_pool for efficient connection reuse instead of
creating a new connection per query.
"""

from psycopg_pool import ConnectionPool
from agent.config import COCKROACHDB_URL

# Module-level pool, lazily initialized
_pool = None


def get_pool() -> ConnectionPool:
    """Get or create the shared connection pool."""
    global _pool
    if _pool is None:
        if not COCKROACHDB_URL:
            raise RuntimeError("COCKROACHDB_URL not configured")
        _pool = ConnectionPool(
            conninfo=COCKROACHDB_URL,
            min_size=2,
            max_size=10,
            open=True,
        )
    return _pool


def close_pool() -> None:
    """Close the connection pool (call on shutdown)."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
