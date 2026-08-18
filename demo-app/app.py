"""
ShopEasy — Demo E-commerce App
Reads products/users from CockroachDB.
Uses heal_flags table to toggle between buggy and fixed code paths.

Run: python demo-app/app.py
Access: http://127.0.0.1:5001
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
import psycopg

from agent.config import COCKROACHDB_URL

app = Flask(__name__)
CORS(app)

AGENT_API = "http://localhost:5000"
TAX_RATE = 0.08


def get_db():
    return psycopg.connect(COCKROACHDB_URL)


def is_healed(bug_id):
    """Check CockroachDB heal_flags table to see if a bug has been fixed."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT healed FROM heal_flags WHERE bug_id = %s", (bug_id,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else False
    except Exception:
        return False


# ============================================================
# Pages
# ============================================================

@app.route("/")
def home():
    return render_template_string(LOGIN_PAGE)


@app.route("/shop")
def shop_page():
    return render_template_string(SHOP_PAGE)


# ============================================================
# API: Login
# BUG: password comparison is inverted
# HEAL: heal_flags.login_password_check
# ============================================================

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, username, password, name FROM users WHERE username = %s",
            (username,)
        )
        row = cur.fetchone()
        conn.close()

        if not row:
            return jsonify({"success": False, "error": "User not found"}), 401

        db_password = row[2]
        user_name = row[3]

        if is_healed("login_password_check"):
            # FIXED: correct comparison
            if db_password == password:
                return jsonify({"success": True, "message": f"Welcome {user_name}!", "token": "session-token"})
            else:
                return jsonify({"success": False, "error": "Invalid password"}), 401
        else:
            # BUGGY: inverted comparison
            if db_password != password:
                return jsonify({"success": True, "message": f"Welcome {user_name}!", "token": "session-token"})
            else:
                return jsonify({"success": False, "error": "Invalid password"}), 401

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# API: Products
# ============================================================

@app.route("/products", methods=["GET"])
def get_products():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, name, price, category, stock, description FROM products ORDER BY name")
        rows = cur.fetchall()
        conn.close()

        products = [{
            "id": str(r[0]),
            "name": r[1],
            "price": float(r[2]),
            "category": r[3],
            "stock": r[4],
            "description": r[5],
        } for r in rows]

        return jsonify({"success": True, "products": products})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# API: Search
# BUG: uses wrong column 'title' instead of 'name'
# HEAL: heal_flags.search_column_name
# ============================================================

@app.route("/search", methods=["GET"])
def search_products():
    query = request.args.get("q", "").lower()
    if not query:
        return get_products()

    try:
        conn = get_db()
        cur = conn.cursor()

        if is_healed("search_column_name"):
            # FIXED: correct column name
            cur.execute(
                "SELECT id, name, price, category, stock, description FROM products WHERE LOWER(name) LIKE %s",
                (f"%{query}%",)
            )
        else:
            # BUGGY: 'title' column doesn't exist
            cur.execute(
                "SELECT id, title, price, category, stock, description FROM products WHERE LOWER(title) LIKE %s",
                (f"%{query}%",)
            )

        rows = cur.fetchall()
        conn.close()

        products = [{
            "id": str(r[0]),
            "name": r[1],
            "price": float(r[2]),
            "category": r[3],
            "stock": r[4],
            "description": r[5],
        } for r in rows]

        return jsonify({"success": True, "products": products, "query": query})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# API: Checkout
# BUG: total = subtotal * tax (should be subtotal + tax)
# HEAL: heal_flags.checkout_total_calc
# ============================================================

