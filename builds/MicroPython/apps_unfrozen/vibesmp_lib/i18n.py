import json

_translations = {}
_fallback = {}
_current_lang = ""
_storage = None
DEBUG_I18N = False

def set_storage(storage):
    global _storage
    _storage = storage

def load_language(lang="en"):
    global _translations, _fallback, _current_lang

    if not _storage:
        print("[ERROR] i18n: Storage not set")
        return

    # Try multiple paths for language files
    paths = [
        "picoware/vibesmp/lang/",
        "picoware/apps/vibesmp_lib/lang/",
        "vibesmp_lib/lang/",
        "/sd/picoware/vibesmp/lang/",
        "/sd/picoware/apps/vibesmp_lib/lang/",
        "/sd/vibesmp_lib/lang/"
    ]

    # Always try to load English as fallback first if not loaded
    if not _fallback:
        if DEBUG_I18N:
            print("[DEBUG] i18n: Looking for en.json fallback...")
        for p in paths:
            try:
                full_path = p + "en.json"
                if _storage.exists(full_path):
                    data = _storage.read(full_path)
                    if data:
                        _fallback = json.loads(data)
                        if DEBUG_I18N:
                            print(f"[DEBUG] i18n: Fallback loaded from {full_path}")
                        del data
                        from gc import collect
                        collect()
                        break
            except (OSError, ValueError) as e:
                continue
        if not _fallback:
            print("[ERROR] i18n: Could not find en.json fallback in any path")

    if _current_lang == lang and _translations:
        return

    if DEBUG_I18N:
        print(f"[DEBUG] i18n: Loading {lang}...")
    for p in paths:
        try:
            path = p + lang + ".json"
            if _storage.exists(path):
                data = _storage.read(path)
                if data:
                    _translations = json.loads(data)
                    if DEBUG_I18N:
                        print(f"[DEBUG] i18n: {lang} loaded from {path}")
                    del data
                    from gc import collect
                    collect()
                    _current_lang = lang
                    return
        except (OSError, ValueError) as e:
            continue

    print("[ERROR] i18n load failed for:", lang)
    _translations = _fallback.copy()

def t(key):
    res = _translations.get(key)
    if res is not None:
        return res
    return _fallback.get(key, key)
