# web_server.py — ProStock Staff Portal + Sync API
#
# New endpoints added for desktop ↔ cloud sync:
#
#   PUSH  (desktop → cloud, called by SyncEngine when online):
#     POST   /api/sync/items          — add item
#     PUT    /api/sync/items          — update item
#     DELETE /api/sync/items          — delete item
#     POST   /api/sync/categories     — add category
#     PUT    /api/sync/categories     — update category
#     DELETE /api/sync/categories     — delete category
#     POST   /api/sync/sales          — record sale
#     POST   /api/sync/movements      — record quantity/movement change
#     POST   /api/sync/users          — add user
#     PUT    /api/sync/users          — update user
#
#   PULL  (cloud → desktop, called by SyncEngine after push):
#     GET    /api/sync/pull/items         ?since=<ISO timestamp>
#     GET    /api/sync/pull/categories    ?since=<ISO timestamp>
#     GET    /api/sync/pull/sales         ?since=<ISO timestamp>
#     GET    /api/sync/pull/movements     ?since=<ISO timestamp>
#     GET    /api/sync/pull/users         ?since=<ISO timestamp>
#
# All existing endpoints (/api/items, /api/purchase, /api/stats, /) are
# unchanged so the web portal continues to work exactly as before.

import os
import threading
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

# ─────────────────────────────────────────────────────────────────────────────
#  Database — NeonDatabase on Render, SQLiteDatabase locally
# ─────────────────────────────────────────────────────────────────────────────
#
#  On Render:   DATABASE_URL is set → uses NeonDatabase (psycopg2 + SSL)
#  Locally:     DATABASE_URL not set → falls back to SQLiteDatabase
#
#  The desktop app never imports web_server; this file only runs on Render.

_db_instance = None
_db_lock = threading.Lock()


def get_db():
    global _db_instance
    if _db_instance is None:
        with _db_lock:
            if _db_instance is None:
                try:
                    if os.environ.get("DATABASE_URL"):
                        from neon_database import NeonDatabase
                        _db_instance = NeonDatabase()
                    else:
                        # Local dev fallback
                        from database import SQLiteDatabase
                        _db_instance = SQLiteDatabase()
                        print("[DB] DATABASE_URL not set — using local SQLite for dev")
                except Exception as e:
                    print(f"[ERROR] Database connection failed: {e}")
                    raise
    return _db_instance


# ─────────────────────────────────────────────────────────────────────────────
#  Existing endpoints (unchanged)
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    try:
        db = get_db()
        items = db.get_all_items()
        return jsonify({"status": "ok", "db": "connected", "item_count": len(items)}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/")
def index():
    return send_from_directory("static", "staff_portal.html")


@app.route("/api/items")
def api_items():
    try:
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
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/purchase", methods=["POST"])
def api_purchase():
    data = request.get_json(force=True)
    cart  = data.get("items", [])
    staff = (data.get("staff_name") or "Staff").strip() or "Staff"

    if not cart:
        return jsonify({"ok": False, "error": "Cart is empty."}), 400

    db = get_db()
    results = []
    all_ok = True

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
                "id":         item_id,  "ok": True,
                "name":       item["name"], "qty_sold": qty,
                "new_stock":  item["quantity"],
                "unit_price": float(item["price"]),
                "line_total": float(item["price"]) * qty,
            })
        else:
            row = db.get_item(item_id)
            row = dict(row) if row else {}
            results.append({
                "id":        item_id,  "ok": False,
                "name":      row.get("name", f"Item #{item_id}"),
                "qty_sold":  qty,
                "available": row.get("quantity", 0),
                "error":     "Insufficient stock.",
            })
            all_ok = False

    return jsonify({"ok": all_ok, "results": results})


