from micropython import const
from picoware.system.vector import Vector
from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_CENTER, BUTTON_BACK, BUTTON_TAB, BUTTON_LEFT_BRACKET, BUTTON_RIGHT_BRACKET
from grocery_lib.i18n import translate
from grocery_lib.ui_utils import draw_header, draw_footer, draw_card, draw_icon, C_BG, C_TEXT, C_PAPER, C_ACCENT, C_SHADOW, C_SEL
from grocery_lib.base_view import BaseView
from grocery_lib.search_mixin import SearchMixin

_BAR_H = const(24)
_MARGIN = const(4)
_ITEM_H = const(30)
_SPACING = const(4)

class QuickAddView(BaseView, SearchMixin):
    """Dual-pane view for quickly adding pantry items to a shopping list."""
    __slots__ = ("pantry_items", "list_items", "_focus_pane", "_pantry_idx", "_list_idx", 
                 "_pantry_offset", "_list_offset", "_max_visible", "_card_size",
                 "_search_query_pantry", "_search_query_list", "filtered_pantry", "filtered_list", "_needs_save",
                 "_last_pantry_idx", "_last_list_idx", "_last_focus_pane", "_last_pantry_offset", "_last_list_offset", "_last_searching")

    def __init__(self, view_manager, app):
        super().__init__(view_manager, app)
        self._focus_pane = 0 # 0: Pantry, 1: List
        self._pantry_idx = 0
        self._list_idx = 0
        self._pantry_offset = 0
        self._list_offset = 0
        self._last_pantry_idx = 0
        self._last_list_idx = 0
        self._last_focus_pane = 0
        self._last_pantry_offset = 0
        self._last_list_offset = 0
        self._last_searching = False
        self._search_query_pantry = ""
        self._search_query_list = ""
        self.filtered_pantry = []
        self.filtered_list = []
        self._needs_save = False
        
        self.pantry_items = None
        self.list_items = None
        
        available_h = self.draw.size.y - (_BAR_H * 2) - 15
        self._max_visible = available_h // (_ITEM_H + _SPACING)
        self._card_size = Vector((self.draw.size.x // 2) - _MARGIN, _ITEM_H)
        
        self.refresh_data()
        self._draw(True)

    @property
    def _search_query(self):
        return self._search_query_pantry if self._focus_pane == 0 else self._search_query_list

    @_search_query.setter
    def _search_query(self, val):
        if self._focus_pane == 0: self._search_query_pantry = val
        else: self._search_query_list = val
        self._filter_items_reset()

    @property
    def _selected_index(self):
        return self._pantry_idx if self._focus_pane == 0 else self._list_idx

    @_selected_index.setter
    def _selected_index(self, val):
        if self._focus_pane == 0: self._pantry_idx = val
        else: self._list_idx = val

    @property
    def _scroll_offset(self):
        return self._pantry_offset if self._focus_pane == 0 else self._list_offset

    @_scroll_offset.setter
    def _scroll_offset(self, val):
        if self._focus_pane == 0: self._pantry_offset = val
        else: self._list_offset = val

    def _filter_items(self):
        # Pantry Filter
        qp = self._search_query_pantry.lower()
        if not qp: self.filtered_pantry = list(range(len(self.pantry_items)))
        else: self.filtered_pantry = [i for i, x in enumerate(self.pantry_items) if qp in x.get("name","").lower()]
        
        # List Filter
        ql = self._search_query_list.lower()
        if not ql: self.filtered_list = list(range(len(self.list_items)))
        else: self.filtered_list = [i for i, x in enumerate(self.list_items) if ql in x.get("name","").lower()]

    def refresh_data(self):
        if self.pantry_items is None:
            self.pantry_items = self.app.storage.get_pantry_items()
        if self.list_items is None:
            self.list_items = self.app.storage.get_items(self.app.active_list)
        self._filter_items()

    def stop(self):
        if self._needs_save:
            self.app.storage.save_items(self.app.active_list, self.list_items)
            self._needs_save = False

    def _draw(self, full=False):
        if not self._dirty and not full: return
        
        is_searching = bool(self._search_query_pantry) or bool(self._search_query_list)
        if self._last_searching != is_searching: full = True

        total_p = len(self.filtered_pantry) + (0 if self._search_query_pantry else 1)
        total_l = len(self.filtered_list) + (0 if self._search_query_list else 1)
        
        # Handle bounds issues and scroll changes
        if self._last_pantry_idx >= total_p: full = True
        if self._last_list_idx >= total_l: full = True
        if self._last_pantry_offset != self._pantry_offset: full = True
        if self._last_list_offset != self._list_offset: full = True
        
        if full or is_searching: 
            self._last_searching = is_searching
            self.draw.fill_screen(C_BG)
            
            p_title = f"P:{self._search_query_pantry}" if self._search_query_pantry else translate("pantry")
            l_title = f"L:{self._search_query_list}" if self._search_query_list else self.app.active_list
            draw_header(self.draw, f"{p_title} | {l_title}", _BAR_H)
            
            self.draw.line_custom(Vector(self.draw.size.x // 2, _BAR_H), Vector(self.draw.size.x // 2, self.draw.size.y - _BAR_H), C_SHADOW)
            
            for i in range(self._pantry_offset, min(total_p, self._pantry_offset + self._max_visible)):
                self._draw_row(i, 0)
                
            for i in range(self._list_offset, min(total_l, self._list_offset + self._max_visible)):
                self._draw_row(i, 1)

            draw_footer(self.draw, translate("hint_quick_add"), _BAR_H)
        else:
            # Surgical redraw
            if self._last_focus_pane != self._focus_pane:
                if self._last_pantry_idx < total_p: self._draw_row(self._last_pantry_idx, 0)
                if self._last_list_idx < total_l: self._draw_row(self._last_list_idx, 1)
                
            if self._last_pantry_idx < total_p: self._draw_row(self._last_pantry_idx, 0)
            if self._pantry_idx < total_p: self._draw_row(self._pantry_idx, 0)
                
            if self._last_list_idx < total_l: self._draw_row(self._last_list_idx, 1)
            if self._list_idx < total_l: self._draw_row(self._list_idx, 1)

        self.draw.swap()
        self._last_pantry_idx = self._pantry_idx
        self._last_list_idx = self._list_idx
        self._last_focus_pane = self._focus_pane
        self._last_pantry_offset = self._pantry_offset
        self._last_list_offset = self._list_offset
        self._dirty = False

    def _draw_row(self, i, pane_idx):
        if pane_idx == 0:
            total = len(self.filtered_pantry) + (0 if self._search_query_pantry else 1)
        else:
            total = len(self.filtered_list) + (0 if self._search_query_list else 1)
            
        if i < 0 or i >= total: return

        is_focused_pane = (self._focus_pane == pane_idx)
        selected_idx = self._pantry_idx if pane_idx == 0 else self._list_idx
        offset = self._pantry_offset if pane_idx == 0 else self._list_offset
        is_selected = (is_focused_pane and i == selected_idx)
        
        y = (_BAR_H + 10) + (i - offset) * (_ITEM_H + _SPACING)
        x = _MARGIN if pane_idx == 0 else (self.draw.size.x // 2) + 2
        
        pos = self._scratch_pos
        pos.x, pos.y = x, y
        draw_card(self.draw, pos, self._card_size, 4, is_selected)
        
        if pane_idx == 0: # Pantry
            if not self._search_query_pantry and i == 0:
                draw_icon(self.draw, "add_item", x + 5, y + 9, C_SEL)
                self.draw.text(Vector(x + 22, y + 8), translate("quick_add_new"), C_SEL, 0)
            else:
                idx = i if self._search_query_pantry else i - 1
                name = self.pantry_items[self.filtered_pantry[idx]].get("name", "??")
                self.draw.text(Vector(x + 8, y + 8), name, C_TEXT, 0)
        else: # List
            if not self._search_query_list and i == 0:
                draw_icon(self.draw, "edit", x + 5, y + 9, C_SEL)
                self.draw.text(Vector(x + 22, y + 8), translate("quick_add_one_off"), C_SEL, 0)
            else:
                idx = i if self._search_query_list else i - 1
                name = self.list_items[self.filtered_list[idx]].get("name", "??")
                qty = self.list_items[self.filtered_list[idx]].get("qty", 1)
                text = name if qty <= 1 else f"{name} x{qty}"
                self.draw.text(Vector(x + 8, y + 8), text, C_TEXT, 0)

    def run(self):
        input_manager = self.view_manager.input_manager
        btn = input_manager.button
        force_full = False

        if btn in (6, 77, 80): # START, ESC, HOME
            input_manager.reset()
            self.stop()
            return "HOME"
        elif btn == BUTTON_BACK:
            input_manager.reset()
            if self.is_searching:
                self.clear_search()
                return None
            self.stop()
            return "EXIT"
            
        if btn == BUTTON_TAB:
            input_manager.reset()
            self.stop()
            return "EXIT"

        from picoware.system.buttons import BUTTON_LEFT, BUTTON_RIGHT
        if btn in (BUTTON_LEFT, BUTTON_RIGHT):
            input_manager.reset()
            self._focus_pane = 1 - self._focus_pane
            self._dirty = True
            self._draw(False)
            return None

        if btn in (BUTTON_LEFT_BRACKET, BUTTON_RIGHT_BRACKET):
            input_manager.reset()
            if self._needs_save:
                self.app.storage.save_items(self.app.active_list, self.list_items)
                self._needs_save = False
            
            all_lists = self.app.storage.get_list_names()
            if not all_lists: return None
            
            try:
                idx = all_lists.index(self.app.active_list)
            except ValueError:
                idx = 0
                
            if btn == BUTTON_LEFT_BRACKET:
                idx = (idx - 1) % len(all_lists)
            else:
                idx = (idx + 1) % len(all_lists)
                
            self.app.active_list = all_lists[idx]
            self.list_items = self.app.storage.get_items(self.app.active_list)
            self._list_idx = 0
            self._list_offset = 0
            self._search_query_list = ""
            self._filter_items()
            self._dirty = True
            self._draw(True)
            return None

        if self.handle_search_input(btn, input_manager):
            input_manager.reset()
            if self._dirty: self._draw(True)
            return None

        total_rows = (len(self.filtered_pantry) + (0 if self._search_query_pantry else 1)) if self._focus_pane == 0 else (len(self.filtered_list) + (0 if self._search_query_list else 1))
        if self.handle_search_navigation(btn, total_rows, self._max_visible):
            input_manager.reset()
            self._scroll_offset = self.handle_scroll(self._selected_index, self._scroll_offset, self._max_visible)
            self._dirty = True
            self._draw(False)
            return None

        if btn == BUTTON_CENTER:
            input_manager.reset()
            if self._focus_pane == 0: # Add to list
                if not self._search_query_pantry and self._pantry_idx == 0:
                    return "ADD_PANTRY_NAME"
                
                if not self.filtered_pantry: return None # Safety
                
                idx_pos = self._pantry_idx if self._search_query_pantry else self._pantry_idx - 1
                if 0 <= idx_pos < len(self.filtered_pantry):
                    idx = self.filtered_pantry[idx_pos]
                    item = self.pantry_items[idx]
                    
                    # Check for duplicates
                    found = False
                    for li in self.list_items:
                        if li["name"] == item["name"]:
                            li["qty"] = li.get("qty", 1) + 1
                            found = True; break
                    if not found:
                        self.list_items.append({"name": item["name"], "qty": 1, "price": item.get("price", 0.0), "category": item.get("category", "other"), "bought": False})
                    
                    self._needs_save = True
                    self._filter_items()
                    self._dirty = True
                    force_full = True
            else: # Remove from list / Add One-off
                if not self._search_query_list and self._list_idx == 0:
                    return "ADD_ONE_OFF"
                
                if not self.filtered_list: return None # Safety
                
                idx_pos = self._list_idx if self._search_query_list else self._list_idx - 1
                if 0 <= idx_pos < len(self.filtered_list):
                    data_idx = self.filtered_list[idx_pos]
                    self.list_items.pop(data_idx)
                    self._needs_save = True
                    self._filter_items()
                    self._list_idx = max(0, min(self._list_idx, len(self.filtered_list) + (0 if self._search_query_list else 1) - 1))
                    self._dirty = True
                    force_full = True
        
        if self._dirty: self._draw(force_full)
        return None
