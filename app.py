"""
SHREZO - Full Application
Flask backend handling: products, categories, cart, signup/login, forgot password.

Run this with:  python app.py
Then open:       http://127.0.0.1:5000  in your browser
"""

from flask import Flask, render_template, redirect, url_for, session, request
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from db import get_connection
import secrets
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "change-this-secret-key-later"  # needed so Flask can use sessions (cart storage)
ADMIN_SIGNUP_CODE = "SHREZO2026"

# ---------------------------------------------------------
# PRODUCT DATA — organized into separate files by category,
# inside the 'products' folder. Each file exports its own PRODUCTS list.
# ---------------------------------------------------------
from products.electronics import PRODUCTS as ELECTRONICS
from products.accessories import PRODUCTS as ACCESSORIES
from products.grocery import PRODUCTS as GROCERY
from products.stationery import PRODUCTS as STATIONERY
from products.shoes import PRODUCTS as SHOES
from products.dairy import PRODUCTS as DAIRY
from products.snacks import PRODUCTS as SNACKS
from products.mens_wear import PRODUCTS as MENS_WEAR
from products.womens_wear import PRODUCTS as WOMENS_WEAR
from products.kids_wear import PRODUCTS as KIDS_WEAR
from products.fruits_vegetables import PRODUCTS as FRUITS_VEGETABLES
from products.kids_toys import PRODUCTS as KIDS_TOYS
from products.beauty import PRODUCTS as BEAUTY
from products.home_decor import PRODUCTS as HOME_DECOR

STATIC_PRODUCTS = (
    ELECTRONICS + ACCESSORIES + GROCERY + STATIONERY + SHOES +
    DAIRY + SNACKS + MENS_WEAR + WOMENS_WEAR + KIDS_WEAR + FRUITS_VEGETABLES +
    KIDS_TOYS + BEAUTY + HOME_DECOR
)


def get_admin_added_products():
    """Fetch any products the admin has added through the panel (stored in MySQL)."""
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id, category, name, price, discount, image, description, brand, stock FROM products")
    rows = cursor.fetchall()
    cursor.close()
    connection.close()

    products = []
    for pid, category, name, price, discount, image, description, brand, stock in rows:
        products.append({
            "id": pid, "category": category, "name": name, "price": price, "discount": discount,
            "image": image, "images": [image, image, image],
            "description": description, "long_description": description,
            "brand": brand, "stock": stock, "rating": 0, "reviews_count": 0, "specifications": {}
        })
    return products


def get_all_products():
    """Combine your original 140 products with any admin has added since."""
    return STATIC_PRODUCTS + get_admin_added_products()

def get_product_by_id(product_id):
    """Helper: find a product dict by its id."""
    for product in get_all_products():
        if product["id"] == product_id:
            return product
    return None


def get_final_price(product):
    """Helper: apply discount to get final price."""
    discount_amount = (product["price"] * product["discount"]) / 100
    return round(product["price"] - discount_amount, 2)


def with_price(product_list):
    """Helper: attach a computed final_price to each product in a list."""
    result = []
    for p in product_list:
        p_copy = dict(p)
        p_copy["final_price"] = get_final_price(p)
        result.append(p_copy)
    return result


def get_diverse_flash_deals(products, max_count=12, min_discount=15):
    """
    Pick the best-discounted product from EACH category first, so no single
    category dominates the row, then keep filling round-robin style until
    max_count is reached (or we run out of eligible products).
    """
    eligible = [p for p in products if p["discount"] >= min_discount]

    by_category = {}
    for p in eligible:
        by_category.setdefault(p["category"], []).append(p)

    for cat in by_category:
        by_category[cat].sort(key=lambda p: p["discount"], reverse=True)

    result = []
    category_names = list(by_category.keys())
    safety_counter = 0
    while len(result) < max_count and any(by_category.values()):
        for cat in category_names:
            if by_category[cat]:
                result.append(by_category[cat].pop(0))
                if len(result) >= max_count:
                    break
        safety_counter += 1
        if safety_counter > 20:  # safety net against infinite loops
            break

    return result