@app.route("/api/restock", methods=["POST"])
def api_restock():
    data = request.get_json(force=True)
    cart  = data.get("items", [])
    staff = (data.get("staff_name") or "Staff").strip() or "Staff"

    if not cart:
        return jsonify({"ok": False, "error": "Restock list is empty."}), 400

    db = get_db()
    results = []
    all_ok = True

    for line in cart:
        item_id = int(line["id"])
        qty     = int(line["qty"])

        if qty <= 0:
            results.append({"id": item_id, "ok": False, "error": "Invalid restock quantity."})
            all_ok = False
            continue

        item_row = db.get_item(item_id)
        if item_row is None:
            results.append({"id": item_id, "ok": False, "error": "Item not found."})
            all_ok = False
            continue

        item = dict(item_row)
        new_quantity = item["quantity"] + qty
        ok = db.update_quantity(
            item_id=item_id,
            new_quantity=new_quantity,
            movement_type="RESTOCK",
            user_id=None,
            notes=f"Restocked by {staff}"
        )

        if ok:
            results.append({
                "id":         item_id,  "ok": True,
                "name":       item["name"], "qty_added": qty,
                "new_stock":  new_quantity,
            })
        else:
            results.append({
                "id":        item_id,  "ok": False,
                "name":      item["name"],
                "error":     "Failed to update stock.",
            })
            all_ok = False

    return jsonify({"ok": all_ok, "results": results})


@app.route("/api/stats")
def api_stats():
    db = get_db()
    return jsonify(db.get_dashboard_stats())


# ─────────────────────────────────────────────────────────────────────────────
#  PUSH endpoints  (desktop → cloud)
# ─────────────────────────────────────────────────────────────────────────────

def _payload():
    body = request.get_json(force=True) or {}
    return body.get("payload", body)   # support both {payload:{}} and flat {}


