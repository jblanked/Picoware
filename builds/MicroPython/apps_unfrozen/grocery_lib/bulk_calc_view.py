from micropython import const
from picoware.system.vector import Vector
from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_CENTER, BUTTON_BACK, BUTTON_ENTER, BUTTON_DELETE, BUTTON_BACKSPACE
from grocery_lib.i18n import translate
from grocery_lib.ui_utils import draw_header, draw_footer, draw_card, draw_icon, C_BG, C_TEXT, C_PAPER, C_ACCENT, C_SEL, _V1, _V2
from grocery_lib.base_view import BaseView
from grocery_lib.format_utils import format_price
from grocery_lib.config import get_config

_BAR_H = const(24)
_MARGIN = const(4)
_ITEM_H = const(32)
_SPACING = const(6)

_C_DIV = const(0xC5F9)    
_C_MULT = const(0x841F)   

class BulkCalcView(BaseView):
    __slots__ = ("vals", "_selected_idx", "_card_size", "_input_buffer", "sep", "_initialized", "_cursor_pos", "_is_selecting")

    def __init__(self, view_manager, app):
        super().__init__(view_manager, app)
        
        # [Price, Quantity, Discount%]
        self.vals = [1.0, 1.0, 0.0]
        self._selected_idx = 0
        self.sep = get_config("decimal_separator")
        self._input_buffer = self._format_val(self.vals[0])
        self._cursor_pos = len(self._input_buffer)
        self._is_selecting = True
        
        self._card_size = Vector(self.draw.size.x - (_MARGIN * 2), _ITEM_H)
        
        self._draw()

    def _format_val(self, val):
        s = str(val)
        if s.endswith(".0"): s = s[:-2]
        return s

    def _get_total(self):
        try:
            sub = self.vals[0] * self.vals[1]
            disc = sub * (self.vals[2] / 100.0)
            return sub - disc
        except (ValueError, TypeError):
            return 0.0

    def _try_parse(self):
        try:
            val = float(self._input_buffer.replace(",", "."))
            if val >= 0:
                self.vals[self._selected_idx] = val
        except (ValueError, TypeError): pass

    def _draw(self):
        if not self._dirty: return
        
        # Static background parts
        if not hasattr(self, "_initialized"):
            self.draw.fill_screen(C_BG)
            draw_header(self.draw, translate("bulk_calc"), _BAR_H)
            draw_footer(self.draw, translate("hint_compare"), _BAR_H)
            self._initialized = True
            
        # Clear content area
        content_y = _BAR_H + 1
        content_h = self.draw.size.y - (_BAR_H * 2) - 2
        _V1.x, _V1.y = 0, content_y
        _V2.x, _V2.y = self.draw.size.x, content_h
        self.draw.fill_rectangle(_V1, _V2, C_BG)
        
        start_y = _BAR_H + 25
        labels = [translate("price"), translate("qty"), translate("discount_percent")]
        icons = [get_config("currency"), "box", "percent"]
        
        # Section Header Pill
        header_text = translate("calc_title")
        hw = self.draw.len(header_text, 0)
        _V1.x, _V1.y = _MARGIN, start_y - 20
        _V2.x, _V2.y = hw + 12, 16
        self.draw.fill_round_rectangle(_V1, _V2, 8, _C_DIV)
        _V1.x, _V1.y = _MARGIN + 6, start_y - 18
        self.draw.text(_V1, header_text, C_TEXT, 0)

        for i in range(3):
            is_sel = (self._selected_idx == i)
            label = labels[i]
            icon_key = icons[i]
            y = start_y + i * (_ITEM_H + _SPACING)
            
            self._scratch_pos.x, self._scratch_pos.y = _MARGIN, y
            draw_card(self.draw, self._scratch_pos, self._card_size, 6, is_sel)
            
            draw_icon(self.draw, icon_key, _MARGIN + 10, y + (_ITEM_H - 12) // 2, C_TEXT)
            
            # Label
            _V1.x, _V1.y = _MARGIN + 30, y + (_ITEM_H - self.draw.font_size.y) // 2
            self.draw.text(_V1, f"{label}:", C_TEXT, 0)
            
            # Value
            val_str = self._format_val(self.vals[i])
            if is_sel:
                val_str = self._input_buffer
            
            v_w = self.draw.len(val_str, 0)
            vx = self.draw.size.x - _MARGIN - v_w - 10
            
            if is_sel:
                if self._is_selecting:
                    _V1.x, _V1.y = vx - 2, y + 2
                    _V2.x, _V2.y = v_w + 4, _ITEM_H - 4
                    self.draw.fill_rectangle(_V1, _V2, C_SEL)
                
                text_y = y + (_ITEM_H - self.draw.font_size.y) // 2
                self.draw.text(Vector(vx, text_y), val_str, C_TEXT, 0)
                
                if not self._is_selecting and self._cursor_visible:
                    pre_w = self.draw.len(val_str[:self._cursor_pos], 0)
                    cx = vx + pre_w
                    self.draw.line_custom(Vector(cx, y + 6), Vector(cx, y + _ITEM_H - 6), C_TEXT)
            else:
                text_y = y + (_ITEM_H - self.draw.font_size.y) // 2
                self.draw.text(Vector(vx, text_y), val_str, C_TEXT, 0)

        # Total Result
        total = self._get_total()
        res_label = translate("total").upper()
        total_str = format_price(total, self.sep)
        
        res_y = start_y + 3 * (_ITEM_H + _SPACING) + 20
        # Cute pill for "TOTAL"
        lw = self.draw.len(res_label, 0)
        lx = (self.draw.size.x - (lw + 12)) // 2
        _V1.x, _V1.y = lx, res_y
        _V2.x, _V2.y = lw + 12, 16
        self.draw.fill_round_rectangle(_V1, _V2, 8, _C_MULT)
        _V1.x, _V1.y = lx + 6, res_y + 2
        self.draw.text(_V1, res_label, C_TEXT, 0)
        
        _V1.y = res_y + 25
        _V1.x = (self.draw.size.x - self.draw.len(total_str, 0)) // 2
        from grocery_lib.ui_utils import draw_text_price
        draw_text_price(self.draw, _V1, total_str, C_ACCENT)

        self.draw.swap()
        self._dirty = False

    def run(self):
        from picoware.system.buttons import BUTTON_LEFT, BUTTON_RIGHT, BUTTON_TAB
        input_manager = self.view_manager.input_manager
        btn = input_manager.button
        
        if btn in (6, 77, 80): # START, ESC, HOME
            input_manager.reset()
            return "HOME"
        elif btn == BUTTON_BACK:
            input_manager.reset()
            return "calculators"
        elif btn == BUTTON_TAB:
            input_manager.reset()
            total = self._get_total()
            if total > 0:
                self.app._temp_save_data = {
                    "price": total,
                    "size": 0.0 # Bulk calc doesn't have unit size per se
                }
                return "SAVE_BEST_DEAL"
            return None
        
        if btn == BUTTON_UP:
            input_manager.reset()
            self._try_parse()
            self._selected_idx = (self._selected_idx - 1) % 3
            self._input_buffer = self._format_val(self.vals[self._selected_idx])
            self._cursor_pos = len(self._input_buffer)
            self._is_selecting = True
            self._dirty = True
        elif btn == BUTTON_DOWN:
            input_manager.reset()
            self._try_parse()
            self._selected_idx = (self._selected_idx + 1) % 3
            self._input_buffer = self._format_val(self.vals[self._selected_idx])
            self._cursor_pos = len(self._input_buffer)
            self._is_selecting = True
            self._dirty = True
        elif btn in (BUTTON_CENTER, 13):
            input_manager.reset()
            self._try_parse()
            self._selected_idx = (self._selected_idx + 1) % 3
            self._input_buffer = self._format_val(self.vals[self._selected_idx])
            self._cursor_pos = len(self._input_buffer)
            self._is_selecting = True
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
            if char and (char.isdigit() or char in ('.', ',')):
                input_manager.reset()
                if char in ('.', ','): char = self.sep
                if self._is_selecting:
                    self._input_buffer = char
                    self._is_selecting = False
                    self._cursor_pos = 1
                else:
                    self._input_buffer = self._input_buffer[:self._cursor_pos] + char + self._input_buffer[self._cursor_pos:]
                    self._cursor_pos += 1
                self._try_parse()
                self._dirty = True
            elif btn in (127, BUTTON_BACKSPACE, BUTTON_DELETE):
                input_manager.reset()
                if self._is_selecting:
                    self._input_buffer = ""
                    self._is_selecting = False
                    self._cursor_pos = 0
                elif self._cursor_pos > 0:
                    self._input_buffer = self._input_buffer[:self._cursor_pos - 1] + self._input_buffer[self._cursor_pos:]
                    self._cursor_pos -= 1
                self._try_parse()
                self._dirty = True
                
        if self._dirty:
            self._draw()
        return None
