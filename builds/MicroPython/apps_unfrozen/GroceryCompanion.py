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

def _init_translations(storage, force=False):
    """
    Initializes default translations if not present on SD card.
    Loads massive strings like HELP_TEXT into storage to save memory later.
    """
    if force or not storage.exists("picoware/grocery/lang.json"):
        trans = {
            "en": {
                "HELP_TEXT": "Grocery Companion Help\n\n[Shopping List]\nCreate, manage and edit grocery lists.\n\n[In Store Mode]\nSelect 'Shopping Mode' on a list.\n- L/R: Change quantity\n- ENTER: Check off item\n- F1: Help Overlay\n- F2: Rename Item\n- F3: Add Item\n- BS: Delete Item\n- F4/F5: Switch Lists\n- BACK: Exit mode\n\n[Pantry]\nManage your existing inventory.\n\n[Settings]\nCustomize theme, language, and font size.\n\n[Calculators]\n- Price Compare: Best deal between 2 items.\n- Discount: Price after % off.\n- Unit Conv: Convert g, kg, oz, lb, L, etc.\n- Running Total: Track spending vs budget.\n- BOGO: True price of Buy 1 Get 1 deals.\n- Bulk: Total cost by weight/qty.\n- Tax: Calculate sales tax.\n- Splitter: Split bill + tip among people.\n\nMade by Slasher006 with the help GeminiAI.",
                "Uncheck All": "Uncheck All",
                "Uncheck All?": "Uncheck All?",
                "Clear Checked": "Clear Checked",
                "Clear Checked?": "Clear Checked?",
                "Clear All Items": "Clear All Items",
                "Clear All Items?": "Clear All Items?",
                "Transfer to Pantry": "Transfer to Pantry",
                "Transfer to Pantry?": "Transfer to Pantry?",
                "All done! Exit?": "All done! Exit?",
                "Reset list?": "Reset list?",
                "Clone List": "Clone List",
                "Duplicate Item": "Duplicate Item",
                "Move Up": "Move Up",
                "Move Down": "Move Down",
                "Sort Alphabetically": "Sort Alphabetically",
                "Clear History": "Clear History",
                "+ Type New Item": "+ Type New Item",
                "Category": "Category",
                "Produce": "Produce",
                "Dairy": "Dairy",
                "Meat": "Meat",
                "Pantry": "Pantry",
                "Frozen": "Frozen",
                "Beverages": "Beverages",
                "Household": "Household",
                "Bakery": "Bakery",
                "Sort by Category": "Sort by Category",
                "None": "None",
                "Recent Items": "Recent Items",
                "Item already in list!\nQuantity increased.": "Item already in list!\nQuantity increased.",
                "List already exists!": "List already exists!",
                "STORE_FOOTER": "[ENT]Chk [F2]Ed [F3]Add [BS]Del",
                "Calculators": "Calculators",
                "Price Compare": "Price Compare",
                "Price A": "Price A",
                "Qty A": "Qty A",
                "Price B": "Price B",
                "Qty B": "Qty B",
                "Best Deal:": "Best Deal:",
                "A is {:.1f}% cheaper!": "A is {:.1f}% cheaper!",
                "B is {:.1f}% cheaper!": "B is {:.1f}% cheaper!",
                "A is cheaper!": "A is cheaper!",
                "B is cheaper!": "B is cheaper!",
                "Same price!": "Same price!",
                "Discount Calc": "Discount Calc",
                "Original Price": "Original Price",
                "Discount %": "Discount %",
                "Final Price:": "Final Price:",
                "You Save:": "You Save:",
                "Currency": "Currency",
                "Decimals": "Decimals",
                "Decimal Point": "Decimal Point",
                "Unit Converter": "Unit Converter",
                "Value": "Value",
                "From": "From",
                "To": "To",
                "Result:": "Result:",
                "Running Total": "Running Total",
                "BOGO Calc": "BOGO Calc",
                "Bulk Estimator": "Bulk Estimator",
                "Sales Tax": "Sales Tax",
                "Bill Splitter": "Bill Splitter",
                "Budget": "Budget",
                "Add Amount": "Add Amount",
                "Manual Total": "Manual Total",
                "Current Total:": "Current Total:",
                "Remaining:": "Remaining:",
                "Item Price": "Item Price",
                "Buy Qty": "Buy Qty",
                "Get Qty": "Get Qty",
                "Real Price/Ea:": "Real Price/Ea:",
                "Price/Unit": "Price/Unit",
                "Est. Weight": "Est. Weight",
                "Est. Cost:": "Est. Cost:",
                "Pre-Tax Price": "Pre-Tax Price",
                "Tax %": "Tax %",
                "Total + Tax:": "Total + Tax:",
                "Total Bill": "Total Bill",
                "People": "People",
                "Tip %": "Tip %",
                "Cost per Person:": "Cost per Person:",
                "Update Translations": "Update Translations",
                "Language File Updated!": "Language File Updated!"
            },
            "de": {
                "Grocery Companion": "Einkaufsbegleiter",
                "Shopping List": "Einkaufsliste",
                "Shopping Lists": "Einkaufslisten",
                "Pantry": "Speisekammer",
                "Settings": "Einstellungen",
                "Exit App": "App beenden",
                "Shopping Mode": "Einkaufsmodus",
                "+ Add Item": "+ Artikel hinzufuegen",
                "Edit List": "Liste bearbeiten",
                "Rename Item": "Artikel umbenennen",
                "Delete Item": "Artikel loeschen",
                "Delete List": "Liste loeschen",
                "Delete List?": "Liste loeschen?",
                "Delete Item?": "Artikel loeschen?",
                "+ Create New List": "+ Neue Liste erstellen",
                "Enter List Name": "Listenname eingeben",
                "Enter Item": "Artikel eingeben",
                "Back": "Zurueck",
                "Theme": "Design",
                "Language": "Sprache",
                "English": "Englisch",
                "German": "Deutsch",
                "Font Size": "Schriftgroesse",
                "Small": "Klein",
                "Medium": "Mittel",
                "Large": "Gross",
                "STORE_FOOTER": "[ENT]Chk [F2]Ed [F3]Add [BS]Del",
                "(Empty)": "(Leer)",
                "Exit store mode?": "Einkaufsmodus beenden?",
                "Yes": "Ja",
                "No": "Nein",
                "Uncheck All": "Alle abwaehlen",
                "Uncheck All?": "Alle abwaehlen?",
                "Clear Checked": "Abgehakte loeschen",
                "Clear Checked?": "Abgehakte loeschen?",
                "Clear All Items": "Alle Artikel loeschen",
                "Clear All Items?": "Alle Artikel loeschen?",
                "Transfer to Pantry": "In Speisekammer",
                "Transfer to Pantry?": "In Speisekammer?",
                "All done! Exit?": "Alles erledigt! Beenden?",
                "Reset list?": "Liste zuruecksetzen?",
                "Clone List": "Liste klonen",
                "Duplicate Item": "Artikel duplizieren",
                "Move Up": "Nach oben",
                "Move Down": "Nach unten",
                "Sort Alphabetically": "Alphabetisch sortieren",
                "Clear History": "Verlauf loeschen",
                "+ Type New Item": "+ Neu eingeben",
                "Category": "Kategorie",
                "Produce": "Obst/Gemuese",
                "Dairy": "Milchprodukte",
                "Meat": "Fleisch",
                "Pantry": "Vorrat",
                "Frozen": "Tiefkuehl",
                "Beverages": "Getraenke",
                "Household": "Haushalt",
                "Bakery": "Backwaren",
                "Sort by Category": "Nach Kategorie",
                "None": "Keine",
                "Recent Items": "Zuletzt verwendet",
                "Item already in list!\nQuantity increased.": "Bereits in Liste!\nMenge erhoeht.",
                "List already exists!": "Liste existiert bereits!",
                "Help": "Hilfe",
                "HELP_TEXT": "Einkaufsbegleiter Hilfe\n\n[Einkaufsliste]\nEinkaufslisten erstellen und bearbeiten.\n\n[Einkaufsmodus]\n'Einkaufsmodus' in einer Liste waehlen.\n- L/R: Menge aendern\n- ENTER: Artikel abhaken\n- F1: Hilfe Overlay\n- F2: Artikel umbenennen\n- F3: Artikel hinzufuegen\n- BS: Artikel loeschen\n- F4/F5: Liste wechseln\n- ZURUECK: Modus beenden\n\n[Speisekammer]\nVerwalte dein vorhandenes Inventar.\n\n[Einstellungen]\nDesign, Sprache und Schriftgroesse anpassen.\n\n[Rechner]\n- Preisvergl.: Finde das beste Angebot.\n- Rabatt: Preis nach % Abzug.\n- Einheiten: g, kg, oz, lb, L usw.\n- Zwischensumme: Budget im Blick behalten.\n- BOGO: Echter Preis bei Kauf 1, Bekomme 1.\n- Mengenrechner: Kosten nach Gewicht/Menge.\n- Steuer: Mehrwertsteuer berechnen.\n- Teiler: Rechnung + Trinkgeld aufteilen.\n\nMade by Slasher006 with the help GeminiAI.",
                "Calculators": "Rechner",
                "Price Compare": "Preisvergleich",
                "Price A": "Preis A",
                "Qty A": "Menge A",
                "Price B": "Preis B",
                "Qty B": "Menge B",
                "Best Deal:": "Bestes Angebot:",
                "A is {:.1f}% cheaper!": "A ist {:.1f}% billiger!",
                "B is {:.1f}% cheaper!": "B ist {:.1f}% billiger!",
                "A is cheaper!": "A ist billiger!",
                "B is cheaper!": "B ist billiger!",
                "Same price!": "Gleicher Preis!",
                "Discount Calc": "Rabattrechner",
                "Original Price": "Originalpreis",
                "Discount %": "Rabatt %",
                "Final Price:": "Endpreis:",
                "You Save:": "Du sparst:",
                "Currency": "Waehrung",
                "Decimals": "Nachkommastellen",
                "Decimal Point": "Dezimalzeichen",
                "Unit Converter": "Einheitenrechner",
                "Value": "Wert",
                "From": "Von",
                "To": "Nach",
                "Result:": "Ergebnis:",
                "Running Total": "Zwischensumme",
                "BOGO Calc": "BOGO Rechner",
                "Bulk Estimator": "Mengenrechner",
                "Sales Tax": "Mehrwertsteuer",
                "Bill Splitter": "Rechnungsteiler",
                "Budget": "Budget",
                "Add Amount": "Betrag hinzufuegen",
                "Manual Total": "Summe (Manuell)",
                "Current Total:": "Aktuelle Summe:",
                "Remaining:": "Verbleibend:",
                "Item Price": "Artikelpreis",
                "Buy Qty": "Kaufmenge",
                "Get Qty": "Gratismenge",
                "Real Price/Ea:": "Echter Stk-Preis:",
                "Price/Unit": "Preis/Einheit",
                "Est. Weight": "Gesch. Gewicht",
                "Est. Cost:": "Gesch. Kosten:",
                "Pre-Tax Price": "Preis (Netto)",
                "Tax %": "Steuer %",
                "Total + Tax:": "Gesamt + Steuer:",
                "Total Bill": "Rechnungsbetrag",
                "People": "Personen",
                "Tip %": "Trinkgeld %",
                "Cost per Person:": "Kosten pro Person:",
                "Update Translations": "Sprachdatei aktualisieren",
                "Language File Updated!": "Sprachdatei aktualisiert!"
            }
        }
        try:
            storage.deserialize(trans, "picoware/grocery/lang.json")
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

_CATEGORIES = ["None", "Produce", "Dairy", "Meat", "Pantry", "Frozen", "Beverages", "Household", "Bakery"]

def _T(text, lang):
    """Translate given text using loaded localization dictionary."""
    global _CURRENT_VM
    if _CURRENT_VM is not None and hasattr(_CURRENT_VM, "grocery_translations"):
        if text in _CURRENT_VM.grocery_translations:
            return _CURRENT_VM.grocery_translations[text]
    return text

def _update_recent_history(view_manager, item_name):
    """Adds a newly typed item into the global recent history list, avoiding duplicates."""
    if not item_name: return
    path = "picoware/grocery/history.json"
    try:
        history = view_manager.storage.serialize(path)
        if not isinstance(history, list): history = []
    except Exception:
        history = []
    
    history = [x for x in history if str(x).lower() != item_name.lower()]
    
    history.insert(0, item_name)
    if len(history) > 20: history = history[:20]
        
    view_manager.storage.deserialize(history, path)

def _get_theme_colors(theme_idx):
    """Returns the RGB565 UI colors based on the selected theme index."""
    global _CURRENT_VM
    idx = theme_idx % len(_THEMES)
    if idx == 0 and _CURRENT_VM is not None:
        return ("System", _CURRENT_VM.background_color, _CURRENT_VM.foreground_color, _CURRENT_VM.selected_color)
    return _THEMES[idx]

def _blend_565(c1, c2):
    """Blends two 16-bit RGB565 colors. Useful for inactive checked item text."""
    r = (((c1 >> 11) & 0x1F) + ((c2 >> 11) & 0x1F)) >> 1
    g = (((c1 >> 5) & 0x3F) + ((c2 >> 5) & 0x3F)) >> 1
    b = ((c1 & 0x1F) + (c2 & 0x1F)) >> 1
    return (r << 11) | (g << 5) | b

def _build_shopping_menu(view_manager):
    """Constructs the root menu, displaying all saved shopping lists."""
    from picoware.gui.menu import Menu
    settings = view_manager.grocery_settings
    lang = settings.get("lang", "en")
    
    _, bg, fg, hl = _get_theme_colors(settings.get("theme_idx", 0))
    draw = view_manager.draw
    app_menu = Menu(
        draw, _T("Grocery Companion", lang), 0, 320,
        fg, bg, hl, fg
    )
    app_menu.add_item(_T("+ Create New List", lang))
    
    try:
        items = view_manager.storage.read_directory("picoware/grocery/lists")
        lists = []
        for item in items:
            fname = item.get("filename", "")
            if not item.get("is_directory", False) and fname.endswith(".json") and fname != "__Pantry__.json":
                lists.append(fname[:-5])
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
    app_menu.set_selected(0)
    return app_menu

def _build_specific_list_menu(view_manager, list_name):
    from picoware.gui.menu import Menu
    settings = view_manager.grocery_settings
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
        data = view_manager.storage.serialize(path)
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
    settings = view_manager.grocery_settings
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
        data = view_manager.storage.serialize(path)
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
    settings = view_manager.grocery_settings
    lang = settings.get("lang", "en")
    
    _, bg, fg, hl = _get_theme_colors(settings.get("theme_idx", 0))
    draw = view_manager.draw
    app_menu = Menu(
        draw, item_name, 0, 320,
        fg, bg, hl, fg
    )
    
    cat_idx = 0
    list_name = getattr(view_manager, "active_list_name", "")
    item_idx = getattr(view_manager, "active_item_idx", 0)
    try:
        data = view_manager.storage.serialize(f"picoware/grocery/lists/{list_name}.json")
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
    settings = view_manager.grocery_settings
    lang = settings.get("lang", "en")
    
    _, bg, fg, hl = _get_theme_colors(settings.get("theme_idx", 0))
    draw = view_manager.draw
    app_menu = Menu(
        draw, _T("Recent Items", lang), 0, 320,
        fg, bg, hl, fg
    )
    app_menu.add_item(_T("+ Type New Item", lang))
    
    try:
        history = view_manager.storage.serialize("picoware/grocery/history.json")
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
    settings = view_manager.grocery_settings
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
    app_menu.add_item("---------------")
    app_menu.add_item(_T("Back", lang))
    app_menu.set_selected(0)
    return app_menu

