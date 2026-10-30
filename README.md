# ShopEase — Stage 1: Product Listing + Cart

This is the first working stage of your e-commerce project.
It shows products on a homepage and lets you add/remove them from a cart.

## What's included
- `app.py` — Flask backend (routes, product data, cart logic)
- `templates/index.html` — homepage (product grid)
- `templates/cart.html` — cart page
- `static/css/style.css` — all styling

## How to run it

1. Open a terminal in this folder.
2. Install Flask:
   ```
   pip install -r requirements.txt
   ```
3. Run the app:
   ```
   python app.py
   ```
4. Open your browser and go to:
   ```
   http://127.0.0.1:5000
   ```

You should see 4 sample products. Click "Add to Cart", then click the cart icon
top-right to see your cart with totals.

## How it works (beginner explanation)

- `PRODUCTS` in `app.py` is a Python list of dictionaries — this is your
  "fake database" for now. Later we'll replace it with a real SQLite database.
- The cart is stored in `session`, which is a way Flask remembers data
  per-user between page loads (using a secure cookie). No database needed yet.
- `render_template()` takes an HTML file from `templates/` and fills in
  the `{{ ... }}` placeholders with real data — this is called Jinja2 templating.

## Next steps (in order)
1. ✅ Product listing + Add to cart (done — this stage)
2. User signup/login (with password hashing)
3. Forgot password (email reset)
4. Save delivery address + estimated delivery time
5. Wishlist
6. Payment integration (Razorpay/Stripe test mode)
7. Live delivery tracking (advanced — real-time GPS)

Come back and ask for the next stage whenever you're ready — we'll connect
a real database (SQLite) around Stage 2, since login needs persistent storage.