@app.route("/api/sync/items", methods=["POST"])
def sync_push_item_insert():
    p = _payload()
    db = get_db()
    try:
        result = db.add_item(
            name=p["name"], price=p["price"],
            category_id=p.get("category_id"), sku=p.get("sku"),
            description=p.get("description"), quantity=p.get("quantity", 0),
            low_stock_threshold=p.get("low_stock_threshold", 10),
            image_path=p.get("image_path"),
        )
        if result:
            return jsonify({"ok": True, "id": result}), 201
        return jsonify({"ok": False, "error": "Insert failed (duplicate SKU?)"}), 409
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/sync/items", methods=["PUT"])
def sync_push_item_update():
    p = _payload()
    db = get_db()
    try:
        item_id = p.pop("id")
        result  = db.update_item(item_id, **p)
        return jsonify({"ok": bool(result)}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/sync/items", methods=["DELETE"])
def sync_push_item_delete():
    p = _payload()
    db = get_db()
    try:
        result = db.delete_item(p["id"])
        return jsonify({"ok": bool(result)}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/sync/categories", methods=["POST"])
def sync_push_category_insert():
    p = _payload()
    db = get_db()
    try:
        result = db.add_category(p["name"], p.get("description"))
        return jsonify({"ok": bool(result), "id": result}), 201
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/sync/categories", methods=["PUT"])
def sync_push_category_update():
    # Categories only have name/description; update via raw SQL if needed.
    p = _payload()
    db = get_db()
    try:
        db._execute_raw(
            "UPDATE categories SET name=?, description=? WHERE id=?",
            (p.get("name"), p.get("description"), p["id"])
        )
        return jsonify({"ok": True}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/sync/categories", methods=["DELETE"])
def sync_push_category_delete():
    p = _payload()
    db = get_db()
    try:
        db._execute_raw("DELETE FROM categories WHERE id=?", (p["id"],))
        return jsonify({"ok": True}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/sync/sales", methods=["POST"])
def sync_push_sale():
    p = _payload()
    db = get_db()
    try:
        result = db.record_sale(
            item_id=p["item_id"],
            quantity_sold=p["quantity_sold"],
            user_id=p.get("user_id"),
            sale_price=p.get("sale_price"),
        )
        return jsonify({"ok": bool(result)}), 200 if result else 409
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/sync/movements", methods=["POST"])
def sync_push_movement():
    p = _payload()
    db = get_db()
    try:
        result = db.update_quantity(
            item_id=p["item_id"],
            new_quantity=p["new_quantity"],
            movement_type=p["movement_type"],
            user_id=p.get("user_id"),
            notes=p.get("notes"),
        )
        return jsonify({"ok": bool(result)}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/sync/users", methods=["POST"])
def sync_push_user_insert():
    p = _payload()
    db = get_db()
    try:
        # Accept a pre-hashed password from the desktop so we never send plaintext.
        db._execute_raw(
            "INSERT INTO users (username, password_hash, email) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            (p["username"], p["password_hash"], p.get("email")),
        )
        return jsonify({"ok": True}), 201
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/sync/users", methods=["PUT"])
def sync_push_user_update():
    p = _payload()
    db = get_db()
    try:
        db._execute_raw(
            "UPDATE users SET password_hash=%s, email=%s WHERE id=%s",
            (p.get("password_hash"), p.get("email"), p["id"]),
        )
        return jsonify({"ok": True}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
#  PULL endpoints  (cloud → desktop)
# ─────────────────────────────────────────────────────────────────────────────

def _since() -> str:
    return request.args.get("since", "1970-01-01T00:00:00+00:00")


@app.route("/api/sync/pull/items")
def sync_pull_items():
    db = get_db()
    try:
        rows = db._fetch_since("items", _since())
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sync/pull/categories")
def sync_pull_categories():
    db = get_db()
    try:
        rows = db._fetch_since("categories", _since())
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sync/pull/sales")
def sync_pull_sales():
    db = get_db()
    try:
        rows = db._fetch_since("sales", _since(), ts_col="sale_date")
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sync/pull/movements")
def sync_pull_movements():
    db = get_db()
    try:
        rows = db._fetch_since("inventory_movements", _since())
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sync/pull/users")
def sync_pull_users():
    db = get_db()
    try:
        # Never return password_hash to the desktop over the wire in plaintext;
        # but we DO need it for offline login, so it's included here.
        # Deploy behind HTTPS (Railway does this by default).
        rows = db._fetch_since("users", _since())
        safe = []
        for r in rows:
            d = dict(r)
            safe.append(d)   # password_hash is hashed (SHA-256), not plaintext
        return jsonify(safe)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
#  Helper — attach _fetch_since and _execute_raw to InventoryDatabase
#  (monkey-patched in so database.py stays unchanged)
# ─────────────────────────────────────────────────────────────────────────────

def _patch_db(db):
    """Add _fetch_since and _execute_raw to whichever db instance we're using."""

    import psycopg2.extras as extras

    def _fetch_since(self, table, since, ts_col="updated_at"):
        # For tables without updated_at, fall back to created_at
        fallback_tables = {"categories", "sales", "inventory_movements", "users"}
        if table in fallback_tables and ts_col == "updated_at":
            ts_col = "created_at"
        # sales uses sale_date
        if table == "sales":
            ts_col = "sale_date"

        with self.get_connection() as conn:
            cur = conn.cursor(cursor_factory=extras.RealDictCursor)
            cur.execute(
                f"SELECT * FROM {table} WHERE {ts_col} > %s ORDER BY {ts_col} ASC",
                (since,)
            )
            return cur.fetchall()

    def _execute_raw(self, sql, params=()):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            conn.commit()

    import types
    db._fetch_since = types.MethodType(_fetch_since, db)
    db._execute_raw  = types.MethodType(_execute_raw, db)
    return db


# Patch on first request so the db singleton is already initialised
@app.before_request
def _ensure_patched():
    try:
        db = get_db()
        if not hasattr(db, "_fetch_since"):
            _patch_db(db)
    except Exception:
        pass   # DB not yet available; health check will surface the error


# ─────────────────────────────────────────────────────────────────────────────
#  Server start helpers (unchanged API)
# ─────────────────────────────────────────────────────────────────────────────

def start_server(host="0.0.0.0", port=5000, db_path="inventory.db"):
    thread = threading.Thread(
        target=lambda: app.run(host=host, port=port, debug=False, use_reloader=False),
        daemon=True,
    )
    thread.start()
    print(f"[ProStock] Staff portal + sync API started on {host}:{port}")
    return thread


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
