# Usage Guide

This guide explains how to discover and use CockroachDB Skills with Claude Code.

## How Skills Work

CockroachDB Skills are automatically discovered by Claude Code when you start a session. Claude:

1. **Scans skill metadata** - Reads the `name` and `description` from each SKILL.md file
2. **Matches your requests** - When you describe a task, Claude identifies relevant skills
3. **Loads skill content** - Retrieves the full guidance only when needed
4. **Provides expert guidance** - Uses skill instructions to give accurate, production-ready advice

**Progressive Loading:** Skills use minimal context initially (just metadata), loading detailed content only when invoked. This keeps Claude fast and efficient.

## Discovering Available Skills

### List All Skills

Ask Claude to show you what's available:

```
What CockroachDB skills are available?
```

or

```
List all skills for CockroachDB
```

### Search by Domain

Skills are organized into 10 operational domains. Ask about specific areas:

```
What skills help with performance tuning?
```

```
Show me skills for security and compliance
```

```
Which skills help with migrations?
```

### Get Skill Details

Learn about a specific skill:

```
Tell me about the reviewing-cluster-health skill
```

```
What does the molt-fetch skill do?
```

## Invoking Skills

Skills can be invoked automatically or explicitly.

### Automatic Invocation (Recommended)

Simply describe what you want to do. Claude will automatically select and use the relevant skill.

**Examples:**

```
I need to check if my CockroachDB cluster is healthy
```
→ Uses `reviewing-cluster-health` skill

```
Help me migrate data from PostgreSQL to CockroachDB
```
→ Uses `molt-fetch` skill

```
My queries are running slowly, how do I diagnose this?
```
→ Uses skills from performance-and-scaling domain

```
I need to set up SSO for my CockroachDB Cloud cluster
```
→ Uses `configuring-sso-and-scim` skill

```
How do I find long-running queries on my cluster right now?
```
→ Uses `triaging-live-sql-activity` skill

### Explicit Invocation

Mention the skill by name if you want to ensure it's used:

```
Use the reviewing-cluster-health skill to check my cluster
```

```
Apply the molt-verify skill to validate my migration
```

## Skill Domains

Skills are organized into 10 operational domains covering the full CockroachDB lifecycle:

### 1. Onboarding and Migrations
Getting started with CockroachDB and moving workloads into the system.

**Available skills:**
- `molt-fetch` - Migrate data from PostgreSQL, MySQL, Oracle, or MSSQL
- `molt-verify` - Verify migration accuracy
- `molt-replicator` - Set up continuous replication during migration

**Example use case:** "I want to migrate from PostgreSQL to CockroachDB"

---

### 2. Query and Schema Design
Designing schemas and writing queries that follow CockroachDB best practices.

**Available skills:**
- `cockroachdb-sql` - Generate CockroachDB-compliant SQL

**Example use case:** "Help me design a schema for a multi-region e-commerce application"

---

### 3. Performance and Scaling
Optimizing query performance and scaling CockroachDB clusters.

**Available skills:**
- `analyzing-range-distribution` - Diagnose uneven data distribution
- `analyzing-schema-change-storage-risk` - Estimate storage for schema changes
- `auditing-table-statistics` - Check optimizer statistics health
- `profiling-statement-fingerprints` - Analyze historical query performance
- `profiling-transaction-fingerprints` - Analyze transaction patterns

**Example use case:** "My application is experiencing high latency on reads"

---

### 4. Operations and Lifecycle
Day-to-day cluster operations and version management.

**Available skills:**
- `managing-certificates-and-encryption` - TLS certificate rotation and CMEK
- `managing-cluster-capacity` - Add/remove nodes, storage management
- `managing-cluster-settings` - Configure cluster settings safely
- `performing-cluster-maintenance` - Drain nodes, rolling restarts
- `provisioning-cluster-for-production` - Production deployment planning
- `reviewing-cluster-health` - Comprehensive health diagnostics
- `upgrading-cluster-version` - Upgrade planning and execution

**Example use case:** "I need to upgrade my cluster to the latest version"

---

### 5. Observability and Diagnostics
Monitoring, alerting, and diagnosing cluster health issues.

**Available skills:**
- `triaging-live-sql-activity` - Find long-running queries and busy sessions
- `monitoring-background-jobs` - Check schema changes, backups, automatic jobs

**Example use case:** "Users are reporting the cluster is slow right now"

---

### 6. Security and Governance
Access control, compliance, and data protection.

**Available skills:**
- `auditing-cloud-cluster-security` - Security posture assessment
- `configuring-audit-logging` - Set up SQL audit logs
- `configuring-ip-allowlists` - Restrict network access
- `configuring-log-export` - Export logs to cloud storage
- `configuring-private-connectivity` - Set up AWS PrivateLink, GCP Private Service Connect
- `configuring-sso-and-scim` - Configure SSO and user provisioning
- `enabling-cmek-encryption` - Customer-managed encryption keys
- `enforcing-password-policies` - Password complexity requirements
- `hardening-user-privileges` - Implement least-privilege access
- `managing-tls-certificates` - Certificate management for self-hosted clusters
- `preparing-compliance-documentation` - Generate compliance reports

**Example use case:** "How do I configure SSO with Okta for my CockroachDB Cloud cluster?"