# Maps each category name to an SVG icon shown on the homepage
CATEGORY_ICONS = {
    "Electronics": '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#fe4f01" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="2" width="14" height="20" rx="2"/><line x1="12" y1="18" x2="12.01" y2="18"/></svg>',
    "Accessories": '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#fe4f01" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8V6a4 4 0 0 1 8 0v2"/><rect x="4" y="8" width="12" height="12" rx="2"/></svg>',
    "Grocery": '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#fe4f01" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="21" r="1"/><circle cx="18" cy="21" r="1"/><path d="M2.5 3h2l2.7 12.4a2 2 0 0 0 2 1.6h8.6a2 2 0 0 0 2-1.6L21.5 7H6"/></svg>',
    "Stationery": '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#fe4f01" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>',
    "Shoes": '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#fe4f01" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 18c0-2 1-3 3-4l5-2 4-3c1-1 2-1 3 0l3 3v3a3 3 0 0 1-3 3H4a1 1 0 0 1-1-1z"/></svg>',
    "Dairy": '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#fe4f01" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M9 2h6l1 5-1 2v11a2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2V9L8 7z"/></svg>',
    "Snacks": '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#fe4f01" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><circle cx="9" cy="9" r="0.8" fill="#854F0B" stroke="none"/><circle cx="15" cy="9" r="0.8" fill="#854F0B" stroke="none"/><circle cx="15" cy="15" r="0.8" fill="#854F0B" stroke="none"/><circle cx="9" cy="15" r="0.8" fill="#854F0B" stroke="none"/></svg>',
    "Mens Wear": '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#fe4f01" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M8 4 4 8l3 3-2 8h14l-2-8 3-3-4-4-3 2h-2z"/></svg>',
    "Womens Wear": '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#fe4f01" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M9 3h6l1 4-2 2 3 12H8l3-12-2-2z"/></svg>',
    "Kids Wear": '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#fe4f01" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M9 2v3L7 7v3a2 2 0 0 0 2 2v9a1.5 1.5 0 0 0 3 0v-9a2 2 0 0 0 2-2V7l-2-2V2"/></svg>',
    "Fruits & Vegetables": '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#fe4f01" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20c-4-2.5-8-5.5-8-10a4.8 4.8 0 0 1 8-3.5A4.8 4.8 0 0 1 20 10c0 4.5-4 7.5-8 10z"/><path d="M12 6.5V3"/></svg>',
    "Kids Toys": '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#fe4f01" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M6 4h5v2a2 2 0 1 0 4 0V4h5a1 1 0 0 1 1 1v5h-2a2 2 0 1 0 0 4h2v5a1 1 0 0 1-1 1h-5v-2a2 2 0 1 0-4 0v2H6a1 1 0 0 1-1-1v-5h2a2 2 0 1 0 0-4H5V5a1 1 0 0 1 1-1z"/></svg>',
    "Beauty": '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#fe4f01" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="2" width="6" height="6" rx="1"/><path d="M9 8h6l-1 12a2 2 0 0 1-2 2 2 2 0 0 1-2-2z"/></svg>',
    "Home Decor": '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#fe4f01" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 18v-4a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v4"/><path d="M3 18h18"/><path d="M5 12V9a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v3"/></svg>',
}


# Maps internal category names to polished display names shown to the user
CATEGORY_DISPLAY_NAMES = {
    "Electronics": "Electronics",
    "Accessories": "Accessories",
    "Grocery": "Grocery",
    "Stationery": "Stationery",
    "Shoes": "Footwear",
    "Dairy": "Dairy",
    "Snacks": "Snacks",
    "Mens Wear": "Men's Fashion",
    "Womens Wear": "Women's Fashion",
    "Kids Wear": "Kids' Fashion",
    "Fruits & Vegetables": "Fruits & Vegetables",
    "Kids Toys": "Kids Toys",
    "Beauty": "Beauty & Personal Care",
    "Home Decor": "Home Decor",
}

