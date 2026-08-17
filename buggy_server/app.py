"""
ShopBroken — A deliberately buggy e-commerce Flask app.
50 routes, each with a REAL bug in the code.
The self-healing agent must patch THIS FILE to fix each endpoint.

Run with: python buggy_server/app.py
Flask debug mode auto-reloads on file changes, so patches take effect immediately.

Each route has a comment like:
    # BUG_001: <description of what's wrong>
So the healer can identify and fix them.
"""

import sys
import os
import time
import json
import math
import hashlib
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify

app = Flask(__name__)

# ============================================================
# Fake data (simulates a database)
# ============================================================
USERS = {
    "user_1": {"id": "user_1", "name": "Alice", "email": "alice@shop.com", "balance": 150.00},
    "user_2": {"id": "user_2", "name": "Bob", "email": "bob@shop.com", "balance": 75.50},
    "user_3": {"id": "user_3", "name": "Charlie", "email": "charlie@shop.com", "balance": 200.00},
}

PRODUCTS = {
    "prod_1": {"id": "prod_1", "name": "Wireless Headphones", "price": 49.99, "stock": 25},
    "prod_2": {"id": "prod_2", "name": "USB-C Cable", "price": 12.99, "stock": 100},
    "prod_3": {"id": "prod_3", "name": "Laptop Stand", "price": 34.99, "stock": 15},
    "prod_4": {"id": "prod_4", "name": "Mechanical Keyboard", "price": 89.99, "stock": 8},
    "prod_5": {"id": "prod_5", "name": "Monitor Light", "price": 29.99, "stock": 30},
}

ORDERS = []
CART = {}
REVIEWS = []
COUPONS = {"SAVE10": 0.10, "HALF50": 0.50, "FREE100": 1.00}


# ============================================================
# ROUTE 1-10: User & Auth endpoints
# ============================================================

# BUG_001: Variable name typo - 'usr' instead of 'user' causes NameError
@app.route("/api/user/<user_id>", methods=["GET"])
def get_user(user_id):
    usr = USERS.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user)


# BUG_002: Division by zero - calculates discount percentage with zero items
@app.route("/api/user/<user_id>/loyalty", methods=["GET"])
def user_loyalty(user_id):
    user = USERS.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    total_orders = 0  # BUG: hardcoded to 0, causes ZeroDivisionError
    discount = 100 / total_orders
    return jsonify({"user": user_id, "discount_percent": discount})


# BUG_003: Wrong dictionary key - 'username' doesn't exist, should be 'name'
@app.route("/api/user/<user_id>/profile", methods=["GET"])
def user_profile(user_id):
    user = USERS.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"greeting": f"Hello, {user['username']}!", "email": user["email"]})


# BUG_004: Infinite loop - while condition never becomes False
@app.route("/api/user/<user_id>/points", methods=["GET"])
def user_points(user_id):
    user = USERS.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    points = 0
    i = 10
    while i > 0:
        points += i
        i += 1  # BUG: should be i -= 1, this loops forever
    return jsonify({"user": user_id, "points": points})


# BUG_005: Type error - comparing string to int without conversion
@app.route("/api/user/<user_id>/tier", methods=["GET"])
def user_tier(user_id):
    user = USERS.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    balance = str(user["balance"])  # BUG: converting to string then comparing with >
    if balance > 100:
        tier = "gold"
    elif balance > 50:
        tier = "silver"
    else:
        tier = "bronze"
    return jsonify({"user": user_id, "tier": tier})


# BUG_006: Missing return statement - function falls through returning None
@app.route("/api/auth/validate-token", methods=["POST"])
def validate_token():
    data = request.get_json() or {}
    token = data.get("token", "")
    if len(token) > 10:
        valid = True
    else:
        valid = False
    # BUG: missing return statement
    jsonify({"valid": valid, "token": token[:8] + "..."})


