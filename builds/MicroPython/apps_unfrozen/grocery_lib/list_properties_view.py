from micropython import const
from picoware.system.vector import Vector
from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_CENTER, BUTTON_BACK, BUTTON_BACKSPACE, BUTTON_DELETE
from grocery_lib.i18n import translate
from grocery_lib.ui_utils import draw_header, draw_footer, draw_card, draw_icon, C_BG, C_TEXT, C_PAPER, C_ACCENT, C_SEL
from grocery_lib.base_view import BaseView
from grocery_lib.config import get_config, set_config

_BAR_H = const(24)
_MARGIN = const(4)
_ITEM_H = const(32)
_SPACING = const(6)
_CARD_RADIUS = const(6)

class ListPropertiesView(BaseView):
    """View for editing shopping list properties (name, budget, cleanup)."""
    __slots__ = ("list_name", "properties", "_selected_index", "_card_size", "_title", "_editing", "_input_buffer", "_cursor_pos", "_is_selecting", "_needs_save")

    def __init__(self, view_manager, app):
        super().__init__(view_manager, app)
        self.list_name = app.active_list
        self._title = translate("list_properties")
        self._needs_save = False
        
        budgets = get_config("list_budgets")
        budget = budgets.get(self.list_name, get_config("base_budget"))
        
        self.properties = [
            ("name", translate("name"), self.list_name),
            ("budget", translate("budget"), str(budget)),
            ("clone", translate("clone_list"), ""),
            ("clear", translate("clear_checked"), ""),
            ("clear_all", translate("clear_items_query").replace("?", ""), ""),
            ("delete", translate("delete_list"), "")
        ]
        
        self._selected_index = 0
        self._editing = False
        self._input_buffer = ""
        self._cursor_pos = 0
        self._is_selecting = False
        
        self._card_size = Vector(self.draw.size.x - (_MARGIN * 2), _ITEM_H)
        self._draw()

    def _on_delete_list_confirm(self, res):
        if res == "OK":
            self._deleted = True
            self.app.storage.remove_list(self.list_name)
            self.app._switch_view("shopping_list")
    def _on_clear_checked_confirm(self, res):
        if res == "OK":
            items = self.app.storage.get_items(self.list_name)
            items = [i for i in items if not i.get("bought", False)]
            self.app.storage.save_items(self.list_name, items)
            self.app._switch_view("list_items")

    def _on_clear_all_confirm(self, res):
        if res == "OK":
            self.app.storage.save_items(self.list_name, [])
            self.app._switch_view("list_items")

    def _draw(self):
        if not self._dirty: return
        self.draw.fill_screen(C_BG)
        draw_header(self.draw, self._title, _BAR_H)
        
        start_y = _BAR_H + _MARGIN + 5
        for i in range(len(self.properties)):
            is_selected = (i == self._selected_index)
            y = start_y + i * (_ITEM_H + _SPACING)
            key, label, val = self.properties[i]
            
            self._scratch_pos.x, self._scratch_pos.y = _MARGIN, y
            draw_card(self.draw, self._scratch_pos, self._card_size, _CARD_RADIUS, is_selected)
            
            # Label
            self._scratch_pos.x, self._scratch_pos.y = _MARGIN + 12, y + (_ITEM_H - self.draw.font_size.y) // 2
            prefix = f"{label}: "
            self.draw.text(self._scratch_pos, prefix, C_TEXT, 0)
            
            # Value
            if is_selected and self._editing:
                val = self._input_buffer
                pre = val[:self._cursor_pos]
                post = val[self._cursor_pos:]
                px = self._scratch_pos.x + self.draw.len(prefix, 0)
                
                if self._is_selecting and val:
                    vw = self.draw.len(val, 0)
                    self.draw.fill_rectangle(Vector(px - 2, y + 4), Vector(vw + 4, _ITEM_H - 8), C_SEL)
                
                self.draw.text(Vector(px, self._scratch_pos.y), pre, C_TEXT, 0)
                cx = px + self.draw.len(pre, 0)
                if not self._is_selecting and self._cursor_visible:
                    self.draw.line_custom(Vector(cx, self._scratch_pos.y + 12), Vector(cx + 8, self._scratch_pos.y + 12), C_TEXT)
                self.draw.text(Vector(cx + 2, self._scratch_pos.y), post, C_TEXT, 0)
            else:
                px = self._scratch_pos.x + self.draw.len(prefix, 0)
                if val:
                    self.draw.text(Vector(px, self._scratch_pos.y), str(val), C_TEXT, 0)
                
                if key in ("name", "budget"): icon = "edit"
                elif key == "delete": icon = "trash"
                elif key == "clone": icon = "add_item"
                else: icon = "sweep" # clear, clear_all
                
                draw_icon(self.draw, icon, self.draw.size.x - _MARGIN - 20, y + (_ITEM_H - 12) // 2)

        draw_footer(self.draw, translate("hint_list_props"), _BAR_H)
        self.draw.swap()
        self._dirty = False

    def stop(self):
        # Save changes if anything changed and we didn't just delete the list
        if not hasattr(self, "_deleted") or not self._deleted:
            if self._editing:
                key, label, old_val = self.properties[self._selected_index]
                if self._input_buffer != old_val:
                    self.properties[self._selected_index] = (key, label, self._input_buffer)
                    self._needs_save = True

            if self._needs_save:
                from grocery_lib.config import get_config, set_config
                new_name = self.properties[0][2]
                try: new_budget = float(str(self.properties[1][2]).replace(",", "."))
                except (ValueError, TypeError): new_budget = 0.0
                
                if new_name != self.list_name:
                    self.app.storage.rename_list(self.list_name, new_name)
                    self.app.active_list = new_name
                
                budgets = get_config("list_budgets")
                budgets[self.app.active_list] = new_budget
                set_config("list_budgets", budgets)

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
            if btn == BUTTON_CENTER:
                input_manager.reset()
                key, label, old_val = self.properties[self._selected_index]
                if self._input_buffer != old_val:
                    self.properties[self._selected_index] = (key, label, self._input_buffer)
                    self._needs_save = True
                self._editing = False
                self._is_selecting = False
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
                self._selected_index = (self._selected_index - 1) % len(self.properties)
                self._dirty = True
            elif btn == BUTTON_DOWN:
                input_manager.reset()
                self._selected_index = (self._selected_index + 1) % len(self.properties)
                self._dirty = True
            elif btn == BUTTON_CENTER:
                input_manager.reset()
                key = self.properties[self._selected_index][0]
                
                from grocery_lib.dialog_view import DialogView
                
                if key == "delete":
                    self.app.current_view = DialogView(self.view_manager, self.app, translate("delete"), translate("delete_list") + "?", self._on_delete_list_confirm)
                    self.app.current_view_name = "add_dialog"
                    return None
                elif key == "clone":
                    items = self.app.storage.get_items(self.list_name)
                    new_name = self.list_name + " (1)"
                    self.app.storage.save_items(new_name, [i.copy() for i in items])
                    return "shopping_list"
                elif key == "clear":
                    self.app.current_view = DialogView(self.view_manager, self.app, translate("clear_checked"), translate("clear_checked_query"), self._on_clear_checked_confirm)
                    self.app.current_view_name = "add_dialog"
                    return None
                elif key == "clear_all":
                    self.app.current_view = DialogView(self.view_manager, self.app, translate("delete"), translate("clear_items_query"), self._on_clear_all_confirm)
                    self.app.current_view_name = "add_dialog"
                    return None
                
                self._editing = True
                self.reset_cursor()
                self._input_buffer = str(self.properties[self._selected_index][2])
                self._cursor_pos = len(self._input_buffer)
                self._is_selecting = True
                self._dirty = True

        if self._dirty:
            self._draw()
        return None
