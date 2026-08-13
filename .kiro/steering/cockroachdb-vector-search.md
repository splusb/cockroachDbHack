---
inclusion: fileMatch
fileMatchPattern: "**/*.sql,**/retrieve.py,**/schema.sql,**/seed*.py"
---

# CockroachDB Vector Search Best Practices

Source: [cockroachlabs/cockroachdb-skills](https://github.com/cockroachlabs/cockroachdb-skills)

## Vector Index Configuration

- Use `CREATE VECTOR INDEX ... ON table (column vector_cosine_ops)` for cosine similarity.
- CockroachDB distributes the vector index across ranges like any other index — no special sharding needed.
- The `<=>` operator computes cosine distance. Lower values = more similar.
- For L2 (Euclidean) distance, use `<->` with `vector_l2_ops`.

## Query Patterns

- Always cast your input as `::vector` when comparing: `embedding <=> %s::vector`
- Use `LIMIT` with `ORDER BY distance` to get top-K results.
- Avoid `SELECT *` — only select columns you need. The embedding column is large (1536 floats = ~12KB per row).
- Don't return the embedding column in search results unless you need it for downstream computation.

## Performance

- Vector indexes use approximate nearest neighbor (ANN) — results are fast but may not be exact top-K.
- For tables under ~10K rows, brute-force scan may be faster than the index. The index shines at scale.
- If you need exact results, you can force a full scan with `SET vectorize_search_mode = 'exact'` (not recommended for production).
- Connection pooling: avoid creating a new connection per query. Use a connection pool (e.g., `psycopg_pool.ConnectionPool`) for production workloads.

## Schema Design for Incident Memory

- `VECTOR(1536)` matches Amazon Titan Embeddings V2 output dimensions.
- Use `gen_random_uuid()` for primary keys — CockroachDB distributes UUID ranges well.
- Add a `created_at TIMESTAMPTZ DEFAULT now()` for time-based filtering.
- Consider a partial index if you frequently filter by service: `CREATE INDEX idx_service ON incidents (service) STORING (symptoms, root_cause, fix)`

## Anti-Patterns

- Don't store embeddings as `FLOAT[]` arrays — use the native `VECTOR` type for index support.
- Don't run vector search without a LIMIT — it will scan all rows.
- Don't mix vector search with complex WHERE clauses — the vector index can't be used with arbitrary predicates efficiently. Filter after retrieval if needed.
