from micropython import const
from picoware.system.buttons import BUTTON_BACK, BUTTON_CENTER, BUTTON_BACKSPACE
import mmbasic

_STATUS_ENDED = const(1)
_STATUS_STOPPED = const(2)
_STATUS_ERROR = const(4)

class MMBasic(mmbasic.MMBasic):
    """A class representing the MMBasic interpreter for Picoware."""

    __slots__ = ("_engine", "_view_manager", "_over", "_present_countdown", "_present_ticks")

    def __init__(self, view_manager, present_ticks:int=20):
        """
        Parameters
        ----------
        view_manager : ViewManager
            The ViewManager instance for the app.
        present_ticks : int, optional
            The number of ticks between graphics screen updates (default is 20). Lower values make graphics more responsive but may reduce performance.
        """
        self._view_manager = view_manager
        draw = view_manager.draw
        super().__init__(
            view_manager.foreground_color,
            view_manager.background_color,
            view_manager.selected_color,
            draw.size.x,
            draw.size.y,
            draw.font_size.x,
            draw.font_size.y,
            draw._background,
            draw._font_default.size,
        )
        self._over = False
        self._present_countdown = 1
        self._present_ticks = present_ticks

    @property
    def is_over(self) -> bool:
        """True when the program has reached a terminal state (END/STOP)."""
        return self._over

    def _feed_button(self, button):
        if button == BUTTON_BACKSPACE:
            self.feed_char("\b")
            return
        if button == BUTTON_CENTER:
            self.feed_char("\n")
            return
        char = self._view_manager.input_manager.button_to_char(button)
        if char:
            self.feed_char(char)

    def run(self) -> bool:
        """Poll buttons, tick the interpreter, redraw the console/graphics.

        Returns False when the program is over (END/STOP) or the user pressed
        BACK, so the host app can return to the menu. Graphics programs keep
        their final image on screen (the app shows it until BACK is pressed).
        """
        button = self._view_manager.input_manager.button
        if button != -1:
            self._view_manager.input_manager.reset()
            if button == BUTTON_BACK:
                return False
            self._feed_button(button)

        status, message, line = self.tick(5)

        if status == _STATUS_ERROR:
            self.console_output("")
            self.console_output("? %s (line %d)" % (message, line))
            self.set_footer("Back to exit")
            self.render(True)
            return True
        if status == _STATUS_ENDED:
            self._over = True
            self.set_footer("Program ended - back to exit")
            self.render(True)
            return False
        if status == _STATUS_STOPPED:
            self._over = True
            self.set_footer("Break - back to exit")
            self.render(True)
            return False
        if self.has_graphics:
            self._present_countdown -= 1
            if self._present_countdown <= 0:
                self.render(False)
                self._present_countdown = self._present_ticks
        else:
            self.render(False)  # console text needs every-loop render
        return True

    def start(self, source=None, path=None) -> bool:
        """Run the provided MMBasic source code."""
        if self._start(source=source, path=path):
            self._over = False
            return True
        self._over = True
        return False