from micropython import const
from picoware.system.vector import Vector
from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_CENTER, BUTTON_BACK, BUTTON_BACKSPACE, BUTTON_DELETE
from grocery_lib.i18n import translate
from grocery_lib.ui_utils import draw_header, draw_footer, draw_card, draw_icon, C_BG, C_TEXT, C_PAPER, C_ACCENT, C_SEL
from grocery_lib.base_view import BaseView

_BAR_H = const(24)
_MARGIN = const(4)
_ITEM_H = const(32)
_SPACING = const(6)
_CARD_RADIUS = const(6)

class PantryEditView(BaseView):
    __slots__ = ("item_idx", "item", "fields", "_selected_index", "_scroll_offset", "_max_visible", "_card_size", "_title", "_editing", "_input_buffer", "_cursor_pos", "_pending_delete", "_is_selecting", "_last_idx", "_needs_save")

    def __init__(self, view_manager, app):
        super().__init__(view_manager, app)
        self.item_idx = app._pending_item_idx
        pantry = app.storage.get_pantry_items()
        self._pending_delete = False
        self._needs_save = False
        
        self.fields = [("name", translate("name")), ("qty", translate("qty")), ("price", translate("price")), ("category", translate("sort_category"))]
        
        if hasattr(app, "_temp_edit_item") and app._temp_edit_item is not None:
            self.item = app._temp_edit_item
            app._temp_edit_item = None
            self._title = translate("edit_item") if self.item_idx is not None else translate("add_item")
            self._needs_save = True
            if self.item_idx is not None and self.item_idx < len(pantry):
                self.fields.append(("clone", translate("clone_item")))
                self.fields.append(("delete", translate("delete")))
        else:
            if self.item_idx is not None and self.item_idx < len(pantry):
                self.item = pantry[self.item_idx].copy()
                self._title = translate("edit_item")
                self.fields.append(("clone", translate("clone_item")))
                self.fields.append(("delete", translate("delete")))
            else:
                self.item = {"name": "", "qty": 1, "price": 0.0}
                self._title = translate("add_item")
                self.item_idx = None
        
        self._selected_index = 0
        self._last_idx = 0
        if hasattr(app, "_temp_edit_idx") and app._temp_edit_idx is not None:
            self._selected_index = app._temp_edit_idx
            self._last_idx = app._temp_edit_idx
            app._temp_edit_idx = None
            
        self._scroll_offset = 0
        self._editing = (self.item_idx is None)
        self._input_buffer = ""
        self._cursor_pos = 0
        self._is_selecting = False
        
        available_h = self.draw.size.y - (_BAR_H * 2) - (_MARGIN * 2)
        self._max_visible = available_h // (_ITEM_H + _SPACING)
        self._card_size = Vector(self.draw.size.x - (_MARGIN * 2), _ITEM_H)
        
        self._draw(True)

    def _on_delete_confirm(self, res):
        self.app._temp_edit_item = None
        if res == "OK" and self._pending_delete:
            pantry = self.app.storage.get_pantry_items()
            if self.item_idx is not None and self.item_idx < len(pantry):
                pantry.pop(self.item_idx)
                self.app.storage.save_pantry(pantry)
            self.app._switch_view("pantry")
        self._pending_delete = False

    def _draw(self, full=False):
        if not self._dirty and not full: return
        start_y = _BAR_H + _MARGIN + 10
        
        if full or self._editing:
            self.draw.fill_screen(C_BG)
            draw_header(self.draw, self._title, _BAR_H)
            
            for i in range(len(self.fields)):
                self._draw_row(i, start_y)

            draw_footer(self.draw, translate("hint_pantry_edit"), _BAR_H)
        else:
            self._draw_row(self._last_idx, start_y)
            self._draw_row(self._selected_index, start_y)
            
        self.draw.swap()
        self._last_idx = self._selected_index
        self._dirty = False

    def _draw_row(self, i, start_y):
        if i < 0 or i >= len(self.fields): return
        
        is_selected = (i == self._selected_index)
        y = start_y + i * (_ITEM_H + _SPACING)
        key, label = self.fields[i]
        
        self._scratch_pos.x, self._scratch_pos.y = _MARGIN, y
        draw_card(self.draw, self._scratch_pos, self._card_size, _CARD_RADIUS, is_selected)
        
        # Label
        self._scratch_pos.x, self._scratch_pos.y = _MARGIN + 12, y + (_ITEM_H - self.draw.font_size.y) // 2
        prefix = f"{label}: " if key != "delete" else label
        self.draw.text(self._scratch_pos, prefix, C_TEXT, 0)
        
        # Value
        if key == "delete":
            draw_icon(self.draw, "box", self.draw.size.x - _MARGIN - 20, y + (_ITEM_H - 12) // 2)
        else:
            if key == "category":
                from grocery_lib.config import get_config
                cats = get_config("categories")
                val_key = self.item.get("category", cats[0] if cats else "other")
                val = translate(val_key)
            else:
                val = str(self.item.get(key, ""))
                
            if is_selected and self._editing:
                px = self._scratch_pos.x + self.draw.len(prefix, 0)
                val = self._input_buffer
                pre = val[:self._cursor_pos]
                post = val[self._cursor_pos:]
                
                if self._is_selecting and val:
                    vw = self.draw.len(val, 0)
                    self.draw.fill_rectangle(Vector(px - 2, y + 4), Vector(vw + 4, _ITEM_H - 8), C_SEL)
                
                self.draw.text(Vector(px, self._scratch_pos.y), pre, C_TEXT, 0)
                
                # Cursor
                cx = px + self.draw.len(pre, 0)
                cw = 8
                if not self._is_selecting and self._cursor_visible:
                    self.draw.line_custom(Vector(cx, self._scratch_pos.y + 12), Vector(cx + cw, self._scratch_pos.y + 12), C_TEXT)
                
                self.draw.text(Vector(cx + 2, self._scratch_pos.y), post, C_TEXT, 0)
            else:
                px = self._scratch_pos.x + self.draw.len(prefix, 0)
                self.draw.text(Vector(px, self._scratch_pos.y), val, C_TEXT, 0)

    def stop(self):
        # Save if we were not just switching to category select
        if self.app.current_view_name != "add_dialog":
            if self._editing:
                key = self.fields[self._selected_index][0]
                val = self._input_buffer
                if key == "qty":
                    try: val = int(val) if val else 0
                    except (ValueError, TypeError): val = 0
                elif key == "price":
                    from grocery_lib.format_utils import parse_price
                    try: val = parse_price(val)
                    except (ValueError, TypeError): val = 0.0
                
                if self.item.get(key) != val:
                    self.item[key] = val
                    self._needs_save = True

            if self._needs_save and self.item and self.item.get("name"):
                pantry = self.app.storage.get_pantry_items()
                if self.item_idx is not None:
                    pantry[self.item_idx] = self.item
                else:
                    pantry.append(self.item)
                    # Set selection to new item in PantryView
                    self.app._view_indices["pantry"] = len(pantry)
                self.app.storage.save_pantry(pantry)
            self.app._temp_edit_item = None

    def run(self):
        if self._editing:
            self._check_cursor()
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
            key = self.fields[self._selected_index][0]

            if btn == BUTTON_CENTER:
                input_manager.reset()
                val = self._input_buffer
                if key == "qty":
                    try: val = int(val) if val else 0
                    except (ValueError, TypeError): val = 0
                elif key == "price":
                    from grocery_lib.format_utils import parse_price
                    try: val = parse_price(val)
                    except (ValueError, TypeError): val = 0.0
                
                if self.item.get(key) != val:
                    self.item[key] = val
                    self._needs_save = True

                self._editing = False
                self._is_selecting = False
                self._selected_index = (self._selected_index + 1) % len(self.fields)
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
                elif btn in (127, BUTTON_BACKSPACE, BUTTON_DELETE): # Backspace
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
                self._selected_index = (self._selected_index - 1) % len(self.fields)
                self._dirty = True
            elif btn == BUTTON_DOWN:
                input_manager.reset()
                self._selected_index = (self._selected_index + 1) % len(self.fields)
                self._dirty = True
            elif btn == BUTTON_CENTER:
                input_manager.reset()
                key = self.fields[self._selected_index][0]
                if key == "delete":
                    from grocery_lib.dialog_view import DialogView
                    self.app._last_main_view = "pantry_edit" 
                    self._pending_delete = True
                    self.app._temp_edit_item = self.item
                    msg = translate("delete_item_query") + "\n(" + self.item.get("name", "") + ")"
                    self.app._save_current_state()
                    self.app.current_view = DialogView(self.view_manager, self.app, translate("warning"), msg, self._on_delete_confirm)
                    self.app.current_view_name = "add_dialog"
                    return None
                
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
                        self.app._switch_view("pantry_edit")
                        
                    self.app._dialog_return_view = self.app.current_view_name
                    self.app._save_current_state()
                    self.app.current_view = AisleSelectView(self.view_manager, self.app, cur_val, _cat_cb)
                    self.app.current_view_name = "add_dialog"
                    return None
                
                if key == "clone":
                    pantry = self.app.storage.get_pantry_items()
                    new_item = self.item.copy()
                    base_name = new_item.get("name", "")
                    new_name = base_name + " (copy)"
                    
                    # Check for duplicates and increment suffix
                    existing_names = {i.get("name") for i in pantry}
                    if new_name in existing_names:
                        suffix = 2
                        while f"{base_name} (copy {suffix})" in existing_names:
                            suffix += 1
                        new_name = f"{base_name} (copy {suffix})"
                        
                    new_item["name"] = new_name
                    self.item = new_item
                    self.item_idx = None # Mark as new
                    self._needs_save = True
                    return "EXIT"
                
                self._editing = True
                self.reset_cursor()
                self._input_buffer = str(self.item.get(key, ""))
                self._cursor_pos = len(self._input_buffer)
                self._is_selecting = True
                self._dirty = True

        if self._dirty:
            self._draw()
        return None

