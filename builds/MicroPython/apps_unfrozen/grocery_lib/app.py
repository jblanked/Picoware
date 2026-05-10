import sys
from grocery_lib.storage import flush_metadata
from grocery_lib.i18n import translate

class GroceryApp:
    def __init__(self, view_manager, loading=None):
        self.view_manager = view_manager
        self.current_view = None
        self.current_view_name = None
        
        if loading: loading.animate()

        # State
        from grocery_lib.config import get_config
        self.active_list = get_config("active_list")
        self._pending_item_idx = None
        self._last_main_view = None
        self._dialog_return_view = None
        self._temp_edit_item = None
        self._temp_edit_idx = None
        self._view_indices = {}
        self._temp_save_data = None
        
        self._parent_map = {
            "shopping_list": "main_menu",
            "add_item": "main_menu",
            "pantry": "main_menu",
            "calculators": "main_menu",
            "settings": "main_menu",
            "list_items": "shopping_list",
            "list_properties": "shopping_list",
            "item_properties": "list_items",
            "pantry_edit": "pantry",
            "quick_calc": "calculators",
            "compare_price": "calculators",
            "bulk_calc": "calculators",
            "settings_aisles": "settings",
            "reset_menu": "settings"
        }
        
        if loading: loading.animate()

        # Prime storage
        from grocery_lib.storage import GroceryStorage
        self.storage = GroceryStorage()
        
        if loading: loading.animate()

        # Load Config & Lang
        from grocery_lib.config import load_config
        cfg = load_config()
        from grocery_lib.i18n import load_language
        load_language(cfg.get("language", "en"))

        if loading: loading.animate()

    def _initial_boot(self):
        self._switch_view("main_menu")
        from grocery_lib.config import get_config, set_config
        if get_config("show_welcome"):
            from grocery_lib.dialog_view import DialogView
            self._dialog_return_view = "main_menu"
            self.current_view = DialogView(self.view_manager, self, translate("welcome_title"), translate("welcome_msg"))
            self.current_view_name = "add_dialog"
            set_config("show_welcome", False)

    def sync_data(self):
        self.storage.sync()
        flush_metadata()

    def _save_current_state(self):
        """Save state (index, etc) of current view before switching."""
        if self.current_view and hasattr(self.current_view, "_selected_index"):
            key = self.current_view_name
            if key == "list_items": key += "_" + str(self.active_list)
            self._view_indices[key] = self.current_view._selected_index
            
        if self.current_view and hasattr(self.current_view, "stop"):
            self.current_view.stop()

    def _switch_view(self, name):
        if self.current_view_name == name: return
        
        # Ensure help/dialogs know where they came from
        if name in ("help", "dialog", "add_dialog"):
            self._dialog_return_view = self.current_view_name
        elif self.current_view_name not in ("help", "dialog", "add_dialog", "quick_calc", "list_items"):
            # Update the return target for F4/F5 toggle
            self._last_main_view = self.current_view_name

        self._save_current_state()
        
        view_class = None
        if name == "main_menu":
            from grocery_lib.main_menu_view import MainMenuView
            view_class = MainMenuView
        elif name == "shopping_list":
            from grocery_lib.lists_view import ListsView
            view_class = ListsView
        elif name == "list_items":
            from grocery_lib.list_view import ListView
            view_class = ListView
        elif name == "pantry":
            from grocery_lib.pantry_view import PantryView
            view_class = PantryView
        elif name == "settings":
            from grocery_lib.settings_view import SettingsView
            view_class = SettingsView
        elif name == "add_item":
            from grocery_lib.quick_add_view import QuickAddView
            view_class = QuickAddView
        elif name == "pantry_edit":
            from grocery_lib.pantry_edit_view import PantryEditView
            view_class = PantryEditView
        elif name == "item_properties":
            from grocery_lib.item_properties_view import ItemPropertiesView
            view_class = ItemPropertiesView
        elif name == "list_properties":
            from grocery_lib.list_properties_view import ListPropertiesView
            view_class = ListPropertiesView
        elif name == "calculators":
            from grocery_lib.calculators_menu_view import CalculatorsMenuView
            view_class = CalculatorsMenuView
        elif name == "quick_calc":
            from grocery_lib.quick_calc_view import QuickCalcView
            view_class = QuickCalcView
        elif name == "compare_price":
            from grocery_lib.compare_view import CompareView
            view_class = CompareView
        elif name == "bulk_calc":
            from grocery_lib.bulk_calc_view import BulkCalcView
            view_class = BulkCalcView
        elif name == "settings_aisles":
            from grocery_lib.aisle_editor_view import AisleEditorView
            view_class = AisleEditorView
        elif name == "reset_menu":
            from grocery_lib.reset_menu_view import ResetMenuView
            view_class = ResetMenuView
        elif name == "help":
            from grocery_lib.help_view import HelpView
            view_class = HelpView
        elif name == "dialog":
            from grocery_lib.dialog_view import DialogView
            view_class = DialogView
        
        if not view_class:
            print("[ERROR] app.switch: Unknown", name)
            return

        self.current_view = view_class(self.view_manager, self)
        self.current_view_name = name
        
        # Restore index
        key = name
        if key == "list_items": key += "_" + str(self.active_list)
        if key in self._view_indices and self.current_view and hasattr(self.current_view, "_selected_index"):
            self.current_view._selected_index = self._view_indices[key]
        
        # Force a redraw after index set and configuration
        if hasattr(self.current_view, "_draw"):
            self.current_view._dirty = True
            self.current_view._draw()

    def run(self):
        if not self.current_view: return
        
        btn = self.view_manager.input_manager.button
        if btn == 90: # F4
            self.view_manager.input_manager.reset()
            if self.current_view_name == "list_items":
                target = self._last_main_view if self._last_main_view else "main_menu"
                self._switch_view(target)
            elif self.current_view_name not in ("settings", "settings_aisles", "add_dialog", "dialog"):
                self._last_main_view = self.current_view_name
                self._switch_view("list_items")
            return

        if btn == 91: # F5
            self.view_manager.input_manager.reset()
            if self.current_view_name == "quick_calc":
                target = self._last_main_view if self._last_main_view else "calculators"
                self._switch_view(target)
            elif self.current_view_name not in ("settings", "settings_aisles", "add_dialog", "dialog", "help"):
                self._last_main_view = self.current_view_name
                self._switch_view("quick_calc")
            return

        if btn == 89: # F3
            self.view_manager.input_manager.reset()
            if self.current_view_name == "help":
                self._switch_view(self._dialog_return_view if self._dialog_return_view else "main_menu")
            elif self.current_view_name not in ("add_dialog", "dialog"):
                self._switch_view("help")
            return
            
        old_view_name = self.current_view_name
        old_view = self.current_view
        res = self.current_view.run()
        
        # If view changed internally to a dialog, ensure we know where to return
        if self.current_view_name == "add_dialog" and old_view_name != "add_dialog":
            self._dialog_return_view = old_view_name
            
        if not res: return
        
        # If view changed internally (e.g. by dialog callback), don't process result
        if self.current_view is not old_view:
            return
            
        # Handle Global Navigation
        if res == "HOME":
            self.view_manager.input_manager.reset()
            self._switch_view("main_menu")
        elif res == "EXIT_HELP":
            self.view_manager.input_manager.reset()
            self._switch_view(self._dialog_return_view if self._dialog_return_view else "main_menu")
        elif res == "EXIT_QUICK_CALC":
            self.view_manager.input_manager.reset()
            self._switch_view("calculators")
        elif res == "BACK":
            parent = self._parent_map.get(self.current_view_name, "main_menu")
            self._switch_view(parent)
        elif res == "EXIT":
            self.view_manager.input_manager.reset()
            if self.current_view_name == "main_menu":
                self.view_manager.back()
            elif self.current_view_name == "add_dialog":
                target = self._dialog_return_view if self._dialog_return_view else "main_menu"
                self._switch_view(target)
            elif self.current_view_name == "add_item":
                target = self._last_main_view if self._last_main_view else "main_menu"
                self._switch_view(target)
            else:
                parent = self._parent_map.get(self.current_view_name, "main_menu")
                self._switch_view(parent)
        
        # Handle Specific Actions
        elif res == "add_item":
            self._last_main_view = self.current_view_name
            self._switch_view("add_item")
        elif res == "CREATE_LIST":
            from grocery_lib.add_view import AddView
            self._dialog_return_view = self.current_view_name
            self._save_current_state()
            self.current_view = AddView(self.view_manager, self, translate("create_list"), self._on_list_created)
            self.current_view_name = "add_dialog"
        elif res == "OPEN_LIST":
            self._switch_view("list_items")
        elif res == "PROPERTIES":
            self._switch_view("list_properties")
        elif res == "ADD_ITEM":
            self._pending_item_idx = None
            self._switch_view("item_properties")
        elif res == "EDIT_ITEM":
            self._switch_view("item_properties")
        elif res == "ADD_PANTRY_ITEM":
            self._pending_item_idx = None
            self._switch_view("pantry_edit")
        elif res == "EDIT_PANTRY_ITEM":
            self._pending_item_idx = self.current_view._selected_index - 1
            self._switch_view("pantry_edit")
        elif res == "ADD_ONE_OFF":
            from grocery_lib.add_view import AddView
            self._dialog_return_view = self.current_view_name
            self._save_current_state()
            self.current_view = AddView(self.view_manager, self, translate("new_one_off"), self._on_one_off_name)
            self.current_view_name = "add_dialog"
        elif res == "ADD_PANTRY_NAME":
            from grocery_lib.add_view import AddView
            self._dialog_return_view = self.current_view_name
            self._save_current_state()
            self.current_view = AddView(self.view_manager, self, translate("add_item"), self._on_pantry_item_added)
            self.current_view_name = "add_dialog"
        elif res == "ADD_AISLE":
            from grocery_lib.add_view import AddView
            self._dialog_return_view = self.current_view_name
            self._save_current_state()
            self.current_view = AddView(self.view_manager, self, translate("add_item"), self._on_aisle_added)
            self.current_view_name = "add_dialog"
        elif res == "SAVE_BEST_DEAL":
            self._start_best_deal_flow()
        elif res == "DELETE_LIST":
            try:
                self.storage.remove_list(self.active_list)
                self._switch_view("shopping_list")
            except OSError:
                self._show_error(translate("err_storage"))
        elif res.startswith("EDIT_"):
            # Settings handling
            self._handle_settings_edit(res[5:])
        else:
            # Try to switch directly
            self._switch_view(res.lower())

    def _start_best_deal_flow(self):
        from grocery_lib.add_view import AddView
        self._dialog_return_view = self.current_view_name
        self._save_current_state()
        
        # Step 1: Name
        view = AddView(self.view_manager, self, translate("name"), self._on_best_deal_name)
        view.input_text = translate("best_value")
        view._cursor_pos = len(view.input_text)
        self.current_view = view
        self.current_view_name = "add_dialog"

    def _on_best_deal_name(self, name):
        self._temp_save_data["name"] = name
        # Step 2: One-off vs Pantry
        from grocery_lib.aisle_select_view import AisleSelectView
        opts = [translate("one_off_short"), translate("pantry_short")]
        self.current_view = AisleSelectView(self.view_manager, self, None, self._on_best_deal_type, opts, translate("save_as"))
        self.current_view_name = "add_dialog"

    def _on_best_deal_type(self, val):
        if val == translate("pantry_short"):
            # Step 3: Category
            from grocery_lib.aisle_select_view import AisleSelectView
            self.current_view = AisleSelectView(self.view_manager, self, "other", self._on_best_deal_finish)
            self.current_view_name = "add_dialog"
        else:
            self._on_best_deal_finish("other", False)

    def _on_best_deal_finish(self, category, is_pantry=True):
        data = self._temp_save_data
        name = data["name"]
        price = data["price"]
        size = data["size"]
        
        # Save to List
        self.storage.add_item(self.active_list, name, 1, price, size, category)
        
        # Save to Pantry if requested
        if is_pantry:
            self.storage.add_pantry_item(name, 1, price, category)
            
        self._temp_save_data = None
        self._switch_view(self._dialog_return_view if self._dialog_return_view else "main_menu")

    def _on_list_created(self, name):
        try:
            self.storage.create_list(name)
        except OSError:
            self._show_error(translate("err_storage"))

    def _on_one_off_name(self, name):
        if not name: return
        self._temp_save_data = {"name": name}
        from grocery_lib.add_view import AddView
        self.current_view = AddView(self.view_manager, self, translate("price"), self._on_one_off_price, is_numeric=True)
        self.current_view_name = "add_dialog"

    def _on_one_off_price(self, val):
        from grocery_lib.format_utils import parse_price
        price = parse_price(val)
        name = self._temp_save_data["name"]
        try:
            self.storage.add_item(self.active_list, name, 1, price)
        except OSError:
            self._show_error(translate("err_storage"))
        self._temp_save_data = None
        self._switch_view(self._dialog_return_view if self._dialog_return_view else "list_items")

    def _on_pantry_item_added(self, name):
        if not name: return
        self._temp_save_data = {"name": name}
        from grocery_lib.add_view import AddView
        self.current_view = AddView(self.view_manager, self, translate("price"), self._on_pantry_item_price, is_numeric=True)
        self.current_view_name = "add_dialog"

    def _on_pantry_item_price(self, val):
        from grocery_lib.format_utils import parse_price
        price = parse_price(val)
        name = self._temp_save_data["name"]
        try:
            self.storage.add_pantry_item(name, 1, price)
        except OSError:
            self._show_error(translate("err_storage"))
        self._temp_save_data = None
        self._switch_view(self._dialog_return_view if self._dialog_return_view else "pantry")

    def _on_aisle_added(self, name):
        from grocery_lib.config import get_config, set_config
        cats = list(get_config("categories"))
        if name and name not in cats:
            cats.append(name)
            set_config("categories", cats)

    def _on_budget_set(self, val):
        from grocery_lib.config import set_config
        try:
            val = val.replace(",", ".")
            set_config("base_budget", float(val))
        except (ValueError, TypeError):
            pass

    def _show_error(self, msg):
        from grocery_lib.dialog_view import DialogView
        self.current_view = DialogView(self.view_manager, self, translate("error"), msg)
        self.current_view_name = "dialog"

    def _handle_settings_edit(self, key):
        from grocery_lib.config import set_config, get_config
        key = key.lower()
        if key == "aisles":
            self._switch_view("settings_aisles")
        elif key == "reset":
            self._switch_view("reset_menu")
        elif key == "base_budget":
            from grocery_lib.add_view import AddView
            self._dialog_return_view = "settings"
            self._save_current_state()
            self.current_view = AddView(self.view_manager, self, translate("base_budget"), self._on_budget_set)
            self.current_view_name = "add_dialog"
        elif key == "language":
            cur = get_config("language")
            new_val = "de" if cur == "en" else "en"
            set_config("language", new_val)
            from grocery_lib.i18n import load_language
            load_language(new_val)
            if self.current_view:
                if hasattr(self.current_view, "refresh_ui"):
                    self.current_view.refresh_ui()
                self.current_view._dirty = True
        elif key == "currency":
            cur = get_config("currency")
            opts = ["dollar", "euro"]
            try:
                new_val = opts[(opts.index(cur) + 1) % len(opts)]
            except ValueError:
                new_val = opts[0]
            set_config("currency", new_val)
            if self.current_view: self.current_view._dirty = True
        elif key == "tax_region":
            cur = get_config("tax_region")
            opts = ["DE", "US", "UK"]
            try:
                new_val = opts[(opts.index(cur) + 1) % len(opts)]
            except ValueError:
                new_val = opts[0]
            set_config("tax_region", new_val)
            if self.current_view: self.current_view._dirty = True
        elif key == "decimal_separator":
            cur = get_config("decimal_separator")
            new_val = "," if cur == "." else "."
            set_config("decimal_separator", new_val)
            # Update sep in current view if it has it
            if self.current_view:
                if hasattr(self.current_view, "sep"):
                    self.current_view.sep = new_val
                self.current_view._dirty = True

    def stop(self):
        self.sync_data()
