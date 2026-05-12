from grocery_lib.i18n import translate
from grocery_lib.ui_utils import draw_modal_frame, draw_lcd_string, C_BG, C_TEXT, C_PAPER, C_SHADOW, C_CARD, C_RED
from grocery_lib.base_view import BaseView
from micropython import const
from picoware.system.vector import Vector

class DialogView(BaseView):
    """View for displaying simple modal messages with confirmation."""
    __slots__ = ("title", "message", "callback", "lcd_text", "_w", "_h", "_frame", "is_alert", "_lines")

    def __init__(self, view_manager, app, title, message, callback=None, lcd_text=None, is_alert=False):
        super().__init__(view_manager, app)
        self.title = title
        self.message = message
        self.callback = callback
        self.lcd_text = lcd_text
        self.is_alert = is_alert
        
        # Handle Multi-line text
        self._lines = message.split("\n")
        max_line_w = 0
        for line in self._lines:
            max_line_w = max(max_line_w, self.draw.len(line, 0))
            
        # Calculate size based on longest line
        self._w = min(self.draw.size.x - 20, max(180, max_line_w + 40))
        
        line_h = 16
        self._h = 80 + (len(self._lines) * line_h)
        if self.lcd_text:
            self._h += 50
            
        self._frame = None
        self._draw()

    def _draw(self):
        if not self._dirty: return
        
        header_bg = C_RED if self.is_alert else None
        self._frame = draw_modal_frame(self.draw, self.title, self._w, self._h, header_bg)
        x, y, w, h, fh = self._frame
        
        # Draw Message Lines
        line_h = 16
        start_y = y + 35
        for i, line in enumerate(self._lines):
            line_w = self.draw.len(line, 0)
            ly = start_y + (i * line_h)
            self.draw.text(Vector(x + (w - line_w) // 2, ly), line, C_RED if self.is_alert else C_TEXT, 0)

        # Draw LCD Text if provided
        if self.lcd_text:
            lcd_box_h = 44
            lcd_box_y = start_y + (len(self._lines) * line_h) + 10
            # Rounded LCD box
            self.draw.fill_round_rectangle(Vector(x + 10, lcd_box_y), Vector(w - 20, lcd_box_h), 6, C_PAPER)
            
            char_count = len(self.lcd_text.replace(".", "").replace(",", ""))
            digit_w, digit_h, spacing = 18, 34, 6
            tw = char_count * digit_w + (char_count - 1) * spacing
            if tw > w - 40:
                digit_w, digit_h, spacing = 14, 24, 4
                tw = char_count * digit_w + (char_count - 1) * spacing

            lcd_x = x + (w - tw) // 2
            lcd_y = lcd_box_y + (lcd_box_h - digit_h) // 2
            draw_lcd_string(self.draw, Vector(lcd_x, lcd_y), self.lcd_text, digit_w, digit_h, spacing, C_TEXT)
        
        # Draw Footer Actions
        if self.callback:
            hint = f"{translate('btn_ok')} (CTR) | {translate('cancel')} (BACK)"
        else:
            hint = translate("btn_ok")
            
        hint_w = self.draw.len(hint, 0)
        hx = x + (w - hint_w) // 2
        hy = y + h - fh + (fh - self.draw.font_size.y) // 2
        self.draw.text(Vector(hx, hy), hint, C_TEXT, 0)
        
        self.draw.swap()
        self._dirty = False

    def run(self):
        from picoware.system.buttons import BUTTON_CENTER, BUTTON_BACK, BUTTON_ENTER
        input_manager = self.view_manager.input_manager
        button = input_manager.button

        if button in (BUTTON_CENTER, BUTTON_ENTER):
            input_manager.reset()
            if self.callback:
                self.callback("OK")
            return "EXIT"
        elif button == BUTTON_BACK:
            input_manager.reset()
            if self.callback:
                self.callback("CANCEL")
            return "EXIT"
        return None
