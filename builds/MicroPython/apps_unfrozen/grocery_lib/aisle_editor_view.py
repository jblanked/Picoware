from grocery_lib.i18n import translate
from grocery_lib.ui_utils import draw_header, draw_footer, draw_card, draw_icon, C_BG, C_TEXT, C_PAPER, C_ACCENT, C_SEL
from grocery_lib.base_view import BaseView
from grocery_lib.config import get_config, set_config
from micropython import const
from picoware.system.vector import Vector

_BAR_H = const(24)
_MARGIN = const(4)
_SPACING = const(4)
_ITEM_H = const(32)
_CARD_RADIUS = const(6)

class AisleEditorView(BaseView):
    """View for reordering categories (aisles)."""
    __slots__ = ("categories", "_selected_index", "_scroll_offset", "_max_visible", "_card_size", "_title", "_moving_idx", "_last_idx", "_pending_delete_idx")

    def __init__(self, view_manager, app):
        super().__init__(view_manager, app)
        self.categories = list(get_config("categories"))
        self._selected_index = 0
        self._scroll_offset = 0
        self._last_idx = 0
        self._moving_idx = -1
        self._pending_delete_idx = -1
        self._title = translate("opt_aisles")
        
        available_h = self.draw.size.y - (_BAR_H * 2) - (_MARGIN * 2)
        self._max_visible = available_h // (_ITEM_H + _SPACING)
        self._card_size = Vector(self.draw.size.x - (_MARGIN * 2), _ITEM_H)
        
        self._draw(True)

    def _on_delete_confirm(self, res):
        if res == "OK" and self._pending_delete_idx != -1:
            idx = self._pending_delete_idx - 1
            if 0 <= idx < len(self.categories):
                old_cat = self.categories.pop(idx)
                self._selected_index = max(0, min(self._selected_index, len(self.categories)))
                set_config("categories", self.categories)
                # Remap orphaned items to 'other'
                self.app.storage.remap_category(old_cat, "other")
        self._pending_delete_idx = -1

    def _draw(self, full=False):
        if not self._dirty and not full: return
        
        start_y = _BAR_H + _MARGIN
        new_offset = self.handle_scroll(self._selected_index, self._scroll_offset, self._max_visible)
        total_items = len(self.categories) + 1
        label_add = translate("add_item")

        if full or new_offset != self._scroll_offset:
            self._scroll_offset = new_offset
            self.draw.fill_screen(C_BG)
            draw_header(self.draw, self._title, _BAR_H)
            
            for i in range(self._scroll_offset, min(total_items, self._scroll_offset + self._max_visible)):
                self._draw_row(i, start_y, label_add)
            
            # Scrollbar
            from grocery_lib.ui_utils import draw_scrollbar
            draw_scrollbar(self.draw, total_items, self._max_visible, self._scroll_offset, start_y, self.draw.size.y - (_BAR_H * 2) - _MARGIN)
        else:
            # Surgical redraw
            self._draw_row(self._last_idx, start_y, label_add)
            self._draw_row(self._selected_index, start_y, label_add)
            
        hint = translate("hint_aisle_move") if self._moving_idx != -1 else (translate("hint_aisles") + " | DEL: Remove")
        draw_footer(self.draw, hint, _BAR_H)
        self.draw.swap()
        self._last_idx = self._selected_index
        self._dirty = False

    def _draw_row(self, i, start_y, label_add):
        if i < 0 or i > len(self.categories): return
        
        is_selected = (i == self._selected_index)
        y = start_y + (i - self._scroll_offset) * (_ITEM_H + _SPACING)
        pos = self._scratch_pos
        pos.x, pos.y = _MARGIN, y
        
        is_moving = (self._moving_idx == i)
        
        if i == 0:
            draw_card(self.draw, pos, self._card_size, _CARD_RADIUS, is_selected)
            draw_icon(self.draw, "add_item", _MARGIN + 12, y + (_ITEM_H - 12) // 2)
            pos.x, pos.y = _MARGIN + 35, y + (_ITEM_H - self.draw.font_size.y) // 2
            self.draw.text(pos, label_add, C_TEXT, 0)
        else:
            color = C_ACCENT if is_moving else (C_SEL if is_selected else C_PAPER)
            # Override draw_card since it uses C_SEL for border when selected
            draw_card(self.draw, pos, self._card_size, _CARD_RADIUS, is_selected)
            if is_moving:
                self.draw.fill_round_rectangle(pos, self._card_size, _CARD_RADIUS, C_ACCENT)
            
            cat_name = translate(self.categories[i-1])
            pos.x, pos.y = _MARGIN + 12, y + (_ITEM_H - self.draw.font_size.y) // 2
            self.draw.text(pos, cat_name, C_TEXT if not is_moving else 0xFFFF, 0)

    def run(self):
        from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_CENTER, BUTTON_BACK, BUTTON_DELETE, BUTTON_BACKSPACE, KEY_DEL, BUTTON_ESCAPE
        input_manager = self.view_manager.input_manager
        btn = input_manager.button

        if btn == -1: return None

        # 1. EXIT KEYS: Physical Back button or Escape key always exits
        if btn in (BUTTON_BACK, BUTTON_ESCAPE):
            input_manager.reset()
            if self._moving_idx != -1:
                self._moving_idx = -1
                self._dirty = True
                return None
            else:
                set_config("categories", self.categories)
                return "EXIT"

        # 2. DELETE KEYS: Delete, KEY_DEL, or Backspace (if an item is selected)
        is_delete_key = btn in (BUTTON_DELETE, KEY_DEL, 127)
        is_backspace = (btn == BUTTON_BACKSPACE)
        
        if (is_delete_key or is_backspace) and self._selected_index > 0:
            input_manager.reset()
            from grocery_lib.dialog_view import DialogView
            self.app._dialog_return_view = "settings_aisles"
            self.app._save_current_state()
            
            self._pending_delete_idx = self._selected_index
            cat_name = self.categories[self._selected_index - 1]
            
            msg = translate("delete_item_query") + "\n(" + cat_name + ")"
            self.app.current_view = DialogView(self.view_manager, self.app, translate("warning"), msg, self._on_delete_confirm)
            self.app.current_view_name = "add_dialog"
            return None
            
        # 3. BACKSPACE AS EXIT: Only if at the very top of the list
        if is_backspace and self._selected_index == 0:
            input_manager.reset()
            set_config("categories", self.categories)
            return "EXIT"

        # 4. NAVIGATION & SELECTION
        old_idx = self._selected_index
        total_items = len(self.categories) + 1
        
        if btn == BUTTON_UP:
            self._selected_index = (self._selected_index - 1) % total_items
        elif btn == BUTTON_DOWN:
            self._selected_index = (self._selected_index + 1) % total_items
            
        if self._selected_index != old_idx:
            input_manager.reset()
            if self._moving_idx != -1 and self._selected_index > 0 and self._moving_idx > 0:
                # Swap categories
                m_idx = self._moving_idx - 1
                s_idx = self._selected_index - 1
                self.categories[m_idx], self.categories[s_idx] = self.categories[s_idx], self.categories[m_idx]
                self._moving_idx = self._selected_index
            self._dirty = True
            self._draw()
        elif btn == BUTTON_CENTER:
            input_manager.reset()
            if self._selected_index == 0:
                return "ADD_AISLE"
            else:
                if self._moving_idx == -1:
                    self._moving_idx = self._selected_index
                else:
                    self._moving_idx = -1
                self._dirty = True
                self._draw(True)
        return None
