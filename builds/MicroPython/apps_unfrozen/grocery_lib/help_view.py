from grocery_lib.i18n import translate
from grocery_lib.ui_utils import draw_modal_frame, C_BG, C_TEXT, C_PAPER
from grocery_lib.base_view import BaseView
from picoware.system.vector import Vector
from grocery_lib.config import get_config
import os

class HelpView(BaseView):
    """Context-aware help view displaying information from text files."""
    __slots__ = ("_scroll_offset", "_lines", "_max_visible", "_frame", "_title", "_wrap_width")

    def __init__(self, view_manager, app):
        super().__init__(view_manager, app)
        self._scroll_offset = 0
        self._lines = []
        self._title = translate("help")
        
        # Determine wrapping width based on frame size
        fw = self.draw.size.x - 20
        self._wrap_width = fw - 25 # 10px padding each side + 5px scrollbar clearance
        
        # Determine file path
        lang = get_config("language")
        view_name = app._dialog_return_view
        if not view_name or view_name == "help":
            view_name = "main_menu"
        
        try:
            import sys
            base = "/".join(__file__.split("/")[:-1]) + "/help"
        except:
            base = "grocery_lib/help"

        path = f"{base}/{lang}/{view_name}.txt"
        if not self._file_exists(path):
            path = f"{base}/en/{view_name}.txt"
        if not self._file_exists(path):
            path = f"{base}/en/main_menu.txt"
            
        self._load_text(path)
        
        # Initial estimate, _draw will refine this
        self._max_visible = (self.draw.size.y - 80) // self.draw.font_size.y
        self._draw()

    def _file_exists(self, path):
        try:
            os.stat(path)
            return True
        except OSError:
            return False

    def _wrap_line(self, line):
        """Measurement-accurate word wrapping."""
        if not line: return [""]
        words = line.split(" ")
        wrapped = []
        curr = ""
        for w in words:
            test = w if not curr else curr + " " + w
            if self.draw.len(test, 0) <= self._wrap_width:
                curr = test
            else:
                if curr: wrapped.append(curr)
                curr = w
        if curr: wrapped.append(curr)
        return wrapped

    def _load_text(self, path):
        try:
            with open(path, "r") as f:
                content = f.read()
                raw_lines = content.split("\n")
                self._lines = []
                for rl in raw_lines:
                    if rl.strip() == "":
                        self._lines.append("")
                    else:
                        self._lines.extend(self._wrap_line(rl))
        except OSError:
            self._lines = ["Help content not found.", f"Path: {path}"]

    def _draw(self):
        if not self._dirty: return
        
        # Large modal frame
        fw, fh = self.draw.size.x - 20, self.draw.size.y - 40
        self._frame = draw_modal_frame(self.draw, self._title, fw, fh)
        fx, fy, fw, fh, f_foot_h = self._frame
        
        # Strict vertical boundaries
        start_y = fy + 30 # Top margin
        footer_y = fy + fh - f_foot_h
        content_h = footer_y - start_y - 4 # Safety buffer
        line_h = self.draw.font_size.y
        self._max_visible = content_h // line_h
        
        # Draw visible lines
        visible_count = min(len(self._lines) - self._scroll_offset, self._max_visible)
        for i in range(visible_count):
            line_idx = self._scroll_offset + i
            y = start_y + i * line_h
            self.draw.text(Vector(fx + 10, y), self._lines[line_idx], C_TEXT, 0)
            
        # Scrollbar if needed
        if len(self._lines) > self._max_visible:
            from grocery_lib.ui_utils import draw_scrollbar
            draw_scrollbar(self.draw, len(self._lines), self._max_visible, self._scroll_offset, start_y, content_h)
            
        hint = translate("btn_ok") + " (F3/BACK)"
        hint_w = self.draw.len(hint, 0)
        self.draw.text(Vector(fx + (fw - hint_w) // 2, fy + fh - f_foot_h + 4), hint, C_TEXT, 0)
        
        self.draw.swap()
        self._dirty = False

    def run(self):
        from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_BACK
        input_manager = self.view_manager.input_manager
        btn = input_manager.button
        
        if btn in (BUTTON_BACK, 89): # BACK or F3
            input_manager.reset()
            return "EXIT_HELP"
        elif btn == BUTTON_UP:
            input_manager.reset()
            self._scroll_offset = max(0, self._scroll_offset - 1)
            self._dirty = True
        elif btn == BUTTON_DOWN:
            input_manager.reset()
            self._scroll_offset = min(max(0, len(self._lines) - self._max_visible), self._scroll_offset + 1)
            self._dirty = True
            
        if self._dirty: self._draw()
        return None
