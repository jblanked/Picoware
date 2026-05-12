from micropython import const
from picoware.system.vector import Vector
from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_CENTER, BUTTON_BACK, BUTTON_BACKSPACE, BUTTON_DELETE
from grocery_lib.i18n import translate
from grocery_lib.ui_utils import draw_header, draw_footer, draw_card, C_BG, C_TEXT, C_PAPER, C_ACCENT, C_SEL
from grocery_lib.base_view import BaseView

_BAR_H = const(24)
_MARGIN = const(4)
_ITEM_H = const(32)
_SPACING = const(6)
_CARD_RADIUS = const(6)

class ItemPropertiesView(BaseView):
    __slots__ = ("item", "item_idx", "_selected_index", "_card_size", "_title", "_editing", "_input_buffer", "_cursor_pos", "_is_selecting", "_last_idx", "_needs_save")

    def __init__(self, view_manager, app):
        super().__init__(view_manager, app)
        self.item_idx = app._pending_item_idx
        items = app.storage.get_items(app.active_list)
        self._needs_save = False
        
        if hasattr(app, "_temp_edit_item") and app._temp_edit_item is not None:
            self.item = app._temp_edit_item
            app._temp_edit_item = None
            self._title = translate("edit_item") if self.item_idx is not None else translate("add_item")
            self._needs_save = True
        else:
            if self.item_idx is not None and self.item_idx < len(items):
                self.item = items[self.item_idx].copy()
                self._title = translate("manage_item")
            else:
                self.item = {"name": "", "qty": 1, "price": 0.0, "bought": False}
                self._title = translate("add_item")
        
        self._selected_index = 0
        self._last_idx = 0
        if hasattr(app, "_temp_edit_idx") and app._temp_edit_idx is not None:
            self._selected_index = app._temp_edit_idx
            self._last_idx = app._temp_edit_idx
            app._temp_edit_idx = None
            
        self._editing = False
        self._input_buffer = ""
        self._cursor_pos = 0
        self._is_selecting = False
        
        self._card_size = Vector(self.draw.size.x - (_MARGIN * 2), _ITEM_H)
        self._draw(True)

    def _draw(self, full=False):
        if not self._dirty and not full: return
        
        from grocery_lib.config import get_config
        cats = get_config("categories")
        
        start_y = _BAR_H + _MARGIN + 5
        fields = [
            ("name", translate("name")), 
            ("qty", translate("qty")),
            ("price", translate("price")),
            ("category", translate("sort_category"))
        ]
        
        if full or self._editing:
            self.draw.fill_screen(C_BG)
            draw_header(self.draw, self._title, _BAR_H)
            
            for i in range(len(fields)):
                self._draw_row(i, start_y, fields, cats)

            draw_footer(self.draw, translate("hint_item_props"), _BAR_H)
        else:
            self._draw_row(self._last_idx, start_y, fields, cats)
            self._draw_row(self._selected_index, start_y, fields, cats)
            
        self.draw.swap()
        self._last_idx = self._selected_index
        self._dirty = False

    def _draw_row(self, i, start_y, fields, cats):
        if i < 0 or i >= len(fields): return
        
        is_selected = (i == self._selected_index)
        y = start_y + i * (_ITEM_H + _SPACING)
        key, label = fields[i]
        
        self._scratch_pos.x, self._scratch_pos.y = _MARGIN, y
        draw_card(self.draw, self._scratch_pos, self._card_size, _CARD_RADIUS, is_selected)
        
        # Label
        tx, ty = _MARGIN + 12, y + (_ITEM_H - self.draw.font_size.y) // 2
        prefix = f"{label}: "
        self.draw.text(Vector(tx, ty), prefix, C_TEXT, 0)
        
        # Value
        px = tx + self.draw.len(prefix, 0)
        if key == "category":
            val_key = self.item.get("category", cats[0] if cats else "other")
            val = translate(val_key)
        else:
            val = str(self.item.get(key, ""))
        
        if is_selected and self._editing:
            val = self._input_buffer
            pre = val[:self._cursor_pos]
            post = val[self._cursor_pos:]
            
            if self._is_selecting and val:
                vw = self.draw.len(val, 0)
                self.draw.fill_rectangle(Vector(px - 2, y + 4), Vector(vw + 4, _ITEM_H - 8), C_SEL)
            
            self.draw.text(Vector(px, ty), pre, C_TEXT, 0)
            cx = px + self.draw.len(pre, 0)
            if not self._is_selecting and self._cursor_visible:
                self.draw.line_custom(Vector(cx, ty + 12), Vector(cx + 8, ty + 12), C_TEXT)
            self.draw.text(Vector(cx + 2, ty), post, C_TEXT, 0)
        else:
            self.draw.text(Vector(px, ty), val, C_TEXT, 0)

    def stop(self):
        # Save if we were not just switching to category select
        if self.app.current_view_name != "add_dialog":
            if self._editing:
                # Commit active buffer
                keys = ["name", "qty", "price", "category"]
                key = keys[self._selected_index]
                val = self._input_buffer
                if self._selected_index == 1:
                    try: val = int(val) if val else 1
                    except (ValueError, TypeError): val = 1
                elif self._selected_index == 2:
                    from grocery_lib.format_utils import parse_price
                    try: val = parse_price(val)
                    except (ValueError, TypeError): val = 0.0
                
                if self.item.get(key) != val:
                    self.item[key] = val
                    self._needs_save = True

            if self._needs_save and self.item and self.item.get("name"):
                items = self.app.storage.get_items(self.app.active_list)
                if self.item_idx is not None:
                    items[self.item_idx] = self.item
                else:
                    items.append(self.item)
                self.app.storage.save_items(self.app.active_list, items)
            self.app._temp_edit_item = None

    def run(self):
        if self._editing:
            self._check_cursor()
        from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_CENTER, BUTTON_BACK, BUTTON_BACKSPACE, BUTTON_DELETE
        input_manager = self.view_manager.input_manager
        btn = input_manager.button
        
        if btn == BUTTON_BACK:
            input_manager.reset()
            if self._editing:
                self._editing = False
                self._dirty = True
            else:
                return "EXIT"
            return None

        if self._editing:
            keys = ["name", "qty", "price", "category"]
            key = keys[self._selected_index]

            if btn == BUTTON_CENTER:
                input_manager.reset()
                val = self._input_buffer
                if self._selected_index == 1:
                    try: val = int(val) if val else 1
                    except (ValueError, TypeError): val = 1
                elif self._selected_index == 2:
                    from grocery_lib.format_utils import parse_price
                    try: val = parse_price(val)
                    except (ValueError, TypeError): val = 0.0
                
                if self.item.get(key) != val:
                    self.item[key] = val
                    self._needs_save = True

                self._editing = False
                self._is_selecting = False
                self._selected_index = (self._selected_index + 1) % 4
                self._dirty = True
            elif btn == BUTTON_LEFT:
                input_manager.reset()
                if self._is_selecting:
                    self._is_selecting = False
                    self._cursor_pos = len(self._input_buffer)
                else:
                    self._cursor_pos = max(0, self._cursor_pos - 1)
                self._dirty = True
            elif btn == BUTTON_RIGHT:
                input_manager.reset()
                if self._is_selecting:
                    self._is_selecting = False
                    self._cursor_pos = len(self._input_buffer)
                else:
                    self._cursor_pos = min(len(self._input_buffer), self._cursor_pos + 1)
                self._dirty = True
            else:
                char = input_manager.button_to_char(btn)
                if char:
                    input_manager.reset()
                    if self._is_selecting:
                        self._input_buffer = char
                        self._is_selecting = False
                        self._cursor_pos = 1
                    else:
                        self._input_buffer = self._input_buffer[:self._cursor_pos] + char + self._input_buffer[self._cursor_pos:]
                        self._cursor_pos += 1
                    self._dirty = True
                elif btn in (127, BUTTON_BACKSPACE, BUTTON_DELETE):
                    input_manager.reset()
                    if self._is_selecting:
                        self._input_buffer = ""
                        self._is_selecting = False
                        self._cursor_pos = 0
                        self._dirty = True
                    elif self._cursor_pos > 0:
                        self._input_buffer = self._input_buffer[:self._cursor_pos-1] + self._input_buffer[self._cursor_pos:]
                        self._cursor_pos -= 1
                        self._dirty = True
        else:
            if btn == BUTTON_UP:
                input_manager.reset()
                self._selected_index = (self._selected_index - 1) % 4
                self._dirty = True
            elif btn == BUTTON_DOWN:
                input_manager.reset()
                self._selected_index = (self._selected_index + 1) % 4
                self._dirty = True
            elif btn == BUTTON_CENTER:
                input_manager.reset()
                keys = ["name", "qty", "price", "category"]
                key = keys[self._selected_index]
                
                if key == "category":
                    from grocery_lib.aisle_select_view import AisleSelectView
                    from grocery_lib.config import get_config
                    cats = get_config("categories")
                    cur_val = self.item.get("category", cats[0] if cats else "other")
                    
                    self.app._temp_edit_item = self.item
                    self.app._temp_edit_idx = self._selected_index
                    
                    def _cat_cb(selected):
                        self.item["category"] = selected
                        self.app._temp_edit_item = self.item
                        self.app._temp_edit_idx = self._selected_index
                        self._needs_save = True
                        self._dirty = True
                        self.app._switch_view("item_properties")
                        
                    self.app._dialog_return_view = self.app.current_view_name
                    self.app.current_view = AisleSelectView(self.view_manager, self.app, cur_val, _cat_cb)
                    self.app.current_view_name = "add_dialog"
                    return None
                
                self._editing = True
                self.reset_cursor()
                self._input_buffer = str(self.item.get(key, ""))
                self._cursor_pos = len(self._input_buffer)
                self._is_selecting = True
                self._dirty = True

        if self._dirty:
            self._draw()
        return None
