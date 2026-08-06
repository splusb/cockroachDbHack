"""
Seed script - generates 20-30 realistic past incidents with real embeddings from Bedrock.

Usage:
    python infra/seed_incidents.py

Prerequisites:
    - .env configured with AWS credentials and COCKROACHDB_URL
    - Bedrock Titan Embeddings V2 access enabled
    - incidents table created in CockroachDB
"""

import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.config import COCKROACHDB_URL
from agent.embed import embed_symptoms
from agent.writeback import write_incident

# Realistic seed incidents across 5 services
SEED_INCIDENTS = [
    # auth-service
    {
        "service": "auth-service",
        "symptoms": "JWT validation failing, 401s spiking across all endpoints, user sessions expiring prematurely",
        "root_cause": "JWT signing key was rotated in secrets manager but auth-service pods were not restarted to pick up the new key",
        "fix": "Rolling restart of auth-service deployment to reload signing keys from secrets manager",
    },
    {
        "service": "auth-service",
        "symptoms": "Login latency increased 10x, connection pool exhausted, timeout errors on /auth/token endpoint",
        "root_cause": "Database connection pool maxed out due to slow query on user_sessions table missing an index",
        "fix": "Add index on user_sessions(user_id, expires_at) and increase connection pool max size from 10 to 25",
    },
    {
        "service": "auth-service",
        "symptoms": "OAuth2 callback failing with 500 errors, Google SSO broken, users unable to link social accounts",
        "root_cause": "Google OAuth client secret expired and was not auto-rotated",
        "fix": "Regenerate OAuth client secret in Google Cloud Console and update the auth-service secret in vault",
    },
    {
        "service": "auth-service",
        "symptoms": "Rate limiter blocking legitimate users, 429 errors spiking, support tickets about locked accounts",
        "root_cause": "Rate limiter Redis instance ran out of memory causing all rate limit checks to fail-closed",
        "fix": "Scale up Redis instance memory from 2GB to 4GB and add eviction policy for rate limit keys",
    },
    # payments-api
    {
        "service": "payments-api",
        "symptoms": "Stripe webhook processing timing out, payments stuck in pending state, customers charged but orders not confirmed",
        "root_cause": "Webhook handler was doing synchronous inventory check that blocked on a downstream service outage",
        "fix": "Make inventory check async, process payment confirmation first, reconcile inventory in background job",
    },
    {
        "service": "payments-api",
        "symptoms": "Duplicate charges appearing for customers, idempotency key collisions in logs, Stripe disputes increasing",
        "root_cause": "Idempotency key generation was using timestamp with only second precision, causing collisions under high load",
        "fix": "Switch idempotency key to UUID v4 and add database-level unique constraint on transaction_id",
    },
    {
        "service": "payments-api",
        "symptoms": "Refund processing failing silently, customers not receiving refunds, accounting reconciliation mismatch",
        "root_cause": "Stripe API version mismatch after library upgrade, refund endpoint response format changed",
        "fix": "Pin Stripe API version in headers to 2024-04-10 and update response parsing logic",
    },
    {
        "service": "payments-api",
        "symptoms": "Currency conversion errors, wrong amounts charged to international customers, FX rate stale",
        "root_cause": "Exchange rate cache TTL set to 24h but provider API was returning errors, serving stale rates",
        "fix": "Reduce FX cache TTL to 1h, add fallback to secondary rate provider, alert if rates are >4h stale",
    },
    # search-indexer
    {
        "service": "search-indexer",
        "symptoms": "Search results returning stale data, new products not appearing in search for hours, indexing lag increasing",
        "root_cause": "Elasticsearch bulk indexing queue backed up due to cluster yellow status from unassigned replica shards",
        "fix": "Increase number of data nodes from 3 to 5, rebalance shards, and increase bulk queue size",
    },
    {
        "service": "search-indexer",
        "symptoms": "Full reindex job crashing at 60% progress, OOM killed, search quality degraded with partial index",
        "root_cause": "Reindex batch size too large for available heap memory after index schema added new field mappings",
        "fix": "Reduce reindex batch size from 5000 to 1000, increase JVM heap from 4GB to 8GB",
    },
    {
        "service": "search-indexer",
        "symptoms": "Typo tolerance not working, fuzzy search returning zero results, customer complaints about search quality",
        "root_cause": "Analyzer configuration was overwritten during last deployment, missing custom synonym and phonetic filters",
        "fix": "Restore analyzer config from git, close and reopen the index to apply analyzer changes",
    },
    {
        "service": "search-indexer",
        "symptoms": "Search latency p99 spiked from 200ms to 3s, cluster CPU at 95%, slow query log flooded",
        "root_cause": "A new wildcard query pattern from the autocomplete feature was causing full index scans",
        "fix": "Add prefix-based edge ngram field for autocomplete, remove wildcard queries from the suggest endpoint",
    },
    # notification-worker
    {
        "service": "notification-worker",
        "symptoms": "Email notifications delayed by 4+ hours, SQS queue depth growing, consumer lag increasing",
        "root_cause": "SMTP connection pool exhausted due to SendGrid rate limiting, no backpressure mechanism",
        "fix": "Implement exponential backoff on SMTP failures, add circuit breaker, increase SQS visibility timeout",
    },
    {
        "service": "notification-worker",
        "symptoms": "Push notifications not delivered to iOS devices, Android working fine, APNs errors in logs",
        "root_cause": "APNs certificate expired, iOS push token refresh failing silently",
        "fix": "Renew APNs certificate, upload to key management, restart notification-worker pods",
    },
    {
        "service": "notification-worker",
        "symptoms": "Users receiving duplicate notifications, same message sent 3-5 times, unsubscribe rate spiking",
        "root_cause": "SQS message visibility timeout shorter than processing time, causing messages to reappear and be processed multiple times",
        "fix": "Increase visibility timeout from 30s to 300s, add deduplication using message_id in Redis with 1h TTL",
    },
    {
        "service": "notification-worker",
        "symptoms": "SMS notifications failing for non-US numbers, Twilio errors for international format, customers in EU not receiving codes",
        "root_cause": "Phone number normalization missing E.164 formatting for numbers without country code prefix",
        "fix": "Add libphonenumber for E.164 normalization before sending to Twilio, default to user's registered country code",
    },
    # api-gateway
    {
        "service": "api-gateway",
        "symptoms": "502 Bad Gateway errors spiking, upstream connection refused, health checks failing intermittently",
        "root_cause": "Kubernetes rolling update caused temporary connection drops, readiness probe too aggressive",
        "fix": "Add preStop lifecycle hook with 15s sleep, increase readiness probe initialDelaySeconds to 30",
    },
    {
        "service": "api-gateway",
        "symptoms": "Request body size limit exceeded errors, file upload endpoint broken, multipart requests rejected",
        "root_cause": "Nginx ingress annotation for client-max-body-size was reset to default 1MB during helm chart upgrade",
        "fix": "Set nginx.ingress.kubernetes.io/proxy-body-size to 50m in ingress annotations, redeploy",
    },
    {
        "service": "api-gateway",
        "symptoms": "CORS errors on frontend, OPTIONS preflight requests failing, third-party integrations broken",
        "root_cause": "New security middleware was added that strips CORS headers from responses on non-GET methods",
        "fix": "Add CORS header passthrough in security middleware config, whitelist allowed origins explicitly",
    },
    {
        "service": "api-gateway",
        "symptoms": "SSL certificate expired, all HTTPS traffic failing, browsers showing security warnings",
        "root_cause": "Let's Encrypt cert auto-renewal job failed silently due to DNS-01 challenge configuration change",
        "fix": "Manually renew cert with certbot, fix DNS provider API credentials, add cert expiry monitoring alert",
    },
    {
        "service": "api-gateway",
        "symptoms": "Sudden spike in 429 rate limit responses, legitimate API partners blocked, revenue-impacting",
        "root_cause": "Global rate limit was applied instead of per-client rate limit after config migration",
        "fix": "Restore per-API-key rate limiting in gateway config, increase global fallback limit 10x as safety net",
    },
    # Cross-service incidents
    {
        "service": "api-gateway",
        "symptoms": "Cascading timeouts across all services, circuit breakers tripping, full platform degradation",
        "root_cause": "Database connection pool on shared PostgreSQL instance exhausted by a runaway analytics query",
        "fix": "Kill the long-running query, set statement_timeout to 30s, move analytics to read replica",
    },
    {
        "service": "payments-api",
        "symptoms": "Memory usage climbing steadily, OOM kills every 6 hours, garbage collection pauses increasing",
        "root_cause": "Memory leak in payment session cache, sessions not evicted after completion",
        "fix": "Add TTL-based eviction to payment session cache, set max cache size to 10000 entries",
    },
    {
        "service": "search-indexer",
        "symptoms": "Disk space on search nodes at 95%, index rotation not working, oldest indices not being deleted",
        "root_cause": "ILM (Index Lifecycle Management) policy was disabled during maintenance and never re-enabled",
        "fix": "Re-enable ILM policy, manually delete indices older than 30 days, add disk space monitoring alert",
    },
    {
        "service": "notification-worker",
        "symptoms": "All notifications going to spam/junk folder, email deliverability dropped from 98% to 40%",
        "root_cause": "SPF record was modified during DNS migration, causing email authentication failures",
        "fix": "Restore correct SPF record with SendGrid include, add DMARC monitoring, verify with mail-tester.com",
    },
]


