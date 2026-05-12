from grocery_lib.i18n import translate
from grocery_lib.ui_utils import draw_header, draw_footer, draw_card, draw_icon, C_BG, C_TEXT, C_PAPER, C_ACCENT
from grocery_lib.base_view import BaseView
from grocery_lib.config import get_config
from grocery_lib.format_utils import format_price
from micropython import const
from picoware.system.vector import Vector

_BAR_H = const(24)
_MARGIN = const(4)
_SPACING = const(4)
_ITEM_H = const(32)
_CARD_RADIUS = const(6)

class ListsView(BaseView):
    """View for managing multiple shopping lists."""
    __slots__ = ("all_lists", "list_counts", "filtered_indices", "_selected_index", "_scroll_offset", "_max_visible", "_card_size", "_last_idx")

    def __init__(self, view_manager, app):
        super().__init__(view_manager, app)
        self._selected_index = 0
        self._scroll_offset = 0
        self._last_idx = 0
        
        available_h = self.draw.size.y - (_BAR_H * 2) - (_MARGIN * 2)
        self._max_visible = available_h // (_ITEM_H + _SPACING)
        self._card_size = Vector(self.draw.size.x - (_MARGIN * 2), _ITEM_H)
        
        self.refresh_data()
        self._draw(True)

    def refresh_data(self):
        self.all_lists = self.app.storage.get_list_names(True)
        self.list_counts = self.app.storage.get_all_list_counts(True)
        self.filtered_indices = list(range(len(self.all_lists)))

    def _draw(self, full=False):
        if not self._dirty and not full: return
        
        start_y = _BAR_H + _MARGIN
        new_offset = self.handle_scroll(self._selected_index, self._scroll_offset, self._max_visible)
        
        show_add = len(self.all_lists) < 10
        total_items = len(self.all_lists) + (1 if show_add else 0)
        
        if full or new_offset != self._scroll_offset:
            self._scroll_offset = new_offset
            self.draw.fill_screen(C_BG)
            draw_header(self.draw, translate("my_lists"), _BAR_H)
            
            budgets = get_config("list_budgets")
            base_budget = get_config("base_budget")
            currency = get_config("currency")
            sep = get_config("decimal_separator")
            label_create = translate("create_list")
            
            for i in range(self._scroll_offset, min(total_items, self._scroll_offset + self._max_visible)):
                self._draw_row(i, start_y, show_add, budgets, base_budget, currency, label_create, sep)
            
            # Scrollbar
            from grocery_lib.ui_utils import draw_scrollbar
            draw_scrollbar(self.draw, total_items, self._max_visible, self._scroll_offset, start_y, self.draw.size.y - (_BAR_H * 2) - _MARGIN)
                
            draw_footer(self.draw, translate("hint_lists"), _BAR_H)
        else:
            # Surgical redraw
            budgets = get_config("list_budgets")
            base_budget = get_config("base_budget")
            currency = get_config("currency")
            sep = get_config("decimal_separator")
            label_create = translate("create_list")
            self._draw_row(self._last_idx, start_y, show_add, budgets, base_budget, currency, label_create, sep)
            self._draw_row(self._selected_index, start_y, show_add, budgets, base_budget, currency, label_create, sep)
            
        self.draw.swap()
        self._last_idx = self._selected_index
        self._dirty = False

    def _draw_row(self, i, start_y, show_add, budgets, base_budget, currency, label_create, sep):
        total_rows = len(self.filtered_indices) + (1 if show_add else 0)
        if i < 0 or i >= total_rows: return
        
        is_selected = (i == self._selected_index)
        y = start_y + (i - self._scroll_offset) * (_ITEM_H + _SPACING)
        pos = self._scratch_pos
        pos.x, pos.y = _MARGIN, y
        
        if show_add and i == 0:
            draw_card(self.draw, pos, self._card_size, _CARD_RADIUS, is_selected)
            draw_icon(self.draw, "add_item", _MARGIN + 12, y + (_ITEM_H - 12) // 2)
            pos.x, pos.y = _MARGIN + 35, y + (_ITEM_H - self.draw.font_size.y) // 2
            self.draw.text(pos, label_create, C_TEXT, 0)
        else:
            draw_card(self.draw, pos, self._card_size, _CARD_RADIUS, is_selected)
            idx = i - (1 if show_add else 0)
            data_idx = self.filtered_indices[idx]
            name = self.all_lists[data_idx]
            
            if name == self.app.active_list:
                hl_color = C_ACCENT
                draw_icon(self.draw, "checkmark", _MARGIN + 10, y + (_ITEM_H - 12) // 2, hl_color)
                text_c = hl_color
            else:
                text_c = C_TEXT
            
            pos.x, pos.y = _MARGIN + 35, y + (_ITEM_H - self.draw.font_size.y) // 2
            stats = self.list_counts.get(name, [0, 0])
            display_text = name + " (" + str(stats[0]) + "/" + str(stats[1]) + ")"
            self.draw.text(pos, display_text, text_c, 0)
            
            budget = budgets.get(name, base_budget)
            if budget > 0:
                from grocery_lib.ui_utils import draw_text_price, _V1, _V2
                price_str = format_price(budget, sep)
                # Calculate pill width based on text length + padding for currency icon
                b_w = self.draw.len(price_str, 0) + (10 if "\x01" in price_str else 0)
                pill_w = b_w + 14
                pill_h = 18
                pill_x = self.draw.size.x - _MARGIN - pill_w - 5
                pill_y = y + (_ITEM_H - pill_h) // 2
                
                # Draw Pill
                _V1.x, _V1.y = pill_x, pill_y
                _V2.x, _V2.y = pill_w, pill_h
                self.draw.fill_round_rectangle(_V1, _V2, 9, C_BG)
                
                # Draw Price inside Pill
                pos.x = pill_x + 7
                pos.y = pill_y + (pill_h - self.draw.font_size.y) // 2
                draw_text_price(self.draw, pos, price_str, C_TEXT)

    def run(self):
        from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_CENTER, BUTTON_BACK, BUTTON_RIGHT, BUTTON_F3
        input_manager = self.view_manager.input_manager
        button = input_manager.button

        if button == BUTTON_BACK:
            input_manager.reset()
            return "EXIT"
        elif button == BUTTON_F3:
            input_manager.reset()
            return "HELP"
            
        old_idx = self._selected_index
        show_add = len(self.all_lists) < 10
        total_items = len(self.all_lists) + (1 if show_add else 0)
        
        if button == BUTTON_UP:
            self._selected_index = (self._selected_index - 1) % total_items
        elif button == BUTTON_DOWN:
            self._selected_index = (self._selected_index + 1) % total_items
        elif button == BUTTON_RIGHT:
            if not show_add or self._selected_index > 0:
                input_manager.reset()
                idx = self._selected_index - (1 if show_add else 0)
                self.app.active_list = self.all_lists[self.filtered_indices[idx]]
                return "PROPERTIES"
            
        if self._selected_index != old_idx:
            input_manager.reset()
            self._dirty = True
            self._draw()
        elif button == BUTTON_CENTER:
            input_manager.reset()
            if show_add and self._selected_index == 0:
                return "CREATE_LIST"
            else:
                idx = self._selected_index - (1 if show_add else 0)
                self.app.active_list = self.all_lists[self.filtered_indices[idx]]
                return "OPEN_LIST"
        return None