@app.route("/checkout", methods=["POST"])
def checkout():
    data = request.get_json()
    items = data.get("items", [])

    if not items:
        return jsonify({"success": False, "error": "Cart is empty"}), 400

    try:
        conn = get_db()
        cur = conn.cursor()

        subtotal = 0
        order_items = []
        for item in items:
            cur.execute("SELECT id, name, price FROM products WHERE id = %s", (item["id"],))
            row = cur.fetchone()
            if row:
                price = float(row[2])
                qty = item.get("quantity", 1)
                subtotal += price * qty
                order_items.append({"name": row[1], "price": price, "quantity": qty})

        conn.close()

        tax = subtotal * TAX_RATE

        if is_healed("checkout_total_calc"):
            # FIXED: correct calculation
            total = subtotal + tax
        else:
            # BUGGY: multiplies instead of adds
            total = subtotal * tax

        return jsonify({
            "success": True,
            "items": order_items,
            "subtotal": round(subtotal, 2),
            "tax": round(tax, 2),
            "total": round(total, 2),
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# API: Place Order
# BUG: INSERT uses 'user_name' column which doesn't exist (should be 'user_id')
# HEAL: heal_flags.order_creation_column
# ============================================================

@app.route("/place-order", methods=["POST"])
def place_order():
    data = request.get_json()
    username = data.get("user_id", "admin")
    items = data.get("items", [])
    total = data.get("total", 0)

    if not items:
        return jsonify({"success": False, "error": "Missing items"}), 400

    try:
        conn = get_db()
        cur = conn.cursor()

        # Look up user UUID from username
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_row = cur.fetchone()
        if not user_row:
            conn.close()
            return jsonify({"success": False, "error": "User not found"}), 404
        user_id = str(user_row[0])

        subtotal = total / 1.08
        tax = total - subtotal

        if is_healed("order_creation_column"):
            # FIXED: correct column name
            cur.execute(
                "INSERT INTO orders (user_id, subtotal, tax, total, status) VALUES (%s, %s, %s, %s, 'confirmed') RETURNING id",
                (user_id, round(subtotal, 2), round(tax, 2), round(total, 2))
            )
        else:
            # BUGGY: 'user_name' column doesn't exist
            cur.execute(
                "INSERT INTO orders (user_name, subtotal, tax, total, status) VALUES (%s, %s, %s, %s, 'confirmed') RETURNING id",
                (user_id, round(subtotal, 2), round(tax, 2), round(total, 2))
            )

        order_id = str(cur.fetchone()[0])
        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "order_id": order_id,
            "message": f"Order {order_id[:8]}... placed successfully!",
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# API: Bug Status (for the agent dashboard)
# ============================================================

@app.route("/bug-status", methods=["GET"])
def bug_status():
    """Return current state of all heal flags."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT bug_id, description, healed, healed_at, fix_description FROM heal_flags ORDER BY bug_id")
        rows = cur.fetchall()
        conn.close()
        return jsonify({
            "success": True,
            "bugs": [{
                "bug_id": r[0],
                "description": r[1],
                "healed": r[2],
                "healed_at": r[3].isoformat() if r[3] else None,
                "fix_description": r[4],
            } for r in rows]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/reset-bugs", methods=["POST"])
def reset_bugs():
    """Reset all bugs to unhealed state (for demo replay)."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE heal_flags SET healed = false, healed_at = NULL")
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "All bugs re-injected. Site is buggy again."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# HTML Pages
# ============================================================

LOGIN_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ShopEasy — Sign In</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f0f2f5;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            background: #fff;
            border-radius: 12px;
            padding: 2.5rem;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.08);
        }
        .logo { text-align: center; font-size: 1.8rem; font-weight: 800; margin-bottom: 0.5rem; color: #1a1a2e; }
        .logo span { color: #4ecdc4; }
        .subtitle { text-align: center; color: #666; margin-bottom: 2rem; font-size: 0.9rem; }
        label { display: block; margin-bottom: 6px; font-weight: 500; font-size: 0.9rem; color: #444; }
        input {
            width: 100%; padding: 12px 14px; border: 1px solid #ddd; border-radius: 6px;
            font-size: 1rem; margin-bottom: 1.25rem;
        }
        input:focus { outline: none; border-color: #4ecdc4; }
        .btn {
            width: 100%; padding: 14px; background: #1a1a2e; color: #fff; border: none;
            border-radius: 6px; font-size: 1rem; font-weight: 600; cursor: pointer;
        }
        .btn:hover { background: #16213e; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .message { margin-top: 1.25rem; padding: 12px; border-radius: 6px; text-align: center; font-size: 0.9rem; display: none; }
        .message.error { display: block; background: #ffeaea; color: #c0392b; border: 1px solid #f5c6cb; }
        .message.success { display: block; background: #e8f8f0; color: #27ae60; border: 1px solid #a3d9c6; }
        .hint { text-align: center; margin-top: 1.5rem; color: #999; font-size: 0.8rem; }
        .links { text-align: center; margin-top: 1rem; }
        .links a { color: #4ecdc4; font-size: 0.85rem; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">Shop<span>Easy</span></div>
        <p class="subtitle">Sign in to your account</p>
        <form id="loginForm">
            <label for="username">Username</label>
            <input type="text" id="username" value="admin" placeholder="Enter username">
            <label for="password">Password</label>
            <input type="password" id="password" value="admin123" placeholder="Enter password">
            <button type="submit" class="btn" id="loginBtn">Sign In</button>
        </form>
        <div id="msg" class="message"></div>
        <p class="hint">Try: admin / admin123</p>
        <div class="links"><a href="/shop">Browse Shop &rarr;</a></div>
    </div>
    <script>
        const AGENT = 'http://localhost:5000';
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('loginBtn');
            const msg = document.getElementById('msg');
            msg.className = 'message';
            btn.disabled = true;
            btn.textContent = 'Signing in...';
            try {
                const res = await fetch('/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        username: document.getElementById('username').value,
                        password: document.getElementById('password').value
                    })
                });
                const data = await res.json();
                if (data.success) {
                    msg.className = 'message success';
                    msg.textContent = data.message;
                    setTimeout(() => window.location.href = '/shop', 1000);
                } else {
                    msg.className = 'message error';
                    msg.textContent = 'Login failed: ' + data.error;
                    reportError('Login fails with correct credentials. User enters valid username and password but gets Invalid password error. The password comparison logic appears to be inverted in the login endpoint.');
                }
            } catch (err) {
                msg.className = 'message error';
                msg.textContent = 'Network error';
            }
            btn.disabled = false;
            btn.textContent = 'Sign In';
        });

        function reportError(symptoms) {
            fetch(AGENT + '/api/investigate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ service: 'demo-app', symptoms, source: 'demo-app' })
            }).then(r => r.json()).then(r => console.log('[Agent]', r)).catch(() => {});
        }
    </script>
</body>
</html>
"""

SHOP_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ShopEasy — Browse</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f0f2f5; min-height: 100vh; }
        nav { background: #1a1a2e; padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; }
        nav .logo { color: #fff; font-size: 1.4rem; font-weight: 700; text-decoration: none; }
        nav .logo span { color: #4ecdc4; }
        nav a { color: rgba(255,255,255,0.8); text-decoration: none; margin-left: 1.5rem; font-size: 0.9rem; }
        main { max-width: 1100px; margin: 2rem auto; padding: 0 2rem; }
        .search-bar { margin-bottom: 1.5rem; display: flex; gap: 0.5rem; }
        .search-bar input { flex: 1; padding: 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 1rem; }
        .search-bar button { padding: 12px 20px; background: #4ecdc4; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 1.5rem; }
        .card { background: #fff; border-radius: 10px; padding: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
        .card h3 { margin-bottom: 0.5rem; }
        .card .price { font-size: 1.3rem; font-weight: 700; color: #1a1a2e; }
        .card .desc { color: #666; font-size: 0.85rem; margin: 0.5rem 0; }
        .card .meta { color: #999; font-size: 0.8rem; }
        .card button { margin-top: 1rem; padding: 8px 16px; background: #4ecdc4; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; }
        .toast { position: fixed; top: 1rem; right: 1rem; background: #fff; border-left: 4px solid #dc3545; padding: 1rem; border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); display: none; max-width: 350px; z-index: 999; }
        .toast.show { display: block; }
        .toast.ok { border-left-color: #28a745; }
        .checkout-bar { position: fixed; bottom: 0; left: 0; right: 0; background: #1a1a2e; padding: 1rem 2rem; display: none; justify-content: space-between; align-items: center; z-index: 50; }
        .checkout-bar span { color: #fff; font-weight: 500; }
        .checkout-bar button { padding: 10px 24px; background: #4ecdc4; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; }
    </style>
</head>
<body>
    <nav>
        <a href="/" class="logo">Shop<span>Easy</span></a>
        <div>
            <a href="/shop">Products</a>
            <a href="/">Account</a>
        </div>
    </nav>
    <main>
        <div class="search-bar">
            <input type="text" id="searchInput" placeholder="Search products...">
            <button onclick="searchProducts()">Search</button>
        </div>
        <div class="grid" id="productsGrid">Loading...</div>
    </main>
    <div id="toast" class="toast"></div>
    <div class="checkout-bar" id="checkoutBar">
        <span id="cartCount">0 item(s) in cart</span>
        <button onclick="doCheckout()">Checkout</button>
    </div>
    <script>
        const AGENT = 'http://localhost:5000';

        async function loadProducts() {
            try {
                const res = await fetch('/products');
                const data = await res.json();
                if (data.success) renderProducts(data.products);
                else {
                    showToast('Error loading products: ' + data.error, true);
                    reportError('Product listing fails when loading the shop page. SQL error: ' + data.error + '. The SELECT query may be using a wrong column name.');
                }
            } catch (e) { showToast('Network error', true); }
        }

        async function searchProducts() {
            const q = document.getElementById('searchInput').value;
            if (!q) { loadProducts(); return; }
            try {
                const res = await fetch('/search?q=' + encodeURIComponent(q));
                const data = await res.json();
                if (data.success) {
                    renderProducts(data.products);
                } else {
                    showToast('Search failed: ' + data.error, true);
                    reportError('Product search fails with query "' + q + '". SQL error: ' + data.error + '. The query appears to use a wrong column name.');
                }
            } catch (e) { showToast('Network error', true); }
        }

        function renderProducts(products) {
            const grid = document.getElementById('productsGrid');
            if (products.length === 0) {
                grid.innerHTML = '<p style="color:#999;">No products found</p>';
                return;
            }
            grid.innerHTML = products.map(p => `
                <div class="card">
                    <h3>${p.name}</h3>
                    <div class="price">$${p.price.toFixed(2)}</div>
                    <div class="desc">${p.description || ''}</div>
                    <div class="meta">${p.category} &middot; ${p.stock} in stock</div>
                    <button onclick="addToCart('${p.id}', '${p.name}')">Add to Cart</button>
                </div>
            `).join('');
        }

        let cart = [];
        function addToCart(id, name) {
            cart.push({id, quantity: 1});
            showToast(name + ' added to cart', false);
            document.getElementById('checkoutBar').style.display = 'flex';
            document.getElementById('cartCount').textContent = cart.length + ' item(s) in cart';
        }

        async function doCheckout() {
            if (cart.length === 0) { showToast('Cart is empty', true); return; }
            try {
                const res = await fetch('/checkout', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ items: cart })
                });
                const data = await res.json();
                if (data.success) {
                    const expected = data.subtotal + data.tax;
                    if (Math.abs(data.total - expected) > 0.01) {
                        showToast('Order total looks wrong: $' + data.total.toFixed(2) + ' (expected ~$' + expected.toFixed(2) + ')', true);
                        reportError('Checkout total calculation is wrong. Subtotal=$' + data.subtotal + ', Tax=$' + data.tax + ', but Total=$' + data.total + '. Expected total should be subtotal + tax = $' + expected.toFixed(2) + '. It appears the code is using multiplication instead of addition.');
                    } else {
                        await placeOrder(data.total);
                    }
                    cart = [];
                    document.getElementById('checkoutBar').style.display = 'none';
                } else {
                    showToast('Checkout failed: ' + data.error, true);
                }
            } catch (e) { showToast('Network error', true); }
        }

        async function placeOrder(total) {
            try {
                const res = await fetch('/place-order', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_id: 'admin',
                        items: cart,
                        total: total
                    })
                });
                const data = await res.json();
                if (data.success) {
                    showToast('Order placed! ' + data.message, false);
                } else {
                    showToast('Order failed: ' + data.error, true);
                    reportError('Order placement fails when inserting into orders table. SQL error: ' + data.error + '. The INSERT statement uses wrong column name user_name instead of user_id.');
                }
            } catch (e) { showToast('Network error placing order', true); }
        }

        function showToast(msg, isError) {
            const t = document.getElementById('toast');
            t.className = isError ? 'toast show' : 'toast show ok';
            t.textContent = msg;
            setTimeout(() => t.className = 'toast', 4000);
        }

        function reportError(symptoms) {
            fetch(AGENT + '/api/investigate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ service: 'demo-app', symptoms, source: 'demo-app' })
            }).then(r => r.json()).then(r => console.log('[Agent]', r)).catch(() => {});
        }

        loadProducts();
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print("\\n" + "=" * 50)
    print(f"  ShopEasy running on port {port}")
    print("  DB: " + (COCKROACHDB_URL[:50] + "..." if COCKROACHDB_URL else "NOT SET"))
    print("=" * 50 + "\\n")
    app.run(debug=False, host="0.0.0.0", port=port)
