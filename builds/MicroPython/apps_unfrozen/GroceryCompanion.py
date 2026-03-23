from micropython import const
from picoware.gui.textbox import TextBox
from picoware.system.vector import Vector
from picoware.system.buttons import BUTTON_BACK, BUTTON_UP, BUTTON_DOWN, BUTTON_CENTER, BUTTON_LEFT, BUTTON_RIGHT, KEY_F1, KEY_F2, KEY_F3, KEY_F4, KEY_F5, BUTTON_BACKSPACE

# App States (Strings to Integer)
STATE_MENU_SHOPPING = const(1)
STATE_MENU_SETTINGS = const(2)
STATE_VIEW_LIST = const(3)
STATE_MENU_SPECIFIC_LIST = const(4)
STATE_KEYBOARD_NEW_LIST = const(5)
STATE_KEYBOARD_ADD_ITEM = const(6)
STATE_CONFIRM_EXIT_STORE = const(7)
STATE_MENU_EDIT_LIST = const(8)
STATE_MENU_EDIT_ITEM = const(9)
STATE_KEYBOARD_EDIT_ITEM = const(10)
STATE_CONFIRM_DELETE_LIST = const(11)
STATE_CONFIRM_DELETE_ITEM = const(12)
STATE_VIEW_HELP = const(13)
STATE_MENU_RECENT_ITEMS = const(14)
STATE_KEYBOARD_CLONE_LIST = const(15)
STATE_CONFIRM_UNCHECK_ALL = const(16)
STATE_KEYBOARD_RENAME_IN_STORE = const(18)
STATE_CONFIRM_CLEAR_CHECKED = const(19)
STATE_CONFIRM_CLEAR_ALL_ITEMS = const(20)
STATE_CONFIRM_TRANSFER_PANTRY = const(21)
STATE_KEYBOARD_ADD_IN_STORE = const(22)
STATE_KEYBOARD_DUPLICATE_ITEM = const(23)
STATE_MENU_CALCULATORS = const(24)
STATE_CALC_PRICE_COMPARE = const(25)
STATE_KEYBOARD_PRICE_COMPARE = const(26)
STATE_CALC_DISCOUNT = const(27)
STATE_KEYBOARD_DISCOUNT = const(28)
STATE_CALC_UNIT_CONVERT = const(29)
STATE_KEYBOARD_UNIT_CONVERT = const(30)
STATE_CALC_RUNNING_TOTAL = const(31)
STATE_KEYBOARD_RUNNING_TOTAL = const(32)
STATE_CALC_BOGO = const(33)
STATE_KEYBOARD_BOGO = const(34)
STATE_CALC_BULK = const(35)
STATE_KEYBOARD_BULK = const(36)
STATE_CALC_TAX = const(37)
STATE_KEYBOARD_TAX = const(38)
STATE_CALC_SPLIT = const(39)
STATE_KEYBOARD_SPLIT = const(40)
STATE_CONFIRM_CLEAR_CALCULATOR = const(41)
STATE_MENU_CONFIRM_SETTINGS = const(42)

class AppState:
    """Encapsulates global application state to prevent view_manager pollution."""
    def __init__(self):
        self.settings = {
            "theme_idx": 0, "lang": "en", "font_size": 1,
            "currency": "$", "decimals": 2, "dec_point": ".", "calc": {}
        }
        self.translations = {}
        self.menu = None
        self.textbox = None
        self.current_view = STATE_MENU_SHOPPING
        self.orig_mapper = None
        self.sys_bg = 0x0000
        self.sys_fg = 0xFFFF
        self.sys_hl = 0x001F
        
        # Additional attributes formerly injected into view_manager
        self.active_list_name = ""
        self.store_data = []
        self.store_idx = 0
        self.store_scroll = 0
        self.store_ui_dirty = False
        self.store_pantry_counts = {}
        self.store_exit_choice_state = 1
        self.active_item_idx = 0
        self.active_item_name = ""
        self.keyboard_just_opened = False
        self.help_return_state = STATE_MENU_SHOPPING
        self.clear_checked_return_state = STATE_MENU_SPECIFIC_LIST
        self.transfer_pantry_return_state = STATE_MENU_SPECIFIC_LIST
        self.clear_all_return_state = STATE_MENU_EDIT_LIST
        self.calc_data = []
        self.calc_selected = 0
        self.calc_return_state = STATE_MENU_CALCULATORS
        self.file_cache = {}

state = None

def _init_translations(storage, force=False):
    """
    Initializes default translations if not present on SD card.
    Loads massive strings like HELP_TEXT into storage to save memory later.
    """
    if force or not storage.exists("picoware/grocery/lang.json"):
        trans_json = r'''{"en": {"HELP_TEXT": "Grocery Companion Help\n\n[Shopping List]\nCreate, manage and edit grocery lists.\n\n[In Store Mode]\nSelect 'Shopping Mode' on a list.\n- L/R: Change quantity\n- ENTER: Check off item\n- F1: Help Overlay\n- F2: Rename Item\n- F3: Add Item\n- BS: Delete Item\n- F4/F5: Switch Lists\n- BACK: Exit mode\n\n[Pantry]\nManage your existing inventory.\n\n[Settings]\nCustomize theme, language, and font size.\n\n[Calculators]\n- BS: Reset current calculator values.\n- Price Compare: Best deal between 2 items.\n- Discount: Price after % off.\n- Unit Conv: Convert g, kg, oz, lb, L, etc.\n- Running Total: Track spending vs budget.\n- BOGO: True price of Buy 1 Get 1 deals.\n- Bulk: Total cost by weight/qty.\n- Tax: Calculate sales tax.\n- Splitter: Split bill + tip among people.\n\nMade by Slasher006 with the help GeminiAI.", "Uncheck All": "Uncheck All", "Uncheck All?": "Uncheck All?", "Clear Checked": "Clear Checked", "Clear Checked?": "Clear Checked?", "Clear All Items": "Clear All Items", "Clear All Items?": "Clear All Items?", "Transfer to Pantry": "Transfer to Pantry", "Transfer to Pantry?": "Transfer to Pantry?", "All done! Exit?": "All done! Exit?", "Reset list?": "Reset list?", "Clone List": "Clone List", "Duplicate Item": "Duplicate Item", "Move Up": "Move Up", "Move Down": "Move Down", "Sort Alphabetically": "Sort Alphabetically", "Clear History": "Clear History", "+ Type New Item": "+ Type New Item", "Category": "Category", "Produce": "Produce", "Dairy": "Dairy", "Meat": "Meat", "Pantry": "Pantry", "Frozen": "Frozen", "Beverages": "Beverages", "Household": "Household", "Bakery": "Bakery", "Sort by Category": "Sort by Category", "None": "None", "Recent Items": "Recent Items", "Item already in list!\nQuantity increased.": "Item already in list!\nQuantity increased.", "List already exists!": "List already exists!", "STORE_FOOTER": "[ENT]Chk [F2]Ed [F3]Add [BS]Del", "Calculators": "Calculators", "Price Compare": "Price Compare", "Price A": "Price A", "Qty A": "Qty A", "Price B": "Price B", "Qty B": "Qty B", "Best Deal:": "Best Deal:", "A is {:.1f}% cheaper!": "A is {:.1f}% cheaper!", "B is {:.1f}% cheaper!": "B is {:.1f}% cheaper!", "A is cheaper!": "A is cheaper!", "B is cheaper!": "B is cheaper!", "Same price!": "Same price!", "Discount Calc": "Discount Calc", "Original Price": "Original Price", "Discount %": "Discount %", "Final Price:": "Final Price:", "You Save:": "You Save:", "Currency": "Currency", "Decimals": "Decimals", "Decimal Point": "Decimal Point", "Unit Converter": "Unit Converter", "Value": "Value", "From": "From", "To": "To", "Result:": "Result:", "Running Total": "Running Total", "BOGO Calc": "BOGO Calc", "Bulk Estimator": "Bulk Estimator", "Sales Tax": "Sales Tax", "Bill Splitter": "Bill Splitter", "Budget": "Budget", "Add Amount": "Add Amount", "Manual Total": "Manual Total", "Current Total:": "Current Total:", "Remaining:": "Remaining:", "Item Price": "Item Price", "Buy Qty": "Buy Qty", "Get Qty": "Get Qty", "Real Price/Ea:": "Real Price/Ea:", "Price/Unit": "Price/Unit", "Est. Weight": "Est. Weight", "Est. Cost:": "Est. Cost:", "Pre-Tax Price": "Pre-Tax Price", "Tax %": "Tax %", "Total + Tax:": "Total + Tax:", "Total Bill": "Total Bill", "People": "People", "Tip %": "Tip %", "Cost per Person:": "Cost per Person:", "Reset Values?": "Reset Values?", "Update Translations": "Update Translations", "Language File Updated!": "Language File Updated!", "CALC_FOOTER": "[BS] Reset Values", "Confirmations": "Confirmations", "On": "On", "Off": "Off", "Exit Store": "Exit Store", "To Pantry": "To Pantry", "Reset Calc": "Reset Calc"}, "de": {"Grocery Companion": "Einkaufsbegleiter", "Shopping List": "Einkaufsliste", "Shopping Lists": "Einkaufslisten", "Pantry": "Speisekammer", "Settings": "Einstellungen", "Exit App": "App beenden", "Shopping Mode": "Einkaufsmodus", "+ Add Item": "+ Artikel hinzufuegen", "Edit List": "Liste bearbeiten", "Rename Item": "Artikel umbenennen", "Delete Item": "Artikel loeschen", "Delete List": "Liste loeschen", "Delete List?": "Liste loeschen?", "Delete Item?": "Artikel loeschen?", "+ Create New List": "+ Neue Liste erstellen", "Enter List Name": "Listenname eingeben", "Enter Item": "Artikel eingeben", "Back": "Zurueck", "Theme": "Design", "Language": "Sprache", "English": "Englisch", "German": "Deutsch", "Font Size": "Schriftgroesse", "Small": "Klein", "Medium": "Mittel", "Large": "Gross", "STORE_FOOTER": "[ENT]Chk [F2]Ed [F3]Add [BS]Del", "(Empty)": "(Leer)", "Exit store mode?": "Einkaufsmodus beenden?", "Yes": "Ja", "No": "Nein", "Uncheck All": "Alle abwaehlen", "Uncheck All?": "Alle abwaehlen?", "Clear Checked": "Abgehakte loeschen", "Clear Checked?": "Abgehakte loeschen?", "Clear All Items": "Alle Artikel loeschen", "Clear All Items?": "Alle Artikel loeschen?", "Transfer to Pantry": "In Speisekammer", "Transfer to Pantry?": "In Speisekammer?", "All done! Exit?": "Alles erledigt! Beenden?", "Reset list?": "Liste zuruecksetzen?", "Clone List": "Liste klonen", "Duplicate Item": "Artikel duplizieren", "Move Up": "Nach oben", "Move Down": "Nach unten", "Sort Alphabetically": "Alphabetisch sortieren", "Clear History": "Verlauf loeschen", "+ Type New Item": "+ Neu eingeben", "Category": "Kategorie", "Produce": "Obst/Gemuese", "Dairy": "Milchprodukte", "Meat": "Fleisch", "Pantry": "Vorrat", "Frozen": "Tiefkuehl", "Beverages": "Getraenke", "Household": "Haushalt", "Bakery": "Backwaren", "Sort by Category": "Nach Kategorie", "None": "Keine", "Recent Items": "Zuletzt verwendet", "Item already in list!\nQuantity increased.": "Bereits in Liste!\nMenge erhoeht.", "List already exists!": "Liste existiert bereits!", "Help": "Hilfe", "HELP_TEXT": "Einkaufsbegleiter Hilfe\n\n[Einkaufsliste]\nEinkaufslisten erstellen und bearbeiten.\n\n[Einkaufsmodus]\n'Einkaufsmodus' in einer Liste waehlen.\n- L/R: Menge aendern\n- ENTER: Artikel abhaken\n- F1: Hilfe Overlay\n- F2: Artikel umbenennen\n- F3: Artikel hinzufuegen\n- BS: Artikel loeschen\n- F4/F5: Liste wechseln\n- ZURUECK: Modus beenden\n\n[Speisekammer]\nVerwalte dein vorhandenes Inventar.\n\n[Einstellungen]\nDesign, Sprache und Schriftgroesse anpassen.\n\n[Rechner]\n- BS: Aktuelle Werte auf 0 zuruecksetzen.\n- Preisvergl.: Finde das beste Angebot.\n- Rabatt: Preis nach % Abzug.\n- Einheiten: g, kg, oz, lb, L usw.\n- Zwischensumme: Budget im Blick behalten.\n- BOGO: Echter Preis bei Kauf 1, Bekomme 1.\n- Mengenrechner: Kosten nach Gewicht/Menge.\n- Steuer: Mehrwertsteuer berechnen.\n- Teiler: Rechnung + Trinkgeld aufteilen.\n\nMade by Slasher006 with the help GeminiAI.", "Calculators": "Rechner", "Price Compare": "Preisvergleich", "Price A": "Preis A", "Qty A": "Menge A", "Price B": "Preis B", "Qty B": "Menge B", "Best Deal:": "Bestes Angebot:", "A is {:.1f}% billiger!": "A ist {:.1f}% billiger!", "B is {:.1f}% billiger!": "B ist {:.1f}% billiger!", "A is cheaper!": "A ist billiger!", "B is cheaper!": "B ist billiger!", "Same price!": "Gleicher Preis!", "Discount Calc": "Rabattrechner", "Original Price": "Originalpreis", "Discount %": "Rabatt %", "Final Price:": "Endpreis:", "You Save:": "Du sparst:", "Currency": "Waehrung", "Decimals": "Nachkommastellen", "Decimal Point": "Dezimalzeichen", "Unit Converter": "Einheitenrechner", "Value": "Wert", "From": "Von", "To": "Nach", "Result:": "Ergebnis:", "Running Total": "Zwischensumme", "BOGO Calc": "BOGO Rechner", "Bulk Estimator": "Mengenrechner", "Sales Tax": "Mehrwertsteuer", "Bill Splitter": "Rechnungsteiler", "Budget": "Budget", "Add Amount": "Betrag hinzufuegen", "Manual Total": "Summe (Manuell)", "Current Total:": "Aktuelle Summe:", "Remaining:": "Verbleibend:", "Item Price": "Artikelpreis", "Buy Qty": "Kaufmenge", "Get Qty": "Gratismenge", "Real Price/Ea:": "Echter Stk-Preis:", "Price/Unit": "Preis/Einheit", "Est. Weight": "Gesch. Gewicht", "Est. Cost:": "Gesch. Kosten:", "Pre-Tax Price": "Preis (Netto)", "Tax %": "Steuer %", "Total + Tax:": "Gesamt + Steuer:", "Total Bill": "Rechnungsbetrag", "People": "Personen", "Tip %": "Trinkgeld %", "Cost per Person:": "Kosten pro Person:", "Reset Values?": "Werte zuruecksetzen?", "Update Translations": "Sprachdatei aktualisieren", "Language File Updated!": "Sprachdatei aktualisiert!", "CALC_FOOTER": "[BS] Werte zuruecksetzen", "Confirmations": "Bestaetigungen", "On": "An", "Off": "Aus", "Exit Store": "Einkauf beenden", "To Pantry": "In Speisekammer", "Reset Calc": "Rechner zuruecksetzen"}}'''
        try:
            storage.write("picoware/grocery/lang.json", trans_json, "w")
        except Exception:
            pass

