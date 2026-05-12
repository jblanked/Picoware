from grocery_lib.i18n import translate
from grocery_lib.ui_utils import draw_header, draw_card, draw_icon, C_BG, C_TEXT, C_SEL, C_PAPER, C_SHADOW
from grocery_lib.base_view import BaseView
from grocery_lib.config import get_config
from grocery_lib.format_utils import format_price
from micropython import const
from picoware.system.vector import Vector
from grocery_lib.search_mixin import SearchMixin

_BAR_H = const(24)
_MARGIN = const(4)
_SPACING = const(4)
_ITEM_H = const(32)
_CARD_RADIUS = const(6)

class ListView(BaseView, SearchMixin):
    """View for managing items within a shopping list."""
    __slots__ = ("list_name", "items", "filtered_indices", "_selected_index", "_scroll_offset", "_max_visible", "_card_size", "_search_query", "_last_idx", "_footer_dirty", "_total_cost", "_bought_cost", "_costs_dirty", "_needs_save", "_pending_delete_idx", "_last_searching")

    def __init__(self, view_manager, app):
        super().__init__(view_manager, app)
        self.list_name = app.active_list
        self._selected_index = 0
        self._scroll_offset = 0
        self._last_idx = 0
        self._footer_dirty = True
        self._needs_save = False
        self._pending_delete_idx = -1
        self.items = None
        self._total_cost = 0.0
        self._bought_cost = 0.0
        self._costs_dirty = True
        self._needs_save = False
        self._last_searching = False
        
        available_h = self.draw.size.y - (_BAR_H * 2) - (_MARGIN * 2)
        self._max_visible = available_h // (_ITEM_H + _SPACING)
        self._card_size = Vector(self.draw.size.x - (_MARGIN * 2), _ITEM_H)
        
        self.init_search()
        self._draw(True)

    def _filter_items(self):
        if self.items is None:
            self.items = self.app.storage.get_items(self.list_name)
        
        # Apply Category Sorting
        from grocery_lib.config import get_config
        cats = get_config("categories")
        def sort_key(idx):
            item = self.items[idx]
            cat = item.get("category", "other")
            try: return cats.index(cat)
            except (ValueError, IndexError): return 999
        
        raw_indices = list(range(len(self.items)))
        raw_indices.sort(key=sort_key)
        
        q = self._search_query.lower()
        if not q:
            self.filtered_indices = raw_indices
        else:
            self.filtered_indices = [i for i in raw_indices if q in self.items[i].get("name", "").lower()]

    def _draw_footer(self):
        from grocery_lib.ui_utils import draw_footer
        if self._costs_dirty or self.items is None:
            if self.items is None:
                self.items = self.app.storage.get_items(self.list_name)
            self._total_cost = sum(i.get("price", 0.0) * i.get("qty", 1) for i in self.items)
            self._bought_cost = sum(i.get("price", 0.0) * i.get("qty", 1) for i in self.items if i.get("bought", False))
            self._costs_dirty = False
            
        # Clear budget area (above the footer bar)
        hy = self.draw.size.y - _BAR_H - 12
        from grocery_lib.ui_utils import _V1, _V2
        _V1.x, _V1.y = 0, hy - 2
        _V2.x, _V2.y = self.draw.size.x, 16 
        self.draw.fill_rectangle(_V1, _V2, C_BG)

        # Draw key hints in the primary footer bar
        hint = translate("hint_list")
        draw_footer(self.draw, hint, _BAR_H)
        
        # Draw budget text in a pill
        from grocery_lib.format_utils import format_price
        sep = get_config("decimal_separator")
        bought_str = format_price(self._bought_cost, sep)
        total_str = format_price(self._total_cost, sep)
        
        # Simpler label to reduce width
        label = f"{bought_str} / {total_str}"

        # Pill background
        from grocery_lib.ui_utils import draw_text_price
        # Small fixed padding instead of dynamic jumping
        tw = self.draw.len(label, 0) + (12 if "\x01" in label else 0)
        pill_w = tw + 16
        pill_h = 18
        pill_x = self.draw.size.x - pill_w - 6
        pill_y = hy - 3
        
        _V1.x, _V1.y = pill_x, pill_y
        _V2.x, _V2.y = pill_w, pill_h
        self.draw.fill_round_rectangle(_V1, _V2, 9, C_PAPER)
        # No border to avoid glitching, PAPER vs BG contrast is sufficient

        draw_text_price(self.draw, Vector(pill_x + 8, pill_y + (pill_h - self.draw.font_size.y) // 2), label, C_TEXT)

    def _draw(self, full=False):
        if not self._dirty and not full: return
        
        is_searching = self.is_searching
        if self._last_searching != is_searching: full = True

        # Adjust y to account for progress bar (4px)
        bar_h = 4
        start_y = _BAR_H + _MARGIN + bar_h
        new_offset = self.handle_scroll(self._selected_index, self._scroll_offset, self._max_visible)
        
        sep = get_config("decimal_separator")
        total_rows = len(self.filtered_indices)

        # Force full redraw if last_idx is out of current bounds or list is empty
        if self._last_idx >= total_rows or total_rows == 0 or is_searching: full = True

        if full or self.is_searching or new_offset != self._scroll_offset:
            self._last_searching = is_searching
            self._scroll_offset = new_offset
            self.draw.fill_screen(C_BG)
            
            # Progress calculation
            total_items = len(self.items)
            bought_count = sum(1 for i in self.items if i.get("bought", False))
            percentage = (bought_count / total_items * 100) if total_items > 0 else 0
            
            title = self.search_title if is_searching else self.list_name
            right_text = "[%d/%d]" % (bought_count, total_items)
            
            from grocery_lib.ui_utils import draw_progress_bar
            draw_header(self.draw, title, _BAR_H, right_text, center_title=False)
            draw_progress_bar(self.draw, _BAR_H, bar_h, percentage)
            
            if total_rows == 0:
                from grocery_lib.ui_utils import draw_text_centered
                prompt = translate("list_empty_prompt")
                
                # Split and draw multi-line prompt
                lines = prompt.split("\n")
                lh = self.draw.font_size.y
                total_h = len(lines) * lh
                sy = _BAR_H + (self.draw.size.y - _BAR_H * 2 - total_h) // 2
                
                for i, line in enumerate(lines):
                    draw_text_centered(self.draw, 0, sy + i * lh, self.draw.size.x, lh, line, C_TEXT, 0)
            else:
                for i in range(self._scroll_offset, min(total_rows, self._scroll_offset + self._max_visible)):
                    self._draw_row(i, start_y, sep)
                
                # Scrollbar
                from grocery_lib.ui_utils import draw_scrollbar
                draw_scrollbar(self.draw, total_rows, self._max_visible, self._scroll_offset, start_y, self.draw.size.y - (_BAR_H * 2) - _MARGIN)

            self._draw_footer()
        else:
            # Surgical redraw with safety
            if self._last_idx < total_rows: self._draw_row(self._last_idx, start_y, sep)
            if self._selected_index < total_rows: self._draw_row(self._selected_index, start_y, sep)
            
            if self._footer_dirty or self._costs_dirty:
                # Update header counter and progress bar
                total_items = len(self.items)
                bought_count = sum(1 for i in self.items if i.get("bought", False))
                percentage = (bought_count / total_items * 100) if total_items > 0 else 0
                title = self.search_title if self.is_searching else self.list_name
                right_text = "[%d/%d]" % (bought_count, total_items)
                
                from grocery_lib.ui_utils import draw_progress_bar
                draw_header(self.draw, title, _BAR_H, right_text, center_title=False)
                draw_progress_bar(self.draw, _BAR_H, bar_h, percentage)
                
                self._draw_footer()
                self._footer_dirty = False
                # Note: _costs_dirty is cleared after footer draw in some views, 
                # but here it's part of the logic that triggers this redraw.
        
        self.draw.swap()
        self._last_idx = self._selected_index
        self._dirty = False

    def _draw_row(self, i, start_y, sep):
        from grocery_lib.ui_utils import C_SHADOW
        total_rows = len(self.filtered_indices)
        if i < 0 or i >= total_rows: return
        
        is_selected = (i == self._selected_index)
        y = start_y + (i - self._scroll_offset) * (_ITEM_H + _SPACING)
        pos = self._scratch_pos
        pos.x, pos.y = _MARGIN, y
        
        # Cache for speed
        d = self.draw
        fs_y = d.font_size.y

        draw_card(d, pos, self._card_size, _CARD_RADIUS, is_selected)
        
        item_idx = self.filtered_indices[i]
        if item_idx < 0 or item_idx >= len(self.items): return
        
        item = self.items[item_idx]
        is_bought = item.get("bought", False)
        
        # Checkbox Icon
        icon_x = _MARGIN + 10
        icon_y = y + (_ITEM_H - 12) // 2
        if is_bought:
            draw_icon(d, "checkmark", icon_x, icon_y, C_SEL)
            text_c = C_SHADOW # Dim bought items
        else:
            draw_icon(d, "box", icon_x, icon_y, C_TEXT)
            text_c = C_TEXT
        
        # Name
        pos.x, pos.y = _MARGIN + 35, y + (_ITEM_H - fs_y) // 2
        name_text = item.get("name", "Unknown")
        if item.get("qty", 1) > 1:
            name_text = "%s x%d" % (name_text, item["qty"])
        d.text(pos, name_text, text_c, 0)
        
        # Price
        price = item.get("price", 0.0)
        if price > 0:
            from grocery_lib.ui_utils import draw_text_price
            price_str = format_price(price * item.get("qty", 1), sep)
            pos.x = d.size.x - _MARGIN - d.len(price_str, 0) - 10
            draw_text_price(d, pos, price_str, text_c)

    def stop(self):
        if self._needs_save:
            self.app.storage.save_items(self.list_name, self.items)
            self._needs_save = False

    def _on_delete_item_confirm(self, res):
        if res == "OK" and self._pending_delete_idx != -1:
            self.items.pop(self._pending_delete_idx)
            self._filter_items()
            self._selected_index = min(self._selected_index, len(self.filtered_indices))
            self._costs_dirty = True
            self.app.storage.save_items(self.list_name, self.items)
            self._dirty = True
        self._pending_delete_idx = -1

    def _on_clear_checked_confirm(self, res):
        if res == "OK":
            self.items = [i for i in self.items if not i.get("bought", False)]
            self._filter_items()
            self._selected_index = min(self._selected_index, len(self.filtered_indices))
            self._costs_dirty = True
            self.app.storage.save_items(self.list_name, self.items)
            self._dirty = True

    def _check_all_bought(self):
        """Check if all items are bought and show completion dialog if so."""
        if not self.items: return
        
        all_bought = True
        for x in self.items:
            if not x.get("bought", False):
                all_bought = False
                break
                
        if all_bought:
            from grocery_lib.dialog_view import DialogView
            from grocery_lib.config import get_config
            self.app._last_main_view = "list_items"
            sep = get_config("decimal_separator")
            lcd_str = f"{self._total_cost:.2f}".replace(".", sep)
            self.stop()
            self.app.current_view = DialogView(self.view_manager, self.app, translate("clear_checked"), translate("clear_items_query"), self._on_clear_checked_confirm, lcd_str)
            self.app.current_view_name = "add_dialog"

    def run(self):
        from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_CENTER, BUTTON_BACK, BUTTON_RIGHT, BUTTON_LEFT, BUTTON_BACKSPACE, BUTTON_TAB
        input_manager = self.view_manager.input_manager
        btn = input_manager.button

        if btn in (6, 77, 80): # START, ESC, HOME
            input_manager.reset()
            self.stop()
            return "HOME"
        elif btn == 56: # PLUS (+)
            input_manager.reset()
            self.stop()
            return "add_item"
        elif btn == BUTTON_BACK:
            input_manager.reset()
            if self.is_searching:
                self.clear_search()
                return None
            self.stop()
            return "EXIT"
            
        # Search handling
        if self.handle_search_input(btn, input_manager):
            input_manager.reset()
            if self._dirty: self._draw()
            return None

        total_items = len(self.filtered_indices)
        
        if self.handle_search_navigation(btn, total_items, self._max_visible):
            input_manager.reset()
            self._dirty = True
            self._draw()
            return None

        if btn == BUTTON_RIGHT:
            idx = self.get_filtered_data_index(False)
            if idx is not None and not self.items[idx].get("bought", False):
                input_manager.reset()
                self.items[idx]["qty"] = self.items[idx].get("qty", 1) + 1
                self._costs_dirty = True
                self._needs_save = True
                self._dirty = True
        elif btn == BUTTON_LEFT:
            idx = self.get_filtered_data_index(False)
            if idx is not None and not self.items[idx].get("bought", False):
                input_manager.reset()
                cur = self.items[idx].get("qty", 1)
                if cur > 1:
                    self.items[idx]["qty"] = cur - 1
                    self._costs_dirty = True
                    self._needs_save = True
                    self._dirty = True
        elif btn == BUTTON_TAB:
            input_manager.reset()
            self.stop()
            return "add_item"
        elif btn in (BUTTON_BACKSPACE, 127):
            idx = self.get_filtered_data_index(False)
            if idx is not None:
                input_manager.reset()
                # Use confirmation dialog for delete
                from grocery_lib.dialog_view import DialogView
                self.app._last_main_view = "list_items"
                self.app._save_current_state()
                
                self._pending_delete_idx = idx
                item = self.items[idx]
                
                msg = translate("delete_item_query") + "\n(" + item.get("name", "") + ")"
                self.app.current_view = DialogView(self.view_manager, self.app, translate("warning"), msg, self._on_delete_item_confirm)
                self.app.current_view_name = "add_dialog"
                return None
        elif btn == BUTTON_CENTER:
            if len(self.filtered_indices) == 0:
                self.stop()
                input_manager.reset()
                return "add_item"
            else:
                idx = self.get_filtered_data_index(False)
                if idx is not None:
                    input_manager.reset()
                    item = self.items[idx]
                    item["bought"] = not item.get("bought", False)
                    self._costs_dirty = True
                    self._needs_save = True
                    self._dirty = True
                    self._draw()
                    
                    if item["bought"]:
                        budget = get_config("list_budgets").get(self.list_name, get_config("base_budget"))
                        if budget > 0 and self._bought_cost > budget:
                            from grocery_lib.dialog_view import DialogView
                            self.app._last_main_view = "list_items"
                            
                            def _on_budget_confirm(res):
                                if res != "OK":
                                    item["bought"] = False
                                    self._costs_dirty = True
                                    self._needs_save = True
                                    self._dirty = True
                                    self.app._switch_view("list_items")
                                else:
                                    # User proceeded, check if list is done
                                    self._check_all_bought()

                            overshoot = self._bought_cost - budget
                            sep = get_config("decimal_separator")
                            lcd_str = f"{overshoot:.2f}".replace(".", sep)
                            msg = translate("budget_exceeded") + "\n(" + item.get("name", "") + ")"
                            self.app._save_current_state()
                            self.app.current_view = DialogView(self.view_manager, self.app, translate("warning"), msg, _on_budget_confirm, lcd_str)
                            self.app.current_view_name = "add_dialog"
                            input_manager.reset() # Extra reset to prevent auto-close
                            return None
                            
                        self._check_all_bought()
                    return None
        
        if self._dirty:
            self._draw()
        return None
