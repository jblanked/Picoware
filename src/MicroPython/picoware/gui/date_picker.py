class DatePicker:
    """
    A GUI component for selecting and rendering a date and time.
    Two-band layout:
      Top band:    Month | Day  | Year
      Bottom band: Hour  | Min  | Sec
    Left/right navigates across all 6 fields, up/down changes the value.
    Returns False when the user is done (CENTER or BACK).
    """

    _MONTHS = (
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    )
    _DAYS_IN_MONTH = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)

    def __init__(self, view_manager, position, size, time: tuple = None):
        """
        Initialize the date picker with a reference to the view manager, position, size, and optional initial time.

        Args:
            - view_manager: View Manager context
            - position: Vector with position coordinates
            - size: Vector with size dimensions
            - time: Optional tuple representing the initial date and time (year, month, day of month, weekday, hour, minute, second, subseconds)
        """
        self._view_manager = view_manager
        self._position = position
        self._size = size
        self._time = (
            time if time is not None else (2024, 1, 1, 0, 0, 0, 0, 0)
        )  # (year, month, day of month, weekday, hour, minute, second, subseconds)
        self._field = 0  # 0=Month, 1=Day, 2=Year, 3=Hour, 4=Minute, 5=Second
        self._needs_redraw = True

    def __del__(self):
        """Clean up resources"""
        del self._position
        del self._size
        del self._time

    @property
    def time(self):
        """Get the currently selected date and time as a tuple."""
        return self._time

    def __band(
        self,
        draw,
        fg,
        bg,
        sel,
        band_y,
        band_h,
        col_w,
        start_x,
        labels,
        values,
        active_col,
        val_h,
        lbl_h,
        lbl_cw,
        val_font,
    ) -> None:
        """Draw a single 3-column drum-roll band."""
        from picoware.system.vector import Vector

        w = col_w * 3
        center_y = band_y + band_h // 2
        sel_pad = 4
        line_top = center_y - val_h // 2 - sel_pad
        line_bot = center_y + val_h // 2 + sel_pad

        # Horizontal border lines
        hr = Vector(start_x, line_top)
        hr_sz = Vector(w, 1)
        draw.fill_rectangle(hr, hr_sz, fg)
        hr.y = line_bot
        draw.fill_rectangle(hr, hr_sz, fg)

        # Vertical column dividers
        div_top = band_y + lbl_h + 6
        div_bot = band_y + band_h - 2
        vd = Vector(0, div_top)
        vd_sz = Vector(1, max(1, div_bot - div_top))
        for i in range(1, 3):
            vd.x = start_x + col_w * i
            draw.fill_rectangle(vd, vd_sz, fg)

        tile_pos = Vector(0, 0)
        tile_sz = Vector(0, 0)
        txt = Vector(0, 0)

        for i in range(3):
            col_x = start_x + col_w * i
            col_cx = col_x + col_w // 2

            val = values[i]
            label = labels[i]

            # Highlight active column
            if i == active_col:
                tile_pos.x = col_x + 3
                tile_pos.y = line_top + 1
                tile_sz.x = col_w - 6
                tile_sz.y = line_bot - line_top - 1
                draw.fill_round_rectangle(tile_pos, tile_sz, 8, sel)

            # Value — centered in band
            val_pw = draw.len(val, val_font)
            txt.x = col_cx - val_pw // 2
            txt.y = center_y - val_h // 2
            draw.text(txt, val, bg if i == active_col else fg, val_font)

            # Field label at top of band
            lbl_pw = len(label) * lbl_cw
            txt.x = col_cx - lbl_pw // 2
            txt.y = band_y + 4
            draw.text(txt, label, fg)

            # ^ / v arrows for the active column only
            if i == active_col:
                arrow_x = col_cx - lbl_cw // 2
                txt.x = arrow_x
                txt.y = line_top - lbl_h - 2
                draw.text(txt, "^", fg)
                txt.x = arrow_x
                txt.y = line_bot + 3
                draw.text(txt, "v", fg)

    def __draw(self) -> None:
        """Render the date+time picker on the display."""
        draw = self._view_manager.draw
        fg = self._view_manager.foreground_color
        bg = self._view_manager.background_color
        sel = self._view_manager.selected_color

        pos = self._position
        size = self._size
        w = size.x
        h = size.y

        year, month, day, weekday, hour, minute, second, sub = self._time
        month = max(1, min(12, month))
        day = max(1, min(self.__max_day(month), day))
        hour = max(0, min(23, hour))
        minute = max(0, min(59, minute))
        second = max(0, min(59, second))

        draw.clear(pos, size, bg)

        VAL_FONT = 2  # FONT_MEDIUM keeps values readable across 3 columns
        val_f = draw.get_font(VAL_FONT)
        val_h = val_f.height
        lbl_h = draw.font_size.y
        lbl_cw = draw.font_size.x
        col_w = w // 3

        # Layout: two equal bands + a hint row at the bottom
        hint_h = lbl_h + 6
        gap = 6
        band_h = (h - hint_h - gap) // 2

        date_y = pos.y
        time_y = pos.y + band_h + gap

        # Date band: Month | Day | Year
        self.__band(
            draw,
            fg,
            bg,
            sel,
            date_y,
            band_h,
            col_w,
            pos.x,
            ("Month", "Day", "Year"),
            (self._MONTHS[month - 1], str(day), str(year)),
            self._field if self._field < 3 else -1,
            val_h,
            lbl_h,
            lbl_cw,
            VAL_FONT,
        )

        # Time band: Hour | Min | Sec
        self.__band(
            draw,
            fg,
            bg,
            sel,
            time_y,
            band_h,
            col_w,
            pos.x,
            ("Hour", "Min", "Sec"),
            (
                "{:02d}".format(hour),
                "{:02d}".format(minute),
                "{:02d}".format(second),
            ),
            (self._field - 3) if self._field >= 3 else -1,
            val_h,
            lbl_h,
            lbl_cw,
            VAL_FONT,
        )

        # Bottom hint
        hint = "L/R:field  U/D:value  OK:done"
        hint_pw = len(hint) * lbl_cw
        if hint_pw > w:
            hint = "L/R field  U/D value"
            hint_pw = len(hint) * lbl_cw
        draw._text(pos.x + (w - hint_pw) // 2, pos.y + h - lbl_h - 2, hint, fg)

        draw.swap()
        self._needs_redraw = False

    def __max_day(self, month: int) -> int:
        """Return the number of days in the given month (1-indexed)."""
        if 1 <= month <= 12:
            return self._DAYS_IN_MONTH[month - 1]
        return 31

    def run(self) -> bool:
        """
        Run one iteration of the date picker event loop.
        Returns True to keep running, False when the user is done.
        """
        from picoware.system.buttons import (
            BUTTON_BACK,
            BUTTON_CENTER,
            BUTTON_UP,
            BUTTON_DOWN,
            BUTTON_LEFT,
            BUTTON_RIGHT,
        )

        inp = self._view_manager.input_manager
        button = inp.button

        if button != -1:
            year, month, day, weekday, hour, minute, second, sub = self._time

            if button in (BUTTON_BACK, BUTTON_CENTER):
                inp.reset()
                return False

            if button == BUTTON_LEFT:
                inp.reset()
                self._field = (self._field - 1) % 6
                self._needs_redraw = True

            elif button == BUTTON_RIGHT:
                inp.reset()
                self._field = (self._field + 1) % 6
                self._needs_redraw = True

            elif button == BUTTON_UP:
                inp.reset()
                if self._field == 0:  # Month
                    month = month % 12 + 1
                    day = min(day, self.__max_day(month))
                elif self._field == 1:  # Day
                    day = day % self.__max_day(month) + 1
                elif self._field == 2:  # Year
                    year += 1
                elif self._field == 3:  # Hour
                    hour = (hour + 1) % 24
                elif self._field == 4:  # Minute
                    minute = (minute + 1) % 60
                else:  # Second
                    second = (second + 1) % 60
                self._time = (year, month, day, weekday, hour, minute, second, sub)
                self._needs_redraw = True

            elif button == BUTTON_DOWN:
                inp.reset()
                if self._field == 0:  # Month
                    month = (month - 2) % 12 + 1
                    day = min(day, self.__max_day(month))
                elif self._field == 1:  # Day
                    day = (day - 2) % self.__max_day(month) + 1
                elif self._field == 2:  # Year
                    year = max(1, year - 1)
                elif self._field == 3:  # Hour
                    hour = (hour - 1) % 24
                elif self._field == 4:  # Minute
                    minute = (minute - 1) % 60
                else:  # Second
                    second = (second - 1) % 60
                self._time = (year, month, day, weekday, hour, minute, second, sub)
                self._needs_redraw = True

        if self._needs_redraw:
            self.__draw()

        return True
