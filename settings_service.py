# settings_service.py — Manages persistent app settings via a JSON config file

import json
import os
from pathlib import Path


SETTINGS_FILE = Path("prostock_settings.json")

DEFAULT_SETTINGS = {
    # General
    "store_name": "My Store",
    "store_currency": "PHP",
    "store_timezone": "Asia/Manila",

    # Inventory
    "low_stock_threshold": 10,
    "auto_restock_alerts": True,
    "barcode_format": "CODE128",

    # Appearance
    "theme": "light",
    "sidebar_collapsed": False,
    "date_format": "MM/DD/YYYY",

    # Notifications
    "notify_low_stock": True,
    "notify_new_sales": False,
    "notify_restock_forecast": True,

    # AI / Reports
    "ai_model": "claude-sonnet-4-20250514",
    "ai_report_auto_generate": False,
    "report_language": "English",

    # Data
    "backup_enabled": False,
    "backup_interval_days": 7,
    "backup_path": "",

    # UI
    "ui_refresh_debounce_ms": 800,

    # Account (read-only display; changes go through StaffAccess/auth)
    "admin_username": "admin",
    "admin_email": "admin@inventory.com",
}


class SettingsService:
    """Read and write application settings to a local JSON file."""

    def __init__(self, settings_path: Path = SETTINGS_FILE):
        self._path = settings_path
        self._data: dict = {}
        self._load()

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def get(self, key: str, fallback=None):
        """Return the current value for *key*, or *fallback* if not found."""
        return self._data.get(key, DEFAULT_SETTINGS.get(key, fallback))

    def set(self, key: str, value) -> None:
        """Persist a single setting."""
        self._data[key] = value
        self._save()

    def set_many(self, updates: dict) -> None:
        """Persist multiple settings at once."""
        self._data.update(updates)
        self._save()

    def reset_to_defaults(self) -> None:
        """Wipe the config file and restore all defaults."""
        self._data = dict(DEFAULT_SETTINGS)
        self._save()

    def all(self) -> dict:
        """Return a full snapshot of the current settings."""
        merged = dict(DEFAULT_SETTINGS)
        merged.update(self._data)
        return merged

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _load(self) -> None:
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._data = {}
        else:
            self._data = dict(DEFAULT_SETTINGS)
            self._save()

    def _save(self) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except OSError as e:
            print(f"[SettingsService] Could not save settings: {e}")
