"""
web_server.py — Flask REST API for the Staff Purchase Portal.
Authentication: QR token-based. Desktop app generates a token,
embeds it in the QR code URL. Tokens valid until app closes.
"""

import os
import threading
import secrets
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from database import InventoryDatabase

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

# Token store
_valid_tokens: set = set()
_token_lock = threading.Lock()

def generate_token() -> str:
    token = secrets.token_urlsafe(32)
    with _token_lock:
        _valid_tokens.add(token)
    print(f"[Auth] Token generated: {token[:12]}...")
    return token

def is_valid_token(token: str) -> bool:
    with _token_lock:
        return bool(token) and token in _valid_tokens

def revoke_all_tokens():
    with _token_lock:
        _valid_tokens.clear()
    print("[Auth] All tokens revoked.")

def _check_token():
    token = (
        request.args.get("token") or
        request.headers.get("X-Auth-Token") or
        (request.get_json(silent=True) or {}).get("token", "")
    )
    return is_valid_token(token)

# Database singleton
_db_instance = None
_db_lock = threading.Lock()

def get_db():
    global _db_instance
    if _db_instance is None:
        with _db_lock:
            if _db_instance is None:
                try:
                    _db_instance = InventoryDatabase()
                except Exception as e:
                    print(f"[ERROR] Database connection failed: {e}")
                    raise
    return _db_instance

EXPIRED_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Access Expired</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Segoe UI',system-ui,sans-serif;background:#f3f4f6;min-height:100vh;display:flex;align-items:center;justify-content:center}
  .card{background:white;border-radius:20px;border:1px solid #e5e7eb;box-shadow:0 4px 24px rgba(0,0,0,.08);padding:48px 40px;max-width:440px;width:90%;text-align:center}
  .icon{font-size:64px;margin-bottom:20px}
  h1{font-size:24px;font-weight:700;color:#111827;margin-bottom:12px}
  p{font-size:15px;color:#6b7280;line-height:1.6;margin-bottom:8px}
  .steps{background:#f9fafb;border-radius:12px;border:1px solid #e5e7eb;padding:20px 24px;margin:24px 0;text-align:left}
  .steps p{font-size:14px;color:#374151;margin-bottom:10px}
  .steps p:last-child{margin-bottom:0}
  .num{display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;background:#6366f1;color:white;border-radius:50%;font-size:12px;font-weight:700;margin-right:8px}
  .badge{display:inline-block;background:#fef3c7;color:#92400e;border:1px solid #fde68a;border-radius:20px;padding:4px 14px;font-size:12px;font-weight:600;margin-bottom:20px}
</style>
</head>
<body>
<div class="card">
  <div class="icon">🔒</div>
  <div class="badge">⚠️ Access Required</div>
  <h1>Portal Access Expired</h1>
  <p>This QR code link is no longer valid or has already expired.</p>
  <p>To access the Staff Portal, you need a fresh QR code from the desktop system.</p>
  <div class="steps">
    <p><span class="num">1</span>Open the <strong>ProStock desktop app</strong></p>
    <p><span class="num">2</span>Go to <strong>Staff Access</strong> in the sidebar</p>
    <p><span class="num">3</span><strong>Scan the QR code</strong> shown on screen</p>
    <p><span class="num">4</span>The portal will open with full access</p>
  </div>
  <p style="font-size:13px;color:#9ca3af">Each QR code is valid for one session only.</p>
</div>
</body>
</html>"""

@app.route("/health")
def health():
    try:
        db = get_db()
        items = db.get_all_items()
        return jsonify({"status": "ok", "db": "connected", "item_count": len(items)}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/validate-token")
def validate_token():
    token = request.args.get("token", "")
    if is_valid_token(token):
        return jsonify({"valid": True}), 200
    return jsonify({"valid": False}), 401

@app.route("/")
def index():
    if not _check_token():
        return EXPIRED_HTML, 403
    return send_from_directory("static", "staff_portal.html")

@app.route("/api/items")
def api_items():
    if not _check_token():
        return jsonify({"error": "Invalid or expired token."}), 401
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
    if not _check_token():
        return jsonify({"ok": False, "error": "Invalid or expired token."}), 401
    data  = request.get_json(force=True)
    cart  = data.get("items", [])
    staff = (data.get("staff_name") or "Staff").strip() or "Staff"
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
        ok = db.record_sale(item_id=item_id, quantity_sold=qty)
        if ok:
            item_row = db.get_item(item_id)
            if item_row is None:
                results.append({"id": item_id, "ok": False, "error": "Item not found after sale."})
                all_ok = False
                continue
            item = dict(item_row)
            results.append({
                "id": item_id, "ok": True,
                "name": item["name"], "qty_sold": qty,
                "new_stock": item["quantity"],
                "unit_price": float(item["price"]),
                "line_total": float(item["price"]) * qty,
            })
        else:
            row = db.get_item(item_id)
            row = dict(row) if row else {}
            results.append({
                "id": item_id, "ok": False,
                "name": row.get("name", f"Item #{item_id}"),
                "qty_sold": qty,
                "available": row.get("quantity", 0),
                "error": "Insufficient stock.",
            })
            all_ok = False
    return jsonify({"ok": all_ok, "results": results})

@app.route("/api/stats")
def api_stats():
    if not _check_token():
        return jsonify({"error": "Invalid or expired token."}), 401
    db = get_db()
    return jsonify(db.get_dashboard_stats())

def start_server(host="0.0.0.0", port=5000, db_path="inventory.db"):
    thread = threading.Thread(
        target=lambda: app.run(host=host, port=port, debug=False, use_reloader=False),
        daemon=True
    )
    thread.start()
    print(f"[ProStock] Staff portal started on {host}:{port}")
    return thread

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
