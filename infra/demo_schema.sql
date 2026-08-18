-- =============================================================
-- Demo App Schema — users, products, heal_flags
-- Run after the main schema.sql
-- =============================================================

-- Users table for login
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username STRING NOT NULL UNIQUE,
  password STRING NOT NULL,
  name STRING NOT NULL
);

-- Products table
CREATE TABLE IF NOT EXISTS products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name STRING NOT NULL,
  price DECIMAL NOT NULL,
  category STRING NOT NULL,
  stock INT NOT NULL DEFAULT 100,
  description STRING
);

-- Heal flags — tracks which bugs have been fixed by the agent
CREATE TABLE IF NOT EXISTS heal_flags (
  bug_id STRING PRIMARY KEY,
  description STRING NOT NULL,
  healed BOOLEAN NOT NULL DEFAULT false,
  healed_at TIMESTAMPTZ,
  fix_description STRING
);

-- Seed users
INSERT INTO users (username, password, name) VALUES
  ('admin', 'admin123', 'Admin User'),
  ('john', 'john456', 'John Doe'),
  ('jane', 'jane789', 'Jane Smith')
ON CONFLICT (username) DO NOTHING;

-- Seed products
INSERT INTO products (name, price, category, stock, description) VALUES
  ('Laptop Pro 15', 999.99, 'electronics', 50, 'High-performance laptop with 16GB RAM'),
  ('Wireless Headphones', 49.99, 'electronics', 200, 'Noise-cancelling bluetooth headphones'),
  ('Coffee Mug', 12.99, 'kitchen', 500, 'Ceramic mug with funny developer quote'),
  ('Notebook Set', 5.99, 'office', 1000, 'Pack of 3 ruled notebooks'),
  ('Backpack', 79.99, 'accessories', 75, 'Water-resistant laptop backpack'),
  ('Mechanical Keyboard', 129.99, 'electronics', 80, 'RGB mechanical keyboard with Cherry MX switches'),
  ('Desk Lamp', 34.99, 'office', 150, 'LED desk lamp with adjustable brightness'),
  ('Water Bottle', 24.99, 'accessories', 300, 'Insulated stainless steel 1L bottle')
ON CONFLICT DO NOTHING;

-- Seed heal flags (all bugs start as unhealed)
INSERT INTO heal_flags (bug_id, description) VALUES
  ('login_password_check', 'Login password comparison is inverted — correct passwords are rejected'),
  ('search_column_name', 'Search query uses non-existent column title instead of name'),
  ('checkout_total_calc', 'Checkout total uses multiplication instead of addition for tax')
ON CONFLICT (bug_id) DO NOTHING;
