import utime
from micropython import const
from picoware.system.vector import Vector
from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_CENTER, BUTTON_BACK, BUTTON_ENTER, BUTTON_DELETE, BUTTON_BACKSPACE, BUTTON_TAB
from grocery_lib.i18n import translate
from grocery_lib.config import get_config
from grocery_lib.ui_utils import draw_header, draw_footer, draw_lcd_string, C_BG, C_TEXT, C_PAPER, C_SHADOW, C_SEL, C_CARD, C_ACCENT
from grocery_lib.base_view import BaseView

_BAR_H = const(24)
_MARGIN = const(4)
_FEEDBACK_MS = const(120)
_SAVED_MS = const(1500)

# Operator Pastel Palette
_C_PLUS = const(0x9E66)   
_C_MINUS = const(0xF410)  
_C_MULT = const(0x841F)   
_C_DIV = const(0xC5F9)    

class QuickCalcView(BaseView):
    __slots__ = ("total", "input_buf", "pending_op", "feedback_op", "feedback_time",
                 "new_calc", "sep", "history", "tax_applied", "_saved_feedback")
    def __init__(self, view_manager, app):
        super().__init__(view_manager, app)
        self.total = 0.0
        self.input_buf = ""
        self.pending_op = ""
        self.history = ""
        self.new_calc = False
        self.tax_applied = False
        self._saved_feedback = 0 # timestamp
        self.feedback_op = None
        self.feedback_time = 0
        self.sep = get_config("decimal_separator")
        self._draw()

    def stop(self):
        pass

    def _draw_op_button(self, pos, size, op, is_active):
        bx, by = pos.x - size.x//2, pos.y - size.y//2
        op_c = _C_PLUS
        if op == "-": op_c = _C_MINUS
        elif op == "*": op_c = _C_MULT
        elif op == "/": op_c = _C_DIV
        elif op == "=": op_c = C_SEL
        
        base_color, symbol_c = (const(0xFFFF), op_c) if is_active else (op_c, const(0xFFFF))
        self.draw.fill_round_rectangle(Vector(bx, by), size, 8, base_color)
        
        s = 10 
        if op == "+":
            self.draw.fill_rectangle(Vector(pos.x - 2, pos.y - s), Vector(4, s*2), symbol_c)
            self.draw.fill_rectangle(Vector(pos.x - s, pos.y - 2), Vector(s*2, 4), symbol_c)
        elif op == "-":
            self.draw.fill_rectangle(Vector(pos.x - s, pos.y - 2), Vector(s*2, 4), symbol_c)
        elif op == "*":
            for i in range(-s, s):
                for offset in range(-2, 2):
                    self.draw.pixel(Vector(pos.x + i + offset, pos.y + i), symbol_c)
                    self.draw.pixel(Vector(pos.x + i + offset, pos.y - i), symbol_c)
        elif op == "/":
            for i in range(-s, s):
                for offset in range(-2, 2):
                    self.draw.pixel(Vector(pos.x + i + offset, pos.y - i), symbol_c)
        elif op == "=":
            self.draw.fill_rectangle(Vector(pos.x - s, pos.y - 6), Vector(s*2, 4), symbol_c)
            self.draw.fill_rectangle(Vector(pos.x - s, pos.y + 2), Vector(s*2, 4), symbol_c)

    def _draw_lcd_op(self, pos, op, color):
        cx, cy = pos.x + 6, pos.y + 6
        t, s = 2, 5
        if op == "+":
            self.draw.fill_rectangle(Vector(cx - t//2, cy - s), Vector(t, s*2), color)
            self.draw.fill_rectangle(Vector(cx - s, cy - t//2), Vector(s*2, t), color)
        elif op == "-":
            self.draw.fill_rectangle(Vector(cx - s, cy - t//2), Vector(s*2, t), color)
        elif op == "*":
            for i in range(-s, s):
                self.draw.pixel(Vector(cx + i, cy + i), color)
                self.draw.pixel(Vector(cx + i, cy - i), color)
        elif op == "/":
            for i in range(-s, s):
                self.draw.pixel(Vector(cx + i, cy - i), color)

    def _draw(self):
        if not self._dirty: return
        self.draw.fill_screen(C_BG)
        draw_header(self.draw, translate("quick_calc"), _BAR_H)
        
        # LCD Panel
        px, py = _MARGIN, _BAR_H + _MARGIN + 5
        pw, ph = self.draw.size.x - _MARGIN*2, 108
        self.draw.fill_round_rectangle(Vector(px, py), Vector(pw, ph), 4, C_PAPER)
        self.draw.rect(Vector(px, py), Vector(pw, ph), C_SHADOW) # subtle border instead
        
        lcd_x, lcd_y = px + 2, py + 2
        self.draw.text(Vector(lcd_x + 6, lcd_y + 4), translate("total").upper(), C_TEXT, 0)
        
        if self.history:
            self.draw.text(Vector(lcd_x + 6, lcd_y + 24), self.history, C_SHADOW, 0)
        
        if self.tax_applied:
            from grocery_lib.format_utils import get_tax_info
            _, label = get_tax_info()
            self.draw.fill_round_rectangle(Vector(lcd_x + 6, lcd_y + 85), Vector(35, 14), 4, const(0xFBE7))
            self.draw.text(Vector(lcd_x + 10, lcd_y + 86), label, C_TEXT, 0)
        
        if utime.ticks_diff(utime.ticks_ms(), self._saved_feedback) < _SAVED_MS:
            self.draw.text(Vector(lcd_x + 45, lcd_y + 86), translate("calc_saved"), C_SEL, 0)
        
        # Dynamic Hint
        hint = translate("calc_hint_tax") if not self.input_buf else translate("calc_hint_perc")
        if self.new_calc: hint = translate("calc_hint_save")
        hw = self.draw.len(hint, 0)
        self.draw.text(Vector(lcd_x + pw - hw - 10, lcd_y + ph - 15), hint, C_SHADOW, 0)

        if self.pending_op:
            self._draw_lcd_op(Vector(lcd_x + 8, lcd_y + 35), self.pending_op, C_TEXT)

        total_str = f"{self.total:.2f}".replace(".", self.sep)
        tw = len(total_str.replace(self.sep, "")) * 14 + (len(total_str.replace(self.sep, "")) - 1) * 4
        draw_lcd_string(self.draw, Vector(lcd_x + (pw - 20) - tw, lcd_y + 10), total_str, 14, 24, 4, C_TEXT)
        
        input_str = self.input_buf if self.input_buf else "0"
        if len(input_str) > 8: input_str = input_str[-8:]
        char_count = len(input_str.replace(".", "").replace(",", ""))
        iw = char_count * 18 + (char_count - 1) * 6
        draw_lcd_string(self.draw, Vector(lcd_x + (pw - 20) - iw, lcd_y + 45), input_str, 18, 34, 6, C_TEXT)

        # Operator Group background
        cx, cy = self.draw.size.x // 2, 215
        self.draw.fill_round_rectangle(Vector(cx - 95, cy - 70), Vector(190, 140), 12, C_PAPER)
        
        now = utime.ticks_ms()
        btn_map = [
            ("+", BUTTON_UP, Vector(cx, cy - 45)),
            ("-", BUTTON_DOWN, Vector(cx, cy + 45)),
            ("*", BUTTON_LEFT, Vector(cx - 65, cy)),
            ("/", BUTTON_RIGHT, Vector(cx + 65, cy)),
            ("=", BUTTON_CENTER, Vector(cx, cy))
        ]
        
        for op, btn_id, bpos in btn_map:
            active = (self.feedback_op == btn_id)
            if not active:
                if btn_id == BUTTON_UP: active = (self.pending_op == "+")
                elif btn_id == BUTTON_DOWN: active = (self.pending_op == "-")
                elif btn_id == BUTTON_LEFT: active = (self.pending_op == "*")
                elif btn_id == BUTTON_RIGHT: active = (self.pending_op == "/")
            
            if self.feedback_op == btn_id and utime.ticks_diff(now, self.feedback_time) >= _FEEDBACK_MS:
                active = False
            
            self._draw_op_button(bpos, Vector(40, 32), op, active)

        draw_footer(self.draw, translate("hint_quick_calc"), _BAR_H)
        self.draw.swap()
        self._dirty = False

    def _apply_math(self, next_op=""):
        if not self.input_buf: 
            if next_op: self.history = f"{self.total:.2f} {next_op}"
            return
        try:
            val = float(self.input_buf.replace(",", "."))
            old_total = self.total
            op = self.pending_op or "+"
            
            if op == "+": self.total += val
            elif op == "-": self.total -= val
            elif op == "*": self.total *= val
            elif op == "/" and val != 0: self.total /= val
            
            self.history = f"{old_total:.2f} {op} {val:.2f}"
            if next_op: self.history += f" {next_op}"
            self.input_buf = ""
        except: pass

    def run(self):
        input_manager = self.view_manager.input_manager
        btn = input_manager.button
        
        if self.feedback_op is not None or utime.ticks_diff(utime.ticks_ms(), self._saved_feedback) < _SAVED_MS:
            if self.feedback_op is not None and utime.ticks_diff(utime.ticks_ms(), self.feedback_time) > _FEEDBACK_MS:
                self.feedback_op = None
            self._dirty = True

        if btn == BUTTON_BACK:
            input_manager.reset()
            if self.input_buf:
                self.input_buf = ""
            elif self.total != 0 or self.pending_op or self.history or self.tax_applied:
                self.total = 0.0
                self.pending_op = ""
                self.history = ""
                self.new_calc = False
                self.tax_applied = False
            else:
                return "EXIT_QUICK_CALC"
            self._dirty = True
            return None

        if btn == BUTTON_TAB:
            input_manager.reset()
            if self.input_buf:
                try:
                    val = float(self.input_buf.replace(",", "."))
                    perc_val = (self.total * val) / 100.0
                    self.input_buf = f"{perc_val:.2f}".replace(".", self.sep)
                except: pass
            else:
                from grocery_lib.format_utils import get_tax_info
                rate, _ = get_tax_info()
                if not self.tax_applied:
                    self.total *= (1.0 + rate)
                    self.tax_applied = True
                else:
                    self.total /= (1.0 + rate)
                    self.tax_applied = False
                self.new_calc = True
            self._dirty = True
            return None

        if btn in (127, BUTTON_BACKSPACE, BUTTON_DELETE):
            input_manager.reset()
            if self.input_buf:
                self.input_buf = self.input_buf[:-1]
                self._dirty = True
            return None

        char = input_manager.button_to_char(btn)
        if char and (char.isdigit() or char in (".", ",")):
            input_manager.reset()
            if self.new_calc:
                if not self.tax_applied: self.total = 0
                self.pending_op = ""
                self.new_calc = False
            if char in (".", ","):
                if "." in self.input_buf or "," in self.input_buf: return None
                char = self.sep
            if len(self.input_buf) < 10:
                self.input_buf += char
                self._dirty = True
            return None

        if btn in (BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_CENTER, BUTTON_ENTER):
            input_manager.reset()
            if btn in (BUTTON_CENTER, BUTTON_ENTER):
                if self.new_calc:
                    from grocery_lib.add_view import AddView
                    def _save_cb(name):
                        self.app.storage.add_item(self.app.active_list, name if name else f"Misc ({self.total:.2f})", 1, self.total)
                        self._saved_feedback = utime.ticks_ms()
                        self.app._switch_view("quick_calc")
                    self.app.current_view = AddView(self.view_manager, self.app, translate("name"), _save_cb)
                    self.app.current_view_name = "add_dialog"
                    return None
                else:
                    self._apply_math()
                    self.pending_op = ""
                    self.new_calc = True
                    self.feedback_op = BUTTON_CENTER
            else:
                self.new_calc = False
                op_map = {BUTTON_UP: "+", BUTTON_DOWN: "-", BUTTON_LEFT: "*", BUTTON_RIGHT: "/"}
                next_op = op_map.get(btn)
                self._apply_math(next_op)
                self.pending_op = next_op
                self.feedback_op = btn
            
            self.feedback_time = utime.ticks_ms()
            self._dirty = True
            return None
        
        if self._dirty: self._draw()
        return None
