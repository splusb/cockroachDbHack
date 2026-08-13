---
inclusion: fileMatch
fileMatchPattern: "**/*.py,**/requirements.txt"
---

# CockroachDB Application Development Skills

Source: [cockroachlabs/cockroachdb-skills](https://github.com/cockroachlabs/cockroachdb-skills)

## Connection Management

- Use connection pooling in production. With psycopg3:
  ```python
  from psycopg_pool import ConnectionPool
  pool = ConnectionPool(conninfo=COCKROACHDB_URL, min_size=2, max_size=10)
  with pool.connection() as conn:
      ...
  ```
- Set `connect_timeout` in the connection string to avoid hanging on network issues.
- CockroachDB Cloud requires SSL — ensure your connection string includes `sslmode=verify-full`.

## Transaction Design

- CockroachDB uses serializable isolation by default. Transactions may be retried automatically by the client.
- For psycopg3, wrap retryable operations:
  ```python
  from psycopg import errors
  
  MAX_RETRIES = 3
  for attempt in range(MAX_RETRIES):
      try:
          with conn.transaction():
              cur.execute(...)
          break
      except errors.SerializationFailure:
          if attempt == MAX_RETRIES - 1:
              raise
          continue
  ```
- Keep transactions short — long-running transactions increase contention.

## Write Patterns

- Use `INSERT ... RETURNING id` to get generated UUIDs back in one round-trip.
- For bulk inserts, use `executemany()` or `COPY` for best throughput.
- CockroachDB handles `INSERT ... ON CONFLICT` (upserts) well for idempotent writes.

## Read Patterns

- Use `AS OF SYSTEM TIME '-5s'` for stale reads that don't need latest data (reduces contention):
  ```sql
  SELECT * FROM incidents AS OF SYSTEM TIME '-5s' WHERE ...
  ```
- This is ideal for vector similarity searches where exact recency isn't critical.

## Error Handling

- Always handle `psycopg.errors.SerializationFailure` — these are retriable.
- Handle `psycopg.OperationalError` for connection failures — implement reconnection logic.
- Log the full error including SQLSTATE for debugging.

## Performance Tips

- Avoid `SELECT *` on tables with vector columns — the embedding data is large.
- Use `EXPLAIN ANALYZE` to verify your queries use the vector index.
- Monitor `crdb_internal.node_statement_statistics` for slow queries.
