from grocery_lib.menu_view import MenuView
from grocery_lib.i18n import translate

class MainMenuView(MenuView):
    """Specialized main menu for the Grocery App."""
    __slots__ = ()
    def __init__(self, view_manager, app):
        items = [
            translate("shopping_list"),
            translate("add_item"),
            translate("pantry"),
            translate("calculators"),
            translate("settings")
        ]
        item_keys = ["shopping_list", "add_item", "pantry", "calculators", "settings"]

        super().__init__(
            view_manager, 
            app, 
            translate("app_name"), 
            items, 
            item_keys,
            hint=translate("hint")
        )