_THEMES = (
    ("System", 0x0000, 0xFFFF, 0x001F),
    ("Dark", 0x0000, 0xFFFF, 0x7BEF),
    ("Light", 0xFFFF, 0x0000, 0xD69A),
    ("Green", 0x0000, 0x07E0, 0x03E0),
    ("Blue", 0x0000, 0x07FF, 0x001F),
    ("Orange", 0x0000, 0xFDA0, 0x9A60)
)

_CATEGORIES = ("None", "Produce", "Dairy", "Meat", "Pantry", "Frozen", "Beverages", "Household", "Bakery")

_CONFIRM_TITLES = {
    STATE_CONFIRM_DELETE_LIST: "Delete List?",
    STATE_CONFIRM_DELETE_ITEM: "Delete Item?",
    STATE_CONFIRM_UNCHECK_ALL: "Uncheck All?",
    STATE_CONFIRM_CLEAR_CHECKED: "Clear Checked?",
    STATE_CONFIRM_CLEAR_ALL_ITEMS: "Clear All Items?",
    STATE_CONFIRM_TRANSFER_PANTRY: "Transfer to Pantry?",
    STATE_CONFIRM_CLEAR_CALCULATOR: "Reset Values?"
}

def _T(text, lang=None):
    """Translate given text using loaded localization dictionary."""
    global state
    if state is not None and text in state.translations:
        return state.translations[text]
    return text

def _update_recent_history(view_manager, item_name):
    """Adds a newly typed item into the global recent history list, avoiding duplicates."""
    if not item_name: return
    path = "picoware/grocery/history.json"
    try:
        history = _smart_serialize(view_manager.storage, path)
        if not isinstance(history, list): history = []
    except Exception:
        history = []
    
    item_lower = item_name.lower()
    i = 0
    while i < len(history):
        if str(history[i]).lower() == item_lower:
            history.pop(i)
        else:
            i += 1
        
    history.insert(0, item_name)
    while len(history) > 20:
        history.pop()
        
    _smart_deserialize(view_manager.storage, history, path)

def _get_theme_colors(theme_idx):
    """Returns the RGB565 UI colors based on the selected theme index."""
    global state
    idx = theme_idx % len(_THEMES)
    if idx == 0 and state is not None:
        return ("System", state.sys_bg, state.sys_fg, state.sys_hl)
    return _THEMES[idx]

def _blend_565(c1, c2):
    """Blends two 16-bit RGB565 colors. Useful for inactive checked item text."""
    r = (((c1 >> 11) & 0x1F) + ((c2 >> 11) & 0x1F)) >> 1
    g = (((c1 >> 5) & 0x3F) + ((c2 >> 5) & 0x3F)) >> 1
    b = ((c1 & 0x1F) + (c2 & 0x1F)) >> 1
    return (r << 11) | (g << 5) | b

def _smart_serialize(storage, path):
    """Reads from cache if available, else hits SD card."""
    global state
    if state is not None and path in state.file_cache:
        return state.file_cache[path]
    try:
        data = storage.serialize(path)
        if state is not None:
            state.file_cache[path] = data
        return data
    except Exception:
        return None

def _smart_deserialize(storage, data, path):
    """Updates RAM cache immediately and defers identical SD card writes."""
    import json
    global state
    try:
        if state is not None:
            state.file_cache[path] = data
        json_str = json.dumps(data)
        cache_key = path + "_hash"
        str_hash = hash(json_str)
        if state is not None:
            if state.file_cache.get(cache_key) == str_hash:
                return
            state.file_cache[cache_key] = str_hash
        storage.write(path, json_str, "w")
    except Exception:
        pass

def _smart_read_directory(storage, path):
    """Caches directory reads. Must be invalidated if lists are added/removed."""
    global state
    cache_key = "dir_" + path
    if state is not None and cache_key in state.file_cache:
        return state.file_cache[cache_key]
    try:
        data = storage.read_directory(path)
        if state is not None:
            state.file_cache[cache_key] = data
        return data
    except Exception:
        return []

def _build_shopping_menu(view_manager):
    """Constructs the root menu, displaying all saved shopping lists."""
    from picoware.gui.menu import Menu
    settings = state.settings
    lang = settings.get("lang", "en")
    
    _, bg, fg, hl = _get_theme_colors(settings.get("theme_idx", 0))
    draw = view_manager.draw
    app_menu = Menu(
        draw, _T("Grocery Companion", lang), 0, 320,
        fg, bg, hl, fg
    )
    app_menu.add_item(_T("+ Create New List", lang))
    
    recent_list = ""
    try:
        items = _smart_read_directory(view_manager.storage, "picoware/grocery/lists")
        lists = []
        max_dt = -1
        for item in items:
            fname = item.get("filename", "")
            if not item.get("is_directory", False) and fname.endswith(".json") and fname != "__Pantry__.json" and len(fname) > 5:
                l_name = fname[:-5]
                lists.append(l_name)
                dt = (item.get("date", 0) << 16) | item.get("time", 0)
                if dt > max_dt:
                    max_dt = dt
                    recent_list = l_name
        lists.sort()
        for list_name in lists:
            app_menu.add_item(list_name)
    except Exception:
        pass
        
    app_menu.add_item("---------------")
    app_menu.add_item(_T("Calculators", lang))
    app_menu.add_item(_T("Pantry", lang))
    app_menu.add_item(_T("Settings", lang))
    app_menu.add_item(_T("Help", lang))
    app_menu.add_item(_T("Exit App", lang))
    
    if recent_list and recent_list in lists:
        app_menu.set_selected(lists.index(recent_list) + 1)
    else:
        app_menu.set_selected(0)
        
    return app_menu

def _build_specific_list_menu(view_manager, list_name):
    from picoware.gui.menu import Menu
    settings = state.settings
    lang = settings.get("lang", "en")
    
    _, bg, fg, hl = _get_theme_colors(settings.get("theme_idx", 0))
    draw = view_manager.draw
    app_menu = Menu(
        draw, list_name, 0, 320,
        fg, bg, hl, fg
    )
    
    checked_count = 0
    path = f"picoware/grocery/lists/{list_name}.json"
    try:
        data = _smart_serialize(view_manager.storage, path)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("c", False):
                    checked_count += 1
    except Exception:
        pass
        
    app_menu.add_item(_T("Shopping Mode", lang))
    app_menu.add_item(_T("Edit List", lang))
    app_menu.add_item(_T("Clone List", lang))
    app_menu.add_item(f"{_T('Uncheck All', lang)} ({checked_count})")
    app_menu.add_item(f"{_T('Clear Checked', lang)} ({checked_count})")
    app_menu.add_item(f"{_T('Transfer to Pantry', lang)} ({checked_count})")
    app_menu.add_item(_T("Delete List", lang))
    app_menu.add_item("---------------")
    app_menu.add_item(_T("Back", lang))
    app_menu.set_selected(0)
    return app_menu

def _build_edit_list_menu(view_manager, list_name):
    from picoware.gui.menu import Menu
    settings = state.settings
    lang = settings.get("lang", "en")
    
    _, bg, fg, hl = _get_theme_colors(settings.get("theme_idx", 0))
    draw = view_manager.draw
    title = _T("Pantry", lang) if list_name == "__Pantry__" else f"{_T('Edit List', lang)}: {list_name} <F4/F5>"
    app_menu = Menu(
        draw, title, 0, 320,
        fg, bg, hl, fg
    )
    
    app_menu.add_item(_T("+ Add Item", lang))
    
    path = f"picoware/grocery/lists/{list_name}.json"
    try:
        data = _smart_serialize(view_manager.storage, path)
        if not isinstance(data, list): data = []
    except Exception:
        data = []
        
    checked_count = 0
    for item in data:
        if isinstance(item, dict) and item.get("c", False):
            checked_count += 1
            
    if data:
        app_menu.add_item(_T("Clear All Items", lang))
        app_menu.add_item(_T("Sort Alphabetically", lang))
        app_menu.add_item(_T("Sort by Category", lang))
        if list_name != "__Pantry__":
            app_menu.add_item(f"{_T('Clear Checked', lang)} ({checked_count})")
            app_menu.add_item(f"{_T('Transfer to Pantry', lang)} ({checked_count})")
        app_menu.add_item("---------------")
        for item in data:
            if isinstance(item, dict):
                app_menu.add_item(f"{item.get('q', 1)}x {item.get('n', 'Unknown')}")
            else:
                app_menu.add_item(str(item))
        app_menu.add_item("---------------")
            
    app_menu.add_item(_T("Back", lang))
    app_menu.set_selected(0)
    return app_menu

def _build_edit_item_menu(view_manager, item_name):
    from picoware.gui.menu import Menu
    settings = state.settings
    lang = settings.get("lang", "en")
    
    _, bg, fg, hl = _get_theme_colors(settings.get("theme_idx", 0))
    draw = view_manager.draw
    app_menu = Menu(
        draw, item_name, 0, 320,
        fg, bg, hl, fg
    )
    
    cat_idx = 0
    list_name = state.active_list_name
    item_idx = state.active_item_idx
    try:
        data = _smart_serialize(view_manager.storage, f"picoware/grocery/lists/{list_name}.json")
        if isinstance(data, list) and item_idx < len(data):
            item = data[item_idx]
            if isinstance(item, dict):
                cat_idx = item.get("cat", 0)
    except Exception:
        pass
        
    cat_name = _T(_CATEGORIES[cat_idx], lang)
    
    app_menu.add_item(_T("Rename Item", lang))
    app_menu.add_item(f"{_T('Category', lang)}: < {cat_name} >")
    app_menu.add_item(_T("Duplicate Item", lang))
    app_menu.add_item(_T("Delete Item", lang))
    app_menu.add_item(_T("Move Up", lang))
    app_menu.add_item(_T("Move Down", lang))
    app_menu.add_item("---------------")
    app_menu.add_item(_T("Back", lang))
    app_menu.set_selected(0)
    return app_menu

def _build_recent_items_menu(view_manager):
    from picoware.gui.menu import Menu
    settings = state.settings
    lang = settings.get("lang", "en")
    
    _, bg, fg, hl = _get_theme_colors(settings.get("theme_idx", 0))
    draw = view_manager.draw
    app_menu = Menu(
        draw, _T("Recent Items", lang), 0, 320,
        fg, bg, hl, fg
    )
    app_menu.add_item(_T("+ Type New Item", lang))
    
    try:
        history = _smart_serialize(view_manager.storage, "picoware/grocery/history.json")
        if isinstance(history, list) and history:
            app_menu.add_item(_T("Clear History", lang))
            app_menu.add_item("---------------")
            for item in history: app_menu.add_item(str(item))
            app_menu.add_item("---------------")
    except Exception: pass
        
    app_menu.add_item(_T("Back", lang))
    app_menu.set_selected(0)
    return app_menu

def _build_settings_menu(view_manager):
    from picoware.gui.menu import Menu
    settings = state.settings
    lang = settings.get("lang", "en")
    
    theme_name, bg, fg, hl = _get_theme_colors(settings.get("theme_idx", 0))
    draw = view_manager.draw
    app_menu = Menu(
        draw, _T("Settings", lang), 0, 320,
        fg, bg, hl, fg
    )
    app_menu.add_item(f"{_T('Theme', lang)}: {theme_name}")
    lang_str = _T("English", lang) if lang == "en" else _T("German", lang)
    app_menu.add_item(f"{_T('Language', lang)}: {lang_str}")
    fs = settings.get("font_size", 1)
    fs_str = _T("Small", lang) if fs == 0 else (_T("Medium", lang) if fs == 1 else _T("Large", lang))
    app_menu.add_item(f"{_T('Font Size', lang)}: {fs_str}")
    curr = settings.get("currency", "$")
    app_menu.add_item(f"{_T('Currency', lang)}: {curr}")
    dec = settings.get("decimals", 2)
    app_menu.add_item(f"{_T('Decimals', lang)}: {dec}")
    dec_p = settings.get("dec_point", ".")
    app_menu.add_item(f"{_T('Decimal Point', lang)}: {dec_p}")
    app_menu.add_item(_T("Update Translations", lang))
    app_menu.add_item(_T("Confirmations", lang))
    app_menu.add_item("---------------")
    app_menu.add_item(_T("Back", lang))
    app_menu.set_selected(0)
    return app_menu

