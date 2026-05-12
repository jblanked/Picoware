import gc
import json
import os
from grocery_lib.i18n import get_path

# --- Metadata Cache ---
_META_CACHE = None
_META_DIRTY = False

def _load_meta():
    global _META_CACHE
    if _META_CACHE is not None: return _META_CACHE
    try:
        path = get_path("lists_meta.json")
        with open(path, "r") as f:
            _META_CACHE = json.load(f)
    except (OSError, ValueError):
        _META_CACHE = {}
    return _META_CACHE

def flush_metadata():
    """Explicitly flush metadata cache to SD card."""
    global _META_DIRTY
    if _META_CACHE is None or not _META_DIRTY: return
    try:
        path = get_path("lists_meta.json")
        with open(path, "w") as f:
            json.dump(_META_CACHE, f)
        _META_DIRTY = False
    except OSError as e:
        print("[ERROR] storage.flush_meta:", e)

def get_all_list_meta():
    return _load_meta()

def update_list_meta(name, bought, total):
    global _META_DIRTY
    meta = _load_meta()
    meta[name] = [bought, total]
    _META_DIRTY = True

# --- Unified Storage Class ---
class GroceryStorage:
    """Consolidated storage manager for lists and pantry."""
    __slots__ = ("_list_cache", "_pantry_cache", "_lists_dir", "_active_list_name", "_active_list_items")
    
    def __init__(self):
        self._list_cache = None
        self._pantry_cache = None
        self._active_list_name = None
        self._active_list_items = None
        self._lists_dir = get_path("lists")
        try: os.mkdir(self._lists_dir)
        except OSError: pass

    def _retry_io(self, func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except OSError as e:
            print("[ERROR] storage IO failed, retrying:", e)
            try:
                return func(*args, **kwargs)
            except OSError as e2:
                print("[ERROR] storage retry failed:", e2)
                raise e2

    def get_list_names(self, force=False):
        if self._list_cache is not None and not force:
            return self._list_cache
        res = []
        try:
            it = os.ilistdir(self._lists_dir)
            for entry in it:
                f = entry[0]
                if f.endswith(".json"):
                    res.append(f[:-5])
            res.sort()
        except OSError as e:
            print("[ERROR] storage.get_list_names:", e)
            
        if "Default" not in res:
            try:
                self.save_items("Default", [])
                res.append("Default")
                res.sort()
            except OSError: pass
        self._list_cache = res
        return res

    def get_all_list_counts(self, force_refresh=False):
        meta = _load_meta()
        names = self.get_list_names()
        changed = False
        for name in names:
            if name not in meta or force_refresh:
                items = self.get_items(name)
                bought = sum(1 for i in items if i.get("bought", False))
                meta[name] = [bought, len(items)]
                changed = True
        
        if changed:
            global _META_DIRTY
            _META_DIRTY = True
        return meta

    def get_items(self, list_name):
        if self._active_list_name == list_name and self._active_list_items is not None:
            return self._active_list_items
        def _read():
            path = get_path("lists/" + list_name + ".json")
            with open(path, "r") as f:
                data = json.load(f)
            return data
        try:
            data = self._retry_io(_read)
            self._active_list_name = list_name
            self._active_list_items = data
            return data
        except (OSError, ValueError):
            return []

    def save_items(self, list_name, items):
        def _write():
            path = get_path("lists/" + list_name + ".json")
            with open(path, "w") as f:
                json.dump(items, f)
        try:
            self._retry_io(_write)
            if self._active_list_name == list_name:
                self._active_list_items = items
            bought = sum(1 for i in items if i.get("bought", False))
            update_list_meta(list_name, bought, len(items))
            if self._list_cache is not None and list_name not in self._list_cache:
                self._list_cache.append(list_name)
                self._list_cache.sort()
        except OSError: pass

    def create_list(self, name):
        if not name: return
        try:
            self.save_items(name, [])
            self.get_list_names(force=True)
        except OSError: pass

    def rename_list(self, old_name, new_name):
        try:
            os.rename(get_path("lists/"+old_name+".json"), get_path("lists/"+new_name+".json"))
            meta = _load_meta()
            if old_name in meta:
                meta[new_name] = meta.pop(old_name)
                global _META_DIRTY
                _META_DIRTY = True
            if self._active_list_name == old_name:
                self._active_list_name = new_name
            self.get_list_names(force=True)
        except OSError as e:
            print("[ERROR] storage.rename_list:", e)

    def remove_list(self, name):
        try:
            os.remove(get_path("lists/" + name + ".json"))
            meta = _load_meta()
            if name in meta:
                del meta[name]
                global _META_DIRTY
                _META_DIRTY = True
            if self._active_list_name == name:
                self._active_list_name = None
                self._active_list_items = None
            self.get_list_names(force=True)
        except OSError as e:
            print("[ERROR] storage.remove_list:", e)

    def get_pantry_items(self, force=False):
        if self._pantry_cache is not None and not force:
            return self._pantry_cache
        def _read():
            path = get_path("pantry.json")
            with open(path, "r") as f:
                data = json.load(f)
            return data
        try:
            self._pantry_cache = self._retry_io(_read)
        except (OSError, ValueError):
            self._pantry_cache = []
        return self._pantry_cache

    def save_pantry(self, items):
        def _write():
            path = get_path("pantry.json")
            with open(path, "w") as f:
                json.dump(items, f)
        try:
            self._retry_io(_write)
            self._pantry_cache = items
        except OSError: pass

    def add_pantry_item(self, name, qty=1, price=0.0, category="other"):
        pantry = self.get_pantry_items()
        pantry.append({"name": name, "qty": qty, "price": price, "category": category, "status": "ok"})
        self.save_pantry(pantry)

    def add_item(self, list_name, name, qty=1, price=0.0, size=0.0, category="other"):
        items = self.get_items(list_name)
        items.append({"name": name, "qty": qty, "price": price, "size": size, "category": category, "bought": False})
        self.save_items(list_name, items)

    def remap_category(self, old_cat, new_cat="other"):
        """Bulk update all items using old_cat to new_cat."""
        # 1. Update Pantry
        pantry = self.get_pantry_items(force=True)
        changed_p = False
        for item in pantry:
            if item.get("category") == old_cat:
                item["category"] = new_cat
                changed_p = True
        if changed_p: self.save_pantry(pantry)

        # 2. Update all Lists
        list_names = self.get_list_names(force=True)
        for name in list_names:
            items = self.get_items(name)
            changed_l = False
            for item in items:
                if item.get("category") == old_cat:
                    item["category"] = new_cat
                    changed_l = True
            if changed_l: self.save_items(name, items)
        
        self.sync()

    def reset_all_lists(self):
        """Delete all shopping lists and metadata."""
        try:
            it = os.ilistdir(self._lists_dir)
            for entry in it:
                f = entry[0]
                if f.endswith(".json"):
                    os.remove(self._lists_dir + "/" + f)
            
            global _META_CACHE, _META_DIRTY
            _META_CACHE = {}
            _META_DIRTY = True
            self.sync()
            self._list_cache = None
            self.get_list_names(force=True) # Re-creates Default
        except OSError as e:
            print("[ERROR] storage.reset_all_lists:", e)

    def reset_pantry(self):
        """Clear pantry items."""
        self.save_pantry([])
        self._pantry_cache = []

    def sync(self):
        flush_metadata()