# BUG_007: Wrong HTTP status code logic - returns 200 on error, 404 on success
@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email", "")
    for user in USERS.values():
        if user["email"] == email:
            return jsonify({"error": "Login failed"}), 404  # BUG: swapped - should return success here
    return jsonify({"token": "fake_jwt_token", "user": user}), 200  # BUG: should be 404 here


# BUG_008: Index out of range - accessing element beyond list length
@app.route("/api/auth/recent-logins", methods=["GET"])
def recent_logins():
    logins = ["2026-08-01", "2026-08-05", "2026-08-10"]
    last_five = []
    for i in range(5):  # BUG: only 3 items but iterating 5 times
        last_five.append(logins[i])
    return jsonify({"recent_logins": last_five})


# BUG_009: Timeout - sleep is way too long
@app.route("/api/auth/refresh", methods=["POST"])
def refresh_token():
    data = request.get_json() or {}
    time.sleep(300)  # BUG: 5 minute sleep, should be 0 or very small
    return jsonify({"token": "refreshed_token", "expires_in": 3600})


# BUG_010: Undefined function call - calling a function that doesn't exist
@app.route("/api/user/<user_id>/verify-email", methods=["POST"])
def verify_email(user_id):
    user = USERS.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    result = send_verification_email(user["email"])  # BUG: function doesn't exist
    return jsonify({"status": "verification sent", "email": user["email"]})


# ============================================================
# ROUTE 11-20: Product endpoints
# ============================================================

# BUG_011: Wrong operator - uses assignment (=) logic error in condition
@app.route("/api/products", methods=["GET"])
def list_products():
    in_stock = []
    for prod in PRODUCTS.values():
        if prod["stock"] == 0:  # BUG: should be > 0 or != 0
            in_stock.append(prod)
    return jsonify({"products": in_stock, "count": len(in_stock)})


# BUG_012: KeyError - accessing 'description' which doesn't exist in product dict
@app.route("/api/product/<product_id>", methods=["GET"])
def get_product(product_id):
    product = PRODUCTS.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    return jsonify({
        "id": product["id"],
        "name": product["name"],
        "price": product["price"],
        "description": product["description"],  # BUG: key doesn't exist
        "stock": product["stock"],
    })


# BUG_013: Math error - tax calculated as price * 108 instead of price * 0.08
@app.route("/api/product/<product_id>/price-with-tax", methods=["GET"])
def product_price_with_tax(product_id):
    product = PRODUCTS.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    tax = product["price"] * 108  # BUG: should be * 0.08
    total = product["price"] + tax
    return jsonify({"product": product["name"], "base_price": product["price"], "tax": tax, "total": total})


# BUG_014: String concatenation with int - TypeError
@app.route("/api/product/<product_id>/label", methods=["GET"])
def product_label(product_id):
    product = PRODUCTS.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    label = product["name"] + " - $" + product["price"]  # BUG: price is float, can't concat with str
    return jsonify({"label": label})


# BUG_015: Logic error - stock check inverted
@app.route("/api/product/<product_id>/availability", methods=["GET"])
def product_availability(product_id):
    product = PRODUCTS.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    if product["stock"] > 0:
        return jsonify({"available": False, "message": "Out of stock"})  # BUG: inverted logic
    else:
        return jsonify({"available": True, "message": "In stock"})


# BUG_016: Modifying dict during iteration - RuntimeError
@app.route("/api/products/clearance", methods=["GET"])
def clearance_products():
    clearance = {}
    for pid, prod in PRODUCTS.items():
        clearance[pid] = {**prod, "price": prod["price"] * 0.5}
    for pid in clearance:
        if clearance[pid]["price"] > 20:
            del clearance[pid]  # BUG: modifying dict during iteration
    return jsonify({"clearance": list(clearance.values())})


# BUG_017: Recursion without base case - RecursionError
@app.route("/api/product/<product_id>/category", methods=["GET"])
def product_category(product_id):
    product = PRODUCTS.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    category = find_category(product["name"])
    return jsonify({"product": product["name"], "category": category})