def _build_confirm_settings_menu(view_manager):
    from picoware.gui.menu import Menu
    settings = state.settings
    lang = settings.get("lang", "en")
    conf = settings.setdefault("confirmations", {})
    
    _, bg, fg, hl = _get_theme_colors(settings.get("theme_idx", 0))
    draw = view_manager.draw
    app_menu = Menu(
        draw, _T("Confirmations", lang), 0, 320,
        fg, bg, hl, fg
    )
    def _tgl(k): return _T("On", lang) if conf.get(k, True) else _T("Off", lang)
    app_menu.add_item(f"{_T('Exit Store', lang)}: < {_tgl('exit_store')} >")
    app_menu.add_item(f"{_T('Delete List', lang)}: < {_tgl('del_list')} >")
    app_menu.add_item(f"{_T('Delete Item', lang)}: < {_tgl('del_item')} >")
    app_menu.add_item(f"{_T('Uncheck All', lang)}: < {_tgl('uncheck_all')} >")
    app_menu.add_item(f"{_T('Clear Checked', lang)}: < {_tgl('clear_checked')} >")
    app_menu.add_item(f"{_T('Clear All', lang)}: < {_tgl('clear_all')} >")
    app_menu.add_item(f"{_T('To Pantry', lang)}: < {_tgl('transfer_pantry')} >")
    app_menu.add_item(f"{_T('Reset Calc', lang)}: < {_tgl('clear_calc')} >")
    app_menu.add_item("---------------")
    app_menu.add_item(_T("Back", lang))
    app_menu.set_selected(0)
    return app_menu

def _build_calculators_menu(view_manager):
    from picoware.gui.menu import Menu
    settings = state.settings
    lang = settings.get("lang", "en")
    
    _, bg, fg, hl = _get_theme_colors(settings.get("theme_idx", 0))
    draw = view_manager.draw
    app_menu = Menu(
        draw, _T("Calculators", lang), 0, 320,
        fg, bg, hl, fg
    )
    app_menu.add_item(_T("Price Compare", lang))
    app_menu.add_item(_T("Discount Calc", lang))
    app_menu.add_item(_T("Unit Converter", lang))
    app_menu.add_item(_T("Running Total", lang))
    app_menu.add_item(_T("BOGO Calc", lang))
    app_menu.add_item(_T("Bulk Estimator", lang))
    app_menu.add_item(_T("Sales Tax", lang))
    app_menu.add_item(_T("Bill Splitter", lang))
    app_menu.add_item("---------------")
    app_menu.add_item(_T("Back", lang))
    app_menu.set_selected(0)
    return app_menu

def _switch_menu(view_manager, next_state, menu_builder, *args, **kwargs):
    """Helper to drastically reduce boilerplate when jumping between menus."""
    settings = state.settings
    state.current_view = next_state
    _, bg, _, _ = _get_theme_colors(settings.get("theme_idx", 0))
    view_manager.draw.clear(color=bg)
    state.menu = menu_builder(view_manager, *args)
    if "selected" in kwargs:
        state.menu.set_selected(kwargs["selected"])
    state.menu.draw()
    view_manager.draw.swap()

def _trigger_confirm(view_manager, next_state, conf_key):
    """Helper to bypass confirmations cleanly if user disabled them in settings."""
    global state
    if state.settings.setdefault("confirmations", {}).get(conf_key, True):
        state.current_view = next_state
        state.store_exit_choice_state = 1
        state.store_ui_dirty = True
    else:
        state.current_view = next_state
        state.store_exit_choice_state = 0
        _handle_confirmations(view_manager, override_button=BUTTON_CENTER)

def start(view_manager):
    """
    Initializes the Menu component and attaches it to the view manager.
    """
    
    global state
    state = AppState()
    state.sys_bg = view_manager.background_color
    state.sys_fg = view_manager.foreground_color
    state.sys_hl = view_manager.selected_color
    
    # --- Monkey patch input manager to capture F-keys natively for Autocomplete ---
    if not hasattr(view_manager, 'grocery_orig_mapper'):
        state.orig_mapper = view_manager.input_manager._key_to_button
        view_manager.input_manager._key_to_button = lambda k: k if 0x81 <= k <= 0x90 else state.orig_mapper(k)

    # Globals to Locals
    settings_file = "picoware/settings/grocerycompanion_set.json"
    view_manager.storage.mkdir("picoware/settings")
    view_manager.storage.mkdir("picoware/grocery")
    view_manager.storage.mkdir("picoware/grocery/lists")
    _init_translations(view_manager.storage)
    if view_manager.storage.exists(settings_file):
        loaded = _smart_serialize(view_manager.storage, settings_file)
        for k in state.settings.keys():
            if k in loaded:
                state.settings[k] = loaded[k]
    
    try:
        all_trans = view_manager.storage.serialize("picoware/grocery/lang.json")
        if isinstance(all_trans, dict):
            state.translations = all_trans.get(state.settings.get("lang", "en"), {})
        del all_trans
    except Exception:
        state.translations = {}

    theme_idx = state.settings["theme_idx"]
    _, bg, _, _ = _get_theme_colors(theme_idx)
    draw = view_manager.draw
    draw.clear(color=bg)
    
    # Initialize the main menu
    app_menu = _build_shopping_menu(view_manager)
    
    # Draw the initial menu state
    app_menu.draw()
    draw.swap()
    
    # Attach to view_manager to persist state WITHOUT global variables
    state.menu = app_menu
    # Strings to Integer
    state.current_view = STATE_MENU_SHOPPING
    
    # Clean up local initialization variables
    del app_menu, draw, bg, settings_file, theme_idx
    
    # Explicit garbage collection
    import gc
    gc.collect()
    
    return True  # Indicate successful start


