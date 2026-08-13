---
inclusion: manual
---

# CockroachDB Operations & Performance Skills

Source: [cockroachlabs/cockroachdb-skills](https://github.com/cockroachlabs/cockroachdb-skills)

## Cluster Health Diagnostics

- Check node status: `SHOW CLUSTER SETTING server.time_until_store_dead`
- View range distribution: `SHOW RANGES FROM TABLE incidents`
- Check for hotspots: `SELECT * FROM crdb_internal.node_statement_statistics ORDER BY count DESC LIMIT 10`

## Index Management

- List all indexes: `SHOW INDEXES FROM incidents`
- Check index usage: `SELECT * FROM crdb_internal.index_usage_statistics WHERE table_name = 'incidents'`
- Vector index stats: `SHOW VECTOR INDEX STATUS idx_incidents_embedding`

## Schema Changes (Online DDL)

- CockroachDB schema changes are online — no downtime needed.
- Adding a column: `ALTER TABLE incidents ADD COLUMN severity STRING DEFAULT 'unknown'`
- Adding an index is non-blocking but may take time on large tables.
- Monitor progress: `SHOW JOBS` to see schema change jobs.

## Backup & Recovery

- CockroachDB Cloud handles automated backups.
- For self-hosted: `BACKUP DATABASE incident_memory INTO 's3://bucket/path'`
- Point-in-time recovery: `RESTORE ... AS OF SYSTEM TIME '2024-01-15 10:00:00'`

## Scaling Considerations

- CockroachDB scales horizontally by adding nodes — data rebalances automatically.
- For this incident memory use case, typical bottlenecks:
  1. Write throughput (solved by adding nodes)
  2. Vector index build time (background, non-blocking)
  3. Connection limits (solved by connection pooling)

## Monitoring Queries for Incident Memory Agent

```sql
-- How many incidents per service?
SELECT service, COUNT(*) FROM incidents GROUP BY service;

-- Average embedding distance for recent searches (custom logging needed)
-- Table size and range count
SHOW RANGES FROM TABLE incidents;

-- Check if vector index is being used
EXPLAIN ANALYZE SELECT service, symptoms FROM incidents ORDER BY embedding <=> '[0.1,...]'::vector LIMIT 5;
```

## Security

- Use role-based access: create a dedicated `incident_agent` role with minimal permissions.
  ```sql
  CREATE ROLE incident_agent;
  GRANT SELECT, INSERT ON incidents TO incident_agent;
  ```
- Rotate connection credentials regularly.
- Use `sslmode=verify-full` in production connection strings.
