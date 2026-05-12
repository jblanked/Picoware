from grocery_lib.i18n import translate
from grocery_lib.ui_utils import draw_header, draw_footer, draw_card, draw_icon, C_BG, C_TEXT, C_PAPER
from grocery_lib.base_view import BaseView
from grocery_lib.search_mixin import SearchMixin
from micropython import const
from picoware.system.vector import Vector

_BAR_H = const(24)
_MARGIN = const(4)
_SPACING = const(4)
_ITEM_H = const(32)
_CARD_RADIUS = const(6)

class PantryView(BaseView, SearchMixin):
    """View for managing pantry inventory."""
    __slots__ = ("items", "filtered_indices", "_selected_index", "_scroll_offset", "_max_visible", "_card_size", "_last_idx", "_search_query", "_last_searching")

    def __init__(self, view_manager, app):
        super().__init__(view_manager, app)
        self._selected_index = 0
        self._scroll_offset = 0
        self._last_idx = 0
        self._search_query = ""
        self.filtered_indices = []
        self._last_searching = False
        
        available_h = self.draw.size.y - (_BAR_H * 2) - (_MARGIN * 2)
        self._max_visible = available_h // (_ITEM_H + _SPACING)
        self._card_size = Vector(self.draw.size.x - (_MARGIN * 2), _ITEM_H)
        
        self.refresh_data()
        self._draw(True)

    def refresh_data(self):
        self.items = self.app.storage.get_pantry_items()
        self._filter_items()

    def _filter_items(self):
        q = self._search_query.lower()
        if not q:
            self.filtered_indices = list(range(len(self.items)))
        else:
            self.filtered_indices = [i for i, item in enumerate(self.items) if q in item.get("name", "").lower()]

    def stop(self):
        pass

    def _draw(self, full=False):
        if not self._dirty and not full: return
        
        is_searching = self.is_searching
        if self._last_searching != is_searching: full = True

        new_offset = self.handle_scroll(self._selected_index, self._scroll_offset, self._max_visible)
        start_y = _BAR_H + _MARGIN
        show_add = not is_searching
        total_rows = len(self.filtered_indices) + (1 if show_add else 0)
        label_add = translate("add_pantry_item")

        # Force full redraw if last_idx is out of current bounds
        if self._last_idx >= total_rows or is_searching: full = True

        if full or new_offset != self._scroll_offset:
            self._last_searching = is_searching
            self._scroll_offset = new_offset
            self.draw.fill_screen(C_BG)
            
            title = self.search_title if is_searching else translate("pantry")
            draw_header(self.draw, title, _BAR_H, "[ ] + H", center_title=not is_searching)
            
            for i in range(self._scroll_offset, min(total_rows, self._scroll_offset + self._max_visible)):
                self._draw_row(i, start_y, label_add, show_add)
            
            # Scrollbar
            from grocery_lib.ui_utils import draw_scrollbar
            draw_scrollbar(self.draw, total_rows, self._max_visible, self._scroll_offset, start_y, self.draw.size.y - (_BAR_H * 2) - _MARGIN)
                
            draw_footer(self.draw, translate("hint_pantry"), _BAR_H)
        else:
            # Surgical redraw
            if self._last_idx < total_rows: self._draw_row(self._last_idx, start_y, label_add, show_add)
            if self._selected_index < total_rows: self._draw_row(self._selected_index, start_y, label_add, show_add)
            
        self.draw.swap()
        self._last_idx = self._selected_index
        self._dirty = False

    def _draw_row(self, i, start_y, label_add, show_add):
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
            self.draw.text(pos, label_add, C_TEXT, 0)
        else:
            draw_card(self.draw, pos, self._card_size, _CARD_RADIUS, is_selected)
            idx = i - (1 if show_add else 0)
            item = self.items[self.filtered_indices[idx]]
            draw_icon(self.draw, "pantry", _MARGIN + 10, y + (_ITEM_H - 12) // 2)
            
            pos.x, pos.y = _MARGIN + 35, y + (_ITEM_H - self.draw.font_size.y) // 2
            name_text = item.get("name", "Unknown")
            self.draw.text(pos, name_text, C_TEXT, 0)
            
            qty_text = "%d" % item.get("qty", 0)
            q_w = self.draw.len(qty_text, 0)
            pos.x = self.draw.size.x - _MARGIN - q_w - 10
            self.draw.text(pos, qty_text, C_TEXT, 0)

    def run(self):
        from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_CENTER, BUTTON_BACK, BUTTON_RIGHT, BUTTON_LEFT
        input_manager = self.view_manager.input_manager
        button = input_manager.button

        # 1. Search input handling first (highest priority)
        if self.handle_search_input(button, input_manager):
            input_manager.reset()
            if self._dirty: self._draw()
            return None

        if button in (6, 77, 80): # START, ESC, HOME
            input_manager.reset()
            return "HOME"
        elif button == 56: # PLUS (+)
            input_manager.reset()
            return "ADD_PANTRY_NAME"
        elif button == BUTTON_BACK:
            input_manager.reset()
            if self.is_searching:
                self.clear_search()
                self._draw()
                return None
            return "EXIT"

        show_add = not self.is_searching
        total_rows = len(self.filtered_indices) + (1 if show_add else 0)
        
        # 2. Search navigation handling
        if self.handle_search_navigation(button, total_rows, self._max_visible):
            input_manager.reset()
            self._dirty = True
            self._draw()
            return None

        # 3. Standard Navigation (only if rows exist)
        if total_rows == 0:
            return None

        old_idx = self._selected_index
        
        if button == BUTTON_UP:
            self._selected_index = (self._selected_index - 1) % total_rows
        elif button == BUTTON_DOWN:
            self._selected_index = (self._selected_index + 1) % total_rows
        elif button == 58: # BUTTON_LEFT_BRACKET
            self._selected_index = max(0, self._selected_index - self._max_visible)
        elif button == 59: # BUTTON_RIGHT_BRACKET
            self._selected_index = min(total_rows - 1, self._selected_index + self._max_visible)
        elif button == BUTTON_LEFT:
            pass
        elif button == BUTTON_RIGHT:
            if not show_add or self._selected_index > 0:
                input_manager.reset()
                idx = self._selected_index - (1 if show_add else 0)
                self.app._pending_item_idx = self.filtered_indices[idx]
                return "EDIT_PANTRY_ITEM"
            
        if self._selected_index != old_idx:
            input_manager.reset()
            self._scroll_offset = self.handle_scroll(self._selected_index, self._scroll_offset, self._max_visible)
            self._dirty = True
            self._draw()
        elif button == BUTTON_CENTER:
            input_manager.reset()
            if show_add and self._selected_index == 0:
                return "ADD_PANTRY_NAME"
            else:
                idx = self._selected_index - (1 if show_add else 0)
                self.app._pending_item_idx = self.filtered_indices[idx]
                return "EDIT_PANTRY_ITEM"
        return None