def _handle_menus(view_manager):
    """
    Handles user inputs for standard Menu components, parsing UP/DOWN selection
    and delegating CENTER confirmation based on the active app state.
    """
    global state
    input_manager = view_manager.input_manager
    button = input_manager.button
    draw = view_manager.draw
    settings = state.settings
    settings_file = "picoware/settings/grocerycompanion_set.json"
    lang = settings.get("lang", "en")
    app_state = state.current_view
    
    current_menu = state.menu
    
    if button == -1:
        return
        
    # Process navigation and wrap-around logic
    if button == BUTTON_UP:
        while True:
            if current_menu.selected_index > 0:
                current_menu.scroll_up()
            elif current_menu.item_count > 0:
                current_menu.set_selected(current_menu.item_count - 1)
            if current_menu.current_item != "---------------":
                break
        current_menu.draw()
        draw.swap()
        
    elif button == BUTTON_DOWN:
        while True:
            if current_menu.selected_index < current_menu.item_count - 1:
                current_menu.scroll_down()
            elif current_menu.item_count > 0:
                current_menu.set_selected(0)
            if current_menu.current_item != "---------------":
                break
        current_menu.draw()
        draw.swap()
        
    elif button in (BUTTON_LEFT, BUTTON_RIGHT):
        # Handles Left/Right toggle values in settings and quantity editors
        selected_idx = current_menu.selected_index
        if app_state == STATE_MENU_SETTINGS:
            if selected_idx == 0: # Theme
                themes_count = len(_THEMES)
                if button == BUTTON_RIGHT:
                    settings["theme_idx"] = (settings["theme_idx"] + 1) % themes_count
                else:
                    settings["theme_idx"] = (settings["theme_idx"] - 1) % themes_count
                _smart_deserialize(view_manager.storage, settings, settings_file)
                _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu, selected=0)
            elif selected_idx == 1: # Language
                settings["lang"] = "de" if settings.get("lang", "en") == "en" else "en"
                _smart_deserialize(view_manager.storage, settings, settings_file)
                try:
                    all_trans = view_manager.storage.serialize("picoware/grocery/lang.json")
                    if isinstance(all_trans, dict):
                        state.translations = all_trans.get(settings["lang"], {})
                    del all_trans
                except Exception:
                    pass
                _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu, selected=1)
            elif selected_idx == 2: # Font Size
                settings["font_size"] = (settings.get("font_size", 1) + (1 if button == BUTTON_RIGHT else -1)) % 3
                _smart_deserialize(view_manager.storage, settings, settings_file)
                _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu, selected=2)
            elif selected_idx == 3: # Currency
                settings["currency"] = "EUR" if settings.get("currency", "$") == "$" else "$"
                _smart_deserialize(view_manager.storage, settings, settings_file)
                _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu, selected=3)
            elif selected_idx == 4: # Decimals
                settings["decimals"] = (settings.get("decimals", 2) + (1 if button == BUTTON_RIGHT else -1)) % 5
                _smart_deserialize(view_manager.storage, settings, settings_file)
                _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu, selected=4)
            elif selected_idx == 5: # Decimal Point
                settings["dec_point"] = "," if settings.get("dec_point", ".") == "." else "."
                _smart_deserialize(view_manager.storage, settings, settings_file)
                _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu, selected=5)
        elif app_state == STATE_MENU_CONFIRM_SETTINGS:
            keys = ["exit_store", "del_list", "del_item", "uncheck_all", "clear_checked", "clear_all", "transfer_pantry", "clear_calc"]
            if selected_idx < len(keys):
                k = keys[selected_idx]
                conf = settings.setdefault("confirmations", {})
                conf[k] = not conf.get(k, True)
                _smart_deserialize(view_manager.storage, settings, settings_file)
                _switch_menu(view_manager, STATE_MENU_CONFIRM_SETTINGS, _build_confirm_settings_menu, selected=selected_idx)
        elif app_state == STATE_MENU_EDIT_LIST:
            list_name = state.active_list_name
            path = f"picoware/grocery/lists/{list_name}.json"
            try:
                data = _smart_serialize(view_manager.storage, path)
                offset = 5 if list_name == "__Pantry__" else 7
                if isinstance(data, list) and (offset - 1) < selected_idx < len(data) + offset:
                    actual_idx = selected_idx - offset
                    item = data[actual_idx]
                    modified = False
                    if isinstance(item, dict):
                        qty = item.get("q", 1)
                        if button == BUTTON_RIGHT:
                            item["q"] = qty + 1
                            modified = True
                        elif button == BUTTON_LEFT and qty > 1:
                            item["q"] = qty - 1
                            modified = True
                    else:
                        qty = 2 if button == BUTTON_RIGHT else 1
                        data[actual_idx] = {"n": str(item), "q": qty, "c": False}
                        modified = True
                    
                    if modified:
                        _smart_deserialize(view_manager.storage, data, path)
                        
                        current_menu.clear()
                        current_menu.add_item(_T("+ Add Item", lang))
                        if data:
                            current_menu.add_item(_T("Clear All Items", lang))
                            current_menu.add_item(_T("Sort Alphabetically", lang))
                            current_menu.add_item(_T("Sort by Category", lang))
                            checked_count = 0
                            for i_item in data:
                                if isinstance(i_item, dict) and i_item.get("c", False):
                                    checked_count += 1
                            if list_name != "__Pantry__":
                                current_menu.add_item(f"{_T('Clear Checked', lang)} ({checked_count})")
                                current_menu.add_item(f"{_T('Transfer to Pantry', lang)} ({checked_count})")
                            current_menu.add_item("---------------")
                            for i_item in data:
                                if isinstance(i_item, dict):
                                    current_menu.add_item(f"{i_item.get('q', 1)}x {i_item.get('n', 'Unknown')}")
                                else:
                                    current_menu.add_item(str(i_item))
                            current_menu.add_item("---------------")
                                
                        current_menu.add_item(_T("Back", lang))
                        
                        current_menu.set_selected(0)
                        for _ in range(selected_idx):
                            current_menu.scroll_down()
                        current_menu.draw()
                        draw.swap()
            except Exception:
                pass
        elif app_state == STATE_MENU_EDIT_ITEM:
            if selected_idx == 1: # Category
                list_name = state.active_list_name
                item_idx = state.active_item_idx
                path = f"picoware/grocery/lists/{list_name}.json"
                try:
                    data = _smart_serialize(view_manager.storage, path)
                    if isinstance(data, list) and item_idx < len(data):
                        item = data[item_idx]
                        if not isinstance(item, dict):
                            item = {"n": str(item), "q": 1, "c": False, "cat": 0}
                            data[item_idx] = item
                            
                        cat_idx = item.get("cat", 0)
                        if button == BUTTON_RIGHT:
                            cat_idx = (cat_idx + 1) % 9
                        else:
                            cat_idx = (cat_idx - 1) % 9
                        item["cat"] = cat_idx
                        _smart_deserialize(view_manager.storage, data, path)
                        _switch_menu(view_manager, STATE_MENU_EDIT_ITEM, _build_edit_item_menu, state.active_item_name, selected=1)
                except Exception: pass
    elif button == BUTTON_CENTER:
        # Processes active row selection actions
        input_manager.reset()
        selected_idx = current_menu.selected_index
        
        if app_state == STATE_MENU_SHOPPING:
            selected_item_text = current_menu.current_item
            
            if selected_idx == 0: # Create New List
                state.current_view = STATE_KEYBOARD_NEW_LIST
                kb = view_manager.keyboard
                kb.reset()
                kb.auto_complete_words = []
                kb.title = _T("Enter List Name", lang)
                kb.response = ""
                kb.run(force=True)
                kb.run(force=True)
                state.keyboard_just_opened = True
                del kb
            elif selected_item_text == "---------------":
                pass # Fallback safety catch
            elif selected_item_text == _T("Pantry", lang):
                state.active_list_name = "__Pantry__"
                _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, "__Pantry__")
            elif selected_item_text == _T("Calculators", lang):
                _switch_menu(view_manager, STATE_MENU_CALCULATORS, _build_calculators_menu)
            elif selected_item_text == _T("Settings", lang):
                _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu)
            elif selected_item_text == _T("Help", lang):
                state.help_return_state = app_state
                state.current_view = STATE_VIEW_HELP
                _, bg, fg, _ = _get_theme_colors(settings["theme_idx"])
                draw.clear(color=bg)
                state.textbox = TextBox(draw, 0, 320, fg, bg)
                state.textbox.set_text(_T("HELP_TEXT", lang))
            elif selected_item_text == _T("Exit App", lang):
                input_manager.reset()
                view_manager.back()
            else: # Specific List selected
                list_name = selected_item_text
                state.active_list_name = list_name
                state.current_view = STATE_MENU_SPECIFIC_LIST
                _, bg, _, _ = _get_theme_colors(settings["theme_idx"])
                draw.clear(color=bg)
                state.menu = _build_specific_list_menu(view_manager, list_name)
                state.menu.draw()
                draw.swap()
                del list_name
                
            del selected_item_text
            
        elif app_state == STATE_MENU_SPECIFIC_LIST:
            list_name = state.active_list_name
            
            if selected_idx == 0: # Shopping Mode
                state.current_view = STATE_VIEW_LIST
                path = f"picoware/grocery/lists/{list_name}.json"
                try:
                    data = _smart_serialize(view_manager.storage, path)
                    if not isinstance(data, list): data = []
                except Exception:
                    data = []
                    
                # Upgrade old strings to dictionary nodes
                modified = False
                for i in range(len(data)):
                    if isinstance(data[i], str):
                        data[i] = {"n": data[i], "q": 1, "c": False}
                    
                data.sort(key=lambda x: x.get("c", False) if isinstance(x, dict) else False)
                view_manager.storage.deserialize(data, path)
                
                state.store_data = data
                state.store_idx = 0
                state.store_scroll = 0
                state.store_ui_dirty = True
                del path
            elif selected_idx == 1: # Edit List
                _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name)
            elif selected_idx == 2: # Clone List
                state.current_view = STATE_KEYBOARD_CLONE_LIST
                kb = view_manager.keyboard
                kb.reset()
                kb.auto_complete_words = []
                kb.title = _T("Enter List Name", lang)
                kb.response = ""
                kb.run(force=True)
                kb.run(force=True)
                state.keyboard_just_opened = True
                del kb
            elif selected_idx == 3: # Uncheck All
                _trigger_confirm(view_manager, STATE_CONFIRM_UNCHECK_ALL, "uncheck_all")
            elif selected_idx == 4: # Clear Checked
                state.clear_checked_return_state = STATE_MENU_SPECIFIC_LIST
                _trigger_confirm(view_manager, STATE_CONFIRM_CLEAR_CHECKED, "clear_checked")
            elif selected_idx == 5: # Transfer to Pantry
                state.transfer_pantry_return_state = STATE_MENU_SPECIFIC_LIST
                _trigger_confirm(view_manager, STATE_CONFIRM_TRANSFER_PANTRY, "transfer_pantry")
            elif selected_idx == 6: # Delete List
                _trigger_confirm(view_manager, STATE_CONFIRM_DELETE_LIST, "del_list")
            elif selected_idx == 7: # Separator
                pass
            elif selected_idx == 8: # Back
                _switch_menu(view_manager, STATE_MENU_SHOPPING, _build_shopping_menu)
                
            del list_name
            
        elif app_state == STATE_MENU_EDIT_LIST:
            list_name = state.active_list_name
            selected_item_text = current_menu.current_item
            
            if selected_item_text == "---------------":
                pass
            elif selected_item_text == _T("Back", lang):
                if list_name == "__Pantry__":
                    _switch_menu(view_manager, STATE_MENU_SHOPPING, _build_shopping_menu)
                else:
                    _switch_menu(view_manager, STATE_MENU_SPECIFIC_LIST, _build_specific_list_menu, list_name)
            elif selected_item_text == _T("+ Add Item", lang):
                _switch_menu(view_manager, STATE_MENU_RECENT_ITEMS, _build_recent_items_menu)
            elif selected_item_text == _T("Clear All Items", lang):
                state.clear_all_return_state = STATE_MENU_EDIT_LIST
                _trigger_confirm(view_manager, STATE_CONFIRM_CLEAR_ALL_ITEMS, "clear_all")
            elif selected_item_text == _T("Sort Alphabetically", lang):
                path = f"picoware/grocery/lists/{list_name}.json"
                try:
                    data = _smart_serialize(view_manager.storage, path)
                    if isinstance(data, list):
                        data.sort(key=lambda x: (x.get("c", False) if isinstance(x, dict) else False, (x.get("n", "") if isinstance(x, dict) else str(x)).lower()))
                        _smart_deserialize(view_manager.storage, data, path)
                except Exception: pass
                _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name, selected=2)
            elif selected_item_text.startswith(_T("Clear Checked", lang)):
                state.clear_checked_return_state = STATE_MENU_EDIT_LIST
                _trigger_confirm(view_manager, STATE_CONFIRM_CLEAR_CHECKED, "clear_checked")
            elif selected_item_text.startswith(_T("Transfer to Pantry", lang)):
                state.transfer_pantry_return_state = STATE_MENU_EDIT_LIST
                _trigger_confirm(view_manager, STATE_CONFIRM_TRANSFER_PANTRY, "transfer_pantry")
            elif selected_item_text == _T("Sort by Category", lang):
                path = f"picoware/grocery/lists/{list_name}.json"
                try:
                    data = _smart_serialize(view_manager.storage, path)
                    if isinstance(data, list):
                        for i in range(len(data)):
                            if not isinstance(data[i], dict):
                                data[i] = {"n": str(data[i]), "q": 1, "c": False, "cat": 0}
                        data.sort(key=lambda x: (x.get("c", False), x.get("cat", 0), x.get("n", "").lower()))
                        _smart_deserialize(view_manager.storage, data, path)
                except Exception: pass
                _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name, selected=3)
            else:
                offset = 5 if list_name == "__Pantry__" else 7
                state.active_item_idx = selected_idx - offset
                state.active_item_name = selected_item_text
                _switch_menu(view_manager, STATE_MENU_EDIT_ITEM, _build_edit_item_menu, selected_item_text)
                
        elif app_state == STATE_MENU_EDIT_ITEM:
            list_name = state.active_list_name
            item_idx = state.active_item_idx
            
            if selected_idx == 0: # Rename Item
                state.current_view = STATE_KEYBOARD_EDIT_ITEM
                kb = view_manager.keyboard
                kb.reset()
                kb.title = _T("Rename Item", lang)
                
                path = f"picoware/grocery/lists/{list_name}.json"
                try:
                    data = _smart_serialize(view_manager.storage, path)
                    if isinstance(data, list) and item_idx < len(data):
                        item = data[item_idx]
                        kb.response = item.get("n", "") if isinstance(item, dict) else str(item)
                    else:
                        kb.response = ""
                except Exception:
                    kb.response = ""
                    
                try:
                    hist = _smart_serialize(view_manager.storage, "picoware/grocery/history.json")
                    if isinstance(hist, list):
                        kb.auto_complete_words = [str(x) for x in hist]
                except Exception:
                    kb.auto_complete_words = []
                    
                kb.run(force=True)
                kb.run(force=True)
                state.keyboard_just_opened = True
                del kb
            elif selected_idx == 1: # Category
                pass
            elif selected_idx == 2: # Duplicate Item
                state.current_view = STATE_KEYBOARD_DUPLICATE_ITEM
                kb = view_manager.keyboard
                kb.reset()
                kb.title = _T("Duplicate Item", lang)
                
                path = f"picoware/grocery/lists/{list_name}.json"
                try:
                    data = _smart_serialize(view_manager.storage, path)
                    if isinstance(data, list) and item_idx < len(data):
                        item = data[item_idx]
                        kb.response = item.get("n", "") if isinstance(item, dict) else str(item)
                    else:
                        kb.response = ""
                except Exception:
                    kb.response = ""
                    
                try:
                    hist = _smart_serialize(view_manager.storage, "picoware/grocery/history.json")
                    if isinstance(hist, list):
                        kb.auto_complete_words = [str(x) for x in hist]
                except Exception:
                    kb.auto_complete_words = []
                    
                kb.run(force=True)
                kb.run(force=True)
                state.keyboard_just_opened = True
                del kb
            elif selected_idx == 3: # Delete Item
                _trigger_confirm(view_manager, STATE_CONFIRM_DELETE_ITEM, "del_item")
            elif selected_idx == 4: # Move Up
                path = f"picoware/grocery/lists/{list_name}.json"
                try:
                    data = _smart_serialize(view_manager.storage, path)
                    if isinstance(data, list) and 0 < item_idx < len(data):
                        data[item_idx], data[item_idx - 1] = data[item_idx - 1], data[item_idx]
                        _smart_deserialize(view_manager.storage, data, path)
                        state.active_item_idx -= 1
                except Exception:
                    pass
                offset = 5 if list_name == "__Pantry__" else 7
                _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name, selected=(state.active_item_idx + offset))
            elif selected_idx == 5: # Move Down
                path = f"picoware/grocery/lists/{list_name}.json"
                try:
                    data = _smart_serialize(view_manager.storage, path)
                    if isinstance(data, list) and item_idx < len(data) - 1:
                        data[item_idx], data[item_idx + 1] = data[item_idx + 1], data[item_idx]
                        _smart_deserialize(view_manager.storage, data, path)
                        state.active_item_idx += 1
                except Exception:
                    pass
                offset = 5 if list_name == "__Pantry__" else 7
                _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name, selected=(state.active_item_idx + offset))
            elif selected_idx == 6: # Separator
                pass
            elif selected_idx == 7: # Back
                offset = 5 if list_name == "__Pantry__" else 7
                _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name, selected=(state.active_item_idx + offset))
                
        elif app_state == STATE_MENU_RECENT_ITEMS:
            selected_item_text = current_menu.current_item
            if selected_item_text == "---------------":
                pass
            elif selected_item_text == _T("Back", lang):
                list_name = state.active_list_name
                _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name)
            elif selected_item_text == _T("+ Type New Item", lang):
                state.current_view = STATE_KEYBOARD_ADD_ITEM
                kb = view_manager.keyboard
                kb.reset()
                kb.title = _T("Enter Item", lang)
                kb.response = ""
                
                try:
                    hist = _smart_serialize(view_manager.storage, "picoware/grocery/history.json")
                    if isinstance(hist, list):
                        kb.auto_complete_words = [str(x) for x in hist]
                except Exception:
                    kb.auto_complete_words = []
                    
                kb.run(force=True)
                kb.run(force=True)
                state.keyboard_just_opened = True
                del kb
            elif selected_item_text == _T("Clear History", lang):
                try:
                    _smart_deserialize(view_manager.storage, [], "picoware/grocery/history.json")
                except Exception:
                    pass
                _switch_menu(view_manager, STATE_MENU_RECENT_ITEMS, _build_recent_items_menu)
            else:
                list_name = state.active_list_name
                if list_name:
                    path = f"picoware/grocery/lists/{list_name}.json"
                    try: data = _smart_serialize(view_manager.storage, path)
                    except Exception: data = []
                    if not isinstance(data, list): data = []
                    
                    found = False
                    for i in range(len(data)):
                        i_name = data[i].get("n", "") if isinstance(data[i], dict) else str(data[i])
                        if i_name.lower() == selected_item_text.lower():
                            if isinstance(data[i], dict):
                                data[i]["q"] = data[i].get("q", 1) + 1
                                data[i]["c"] = False
                            else:
                                data[i] = {"n": i_name, "q": 2, "c": False}
                            found = True
                            break
                    if not found:
                        data.append({"n": selected_item_text, "q": 1, "c": False})
                        
                    _smart_deserialize(view_manager.storage, data, path)
                    _update_recent_history(view_manager, selected_item_text)
                    if found:
                        view_manager.alert(_T("Item already in list!\nQuantity increased.", lang), False)
                    
                _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name)

        elif app_state == STATE_MENU_CALCULATORS:
            selected_item_text = current_menu.current_item
            calc_dict = settings.setdefault("calc", {})
            if selected_item_text == _T("Price Compare", lang):
                state.current_view = STATE_CALC_PRICE_COMPARE
                state.calc_data = calc_dict.setdefault("price", [0.0, 1.0, 0, 0.0, 1.0, 0])
                state.calc_selected = 0
                state.store_ui_dirty = True
            elif selected_item_text == _T("Discount Calc", lang):
                state.current_view = STATE_CALC_DISCOUNT
                state.calc_data = calc_dict.setdefault("discount", [0.0, 0.0])
                state.calc_selected = 0
                state.store_ui_dirty = True
            elif selected_item_text == _T("Unit Converter", lang):
                state.current_view = STATE_CALC_UNIT_CONVERT
                state.calc_data = calc_dict.setdefault("unit", [1.0, 0, 1])
                state.calc_selected = 0
                state.store_ui_dirty = True
            elif selected_item_text == _T("Running Total", lang):
                state.current_view = STATE_CALC_RUNNING_TOTAL
                state.calc_data = calc_dict.setdefault("total", [0.0, 0.0, 0.0])
                state.calc_selected = 0
                state.store_ui_dirty = True
            elif selected_item_text == _T("BOGO Calc", lang):
                state.current_view = STATE_CALC_BOGO
                state.calc_data = calc_dict.setdefault("bogo", [0.0, 1.0, 1.0, 100.0])
                state.calc_selected = 0
                state.store_ui_dirty = True
            elif selected_item_text == _T("Bulk Estimator", lang):
                state.current_view = STATE_CALC_BULK
                state.calc_data = calc_dict.setdefault("bulk", [0.0, 0.0])
                state.calc_selected = 0
                state.store_ui_dirty = True
            elif selected_item_text == _T("Sales Tax", lang):
                state.current_view = STATE_CALC_TAX
                state.calc_data = calc_dict.setdefault("tax", [0.0, 0.0])
                state.calc_selected = 0
                state.store_ui_dirty = True
            elif selected_item_text == _T("Bill Splitter", lang):
                state.current_view = STATE_CALC_SPLIT
                state.calc_data = calc_dict.setdefault("split", [0.0, 2.0, 0.0])
                state.calc_selected = 0
                state.store_ui_dirty = True
            elif selected_item_text == _T("Back", lang):
                _switch_menu(view_manager, STATE_MENU_SHOPPING, _build_shopping_menu)

        elif app_state == STATE_MENU_SETTINGS:
            if selected_idx == 0: # Theme
                settings["theme_idx"] = (settings["theme_idx"] + 1) % len(_THEMES)
                _smart_deserialize(view_manager.storage, settings, settings_file)
                _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu, selected=0)
            elif selected_idx == 1: # Language
                settings["lang"] = "de" if settings.get("lang", "en") == "en" else "en"
                _smart_deserialize(view_manager.storage, settings, settings_file)
                try:
                    all_trans = view_manager.storage.serialize("picoware/grocery/lang.json")
                    if isinstance(all_trans, dict):
                        state.translations = all_trans.get(settings["lang"], {})
                    del all_trans
                except Exception:
                    pass
                _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu, selected=1)
            elif selected_idx == 2: # Font Size
                settings["font_size"] = (settings.get("font_size", 1) + 1) % 3
                _smart_deserialize(view_manager.storage, settings, settings_file)
                _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu, selected=2)
            elif selected_idx == 3: # Currency
                settings["currency"] = "EUR" if settings.get("currency", "$") == "$" else "$"
                _smart_deserialize(view_manager.storage, settings, settings_file)
                _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu, selected=3)
            elif selected_idx == 4: # Decimals
                settings["decimals"] = (settings.get("decimals", 2) + 1) % 5
                _smart_deserialize(view_manager.storage, settings, settings_file)
                _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu, selected=4)
            elif selected_idx == 5: # Decimal Point
                settings["dec_point"] = "," if settings.get("dec_point", ".") == "." else "."
                _smart_deserialize(view_manager.storage, settings, settings_file)
                _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu, selected=5)
            elif selected_idx == 6: # Update Translations
                _init_translations(view_manager.storage, force=True)
                try:
                    all_trans = view_manager.storage.serialize("picoware/grocery/lang.json")
                    if isinstance(all_trans, dict):
                        state.translations = all_trans.get(lang, {})
                    del all_trans
                except Exception:
                    pass
                view_manager.alert(_T("Language File Updated!", lang), False)
                _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu, selected=6)
            elif selected_idx == 7: # Confirmations Sub-menu
                _switch_menu(view_manager, STATE_MENU_CONFIRM_SETTINGS, _build_confirm_settings_menu)
            elif selected_idx == 8: # Separator
                pass
            elif selected_idx == 9: # Back
                _switch_menu(view_manager, STATE_MENU_SHOPPING, _build_shopping_menu)
        elif app_state == STATE_MENU_CONFIRM_SETTINGS:
            if selected_idx == 9:
                _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu, selected=7)
                
    elif button in (KEY_F4, KEY_F5):
        if app_state == STATE_MENU_EDIT_LIST:
            list_name = state.active_list_name
            if list_name != "__Pantry__":
                try:
                    items = _smart_read_directory(view_manager.storage, "picoware/grocery/lists")
                    lists = []
                    for item in items:
                        fname = item.get("filename", "")
                        if not item.get("is_directory", False) and fname.endswith(".json") and fname != "__Pantry__.json":
                            lists.append(fname[:-5])
                    
                    lists.sort()
                    
                    if lists and len(lists) > 1:
                        current_idx = -1
                        if list_name in lists:
                            current_idx = lists.index(list_name)
                        
                        if current_idx != -1:
                            new_idx = (current_idx - 1) % len(lists) if button == KEY_F4 else (current_idx + 1) % len(lists)
                            list_name = lists[new_idx]
                            state.active_list_name = list_name
                            
                            _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name)
                except Exception:
                    pass
            
    elif button == BUTTON_BACK:
        if app_state == STATE_MENU_SHOPPING:
            input_manager.reset()
            view_manager.back()
        elif app_state == STATE_MENU_SETTINGS:
            _switch_menu(view_manager, STATE_MENU_SHOPPING, _build_shopping_menu)
        elif app_state == STATE_MENU_CONFIRM_SETTINGS:
            _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu, selected=7)
        elif app_state == STATE_MENU_CALCULATORS:
            _switch_menu(view_manager, STATE_MENU_SHOPPING, _build_shopping_menu)
        elif app_state == STATE_MENU_SPECIFIC_LIST:
            _switch_menu(view_manager, STATE_MENU_SHOPPING, _build_shopping_menu)
        elif app_state == STATE_MENU_EDIT_LIST:
            list_name = state.active_list_name
            if list_name == "__Pantry__":
                _switch_menu(view_manager, STATE_MENU_SHOPPING, _build_shopping_menu)
            else:
                _switch_menu(view_manager, STATE_MENU_SPECIFIC_LIST, _build_specific_list_menu, list_name)
        elif app_state == STATE_MENU_EDIT_ITEM:
            list_name = state.active_list_name
            offset = 5 if list_name == "__Pantry__" else 7
            _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name, selected=(state.active_item_idx + offset))
        elif app_state == STATE_MENU_RECENT_ITEMS:
            list_name = state.active_list_name
            _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name)
        else:
            input_manager.reset()
            view_manager.back()
        
    # Reset input to prevent multi-triggering
    input_manager.reset()
    del current_menu