# Colour options shown on product pages — fashion categories only.
# Each colour has a display name and a hex code for the colour circle.
FASHION_COLORS = {
    "Mens Wear": [
        {"name": "Black", "hex": "#1a1a1a"},
        {"name": "Navy", "hex": "#1f2f56"},
        {"name": "White", "hex": "#f5f5f5"},
        {"name": "Olive", "hex": "#6b705c"},
        {"name": "Maroon", "hex": "#7a1f2b"},
    ],
    "Womens Wear": [
        {"name": "Black", "hex": "#1a1a1a"},
        {"name": "Red", "hex": "#c62828"},
        {"name": "Pink", "hex": "#f48fb1"},
        {"name": "Teal", "hex": "#00796b"},
        {"name": "Mustard", "hex": "#e0a800"},
    ],
    "Kids Wear": [
        {"name": "Blue", "hex": "#1e88e5"},
        {"name": "Yellow", "hex": "#fdd835"},
        {"name": "Green", "hex": "#43a047"},
        {"name": "Pink", "hex": "#f06292"},
        {"name": "Orange", "hex": "#fb8c00"},
    ],
    "Shoes": [
        {"name": "Black", "hex": "#1a1a1a"},
        {"name": "White", "hex": "#f5f5f5"},
        {"name": "Grey", "hex": "#8e8e8e"},
        {"name": "Brown", "hex": "#6d4c41"},
        {"name": "Blue", "hex": "#1e88e5"},
    ],
}  


# ---------------------------------------------------------
# ROUTES
# ---------------------------------------------------------

@app.route("/")
def home():
    """Show the homepage: hero, offers, categories, flash deals, best sellers, new arrivals."""
    products = get_all_products()

    categories = sorted(set(p["category"] for p in products))
    categories_with_icons = [
        {
            "name": cat,
            "display_name": CATEGORY_DISPLAY_NAMES.get(cat, cat),
            "icon": CATEGORY_ICONS.get(cat, "🛍️")
        }
        for cat in categories
    ]

    flash_deals = with_price(get_diverse_flash_deals(products))

    best_sellers = sorted(products, key=lambda p: (p["rating"], p["reviews_count"]), reverse=True)[:8]
    best_sellers = with_price(best_sellers)

    new_arrivals = sorted(products, key=lambda p: p["id"], reverse=True)[:8]
    new_arrivals = with_price(new_arrivals)

    cart_count = sum(session.get("cart", {}).values())
    cart_quantities = session.get("cart", {})
    return render_template(
        "index.html",
        categories=categories_with_icons,
        flash_deals=flash_deals,
        best_sellers=best_sellers,
        new_arrivals=new_arrivals,
        cart_count=cart_count,
        cart_quantities=cart_quantities
    )


@app.route("/search")
def search():
    """Show products matching a search query (checks name + description)."""
    query = request.args.get("q", "").strip().lower()
    products = get_all_products()

    if query:
        matching_products = [
            p for p in products
            if query in p["name"].lower() or query in p["description"].lower()
        ]
    else:
        matching_products = []

    products_with_price = with_price(matching_products)

    cart_count = sum(session.get("cart", {}).values())
    cart_quantities = session.get("cart", {})
    return render_template(
        "search_results.html",
        query=query,
        products=products_with_price,
        cart_count=cart_count,
        cart_quantities=cart_quantities
    )

@app.route("/category/<category_name>")
def category_page(category_name):
    """Show all products belonging to one category."""
    products = get_all_products()
    matching_products = [p for p in products if p["category"] == category_name]
    products_with_price = with_price(matching_products)

    display_name = CATEGORY_DISPLAY_NAMES.get(category_name, category_name)
    cart_count = sum(session.get("cart", {}).values())
    cart_quantities = session.get("cart", {})          # ← NEW LINE
    return render_template(
        "category.html",
        category_name=category_name,
        display_name=display_name,
        products=products_with_price,
        cart_count=cart_count,
        cart_quantities=cart_quantities                # ← NEW ARGUMENT
    )