def find_category(name):
    # BUG: calls itself with same argument, infinite recursion
    return find_category(name)


# BUG_018: Wrong slice - returns empty list due to reversed indices
@app.route("/api/products/top-sellers", methods=["GET"])
def top_sellers():
    sorted_products = sorted(PRODUCTS.values(), key=lambda p: p["stock"], reverse=True)
    top_3 = sorted_products[3:0]  # BUG: should be [0:3]
    return jsonify({"top_sellers": top_3})


# BUG_019: NoneType access - .get returns None, then tries to access attribute
@app.route("/api/product/search", methods=["GET"])
def search_product():
    query = request.args.get("q")
    results = []
    for prod in PRODUCTS.values():
        if query.lower() in prod["name"].lower():  # BUG: query can be None if not provided
            results.append(prod)
    return jsonify({"results": results, "query": query})


# BUG_020: JSON serialization error - trying to serialize a set
@app.route("/api/products/categories", methods=["GET"])
def product_categories():
    categories = set()  # BUG: sets are not JSON serializable
    categories.add("electronics")
    categories.add("accessories")
    categories.add("furniture")
    return jsonify({"categories": categories})


# ============================================================
# ROUTE 21-30: Cart & Order endpoints
# ============================================================

# BUG_021: Appending to None - CART[user_id] is never initialized as list
@app.route("/api/cart/<user_id>/add", methods=["POST"])
def add_to_cart(user_id):
    data = request.get_json() or {}
    product_id = data.get("product_id")
    if product_id not in PRODUCTS:
        return jsonify({"error": "Product not found"}), 404
    CART[user_id].append(product_id)  # BUG: CART[user_id] doesn't exist yet, KeyError
    return jsonify({"cart": CART[user_id], "message": "Item added"})


# BUG_022: Using 'is' instead of '==' for string comparison
@app.route("/api/cart/<user_id>", methods=["GET"])
def get_cart(user_id):
    items = CART.get(user_id, [])
    cart_details = []
    for item_id in items:
        if item_id is "prod_1":  # BUG: 'is' compares identity not equality
            cart_details.append(PRODUCTS[item_id])
    return jsonify({"user": user_id, "items": cart_details})


# BUG_023: Off-by-one error - range starts at 1 but list is 0-indexed
@app.route("/api/cart/<user_id>/total", methods=["GET"])
def cart_total(user_id):
    items = CART.get(user_id, ["prod_1", "prod_2"])
    total = 0
    for i in range(1, len(items) + 1):  # BUG: starts at 1, items[len] is out of bounds
        total += PRODUCTS[items[i]]["price"]
    return jsonify({"total": total})


# BUG_024: Mutation of default argument
@app.route("/api/order/create", methods=["POST"])
def create_order(items=[]):  # BUG: mutable default argument
    data = request.get_json() or {}
    items.append(data.get("product_id", "prod_1"))
    order = {"id": f"order_{len(ORDERS)}", "items": items, "created": str(datetime.now())}
    ORDERS.append(order)
    return jsonify(order)


# BUG_025: Wrong format specifier - using %d for a float
@app.route("/api/order/<user_id>/summary", methods=["GET"])
def order_summary(user_id):
    user = USERS.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    summary = "Balance: %d, Name: %s" % (user["balance"], user["name"])  # BUG: %d truncates float
    return jsonify({"summary": summary, "accurate_balance": user["balance"]})


# BUG_026: Incorrect boolean logic - 'and' should be 'or'
@app.route("/api/order/validate", methods=["POST"])
def validate_order():
    data = request.get_json() or {}
    product_id = data.get("product_id", "")
    quantity = data.get("quantity", 0)
    # BUG: should be 'or' — currently both must fail for error message
    if not product_id and quantity <= 0:
        return jsonify({"error": "Invalid order: need product_id and quantity > 0"}), 400
    if product_id not in PRODUCTS:
        return jsonify({"error": "Product not found"}), 404
    return jsonify({"valid": True, "product": product_id, "quantity": quantity})


