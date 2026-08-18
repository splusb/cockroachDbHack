-- =============================================================
-- ShopEasy Demo App — CockroachDB Schema
-- =============================================================

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username STRING NOT NULL UNIQUE,
  password STRING NOT NULL,
  name STRING NOT NULL,
  email STRING,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name STRING NOT NULL,
  price DECIMAL(10, 2) NOT NULL,
  category STRING NOT NULL,
  stock INT NOT NULL DEFAULT 100,
  description STRING,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  subtotal DECIMAL(10, 2) NOT NULL,
  tax DECIMAL(10, 2) NOT NULL,
  total DECIMAL(10, 2) NOT NULL,
  status STRING NOT NULL DEFAULT 'pending',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS order_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders(id),
  product_id UUID NOT NULL REFERENCES products(id),
  quantity INT NOT NULL DEFAULT 1,
  price DECIMAL(10, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS heal_flags (
  bug_id STRING PRIMARY KEY,
  description STRING NOT NULL,
  healed BOOLEAN NOT NULL DEFAULT false,
  healed_at TIMESTAMPTZ,
  fix_description STRING
);