def _build_calculators_menu(view_manager):
    from picoware.gui.menu import Menu
    settings = view_manager.grocery_settings
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
    settings = view_manager.grocery_settings
    view_manager.custom_app_state = next_state
    _, bg, _, _ = _get_theme_colors(settings.get("theme_idx", 0))
    view_manager.draw.clear(color=bg)
    view_manager.custom_app_menu = menu_builder(view_manager, *args)
    if "selected" in kwargs:
        view_manager.custom_app_menu.set_selected(kwargs["selected"])
    view_manager.custom_app_menu.draw()
    view_manager.draw.swap()

def start(view_manager):
    """
    Initializes the Menu component and attaches it to the view manager.
    """
    
    global _CURRENT_VM
    _CURRENT_VM = view_manager
    
    # --- Monkey patch input manager to capture F-keys natively for Autocomplete ---
    if not hasattr(view_manager, 'grocery_orig_mapper'):
        view_manager.grocery_orig_mapper = view_manager.input_manager._key_to_button
        view_manager.input_manager._key_to_button = lambda k: k if 0x81 <= k <= 0x90 else view_manager.grocery_orig_mapper(k)

    # Globals to Locals
    settings_file = "picoware/settings/grocerycompanion_set.json"
    view_manager.grocery_settings = {
        "theme_idx": 0,
        "lang": "en",
        "font_size": 1,
        "currency": "$",
        "decimals": 2,
        "dec_point": "."
    }
    view_manager.storage.mkdir("picoware/settings")
    view_manager.storage.mkdir("picoware/grocery")
    view_manager.storage.mkdir("picoware/grocery/lists")
    _init_translations(view_manager.storage)
    if view_manager.storage.exists(settings_file):
        loaded = view_manager.storage.serialize(settings_file)
        if "theme_idx" in loaded:
            view_manager.grocery_settings["theme_idx"] = loaded["theme_idx"]
        if "lang" in loaded:
            view_manager.grocery_settings["lang"] = loaded["lang"]
        if "font_size" in loaded:
            view_manager.grocery_settings["font_size"] = loaded["font_size"]
        if "currency" in loaded:
            view_manager.grocery_settings["currency"] = loaded["currency"]
        if "decimals" in loaded:
            view_manager.grocery_settings["decimals"] = loaded["decimals"]
        if "dec_point" in loaded:
            view_manager.grocery_settings["dec_point"] = loaded["dec_point"]
    
    try:
        all_trans = view_manager.storage.serialize("picoware/grocery/lang.json")
        view_manager.grocery_translations = all_trans.get(view_manager.grocery_settings.get("lang", "en"), {})
    except Exception:
        view_manager.grocery_translations = {}

    theme_idx = view_manager.grocery_settings["theme_idx"]
    _, bg, _, _ = _get_theme_colors(theme_idx)
    draw = view_manager.draw
    draw.clear(color=bg)
    
    # Initialize the main menu
    app_menu = _build_shopping_menu(view_manager)
    
    # Draw the initial menu state
    app_menu.draw()
    draw.swap()
    
    # Attach to view_manager to persist state WITHOUT global variables
    view_manager.custom_app_menu = app_menu  # Use local variable
    # Strings to Integer
    view_manager.custom_app_state = STATE_MENU_SHOPPING
    
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
    global _CURRENT_VM
    _CURRENT_VM = view_manager
    input_manager = view_manager.input_manager
    button = input_manager.button
    draw = view_manager.draw
    settings = view_manager.grocery_settings
    settings_file = "picoware/settings/grocerycompanion_set.json"
    lang = settings.get("lang", "en")
    state = getattr(view_manager, 'custom_app_state', STATE_MENU_SHOPPING)
    
    if state in (STATE_MENU_SHOPPING, STATE_MENU_SETTINGS, STATE_MENU_SPECIFIC_LIST, STATE_MENU_EDIT_LIST, STATE_MENU_EDIT_ITEM, STATE_MENU_RECENT_ITEMS, STATE_MENU_CALCULATORS):
        current_menu = view_manager.custom_app_menu
        
        if button != -1: # BUTTON_NONE is -1
            # Process navigation and wrap-around logic
            if button == BUTTON_UP:
                if current_menu.selected_index > 0:
                    current_menu.scroll_up()
                elif current_menu.item_count > 0:
                    current_menu.set_selected(current_menu.item_count - 1)
                
                while current_menu.current_item == "---------------":
                    if current_menu.selected_index > 0:
                        current_menu.scroll_up()
                    elif current_menu.item_count > 0:
                        current_menu.set_selected(current_menu.item_count - 1)
                current_menu.draw()
                draw.swap()
                
            elif button == BUTTON_DOWN:
                if current_menu.selected_index < current_menu.item_count - 1:
                    current_menu.scroll_down()
                elif current_menu.item_count > 0:
                    current_menu.set_selected(0)
                
                while current_menu.current_item == "---------------":
                    if current_menu.selected_index < current_menu.item_count - 1:
                        current_menu.scroll_down()
                    elif current_menu.item_count > 0:
                        current_menu.set_selected(0)
                current_menu.draw()
                draw.swap()
                
            elif button in (BUTTON_LEFT, BUTTON_RIGHT):
                # Handles Left/Right toggle values in settings and quantity editors
                selected_idx = current_menu.selected_index
                if state == STATE_MENU_SETTINGS:
                    if selected_idx == 0: # Theme
                        themes_count = len(_THEMES)
                        if button == BUTTON_RIGHT:
                            settings["theme_idx"] = (settings["theme_idx"] + 1) % themes_count
                        else:
                            settings["theme_idx"] = (settings["theme_idx"] - 1) % themes_count
                        view_manager.storage.deserialize(settings, settings_file)
                        _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu, selected=0)
                    elif selected_idx == 1: # Language
                        settings["lang"] = "de" if settings.get("lang", "en") == "en" else "en"
                        view_manager.storage.deserialize(settings, settings_file)
                        try:
                            all_trans = view_manager.storage.serialize("picoware/grocery/lang.json")
                            view_manager.grocery_translations = all_trans.get(settings["lang"], {})
                        except Exception:
                            pass
                        _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu, selected=1)
                    elif selected_idx == 2: # Font Size
                        settings["font_size"] = (settings.get("font_size", 1) + (1 if button == BUTTON_RIGHT else -1)) % 3
                        view_manager.storage.deserialize(settings, settings_file)
                        _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu, selected=2)
                    elif selected_idx == 3: # Currency
                        settings["currency"] = "EUR" if settings.get("currency", "$") == "$" else "$"
                        view_manager.storage.deserialize(settings, settings_file)
                        _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu, selected=3)
                    elif selected_idx == 4: # Decimals
                        settings["decimals"] = (settings.get("decimals", 2) + (1 if button == BUTTON_RIGHT else -1)) % 5
                        view_manager.storage.deserialize(settings, settings_file)
                        _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu, selected=4)
                    elif selected_idx == 5: # Decimal Point
                        settings["dec_point"] = "," if settings.get("dec_point", ".") == "." else "."
                        view_manager.storage.deserialize(settings, settings_file)
                        _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu, selected=5)
                elif state == STATE_MENU_EDIT_LIST:
                    list_name = getattr(view_manager, "active_list_name", "")
                    path = f"picoware/grocery/lists/{list_name}.json"
                    try:
                        data = view_manager.storage.serialize(path)
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
                                view_manager.storage.deserialize(data, path)
                                
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
                elif state == STATE_MENU_EDIT_ITEM:
                    if selected_idx == 1: # Category
                        list_name = getattr(view_manager, "active_list_name", "")
                        item_idx = getattr(view_manager, "active_item_idx", 0)
                        path = f"picoware/grocery/lists/{list_name}.json"
                        try:
                            data = view_manager.storage.serialize(path)
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
                                view_manager.storage.deserialize(data, path)
                                _switch_menu(view_manager, STATE_MENU_EDIT_ITEM, _build_edit_item_menu, getattr(view_manager, "active_item_name", ""), selected=1)
                        except Exception: pass
            elif button == BUTTON_CENTER:
                # Processes active row selection actions
                input_manager.reset()
                selected_idx = current_menu.selected_index
                
                if state == STATE_MENU_SHOPPING:
                    selected_item_text = current_menu.current_item
                    
                    if selected_idx == 0: # Create New List
                        view_manager.custom_app_state = STATE_KEYBOARD_NEW_LIST
                        kb = view_manager.keyboard
                        kb.reset()
                        kb.auto_complete_words = []
                        kb.title = _T("Enter List Name", lang)
                        kb.response = ""
                        kb.run(force=True)
                        kb.run(force=True)
                        view_manager.keyboard_just_opened = True
                        del kb
                    elif selected_item_text == "---------------":
                        pass # Fallback safety catch
                    elif selected_item_text == _T("Pantry", lang):
                        view_manager.active_list_name = "__Pantry__"
                        _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, "__Pantry__")
                    elif selected_item_text == _T("Calculators", lang):
                        _switch_menu(view_manager, STATE_MENU_CALCULATORS, _build_calculators_menu)
                    elif selected_item_text == _T("Settings", lang):
                        _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu)
                    elif selected_item_text == _T("Help", lang):
                        view_manager.help_return_state = state
                        view_manager.custom_app_state = STATE_VIEW_HELP
                        _, bg, fg, _ = _get_theme_colors(settings["theme_idx"])
                        draw.clear(color=bg)
                        view_manager.custom_app_textbox = TextBox(draw, 0, 320, fg, bg)
                        view_manager.custom_app_textbox.set_text(_T("HELP_TEXT", lang))
                    elif selected_item_text == _T("Exit App", lang):
                        input_manager.reset()
                        view_manager.back()
                    else: # Specific List selected
                        list_name = selected_item_text
                        view_manager.active_list_name = list_name
                        view_manager.custom_app_state = STATE_MENU_SPECIFIC_LIST
                        _, bg, _, _ = _get_theme_colors(settings["theme_idx"])
                        draw.clear(color=bg)
                        view_manager.custom_app_menu = _build_specific_list_menu(view_manager, list_name)
                        view_manager.custom_app_menu.draw()
                        draw.swap()
                        del list_name
                        
                    del selected_item_text
                    
                elif state == STATE_MENU_SPECIFIC_LIST:
                    list_name = getattr(view_manager, "active_list_name", "")
                    
                    if selected_idx == 0: # Shopping Mode
                        view_manager.custom_app_state = STATE_VIEW_LIST
                        path = f"picoware/grocery/lists/{list_name}.json"
                        try:
                            data = view_manager.storage.serialize(path)
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
                        
                        view_manager.store_data = data
                        view_manager.store_idx = 0
                        view_manager.store_scroll = 0
                        view_manager.store_ui_dirty = True
                        del path
                    elif selected_idx == 1: # Edit List
                        _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name)
                    elif selected_idx == 2: # Clone List
                        view_manager.custom_app_state = STATE_KEYBOARD_CLONE_LIST
                        kb = view_manager.keyboard
                        kb.reset()
                        kb.auto_complete_words = []
                        kb.title = _T("Enter List Name", lang)
                        kb.response = ""
                        kb.run(force=True)
                        kb.run(force=True)
                        view_manager.keyboard_just_opened = True
                        del kb
                    elif selected_idx == 3: # Uncheck All
                        view_manager.custom_app_state = STATE_CONFIRM_UNCHECK_ALL
                        view_manager.store_exit_choice_state = 1
                        view_manager.store_ui_dirty = True
                    elif selected_idx == 4: # Clear Checked
                        view_manager.custom_app_state = STATE_CONFIRM_CLEAR_CHECKED
                        view_manager.store_exit_choice_state = 1
                        view_manager.store_ui_dirty = True
                        view_manager.clear_checked_return_state = STATE_MENU_SPECIFIC_LIST
                    elif selected_idx == 5: # Transfer to Pantry
                        view_manager.custom_app_state = STATE_CONFIRM_TRANSFER_PANTRY
                        view_manager.store_exit_choice_state = 1
                        view_manager.store_ui_dirty = True
                        view_manager.transfer_pantry_return_state = STATE_MENU_SPECIFIC_LIST
                    elif selected_idx == 6: # Delete List
                        view_manager.custom_app_state = STATE_CONFIRM_DELETE_LIST
                        view_manager.store_exit_choice_state = 1
                        view_manager.store_ui_dirty = True
                    elif selected_idx == 7: # Separator
                        pass
                    elif selected_idx == 8: # Back
                        _switch_menu(view_manager, STATE_MENU_SHOPPING, _build_shopping_menu)
                        
                    del list_name
                    
                elif state == STATE_MENU_EDIT_LIST:
                    list_name = getattr(view_manager, "active_list_name", "")
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
                        view_manager.custom_app_state = STATE_CONFIRM_CLEAR_ALL_ITEMS
                        view_manager.store_exit_choice_state = 1
                        view_manager.store_ui_dirty = True
                    elif selected_item_text == _T("Sort Alphabetically", lang):
                        path = f"picoware/grocery/lists/{list_name}.json"
                        try:
                            data = view_manager.storage.serialize(path)
                            if isinstance(data, list):
                                data.sort(key=lambda x: (x.get("c", False) if isinstance(x, dict) else False, (x.get("n", "") if isinstance(x, dict) else str(x)).lower()))
                                view_manager.storage.deserialize(data, path)
                        except Exception: pass
                        _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name, selected=2)
                    elif selected_item_text.startswith(_T("Clear Checked", lang)):
                        view_manager.custom_app_state = STATE_CONFIRM_CLEAR_CHECKED
                        view_manager.store_exit_choice_state = 1
                        view_manager.store_ui_dirty = True
                        view_manager.clear_checked_return_state = STATE_MENU_EDIT_LIST
                    elif selected_item_text.startswith(_T("Transfer to Pantry", lang)):
                        view_manager.custom_app_state = STATE_CONFIRM_TRANSFER_PANTRY
                        view_manager.store_exit_choice_state = 1
                        view_manager.store_ui_dirty = True
                        view_manager.transfer_pantry_return_state = STATE_MENU_EDIT_LIST
                    elif selected_item_text == _T("Sort by Category", lang):
                        path = f"picoware/grocery/lists/{list_name}.json"
                        try:
                            data = view_manager.storage.serialize(path)
                            if isinstance(data, list):
                                for i in range(len(data)):
                                    if not isinstance(data[i], dict):
                                        data[i] = {"n": str(data[i]), "q": 1, "c": False, "cat": 0}
                                data.sort(key=lambda x: (x.get("c", False), x.get("cat", 0), x.get("n", "").lower()))
                                view_manager.storage.deserialize(data, path)
                        except Exception: pass
                        _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name, selected=3)
                    else:
                        offset = 5 if list_name == "__Pantry__" else 7
                        view_manager.active_item_idx = selected_idx - offset
                        view_manager.active_item_name = selected_item_text
                        _switch_menu(view_manager, STATE_MENU_EDIT_ITEM, _build_edit_item_menu, selected_item_text)
                        
                elif state == STATE_MENU_EDIT_ITEM:
                    list_name = getattr(view_manager, "active_list_name", "")
                    item_idx = getattr(view_manager, "active_item_idx", 0)
                    
                    if selected_idx == 0: # Rename Item
                        view_manager.custom_app_state = STATE_KEYBOARD_EDIT_ITEM
                        kb = view_manager.keyboard
                        kb.reset()
                        kb.title = _T("Rename Item", lang)
                        
                        path = f"picoware/grocery/lists/{list_name}.json"
                        try:
                            data = view_manager.storage.serialize(path)
                            if isinstance(data, list) and item_idx < len(data):
                                item = data[item_idx]
                                kb.response = item.get("n", "") if isinstance(item, dict) else str(item)
                            else:
                                kb.response = ""
                        except Exception:
                            kb.response = ""
                            
                        try:
                            hist = view_manager.storage.serialize("picoware/grocery/history.json")
                            if isinstance(hist, list):
                                kb.auto_complete_words = [str(x) for x in hist]
                        except Exception:
                            kb.auto_complete_words = []
                            
                        kb.run(force=True)
                        kb.run(force=True)
                        view_manager.keyboard_just_opened = True
                        del kb
                    elif selected_idx == 1: # Category
                        pass
                    elif selected_idx == 2: # Duplicate Item
                        view_manager.custom_app_state = STATE_KEYBOARD_DUPLICATE_ITEM
                        kb = view_manager.keyboard
                        kb.reset()
                        kb.title = _T("Duplicate Item", lang)
                        
                        path = f"picoware/grocery/lists/{list_name}.json"
                        try:
                            data = view_manager.storage.serialize(path)
                            if isinstance(data, list) and item_idx < len(data):
                                item = data[item_idx]
                                kb.response = item.get("n", "") if isinstance(item, dict) else str(item)
                            else:
                                kb.response = ""
                        except Exception:
                            kb.response = ""
                            
                        try:
                            hist = view_manager.storage.serialize("picoware/grocery/history.json")
                            if isinstance(hist, list):
                                kb.auto_complete_words = [str(x) for x in hist]
                        except Exception:
                            kb.auto_complete_words = []
                            
                        kb.run(force=True)
                        kb.run(force=True)
                        view_manager.keyboard_just_opened = True
                        del kb
                    elif selected_idx == 3: # Delete Item
                        view_manager.custom_app_state = STATE_CONFIRM_DELETE_ITEM
                        view_manager.store_exit_choice_state = 1
                        view_manager.store_ui_dirty = True
                    elif selected_idx == 4: # Move Up
                        path = f"picoware/grocery/lists/{list_name}.json"
                        try:
                            data = view_manager.storage.serialize(path)
                            if isinstance(data, list) and 0 < item_idx < len(data):
                                data[item_idx], data[item_idx - 1] = data[item_idx - 1], data[item_idx]
                                view_manager.storage.deserialize(data, path)
                                view_manager.active_item_idx -= 1
                        except Exception:
                            pass
                        offset = 5 if list_name == "__Pantry__" else 7
                        _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name, selected=(view_manager.active_item_idx + offset))
                    elif selected_idx == 5: # Move Down
                        path = f"picoware/grocery/lists/{list_name}.json"
                        try:
                            data = view_manager.storage.serialize(path)
                            if isinstance(data, list) and item_idx < len(data) - 1:
                                data[item_idx], data[item_idx + 1] = data[item_idx + 1], data[item_idx]
                                view_manager.storage.deserialize(data, path)
                                view_manager.active_item_idx += 1
                        except Exception:
                            pass
                        view_manager.custom_app_state = STATE_MENU_EDIT_LIST
                        _, bg, _, _ = _get_theme_colors(settings["theme_idx"])
                        draw.clear(color=bg)
                        view_manager.custom_app_menu = _build_edit_list_menu(view_manager, list_name)
                        offset = 5 if list_name == "__Pantry__" else 7
                        view_manager.custom_app_menu.set_selected(view_manager.active_item_idx + offset)
                        view_manager.custom_app_menu.draw()
                        draw.swap()
                    elif selected_idx == 6: # Separator
                        pass
                    elif selected_idx == 7: # Back
                        view_manager.custom_app_state = STATE_MENU_EDIT_LIST
                        _, bg, _, _ = _get_theme_colors(settings["theme_idx"])
                        draw.clear(color=bg)
                        view_manager.custom_app_menu = _build_edit_list_menu(view_manager, list_name)
                        offset = 5 if list_name == "__Pantry__" else 7
                        view_manager.custom_app_menu.set_selected(view_manager.active_item_idx + offset)
                        view_manager.custom_app_menu.draw()
                        draw.swap()
                        view_manager.custom_app_menu = _build_edit_list_menu(view_manager, list_name)
                        view_manager.custom_app_menu.draw()
                        draw.swap()
                        
                elif state == STATE_MENU_RECENT_ITEMS:
                    selected_item_text = current_menu.current_item
                    if selected_item_text == "---------------":
                        pass
                    elif selected_item_text == _T("Back", lang):
                        list_name = getattr(view_manager, "active_list_name", "")
                        _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name)
                    elif selected_item_text == _T("+ Type New Item", lang):
                        view_manager.custom_app_state = STATE_KEYBOARD_ADD_ITEM
                        kb = view_manager.keyboard
                        kb.reset()
                        kb.title = _T("Enter Item", lang)
                        kb.response = ""
                        
                        try:
                            hist = view_manager.storage.serialize("picoware/grocery/history.json")
                            if isinstance(hist, list):
                                kb.auto_complete_words = [str(x) for x in hist]
                        except Exception:
                            kb.auto_complete_words = []
                            
                        kb.run(force=True)
                        kb.run(force=True)
                        view_manager.keyboard_just_opened = True
                        del kb
                    elif selected_item_text == _T("Clear History", lang):
                        try:
                            view_manager.storage.deserialize([], "picoware/grocery/history.json")
                        except Exception:
                            pass
                        _switch_menu(view_manager, STATE_MENU_RECENT_ITEMS, _build_recent_items_menu)
                    else:
                        list_name = getattr(view_manager, "active_list_name", "")
                        if list_name:
                            path = f"picoware/grocery/lists/{list_name}.json"
                            try: data = view_manager.storage.serialize(path)
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
                                
                            view_manager.storage.deserialize(data, path)
                            _update_recent_history(view_manager, selected_item_text)
                            if found:
                                view_manager.alert(_T("Item already in list!\nQuantity increased.", lang), False)
                            
                        _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name)

                elif state == STATE_MENU_CALCULATORS:
                    selected_item_text = current_menu.current_item
                    if selected_item_text == _T("Price Compare", lang):
                        view_manager.custom_app_state = STATE_CALC_PRICE_COMPARE
                        view_manager.calc_data = [0.0, 1.0, 0, 0.0, 1.0, 0] # Price A, Qty A, Unit A, Price B, Qty B, Unit B
                        view_manager.calc_selected = 0
                        view_manager.store_ui_dirty = True
                    elif selected_item_text == _T("Discount Calc", lang):
                        view_manager.custom_app_state = STATE_CALC_DISCOUNT
                        view_manager.calc_data = [0.0, 0.0] # Price, Discount %
                        view_manager.calc_selected = 0
                        view_manager.store_ui_dirty = True
                    elif selected_item_text == _T("Unit Converter", lang):
                        view_manager.custom_app_state = STATE_CALC_UNIT_CONVERT
                        view_manager.calc_data = [1.0, 0, 1] # Value, From Idx, To Idx
                        view_manager.calc_selected = 0
                        view_manager.store_ui_dirty = True
                    elif selected_item_text == _T("Running Total", lang):
                        view_manager.custom_app_state = STATE_CALC_RUNNING_TOTAL
                        view_manager.calc_data = [0.0, 0.0, 0.0]
                        view_manager.calc_selected = 0
                        view_manager.store_ui_dirty = True
                    elif selected_item_text == _T("BOGO Calc", lang):
                        view_manager.custom_app_state = STATE_CALC_BOGO
                        view_manager.calc_data = [0.0, 1.0, 1.0, 100.0]
                        view_manager.calc_selected = 0
                        view_manager.store_ui_dirty = True
                    elif selected_item_text == _T("Bulk Estimator", lang):
                        view_manager.custom_app_state = STATE_CALC_BULK
                        view_manager.calc_data = [0.0, 0.0]
                        view_manager.calc_selected = 0
                        view_manager.store_ui_dirty = True
                    elif selected_item_text == _T("Sales Tax", lang):
                        view_manager.custom_app_state = STATE_CALC_TAX
                        view_manager.calc_data = [0.0, 0.0]
                        view_manager.calc_selected = 0
                        view_manager.store_ui_dirty = True
                    elif selected_item_text == _T("Bill Splitter", lang):
                        view_manager.custom_app_state = STATE_CALC_SPLIT
                        view_manager.calc_data = [0.0, 2.0, 0.0]
                        view_manager.calc_selected = 0
                        view_manager.store_ui_dirty = True
                    elif selected_item_text == _T("Back", lang):
                        _switch_menu(view_manager, STATE_MENU_SHOPPING, _build_shopping_menu)

                elif state == STATE_MENU_SETTINGS:
                    if selected_idx == 0: # Theme
                        settings["theme_idx"] = (settings["theme_idx"] + 1) % len(_THEMES)
                        view_manager.storage.deserialize(settings, settings_file)
                        _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu, selected=0)
                    elif selected_idx == 1: # Language
                        settings["lang"] = "de" if settings.get("lang", "en") == "en" else "en"
                        view_manager.storage.deserialize(settings, settings_file)
                        try:
                            all_trans = view_manager.storage.serialize("picoware/grocery/lang.json")
                            view_manager.grocery_translations = all_trans.get(settings["lang"], {})
                        except Exception:
                            pass
                        _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu, selected=1)
                    elif selected_idx == 2: # Font Size
                        settings["font_size"] = (settings.get("font_size", 1) + 1) % 3
                        view_manager.storage.deserialize(settings, settings_file)
                        _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu, selected=2)
                    elif selected_idx == 3: # Currency
                        settings["currency"] = "EUR" if settings.get("currency", "$") == "$" else "$"
                        view_manager.storage.deserialize(settings, settings_file)
                        _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu, selected=3)
                    elif selected_idx == 4: # Decimals
                        settings["decimals"] = (settings.get("decimals", 2) + 1) % 5
                        view_manager.storage.deserialize(settings, settings_file)
                        _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu, selected=4)
                    elif selected_idx == 5: # Decimal Point
                        settings["dec_point"] = "," if settings.get("dec_point", ".") == "." else "."
                        view_manager.storage.deserialize(settings, settings_file)
                        _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu, selected=5)
                    elif selected_idx == 6: # Update Translations
                        _init_translations(view_manager.storage, force=True)
                        try:
                            all_trans = view_manager.storage.serialize("picoware/grocery/lang.json")
                            view_manager.grocery_translations = all_trans.get(lang, {})
                        except Exception:
                            pass
                        view_manager.alert(_T("Language File Updated!", lang), False)
                        _switch_menu(view_manager, STATE_MENU_SETTINGS, _build_settings_menu, selected=6)
                    elif selected_idx == 7: # Separator
                        pass
                    elif selected_idx == 8: # Back
                        _switch_menu(view_manager, STATE_MENU_SHOPPING, _build_shopping_menu)
                        
            elif button in (KEY_F4, KEY_F5):
                if state == STATE_MENU_EDIT_LIST:
                    list_name = getattr(view_manager, "active_list_name", "")
                    if list_name != "__Pantry__":
                        try:
                            items = view_manager.storage.read_directory("picoware/grocery/lists")
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
                                    view_manager.active_list_name = list_name
                                    
                                    _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name)
                        except Exception:
                            pass
                    
            elif button == BUTTON_BACK:
                if state == STATE_MENU_SHOPPING:
                    input_manager.reset()
                    view_manager.back()
                elif state == STATE_MENU_SETTINGS:
                    _switch_menu(view_manager, STATE_MENU_SHOPPING, _build_shopping_menu)
                elif state == STATE_MENU_CALCULATORS:
                    _switch_menu(view_manager, STATE_MENU_SHOPPING, _build_shopping_menu)
                elif state == STATE_MENU_SPECIFIC_LIST:
                    _switch_menu(view_manager, STATE_MENU_SHOPPING, _build_shopping_menu)
                elif state == STATE_MENU_EDIT_LIST:
                    list_name = getattr(view_manager, "active_list_name", "")
                    if list_name == "__Pantry__":
                        _switch_menu(view_manager, STATE_MENU_SHOPPING, _build_shopping_menu)
                    else:
                        _switch_menu(view_manager, STATE_MENU_SPECIFIC_LIST, _build_specific_list_menu, list_name)
                elif state == STATE_MENU_EDIT_ITEM:
                    list_name = getattr(view_manager, "active_list_name", "")
                    offset = 5 if list_name == "__Pantry__" else 7
                    _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name, selected=(getattr(view_manager, "active_item_idx", 0) + offset))
                elif state == STATE_MENU_RECENT_ITEMS:
                    list_name = getattr(view_manager, "active_list_name", "")
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
    input_manager = view_manager.input_manager
    button = input_manager.button
    draw = view_manager.draw
    settings = view_manager.grocery_settings
    lang = settings.get("lang", "en")
    state = getattr(view_manager, 'custom_app_state', STATE_MENU_SHOPPING)

    if state == STATE_VIEW_LIST:
        list_name = getattr(view_manager, "active_list_name", "")
        data = getattr(view_manager, "store_data", [])
        idx = getattr(view_manager, "store_idx", 0)
        scroll = getattr(view_manager, "store_scroll", 0)
        dirty = getattr(view_manager, "store_ui_dirty", False)
        
        if button != -1:
            dirty = True
            if button == KEY_F1:
                view_manager.help_return_state = state
                view_manager.custom_app_state = STATE_VIEW_HELP
                _, bg, fg, _ = _get_theme_colors(settings["theme_idx"])
                draw.clear(color=bg)
                view_manager.custom_app_textbox = TextBox(draw, 0, 320, fg, bg)
                view_manager.custom_app_textbox.set_text(_T("HELP_TEXT", lang))
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
                    view_manager.storage.deserialize(data, f"picoware/grocery/lists/{list_name}.json")
            elif button == BUTTON_RIGHT and data:
                # Increase item quantity directly from the store UI
                if not data[idx].get("c", False):
                    data[idx]["q"] = data[idx].get("q", 1) + 1
                    view_manager.storage.deserialize(data, f"picoware/grocery/lists/{list_name}.json")
            elif button == BUTTON_CENTER and data:
                # Toggle Checkbox and reorganize the list so checked items sink to the bottom
                toggled_item = data[idx]
                toggled_item["c"] = not toggled_item.get("c", False)
                data.sort(key=lambda x: x.get("c", False) if isinstance(x, dict) else False)
                view_manager.storage.deserialize(data, f"picoware/grocery/lists/{list_name}.json")
                
                if data and all(item.get("c", False) for item in data):
                    view_manager.custom_app_state = STATE_CONFIRM_EXIT_STORE
                    view_manager.store_exit_choice_state = 0
                    view_manager.store_ui_dirty = True
            elif button == KEY_F2:
                if data:
                    view_manager.custom_app_state = STATE_KEYBOARD_RENAME_IN_STORE
                    kb = view_manager.keyboard
                    kb.reset()
                    kb.title = _T("Rename Item", lang)
                    
                    item = data[idx]
                    kb.response = item.get("n", "") if isinstance(item, dict) else str(item)
                    
                    try:
                        hist = view_manager.storage.serialize("picoware/grocery/history.json")
                        if isinstance(hist, list):
                            kb.auto_complete_words = [str(x) for x in hist]
                    except Exception:
                        kb.auto_complete_words = []
                        
                    kb.run(force=True)
                    kb.run(force=True)
                    view_manager.keyboard_just_opened = True
                    del kb
                else:
                    view_manager.custom_app_state = STATE_MENU_EDIT_LIST
                    _, bg, _, _ = _get_theme_colors(settings["theme_idx"])
                    draw.clear(color=bg)
                    view_manager.custom_app_menu = _build_edit_list_menu(view_manager, list_name)
                    view_manager.custom_app_menu.draw()
                    draw.swap()
            elif button == BUTTON_BACKSPACE and data:
                path = f"picoware/grocery/lists/{list_name}.json"
                try:
                    if isinstance(data, list) and idx < len(data):
                        data.pop(idx)
                        view_manager.storage.deserialize(data, path)
                        view_manager.store_data = data
                        if idx >= len(data) and idx > 0:
                            idx -= 1
                        if idx < scroll: scroll = idx
                        if not data:
                            idx = 0
                            scroll = 0
                except Exception:
                    pass
            elif button == KEY_F3:
                view_manager.custom_app_state = STATE_KEYBOARD_ADD_IN_STORE
                kb = view_manager.keyboard
                kb.reset()
                kb.title = _T("Enter Item", lang)
                kb.response = ""
                
                try:
                    hist = view_manager.storage.serialize("picoware/grocery/history.json")
                    if isinstance(hist, list):
                        kb.auto_complete_words = [str(x) for x in hist]
                except Exception:
                    kb.auto_complete_words = []
                    
                kb.run(force=True)
                kb.run(force=True)
                view_manager.keyboard_just_opened = True
                del kb
            elif button in (KEY_F4, KEY_F5):
                # Fast list switching shortcut without exiting store mode
                try:
                    items = view_manager.storage.read_directory("picoware/grocery/lists")
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
                            view_manager.active_list_name = list_name
                            
                            path = f"picoware/grocery/lists/{list_name}.json"
                            try:
                                data = view_manager.storage.serialize(path)
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
                                view_manager.storage.deserialize(data, path)
                                
                            view_manager.store_data = data
                            idx = scroll = view_manager.store_idx = view_manager.store_scroll = 0
                except Exception:
                    pass
            elif button == BUTTON_BACK:
                view_manager.custom_app_state = STATE_CONFIRM_EXIT_STORE
                view_manager.store_exit_choice_state = 1
                view_manager.store_ui_dirty = True
                
            if hasattr(view_manager, "store_idx"):
                view_manager.store_idx = idx
                view_manager.store_scroll = scroll
            input_manager.reset()
            
        if dirty and getattr(view_manager, 'custom_app_state', STATE_VIEW_LIST) == STATE_VIEW_LIST:
            # Redraw logic for custom list view
            view_manager.store_ui_dirty = False
            font_size = settings.get("font_size", 1)
            
            if not hasattr(view_manager, "store_pantry_counts"):
                try:
                    pantry = view_manager.storage.serialize("picoware/grocery/lists/__Pantry__.json")
                    counts = {}
                    if isinstance(pantry, list):
                        for p in pantry:
                            n = p.get("n", "") if isinstance(p, dict) else str(p)
                            q = p.get("q", 1) if isinstance(p, dict) else 1
                            counts[n.lower()] = q
                    view_manager.store_pantry_counts = counts
                except Exception:
                    view_manager.store_pantry_counts = {}
                    
            _, bg, fg, hl = _get_theme_colors(settings["theme_idx"])
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
                view_manager.store_scroll = scroll
                
            y = 30
            r_3 = row_h // 3
            pantry_counts = getattr(view_manager, "store_pantry_counts", {})
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
                    text_col = _blend_565(fg, bg) if is_checked else fg
                    
                circ_y = y + row_h // 2
                vec1.x = 15; vec1.y = circ_y
                draw.circle(vec1, r_3, text_col)
                if is_checked:
                    draw.fill_circle(vec1, r_3 - 2, text_col)
                    
                cat_idx = item.get("cat", 0)
                if cat_idx > 0:
                    cat_str = f"[{_T(_CATEGORIES[cat_idx], lang)[:3]}] "
                else:
                    cat_str = ""
                text_str = f"{cat_str}{item.get('q', 1)}x {item_name}"
                p_qty = pantry_counts.get(item_name.lower(), 0)
                p_w = draw.len(f"[{p_qty}]", font_size) if p_qty > 0 else 0
                max_w = 320 - 35 - p_w - 10
                
                if draw.len(text_str, font_size) > max_w:
                    while draw.len(text_str + "...", font_size) > max_w and len(text_str) > 3:
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
                    p_str = f"[{p_qty}]"
                    p_w = draw.len(p_str, font_size)
                    vec1.x = 320 - p_w - 5; vec1.y = y + 6
                    draw.text(vec1, p_str, text_col, font_size)
                    
                y += row_h
                
            if not data:
                vec1.x = 10; vec1.y = 40
                draw.text(vec1, _T("(Empty)", lang), fg, font_size)
                
            vec1.x = 0; vec1.y = 320 - 20
            vec2.x = 320; vec2.y = 20
            draw.fill_rectangle(vec1, vec2, bg)
            
            vec1.x = 0; vec1.y = 300
            vec2.x = 320; vec2.y = 300
            draw.line_custom(vec1, vec2, fg)
            
            vec1.x = 5; vec1.y = 304
            draw.text(vec1, _T("STORE_FOOTER", lang), fg)
            
            draw.swap()
            del vec1, vec2
            