# BUG_027: Integer overflow simulation - calculating factorial of large number
@app.route("/api/order/shipping-estimate", methods=["GET"])
def shipping_estimate():
    weight = request.args.get("weight", "5")
    # BUG: calculates factorial of weight for no reason, huge number crashes json
    cost = math.factorial(int(weight) * 10)
    return jsonify({"shipping_cost": cost, "weight": weight})


# BUG_028: File not found - trying to read a config file that doesn't exist
@app.route("/api/order/shipping-zones", methods=["GET"])
def shipping_zones():
    with open("/tmp/shipping_zones_that_does_not_exist.json", "r") as f:  # BUG: file doesn't exist
        zones = json.load(f)
    return jsonify({"zones": zones})


# BUG_029: Wrong variable in return - returns 'price' before it's defined in scope
@app.route("/api/order/apply-coupon", methods=["POST"])
def apply_coupon():
    data = request.get_json() or {}
    code = data.get("code", "")
    subtotal = data.get("subtotal", 100.0)
    if code in COUPONS:
        discount_rate = COUPONS[code]
        final = subtotal * (1 - discount_rate)
    return jsonify({"original": subtotal, "discount": discount_rate, "final": final})  # BUG: if code not in COUPONS, variables undefined


# BUG_030: Circular reference - creates unserializable structure
@app.route("/api/order/history", methods=["GET"])
def order_history():
    history = {"orders": [], "meta": {}}
    history["meta"]["parent"] = history  # BUG: circular reference, can't serialize to JSON
    history["orders"].append({"id": "order_1", "total": 49.99})
    return jsonify(history)


# ============================================================
# ROUTE 31-40: Payment & Review endpoints
# ============================================================

# BUG_031: Wrong operator precedence - missing parentheses
@app.route("/api/payment/calculate-tax", methods=["GET"])
def calculate_tax():
    amount = float(request.args.get("amount", "100"))
    # BUG: should be amount * (1 + 0.08), but operator precedence gives wrong result
    # Actually the bug: calculates tax on 1 instead of amount
    tax_rate = 0.08
    total = amount + 1 * tax_rate  # BUG: should be amount + amount * tax_rate
    return jsonify({"amount": amount, "tax_rate": tax_rate, "total": total})


# BUG_032: Accessing index of empty list
@app.route("/api/payment/last-transaction", methods=["GET"])
def last_transaction():
    transactions = []  # BUG: empty list, accessing [0] will IndexError
    return jsonify({"last": transactions[0]})


# BUG_033: Using wrong method on dict - .append() doesn't exist on dicts
@app.route("/api/payment/process", methods=["POST"])
def process_payment():
    data = request.get_json() or {}
    result = {}
    result.append({"status": "processed"})  # BUG: dicts don't have .append()
    return jsonify(result)


# BUG_034: Forgetting to decode bytes
@app.route("/api/payment/receipt/<order_id>", methods=["GET"])
def payment_receipt(order_id):
    receipt_data = hashlib.sha256(order_id.encode()).digest()  # returns bytes
    return jsonify({"order_id": order_id, "receipt_hash": receipt_data})  # BUG: bytes not JSON serializable


# BUG_035: Wrong comparison - using 'not in' incorrectly with dict values
@app.route("/api/payment/verify-amount", methods=["POST"])
def verify_amount():
    data = request.get_json() or {}
    amount = data.get("amount", 0)
    valid_amounts = {"min": 1.0, "max": 10000.0}
    if amount not in valid_amounts:  # BUG: checks keys not values, should be amount < min or > max
        return jsonify({"error": "Invalid amount"}), 400
    return jsonify({"verified": True, "amount": amount})


