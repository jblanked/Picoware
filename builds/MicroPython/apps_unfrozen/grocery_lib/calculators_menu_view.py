from grocery_lib.menu_view import MenuView
from grocery_lib.i18n import translate

class CalculatorsMenuView(MenuView):
    """View for selecting which grocery calculator to use."""
    __slots__ = ()
    def __init__(self, view_manager, app):
        items = [
            translate("quick_calc"),
            translate("compare_price"),
            translate("bulk_calc")
        ]
        item_keys = ["quick_calc", "compare_price", "bulk_calc"]
        
        super().__init__(
            view_manager, 
            app, 
            translate("calculators"), 
            items, 
            item_keys,
            hint=translate("hint")
        )
