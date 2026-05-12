from grocery_lib.i18n import translate
from grocery_lib.ui_utils import draw_header, draw_footer, draw_card, draw_icon, draw_text_price, C_BG, C_TEXT, C_PAPER
from grocery_lib.base_view import BaseView
from grocery_lib.config import get_config, set_config
from micropython import const
from picoware.system.vector import Vector

_BAR_H = const(24)
_MARGIN = const(4)
_SPACING = const(4)
_ITEM_H = const(32)
_CARD_RADIUS = const(6)

class SettingsView(BaseView):
    """View for adjusting app settings."""
    __slots__ = ("_options", "_selected_index", "_scroll_offset", "_max_visible", "card_w", "_card_size", "_last_idx")

    def __init__(self, view_manager, app):
        super().__init__(view_manager, app)
        self._options = ["base_budget", "language", "currency", "decimal_separator", "tax_region", "aisles", "reset"]
        self._selected_index = 0
        self._scroll_offset = 0
        self._last_idx = 0
        
        available_h = self.draw.size.y - (_BAR_H * 2) - (_MARGIN * 2)
        self._max_visible = available_h // (_ITEM_H + _SPACING)
        self.card_w = self.draw.size.x - (_MARGIN * 2)
        self._card_size = Vector(self.card_w, _ITEM_H)
        
        self._draw(True)

    def stop(self):
        pass

    def refresh_ui(self):
        """Called when language changes to refresh localized strings."""
        self._dirty = True
        self._draw(True)

    def _draw(self, full=False):
        if not self._dirty and not full: return
        
        start_y = _BAR_H + _MARGIN
        new_offset = self.handle_scroll(self._selected_index, self._scroll_offset, self._max_visible)
        
        if full or new_offset != self._scroll_offset:
            self._scroll_offset = new_offset
            self.draw.fill_screen(C_BG)
            draw_header(self.draw, translate("settings"), _BAR_H)
            for i in range(self._scroll_offset, min(len(self._options), self._scroll_offset + self._max_visible)):
                self._draw_row(i, start_y)
            
            # Scrollbar
            from grocery_lib.ui_utils import draw_scrollbar
            draw_scrollbar(self.draw, len(self._options), self._max_visible, self._scroll_offset, start_y, self.draw.size.y - (_BAR_H * 2) - _MARGIN)
            
            draw_footer(self.draw, translate("hint"), _BAR_H)
        else:
            # Surgical redraw of affected rows
            self._draw_row(self._last_idx, start_y)
            self._draw_row(self._selected_index, start_y)
            
        self.draw.swap()
        self._last_idx = self._selected_index
        self._dirty = False

    def _draw_row(self, i, start_y):
        if i < 0 or i >= len(self._options): return
        
        is_selected = (i == self._selected_index)
        y = start_y + (i - self._scroll_offset) * (_ITEM_H + _SPACING)
        pos = self._scratch_pos
        pos.x, pos.y = _MARGIN, y
        
        # Cache draw and font for speed
        d = self.draw
        fs_y = d.font_size.y
        
        draw_card(d, pos, self._card_size, _CARD_RADIUS, is_selected)
        
        key = self._options[i]
        label = translate(key)
        val = get_config(key)
        
        if key == "aisles":
            val = len(get_config("categories"))
        
        # Icon
        icon_key = key
        if key == "currency": icon_key = get_config("currency")
        elif key == "aisles": icon_key = "shopping_list"
        elif key == "reset": icon_key = "trash"
        draw_icon(d, icon_key, _MARGIN + 10, y + (_ITEM_H - 12) // 2)
        
        # Label
        pos.x, pos.y = _MARGIN + 35, y + (_ITEM_H - fs_y) // 2
        d.text(pos, label, C_TEXT, 0)
        
        # Value
        if val is not None:
            if isinstance(val, (int, float)): val = str(val)
            else: val = translate(str(val))
            
            pos.x = d.size.x - _MARGIN - d.len(val, 0) - 10
            draw_text_price(d, pos, val, C_TEXT)

    def run(self):
        from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_CENTER, BUTTON_BACK
        input_manager = self.view_manager.input_manager
        button = input_manager.button
        res = None

        if button == BUTTON_BACK:
            input_manager.reset()
            res = "EXIT"
        elif button == BUTTON_UP:
            input_manager.reset()
            self._selected_index = (self._selected_index - 1) % len(self._options)
            self._dirty = True
        elif button == BUTTON_DOWN:
            input_manager.reset()
            self._selected_index = (self._selected_index + 1) % len(self._options)
            self._dirty = True
        elif button == BUTTON_CENTER:
            input_manager.reset()
            res = "EDIT_" + self._options[self._selected_index].upper()
            
        if self._dirty:
            self._scroll_offset = self.handle_scroll(self._selected_index, self._scroll_offset, self._max_visible)
            self._draw()
            
        return res
