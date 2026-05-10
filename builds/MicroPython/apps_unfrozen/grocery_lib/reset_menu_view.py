from grocery_lib.i18n import translate
from grocery_lib.ui_utils import draw_header, draw_footer, draw_card, draw_icon, C_BG, C_TEXT, C_RED, C_PAPER
from grocery_lib.base_view import BaseView
from micropython import const
from picoware.system.vector import Vector

_BAR_H = const(24)
_MARGIN = const(4)
_SPACING = const(4)
_ITEM_H = const(32)
_CARD_RADIUS = const(6)

class ResetMenuView(BaseView):
    """View for destructive reset actions."""
    __slots__ = ("_options", "_selected_index", "_card_size", "_last_idx")

    def __init__(self, view_manager, app):
        super().__init__(view_manager, app)
        self._options = ["clear_lists", "clear_pantry"]
        self._selected_index = 0
        self._last_idx = 0
        self._card_size = Vector(self.draw.size.x - (_MARGIN * 2), _ITEM_H)
        self._draw(True)

    def _draw(self, full=False):
        if not self._dirty and not full: return
        
        start_y = _BAR_H + _MARGIN
        if full:
            self.draw.fill_screen(C_BG)
            draw_header(self.draw, translate("reset"), _BAR_H)
            for i in range(len(self._options)):
                self._draw_row(i, start_y)
            draw_footer(self.draw, translate("hint_select"), _BAR_H)
        else:
            self._draw_row(self._last_idx, start_y)
            self._draw_row(self._selected_index, start_y)
            
        self.draw.swap()
        self._last_idx = self._selected_index
        self._dirty = False

    def _draw_row(self, i, start_y):
        if i < 0 or i >= len(self._options): return
        
        is_selected = (i == self._selected_index)
        y = start_y + i * (_ITEM_H + _SPACING)
        pos = self._scratch_pos
        pos.x, pos.y = _MARGIN, y
        
        draw_card(self.draw, pos, self._card_size, _CARD_RADIUS, is_selected)
        
        key = self._options[i]
        label = translate(key)
        
        # Danger Icon in Red
        draw_icon(self.draw, "trash", _MARGIN + 10, y + (_ITEM_H - 12) // 2, C_RED)
        
        # Label in Red if selected for extra caution
        color = C_RED if is_selected else C_TEXT
        pos.x, pos.y = _MARGIN + 35, y + (_ITEM_H - self.draw.font_size.y) // 2
        self.draw.text(pos, label, color, 0)

    def _on_confirm_lists(self, res):
        if res == "OK":
            self.app.storage.reset_all_lists()
            self.app._switch_view("reset_menu")

    def _on_confirm_pantry(self, res):
        if res == "OK":
            self.app.storage.reset_pantry()
            self.app._switch_view("reset_menu")

    def run(self):
        from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_CENTER, BUTTON_BACK
        input_manager = self.view_manager.input_manager
        btn = input_manager.button

        if btn == BUTTON_BACK:
            input_manager.reset()
            return "settings"
        elif btn == BUTTON_UP:
            input_manager.reset()
            self._selected_index = (self._selected_index - 1) % len(self._options)
            self._dirty = True
            self._draw()
        elif btn == BUTTON_DOWN:
            input_manager.reset()
            self._selected_index = (self._selected_index + 1) % len(self._options)
            self._dirty = True
            self._draw()
        elif btn == BUTTON_CENTER:
            input_manager.reset()
            from grocery_lib.dialog_view import DialogView
            msg = translate("destructive_warning") + "\n" + translate("destructive_info")
            
            callback = self._on_confirm_lists if self._selected_index == 0 else self._on_confirm_pantry
            self.app.current_view = DialogView(self.view_manager, self.app, translate("warning"), msg, callback, is_alert=True)
            self.app.current_view_name = "add_dialog"
            return None
        return None