# BUG_036: Regex with unescaped special chars - re error
@app.route("/api/review/search", methods=["GET"])
def search_reviews():
    import re
    query = request.args.get("q", "great product (5 stars)")
    pattern = re.compile(query)  # BUG: query has unescaped parens, will crash on bad input
    matches = [r for r in REVIEWS if pattern.search(str(r))]
    return jsonify({"matches": matches})


# BUG_037: Integer expected but string given to range()
@app.route("/api/review/stars-distribution", methods=["GET"])
def stars_distribution():
    max_stars = "5"  # BUG: string instead of int, range() needs int
    distribution = {}
    for i in range(1, max_stars + 1):
        distribution[i] = 0
    return jsonify({"distribution": distribution})


# BUG_038: Double-encoding JSON - returns string instead of object
@app.route("/api/review/submit", methods=["POST"])
def submit_review():
    data = request.get_json() or {}
    review = {
        "product": data.get("product_id", "prod_1"),
        "rating": data.get("rating", 5),
        "text": data.get("text", "Great!"),
    }
    REVIEWS.append(review)
    return jsonify({"review": json.dumps(review)})  # BUG: double serializing, returns string not object


# BUG_039: Using = instead of == in f-string expression (SyntaxError at runtime)
@app.route("/api/review/count", methods=["GET"])
def review_count():
    count = len(REVIEWS)
    # BUG: this will actually work in Python 3.8+ as f-string debugging, but returns wrong format
    # Real bug: returns repr with = sign instead of clean value
    return jsonify({"message": f"{count=} reviews posted"})  # produces "count=0 reviews posted"


# BUG_040: Shadowing built-in 'list' then trying to use it
@app.route("/api/review/recent", methods=["GET"])
def recent_reviews():
    list = REVIEWS[-5:]  # BUG: shadows built-in 'list'
    formatted = list(map(lambda r: {"text": r.get("text", ""), "rating": r.get("rating", 0)}, list))  # crashes: 'list' is now a list object not the function
    return jsonify({"recent": formatted})


# ============================================================
# ROUTE 41-50: Admin, Search, Analytics endpoints
# ============================================================

# BUG_041: Trying to modify a tuple - TypeError
@app.route("/api/admin/settings", methods=["GET"])
def admin_settings():
    settings = ("dark_mode", "notifications", "language")  # BUG: tuple is immutable
    settings[0] = "light_mode"  # TypeError: tuple doesn't support item assignment
    return jsonify({"settings": list(settings)})


# BUG_042: Unpacking wrong number of values - ValueError
@app.route("/api/admin/stats", methods=["GET"])
def admin_stats():
    data = (len(USERS), len(PRODUCTS), len(ORDERS))
    users, products, orders, reviews = data  # BUG: unpacking 3 values into 4 variables
    return jsonify({"users": users, "products": products, "orders": orders, "reviews": reviews})


# BUG_043: Global variable referenced before assignment
@app.route("/api/admin/reset-counter", methods=["POST"])
def reset_counter():
    counter = counter + 1  # BUG: UnboundLocalError - need 'global counter' or initialize
    return jsonify({"counter": counter})

counter = 0


# BUG_044: String method returns new string - original unchanged
@app.route("/api/search/normalize", methods=["GET"])
def normalize_query():
    query = request.args.get("q", "  Hello World  ")
    query.strip()  # BUG: strip() returns new string, doesn't modify in place
    query.lower()  # BUG: same issue
    return jsonify({"normalized": query})  # Still has spaces and caps


# BUG_045: Using + to merge dicts (TypeError in Python)
@app.route("/api/search/filters", methods=["GET"])
def search_filters():
    base_filters = {"in_stock": True}
    extra_filters = {"min_price": 10, "max_price": 100}
    all_filters = base_filters + extra_filters  # BUG: can't use + on dicts
    return jsonify({"filters": all_filters})