def _handle_store(view_manager):
    """
    Handles the heavy-lifting logic for 'Store Mode'. Displays list items
    with custom checkbox icons, quantities, and responds to fast keyboard shortcuts.
    """
    global state
    input_manager = view_manager.input_manager
    button = input_manager.button
    
    dirty = state.store_ui_dirty
    if button == -1 and not dirty:
        return
        
    draw = view_manager.draw
    settings = state.settings
    
    list_name = state.active_list_name
    path = f"picoware/grocery/lists/{list_name}.json"
    data = state.store_data
    idx = state.store_idx
    scroll = state.store_scroll
    
    if button != -1:
        dirty = True
        if button == KEY_F1:
            state.help_return_state = STATE_VIEW_LIST
            state.current_view = STATE_VIEW_HELP
            _, bg, fg, _ = _get_theme_colors(settings["theme_idx"])
            draw.clear(color=bg)
            state.textbox = TextBox(draw, 0, 320, fg, bg)
            state.textbox.set_text(_T("HELP_TEXT"))
        elif button == BUTTON_UP:
            # Custom scrolling logic for store mode view
            if idx > 0:
                idx -= 1
            elif data:
                idx = len(data) - 1
            if idx < scroll: scroll = idx
        elif button == BUTTON_DOWN:
            if idx < len(data) - 1:
                idx += 1
            elif data:
                idx = 0
                scroll = 0
        elif button == BUTTON_LEFT and data:
            # Decrease item quantity directly from the store UI
            if not data[idx].get("c", False) and data[idx].get("q", 1) > 1:
                data[idx]["q"] -= 1
                _smart_deserialize(view_manager.storage, data, path)
        elif button == BUTTON_RIGHT and data:
            # Increase item quantity directly from the store UI
            if not data[idx].get("c", False):
                data[idx]["q"] = data[idx].get("q", 1) + 1
                _smart_deserialize(view_manager.storage, data, path)
        elif button == BUTTON_CENTER and data:
            # Toggle Checkbox and reorganize the list so checked items sink to the bottom
            toggled_item = data[idx]
            toggled_item["c"] = not toggled_item.get("c", False)
            data.sort(key=lambda x: x.get("c", False) if isinstance(x, dict) else False)
            _smart_deserialize(view_manager.storage, data, path)
            
            if data and all(item.get("c", False) for item in data):
                _trigger_confirm(view_manager, STATE_CONFIRM_EXIT_STORE, "exit_store")
        elif button == KEY_F2:
            if data:
                state.current_view = STATE_KEYBOARD_RENAME_IN_STORE
                kb = view_manager.keyboard
                kb.reset()
                kb.title = _T("Rename Item")
                
                item = data[idx]
                kb.response = item.get("n", "") if isinstance(item, dict) else str(item)
                
                try:
                    hist = _smart_serialize(view_manager.storage, "picoware/grocery/history.json")
                    if isinstance(hist, list):
                        kb.auto_complete_words = [str(x) for x in hist]
                except Exception:
                    kb.auto_complete_words = []
                    
                kb.run(force=True)
                kb.run(force=True)
                state.keyboard_just_opened = True
                del kb
            else:
                state.current_view = STATE_MENU_EDIT_LIST
                _, bg, _, _ = _get_theme_colors(settings["theme_idx"])
                draw.clear(color=bg)
                state.menu = _build_edit_list_menu(view_manager, list_name)
                state.menu.draw()
                draw.swap()
        elif button == BUTTON_BACKSPACE and data:
            try:
                if isinstance(data, list) and idx < len(data):
                    data.pop(idx)
                    _smart_deserialize(view_manager.storage, data, path)
                    state.store_data = data
                    if idx >= len(data) and idx > 0:
                        idx -= 1
                    if idx < scroll: scroll = idx
                    if not data:
                        idx = 0
                        scroll = 0
            except Exception:
                pass
        elif button == KEY_F3:
            state.current_view = STATE_KEYBOARD_ADD_IN_STORE
            kb = view_manager.keyboard
            kb.reset()
            kb.title = _T("Enter Item")
            kb.response = ""
            
            try:
                hist = _smart_serialize(view_manager.storage, "picoware/grocery/history.json")
                if isinstance(hist, list):
                    kb.auto_complete_words = [str(x) for x in hist]
            except Exception:
                kb.auto_complete_words = []
                
            kb.run(force=True)
            kb.run(force=True)
            state.keyboard_just_opened = True
            del kb
        elif button in (KEY_F4, KEY_F5):
            # Fast list switching shortcut without exiting store mode
            try:
                items = _smart_read_directory(view_manager.storage, "picoware/grocery/lists")
                lists = []
                for item in items:
                    fname = item.get("filename", "")
                    if not item.get("is_directory", False) and fname.endswith(".json") and fname != "__Pantry__.json":
                        lists.append(fname[:-5])
                
                lists.sort()
                
                if lists and len(lists) > 1:
                    current_idx = -1
                    if list_name in lists:
                        current_idx = lists.index(list_name)
                    
                    if current_idx != -1:
                        new_idx = (current_idx - 1) % len(lists) if button == KEY_F4 else (current_idx + 1) % len(lists)
                        
                        list_name = lists[new_idx]
                        state.active_list_name = list_name
                        
                        path = f"picoware/grocery/lists/{list_name}.json"
                        try:
                            data = _smart_serialize(view_manager.storage, path)
                            if not isinstance(data, list): data = []
                        except Exception:
                            data = []
                            
                        modified = False
                        for i in range(len(data)):
                            if isinstance(data[i], str):
                                data[i] = {"n": data[i], "q": 1, "c": False}
                                modified = True
                            
                        data.sort(key=lambda x: x.get("c", False) if isinstance(x, dict) else False)
                        if modified:
                            _smart_deserialize(view_manager.storage, data, path)
                            
                        state.store_data = data
                        idx = scroll = state.store_idx = state.store_scroll = 0
                        _prune_file_cache()
            except Exception:
                pass
        elif button == BUTTON_BACK:
            _trigger_confirm(view_manager, STATE_CONFIRM_EXIT_STORE, "exit_store")
            
        state.store_idx = idx
        state.store_scroll = scroll
        input_manager.reset()
        
    if not dirty or state.current_view != STATE_VIEW_LIST:
        return
        
    # Redraw logic for custom list view
    state.store_ui_dirty = False
    font_size = settings.get("font_size", 1)
    
    if not state.store_pantry_counts.get("_loaded", False):
        try:
            pantry = _smart_serialize(view_manager.storage, "picoware/grocery/lists/__Pantry__.json")
            counts = {"_loaded": True}
            if isinstance(pantry, list):
                for p in pantry:
                    n = p.get("n", "") if isinstance(p, dict) else str(p)
                    q = p.get("q", 1) if isinstance(p, dict) else 1
                    counts[n.lower()] = q
            state.store_pantry_counts = counts
        except Exception:
            state.store_pantry_counts = {"_loaded": True}
            
    _, bg, fg, hl = _get_theme_colors(settings["theme_idx"])
    checked_col = _blend_565(fg, bg)
    draw.clear(color=bg)
    
    vec1 = Vector(0, 0)
    vec2 = Vector(320, 26)
    draw.fill_rectangle(vec1, vec2, hl)
    vec1.x = 5; vec1.y = 5
    draw.text(vec1, list_name, bg)
    
    hint_str = "<F4/F5>"
    hw = draw.len(hint_str)
    vec1.x = 320 - hw - 10; vec1.y = 5
    draw.text(vec1, hint_str, bg)
    
    font_h = draw.get_font(font_size).height
    row_h = font_h + 12
    max_visible = (320 - 50) // row_h
    
    if idx >= scroll + max_visible:
        scroll = idx - max_visible + 1
        state.store_scroll = scroll
        
    y = 30
    r_3 = row_h // 3
    dots_w = draw.len("...", font_size)
    pantry_counts = state.store_pantry_counts
    
    cat_cache = {0: ""}
    for c in range(1, len(_CATEGORIES)):
        cat_cache[c] = f"[{_T(_CATEGORIES[c])[:3]}] "
        
    for i in range(scroll, min(len(data), scroll + max_visible)):
        item = data[i]
        is_sel = (i == idx)
        is_checked = item.get("c", False)
        item_name = item.get("n", "Unknown")
        
        if is_sel:
            vec1.x = 0; vec1.y = y
            vec2.x = 320; vec2.y = row_h
            draw.fill_rectangle(vec1, vec2, hl)
            text_col = fg if is_checked else bg
        else:
            text_col = checked_col if is_checked else fg
            
        circ_y = y + row_h // 2
        vec1.x = 15; vec1.y = circ_y
        draw.circle(vec1, r_3, text_col)
        if is_checked:
            draw.fill_circle(vec1, r_3 - 2, text_col)
            
        cat_str = cat_cache.get(item.get("cat", 0), "")
        text_str = f"{cat_str}{item.get('q', 1)}x {item_name}"
        p_qty = pantry_counts.get(item_name.lower(), 0)
        p_str = f"[{p_qty}]" if p_qty > 0 else ""
        p_w = draw.len(p_str, font_size) if p_qty > 0 else 0
        max_w = 320 - 35 - p_w - 10
        
        if draw.len(text_str, font_size) > max_w:
            while draw.len(text_str, font_size) + dots_w > max_w and len(text_str) > 3:
                text_str = text_str[:-1]
            text_str += "..."
            
        vec1.x = 35; vec1.y = y + 6
        draw.text(vec1, text_str, text_col, font_size)
        
        if is_checked:
            text_w = draw.len(text_str, font_size)
            vec1.x = 35; vec1.y = circ_y
            vec2.x = 35 + text_w; vec2.y = circ_y
            draw.line_custom(vec1, vec2, text_col)
            
        if p_qty > 0:
            vec1.x = 320 - p_w - 5; vec1.y = y + 6
            draw.text(vec1, p_str, text_col, font_size)
            
        y += row_h
        
    if not data:
        vec1.x = 10; vec1.y = 40
        draw.text(vec1, _T("(Empty)"), fg, font_size)
        
    vec1.x = 0; vec1.y = 320 - 20
    vec2.x = 320; vec2.y = 20
    draw.fill_rectangle(vec1, vec2, bg)
    
    vec1.x = 0; vec1.y = 300
    vec2.x = 320; vec2.y = 300
    draw.line_custom(vec1, vec2, fg)
    
    vec1.x = 5; vec1.y = 304
    draw.text(vec1, _T("STORE_FOOTER"), fg)
    
    draw.swap()
    del vec1, vec2
            