def main():
    """Seed the incidents table with realistic data and real embeddings."""
    print(f"\n{'='*60}")
    print(f"  SEED INCIDENTS - Generating embeddings and inserting")
    print(f"{'='*60}")
    print(f"\n  Total incidents to seed: {len(SEED_INCIDENTS)}")
    print(f"  Database: {COCKROACHDB_URL[:50]}...")
    print(f"\n{'='*60}\n")

    success_count = 0
    fail_count = 0

    for i, incident in enumerate(SEED_INCIDENTS, 1):
        print(f"  [{i}/{len(SEED_INCIDENTS)}] {incident['service']}: {incident['symptoms'][:50]}...")

        try:
            # Generate real embedding from Bedrock
            embedding = embed_symptoms(incident["symptoms"])
            print(f"           ✓ Embedding generated ({len(embedding)} dims)")

            # Write to database
            incident_id = write_incident(
                service=incident["service"],
                symptoms=incident["symptoms"],
                root_cause=incident["root_cause"],
                fix=incident["fix"],
                embedding=embedding,
            )

            if incident_id:
                print(f"           ✓ Inserted: {incident_id}")
                success_count += 1
            else:
                print(f"           ✗ Write failed (check fallback file)")
                fail_count += 1

            # Small delay to avoid Bedrock throttling
            time.sleep(0.5)

        except Exception as e:
            print(f"           ✗ Error: {e}")
            fail_count += 1

    print(f"\n{'='*60}")
    print(f"  DONE: {success_count} inserted, {fail_count} failed")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