# BUG_046: Incorrect walrus operator placement / syntax issue
@app.route("/api/analytics/popular", methods=["GET"])
def popular_products():
    products = list(PRODUCTS.values())
    # BUG: trying to sort by non-existent key 'sales'
    popular = sorted(products, key=lambda p: p["sales"], reverse=True)
    return jsonify({"popular": popular[:3]})


# BUG_047: Wrong exception handling - catches too broad, hides real error
@app.route("/api/analytics/revenue", methods=["GET"])
def revenue():
    try:
        total = sum(p["price"] * p["stock"] for p in PRODUCTS.values())
        result = total / 0  # BUG: ZeroDivisionError hidden by bare except
    except:
        result = None
    return jsonify({"revenue": result})  # Always returns null


# BUG_048: Async without await (or rather, returning coroutine instead of value)
@app.route("/api/analytics/daily-report", methods=["GET"])
def daily_report():
    import asyncio

    async def compute_report():
        return {"date": str(datetime.now().date()), "orders": len(ORDERS), "revenue": 0}

    report = compute_report()  # BUG: returns coroutine object, not the dict
    return jsonify({"report": str(report)})  # Returns "<coroutine object ...>"


# BUG_049: Lambda scoping issue - all lambdas capture same variable
@app.route("/api/analytics/discounts", methods=["GET"])
def discount_tiers():
    tiers = []
    for i in range(5):
        tiers.append(lambda x: x * i / 10)  # BUG: all lambdas will use i=4 (last value)
    # Apply each "tier" to base price 100 — all will give same result
    results = [t(100) for t in tiers]
    return jsonify({"tiers": results, "expected": [0, 10, 20, 30, 40]})


# BUG_050: Comparing different types - datetime vs string
@app.route("/api/analytics/since", methods=["GET"])
def analytics_since():
    since = request.args.get("date", "2026-01-01")
    now = datetime.now()
    if now > since:  # BUG: comparing datetime to string - TypeError
        return jsonify({"data": "analytics data", "since": since})
    return jsonify({"error": "Date is in the future"}), 400


# ============================================================
# Health check (this one works!)
# ============================================================
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "bugs": 50, "message": "ShopBroken is running. Fix the bugs!"})