def _handle_confirmations(view_manager, override_button=None):
    """
    Handles logic for drawing and evaluating all Yes/No prompt modals
    (e.g., Delete List, Clear Checked, Transfer to Pantry).
    """
    global state
    input_manager = view_manager.input_manager
    button = override_button if override_button is not None else input_manager.button
    draw = view_manager.draw
    settings = state.settings
    app_state = state.current_view

    choice_state = state.store_exit_choice_state
    dirty = state.store_ui_dirty
    
    if button != -1:
        dirty = True
        if button in (BUTTON_LEFT, BUTTON_UP):
            choice_state = 0
        elif button in (BUTTON_RIGHT, BUTTON_DOWN):
            choice_state = 1
        elif button == BUTTON_CENTER:
            if app_state == STATE_CONFIRM_EXIT_STORE:
                if choice_state == 0: # Yes
                    data = state.store_data
                    all_checked = all(item.get("c", False) for item in data) if data else False
                    
                    if all_checked:
                        state.current_view = STATE_CONFIRM_TRANSFER_PANTRY
                        state.transfer_pantry_return_state = STATE_CONFIRM_CLEAR_ALL_ITEMS
                        state.clear_all_return_state = STATE_MENU_SPECIFIC_LIST
                        state.store_data = []
                        state.store_idx = 0
                        state.store_scroll = 0
                        state.store_pantry_counts = {}
                        _trigger_confirm(view_manager, STATE_CONFIRM_TRANSFER_PANTRY, "transfer_pantry")
                        if override_button is None:
                            input_manager.reset()
                        return
                    else:
                        state.current_view = STATE_MENU_SPECIFIC_LIST
                        list_name = state.active_list_name
                        state.store_data = []
                        state.store_idx = 0
                        state.store_scroll = 0
                        state.store_pantry_counts = {}
                        choice_state = 1
                        
                        _switch_menu(view_manager, STATE_MENU_SPECIFIC_LIST, _build_specific_list_menu, list_name)
                else: # No
                    state.current_view = STATE_VIEW_LIST
                    state.store_ui_dirty = True
                    choice_state = 1
            elif app_state == STATE_CONFIRM_DELETE_LIST:
                if choice_state == 0: # Yes
                    list_name = state.active_list_name
                    if list_name is not None:
                        try: view_manager.storage.remove(f"picoware/grocery/lists/{list_name}.json")
                        except Exception: pass
                        try:
                            if state is not None and "dir_picoware/grocery/lists" in state.file_cache:
                                del state.file_cache["dir_picoware/grocery/lists"]
                        except Exception: pass
                    
                    state.active_list_name = ""
                    state.store_data = []
                    state.store_idx = 0
                    state.store_scroll = 0
                    state.store_pantry_counts = {}
                    choice_state = 1
                    
                    _switch_menu(view_manager, STATE_MENU_SHOPPING, _build_shopping_menu)
                else: # No
                    list_name = state.active_list_name
                    choice_state = 1
                    _switch_menu(view_manager, STATE_MENU_SPECIFIC_LIST, _build_specific_list_menu, list_name)
            elif app_state == STATE_CONFIRM_DELETE_ITEM:
                if choice_state == 0: # Yes
                    list_name = state.active_list_name
                    item_idx = state.active_item_idx
                    path = f"picoware/grocery/lists/{list_name}.json"
                    try:
                        data = _smart_serialize(view_manager.storage, path)
                        if isinstance(data, list) and item_idx < len(data):
                            data.pop(item_idx)
                            _smart_deserialize(view_manager.storage, data, path)
                            if item_idx >= len(data) and item_idx > 0:
                                state.active_item_idx = item_idx - 1
                    except Exception:
                        pass
                        
                    choice_state = 1
                    offset = 5 if list_name == "__Pantry__" else 7
                    _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name, selected=(state.active_item_idx + offset))
                else: # No
                    item_name = state.active_item_name
                    choice_state = 1
                    _switch_menu(view_manager, STATE_MENU_EDIT_ITEM, _build_edit_item_menu, item_name, selected=3)
            elif app_state == STATE_CONFIRM_UNCHECK_ALL:
                list_name = state.active_list_name
                if choice_state == 0: # Yes
                    path = f"picoware/grocery/lists/{list_name}.json"
                    try:
                        data = _smart_serialize(view_manager.storage, path)
                        if isinstance(data, list):
                            modified = False
                            for item in data:
                                if isinstance(item, dict) and item.get("c", False):
                                    item["c"] = False
                                    modified = True
                            if modified:
                                _smart_deserialize(view_manager.storage, data, path)
                    except Exception:
                        pass
                
                choice_state = 1
                _switch_menu(view_manager, STATE_MENU_SPECIFIC_LIST, _build_specific_list_menu, list_name, selected=3)
            elif app_state == STATE_CONFIRM_CLEAR_CHECKED:
                list_name = state.active_list_name
                if choice_state == 0: # Yes
                    path = f"picoware/grocery/lists/{list_name}.json"
                    try:
                        data = _smart_serialize(view_manager.storage, path)
                        if isinstance(data, list):
                            new_data = [item for item in data if not (isinstance(item, dict) and item.get("c", False))]
                            if len(new_data) != len(data):
                                _smart_deserialize(view_manager.storage, new_data, path)
                    except Exception:
                        pass
                
                ret_state = state.clear_checked_return_state
                state.clear_checked_return_state = STATE_MENU_SPECIFIC_LIST
                choice_state = 1
                
                if ret_state == STATE_MENU_SPECIFIC_LIST:
                    _switch_menu(view_manager, ret_state, _build_specific_list_menu, list_name, selected=4)
                else:
                    _switch_menu(view_manager, ret_state, _build_edit_list_menu, list_name, selected=4)
            elif app_state == STATE_CONFIRM_CLEAR_ALL_ITEMS:
                list_name = state.active_list_name
                if choice_state == 0: # Yes
                    path = f"picoware/grocery/lists/{list_name}.json"
                    try:
                        _smart_deserialize(view_manager.storage, [], path)
                    except Exception:
                        pass
                
                ret_state = getattr(state, 'clear_all_return_state', STATE_MENU_EDIT_LIST)
                state.clear_all_return_state = STATE_MENU_EDIT_LIST
                choice_state = 1
                
                if ret_state == STATE_MENU_SPECIFIC_LIST:
                    _switch_menu(view_manager, STATE_MENU_SPECIFIC_LIST, _build_specific_list_menu, list_name)
                else:
                    _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name, selected=1)
            elif app_state == STATE_CONFIRM_TRANSFER_PANTRY:
                list_name = state.active_list_name
                if choice_state == 0: # Yes
                    path = f"picoware/grocery/lists/{list_name}.json"
                    pantry_path = "picoware/grocery/lists/__Pantry__.json"
                    try:
                        data = _smart_serialize(view_manager.storage, path)
                        pantry_data = _smart_serialize(view_manager.storage, pantry_path)
                        if not isinstance(pantry_data, list): pantry_data = []
                        if isinstance(data, list):
                            checked_items = [item for item in data if isinstance(item, dict) and item.get("c", False)]
                            new_data = [item for item in data if not (isinstance(item, dict) and item.get("c", False))]
                            
                            if checked_items:
                                for c_item in checked_items:
                                    c_name = c_item.get("n", "")
                                    c_qty = c_item.get("q", 1)
                                    found = False
                                    for i in range(len(pantry_data)):
                                        p_name = pantry_data[i].get("n", "") if isinstance(pantry_data[i], dict) else str(pantry_data[i])
                                        if p_name.lower() == c_name.lower():
                                            if isinstance(pantry_data[i], dict):
                                                pantry_data[i]["q"] = pantry_data[i].get("q", 1) + c_qty
                                                pantry_data[i]["c"] = False
                                            else:
                                                pantry_data[i] = {"n": p_name, "q": c_qty + 1, "c": False}
                                            found = True
                                            break
                                    if not found:
                                        pantry_data.append({"n": c_name, "q": c_qty, "c": False})
                                        
                                _smart_deserialize(view_manager.storage, new_data, path)
                                _smart_deserialize(view_manager.storage, pantry_data, pantry_path)
                    except Exception:
                        pass
                
                ret_state = state.transfer_pantry_return_state
                state.transfer_pantry_return_state = STATE_MENU_SPECIFIC_LIST
                choice_state = 1
                
                if ret_state == STATE_CONFIRM_CLEAR_ALL_ITEMS:
                    _trigger_confirm(view_manager, STATE_CONFIRM_CLEAR_ALL_ITEMS, "clear_all")
                    if override_button is None:
                        input_manager.reset()
                    return
                elif ret_state == STATE_MENU_SPECIFIC_LIST:
                    _switch_menu(view_manager, ret_state, _build_specific_list_menu, list_name, selected=5)
                else:
                    _switch_menu(view_manager, ret_state, _build_edit_list_menu, list_name, selected=5)
            elif app_state == STATE_CONFIRM_CLEAR_CALCULATOR:
                ret_state = state.calc_return_state
                if choice_state == 0: # Yes
                    if ret_state == STATE_CALC_PRICE_COMPARE:
                        state.calc_data[:] = [0.0, 1.0, 0, 0.0, 1.0, 0]
                    elif ret_state == STATE_CALC_DISCOUNT:
                        state.calc_data[:] = [0.0, 0.0]
                    elif ret_state == STATE_CALC_UNIT_CONVERT:
                        state.calc_data[:] = [1.0, 0, 1]
                    elif ret_state == STATE_CALC_RUNNING_TOTAL:
                        state.calc_data[:] = [0.0, 0.0, 0.0]
                    elif ret_state == STATE_CALC_BOGO:
                        state.calc_data[:] = [0.0, 1.0, 1.0, 100.0]
                    elif ret_state == STATE_CALC_BULK:
                        state.calc_data[:] = [0.0, 0.0]
                    elif ret_state == STATE_CALC_TAX:
                        state.calc_data[:] = [0.0, 0.0]
                    elif ret_state == STATE_CALC_SPLIT:
                        state.calc_data[:] = [0.0, 2.0, 0.0]
                    _smart_deserialize(view_manager.storage, settings, "picoware/settings/grocerycompanion_set.json")
                
                state.current_view = ret_state
                choice_state = 1
                state.calc_return_state = STATE_MENU_CALCULATORS
                state.store_ui_dirty = True
                
        elif button == BUTTON_BACK:
            choice_state = 1
            if app_state == STATE_CONFIRM_EXIT_STORE:
                state.current_view = STATE_VIEW_LIST
                state.store_ui_dirty = True
            elif app_state == STATE_CONFIRM_DELETE_LIST:
                list_name = state.active_list_name
                _switch_menu(view_manager, STATE_MENU_SPECIFIC_LIST, _build_specific_list_menu, list_name)
            elif app_state == STATE_CONFIRM_DELETE_ITEM:
                item_name = state.active_item_name
                _switch_menu(view_manager, STATE_MENU_EDIT_ITEM, _build_edit_item_menu, item_name, selected=3)
            elif app_state == STATE_CONFIRM_UNCHECK_ALL:
                list_name = state.active_list_name
                _switch_menu(view_manager, STATE_MENU_SPECIFIC_LIST, _build_specific_list_menu, list_name, selected=3)
            elif app_state == STATE_CONFIRM_CLEAR_CHECKED:
                ret_state = state.clear_checked_return_state
                state.clear_checked_return_state = STATE_MENU_SPECIFIC_LIST
                list_name = state.active_list_name
                if ret_state == STATE_MENU_SPECIFIC_LIST:
                    _switch_menu(view_manager, ret_state, _build_specific_list_menu, list_name, selected=4)
                else:
                    _switch_menu(view_manager, ret_state, _build_edit_list_menu, list_name, selected=4)
            elif app_state == STATE_CONFIRM_CLEAR_ALL_ITEMS:
                list_name = state.active_list_name
                ret_state = getattr(state, 'clear_all_return_state', STATE_MENU_EDIT_LIST)
                state.clear_all_return_state = STATE_MENU_EDIT_LIST
                if ret_state == STATE_MENU_SPECIFIC_LIST:
                    _switch_menu(view_manager, STATE_MENU_SPECIFIC_LIST, _build_specific_list_menu, list_name)
                else:
                    _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name, selected=1)
            elif app_state == STATE_CONFIRM_TRANSFER_PANTRY:
                ret_state = state.transfer_pantry_return_state
                state.transfer_pantry_return_state = STATE_MENU_SPECIFIC_LIST
                list_name = state.active_list_name
                if ret_state == STATE_CONFIRM_CLEAR_ALL_ITEMS:
                    state.current_view = STATE_CONFIRM_CLEAR_ALL_ITEMS
                    state.store_exit_choice_state = 1
                    state.store_ui_dirty = True
                elif ret_state == STATE_MENU_SPECIFIC_LIST:
                    _switch_menu(view_manager, ret_state, _build_specific_list_menu, list_name, selected=5)
                else:
                    _switch_menu(view_manager, ret_state, _build_edit_list_menu, list_name, selected=5)
            elif app_state == STATE_CONFIRM_CLEAR_CALCULATOR:
                ret_state = state.calc_return_state
                state.current_view = ret_state
                state.calc_return_state = STATE_MENU_CALCULATORS
                state.store_ui_dirty = True
            
        state.store_exit_choice_state = choice_state
        if override_button is None:
            input_manager.reset()
        
    app_state = state.current_view
    if dirty and app_state in (STATE_CONFIRM_EXIT_STORE, STATE_CONFIRM_DELETE_LIST, STATE_CONFIRM_DELETE_ITEM, STATE_CONFIRM_UNCHECK_ALL, STATE_CONFIRM_CLEAR_CHECKED, STATE_CONFIRM_CLEAR_ALL_ITEMS, STATE_CONFIRM_TRANSFER_PANTRY, STATE_CONFIRM_CLEAR_CALCULATOR):
        state.store_ui_dirty = False
        _, bg, fg, hl = _get_theme_colors(settings["theme_idx"])
        
        draw.clear(color=bg)
        
        v1 = Vector(20, 100)
        v2 = Vector(280, 120)
        draw.rect(v1, v2, fg)
        
        if app_state == STATE_CONFIRM_EXIT_STORE:
            data = state.store_data
            all_checked = all(item.get("c", False) for item in data) if data else False
            title_str = _T("All done! Exit?") if all_checked else _T("Exit store mode?")
        else:
            title_str = _T(_CONFIRM_TITLES.get(app_state, ""))
        
        font_sz = 2
        tw = draw.len(title_str, font_sz)
        draw.text(Vector(20 + (280 - tw)//2, 115), title_str, fg, font_sz)
        
        opt_yes = _T("Yes")
        yw = draw.len(opt_yes, font_sz)
        y_pos = Vector(70, 170)
        if choice_state == 0:
            draw.fill_rectangle(Vector(y_pos.x - 10, y_pos.y - 5), Vector(yw + 20, 26), hl)
            draw.text(y_pos, opt_yes, bg, font_sz)
        else:
            draw.text(y_pos, opt_yes, fg, font_sz)
            
        opt_no = _T("No")
        nw = draw.len(opt_no, font_sz)
        n_pos = Vector(250 - nw, 170)
        if choice_state == 1:
            draw.fill_rectangle(Vector(n_pos.x - 10, n_pos.y - 5), Vector(nw + 20, 26), hl)
            draw.text(n_pos, opt_no, bg, font_sz)
        else:
            draw.text(n_pos, opt_no, fg, font_sz)
            
        draw.swap()
        del v1, v2, y_pos, n_pos

def _draw_calc_results(draw, app_state, cdata, font_size, y, fg, hl, dec, curr, dp, c_units, c_units_uc):
    fmt_str = "{:." + str(dec) + "f}"
    
    def _draw_res(lbl, val, y_pos, val_col=hl):
        draw.text(Vector(10, y_pos), _T(lbl), fg, font_size)
        v_str = fmt_str.format(val).replace('.', dp) + f" {curr}"
        draw.text(Vector(310 - draw.len(v_str, font_size), y_pos), v_str, val_col, font_size)
        
    if app_state == STATE_CALC_PRICE_COMPARE:
        pa, qa, ua, pb, qb, ub = cdata[0], cdata[1] if cdata[1] > 0 else 1.0, int(cdata[2]), cdata[3], cdata[4] if cdata[4] > 0 else 1.0, int(cdata[5])
        mults = (1.0, 1.0, 1000.0, 28.3495, 453.592, 1.0, 1000.0, 29.5735, 3785.41)
        val_a = pa / (qa * mults[ua])
        val_b = pb / (qb * mults[ub])
        if val_a == 0 and val_b == 0: res_str = "---"
        elif val_a < val_b: res_str = _T("A is {:.1f}% cheaper!").format(((val_b - val_a) / val_b) * 100).replace('.', dp) if val_b > 0 else _T("A is cheaper!")
        elif val_b < val_a: res_str = _T("B is {:.1f}% cheaper!").format(((val_a - val_b) / val_a) * 100).replace('.', dp) if val_a > 0 else _T("B is cheaper!")
        else: res_str = _T("Same price!")
        draw.text(Vector(10, y), _T("Best Deal:"), fg, font_size)
        draw.text(Vector(310 - draw.len(res_str, font_size), y), res_str, hl, font_size)
        
    elif app_state == STATE_CALC_DISCOUNT:
        price, disc = cdata[0], cdata[1]
        saved = price * (disc / 100.0)
        _draw_res("Final Price:", price - saved, y)
        _draw_res("You Save:", saved, y + 30)
        
    elif app_state == STATE_CALC_UNIT_CONVERT:
        val, from_idx, to_idx = cdata[0], int(cdata[1]), int(cdata[2])
        mults = (1.0, 1000.0, 28.3495, 453.592, 1.0, 1000.0, 29.5735, 3785.41)
        res = val * (mults[from_idx] / mults[to_idx])
        draw.text(Vector(10, y), _T("Result:"), fg, font_size)
        num_str = str(int(res)) if res == int(res) else f"{res:.5f}".rstrip('0').rstrip('.')
        res_str = num_str.replace('.', dp) + f" {c_units_uc[to_idx]}"
        draw.text(Vector(310 - draw.len(res_str, font_size), y), res_str, hl, font_size)
        
    elif app_state == STATE_CALC_RUNNING_TOTAL:
        _draw_res("Current Total:", cdata[2], y)
        rem = cdata[0] - cdata[2]
        _draw_res("Remaining:", rem, y + 30, hl if rem >= 0 else 0xF800)
        
    elif app_state == STATE_CALC_BOGO:
        price, buy_q, get_q, disc = cdata[0], cdata[1], cdata[2], cdata[3]
        t_items = buy_q + get_q
        real_p = ((buy_q * price) + (get_q * price * (100.0 - disc) / 100.0)) / t_items if t_items > 0 else 0.0
        _draw_res("Real Price/Ea:", real_p, y)
        
    elif app_state == STATE_CALC_BULK:
        _draw_res("Est. Cost:", cdata[0] * cdata[1], y)
        
    elif app_state == STATE_CALC_TAX:
        _draw_res("Total + Tax:", cdata[0] * (1.0 + cdata[1] / 100.0), y)
        
    elif app_state == STATE_CALC_SPLIT:
        people = cdata[1] if cdata[1] > 0 else 1.0
        _draw_res("Cost per Person:", (cdata[0] * (1.0 + cdata[2] / 100.0)) / people, y)

def _handle_calculators(view_manager):
    """
    Encapsulates all calculator tool logic. Refactored into a single generalized loop
    to significantly reduce repetition, bytecode size, and maintenance overhead.
    """
    global state
    input_manager = view_manager.input_manager
    button = input_manager.button
    
    dirty = state.store_ui_dirty
    if button == -1 and not dirty:
        return
        
    draw = view_manager.draw
    settings = state.settings
    app_state = state.current_view

    c_units = ("", "g", "kg", "oz", "lb", "ml", "L", "fl oz", "gal")
    c_units_uc = ("g", "kg", "oz", "lb", "ml", "L", "fl oz", "gal")

    # 1. Configuration Map
    if app_state == STATE_CALC_PRICE_COMPARE:
        c_rows, c_title, c_kb, c_lbls = 4, "Price Compare", STATE_KEYBOARD_PRICE_COMPARE, ["Price A", "Qty A", "Price B", "Qty B"]
        c_defaults = [0.0, 1.0, 0, 0.0, 1.0, 0]
    elif app_state == STATE_CALC_DISCOUNT:
        c_rows, c_title, c_kb, c_lbls = 2, "Discount Calc", STATE_KEYBOARD_DISCOUNT, ["Original Price", "Discount %"]
        c_defaults = [0.0, 0.0]
    elif app_state == STATE_CALC_UNIT_CONVERT:
        c_rows, c_title, c_kb, c_lbls = 3, "Unit Converter", STATE_KEYBOARD_UNIT_CONVERT, ["Value", "From", "To"]
        c_defaults = [1.0, 0, 1]
    elif app_state == STATE_CALC_RUNNING_TOTAL:
        c_rows, c_title, c_kb, c_lbls = 3, "Running Total", STATE_KEYBOARD_RUNNING_TOTAL, ["Budget", "Add Amount", "Manual Total"]
        c_defaults = [0.0, 0.0, 0.0]
    elif app_state == STATE_CALC_BOGO:
        c_rows, c_title, c_kb, c_lbls = 4, "BOGO Calc", STATE_KEYBOARD_BOGO, ["Item Price", "Buy Qty", "Get Qty", "Discount %"]
        c_defaults = [0.0, 1.0, 1.0, 100.0]
    elif app_state == STATE_CALC_BULK:
        c_rows, c_title, c_kb, c_lbls = 2, "Bulk Estimator", STATE_KEYBOARD_BULK, ["Price/Unit", "Est. Weight"]
        c_defaults = [0.0, 0.0]
    elif app_state == STATE_CALC_TAX:
        c_rows, c_title, c_kb, c_lbls = 2, "Sales Tax", STATE_KEYBOARD_TAX, ["Pre-Tax Price", "Tax %"]
        c_defaults = [0.0, 0.0]
    elif app_state == STATE_CALC_SPLIT:
        c_rows, c_title, c_kb, c_lbls = 3, "Bill Splitter", STATE_KEYBOARD_SPLIT, ["Total Bill", "People", "Tip %"]
        c_defaults = [0.0, 2.0, 0.0]

    # Data Initialization
    cdata = state.calc_data
    if not cdata: cdata = c_defaults
    if app_state == STATE_CALC_PRICE_COMPARE and len(cdata) == 4:
        cdata.insert(2, 0)
        cdata.append(0)
        state.calc_data = cdata

    # 2. Input Handling
    if button != -1:
        dirty = True
        char = input_manager.button_to_char(button)
        if button == BUTTON_UP:
            state.calc_selected = (state.calc_selected - 1) % c_rows
        elif button == BUTTON_DOWN:
            state.calc_selected = (state.calc_selected + 1) % c_rows
        elif button == BUTTON_LEFT:
            if app_state == STATE_CALC_PRICE_COMPARE and state.calc_selected in (1, 3):
                idx = 2 if state.calc_selected == 1 else 5
                cdata[idx] = (cdata[idx] - 1) % len(c_units)
                _smart_deserialize(view_manager.storage, settings, "picoware/settings/grocerycompanion_set.json")
            elif app_state == STATE_CALC_UNIT_CONVERT and state.calc_selected in (1, 2):
                cdata[state.calc_selected] = (cdata[state.calc_selected] - 1) % len(c_units_uc)
                _smart_deserialize(view_manager.storage, settings, "picoware/settings/grocerycompanion_set.json")
            else:
                _switch_menu(view_manager, STATE_MENU_CALCULATORS, _build_calculators_menu)
        elif button == BUTTON_RIGHT:
            if app_state == STATE_CALC_PRICE_COMPARE and state.calc_selected in (1, 3):
                idx = 2 if state.calc_selected == 1 else 5
                cdata[idx] = (cdata[idx] + 1) % len(c_units)
                _smart_deserialize(view_manager.storage, settings, "picoware/settings/grocerycompanion_set.json")
            elif app_state == STATE_CALC_UNIT_CONVERT and state.calc_selected in (1, 2):
                cdata[state.calc_selected] = (cdata[state.calc_selected] + 1) % len(c_units_uc)
                _smart_deserialize(view_manager.storage, settings, "picoware/settings/grocerycompanion_set.json")
        elif button == BUTTON_CENTER or (char != "" and char in "0123456789.,"):
            if app_state == STATE_CALC_UNIT_CONVERT and state.calc_selected != 0:
                pass # Can't type into unit selectors
            else:
                is_char = (char != "" and char in "0123456789.," and button != BUTTON_CENTER)
                input_manager.reset()
                state.current_view = c_kb
                kb = view_manager.keyboard
                kb.reset()
                kb.title = _T(c_lbls[state.calc_selected])
                
                if is_char:
                    kb.response = char
                elif app_state == STATE_CALC_RUNNING_TOTAL and state.calc_selected == 1:
                    kb.response = ""
                else:
                    idx = (0, 1, 3, 4)[state.calc_selected] if app_state == STATE_CALC_PRICE_COMPARE else state.calc_selected
                    kb.response = str(cdata[idx]).replace('.', settings.get("dec_point", "."))
                
                kb.run(force=True)
                kb.run(force=True)
                state.keyboard_just_opened = True
        elif button == BUTTON_BACK:
            _switch_menu(view_manager, STATE_MENU_CALCULATORS, _build_calculators_menu)
        elif button == BUTTON_BACKSPACE:
            state.calc_return_state = app_state
            _trigger_confirm(view_manager, STATE_CONFIRM_CLEAR_CALCULATOR, "clear_calc")
        
        input_manager.reset()

    # 3. UI Drawing
    if not dirty or state.current_view != app_state:
        return
        
    state.store_ui_dirty = False
    _, bg, fg, hl = _get_theme_colors(settings["theme_idx"])
    draw.clear(color=bg)
    
    vec1 = Vector(0, 0)
    vec2 = Vector(320, 26)
    draw.fill_rectangle(vec1, vec2, hl)
    vec1.x = 5; vec1.y = 5
    draw.text(vec1, _T(c_title), bg)
    
    font_size = 1
    dec = settings.get("decimals", 2)
    curr = settings.get("currency", "$")
    dp = settings.get("dec_point", ".")
    fmt_str = "{:." + str(dec) + "f}"
    
    y = 40
    for i in range(c_rows):
        if i == state.calc_selected:
            draw.fill_rectangle(Vector(0, y - 2), Vector(320, 24), hl)
            text_color = bg
        else:
            text_color = fg
        
        draw.text(Vector(10, y), _T(c_lbls[i]) + ":", text_color, font_size)
        
        if app_state == STATE_CALC_PRICE_COMPARE:
            idx_map = (0, 1, 3, 4)
            val = cdata[idx_map[i]]
        else:
            val = cdata[i]
        
        # Formatting Value Logic
        if app_state == STATE_CALC_RUNNING_TOTAL and i == 1:
            val_str = "+ ..."
        elif app_state == STATE_CALC_UNIT_CONVERT and i in (1, 2):
            val_str = f"< {c_units_uc[cdata[i]]} >"
        elif app_state == STATE_CALC_PRICE_COMPARE and i in (1, 3):
            num_str = str(int(val)) if val == int(val) else f"{val:.3f}".rstrip('0').rstrip('.')
            val_str = num_str.replace('.', dp)
            unit_idx = cdata[2] if i == 1 else cdata[5]
            if unit_idx > 0:
                val_str = f"< {val_str} {c_units[unit_idx]} >"
            else:
                val_str = f"< {val_str} >"
        else:
            is_curr = (app_state == STATE_CALC_PRICE_COMPARE and i in (0, 2)) or \
                      (app_state == STATE_CALC_DISCOUNT and i == 0) or \
                      (app_state == STATE_CALC_RUNNING_TOTAL and i in (0, 2)) or \
                      (app_state == STATE_CALC_BOGO and i == 0) or \
                      (app_state == STATE_CALC_BULK and i == 0) or \
                      (app_state == STATE_CALC_TAX and i == 0) or \
                      (app_state == STATE_CALC_SPLIT and i == 0)
            is_perc = (app_state == STATE_CALC_DISCOUNT and i == 1) or \
                      (app_state == STATE_CALC_BOGO and i == 3) or \
                      (app_state == STATE_CALC_TAX and i == 1) or \
                      (app_state == STATE_CALC_SPLIT and i == 2)
            
            if is_curr:
                num_str = ("{:." + str(dec) + "f}").format(val).replace('.', dp)
                val_str = f"{num_str} {curr}"
            elif is_perc:
                num_str = str(int(val)) if val == int(val) else f"{val:.2f}".rstrip('0').rstrip('.')
                val_str = num_str.replace('.', dp) + "%"
            else:
                num_str = str(int(val)) if val == int(val) else f"{val:.5f}".rstrip('0').rstrip('.')
                val_str = num_str.replace('.', dp)
            
        vw = draw.len(val_str, font_size)
        draw.text(Vector(310 - vw, y), val_str, text_color, font_size)
        y += 30
        
    draw.line_custom(Vector(10, y), Vector(310, y), fg)
    y += 10
    
    _draw_calc_results(draw, app_state, cdata, font_size, y, fg, hl, dec, curr, dp, c_units, c_units_uc)

    draw.line_custom(Vector(0, 300), Vector(320, 300), fg)
    draw.text(Vector(5, 304), _T("CALC_FOOTER"), fg)
    draw.swap()

def _handle_help(view_manager):
    global state
    input_manager = view_manager.input_manager
    button = input_manager.button
    
    if button == -1:
        return
        
    draw = view_manager.draw
    settings = state.settings
    textbox = state.textbox
    
    if textbox:
        if button == BUTTON_UP:
            textbox.scroll_up()
        elif button == BUTTON_DOWN:
            textbox.scroll_down()
        elif button in (BUTTON_BACK, BUTTON_LEFT):
            ret_state = state.help_return_state
            state.current_view = ret_state
            state.help_return_state = STATE_MENU_SHOPPING
            state.textbox = None
            
            _, bg, _, _ = _get_theme_colors(settings["theme_idx"])
            draw.clear(color=bg)
            
            if ret_state == STATE_VIEW_LIST:
                state.store_ui_dirty = True
            elif state.menu is not None:
                state.menu.draw()
                draw.swap()
        input_manager.reset()
    del textbox

def _handle_keyboards(view_manager):
    """
    Intercepts keyboard sessions. Retrieves user input when the system keyboard
    closes and applies the values directly to the invoking states.
    """
    global state
    input_manager = view_manager.input_manager
    button = input_manager.button
    settings = state.settings
    app_state = state.current_view

    if state.keyboard_just_opened:
        if button == BUTTON_CENTER:
            input_manager.reset()
        else:
            state.keyboard_just_opened = False
            
    kb = view_manager.keyboard
    if not kb.run(): # User pressed BACK inside the keyboard to cancel
        kb.reset()
        kb.auto_complete_words = []
        if app_state == STATE_KEYBOARD_NEW_LIST:
            _switch_menu(view_manager, STATE_MENU_SHOPPING, _build_shopping_menu)
        elif app_state == STATE_KEYBOARD_ADD_ITEM:
            _switch_menu(view_manager, STATE_MENU_RECENT_ITEMS, _build_recent_items_menu)
        elif app_state in (STATE_KEYBOARD_EDIT_ITEM, STATE_KEYBOARD_DUPLICATE_ITEM):
            list_name = state.active_list_name
            _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name)
            del list_name
        elif app_state == STATE_KEYBOARD_CLONE_LIST:
            list_name = state.active_list_name
            _switch_menu(view_manager, STATE_MENU_SPECIFIC_LIST, _build_specific_list_menu, list_name)
            del list_name
        elif app_state in (STATE_KEYBOARD_RENAME_IN_STORE, STATE_KEYBOARD_ADD_IN_STORE):
            state.current_view = STATE_VIEW_LIST
            state.store_ui_dirty = True
        elif app_state in (STATE_KEYBOARD_PRICE_COMPARE, STATE_KEYBOARD_DISCOUNT, STATE_KEYBOARD_UNIT_CONVERT, STATE_KEYBOARD_RUNNING_TOTAL, STATE_KEYBOARD_BOGO, STATE_KEYBOARD_BULK, STATE_KEYBOARD_TAX, STATE_KEYBOARD_SPLIT):
            state.current_view = app_state - 1
            state.store_ui_dirty = True
    elif kb.is_finished:
        if app_state == STATE_KEYBOARD_NEW_LIST:
            name = kb.response.strip()
            if name:
                name = name.replace("/", "-").replace("\\", "-")
                if name.lower() != "__pantry__":
                    path = f"picoware/grocery/lists/{name}.json"
                    if not view_manager.storage.exists(path):
                        _smart_deserialize(view_manager.storage, [], path)
                        try:
                            if state is not None and "dir_picoware/grocery/lists" in state.file_cache:
                                del state.file_cache["dir_picoware/grocery/lists"]
                        except Exception: pass
                    else:
                        view_manager.alert(_T("List already exists!"), False)
            kb.reset()
            _switch_menu(view_manager, STATE_MENU_SHOPPING, _build_shopping_menu)
            del name
        elif app_state in (STATE_KEYBOARD_ADD_ITEM, STATE_KEYBOARD_ADD_IN_STORE):
            item = kb.response.strip()
            list_name = state.active_list_name
            if item and list_name:
                path = f"picoware/grocery/lists/{list_name}.json"
                try:
                    data = _smart_serialize(view_manager.storage, path)
                    if not isinstance(data, list): data = []
                except Exception:
                    data = []
                    
                found = False
                for i in range(len(data)):
                    i_name = data[i].get("n", "") if isinstance(data[i], dict) else str(data[i])
                    if i_name.lower() == item.lower():
                        if isinstance(data[i], dict):
                            data[i]["q"] = data[i].get("q", 1) + 1
                            data[i]["c"] = False
                        else:
                            data[i] = {"n": i_name, "q": 2, "c": False}
                        found = True
                        break
                if not found:
                    data.append({"n": item, "q": 1, "c": False})
                    
                if app_state == STATE_KEYBOARD_ADD_IN_STORE:
                    data.sort(key=lambda x: x.get("c", False))
                    state.store_data = data
                    
                _smart_deserialize(view_manager.storage, data, path)
                _update_recent_history(view_manager, item)
                if found:
                    view_manager.alert(_T("Item already in list!\nQuantity increased."), False)
            kb.reset()
            if app_state == STATE_KEYBOARD_ADD_ITEM:
                _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name)
            else:
                state.current_view = STATE_VIEW_LIST
                state.store_ui_dirty = True
        elif app_state in (STATE_KEYBOARD_EDIT_ITEM, STATE_KEYBOARD_RENAME_IN_STORE):
            item_name = kb.response.strip()
            list_name = state.active_list_name
            item_idx = state.active_item_idx if app_state == STATE_KEYBOARD_EDIT_ITEM else state.store_idx
            
            if item_name and list_name:
                path = f"picoware/grocery/lists/{list_name}.json"
                try:
                    data = _smart_serialize(view_manager.storage, path)
                    if isinstance(data, list) and item_idx < len(data):
                        if isinstance(data[item_idx], dict):
                            data[item_idx]["n"] = item_name
                        else:
                            data[item_idx] = {"n": item_name, "q": 1, "c": False}
                        _smart_deserialize(view_manager.storage, data, path)
                        _update_recent_history(view_manager, item_name)
                        if app_state == STATE_KEYBOARD_RENAME_IN_STORE:
                            state.store_data = data
                except Exception:
                    pass
                    
            kb.reset()
            if app_state == STATE_KEYBOARD_EDIT_ITEM:
                _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name)
            else:
                state.current_view = STATE_VIEW_LIST
                state.store_ui_dirty = True
        elif app_state == STATE_KEYBOARD_DUPLICATE_ITEM:
            new_name = kb.response.strip()
            list_name = state.active_list_name
            item_idx = state.active_item_idx
            offset = 5 if list_name == "__Pantry__" else 7
            target_idx = item_idx + offset
            
            if new_name and list_name:
                path = f"picoware/grocery/lists/{list_name}.json"
                try:
                    data = _smart_serialize(view_manager.storage, path)
                    if isinstance(data, list) and item_idx < len(data):
                        old_name = data[item_idx].get("n", "") if isinstance(data[item_idx], dict) else str(data[item_idx])
                        if new_name.lower() != old_name.lower():
                            new_item = {"n": new_name, "q": 1, "c": False}
                            data.insert(item_idx + 1, new_item)
                            _smart_deserialize(view_manager.storage, data, path)
                            _update_recent_history(view_manager, new_name)
                            target_idx += 1
                except Exception:
                    pass
                    
            kb.reset()
            _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name, selected=target_idx)
            del new_name, list_name, target_idx
        elif app_state == STATE_KEYBOARD_CLONE_LIST:
            new_name = kb.response.strip()
            list_name = state.active_list_name
            if new_name and list_name and new_name.lower() != list_name.lower() and new_name.lower() != "__pantry__":
                new_name = new_name.replace("/", "-").replace("\\", "-")
                path = f"picoware/grocery/lists/{list_name}.json"
                new_path = f"picoware/grocery/lists/{new_name}.json"
                if not view_manager.storage.exists(new_path):
                    try:
                        data = _smart_serialize(view_manager.storage, path)
                        if isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict): item["c"] = False
                            _smart_deserialize(view_manager.storage, data, new_path)
                            try:
                                if state is not None and "dir_picoware/grocery/lists" in state.file_cache:
                                    del state.file_cache["dir_picoware/grocery/lists"]
                            except Exception: pass
                    except Exception: pass
                else:
                    view_manager.alert(_T("List already exists!"), False)
            kb.reset()
            _switch_menu(view_manager, STATE_MENU_SHOPPING, _build_shopping_menu)
        elif app_state in (STATE_KEYBOARD_PRICE_COMPARE, STATE_KEYBOARD_DISCOUNT, STATE_KEYBOARD_UNIT_CONVERT, STATE_KEYBOARD_RUNNING_TOTAL, STATE_KEYBOARD_BOGO, STATE_KEYBOARD_BULK, STATE_KEYBOARD_TAX, STATE_KEYBOARD_SPLIT):
            try:
                val = float(kb.response.strip().replace(',', '.'))
            except ValueError:
                val = 0.0
            
            if app_state == STATE_KEYBOARD_PRICE_COMPARE:
                idx_map = (0, 1, 3, 4)
                state.calc_data[idx_map[state.calc_selected]] = val
            elif app_state == STATE_KEYBOARD_UNIT_CONVERT:
                state.calc_data[0] = val
            elif app_state == STATE_KEYBOARD_RUNNING_TOTAL and state.calc_selected == 1:
                state.calc_data[2] += val
            else:
                state.calc_data[state.calc_selected] = val
                
            state.current_view = app_state - 1
            
            _smart_deserialize(view_manager.storage, settings, "picoware/settings/grocerycompanion_set.json")
            kb.reset()
            state.store_ui_dirty = True
        kb.auto_complete_words = []
    del kb

