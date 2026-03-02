from picoware.applications.wifi.utils import connect_to_saved_wifi


class PicowareAnimation:
    """Class to draw "Picoware" animation"""

    def __init__(self, draw):
        from picoware.system.vector import Vector

        self.display = draw
        self.letter_states = []
        self.animation_complete = False
        self.circle_radius = 0
        self.circle_max_radius = 80
        self.circle_opacity = 100
        self.size = self.display.size
        self.center_x = self.size.x // 2
        self.center_y = self.size.y // 2
        self.frame_counter = 0

        self.text_vec = Vector(0, 0)
        self.circ_vec = Vector(0, 0)

        self._initialize_letter_animation()

    def __del__(self):
        del self.letter_states
        self.letter_states = None
        self.text_vec = None
        self.circ_vec = None

    def _initialize_letter_animation(self) -> None:
        """Initialize the animation state for each letter in 'Picoware'."""
        from picoware.system.colors import (
            TFT_RED,
            TFT_GREEN,
            TFT_BLUE,
            TFT_YELLOW,
            TFT_VIOLET,
            TFT_CYAN,
            TFT_ORANGE,
            TFT_PINK,
            TFT_SKYBLUE,
        )

        self.letter_states = []

        text = "Picoware"
        self.letter_states = []
        self.circle_opacity = 100

        # Calculate target position (center of screen)
        char_width = self.display.font_size.x
        total_width = len(text) * char_width
        target_y = self.center_y
        start_x = (self.size.x - total_width) // 2

        # Color palette (RGB565 format)
        colors = [
            TFT_RED,
            TFT_GREEN,
            TFT_BLUE,
            TFT_YELLOW,
            TFT_VIOLET,
            TFT_CYAN,
            TFT_ORANGE,
            TFT_PINK,
            TFT_SKYBLUE,
        ]

        # Different starting Y positions and delays for each letter
        from random import randint, choice

        for i, char in enumerate(text):
            letter_state = {
                "char": char,
                "target_x": start_x + (i * char_width),
                "target_y": target_y,
                "current_y": target_y + randint(-80, -40),  # Start above target
                "delay": i * 3,  # Staggered start times
                "frame": 0,
                "opacity": 0,  # Start invisible (0-100 scale)
                "color": choice(colors),  # Random color for each letter
            }
            self.letter_states.append(letter_state)

    def draw(self) -> None:
        """Draw the animated 'Picoware' text."""

        # Draw background animations
        if self.circle_radius < self.circle_max_radius:
            self.circle_radius += 2
        else:
            # Reset for continuous animation
            self.circle_radius = 0
            self.circle_opacity = 100

        # Fade out as it expands
        if self.circle_radius > self.circle_max_radius // 2:
            self.circle_opacity = max(0, self.circle_opacity - 3)

        # Draw circle with fade effect
        if self.circle_opacity > 20:  # Only draw if visible enough
            color = 0x4208

            # Draw if opacity threshold is met
            if (
                self.frame_counter % max(1, (100 - self.circle_opacity) // 20 + 1)
            ) == 0:
                self.circ_vec.x = self.center_x
                self.circ_vec.y = self.center_y
                self.display.circle(self.circ_vec, self.circle_radius, color)

        all_settled = True

        for letter in self.letter_states:
            # Handle delay before letter starts moving
            if letter["frame"] < letter["delay"]:
                letter["frame"] += 1
                all_settled = False
                continue

            # Animate Y position (ease-out effect)
            if letter["current_y"] > letter["target_y"]:
                diff = letter["current_y"] - letter["target_y"]
                letter["current_y"] -= max(1, diff // 4)  # Ease-out
                all_settled = False
            else:
                letter["current_y"] = letter["target_y"]

            # Fade in opacity (0-100 scale)
            if letter["opacity"] < 100:
                letter["opacity"] = min(100, letter["opacity"] + 5)
                all_settled = False

            # Draw the letter with fade effect
            if letter["opacity"] > 0:
                # Higher opacity = more solid appearance
                opacity_threshold = 100 - letter["opacity"]

                # Use modulo to create a fade pattern
                # At low opacity, only draw occasionally; at high opacity, always draw
                if (self.frame_counter % max(1, opacity_threshold // 10 + 1)) == 0:
                    self.text_vec.x = letter["target_x"]
                    self.text_vec.y = int(letter["current_y"])
                    self.display.text(
                        self.text_vec,
                        letter["char"],
                        letter["color"],
                    )

            letter["frame"] += 1

        self.animation_complete = all_settled
        self.frame_counter += 1


_desktop = None
_desktop_http = None
_desktop_picoware = None
_desktop_time_updated = False
_time = None
_timezone = None
_has_wifi = True


def _http_callback(response, state, error):
    """HTTP callback to process location and time data."""
    global _desktop_http, _desktop_time_updated, _timezone

    if not _desktop_http:
        return

    if any([not response, error, state == 2]):  # HTTP_ERROR
        _desktop_http.close()
        # Retry step 1
        _desktop_http.get_async("https://ipwhois.app/json/")
        return

    data: dict = response.json()

    # Get timezone from IP location
    if _timezone is None:
        timezone = data.get("timezone", "UTC")
        _timezone = timezone

        # Fetch time for detected timezone
        _desktop_http.close()
        _desktop_http.get_async(
            f"http://timeapi.io/api/time/current/zone?timeZone={_timezone}"
        )
        return

    # Process time data from timeapi.io
    year = data.get("year")
    month = data.get("month")
    day = data.get("day")
    hour = data.get("hour")
    minute = data.get("minute")
    seconds = data.get("seconds")

    if all([year, month, day, hour, minute, seconds]):
        _time.set(year, month, day, hour, minute, seconds)
        _desktop_time_updated = True
        _desktop.set_time(_time.time)

    _desktop_http.close()
    del _desktop_http
    _desktop_http = None


def start(view_manager) -> bool:
    """Start the loading animation."""
    from picoware.gui.desktop import Desktop

    global _desktop, _desktop_http, _desktop_picoware, _time, _desktop_time_updated, _timezone, _has_wifi

    if _desktop is None:
        _desktop = Desktop(
            view_manager.draw,
            view_manager.foreground_color,
            view_manager.background_color,
        )

    if _desktop_picoware is None:
        _desktop_picoware = PicowareAnimation(view_manager.draw)

    if not view_manager.has_wifi:
        _has_wifi = False
        return True

    _has_wifi = True

    connect_to_saved_wifi(view_manager)

    if _desktop_http is None:
        from picoware.system.http import HTTP

        _desktop_http = HTTP(thread_manager=view_manager.thread_manager)

        if view_manager.wifi.is_connected() and not view_manager.time.is_set:
            _desktop_time_updated = False
            _timezone = None  # Reset timezone
            _desktop_http.callback = _http_callback
            # Get timezone from IP location
            _desktop_http.get_async("https://ipwhois.app/json/")

    _time = view_manager.time

    return _desktop is not None


def run(view_manager) -> None:
    """Animate the loading spinner."""
    from picoware.system.buttons import BUTTON_LEFT, BUTTON_CENTER, BUTTON_UP

    global _desktop_time_updated, _timezone, _has_wifi

    input_manager = view_manager.input_manager
    button: int = input_manager.button

    if button == BUTTON_LEFT:
        from picoware.applications.system import system_info
        from picoware.system.view import View

        input_manager.reset()
        view_manager.add(
            View("system_info", system_info.run, system_info.start, system_info.stop)
        )
        view_manager.switch_to("system_info")
        return
    if button in (BUTTON_CENTER, BUTTON_UP):
        from picoware.applications import library
        from picoware.system.view import View

        input_manager.reset()
        view_manager.add(View("library", library.run, library.start, library.stop))
        view_manager.switch_to("library")
        return

    battery_level: int = input_manager.battery
    _desktop.set_battery(battery_level)

    # Clear and draw header
    view_manager.draw.erase()
    _desktop.draw_header(False if not _has_wifi else view_manager.wifi.is_connected())

    # Draw animated picoware text every frame
    _desktop_picoware.draw()

    # Swap buffer to display
    view_manager.draw.swap()

    if not _has_wifi:
        return

    wifi = view_manager.wifi
    is_connected = wifi.is_connected()
    if not is_connected:
        if wifi.state in (0, 4):  # WIFI_STATE_IDLE, WIFI_STATE_TIMEOUT
            connect_to_saved_wifi(view_manager)
        return

    if _desktop_time_updated:
        # time is RTC, so no need to fetch, just pass the updated time
        _desktop.set_time(_time.time)
        return

    if (
        is_connected
        and not view_manager.time.is_set
        and _desktop_http is not None
        and not _desktop_http.in_progress
    ):
        _desktop_time_updated = False
        _timezone = None  # Reset timezone
        _desktop_http.callback = _http_callback
        # Get timezone from IP location
        _desktop_http.get_async("https://ipwhois.app/json/")


def stop(view_manager) -> None:
    """Stop the loading animation."""
    from gc import collect

    global _desktop
    global _desktop_http
    global _desktop_picoware
    global _desktop_time_updated
    global _timezone
    global _has_wifi

    if _desktop:
        del _desktop
        _desktop = None
    if _desktop_http:
        _desktop_http.close()
        del _desktop_http
        _desktop_http = None
    if _desktop_picoware:
        del _desktop_picoware
        _desktop_picoware = None

    _desktop_time_updated = view_manager.time.is_set
    _timezone = None
    _has_wifi = True

    collect()