# ============================================================
# Metrics endpoint - checks which routes actually work
# ============================================================
@app.route("/metrics", methods=["GET"])
def metrics():
    """Test all 50 bug endpoints and report which ones return 200 vs error."""
    import signal

    class TimeoutError(Exception):
        pass

    def timeout_handler(signum, frame):
        raise TimeoutError("Timed out")

    with app.test_client() as client:
        results = []
        endpoints = [
            ("BUG_001", "GET", "/api/user/user_1"),
            ("BUG_002", "GET", "/api/user/user_1/loyalty"),
            ("BUG_003", "GET", "/api/user/user_1/profile"),
            ("BUG_004", "GET", "/api/user/user_1/points"),
            ("BUG_005", "GET", "/api/user/user_1/tier"),
            ("BUG_006", "POST", "/api/auth/validate-token"),
            ("BUG_007", "POST", "/api/auth/login"),
            ("BUG_008", "GET", "/api/auth/recent-logins"),
            ("BUG_009", "POST", "/api/auth/refresh"),
            ("BUG_010", "POST", "/api/user/user_1/verify-email"),
            ("BUG_011", "GET", "/api/products"),
            ("BUG_012", "GET", "/api/product/prod_1"),
            ("BUG_013", "GET", "/api/product/prod_1/price-with-tax"),
            ("BUG_014", "GET", "/api/product/prod_1/label"),
            ("BUG_015", "GET", "/api/product/prod_1/availability"),
            ("BUG_016", "GET", "/api/products/clearance"),
            ("BUG_017", "GET", "/api/product/prod_1/category"),
            ("BUG_018", "GET", "/api/products/top-sellers"),
            ("BUG_019", "GET", "/api/product/search?q=head"),
            ("BUG_020", "GET", "/api/products/categories"),
            ("BUG_021", "POST", "/api/cart/user_1/add"),
            ("BUG_022", "GET", "/api/cart/user_1"),
            ("BUG_023", "GET", "/api/cart/user_1/total"),
            ("BUG_024", "POST", "/api/order/create"),
            ("BUG_025", "GET", "/api/order/user_1/summary"),
            ("BUG_026", "POST", "/api/order/validate"),
            ("BUG_027", "GET", "/api/order/shipping-estimate?weight=5"),
            ("BUG_028", "GET", "/api/order/shipping-zones"),
            ("BUG_029", "POST", "/api/order/apply-coupon"),
            ("BUG_030", "GET", "/api/order/history"),
            ("BUG_031", "GET", "/api/payment/calculate-tax?amount=100"),
            ("BUG_032", "GET", "/api/payment/last-transaction"),
            ("BUG_033", "POST", "/api/payment/process"),
            ("BUG_034", "GET", "/api/payment/receipt/order_1"),
            ("BUG_035", "POST", "/api/payment/verify-amount"),
            ("BUG_036", "GET", "/api/review/search?q=test"),
            ("BUG_037", "GET", "/api/review/stars-distribution"),
            ("BUG_038", "POST", "/api/review/submit"),
            ("BUG_039", "GET", "/api/review/count"),
            ("BUG_040", "GET", "/api/review/recent"),
            ("BUG_041", "GET", "/api/admin/settings"),
            ("BUG_042", "GET", "/api/admin/stats"),
            ("BUG_043", "POST", "/api/admin/reset-counter"),
            ("BUG_044", "GET", "/api/search/normalize?q=+Hello+"),
            ("BUG_045", "GET", "/api/search/filters"),
            ("BUG_046", "GET", "/api/analytics/popular"),
            ("BUG_047", "GET", "/api/analytics/revenue"),
            ("BUG_048", "GET", "/api/analytics/daily-report"),
            ("BUG_049", "GET", "/api/analytics/discounts"),
            ("BUG_050", "GET", "/api/analytics/since"),
        ]

        healed = 0
        broken = 0
        for bug_id, method, path in endpoints:
            try:
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(3)  # 3 second timeout per endpoint
                try:
                    if method == "GET":
                        resp = client.get(path)
                    else:
                        resp = client.post(path, json={"token": "test", "email": "alice@shop.com",
                                                       "product_id": "prod_1", "quantity": 1,
                                                       "code": "SAVE10", "subtotal": 100,
                                                       "amount": 50, "rating": 5, "text": "Good"})
                    signal.alarm(0)
                    if resp.status_code == 200:
                        healed += 1
                        results.append({"bug": bug_id, "status": "HEALED", "code": resp.status_code})
                    else:
                        broken += 1
                        results.append({"bug": bug_id, "status": "BROKEN", "code": resp.status_code})
                except TimeoutError:
                    broken += 1
                    results.append({"bug": bug_id, "status": "BROKEN", "error": "timeout (infinite loop or sleep)"})
                except RecursionError:
                    broken += 1
                    results.append({"bug": bug_id, "status": "BROKEN", "error": "infinite recursion"})
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)
            except Exception as e:
                broken += 1
                results.append({"bug": bug_id, "status": "BROKEN", "error": str(e)[:100]})

        total = len(endpoints)
        precision = healed / total if total > 0 else 0
        return jsonify({
            "total": total,
            "healed": healed,
            "broken": broken,
            "heal_rate": round(precision, 4),
            "results": results,
        })


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  SHOPBROKEN — 50 real bugs to heal")
    print("  http://localhost:7777")
    print("=" * 60)
    print("  /health          — confirms server is up")
    print("  /metrics         — checks which bugs are fixed (precision)")
    print("  Fix bugs in: buggy_server/app.py")
    print("  Flask auto-reloads on file save!")
    print("=" * 60 + "\n")
    app.run(host="0.0.0.0", port=7777, debug=True)