def run(view_manager):
    global state
    app_state = state.current_view
    if app_state in (STATE_MENU_SHOPPING, STATE_MENU_SETTINGS, STATE_MENU_CONFIRM_SETTINGS, STATE_MENU_SPECIFIC_LIST, STATE_MENU_EDIT_LIST, STATE_MENU_EDIT_ITEM, STATE_MENU_RECENT_ITEMS, STATE_MENU_CALCULATORS):
        _handle_menus(view_manager)
    elif app_state == STATE_VIEW_LIST:
        _handle_store(view_manager)
    elif app_state in (STATE_CONFIRM_EXIT_STORE, STATE_CONFIRM_DELETE_LIST, STATE_CONFIRM_DELETE_ITEM, STATE_CONFIRM_UNCHECK_ALL, STATE_CONFIRM_CLEAR_CHECKED, STATE_CONFIRM_CLEAR_ALL_ITEMS, STATE_CONFIRM_TRANSFER_PANTRY, STATE_CONFIRM_CLEAR_CALCULATOR):
        _handle_confirmations(view_manager)
    elif app_state in (STATE_CALC_PRICE_COMPARE, STATE_CALC_DISCOUNT, STATE_CALC_UNIT_CONVERT, STATE_CALC_RUNNING_TOTAL, STATE_CALC_BOGO, STATE_CALC_BULK, STATE_CALC_TAX, STATE_CALC_SPLIT):
        _handle_calculators(view_manager)
    elif app_state == STATE_VIEW_HELP:
        _handle_help(view_manager)
    elif app_state in (STATE_KEYBOARD_NEW_LIST, STATE_KEYBOARD_ADD_ITEM, STATE_KEYBOARD_EDIT_ITEM, STATE_KEYBOARD_CLONE_LIST, STATE_KEYBOARD_RENAME_IN_STORE, STATE_KEYBOARD_ADD_IN_STORE, STATE_KEYBOARD_DUPLICATE_ITEM, STATE_KEYBOARD_PRICE_COMPARE, STATE_KEYBOARD_DISCOUNT, STATE_KEYBOARD_UNIT_CONVERT, STATE_KEYBOARD_RUNNING_TOTAL, STATE_KEYBOARD_BOGO, STATE_KEYBOARD_BULK, STATE_KEYBOARD_TAX, STATE_KEYBOARD_SPLIT):
        _handle_keyboards(view_manager)

def stop(view_manager):
    """
    Handles application teardown, deletes custom objects, and clears RAM.
    """
    
    global state
    
    theme_idx = state.settings["theme_idx"] if state else 0
    _, bg, _, _ = _get_theme_colors(theme_idx)
    # Clear the screen before releasing control
    draw = view_manager.draw
    draw.clear(color=bg)
    draw.swap()
    
    # Restore original input mapper
    if state:
        if state.orig_mapper:
            view_manager.input_manager._key_to_button = state.orig_mapper
        if state.menu is not None:
            state.menu.clear()
        state.file_cache.clear()
        state.translations.clear()
            
    view_manager.keyboard.auto_complete_words = []
    view_manager.keyboard.reset()
        
    # Clean up local variables
    del draw, bg
    
    state = None
    
    # Final garbage collection sweep
    from gc import collect
    collect()