@app.route("/product/<int:product_id>")
def product_detail(product_id):
    """Show full details for a single product: gallery, pricing, specs."""
    product = get_product_by_id(product_id)
    if not product:
        return redirect(url_for("home"))

    product_copy = dict(product)
    product_copy["final_price"] = get_final_price(product)
    product_copy["savings"] = round(product["price"] - product_copy["final_price"], 2)

    all_products = get_all_products()
    related = [p for p in all_products if p["id"] != product_id and p["category"] == product["category"]][:4]
    if len(related) < 4:
        extra = [p for p in all_products if p["id"] != product_id and p not in related][:4 - len(related)]
        related += extra

    related_with_price = with_price(related)

    in_wishlist = False
    if "user_id" in session:
        in_wishlist = product_id in get_wishlist_product_ids(session["user_id"])

    cart_count = sum(session.get("cart", {}).values())
    cart_quantities = session.get("cart", {})
    colors = FASHION_COLORS.get(product["category"], [])
    return render_template(
        "product_detail.html",
        product=product_copy,
        related_products=related_with_price,
        in_wishlist=in_wishlist,
        cart_count=cart_count,
        cart_quantities=cart_quantities,
        colors=colors
    )


@app.route("/add-to-cart/<int:product_id>")
def add_to_cart(product_id):
    """Add one unit of a product to the cart (stored in session). Requires login."""
    if "user_id" not in session:
        session["pending_cart_add"] = product_id
        return redirect(url_for("login", next="add_to_cart"))

    cart = session.get("cart", {})
    product_id_str = str(product_id)
    cart[product_id_str] = cart.get(product_id_str, 0) + 1
    session["cart"] = cart

    next_page = request.args.get("next")
    if next_page == "product":
        return redirect(url_for("product_detail", product_id=product_id))

    # Stay on whatever page the person was browsing (category, search results, etc.)
    # instead of always jumping to the homepage.
    if request.referrer:
        return redirect(request.referrer)
    return redirect(url_for("home"))

@app.route("/cart")
def view_cart():
    """Show everything currently in the cart, with total price."""
    cart = session.get("cart", {})
    cart_items = []
    total = 0

    for product_id_str, quantity in cart.items():
        product = get_product_by_id(int(product_id_str))
        if product:
            final_price = get_final_price(product)
            subtotal = final_price * quantity
            total += subtotal
            cart_items.append({
                "product": product,
                "quantity": quantity,
                "final_price": final_price,
                "subtotal": subtotal
            })

    return render_template("cart.html", cart_items=cart_items, total=total)

@app.route("/decrease-quantity/<int:product_id>")
def decrease_quantity(product_id):
    """Remove one unit of a product from the cart. If it reaches 0, remove
    the product entirely so the card goes back to showing 'Add to Cart'."""
    cart = session.get("cart", {})
    product_id_str = str(product_id)

    if product_id_str in cart:
        cart[product_id_str] -= 1
        if cart[product_id_str] <= 0:
            cart.pop(product_id_str)

    session["cart"] = cart

    if request.referrer:
        return redirect(request.referrer)
    return redirect(url_for("home"))


@app.route("/remove-from-cart/<int:product_id>")
def remove_from_cart(product_id):
    """Remove a product completely from the cart."""
    cart = session.get("cart", {})
    cart.pop(str(product_id), None)
    session["cart"] = cart
    return redirect(url_for("view_cart"))

