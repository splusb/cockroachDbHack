"""
Create the incidents table and indexes in CockroachDB.

Usage:
    python infra/create_table.py

Works with both local CockroachDB and CockroachDB Cloud —
just set COCKROACHDB_URL in your .env file.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg
from agent.config import COCKROACHDB_URL

if not COCKROACHDB_URL:
    print("ERROR: COCKROACHDB_URL not configured. Set it in .env")
    sys.exit(1)

print(f"Connecting to: {COCKROACHDB_URL[:60]}...")

try:
    conn = psycopg.connect(COCKROACHDB_URL, connect_timeout=10)
except Exception as e:
    print(f"ERROR: Could not connect: {e}")
    sys.exit(1)

print("✓ Connected\n")

# Execute each statement from schema.sql separately
schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")
with open(schema_path) as f:
    sql = f.read()

statements = [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--")]

for i, statement in enumerate(statements, 1):
    # Skip comment-only blocks
    lines = [l for l in statement.split("\n") if l.strip() and not l.strip().startswith("--")]
    if not lines:
        continue
    clean = "\n".join(lines)
    print(f"  [{i}/{len(statements)}] {clean[:70]}...")
    try:
        conn.execute(clean)
        conn.commit()
        print(f"  [{i}/{len(statements)}] ✓ Done")
    except Exception as e:
        # Ignore "already exists" errors gracefully
        err_str = str(e)
        if "already exists" in err_str:
            print(f"  [{i}/{len(statements)}] ✓ Already exists (skipped)")
            conn.rollback()
        else:
            print(f"  [{i}/{len(statements)}] ✗ Error: {e}")
            conn.rollback()

conn.close()
print("\n✓ Schema setup complete!")
print("  Next step: python infra/seed_incidents.py")
