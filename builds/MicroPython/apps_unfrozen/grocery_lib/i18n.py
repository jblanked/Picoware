_translations = {}
_current_lang = None

# Pre-calculate base path once at module level to avoid overhead in get_path
try:
    import os
    _f = __file__
    if _f.startswith("/"):
        _base_path = _f.rsplit("/", 1)[0] + "/"
    else:
        _cwd = os.getcwd()
        if not _cwd.endswith("/"): _cwd += "/"
        if _f.startswith("./"): _f = _f[2:]
        if "/" in _f:
            _base_path = _cwd + _f.rsplit("/", 1)[0] + "/"
        else:
            _base_path = _cwd
except Exception:
    _base_path = "/sd/picoware/apps_unfrozen/grocery_lib/"

def get_path(subpath):
    """Resolve an absolute path within the app package."""
    return _base_path + subpath

def load_language(lang="en"):
    global _translations, _current_lang
    if _translations and _current_lang == lang:
        return
        
    import json
    try:
        path = get_path("language/" + lang + ".json")
        with open(path, "r") as f:
            _translations = json.load(f)
            _current_lang = lang
    except Exception:
        _translations = {}
        _current_lang = lang

def clear_translations():
    global _translations, _current_lang
    _translations = {}
    _current_lang = None

def translate(key):
    return _translations.get(key, key)