@app.route("/address", methods=["GET", "POST"])
def address():
    """Show saved addresses (GET) or save a new one (POST). Requires login."""
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    connection = get_connection()
    cursor = connection.cursor()

    if request.method == "POST":
        full_name = request.form["full_name"]
        phone_number = request.form["phone_number"]
        address_line = request.form["address_line"]
        city = request.form["city"]
        state = request.form["state"]
        pincode = request.form["pincode"]

        cursor.execute(
            """INSERT INTO addresses (user_id, full_name, phone_number, address_line, city, state, pincode)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (user_id, full_name, phone_number, address_line, city, state, pincode)
        )
        connection.commit()
        new_address_id = cursor.lastrowid
        cursor.close()
        connection.close()

        # After saving, go straight to payment with this address selected
        return redirect(url_for("payment", address_id=new_address_id))

    # GET request: show all saved addresses for this user
    cursor.execute(
        "SELECT id, full_name, phone_number, address_line, city, state, pincode FROM addresses WHERE user_id = %s",
        (user_id,)
    )
    rows = cursor.fetchall()
    cursor.close()
    connection.close()

    saved_addresses = [
        {
            "id": r[0], "full_name": r[1], "phone_number": r[2],
            "address_line": r[3], "city": r[4], "state": r[5], "pincode": r[6]
        }
        for r in rows
    ]

    cart_count = sum(session.get("cart", {}).values())
    return render_template("address.html", saved_addresses=saved_addresses, cart_count=cart_count)

@app.route("/payment", methods=["GET", "POST"])
def payment():
    """Show payment options (GET) or place the order (POST). Requires login."""
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    address_id = request.args.get("address_id", type=int)

    connection = get_connection()
    cursor = connection.cursor()

    # Confirm this address actually belongs to this logged-in user (security check)
    cursor.execute(
        "SELECT id, full_name, phone_number, address_line, city, state, pincode FROM addresses WHERE id = %s AND user_id = %s",
        (address_id, user_id)
    )
    address_row = cursor.fetchone()

    if address_row is None:
        cursor.close()
        connection.close()
        return redirect(url_for("address"))

    if request.method == "POST":
        payment_method = request.form["payment_method"]

        # Rebuild the cart items from session (same pattern as view_cart)
        cart = session.get("cart", {})
        cart_items = []
        total = 0
        for product_id_str, quantity in cart.items():
            product = get_product_by_id(int(product_id_str))
            if product:
                final_price = get_final_price(product)
                subtotal = final_price * quantity
                total += subtotal
                cart_items.append({"product": product, "quantity": quantity, "final_price": final_price})

        if not cart_items:
            cursor.close()
            connection.close()
            return redirect(url_for("home"))

        placed_at = datetime.now().isoformat()

        cursor.execute(
            "INSERT INTO orders (user_id, address_id, total_amount, status, placed_at) VALUES (%s, %s, %s, %s, %s)",
            (user_id, address_id, total, "placed", placed_at)
        )
        connection.commit()
        order_id = cursor.lastrowid

        for item in cart_items:
            cursor.execute(
                """INSERT INTO order_items (order_id, product_id, product_name, quantity, price_at_purchase)
                   VALUES (%s, %s, %s, %s, %s)""",
                (order_id, item["product"]["id"], item["product"]["name"], item["quantity"], item["final_price"])
            )
        connection.commit()
        cursor.close()
        connection.close()

        # Order placed — clear the cart
        session["cart"] = {}

        return redirect(url_for("order_confirmation", order_id=order_id))

    # GET request: show payment page with cart summary
    cursor.close()
    connection.close()

    address = {
        "id": address_row[0], "full_name": address_row[1], "phone_number": address_row[2],
        "address_line": address_row[3], "city": address_row[4], "state": address_row[5], "pincode": address_row[6]
    }

    cart = session.get("cart", {})
    cart_items = []
    total = 0
    for product_id_str, quantity in cart.items():
        product = get_product_by_id(int(product_id_str))
        if product:
            final_price = get_final_price(product)
            subtotal = final_price * quantity
            total += subtotal
            cart_items.append({"product": product, "quantity": quantity, "final_price": final_price, "subtotal": subtotal})

    cart_count = sum(session.get("cart", {}).values())
    return render_template(
        "payment.html",
        address=address,
        cart_items=cart_items,
        total=total,
        cart_count=cart_count
    )


@app.route("/order-confirmation/<int:order_id>")
def order_confirmation(order_id):
    """Show a confirmation screen after an order is placed."""
    if "user_id" not in session:
        return redirect(url_for("login"))

    cart_count = sum(session.get("cart", {}).values())
    return render_template("order_confirmation.html", order_id=order_id, cart_count=cart_count)

def get_wishlist_product_ids(user_id):
    """Helper: get the set of product IDs a user has wishlisted."""
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT product_id FROM wishlist WHERE user_id = %s", (user_id,))
    ids = {r[0] for r in cursor.fetchall()}
    cursor.close()
    connection.close()
    return ids


@app.route("/wishlist/toggle/<int:product_id>")
def toggle_wishlist(product_id):
    """Add a product to the wishlist if not already there, remove it if it is. Requires login."""
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT id FROM wishlist WHERE user_id = %s AND product_id = %s", (user_id, product_id))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("DELETE FROM wishlist WHERE user_id = %s AND product_id = %s", (user_id, product_id))
    else:
        added_at = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO wishlist (user_id, product_id, added_at) VALUES (%s, %s, %s)",
            (user_id, product_id, added_at)
        )

    connection.commit()
    cursor.close()
    connection.close()

    if request.referrer:
        return redirect(request.referrer)
    return redirect(url_for("home"))


@app.route("/wishlist")
def view_wishlist():
    """Show all products the logged-in user has wishlisted."""
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    wishlist_ids = get_wishlist_product_ids(user_id)

    wishlist_products = [get_product_by_id(pid) for pid in wishlist_ids]
    wishlist_products = [p for p in wishlist_products if p]  # drop any that no longer exist
    wishlist_products = with_price(wishlist_products)

    cart_count = sum(session.get("cart", {}).values())
    return render_template("wishlist.html", products=wishlist_products, cart_count=cart_count)

@app.route("/my-orders")
def my_orders():
    """Show the logged-in user's own order history."""
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT id, total_amount, status, placed_at FROM orders WHERE user_id = %s ORDER BY id DESC",
        (user_id,)
    )
    order_rows = cursor.fetchall()

    orders = []
    for order_id, total_amount, status, placed_at in order_rows:
        cursor.execute(
            "SELECT product_name, quantity, price_at_purchase FROM order_items WHERE order_id = %s",
            (order_id,)
        )
        item_rows = cursor.fetchall()
        items = [
            {"product_name": r[0], "quantity": r[1], "price_at_purchase": r[2]}
            for r in item_rows
        ]
        orders.append({
            "id": order_id,
            "total_amount": total_amount,
            "status": status,
            "placed_at": placed_at,
            "line_items": items
        })

    cursor.close()
    connection.close()

    cart_count = sum(session.get("cart", {}).values())
    return render_template("my_orders.html", orders=orders, cart_count=cart_count)

