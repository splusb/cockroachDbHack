"""
Seed the shop database with sample users and products.

Usage:
    python infra/seed_shop.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg
from agent.config import COCKROACHDB_URL

if not COCKROACHDB_URL:
    print("ERROR: COCKROACHDB_URL not configured")
    sys.exit(1)

print(f"Connecting to CockroachDB...")
conn = psycopg.connect(COCKROACHDB_URL)
cur = conn.cursor()

# --- Create schema first ---
schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shop_schema.sql")
with open(schema_path) as f:
    sql = f.read()

statements = [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--")]
for stmt in statements:
    lines = [l for l in stmt.split("\n") if l.strip() and not l.strip().startswith("--")]
    if not lines:
        continue
    clean = "\n".join(lines)
    try:
        cur.execute(clean)
        conn.commit()
        print(f"  ✓ Executed: {clean[:60]}...")
    except Exception as e:
        conn.rollback()
        if "already exists" in str(e):
            print(f"  ✓ Already exists (skipped)")
        else:
            print(f"  ✗ Error: {e}")
            print(f"    SQL: {clean[:80]}")

print("✓ Schema ready")

# --- Seed Users ---
print("Seeding users...")
users = [
    ("admin", "admin123", "Admin User", "admin@shopeasy.com"),
    ("john", "john456", "John Doe", "john@example.com"),
    ("jane", "jane789", "Jane Smith", "jane@example.com"),
]

for username, password, name, email in users:
    try:
        cur.execute(
            """INSERT INTO users (username, password, name, email)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (username) DO NOTHING""",
            (username, password, name, email)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"  User {username}: {e}")

print(f"  ✓ {len(users)} users seeded")

# --- Seed Products ---
print("Seeding products...")
products = [
    ("Laptop Pro 15", 999.99, "electronics", 50, "15-inch display, 16GB RAM, 512GB SSD"),
    ("Wireless Mouse", 49.99, "electronics", 200, "Ergonomic, 2.4GHz wireless, silent clicks"),
    ("Mechanical Keyboard", 129.99, "electronics", 75, "Cherry MX switches, RGB backlit"),
    ("USB-C Hub", 79.99, "accessories", 150, "7-in-1: HDMI, USB 3.0, SD, ethernet"),
    ("Monitor Stand", 59.99, "accessories", 100, "Adjustable height, cable management"),
    ("Noise-Cancelling Headphones", 249.99, "electronics", 30, "Active noise cancellation, 30hr battery"),
    ("Webcam HD", 89.99, "electronics", 60, "1080p, auto-focus, built-in mic"),
    ("Laptop Sleeve", 29.99, "accessories", 200, "Water-resistant neoprene, fits 13-15 inch"),
]

for name, price, category, stock, description in products:
    try:
        cur.execute(
            """INSERT INTO products (name, price, category, stock, description)
               VALUES (%s, %s, %s, %s, %s)""",
            (name, price, category, stock, description)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        # Check if it's a duplicate
        cur.execute("SELECT count(*) FROM products WHERE name = %s", (name,))
        if cur.fetchone()[0] > 0:
            pass  # Already exists
        else:
            print(f"  Product {name}: {e}")

cur.execute("SELECT count(*) FROM products")
count = cur.fetchone()[0]
print(f"  ✓ {count} products in database")

cur.execute("SELECT count(*) FROM users")
count = cur.fetchone()[0]
print(f"  ✓ {count} users in database")

# --- Seed Heal Flags ---
print("Seeding heal_flags...")
flags = [
    ("login_password_check", "Login: password comparison is inverted (!= instead of ==)", "Change != to == in password comparison"),
    ("search_column_name", "Search: query uses wrong column 'title' instead of 'name'", "Change 'title' to 'name' in the SQL query"),
    ("checkout_total_calc", "Checkout: total = subtotal * tax instead of subtotal + tax", "Change subtotal * tax to subtotal + tax"),
]

for bug_id, description, fix_desc in flags:
    try:
        cur.execute(
            """INSERT INTO heal_flags (bug_id, description, healed, fix_description)
               VALUES (%s, %s, false, %s)
               ON CONFLICT (bug_id) DO UPDATE SET description = EXCLUDED.description, fix_description = EXCLUDED.fix_description""",
            (bug_id, description, fix_desc)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"  Flag {bug_id}: {e}")

cur.execute("SELECT bug_id, healed FROM heal_flags")
for row in cur.fetchall():
    print(f"  {row[0]}: healed={row[1]}")

conn.close()
print("\n✓ Shop data seeded successfully!")
print("  Start the demo app: python demo-app/app.py")
