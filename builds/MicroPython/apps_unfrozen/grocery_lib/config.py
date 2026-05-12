from grocery_lib.i18n import get_path

_config = {
    "language": "en",
    "currency": "dollar",
    "decimal_separator": ".",
    "tax_region": "DE",
    "active_list": "Default",
    "sort_mode": "category",
    "categories": ["veggie", "meat", "dairy", "bakery", "frozen", "other"],
    "base_budget": 0.0,
    "list_budgets": {},
    "show_welcome": True
}

def load_config():
    global _config
    import json
    path = get_path("config.json")
    try:
        with open(path, "r") as f:
            data = json.load(f)
            if data:
                _config.update(data)
    except Exception:
        save_config()
    return _config

def save_config():
    import json
    path = get_path("config.json")
    try:
        with open(path, "w") as f:
            json.dump(_config, f)
    except Exception: pass

def get_config(key):
    return _config.get(key)

def set_config(key, value):
    _config[key] = value
    save_config()

def prune_budget(list_name):
    """Remove budget entry for a deleted list to prevent config bloat."""
    budgets = _config.get("list_budgets", {})
    if list_name in budgets:
        del budgets[list_name]
        save_config()

def clear_config():
    global _config
    _config = {
        "language": "en",
        "currency": "dollar",
        "decimal_separator": ".",
        "tax_region": "DE",
        "categories": ["veggie", "meat", "dairy", "bakery", "frozen", "other"],
        "base_budget": 0.0,
        "list_budgets": {},
        "show_welcome": True
    }