def require_admin():
    """Helper: returns True if the logged-in user is an admin, False otherwise."""
    return session.get("role") == "admin"


@app.route("/admin")
def admin_dashboard():
    """Admin-only dashboard: totals + every order placed, with who bought what."""
    if "user_id" not in session:
        return redirect(url_for("login"))
    if not require_admin():
        return "Access denied — admin only.", 403

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM orders")
    total_orders = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM login_logs")
    total_logins = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM login_logs WHERE DATE(logged_in_at) = CURDATE()")
    todays_logins = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(total_amount) FROM orders")
    total_revenue = cursor.fetchone()[0] or 0

    cursor.execute("""
        SELECT orders.id, users.name, users.email, orders.total_amount, orders.status, orders.placed_at
        FROM orders
        JOIN users ON orders.user_id = users.id
        ORDER BY orders.id DESC
    """)
    order_rows = cursor.fetchall()

    all_orders = []
    for order_id, user_name, user_email, total_amount, status, placed_at in order_rows:
        cursor.execute(
            "SELECT product_name, quantity, price_at_purchase FROM order_items WHERE order_id = %s",
            (order_id,)
        )
        item_rows = cursor.fetchall()
        line_items = [{"product_name": r[0], "quantity": r[1], "price_at_purchase": r[2]} for r in item_rows]
        all_orders.append({
            "id": order_id, "user_name": user_name, "user_email": user_email,
            "total_amount": total_amount, "status": status, "placed_at": placed_at,
            "line_items": line_items
        })

    cursor.close()
    connection.close()

    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        total_orders=total_orders,
        total_revenue=total_revenue,
        total_logins=total_logins,
        todays_logins=todays_logins,
        all_orders=all_orders,
        cart_count=0
    )
    
@app.route("/admin/users")
def admin_users():
    """Admin-only: list every registered user."""
    if "user_id" not in session:
        return redirect(url_for("login"))
    if not require_admin():
        return "Access denied — admin only.", 403

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id, name, email, role FROM users ORDER BY id")
    rows = cursor.fetchall()
    cursor.close()
    connection.close()

    users = [{"id": r[0], "name": r[1], "email": r[2], "role": r[3]} for r in rows]

    return render_template("admin_users.html", users=users, cart_count=0)

