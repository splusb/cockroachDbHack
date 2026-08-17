"""
Demo Buggy Web App - Flask application with intentional bugs for self-healing demo.

Bugs injected:
1. Login: password comparison is inverted (== should be !=, or vice versa)
2. Checkout: total calculation multiplies instead of adds tax
3. Search: returns empty results due to wrong column name

Run: python demo-app/app.py
Access: http://localhost:5000
"""

from flask import Flask, jsonify, request

app = Flask(__name__)

# Simulated user database
USERS = {
    "admin": {"password": "admin123", "name": "Admin User"},
    "john": {"password": "john456", "name": "John Doe"},
    "jane": {"password": "jane789", "name": "Jane Smith"},
}

# Simulated product catalog
PRODUCTS = [
    {"id": 1, "name": "Laptop", "price": 999.99, "category": "electronics"},
    {"id": 2, "name": "Headphones", "price": 49.99, "category": "electronics"},
    {"id": 3, "name": "Coffee Mug", "price": 12.99, "category": "kitchen"},
    {"id": 4, "name": "Notebook", "price": 5.99, "category": "office"},
    {"id": 5, "name": "Backpack", "price": 79.99, "category": "accessories"},
]

TAX_RATE = 0.08  # 8% tax


@app.route("/")
def home():
    return jsonify({"status": "running", "endpoints": ["/login", "/checkout", "/search"]})


# ============================================================
# BUG 1: Login - password check is INVERTED
# The != should be == (accepts wrong passwords, rejects correct ones)
# ============================================================
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")

    user = USERS.get(username)
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 401

    # BUG: != should be ==
    if user["password"] == password:
        return jsonify({"success": True, "message": f"Welcome {user['name']}!", "token": "fake-jwt-token"})
    else:
        return jsonify({"success": False, "error": "Invalid password"}), 401


# ============================================================
# BUG 2: Checkout - tax calculation uses MULTIPLY instead of ADD
# total = subtotal * tax should be total = subtotal + tax
# ============================================================
@app.route("/checkout", methods=["POST"])
def checkout():
    data = request.get_json()
    items = data.get("items", [])

    if not items:
        return jsonify({"success": False, "error": "Cart is empty"}), 400

    subtotal = 0
    order_items = []
    for item_id in items:
        product = next((p for p in PRODUCTS if p["id"] == item_id), None)
        if product:
            subtotal += product["price"]
            order_items.append(product["name"])

    tax = subtotal * TAX_RATE

    # BUG: should be subtotal + tax, not subtotal * tax
    total = subtotal * tax

    return jsonify({
        "success": True,
        "items": order_items,
        "subtotal": round(subtotal, 2),
        "tax": round(tax, 2),
        "total": round(total, 2),
    })


# ============================================================
# BUG 3: Search - uses wrong field name 'title' instead of 'name'
# ============================================================
@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("q", "").lower()
    if not query:
        return jsonify({"results": PRODUCTS})

    # BUG: 'title' doesn't exist, should be 'name'
    results = [p for p in PRODUCTS if query in p.get("title", "").lower()]

    return jsonify({"query": query, "results": results, "count": len(results)})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
