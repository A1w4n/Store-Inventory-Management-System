"""
web_server.py — Flask REST API for the Staff Purchase Portal.
Runs in a daemon thread alongside the PySide6 desktop app.
Shares the same inventory.db file.
"""

from flask import Flask, jsonify, request, send_from_directory
import os
import threading
import time

from database import InventoryDatabase

app = Flask(__name__, static_folder=".", static_url_path="")

# Use a single global database instance to avoid connection conflicts
_db_instance = None
_db_lock = threading.Lock()

def get_db(db_path="inventory.db"):
    """Get or create the shared database instance."""
    global _db_instance
    if _db_instance is None:
        with _db_lock:
            if _db_instance is None:
                _db_instance = InventoryDatabase(db_path)
    return _db_instance


# ── Static portal page ────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(".", "staff_portal.html")


# ── Serve item images ─────────────────────────────────────────────────────────

@app.route("/item-image")
def item_image():
    from flask import send_file, abort
    import os
    path = request.args.get("path", "")
    if path and os.path.isfile(path):
        return send_file(path)
    abort(404)


# ── API: list all items ───────────────────────────────────────────────────────

@app.route("/api/items")
def api_items():
    db = get_db()
    search = request.args.get("q", "").strip()
    if search:
        rows = db.search_items(search)
    else:
        rows = db.get_all_items()

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


# ── API: confirm purchase (cart checkout) ────────────────────────────────────

@app.route("/api/purchase", methods=["POST"])
def api_purchase():
    """
    Body: { "items": [{"id": 1, "qty": 2}, ...], "staff_name": "Juan" }
    Deducts stock for every line using record_sale().
    Returns per-line success/failure so the UI can show a receipt.
    """
    data = request.get_json(force=True)
    cart  = data.get("items", [])
    staff = data.get("staff_name", "Staff").strip() or "Staff"

    if not cart:
        return jsonify({"ok": False, "error": "Cart is empty."}), 400

    db = get_db()
    results = []
    all_ok  = True

    for line in cart:
        item_id = int(line["id"])
        qty     = int(line["qty"])

        if qty <= 0:
            results.append({"id": item_id, "ok": False, "error": "Invalid quantity."})
            all_ok = False
            continue

        # record_sale handles stock-check and deduction atomically
        ok = db.record_sale(
            item_id=item_id,
            quantity_sold=qty,
        )

        if ok:
            # Fetch updated quantity to return in receipt
            item_row = db.get_item(item_id)
            if item_row is None:
                results.append({"id": item_id, "ok": False, "error": "Item not found after sale."})
                all_ok = False
                continue
            item = dict(item_row)
            results.append({
                "id":           item_id,
                "ok":           True,
                "name":         item["name"],
                "qty_sold":     qty,
                "new_stock":    item["quantity"],
                "unit_price":   float(item["price"]),
                "line_total":   float(item["price"]) * qty,
            })
        else:
            # Likely insufficient stock
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


# ── Runner (called from main.py) ──────────────────────────────────────────────

def start_server(host="0.0.0.0", port=5000, db_path="inventory.db"):
    """Start Flask server with the specified database path."""
    # Initialize the global database instance with the provided path
    get_db(db_path)
    
    def run_app():
        app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)
    
    t = threading.Thread(target=run_app, daemon=True)
    t.start()
    time.sleep(1)  # Brief delay to ensure server starts
    print(f"[Staff Portal] Running at http://localhost:{port}")
    return t
