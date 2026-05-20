# synced_database.py — Drop-in offline-first database wrapper for ProStock
#
# Replace every:
#   db = SQLiteDatabase()      with:
#   db = SyncedDatabase()
#
# All reads come from local SQLite (fast, works offline).
# All writes go to SQLite immediately AND are enqueued in sync_outbox so the
# SyncEngine can push them to the cloud next time it's online.
#
# Usage:
#   from synced_database import SyncedDatabase
#   from sync_engine import SyncEngine
#
#   engine = SyncEngine(local_db_path="inventory.db", cloud_url="https://...")
#   engine.start()
#
#   db = SyncedDatabase(engine)
#   items = db.get_all_items()          # reads local SQLite
#   db.add_item("Rice", 50.0, ...)      # writes local + queues for cloud

from database import SQLiteDatabase
from sync_engine import SyncEngine


class SyncedDatabase(SQLiteDatabase):
    """
    Thin subclass of SQLiteDatabase that intercepts every mutating method
    and enqueues the operation to SyncEngine's outbox for cloud delivery.
    """

    def __init__(self, sync_engine: SyncEngine, db_path: str = "inventory.db"):
        super().__init__(db_path=db_path)
        self._engine = sync_engine
        self._on_change = None
        # Register to be notified when remote pulls upsert rows into local DB
        try:
            if hasattr(self._engine, 'set_on_pull_listener'):
                self._engine.set_on_pull_listener(self._notify_change)
        except Exception:
            pass

    def set_change_listener(self, callback):
        """Set a callback that runs after any successful local write."""
        self._on_change = callback

    def _notify_change(self):
        if callable(self._on_change):
            try:
                self._on_change()
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    #  Users                                                               #
    # ------------------------------------------------------------------ #

    def add_user(self, username, password, email=None):
        result = super().add_user(username, password, email)
        if result:
            self._engine.enqueue("users", "INSERT", {
                "id": result,
                "username": username,
                "email": email,
                # Never send raw passwords to the cloud — send the hash only.
                "password_hash": self._hash_password(password),
            })
            self._notify_change()
        return result

    # ------------------------------------------------------------------ #
    #  Categories                                                          #
    # ------------------------------------------------------------------ #

    def add_category(self, name, description=None):
        result = super().add_category(name, description)
        if result:
            self._engine.enqueue("categories", "INSERT", {
                "id": result,
                "name": name,
                "description": description,
            })
            self._notify_change()
        return result

    # ------------------------------------------------------------------ #
    #  Items                                                               #
    # ------------------------------------------------------------------ #

    def add_item(self, name, price, category_id=None, sku=None, description=None,
                 quantity=0, low_stock_threshold=10, image_path=None):
        result = super().add_item(
            name, price, category_id, sku, description,
            quantity, low_stock_threshold, image_path
        )
        if result:
            self._engine.enqueue("items", "INSERT", {
                "id": result,
                "name": name, "price": price, "category_id": category_id,
                "sku": sku, "description": description, "quantity": quantity,
                "low_stock_threshold": low_stock_threshold, "image_path": image_path,
            })
            self._notify_change()
        return result

    def update_item(self, item_id, **kwargs):
        result = super().update_item(item_id, **kwargs)
        if result:
            self._engine.enqueue("items", "UPDATE", {"id": item_id, **kwargs})
            self._notify_change()
        return result

    def delete_item(self, item_id):
        result = super().delete_item(item_id)
        if result:
            self._engine.enqueue("items", "DELETE", {"id": item_id})
            self._notify_change()
        return result

    # ------------------------------------------------------------------ #
    #  Inventory / Quantity                                                #
    # ------------------------------------------------------------------ #

    def update_quantity(self, item_id, new_quantity, movement_type,
                        user_id=None, notes=None):
        result = super().update_quantity(
            item_id, new_quantity, movement_type, user_id, notes
        )
        if result:
            self._engine.enqueue("inventory_movements", "QUANTITY", {
                "item_id": item_id,
                "new_quantity": new_quantity,
                "movement_type": movement_type,
                "user_id": user_id,
                "notes": notes,
            })
            self._notify_change()
        return result

    # ------------------------------------------------------------------ #
    #  Sales                                                               #
    # ------------------------------------------------------------------ #

    def record_sale(self, item_id, quantity_sold, user_id=None, sale_price=None):
        result = super().record_sale(item_id, quantity_sold, user_id, sale_price)
        if result:
            self._engine.enqueue("sales", "SALE", {
                "item_id": item_id,
                "quantity_sold": quantity_sold,
                "user_id": user_id,
                "sale_price": sale_price,
            })
            self._notify_change()
        return result