---

### 7. Integrations and Ecosystem
Connecting CockroachDB to external tools and platforms.

**Example use case:** "Set up a changefeed to Kafka"

---

### 8. Cost and Usage Management
Understanding and optimizing resource consumption.

**Example use case:** "How can I reduce storage costs?"

---

### 9. Resilience and Disaster Recovery
Ensuring high availability and preparing for failures.

**Example use case:** "Set up automated backups"

---

### 10. Application Development
Building applications that use CockroachDB effectively.

**Example use case:** "How do I handle transaction retries in my application?"

---

## Example Workflows

### Daily Cluster Health Check

**Request:**
```
Check the health of my CockroachDB cluster
```

**What happens:**
1. Claude uses the `reviewing-cluster-health` skill
2. Provides diagnostic SQL queries to run
3. Explains what to look for in the results
4. Identifies potential issues based on your cluster's state

**Output example:**
- Queries to check node status, replication health, storage usage
- Guidance on interpreting metrics
- Warnings if issues detected
- Next steps for remediation

---

### Migration Planning

**Request:**
```
I want to migrate my PostgreSQL database to CockroachDB
```

**What happens:**
1. Claude uses migration skills to assess your situation
2. Recommends using `molt-fetch` for data migration
3. Explains schema compatibility considerations
4. Provides step-by-step migration plan with safety checks

**Output example:**
- Pre-migration checklist
- Schema analysis and modifications needed
- Data migration command with recommended flags
- Verification steps using `molt-verify`
- Rollback plan if issues occur

---

### Performance Troubleshooting

**Request:**
```
My application queries are slow. How do I find which ones?
```

**What happens:**
1. Claude uses `triaging-live-sql-activity` for immediate diagnostics
2. Then suggests `profiling-statement-fingerprints` for historical analysis
3. Provides queries to identify slow statements
4. Explains optimization strategies

**Output example:**
- SQL to find currently running slow queries
- Queries to analyze historical performance patterns
- Specific suggestions based on query types (scans, joins, etc.)
- Index recommendations

---

## Understanding Skill Output

Skills provide **guidance and queries**, not automated execution. Here's what to expect:

### Diagnostic Queries

Skills often provide SQL queries to run:

```sql
-- Check cluster health
SHOW CLUSTER STATEMENTS;
SHOW RANGES FROM DATABASE your_database;
SELECT * FROM crdb_internal.node_metrics;
```

**You run these queries yourself** using your SQL client or DB Console.

### Step-by-Step Instructions

Skills break down complex operations into clear steps:

```
1. Verify prerequisites (backups, permissions)
2. Run pre-flight checks
3. Execute the operation
4. Validate results
5. Monitor for issues
```

### Safety Warnings

Skills include guardrails for risky operations:

```
⚠️ This operation will temporarily increase cluster load
- Run during off-peak hours
- Monitor cluster metrics
- Have a rollback plan ready
```

### Links to Official Documentation

Skills reference CockroachDB docs for detailed information:

```
For more details, see:
- CockroachDB Docs: Multi-Region Overview
- CockroachDB Docs: Zone Configuration
```

## Best Practices

### Be Specific

**Better:**
```
Help me diagnose slow queries in the payments database
```

**Less effective:**
```
Database is slow
```

### Provide Context

Mention your deployment type when relevant:

```
I'm using CockroachDB Cloud Serverless and need to configure SSO
```

```
My self-hosted cluster is running version 23.1
```

### Follow Safety Warnings

Skills include safety checks for good reason:
- Take backups before schema changes
- Test in non-production first
- Run maintenance during off-peak hours
- Monitor after changes

### Reference Official Docs

Skills link to authoritative documentation. Follow these links for:
- Latest syntax and features
- Detailed reference material
- Version-specific guidance

## Limitations

**Skills provide guidance, not automation:**
- You run the queries and commands yourself
- Some operations require manual confirmation
- Skills don't execute changes directly

**Skills are read-only by default:**
- Diagnostic queries don't modify data
- Write operations require your explicit action
- Safety checks must be manually verified

**Skills may not cover all edge cases:**
- Every cluster is unique
- Complex scenarios may need customization
- Contact CockroachDB support for critical issues

## Getting Help

### Skill-Specific Questions

Ask Claude to clarify skill guidance:

```
What does this query from the health check skill do?
```

```
Why does the skill recommend this approach?
```

### General CockroachDB Questions

For questions beyond skill scope:

- **[CockroachDB Documentation](https://www.cockroachlabs.com/docs/)** - Official docs
- **[CockroachDB Forum](https://forum.cockroachlabs.com/)** - Community support
- **[CockroachDB Support](https://support.cockroachlabs.com/)** - Enterprise support

### Skill Issues

Report problems or suggest improvements:

- **[GitHub Issues](https://github.com/cockroachlabs/cockroachdb-skills/issues)** - Bug reports and feature requests
- **[Contributing Guide](../CONTRIBUTING.md)** - Help improve skills

## Next Steps

- **[Browse Skills](../skills/)** - Explore all available skills by domain
- **[Contributing](../CONTRIBUTING.md)** - Add your own CockroachDB expertise
- **[Agent Skills Specification](https://agentskills.io/specification)** - Learn about the skills framework
