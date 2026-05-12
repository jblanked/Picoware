from micropython import const
from picoware.system.vector import Vector
from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_CENTER, BUTTON_BACK, BUTTON_DELETE, BUTTON_BACKSPACE
from grocery_lib.i18n import translate
from grocery_lib.ui_utils import draw_header, draw_footer, draw_card, draw_icon, draw_text_price, C_BG, C_TEXT, C_PAPER, C_ACCENT, C_SEL, C_SHADOW, _V1, _V2
from grocery_lib.base_view import BaseView
from grocery_lib.format_utils import format_price
from grocery_lib.config import get_config

_BAR_H = const(24)
_MARGIN = const(4)
_ITEM_H = const(30)
_SPACING = const(4)

class CompareView(BaseView):
    __slots__ = ("vals", "_selected_idx", "_card_size", "_input_buffer", "sep", "_cursor_pos", "_is_selecting", "_last_idx", "_last_best")

    def __init__(self, view_manager, app):
        super().__init__(view_manager, app)
        
        # [Price A, Size A, Price B, Size B]
        self.vals = [1.0, 100.0, 1.0, 100.0]
        self._selected_idx = 0
        self._last_idx = 0
        self._last_best = -1
        self.sep = get_config("decimal_separator")
        self._input_buffer = self._format_val(self.vals[0])
        self._cursor_pos = len(self._input_buffer)
        self._is_selecting = True
        
        self._card_size = Vector(self.draw.size.x - (_MARGIN * 2), _ITEM_H)
        
        self._draw(True)

    def stop(self):
        pass

    def _format_val(self, val):
        s = str(val)
        if s.endswith(".0"): s = s[:-2]
        return s

    def _get_unit_prices(self):
        up_a = self.vals[0] / self.vals[1] if self.vals[1] > 0 else 0
        up_b = self.vals[2] / self.vals[3] if self.vals[3] > 0 else 0
        return up_a, up_b

    def _try_parse(self):
        try:
            val = float(self._input_buffer.replace(",", "."))
            if val >= 0:
                self.vals[self._selected_idx] = val
        except (ValueError, TypeError): pass

    def _draw(self, full=False):
        if not self._dirty and not full: return
        
        from grocery_lib.ui_utils import draw_text_price, draw_icon

        up_a, up_b = self._get_unit_prices()
        best = -1
        if up_a > 0 and up_b > 0:
            if up_a < up_b: best = 0
            elif up_b < up_a: best = 1
            
        if best != self._last_best: full = True
            
        start_y = 30 
        col_w = (self.draw.size.x // 2) - 6
        card_size = Vector(col_w, 40) # Taller cards for vertical stacking
        
        if full:
            self.draw.fill_screen(C_BG)
            draw_header(self.draw, translate("compare_price"), _BAR_H)
            draw_footer(self.draw, translate("hint_compare"), _BAR_H)

            for item_idx in range(2):
                col_x = 4 if item_idx == 0 else (self.draw.size.x // 2) + 2
                is_best = (best == item_idx)
                
                # --- Column Header ---
                _V1.x, _V1.y = col_x, start_y
                _V2.x, _V2.y = col_w, 42
                header_bg = C_ACCENT if is_best else C_PAPER
                self.draw.fill_round_rectangle(_V1, _V2, 6, header_bg)
                
                title = translate("item_a") if item_idx == 0 else translate("item_b")
                tc = C_PAPER if is_best else C_TEXT
                self.draw.text(Vector(col_x + 6, start_y + 4), title, tc, 0)
                
                # Unit Price below Title
                up_val = up_a if item_idx == 0 else up_b
                up_str = format_price(up_val, self.sep) + "/" + translate("calc_size").lower()
                up_tc = C_BG if is_best else C_SHADOW
                draw_text_price(self.draw, Vector(col_x + 6, start_y + 22), up_str, up_tc)
                
                row_y = start_y + 48
                for sub_idx in range(2):
                    idx = item_idx * 2 + sub_idx
                    self._draw_field(idx, item_idx, sub_idx, col_x, row_y, col_w, card_size)

            # --- Result Box ---
            if best != -1:
                row_y = start_y + 48
                res_y = row_y + 90
                res_h = 32
                res_w = self.draw.size.x - 20
                res_x = 10
                
                # Box
                _V1.x, _V1.y = res_x, res_y
                _V2.x, _V2.y = res_w, res_h
                self.draw.fill_round_rectangle(_V1, _V2, 8, C_ACCENT)
                # Inner Paper
                _V1.x, _V1.y = res_x + 2, res_y + 2
                _V2.x, _V2.y = res_w - 4, res_h - 4
                self.draw.fill_round_rectangle(_V1, _V2, 6, C_PAPER)
                
                winner_text = translate("item_a") if best == 0 else translate("item_b")
                result_msg = f"{translate('best_value')}: {winner_text}"
                
                # Icon
                draw_icon(self.draw, "star", res_x + 8, res_y + (res_h - 12) // 2, C_ACCENT)
                
                # Text centered in box
                tw = self.draw.len(result_msg, 0)
                tx = res_x + (res_w - tw) // 2
                ty = res_y + (res_h - self.draw.font_size.y) // 2
                self.draw.text(Vector(tx, ty), result_msg, C_TEXT, 0)
        else:
            row_y = start_y + 48
            for idx in (self._last_idx, self._selected_idx):
                item_idx = idx // 2
                sub_idx = idx % 2
                col_x = 4 if item_idx == 0 else (self.draw.size.x // 2) + 2
                self._draw_field(idx, item_idx, sub_idx, col_x, row_y, col_w, card_size)

        self.draw.swap()
        self._last_idx = self._selected_idx
        self._last_best = best
        self._dirty = False

    def _draw_field(self, idx, item_idx, sub_idx, col_x, row_y, col_w, card_size):
        is_sel = (self._selected_idx == idx)
        label = translate("price") if sub_idx == 0 else translate("size")
        y = row_y + sub_idx * 44
        
        self._scratch_pos.x, self._scratch_pos.y = col_x, y
        draw_card(self.draw, self._scratch_pos, card_size, 4, is_sel)
        
        # Label (Small/Dim)
        self.draw.text(Vector(col_x + 6, y + 4), label, C_SHADOW, 0)
        
        # Value (Main)
        val_str = self._input_buffer if is_sel else self._format_val(self.vals[idx])
        v_w = self.draw.len(val_str, 0)
        vx = col_x + col_w - v_w - 8
        
        if is_sel and self._is_selecting:
            _V1.x, _V1.y = vx - 2, y + 17
            _V2.x, _V2.y = v_w + 4, self.draw.font_size.y + 2
            self.draw.fill_rectangle(_V1, _V2, C_SEL)
        
        self.draw.text(Vector(vx, y + 18), val_str, C_TEXT, 0)
        
        if is_sel and not self._is_selecting and self._cursor_visible:
            cx = vx + self.draw.len(val_str[:self._cursor_pos], 0)
            self.draw.line_custom(Vector(cx, y + 16), Vector(cx, y + 32), C_TEXT)

    def run(self):
        self._check_cursor()
        from picoware.system.buttons import BUTTON_TAB
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
            up_a, up_b = self._get_unit_prices()
            best = -1
            if up_a > 0 and up_b > 0:
                if up_a < up_b: best = 0
                elif up_b < up_a: best = 1
            
            if best != -1:
                self.app._temp_save_data = {
                    "price": self.vals[best * 2],
                    "size": self.vals[best * 2 + 1]
                }
                return "SAVE_BEST_DEAL"
            return None
        
        if btn == BUTTON_UP:
            input_manager.reset()
            self._try_parse()
            self._selected_idx = (self._selected_idx - 1) % 4
            self._input_buffer = self._format_val(self.vals[self._selected_idx])
            self._cursor_pos = len(self._input_buffer)
            self._is_selecting = True
            self._dirty = True
        elif btn == BUTTON_DOWN:
            input_manager.reset()
            self._try_parse()
            self._selected_idx = (self._selected_idx + 1) % 4
            self._input_buffer = self._format_val(self.vals[self._selected_idx])
            self._cursor_pos = len(self._input_buffer)
            self._is_selecting = True
            self._dirty = True
        elif btn in (BUTTON_CENTER, 13):
            input_manager.reset()
            self._try_parse()
            self._selected_idx = (self._selected_idx + 1) % 4
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