@app.route("/admin/add-product", methods=["GET", "POST"])
def admin_add_product():
    """Admin-only: add a new product to the catalog."""
    if "user_id" not in session:
        return redirect(url_for("login"))
    if not require_admin():
        return "Access denied — admin only.", 403

    if request.method == "POST":
        category = request.form["category"]
        name = request.form["name"]
        price = request.form["price"]
        discount = request.form["discount"] or 0
        image = request.form["image"]
        description = request.form["description"]
        brand = request.form["brand"]
        stock = request.form["stock"]

        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """INSERT INTO products (category, name, price, discount, image, description, brand, stock)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (category, name, price, discount, image, description, brand, stock)
        )
        connection.commit()
        cursor.close()
        connection.close()

        return redirect(url_for("admin_dashboard"))

    # GET request: show the form, with existing categories as suggestions
    all_products = get_all_products()
    existing_categories = sorted(set(p["category"] for p in all_products))

    return render_template("admin_add_product.html", existing_categories=existing_categories, cart_count=0)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    """Show the signup form (GET) or create a new account (POST)."""
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                (name, email, hashed_password)
            )
            connection.commit()
        except mysql.connector.IntegrityError:
            cursor.close()
            connection.close()
            return render_template("signup.html", error="That email is already registered.")

        cursor.close()
        connection.close()
        return redirect(url_for("login"))

    return render_template("signup.html", error=None)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Show the login form (GET) or check credentials and log the user in (POST)."""
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT id, name, password, role FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        connection.close()

        if user is None:
            return render_template("login.html", error="No account found with that email.")

        user_id, user_name, hashed_password, role = user

        if check_password_hash(hashed_password, password):
            session["user_id"] = user_id
            session["user_name"] = user_name
            session["role"] = role

            # Record this login so the admin dashboard can count logins later
            log_connection = get_connection()
            log_cursor = log_connection.cursor()
            log_cursor.execute(
                "INSERT INTO login_logs (user_id, logged_in_at) VALUES (%s, %s)",
                (user_id, datetime.now())
            )
            log_connection.commit()
            log_cursor.close()
            log_connection.close()

            # Admins go straight to the admin dashboard, everyone else continues normally
            if role == "admin":
                return redirect(url_for("admin_dashboard"))

            pending_product_id = session.pop("pending_cart_add", None)
            if pending_product_id:
                return redirect(url_for("add_to_cart", product_id=pending_product_id))

            return redirect(url_for("home"))
        else:
            return render_template("login.html", error="Incorrect password.")

    return render_template("login.html", error=None)

@app.route("/logout")
def logout():
    """Log the user out by clearing their session data."""
    session.pop("user_id", None)
    session.pop("user_name", None)
    return redirect(url_for("home"))


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Show the forgot-password form (GET), or generate a reset link (POST)."""
    if request.method == "POST":
        email = request.form["email"]

        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user is None:
            cursor.close()
            connection.close()
            return render_template("forgot_password.html", error="No account found with that email.", reset_link=None)

        user_id = user[0]
        token = secrets.token_urlsafe(32)
        expires_at = (datetime.now() + timedelta(minutes=30)).isoformat()

        cursor.execute(
            "INSERT INTO password_resets (user_id, token, expires_at) VALUES (%s, %s, %s)",
            (user_id, token, expires_at)
        )
        connection.commit()
        cursor.close()
        connection.close()

        reset_link = url_for("reset_password", token=token, _external=True)
        return render_template("forgot_password.html", error=None, reset_link=reset_link)

    return render_template("forgot_password.html", error=None, reset_link=None)


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Show the new-password form (GET), or actually update the password (POST)."""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT user_id, expires_at FROM password_resets WHERE token = %s", (token,))
    reset_entry = cursor.fetchone()

    if reset_entry is None:
        cursor.close()
        connection.close()
        return "This reset link is invalid or has already been used.", 400

    user_id, expires_at = reset_entry

    if datetime.now() > datetime.fromisoformat(expires_at):
        cursor.close()
        connection.close()
        return "This reset link has expired. Please request a new one.", 400

    if request.method == "POST":
        new_password = request.form["new_password"]
        hashed_password = generate_password_hash(new_password)

        cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_password, user_id))
        cursor.execute("DELETE FROM password_resets WHERE token = %s", (token,))

        connection.commit()
        cursor.close()
        connection.close()
        return redirect(url_for("login"))

    cursor.close()
    connection.close()
    return render_template("reset_password.html", error=None, token=token)

if __name__ == "__main__":
    app.run(debug=True)