def _handle_confirmations(view_manager):
    """
    Handles logic for drawing and evaluating all Yes/No prompt modals
    (e.g., Delete List, Clear Checked, Transfer to Pantry).
    """
    input_manager = view_manager.input_manager
    button = input_manager.button
    draw = view_manager.draw
    settings = view_manager.grocery_settings
    lang = settings.get("lang", "en")
    state = getattr(view_manager, 'custom_app_state', STATE_MENU_SHOPPING)

    if state == STATE_CONFIRM_EXIT_STORE:
        choice_state = getattr(view_manager, "store_exit_choice_state", 1)
        dirty = getattr(view_manager, "store_ui_dirty", True)
        
        if button != -1:
            dirty = True
            if button in (BUTTON_LEFT, BUTTON_UP):
                choice_state = 0
            elif button in (BUTTON_RIGHT, BUTTON_DOWN):
                choice_state = 1
            elif button == BUTTON_CENTER:
                if choice_state == 0: # Yes
                    data = getattr(view_manager, "store_data", [])
                    all_checked = all(item.get("c", False) for item in data) if data else False
                    
                    if all_checked:
                        view_manager.custom_app_state = STATE_CONFIRM_TRANSFER_PANTRY
                        view_manager.transfer_pantry_return_state = STATE_MENU_SPECIFIC_LIST
                        if hasattr(view_manager, "store_data"): del view_manager.store_data
                        if hasattr(view_manager, "store_idx"): del view_manager.store_idx
                        if hasattr(view_manager, "store_scroll"): del view_manager.store_scroll
                        if hasattr(view_manager, "store_pantry_counts"): del view_manager.store_pantry_counts
                        view_manager.store_exit_choice_state = 0
                        view_manager.store_ui_dirty = True
                    else:
                        view_manager.custom_app_state = STATE_MENU_SPECIFIC_LIST
                        list_name = getattr(view_manager, "active_list_name", "")
                        if hasattr(view_manager, "store_data"): del view_manager.store_data
                        if hasattr(view_manager, "store_idx"): del view_manager.store_idx
                        if hasattr(view_manager, "store_scroll"): del view_manager.store_scroll
                        if hasattr(view_manager, "store_ui_dirty"): del view_manager.store_ui_dirty
                        if hasattr(view_manager, "store_pantry_counts"): del view_manager.store_pantry_counts
                        if hasattr(view_manager, "store_exit_choice_state"): del view_manager.store_exit_choice_state
                        
                        _, bg, _, _ = _get_theme_colors(settings["theme_idx"])
                        draw.clear(color=bg)
                        view_manager.custom_app_menu = _build_specific_list_menu(view_manager, list_name)
                        view_manager.custom_app_menu.draw()
                        draw.swap()
                else: # No
                    view_manager.custom_app_state = STATE_VIEW_LIST
                    view_manager.store_ui_dirty = True
                    if hasattr(view_manager, "store_exit_choice_state"): del view_manager.store_exit_choice_state
            elif button == BUTTON_BACK:
                view_manager.custom_app_state = STATE_VIEW_LIST
                view_manager.store_ui_dirty = True
                if hasattr(view_manager, "store_exit_choice_state"): del view_manager.store_exit_choice_state
                
            if hasattr(view_manager, "store_exit_choice_state"):
                view_manager.store_exit_choice_state = choice_state
            input_manager.reset()
            
        if dirty and getattr(view_manager, 'custom_app_state', STATE_CONFIRM_EXIT_STORE) == STATE_CONFIRM_EXIT_STORE:
            view_manager.store_ui_dirty = False
            _, bg, fg, hl = _get_theme_colors(settings["theme_idx"])
            
            draw.clear(color=bg)
            
            v1 = Vector(20, 100)
            v2 = Vector(280, 120)
            draw.rect(v1, v2, fg)
            
            data = getattr(view_manager, "store_data", [])
            all_checked = all(item.get("c", False) for item in data) if data else False
            
            title_str = _T("All done! Exit?", lang) if all_checked else _T("Exit store mode?", lang)
            font_sz = 2
            tw = draw.len(title_str, font_sz)
            draw.text(Vector(20 + (280 - tw)//2, 115), title_str, fg, font_sz)
            
            opt_yes = _T("Yes", lang)
            yw = draw.len(opt_yes, font_sz)
            y_pos = Vector(70, 170)
            if choice_state == 0:
                draw.fill_rectangle(Vector(y_pos.x - 10, y_pos.y - 5), Vector(yw + 20, 26), hl)
                draw.text(y_pos, opt_yes, bg, font_sz)
            else:
                draw.text(y_pos, opt_yes, fg, font_sz)
                
            opt_no = _T("No", lang)
            nw = draw.len(opt_no, font_sz)
            n_pos = Vector(250 - nw, 170)
            if choice_state == 1:
                draw.fill_rectangle(Vector(n_pos.x - 10, n_pos.y - 5), Vector(nw + 20, 26), hl)
                draw.text(n_pos, opt_no, bg, font_sz)
            else:
                draw.text(n_pos, opt_no, fg, font_sz)
                
            draw.swap()
            del v1, v2, y_pos, n_pos

    elif state == STATE_CONFIRM_DELETE_LIST:
        choice_state = getattr(view_manager, "store_exit_choice_state", 1)
        dirty = getattr(view_manager, "store_ui_dirty", True)
        
        if button != -1:
            dirty = True
            if button in (BUTTON_LEFT, BUTTON_UP):
                choice_state = 0
            elif button in (BUTTON_RIGHT, BUTTON_DOWN):
                choice_state = 1
            elif button == BUTTON_CENTER:
                if choice_state == 0: # Yes
                    list_name = getattr(view_manager, "active_list_name", "")
                    if list_name:
                        try: view_manager.storage.remove(f"picoware/grocery/lists/{list_name}.json")
                        except Exception: pass
                    view_manager.custom_app_state = STATE_MENU_SHOPPING
                    
                    if hasattr(view_manager, "store_exit_choice_state"): del view_manager.store_exit_choice_state
                    if hasattr(view_manager, "active_list_name"): del view_manager.active_list_name
                    if hasattr(view_manager, "store_data"): del view_manager.store_data
                    if hasattr(view_manager, "store_idx"): del view_manager.store_idx
                    if hasattr(view_manager, "store_scroll"): del view_manager.store_scroll
                    if hasattr(view_manager, "store_pantry_counts"): del view_manager.store_pantry_counts
                    
                    _, bg, _, _ = _get_theme_colors(settings["theme_idx"])
                    draw.clear(color=bg)
                    view_manager.custom_app_menu = _build_shopping_menu(view_manager)
                    view_manager.custom_app_menu.draw()
                    draw.swap()
                else: # No
                    view_manager.custom_app_state = STATE_MENU_SPECIFIC_LIST
                    list_name = getattr(view_manager, "active_list_name", "")
                    if hasattr(view_manager, "store_exit_choice_state"): del view_manager.store_exit_choice_state
                    
                    _, bg, _, _ = _get_theme_colors(settings["theme_idx"])
                    draw.clear(color=bg)
                    view_manager.custom_app_menu = _build_specific_list_menu(view_manager, list_name)
                    view_manager.custom_app_menu.draw()
                    draw.swap()
            elif button == BUTTON_BACK:
                view_manager.custom_app_state = STATE_MENU_SPECIFIC_LIST
                list_name = getattr(view_manager, "active_list_name", "")
                if hasattr(view_manager, "store_exit_choice_state"): del view_manager.store_exit_choice_state
                
                _, bg, _, _ = _get_theme_colors(settings["theme_idx"])
                draw.clear(color=bg)
                view_manager.custom_app_menu = _build_specific_list_menu(view_manager, list_name)
                view_manager.custom_app_menu.draw()
                draw.swap()
                
            if hasattr(view_manager, "store_exit_choice_state"):
                view_manager.store_exit_choice_state = choice_state
            input_manager.reset()
            
        if dirty and getattr(view_manager, 'custom_app_state', STATE_CONFIRM_DELETE_LIST) == STATE_CONFIRM_DELETE_LIST:
            view_manager.store_ui_dirty = False
            _, bg, fg, hl = _get_theme_colors(settings["theme_idx"])
            
            draw.clear(color=bg)
            
            v1 = Vector(20, 100)
            v2 = Vector(280, 120)
            draw.rect(v1, v2, fg)
            
            title_str = _T("Delete List?", lang)
            font_sz = 2
            tw = draw.len(title_str, font_sz)
            draw.text(Vector(20 + (280 - tw)//2, 115), title_str, fg, font_sz)
            
            opt_yes = _T("Yes", lang)
            yw = draw.len(opt_yes, font_sz)
            y_pos = Vector(70, 170)
            if choice_state == 0:
                draw.fill_rectangle(Vector(y_pos.x - 10, y_pos.y - 5), Vector(yw + 20, 26), hl)
                draw.text(y_pos, opt_yes, bg, font_sz)
            else:
                draw.text(y_pos, opt_yes, fg, font_sz)
                
            opt_no = _T("No", lang)
            nw = draw.len(opt_no, font_sz)
            n_pos = Vector(250 - nw, 170)
            if choice_state == 1:
                draw.fill_rectangle(Vector(n_pos.x - 10, n_pos.y - 5), Vector(nw + 20, 26), hl)
                draw.text(n_pos, opt_no, bg, font_sz)
            else:
                draw.text(n_pos, opt_no, fg, font_sz)
                
            draw.swap()
            del v1, v2, y_pos, n_pos

    elif state == STATE_CONFIRM_DELETE_ITEM:
        choice_state = getattr(view_manager, "store_exit_choice_state", 1)
        dirty = getattr(view_manager, "store_ui_dirty", True)
        
        if button != -1:
            dirty = True
            if button in (BUTTON_LEFT, BUTTON_UP):
                choice_state = 0
            elif button in (BUTTON_RIGHT, BUTTON_DOWN):
                choice_state = 1
            elif button == BUTTON_CENTER:
                if choice_state == 0: # Yes
                    list_name = getattr(view_manager, "active_list_name", "")
                    item_idx = getattr(view_manager, "active_item_idx", 0)
                    path = f"picoware/grocery/lists/{list_name}.json"
                    try:
                        data = view_manager.storage.serialize(path)
                        if isinstance(data, list) and item_idx < len(data):
                            data.pop(item_idx)
                            view_manager.storage.deserialize(data, path)
                            if item_idx >= len(data) and item_idx > 0:
                                view_manager.active_item_idx = item_idx - 1
                    except Exception:
                        pass
                        
                    view_manager.custom_app_state = STATE_MENU_EDIT_LIST
                    if hasattr(view_manager, "store_exit_choice_state"): del view_manager.store_exit_choice_state
                    
                    _, bg, _, _ = _get_theme_colors(settings["theme_idx"])
                    draw.clear(color=bg)
                    view_manager.custom_app_menu = _build_edit_list_menu(view_manager, list_name)
                    offset = 5 if list_name == "__Pantry__" else 7
                    view_manager.custom_app_menu.set_selected(getattr(view_manager, "active_item_idx", 0) + offset)
                    view_manager.custom_app_menu.draw()
                    draw.swap()
                else: # No
                    view_manager.custom_app_state = STATE_MENU_EDIT_ITEM
                    item_name = getattr(view_manager, "active_item_name", "")
                    if hasattr(view_manager, "store_exit_choice_state"): del view_manager.store_exit_choice_state
                    
                    _, bg, _, _ = _get_theme_colors(settings["theme_idx"])
                    draw.clear(color=bg)
                    view_manager.custom_app_menu = _build_edit_item_menu(view_manager, item_name)
                    view_manager.custom_app_menu.set_selected(3)
                    view_manager.custom_app_menu.draw()
                    draw.swap()
            elif button == BUTTON_BACK:
                view_manager.custom_app_state = STATE_MENU_EDIT_ITEM
                item_name = getattr(view_manager, "active_item_name", "")
                if hasattr(view_manager, "store_exit_choice_state"): del view_manager.store_exit_choice_state
                
                _, bg, _, _ = _get_theme_colors(settings["theme_idx"])
                draw.clear(color=bg)
                view_manager.custom_app_menu = _build_edit_item_menu(view_manager, item_name)
                view_manager.custom_app_menu.set_selected(3)
                view_manager.custom_app_menu.draw()
                draw.swap()
                
            if hasattr(view_manager, "store_exit_choice_state"):
                view_manager.store_exit_choice_state = choice_state
            input_manager.reset()
            
        if dirty and getattr(view_manager, 'custom_app_state', STATE_CONFIRM_DELETE_ITEM) == STATE_CONFIRM_DELETE_ITEM:
            view_manager.store_ui_dirty = False
            _, bg, fg, hl = _get_theme_colors(settings["theme_idx"])
            
            draw.clear(color=bg)
            
            v1 = Vector(20, 100)
            v2 = Vector(280, 120)
            draw.rect(v1, v2, fg)
            
            title_str = _T("Delete Item?", lang)
            font_sz = 2
            tw = draw.len(title_str, font_sz)
            draw.text(Vector(20 + (280 - tw)//2, 115), title_str, fg, font_sz)
            
            opt_yes = _T("Yes", lang)
            yw = draw.len(opt_yes, font_sz)
            y_pos = Vector(70, 170)
            if choice_state == 0:
                draw.fill_rectangle(Vector(y_pos.x - 10, y_pos.y - 5), Vector(yw + 20, 26), hl)
                draw.text(y_pos, opt_yes, bg, font_sz)
            else:
                draw.text(y_pos, opt_yes, fg, font_sz)
                
            opt_no = _T("No", lang)
            nw = draw.len(opt_no, font_sz)
            n_pos = Vector(250 - nw, 170)
            if choice_state == 1:
                draw.fill_rectangle(Vector(n_pos.x - 10, n_pos.y - 5), Vector(nw + 20, 26), hl)
                draw.text(n_pos, opt_no, bg, font_sz)
            else:
                draw.text(n_pos, opt_no, fg, font_sz)
                
            draw.swap()
            del v1, v2, y_pos, n_pos

    elif state == STATE_CONFIRM_UNCHECK_ALL:
        choice_state = getattr(view_manager, "store_exit_choice_state", 1)
        dirty = getattr(view_manager, "store_ui_dirty", True)
        
        if button != -1:
            dirty = True
            if button in (BUTTON_LEFT, BUTTON_UP):
                choice_state = 0
            elif button in (BUTTON_RIGHT, BUTTON_DOWN):
                choice_state = 1
            elif button == BUTTON_CENTER:
                list_name = getattr(view_manager, "active_list_name", "")
                if choice_state == 0: # Yes
                    path = f"picoware/grocery/lists/{list_name}.json"
                    try:
                        data = view_manager.storage.serialize(path)
                        if isinstance(data, list):
                            modified = False
                            for item in data:
                                if isinstance(item, dict) and item.get("c", False):
                                    item["c"] = False
                                    modified = True
                            if modified:
                                view_manager.storage.deserialize(data, path)
                    except Exception:
                        pass
                
                view_manager.custom_app_state = STATE_MENU_SPECIFIC_LIST
                if hasattr(view_manager, "store_exit_choice_state"): del view_manager.store_exit_choice_state
                
                _, bg, _, _ = _get_theme_colors(settings["theme_idx"])
                draw.clear(color=bg)
                view_manager.custom_app_menu = _build_specific_list_menu(view_manager, list_name)
                view_manager.custom_app_menu.set_selected(3)
                view_manager.custom_app_menu.draw()
                draw.swap()
            elif button == BUTTON_BACK:
                view_manager.custom_app_state = STATE_MENU_SPECIFIC_LIST
                list_name = getattr(view_manager, "active_list_name", "")
                if hasattr(view_manager, "store_exit_choice_state"): del view_manager.store_exit_choice_state
                
                _, bg, _, _ = _get_theme_colors(settings["theme_idx"])
                draw.clear(color=bg)
                view_manager.custom_app_menu = _build_specific_list_menu(view_manager, list_name)
                view_manager.custom_app_menu.set_selected(3)
                view_manager.custom_app_menu.draw()
                draw.swap()
                
            if hasattr(view_manager, "store_exit_choice_state"):
                view_manager.store_exit_choice_state = choice_state
            input_manager.reset()
            
        if dirty and getattr(view_manager, 'custom_app_state', STATE_CONFIRM_UNCHECK_ALL) == STATE_CONFIRM_UNCHECK_ALL:
            view_manager.store_ui_dirty = False
            _, bg, fg, hl = _get_theme_colors(settings["theme_idx"])
            
            draw.clear(color=bg)
            
            v1 = Vector(20, 100)
            v2 = Vector(280, 120)
            draw.rect(v1, v2, fg)
            
            title_str = _T("Uncheck All?", lang)
            font_sz = 2
            tw = draw.len(title_str, font_sz)
            draw.text(Vector(20 + (280 - tw)//2, 115), title_str, fg, font_sz)
            
            opt_yes = _T("Yes", lang)
            yw = draw.len(opt_yes, font_sz)
            y_pos = Vector(70, 170)
            if choice_state == 0:
                draw.fill_rectangle(Vector(y_pos.x - 10, y_pos.y - 5), Vector(yw + 20, 26), hl)
                draw.text(y_pos, opt_yes, bg, font_sz)
            else:
                draw.text(y_pos, opt_yes, fg, font_sz)
                
            opt_no = _T("No", lang)
            nw = draw.len(opt_no, font_sz)
            n_pos = Vector(250 - nw, 170)
            if choice_state == 1:
                draw.fill_rectangle(Vector(n_pos.x - 10, n_pos.y - 5), Vector(nw + 20, 26), hl)
                draw.text(n_pos, opt_no, bg, font_sz)
            else:
                draw.text(n_pos, opt_no, fg, font_sz)
                
            draw.swap()
            del v1, v2, y_pos, n_pos

    elif state == STATE_CONFIRM_CLEAR_CHECKED:
        choice_state = getattr(view_manager, "store_exit_choice_state", 1)
        dirty = getattr(view_manager, "store_ui_dirty", True)
        
        if button != -1:
            dirty = True
            if button in (BUTTON_LEFT, BUTTON_UP):
                choice_state = 0
            elif button in (BUTTON_RIGHT, BUTTON_DOWN):
                choice_state = 1
            elif button == BUTTON_CENTER:
                list_name = getattr(view_manager, "active_list_name", "")
                if choice_state == 0: # Yes
                    path = f"picoware/grocery/lists/{list_name}.json"
                    try:
                        data = view_manager.storage.serialize(path)
                        if isinstance(data, list):
                            new_data = [item for item in data if not (isinstance(item, dict) and item.get("c", False))]
                            if len(new_data) != len(data):
                                view_manager.storage.deserialize(new_data, path)
                    except Exception:
                        pass
                
                ret_state = getattr(view_manager, "clear_checked_return_state", STATE_MENU_SPECIFIC_LIST)
                view_manager.custom_app_state = ret_state
                if hasattr(view_manager, "store_exit_choice_state"): del view_manager.store_exit_choice_state
                if hasattr(view_manager, "clear_checked_return_state"): del view_manager.clear_checked_return_state
                
                _, bg, _, _ = _get_theme_colors(settings["theme_idx"])
                draw.clear(color=bg)
                if ret_state == STATE_MENU_SPECIFIC_LIST:
                    view_manager.custom_app_menu = _build_specific_list_menu(view_manager, list_name)
                    view_manager.custom_app_menu.set_selected(4)
                else:
                    view_manager.custom_app_menu = _build_edit_list_menu(view_manager, list_name)
                    view_manager.custom_app_menu.set_selected(4)
                view_manager.custom_app_menu.draw()
                draw.swap()
            elif button == BUTTON_BACK:
                ret_state = getattr(view_manager, "clear_checked_return_state", STATE_MENU_SPECIFIC_LIST)
                view_manager.custom_app_state = ret_state
                list_name = getattr(view_manager, "active_list_name", "")
                if hasattr(view_manager, "store_exit_choice_state"): del view_manager.store_exit_choice_state
                if hasattr(view_manager, "clear_checked_return_state"): del view_manager.clear_checked_return_state
                
                _, bg, _, _ = _get_theme_colors(settings["theme_idx"])
                draw.clear(color=bg)
                if ret_state == STATE_MENU_SPECIFIC_LIST:
                    view_manager.custom_app_menu = _build_specific_list_menu(view_manager, list_name)
                    view_manager.custom_app_menu.set_selected(4)
                else:
                    view_manager.custom_app_menu = _build_edit_list_menu(view_manager, list_name)
                    view_manager.custom_app_menu.set_selected(4)
                view_manager.custom_app_menu.draw()
                draw.swap()
                
            if hasattr(view_manager, "store_exit_choice_state"):
                view_manager.store_exit_choice_state = choice_state
            input_manager.reset()
            
        if dirty and getattr(view_manager, 'custom_app_state', STATE_CONFIRM_CLEAR_CHECKED) == STATE_CONFIRM_CLEAR_CHECKED:
            view_manager.store_ui_dirty = False
            _, bg, fg, hl = _get_theme_colors(settings["theme_idx"])
            
            draw.clear(color=bg)
            
            v1 = Vector(20, 100)
            v2 = Vector(280, 120)
            draw.rect(v1, v2, fg)
            
            title_str = _T("Clear Checked?", lang)
            font_sz = 2
            tw = draw.len(title_str, font_sz)
            draw.text(Vector(20 + (280 - tw)//2, 115), title_str, fg, font_sz)
            
            opt_yes = _T("Yes", lang)
            yw = draw.len(opt_yes, font_sz)
            y_pos = Vector(70, 170)
            if choice_state == 0:
                draw.fill_rectangle(Vector(y_pos.x - 10, y_pos.y - 5), Vector(yw + 20, 26), hl)
                draw.text(y_pos, opt_yes, bg, font_sz)
            else:
                draw.text(y_pos, opt_yes, fg, font_sz)
                
            opt_no = _T("No", lang)
            nw = draw.len(opt_no, font_sz)
            n_pos = Vector(250 - nw, 170)
            if choice_state == 1:
                draw.fill_rectangle(Vector(n_pos.x - 10, n_pos.y - 5), Vector(nw + 20, 26), hl)
                draw.text(n_pos, opt_no, bg, font_sz)
            else:
                draw.text(n_pos, opt_no, fg, font_sz)
                
            draw.swap()
            del v1, v2, y_pos, n_pos
            
    elif state == STATE_CONFIRM_CLEAR_ALL_ITEMS:
        choice_state = getattr(view_manager, "store_exit_choice_state", 1)
        dirty = getattr(view_manager, "store_ui_dirty", True)
        
        if button != -1:
            dirty = True
            if button in (BUTTON_LEFT, BUTTON_UP):
                choice_state = 0
            elif button in (BUTTON_RIGHT, BUTTON_DOWN):
                choice_state = 1
            elif button == BUTTON_CENTER:
                list_name = getattr(view_manager, "active_list_name", "")
                if choice_state == 0: # Yes
                    path = f"picoware/grocery/lists/{list_name}.json"
                    try:
                        view_manager.storage.deserialize([], path)
                    except Exception:
                        pass
                
                view_manager.custom_app_state = STATE_MENU_EDIT_LIST
                if hasattr(view_manager, "store_exit_choice_state"): del view_manager.store_exit_choice_state
                
                _, bg, _, _ = _get_theme_colors(settings["theme_idx"])
                draw.clear(color=bg)
                view_manager.custom_app_menu = _build_edit_list_menu(view_manager, list_name)
                if choice_state == 0:
                    view_manager.custom_app_menu.set_selected(0)
                else:
                    view_manager.custom_app_menu.set_selected(1)
                view_manager.custom_app_menu.draw()
                draw.swap()
            elif button == BUTTON_BACK:
                view_manager.custom_app_state = STATE_MENU_EDIT_LIST
                list_name = getattr(view_manager, "active_list_name", "")
                if hasattr(view_manager, "store_exit_choice_state"): del view_manager.store_exit_choice_state
                
                _, bg, _, _ = _get_theme_colors(settings["theme_idx"])
                draw.clear(color=bg)
                view_manager.custom_app_menu = _build_edit_list_menu(view_manager, list_name)
                view_manager.custom_app_menu.set_selected(1)
                view_manager.custom_app_menu.draw()
                draw.swap()
                
            if hasattr(view_manager, "store_exit_choice_state"):
                view_manager.store_exit_choice_state = choice_state
            input_manager.reset()
            
        if dirty and getattr(view_manager, 'custom_app_state', STATE_CONFIRM_CLEAR_ALL_ITEMS) == STATE_CONFIRM_CLEAR_ALL_ITEMS:
            view_manager.store_ui_dirty = False
            _, bg, fg, hl = _get_theme_colors(settings["theme_idx"])
            
            draw.clear(color=bg)
            
            v1 = Vector(20, 100)
            v2 = Vector(280, 120)
            draw.rect(v1, v2, fg)
            
            title_str = _T("Clear All Items?", lang)
            font_sz = 2
            tw = draw.len(title_str, font_sz)
            draw.text(Vector(20 + (280 - tw)//2, 115), title_str, fg, font_sz)
            
            opt_yes = _T("Yes", lang)
            yw = draw.len(opt_yes, font_sz)
            y_pos = Vector(70, 170)
            if choice_state == 0:
                draw.fill_rectangle(Vector(y_pos.x - 10, y_pos.y - 5), Vector(yw + 20, 26), hl)
                draw.text(y_pos, opt_yes, bg, font_sz)
            else:
                draw.text(y_pos, opt_yes, fg, font_sz)
                
            opt_no = _T("No", lang)
            nw = draw.len(opt_no, font_sz)
            n_pos = Vector(250 - nw, 170)
            if choice_state == 1:
                draw.fill_rectangle(Vector(n_pos.x - 10, n_pos.y - 5), Vector(nw + 20, 26), hl)
                draw.text(n_pos, opt_no, bg, font_sz)
            else:
                draw.text(n_pos, opt_no, fg, font_sz)
                
            draw.swap()
            del v1, v2, y_pos, n_pos
            
    elif state == STATE_CONFIRM_TRANSFER_PANTRY:
        choice_state = getattr(view_manager, "store_exit_choice_state", 1)
        dirty = getattr(view_manager, "store_ui_dirty", True)
        
        if button != -1:
            dirty = True
            if button in (BUTTON_LEFT, BUTTON_UP):
                choice_state = 0
            elif button in (BUTTON_RIGHT, BUTTON_DOWN):
                choice_state = 1
            elif button == BUTTON_CENTER:
                list_name = getattr(view_manager, "active_list_name", "")
                if choice_state == 0: # Yes
                    path = f"picoware/grocery/lists/{list_name}.json"
                    pantry_path = "picoware/grocery/lists/__Pantry__.json"
                    try:
                        data = view_manager.storage.serialize(path)
                        pantry_data = view_manager.storage.serialize(pantry_path)
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
                                        
                                view_manager.storage.deserialize(new_data, path)
                                view_manager.storage.deserialize(pantry_data, pantry_path)
                    except Exception:
                        pass
                
                ret_state = getattr(view_manager, "transfer_pantry_return_state", STATE_MENU_SPECIFIC_LIST)
                view_manager.custom_app_state = ret_state
                if hasattr(view_manager, "store_exit_choice_state"): del view_manager.store_exit_choice_state
                if hasattr(view_manager, "transfer_pantry_return_state"): del view_manager.transfer_pantry_return_state
                
                _, bg, _, _ = _get_theme_colors(settings["theme_idx"])
                draw.clear(color=bg)
                if ret_state == STATE_MENU_SPECIFIC_LIST:
                    view_manager.custom_app_menu = _build_specific_list_menu(view_manager, list_name)
                    view_manager.custom_app_menu.set_selected(5)
                else:
                    view_manager.custom_app_menu = _build_edit_list_menu(view_manager, list_name)
                    view_manager.custom_app_menu.set_selected(5)
                view_manager.custom_app_menu.draw()
                draw.swap()
            elif button == BUTTON_BACK:
                ret_state = getattr(view_manager, "transfer_pantry_return_state", STATE_MENU_SPECIFIC_LIST)
                view_manager.custom_app_state = ret_state
                list_name = getattr(view_manager, "active_list_name", "")
                if hasattr(view_manager, "store_exit_choice_state"): del view_manager.store_exit_choice_state
                if hasattr(view_manager, "transfer_pantry_return_state"): del view_manager.transfer_pantry_return_state
                
                _, bg, _, _ = _get_theme_colors(settings["theme_idx"])
                draw.clear(color=bg)
                if ret_state == STATE_MENU_SPECIFIC_LIST:
                    view_manager.custom_app_menu = _build_specific_list_menu(view_manager, list_name)
                    view_manager.custom_app_menu.set_selected(5)
                else:
                    view_manager.custom_app_menu = _build_edit_list_menu(view_manager, list_name)
                    view_manager.custom_app_menu.set_selected(5)
                view_manager.custom_app_menu.draw()
                draw.swap()
                
            if hasattr(view_manager, "store_exit_choice_state"):
                view_manager.store_exit_choice_state = choice_state
            input_manager.reset()
            
        if dirty and getattr(view_manager, 'custom_app_state', STATE_CONFIRM_TRANSFER_PANTRY) == STATE_CONFIRM_TRANSFER_PANTRY:
            view_manager.store_ui_dirty = False
            _, bg, fg, hl = _get_theme_colors(settings["theme_idx"])
            
            draw.clear(color=bg)
            
            v1 = Vector(20, 100)
            v2 = Vector(280, 120)
            draw.rect(v1, v2, fg)
            
            title_str = _T("Transfer to Pantry?", lang)
            font_sz = 2
            tw = draw.len(title_str, font_sz)
            draw.text(Vector(20 + (280 - tw)//2, 115), title_str, fg, font_sz)
            
            opt_yes = _T("Yes", lang)
            yw = draw.len(opt_yes, font_sz)
            y_pos = Vector(70, 170)
            if choice_state == 0:
                draw.fill_rectangle(Vector(y_pos.x - 10, y_pos.y - 5), Vector(yw + 20, 26), hl)
                draw.text(y_pos, opt_yes, bg, font_sz)
            else:
                draw.text(y_pos, opt_yes, fg, font_sz)
                
            opt_no = _T("No", lang)
            nw = draw.len(opt_no, font_sz)
            n_pos = Vector(250 - nw, 170)
            if choice_state == 1:
                draw.fill_rectangle(Vector(n_pos.x - 10, n_pos.y - 5), Vector(nw + 20, 26), hl)
                draw.text(n_pos, opt_no, bg, font_sz)
            else:
                draw.text(n_pos, opt_no, fg, font_sz)
                
            draw.swap()
            del v1, v2, y_pos, n_pos

def _handle_calculators(view_manager):
    """
    Encapsulates all calculator tool logic (Price Compare, Discounts, Conversions, etc.)
    Optimized heavily to reuse a single dynamic input/output drawing loop.
    """
    input_manager = view_manager.input_manager
    button = input_manager.button
    draw = view_manager.draw
    settings = view_manager.grocery_settings
    lang = settings.get("lang", "en")
    state = getattr(view_manager, 'custom_app_state', STATE_MENU_SHOPPING)

    if state == STATE_CALC_PRICE_COMPARE:
        dirty = getattr(view_manager, "store_ui_dirty", True)
        units = ["", "g", "kg", "oz", "lb", "ml", "L", "fl oz", "gal"]
        cdata = getattr(view_manager, "calc_data", [0.0, 1.0, 0, 0.0, 1.0, 0])
        if len(cdata) == 4:
            cdata.insert(2, 0)
            cdata.append(0)
            view_manager.calc_data = cdata
        
        if button != -1:
            dirty = True
            if button == BUTTON_UP:
                view_manager.calc_selected = (view_manager.calc_selected - 1) % 4
            elif button == BUTTON_DOWN:
                view_manager.calc_selected = (view_manager.calc_selected + 1) % 4
            elif button == BUTTON_LEFT:
                if view_manager.calc_selected == 1:
                    view_manager.calc_data[2] = (view_manager.calc_data[2] - 1) % len(units)
                elif view_manager.calc_selected == 3:
                    view_manager.calc_data[5] = (view_manager.calc_data[5] - 1) % len(units)
            elif button == BUTTON_RIGHT:
                if view_manager.calc_selected == 1:
                    view_manager.calc_data[2] = (view_manager.calc_data[2] + 1) % len(units)
                elif view_manager.calc_selected == 3:
                    view_manager.calc_data[5] = (view_manager.calc_data[5] + 1) % len(units)
            elif button == BUTTON_CENTER:
                input_manager.reset()
                view_manager.custom_app_state = STATE_KEYBOARD_PRICE_COMPARE
                kb = view_manager.keyboard
                kb.reset()
                labels = [_T("Price A", lang), _T("Qty A", lang), _T("Price B", lang), _T("Qty B", lang)]
                kb.title = labels[view_manager.calc_selected]
                idx_map = {0: 0, 1: 1, 2: 3, 3: 4}
                val_idx = idx_map[view_manager.calc_selected]
                kb.response = str(view_manager.calc_data[val_idx]).replace('.', settings.get("dec_point", "."))
                kb.run(force=True)
                kb.run(force=True)
                view_manager.keyboard_just_opened = True
                del labels, kb
            elif button == BUTTON_BACK:
                view_manager.custom_app_state = STATE_MENU_CALCULATORS
                _, bg, _, _ = _get_theme_colors(settings["theme_idx"])
                draw.clear(color=bg)
                view_manager.custom_app_menu = _build_calculators_menu(view_manager)
                view_manager.custom_app_menu.draw()
                draw.swap()
            else:
                char = input_manager.button_to_char(button)
                if char and char in "0123456789.,":
                    input_manager.reset()
                    view_manager.custom_app_state = STATE_KEYBOARD_PRICE_COMPARE
                    kb = view_manager.keyboard
                    kb.reset()
                    labels = [_T("Price A", lang), _T("Qty A", lang), _T("Price B", lang), _T("Qty B", lang)]
                    kb.title = labels[view_manager.calc_selected]
                    kb.response = char
                    kb.run(force=True)
                    kb.run(force=True)
                    view_manager.keyboard_just_opened = True
                    del labels, kb
            input_manager.reset()
            
        if dirty and getattr(view_manager, 'custom_app_state', STATE_CALC_PRICE_COMPARE) == STATE_CALC_PRICE_COMPARE:
            view_manager.store_ui_dirty = False
            _, bg, fg, hl = _get_theme_colors(settings["theme_idx"])
            draw.clear(color=bg)
            
            vec1 = Vector(0, 0)
            vec2 = Vector(320, 26)
            draw.fill_rectangle(vec1, vec2, hl)
            vec1.x = 5; vec1.y = 5
            draw.text(vec1, _T("Price Compare", lang), bg)
            
            font_size = 1
            labels = [_T("Price A", lang), _T("Qty A", lang), _T("Price B", lang), _T("Qty B", lang)]
            dec = settings.get("decimals", 2)
            curr = settings.get("currency", "$")
            dp = settings.get("dec_point", ".")
            
            y = 40
            for i in range(4):
                if i == getattr(view_manager, "calc_selected", 0):
                    draw.fill_rectangle(Vector(0, y - 2), Vector(320, 24), hl)
                    text_color = bg
                else:
                    text_color = fg
                
                draw.text(Vector(10, y), labels[i] + ":", text_color, font_size)
                
                cdata = getattr(view_manager, "calc_data", [0.0, 1.0, 0, 0.0, 1.0, 0])
                idx_map = {0: 0, 1: 1, 2: 3, 3: 4}
                val = cdata[idx_map[i]]
                
                if i in (0, 2):
                    num_str = ("{:." + str(dec) + "f}").format(val).replace('.', dp)
                    val_str = f"{num_str} {curr}"
                else:
                    num_str = str(int(val)) if val == int(val) else f"{val:.3f}".rstrip('0').rstrip('.')
                    val_str = num_str.replace('.', dp)
                    unit_idx = cdata[2] if i == 1 else cdata[5]
                    if unit_idx > 0:
                        val_str = f"< {val_str} {units[unit_idx]} >"
                    else:
                        val_str = f"< {val_str} >"
                        
                vw = draw.len(val_str, font_size)
                draw.text(Vector(310 - vw, y), val_str, text_color, font_size)
                y += 30
                
            draw.line_custom(Vector(10, y), Vector(310, y), fg)
            y += 10
            
            cdata = getattr(view_manager, "calc_data", [0.0, 1.0, 0, 0.0, 1.0, 0])
            pa, qa, ua, pb, qb, ub = cdata[0], cdata[1] if cdata[1] > 0 else 1.0, cdata[2], cdata[3], cdata[4] if cdata[4] > 0 else 1.0, cdata[5]
            
            mults = [1.0, 1.0, 1000.0, 28.3495, 453.592, 1.0, 1000.0, 29.5735, 3785.41]
            
            norm_qa = qa * mults[ua]
            norm_qb = qb * mults[ub]
            
            val_a = pa / norm_qa
            val_b = pb / norm_qb
            
            if val_a == 0 and val_b == 0: res_str = "---"
            elif val_a < val_b: res_str = _T("A is {:.1f}% cheaper!", lang).format(((val_b - val_a) / val_b) * 100).replace('.', dp) if val_b > 0 else _T("A is cheaper!", lang)
            elif val_b < val_a: res_str = _T("B is {:.1f}% cheaper!", lang).format(((val_a - val_b) / val_a) * 100).replace('.', dp) if val_a > 0 else _T("B is cheaper!", lang)
            else: res_str = _T("Same price!", lang)
                
            draw.text(Vector(10, y), _T("Best Deal:", lang), fg, font_size)
            res_w = draw.len(res_str, font_size)
            draw.text(Vector(310 - res_w, y), res_str, hl, font_size)
            draw.swap()

    elif state == STATE_CALC_DISCOUNT:
        dirty = getattr(view_manager, "store_ui_dirty", True)
        
        if button != -1:
            dirty = True
            if button == BUTTON_UP:
                view_manager.calc_selected = (view_manager.calc_selected - 1) % 2
            elif button == BUTTON_DOWN:
                view_manager.calc_selected = (view_manager.calc_selected + 1) % 2
            elif button == BUTTON_CENTER:
                input_manager.reset()
                view_manager.custom_app_state = STATE_KEYBOARD_DISCOUNT
                kb = view_manager.keyboard
                kb.reset()
                labels = [_T("Original Price", lang), _T("Discount %", lang)]
                kb.title = labels[view_manager.calc_selected]
                kb.response = str(view_manager.calc_data[view_manager.calc_selected]).replace('.', settings.get("dec_point", "."))
                kb.run(force=True)
                kb.run(force=True)
                view_manager.keyboard_just_opened = True
                del labels, kb
            elif button in (BUTTON_BACK, BUTTON_LEFT):
                view_manager.custom_app_state = STATE_MENU_CALCULATORS
                _, bg, _, _ = _get_theme_colors(settings["theme_idx"])
                draw.clear(color=bg)
                view_manager.custom_app_menu = _build_calculators_menu(view_manager)
                view_manager.custom_app_menu.draw()
                draw.swap()
            else:
                char = input_manager.button_to_char(button)
                if char and char in "0123456789.,":
                    input_manager.reset()
                    view_manager.custom_app_state = STATE_KEYBOARD_DISCOUNT
                    kb = view_manager.keyboard
                    kb.reset()
                    labels = [_T("Original Price", lang), _T("Discount %", lang)]
                    kb.title = labels[view_manager.calc_selected]
                    kb.response = char
                    kb.run(force=True)
                    kb.run(force=True)
                    view_manager.keyboard_just_opened = True
                    del labels, kb
            input_manager.reset()
            
        if dirty and getattr(view_manager, 'custom_app_state', STATE_CALC_DISCOUNT) == STATE_CALC_DISCOUNT:
            view_manager.store_ui_dirty = False
            _, bg, fg, hl = _get_theme_colors(settings["theme_idx"])
            draw.clear(color=bg)
            
            vec1 = Vector(0, 0)
            vec2 = Vector(320, 26)
            draw.fill_rectangle(vec1, vec2, hl)
            vec1.x = 5; vec1.y = 5
            draw.text(vec1, _T("Discount Calc", lang), bg)
            
            font_size = 1
            labels = [_T("Original Price", lang), _T("Discount %", lang)]
            dec = settings.get("decimals", 2)
            curr = settings.get("currency", "$")
            dp = settings.get("dec_point", ".")
            
            y = 40
            for i in range(2):
                if i == getattr(view_manager, "calc_selected", 0):
                    draw.fill_rectangle(Vector(0, y - 2), Vector(320, 24), hl)
                    text_color = bg
                else:
                    text_color = fg
                
                draw.text(Vector(10, y), labels[i] + ":", text_color, font_size)
                val = getattr(view_manager, "calc_data", [0.0, 0.0])[i]
                if i == 0:
                    val_str = ("{:." + str(dec) + "f} {}").format(val, curr)
                else:
                    val_str = str(int(val)) + "%" if val == int(val) else f"{val:.2f}".rstrip('0').rstrip('.') + "%"
                vw = draw.len(val_str, font_size)
                draw.text(Vector(310 - vw, y), val_str, text_color, font_size)
                y += 30
                
            draw.line_custom(Vector(10, y), Vector(310, y), fg)
            y += 10
            
            cdata = getattr(view_manager, "calc_data", [0.0, 0.0])
            price, disc = cdata[0], cdata[1]
            
            saved = price * (disc / 100.0)
            final = price - saved
            
            draw.text(Vector(10, y), _T("Final Price:", lang), fg, font_size)
            res_str = ("{:." + str(dec) + "f}").format(final).replace('.', dp) + f" {curr}"
            res_w = draw.len(res_str, font_size)
            draw.text(Vector(310 - res_w, y), res_str, hl, font_size)
            
            y += 30
            draw.text(Vector(10, y), _T("You Save:", lang), fg, font_size)
            save_str = ("{:." + str(dec) + "f}").format(saved).replace('.', dp) + f" {curr}"
            save_w = draw.len(save_str, font_size)
            draw.text(Vector(310 - save_w, y), save_str, hl, font_size)
            
            draw.swap()

    elif state == STATE_CALC_UNIT_CONVERT:
        dirty = getattr(view_manager, "store_ui_dirty", True)
        units = ["g", "kg", "oz", "lb", "ml", "L", "fl oz", "gal"]
        
        if button != -1:
            dirty = True
            if button == BUTTON_UP:
                view_manager.calc_selected = (view_manager.calc_selected - 1) % 3
            elif button == BUTTON_DOWN:
                view_manager.calc_selected = (view_manager.calc_selected + 1) % 3
            elif button == BUTTON_LEFT:
                if view_manager.calc_selected == 1:
                    view_manager.calc_data[1] = (view_manager.calc_data[1] - 1) % len(units)
                elif view_manager.calc_selected == 2:
                    view_manager.calc_data[2] = (view_manager.calc_data[2] - 1) % len(units)
            elif button == BUTTON_RIGHT:
                if view_manager.calc_selected == 1:
                    view_manager.calc_data[1] = (view_manager.calc_data[1] + 1) % len(units)
                elif view_manager.calc_selected == 2:
                    view_manager.calc_data[2] = (view_manager.calc_data[2] + 1) % len(units)
            elif button == BUTTON_CENTER:
                if view_manager.calc_selected == 0:
                    input_manager.reset()
                    view_manager.custom_app_state = STATE_KEYBOARD_UNIT_CONVERT
                    kb = view_manager.keyboard
                    kb.reset()
                    kb.title = _T("Value", lang)
                    kb.response = str(view_manager.calc_data[0]).replace('.', settings.get("dec_point", "."))
                    kb.run(force=True)
                    kb.run(force=True)
                    view_manager.keyboard_just_opened = True
                    del kb
            elif button == BUTTON_BACK:
                view_manager.custom_app_state = STATE_MENU_CALCULATORS
                _, bg, _, _ = _get_theme_colors(settings["theme_idx"])
                draw.clear(color=bg)
                view_manager.custom_app_menu = _build_calculators_menu(view_manager)
                view_manager.custom_app_menu.draw()
                draw.swap()
            else:
                if view_manager.calc_selected == 0:
                    char = input_manager.button_to_char(button)
                    if char and char in "0123456789.,":
                        input_manager.reset()
                        view_manager.custom_app_state = STATE_KEYBOARD_UNIT_CONVERT
                        kb = view_manager.keyboard
                        kb.reset()
                        kb.title = _T("Value", lang)
                        kb.response = char
                        kb.run(force=True)
                        kb.run(force=True)
                        view_manager.keyboard_just_opened = True
                        del kb
            input_manager.reset()
            
        if dirty and getattr(view_manager, 'custom_app_state', STATE_CALC_UNIT_CONVERT) == STATE_CALC_UNIT_CONVERT:
            view_manager.store_ui_dirty = False
            _, bg, fg, hl = _get_theme_colors(settings["theme_idx"])
            draw.clear(color=bg)
            
            vec1 = Vector(0, 0)
            vec2 = Vector(320, 26)
            draw.fill_rectangle(vec1, vec2, hl)
            vec1.x = 5; vec1.y = 5
            draw.text(vec1, _T("Unit Converter", lang), bg)
            
            font_size = 1
            labels = [_T("Value", lang), _T("From", lang), _T("To", lang)]
            dp = settings.get("dec_point", ".")
            
            y = 40
            for i in range(3):
                if i == getattr(view_manager, "calc_selected", 0):
                    draw.fill_rectangle(Vector(0, y - 2), Vector(320, 24), hl)
                    text_color = bg
                else:
                    text_color = fg
                
                draw.text(Vector(10, y), labels[i] + ":", text_color, font_size)
                cdata = getattr(view_manager, "calc_data", [1.0, 0, 1])
                if i == 0:
                    val = cdata[0]
                    num_str = str(int(val)) if val == int(val) else f"{val:.5f}".rstrip('0').rstrip('.')
                    val_str = num_str.replace('.', dp)
                elif i == 1:
                    val_str = f"< {units[cdata[1]]} >"
                else:
                    val_str = f"< {units[cdata[2]]} >"
                    
                vw = draw.len(val_str, font_size)
                draw.text(Vector(310 - vw, y), val_str, text_color, font_size)
                y += 30
                
            draw.line_custom(Vector(10, y), Vector(310, y), fg)
            y += 10
            
            cdata = getattr(view_manager, "calc_data", [1.0, 0, 1])
            val, from_idx, to_idx = cdata[0], cdata[1], cdata[2]
            mults = [1.0, 1000.0, 28.3495, 453.592, 1.0, 1000.0, 29.5735, 3785.41]
            
            res = val * (mults[from_idx] / mults[to_idx])
            
            draw.text(Vector(10, y), _T("Result:", lang), fg, font_size)
            num_str = str(int(res)) if res == int(res) else f"{res:.5f}".rstrip('0').rstrip('.')
            res_str = num_str.replace('.', dp) + f" {units[to_idx]}"
            res_w = draw.len(res_str, font_size)
            draw.text(Vector(310 - res_w, y), res_str, hl, font_size)
            draw.swap()

    elif state in (STATE_CALC_RUNNING_TOTAL, STATE_CALC_BOGO, STATE_CALC_BULK, STATE_CALC_TAX, STATE_CALC_SPLIT):
        dirty = getattr(view_manager, "store_ui_dirty", True)
        
        if state == STATE_CALC_RUNNING_TOTAL:
            c_rows, c_title, c_kb, c_lbls = 3, "Running Total", STATE_KEYBOARD_RUNNING_TOTAL, ["Budget", "Add Amount", "Manual Total"]
        elif state == STATE_CALC_BOGO:
            c_rows, c_title, c_kb, c_lbls = 4, "BOGO Calc", STATE_KEYBOARD_BOGO, ["Item Price", "Buy Qty", "Get Qty", "Discount %"]
        elif state == STATE_CALC_BULK:
            c_rows, c_title, c_kb, c_lbls = 2, "Bulk Estimator", STATE_KEYBOARD_BULK, ["Price/Unit", "Est. Weight"]
        elif state == STATE_CALC_TAX:
            c_rows, c_title, c_kb, c_lbls = 2, "Sales Tax", STATE_KEYBOARD_TAX, ["Pre-Tax Price", "Tax %"]
        elif state == STATE_CALC_SPLIT:
            c_rows, c_title, c_kb, c_lbls = 3, "Bill Splitter", STATE_KEYBOARD_SPLIT, ["Total Bill", "People", "Tip %"]
            
        if button != -1:
            dirty = True
            if button == BUTTON_UP:
                view_manager.calc_selected = (view_manager.calc_selected - 1) % c_rows
            elif button == BUTTON_DOWN:
                view_manager.calc_selected = (view_manager.calc_selected + 1) % c_rows
            elif button == BUTTON_CENTER:
                input_manager.reset()
                view_manager.custom_app_state = c_kb
                kb = view_manager.keyboard
                kb.reset()
                kb.title = _T(c_lbls[view_manager.calc_selected], lang)
                if state == STATE_CALC_RUNNING_TOTAL and view_manager.calc_selected == 1:
                    kb.response = ""
                else:
                    kb.response = str(view_manager.calc_data[view_manager.calc_selected]).replace('.', settings.get("dec_point", "."))
                kb.run(force=True)
                kb.run(force=True)
                view_manager.keyboard_just_opened = True
            elif button in (BUTTON_BACK, BUTTON_LEFT):
                view_manager.custom_app_state = STATE_MENU_CALCULATORS
                _, bg, _, _ = _get_theme_colors(settings["theme_idx"])
                draw.clear(color=bg)
                view_manager.custom_app_menu = _build_calculators_menu(view_manager)
                view_manager.custom_app_menu.draw()
                draw.swap()
            else:
                char = input_manager.button_to_char(button)
                if char and char in "0123456789.,":
                    input_manager.reset()
                    view_manager.custom_app_state = c_kb
                    kb = view_manager.keyboard
                    kb.reset()
                    kb.title = _T(c_lbls[view_manager.calc_selected], lang)
                    kb.response = char
                    kb.run(force=True)
                    kb.run(force=True)
                    view_manager.keyboard_just_opened = True
            input_manager.reset()
            
        if dirty and getattr(view_manager, 'custom_app_state', state) == state:
            view_manager.store_ui_dirty = False
            _, bg, fg, hl = _get_theme_colors(settings["theme_idx"])
            draw.clear(color=bg)
            
            vec1 = Vector(0, 0)
            vec2 = Vector(320, 26)
            draw.fill_rectangle(vec1, vec2, hl)
            vec1.x = 5; vec1.y = 5
            draw.text(vec1, _T(c_title, lang), bg)
            
            font_size = 1
            dec = settings.get("decimals", 2)
            curr = settings.get("currency", "$")
            dp = settings.get("dec_point", ".")
            
            y = 40
            cdata = getattr(view_manager, "calc_data", [0.0] * c_rows)
            for i in range(c_rows):
                if i == getattr(view_manager, "calc_selected", 0):
                    draw.fill_rectangle(Vector(0, y - 2), Vector(320, 24), hl)
                    text_color = bg
                else:
                    text_color = fg
                
                draw.text(Vector(10, y), _T(c_lbls[i], lang) + ":", text_color, font_size)
                
                val = cdata[i]
                if state == STATE_CALC_RUNNING_TOTAL and i == 1:
                    val_str = "+ ..."
                elif state == STATE_CALC_RUNNING_TOTAL and i in (0, 2):
                    num_str = ("{:." + str(dec) + "f}").format(val).replace('.', dp)
                    val_str = f"{num_str} {curr}"
                elif state == STATE_CALC_BOGO:
                    if i == 0:
                        num_str = ("{:." + str(dec) + "f}").format(val).replace('.', dp)
                        val_str = f"{num_str} {curr}"
                    elif i == 3:
                        num_str = str(int(val)) if val == int(val) else f"{val:.2f}".rstrip('0').rstrip('.')
                        val_str = num_str.replace('.', dp) + "%"
                    else:
                        num_str = str(int(val)) if val == int(val) else f"{val:.3f}".rstrip('0').rstrip('.')
                        val_str = num_str.replace('.', dp)
                elif state == STATE_CALC_BULK:
                    if i == 0:
                        num_str = ("{:." + str(dec) + "f}").format(val).replace('.', dp)
                        val_str = f"{num_str} {curr}"
                    else:
                        num_str = str(int(val)) if val == int(val) else f"{val:.3f}".rstrip('0').rstrip('.')
                        val_str = num_str.replace('.', dp)
                elif state == STATE_CALC_TAX:
                    if i == 0:
                        num_str = ("{:." + str(dec) + "f}").format(val).replace('.', dp)
                        val_str = f"{num_str} {curr}"
                    else:
                        num_str = str(int(val)) if val == int(val) else f"{val:.2f}".rstrip('0').rstrip('.')
                        val_str = num_str.replace('.', dp) + "%"
                elif state == STATE_CALC_SPLIT:
                    if i == 0:
                        num_str = ("{:." + str(dec) + "f}").format(val).replace('.', dp)
                        val_str = f"{num_str} {curr}"
                    elif i == 1:
                        num_str = str(int(val)) if val == int(val) else f"{val:.3f}".rstrip('0').rstrip('.')
                        val_str = num_str.replace('.', dp)
                    else:
                        num_str = str(int(val)) if val == int(val) else f"{val:.2f}".rstrip('0').rstrip('.')
                        val_str = num_str.replace('.', dp) + "%"
                else:
                    val_str = str(val)
                    
                vw = draw.len(val_str, font_size)
                draw.text(Vector(310 - vw, y), val_str, text_color, font_size)
                y += 30
                
            draw.line_custom(Vector(10, y), Vector(310, y), fg)
            y += 10
            
            if state == STATE_CALC_RUNNING_TOTAL:
                res_str1 = ("{:." + str(dec) + "f}").format(cdata[2]).replace('.', dp) + f" {curr}"
                draw.text(Vector(10, y), _T("Current Total:", lang), fg, font_size)
                res_w1 = draw.len(res_str1, font_size)
                draw.text(Vector(310 - res_w1, y), res_str1, hl, font_size)
                
                y += 30
                rem = cdata[0] - cdata[2]
                res_str2 = ("{:." + str(dec) + "f}").format(rem).replace('.', dp) + f" {curr}"
                draw.text(Vector(10, y), _T("Remaining:", lang), fg, font_size)
                res_w2 = draw.len(res_str2, font_size)
                draw.text(Vector(310 - res_w2, y), res_str2, hl if rem >= 0 else 0xF800, font_size)
                
            elif state == STATE_CALC_BOGO:
                price, buy_q, get_q, disc = cdata[0], cdata[1], cdata[2], cdata[3]
                t_items = buy_q + get_q
                if t_items > 0:
                    t_price = (buy_q * price) + (get_q * price * (100.0 - disc) / 100.0)
                    real_p = t_price / t_items
                else:
                    real_p = 0.0
                res_str = ("{:." + str(dec) + "f}").format(real_p).replace('.', dp) + f" {curr}"
                draw.text(Vector(10, y), _T("Real Price/Ea:", lang), fg, font_size)
                res_w = draw.len(res_str, font_size)
                draw.text(Vector(310 - res_w, y), res_str, hl, font_size)
                
            elif state == STATE_CALC_BULK:
                cost = cdata[0] * cdata[1]
                res_str = ("{:." + str(dec) + "f}").format(cost).replace('.', dp) + f" {curr}"
                draw.text(Vector(10, y), _T("Est. Cost:", lang), fg, font_size)
                res_w = draw.len(res_str, font_size)
                draw.text(Vector(310 - res_w, y), res_str, hl, font_size)
                
            elif state == STATE_CALC_TAX:
                cost = cdata[0] * (1.0 + cdata[1] / 100.0)
                res_str = ("{:." + str(dec) + "f}").format(cost).replace('.', dp) + f" {curr}"
                draw.text(Vector(10, y), _T("Total + Tax:", lang), fg, font_size)
                res_w = draw.len(res_str, font_size)
                draw.text(Vector(310 - res_w, y), res_str, hl, font_size)
                
            elif state == STATE_CALC_SPLIT:
                people = cdata[1] if cdata[1] > 0 else 1.0
                cost = (cdata[0] * (1.0 + cdata[2] / 100.0)) / people
                res_str = ("{:." + str(dec) + "f}").format(cost).replace('.', dp) + f" {curr}"
                draw.text(Vector(10, y), _T("Cost per Person:", lang), fg, font_size)
                res_w = draw.len(res_str, font_size)
                draw.text(Vector(310 - res_w, y), res_str, hl, font_size)

            draw.swap()

def _handle_help(view_manager):
    input_manager = view_manager.input_manager
    button = input_manager.button
    draw = view_manager.draw
    settings = view_manager.grocery_settings
    lang = settings.get("lang", "en")
    state = getattr(view_manager, 'custom_app_state', STATE_MENU_SHOPPING)

    if state == STATE_VIEW_HELP:
        textbox = getattr(view_manager, "custom_app_textbox", None)
        if textbox and button != -1:
            if button == BUTTON_UP:
                textbox.scroll_up()
            elif button == BUTTON_DOWN:
                textbox.scroll_down()
            elif button in (BUTTON_BACK, BUTTON_LEFT):
                ret_state = getattr(view_manager, "help_return_state", STATE_MENU_SHOPPING)
                view_manager.custom_app_state = ret_state
                if hasattr(view_manager, "help_return_state"):
                    del view_manager.help_return_state
                del view_manager.custom_app_textbox
                
                _, bg, _, _ = _get_theme_colors(settings["theme_idx"])
                draw.clear(color=bg)
                
                if ret_state == STATE_VIEW_LIST:
                    view_manager.store_ui_dirty = True
                elif hasattr(view_manager, "custom_app_menu"):
                    view_manager.custom_app_menu.draw()
                    draw.swap()
            input_manager.reset()
        del textbox

def _handle_keyboards(view_manager):
    """
    Intercepts keyboard sessions. Retrieves user input when the system keyboard
    closes and applies the values directly to the invoking states.
    """
    input_manager = view_manager.input_manager
    button = input_manager.button
    draw = view_manager.draw
    settings = view_manager.grocery_settings
    lang = settings.get("lang", "en")
    state = getattr(view_manager, 'custom_app_state', STATE_MENU_SHOPPING)

    if state in (STATE_KEYBOARD_NEW_LIST, STATE_KEYBOARD_ADD_ITEM, STATE_KEYBOARD_EDIT_ITEM, STATE_KEYBOARD_CLONE_LIST, STATE_KEYBOARD_RENAME_IN_STORE, STATE_KEYBOARD_ADD_IN_STORE, STATE_KEYBOARD_DUPLICATE_ITEM, STATE_KEYBOARD_PRICE_COMPARE, STATE_KEYBOARD_DISCOUNT, STATE_KEYBOARD_UNIT_CONVERT, STATE_KEYBOARD_RUNNING_TOTAL, STATE_KEYBOARD_BOGO, STATE_KEYBOARD_BULK, STATE_KEYBOARD_TAX, STATE_KEYBOARD_SPLIT):
        if getattr(view_manager, "keyboard_just_opened", False):
            if button == BUTTON_CENTER:
                input_manager.reset()
            else:
                view_manager.keyboard_just_opened = False
                
        kb = view_manager.keyboard
        if not kb.run(): # User pressed BACK inside the keyboard to cancel
            kb.reset()
            if state == STATE_KEYBOARD_NEW_LIST:
                _switch_menu(view_manager, STATE_MENU_SHOPPING, _build_shopping_menu)
            elif state == STATE_KEYBOARD_ADD_ITEM:
                _switch_menu(view_manager, STATE_MENU_RECENT_ITEMS, _build_recent_items_menu)
            elif state in (STATE_KEYBOARD_EDIT_ITEM, STATE_KEYBOARD_DUPLICATE_ITEM):
                list_name = getattr(view_manager, "active_list_name", "")
                _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name)
                del list_name
            elif state == STATE_KEYBOARD_CLONE_LIST:
                list_name = getattr(view_manager, "active_list_name", "")
                _switch_menu(view_manager, STATE_MENU_SPECIFIC_LIST, _build_specific_list_menu, list_name)
                del list_name
            elif state in (STATE_KEYBOARD_RENAME_IN_STORE, STATE_KEYBOARD_ADD_IN_STORE):
                view_manager.custom_app_state = STATE_VIEW_LIST
                view_manager.store_ui_dirty = True
            elif state == STATE_KEYBOARD_PRICE_COMPARE:
                view_manager.custom_app_state = STATE_CALC_PRICE_COMPARE
                view_manager.store_ui_dirty = True
            elif state == STATE_KEYBOARD_DISCOUNT:
                view_manager.custom_app_state = STATE_CALC_DISCOUNT
                view_manager.store_ui_dirty = True
            elif state == STATE_KEYBOARD_UNIT_CONVERT:
                view_manager.custom_app_state = STATE_CALC_UNIT_CONVERT
                view_manager.store_ui_dirty = True
            elif state == STATE_KEYBOARD_RUNNING_TOTAL:
                view_manager.custom_app_state = STATE_CALC_RUNNING_TOTAL
                view_manager.store_ui_dirty = True
            elif state == STATE_KEYBOARD_BOGO:
                view_manager.custom_app_state = STATE_CALC_BOGO
                view_manager.store_ui_dirty = True
            elif state == STATE_KEYBOARD_BULK:
                view_manager.custom_app_state = STATE_CALC_BULK
                view_manager.store_ui_dirty = True
            elif state == STATE_KEYBOARD_TAX:
                view_manager.custom_app_state = STATE_CALC_TAX
                view_manager.store_ui_dirty = True
            elif state == STATE_KEYBOARD_SPLIT:
                view_manager.custom_app_state = STATE_CALC_SPLIT
                view_manager.store_ui_dirty = True
        elif kb.is_finished:
            if state == STATE_KEYBOARD_NEW_LIST:
                name = kb.response.strip()
                if name:
                    name = name.replace("/", "-").replace("\\", "-")
                    if name.lower() != "__pantry__":
                        path = f"picoware/grocery/lists/{name}.json"
                        if not view_manager.storage.exists(path):
                            view_manager.storage.deserialize([], path)
                        else:
                            view_manager.alert(_T("List already exists!", lang), False)
                kb.reset()
                _switch_menu(view_manager, STATE_MENU_SHOPPING, _build_shopping_menu)
                del name
            elif state == STATE_KEYBOARD_ADD_ITEM:
                item = kb.response.strip()
                list_name = getattr(view_manager, "active_list_name", "")
                if item and list_name:
                    path = f"picoware/grocery/lists/{list_name}.json"
                    try:
                        data = view_manager.storage.serialize(path)
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
                        
                    view_manager.storage.deserialize(data, path)
                    _update_recent_history(view_manager, item)
                    print(f"[DEBUG] Saved item '{item}' to '{list_name}'")
                    if found:
                        view_manager.alert(_T("Item already in list!\nQuantity increased.", lang), False)
                    del data, path
                kb.reset()
                _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name)
                del item, list_name
            elif state == STATE_KEYBOARD_EDIT_ITEM:
                item_name = kb.response.strip()
                list_name = getattr(view_manager, "active_list_name", "")
                item_idx = getattr(view_manager, "active_item_idx", 0)
                
                if item_name and list_name:
                    path = f"picoware/grocery/lists/{list_name}.json"
                    try:
                        data = view_manager.storage.serialize(path)
                        if isinstance(data, list) and item_idx < len(data):
                            if isinstance(data[item_idx], dict):
                                data[item_idx]["n"] = item_name
                            else:
                                data[item_idx] = {"n": item_name, "q": 1, "c": False}
                            view_manager.storage.deserialize(data, path)
                            _update_recent_history(view_manager, item_name)
                    except Exception:
                        pass
                        
                kb.reset()
                _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name)
                del item_name, list_name
            elif state == STATE_KEYBOARD_DUPLICATE_ITEM:
                new_name = kb.response.strip()
                list_name = getattr(view_manager, "active_list_name", "")
                item_idx = getattr(view_manager, "active_item_idx", 0)
                offset = 5 if list_name == "__Pantry__" else 7
                target_idx = item_idx + offset
                
                if new_name and list_name:
                    path = f"picoware/grocery/lists/{list_name}.json"
                    try:
                        data = view_manager.storage.serialize(path)
                        if isinstance(data, list) and item_idx < len(data):
                            old_name = data[item_idx].get("n", "") if isinstance(data[item_idx], dict) else str(data[item_idx])
                            if new_name.lower() != old_name.lower():
                                new_item = {"n": new_name, "q": 1, "c": False}
                                data.insert(item_idx + 1, new_item)
                                view_manager.storage.deserialize(data, path)
                                _update_recent_history(view_manager, new_name)
                                target_idx += 1
                    except Exception:
                        pass
                        
                kb.reset()
                _switch_menu(view_manager, STATE_MENU_EDIT_LIST, _build_edit_list_menu, list_name, selected=target_idx)
                del new_name, list_name, target_idx
            elif state == STATE_KEYBOARD_CLONE_LIST:
                new_name = kb.response.strip()
                list_name = getattr(view_manager, "active_list_name", "")
                if new_name and list_name and new_name.lower() != list_name.lower() and new_name.lower() != "__pantry__":
                    new_name = new_name.replace("/", "-").replace("\\", "-")
                    path = f"picoware/grocery/lists/{list_name}.json"
                    new_path = f"picoware/grocery/lists/{new_name}.json"
                    if not view_manager.storage.exists(new_path):
                        try:
                            data = view_manager.storage.serialize(path)
                            if isinstance(data, list):
                                for item in data:
                                    if isinstance(item, dict): item["c"] = False
                                view_manager.storage.deserialize(data, new_path)
                        except Exception: pass
                    else:
                        view_manager.alert(_T("List already exists!", lang), False)
                kb.reset()
                _switch_menu(view_manager, STATE_MENU_SHOPPING, _build_shopping_menu)
                del new_name, list_name
            elif state == STATE_KEYBOARD_RENAME_IN_STORE:
                item_name = kb.response.strip()
                list_name = getattr(view_manager, "active_list_name", "")
                item_idx = getattr(view_manager, "store_idx", 0)
                
                if item_name and list_name:
                    path = f"picoware/grocery/lists/{list_name}.json"
                    try:
                        data = view_manager.storage.serialize(path)
                        if isinstance(data, list) and item_idx < len(data):
                            if isinstance(data[item_idx], dict):
                                data[item_idx]["n"] = item_name
                            else:
                                data[item_idx] = {"n": item_name, "q": 1, "c": False}
                            view_manager.storage.deserialize(data, path)
                            _update_recent_history(view_manager, item_name)
                            view_manager.store_data = data
                    except Exception:
                        pass
                        
                kb.reset()
                view_manager.custom_app_state = STATE_VIEW_LIST
                view_manager.store_ui_dirty = True
                del item_name, list_name
            elif state == STATE_KEYBOARD_ADD_IN_STORE:
                item = kb.response.strip()
                list_name = getattr(view_manager, "active_list_name", "")
                if item and list_name:
                    path = f"picoware/grocery/lists/{list_name}.json"
                    try:
                        data = view_manager.storage.serialize(path)
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
                        
                    data.sort(key=lambda x: x.get("c", False) if isinstance(x, dict) else False)
                    view_manager.storage.deserialize(data, path)
                    _update_recent_history(view_manager, item)
                    view_manager.store_data = data
                    if found:
                        view_manager.alert(_T("Item already in list!\nQuantity increased.", lang), False)
                    del data, path
                kb.reset()
                view_manager.custom_app_state = STATE_VIEW_LIST
                view_manager.store_ui_dirty = True
                del item, list_name
            elif state in (STATE_KEYBOARD_PRICE_COMPARE, STATE_KEYBOARD_DISCOUNT, STATE_KEYBOARD_UNIT_CONVERT, STATE_KEYBOARD_RUNNING_TOTAL, STATE_KEYBOARD_BOGO, STATE_KEYBOARD_BULK, STATE_KEYBOARD_TAX, STATE_KEYBOARD_SPLIT):
                try:
                    val = float(kb.response.strip().replace(',', '.'))
                except ValueError:
                    val = 0.0
                
                if state == STATE_KEYBOARD_PRICE_COMPARE:
                    cdata = getattr(view_manager, "calc_data", [0.0, 1.0, 0, 0.0, 1.0, 0])
                    idx_map = {0: 0, 1: 1, 2: 3, 3: 4}
                    val_idx = idx_map[view_manager.calc_selected]
                    cdata[val_idx] = val
                    view_manager.calc_data = cdata
                    view_manager.custom_app_state = STATE_CALC_PRICE_COMPARE
                elif state == STATE_KEYBOARD_DISCOUNT:
                    view_manager.calc_data[view_manager.calc_selected] = val
                    view_manager.custom_app_state = STATE_CALC_DISCOUNT
                elif state == STATE_KEYBOARD_UNIT_CONVERT:
                    view_manager.calc_data[0] = val
                    view_manager.custom_app_state = STATE_CALC_UNIT_CONVERT
                elif state == STATE_KEYBOARD_RUNNING_TOTAL:
                    if view_manager.calc_selected == 1:
                        view_manager.calc_data[2] += val
                    else:
                        view_manager.calc_data[view_manager.calc_selected] = val
                    view_manager.custom_app_state = STATE_CALC_RUNNING_TOTAL
                elif state == STATE_KEYBOARD_BOGO:
                    view_manager.calc_data[view_manager.calc_selected] = val
                    view_manager.custom_app_state = STATE_CALC_BOGO
                elif state == STATE_KEYBOARD_BULK:
                    view_manager.calc_data[view_manager.calc_selected] = val
                    view_manager.custom_app_state = STATE_CALC_BULK
                elif state == STATE_KEYBOARD_TAX:
                    view_manager.calc_data[view_manager.calc_selected] = val
                    view_manager.custom_app_state = STATE_CALC_TAX
                elif state == STATE_KEYBOARD_SPLIT:
                    view_manager.calc_data[view_manager.calc_selected] = val
                    view_manager.custom_app_state = STATE_CALC_SPLIT
                    
                kb.reset()
                view_manager.store_ui_dirty = True
        del kb

def run(view_manager):
    state = getattr(view_manager, 'custom_app_state', STATE_MENU_SHOPPING)
    if state in (STATE_MENU_SHOPPING, STATE_MENU_SETTINGS, STATE_MENU_SPECIFIC_LIST, STATE_MENU_EDIT_LIST, STATE_MENU_EDIT_ITEM, STATE_MENU_RECENT_ITEMS, STATE_MENU_CALCULATORS):
        _handle_menus(view_manager)
    elif state == STATE_VIEW_LIST:
        _handle_store(view_manager)
    elif state in (STATE_CONFIRM_EXIT_STORE, STATE_CONFIRM_DELETE_LIST, STATE_CONFIRM_DELETE_ITEM, STATE_CONFIRM_UNCHECK_ALL, STATE_CONFIRM_CLEAR_CHECKED, STATE_CONFIRM_CLEAR_ALL_ITEMS, STATE_CONFIRM_TRANSFER_PANTRY):
        _handle_confirmations(view_manager)
    elif state in (STATE_CALC_PRICE_COMPARE, STATE_CALC_DISCOUNT, STATE_CALC_UNIT_CONVERT, STATE_CALC_RUNNING_TOTAL, STATE_CALC_BOGO, STATE_CALC_BULK, STATE_CALC_TAX, STATE_CALC_SPLIT):
        _handle_calculators(view_manager)
    elif state == STATE_VIEW_HELP:
        _handle_help(view_manager)
    elif state in (STATE_KEYBOARD_NEW_LIST, STATE_KEYBOARD_ADD_ITEM, STATE_KEYBOARD_EDIT_ITEM, STATE_KEYBOARD_CLONE_LIST, STATE_KEYBOARD_RENAME_IN_STORE, STATE_KEYBOARD_ADD_IN_STORE, STATE_KEYBOARD_DUPLICATE_ITEM, STATE_KEYBOARD_PRICE_COMPARE, STATE_KEYBOARD_DISCOUNT, STATE_KEYBOARD_UNIT_CONVERT, STATE_KEYBOARD_RUNNING_TOTAL, STATE_KEYBOARD_BOGO, STATE_KEYBOARD_BULK, STATE_KEYBOARD_TAX, STATE_KEYBOARD_SPLIT):
        _handle_keyboards(view_manager)

def stop(view_manager):
    """
    Handles application teardown, deletes custom objects, and clears RAM.
    """
    
    global _CURRENT_VM
    _CURRENT_VM = view_manager
    
    settings = getattr(view_manager, 'grocery_settings', None)
    theme_idx = settings["theme_idx"] if settings else 0
    _, bg, _, _ = _get_theme_colors(theme_idx)
    # Clear the screen before releasing control
    draw = view_manager.draw
    draw.clear(color=bg)
    draw.swap()
    
    # Restore original input mapper
    if hasattr(view_manager, 'grocery_orig_mapper'):
        view_manager.input_manager._key_to_button = view_manager.grocery_orig_mapper
        delattr(view_manager, 'grocery_orig_mapper')
        
    # Detach and delete all custom objects attached to view_manager to free memory
    attrs_to_clean = [
        'custom_app_menu', 'custom_app_textbox', 'custom_app_state',
        'grocery_settings', 'grocery_translations', 'active_list_name', 'store_data',
        'store_idx', 'store_scroll', 'store_ui_dirty', 'store_pantry_counts',
        'store_exit_choice_state', 'active_item_idx', 'active_item_name',
        'keyboard_just_opened', 'grocery_orig_mapper', 'help_return_state',
        'clear_checked_return_state', 'transfer_pantry_return_state',
        'calc_data', 'calc_selected'
    ]
    
    for attr in attrs_to_clean:
        if hasattr(view_manager, attr):
            delattr(view_manager, attr)
        
    # Clean up local variables
    del draw, bg
    
    _CURRENT_VM = None
    
    # Final garbage collection sweep
    from gc import collect
    collect()
