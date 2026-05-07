"""
web_server.py — Flask REST API for the Staff Purchase Portal.
Cloud deployment version: runs as a standalone app on Railway.
Database: Supabase PostgreSQL (connection string via DATABASE_URL env var).
"""

import os
import threading
from flask import Flask, jsonify, request, send_from_directory, abort
from flask_cors import CORS
from database import InventoryDatabase

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)  # Allow requests from any origin (desktop app, browsers, etc.)

# ── Database (thread-safe singleton) ─────────────────────────────────────────

_db_instance = None
_db_lock = threading.Lock()

def get_db():
    """Return the shared InventoryDatabase instance (PostgreSQL in cloud mode)."""
    global _db_instance
    if _db_instance is None:
        with _db_lock:
            if _db_instance is None:
                _db_instance = InventoryDatabase()  # reads DATABASE_URL from env
    return _db_instance


# ── Health check ──────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


# ── Static portal page ────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "staff_portal.html")


# ── API: list all items ───────────────────────────────────────────────────────

@app.route("/api/items")
def api_items():
    db = get_db()
    search = request.args.get("q", "").strip()
    rows = db.search_items(search) if search else db.get_all_items()

    items = []
    for r in rows:
        r = dict(r)
        items.append({
            "id":            r["id"],
            "name":          r["name"],
            "sku":           r.get("sku") or "",
            "price":         float(r["price"]),
            "quantity":      r["quantity"],
            "category_name": r.get("category_name") or "Uncategorized",
            "image_path":    r.get("image_path") or "",
        })
    return jsonify(items)


# ── API: confirm purchase ────────────────────────────────────────────────────

@app.route("/api/purchase", methods=["POST"])
def api_purchase():
    """
    Body: { "items": [{"id": 1, "qty": 2}, ...], "staff_name": "Juan" }
    Deducts stock for every cart line atomically via record_sale().
    """
    data  = request.get_json(force=True)
    cart  = data.get("items", [])
    staff = (data.get("staff_name") or "Staff").strip() or "Staff"

    if not cart:
        return jsonify({"ok": False, "error": "Cart is empty."}), 400

    db      = get_db()
    results = []
    all_ok  = True

    for line in cart:
        item_id = int(line["id"])
        qty     = int(line["qty"])

        if qty <= 0:
            results.append({"id": item_id, "ok": False, "error": "Invalid quantity."})
            all_ok = False
            continue

        ok = db.record_sale(item_id=item_id, quantity_sold=qty)

        if ok:
            item_row = db.get_item(item_id)
            if item_row is None:
                results.append({"id": item_id, "ok": False, "error": "Item not found after sale."})
                all_ok = False
                continue
            item = dict(item_row)
            results.append({
                "id":         item_id,
                "ok":         True,
                "name":       item["name"],
                "qty_sold":   qty,
                "new_stock":  item["quantity"],
                "unit_price": float(item["price"]),
                "line_total": float(item["price"]) * qty,
            })
        else:
            row = db.get_item(item_id)
            row = dict(row) if row else {}
            results.append({
                "id":        item_id,
                "ok":        False,
                "name":      row.get("name", f"Item #{item_id}"),
                "qty_sold":  qty,
                "available": row.get("quantity", 0),
                "error":     "Insufficient stock.",
            })
            all_ok = False

    return jsonify({"ok": all_ok, "results": results})


# ── API: dashboard stats (for desktop app if needed) ─────────────────────────

@app.route("/api/stats")
def api_stats():
    db = get_db()
    return jsonify(db.get_dashboard_stats())

def start_server(host="0.0.0.0", port=5000, db_path="inventory.db"):
    """Start Flask server in a background thread."""
    import threading
    thread = threading.Thread(
        target=lambda: app.run(host=host, port=port, debug=False, use_reloader=False),
        daemon=True
    )
    thread.start()
    print(f"[ProStock] Staff portal started on {host}:{port}")
    return thread

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


