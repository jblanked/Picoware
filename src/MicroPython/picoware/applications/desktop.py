class PicowareAnimation:
    """Class to draw "Picoware" animation"""

    def __init__(self, draw):
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

        self._initialize_letter_animation()

    def __del__(self):
        del self.letter_states
        self.letter_states = None

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
            TFT_DARKCYAN,
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
            TFT_DARKCYAN,
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
        from picoware.system.vector import Vector

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
                self.display.circle(
                    Vector(self.center_x, self.center_y), self.circle_radius, color
                )

        all_settled = True

        text_vector = Vector(0, 0)
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
                    text_vector.x = letter["target_x"]
                    text_vector.y = int(letter["current_y"])
                    self.display.text(
                        text_vector,
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


def start(view_manager) -> bool:
    """Start the loading animation."""
    from picoware.gui.desktop import Desktop
    from picoware.applications.wifi.utils import connect_to_saved_wifi

    global _desktop, _desktop_http, _desktop_picoware

    if _desktop is None:
        _desktop = Desktop(
            view_manager.draw,
            view_manager.get_foreground_color(),
            view_manager.get_background_color(),
        )

    if _desktop_picoware is None:
        _desktop_picoware = PicowareAnimation(view_manager.draw)

    if not view_manager.has_wifi:
        return True

    wifi = view_manager.get_wifi()

    connect_to_saved_wifi(view_manager)

    if _desktop_http is None:
        from picoware.system.http import HTTP

        _desktop_http = HTTP()

        if wifi.is_connected():
            _desktop_http.get_async("http://worldtimeapi.org/api/ip")

    return True


def run(view_manager) -> None:
    """Animate the loading spinner."""
    from picoware.system.buttons import BUTTON_LEFT, BUTTON_CENTER, BUTTON_UP
    from picoware.system.view import View

    input_manager = view_manager.input_manager
    button: int = input_manager.button

    global _desktop_http, _desktop_time_updated

    if _desktop:
        from picoware.system.vector import Vector

        battery_level: int = input_manager.battery
        _desktop.set_battery(battery_level)

        # Clear and draw header
        view_manager.draw.clear(
            Vector(0, 0), view_manager.draw.size, view_manager.get_background_color()
        )
        _desktop.draw_header()

        # Draw animated picoware text every frame
        _desktop_picoware.draw()

        # Swap buffer to display
        view_manager.draw.swap()

        wifi = view_manager.get_wifi()
        if wifi:
            if not _desktop_time_updated and wifi.is_connected():
                if _desktop_http and _desktop_http.is_request_complete():
                    try:
                        response = _desktop_http.response.text
                        if not response:
                            # i realized that sometimes this API returns an empty response
                            # but it usually works within 2-3 tries
                            _desktop_http.clear_async_response()
                            _desktop_http.get_async("http://worldtimeapi.org/api/ip")
                            return
                        if _desktop_http.state == 0:  # HTTP_IDLE
                            from ujson import loads

                            data: dict = loads(response)
                            datetime_str: str = data.get("datetime", "")
                            if datetime_str:
                                date_part, time_part = datetime_str.split("T")
                                time_part = time_part.split(".")[
                                    0
                                ]  # Remove milliseconds
                                hours, minutes, seconds = map(int, time_part.split(":"))
                                year, month, day = map(int, date_part.split("-"))

                                view_manager.get_time().set(
                                    year, month, day, hours, minutes, seconds
                                )

                                _desktop_time_updated = True

                                _desktop.set_time(view_manager.get_time().time)

                                del _desktop_http
                                _desktop_http = None
                        else:
                            print(
                                "Failed to fetch time data, HTTP state:",
                                _desktop_http.state,
                            )

                    except Exception as e:
                        print("Error processing time data:", e)
            elif _desktop_time_updated:
                # time is RTC, so no need to fetch, just pass the updated time
                _desktop.set_time(view_manager.get_time().time)

    if button == BUTTON_LEFT:
        from picoware.applications.system import system_info

        input_manager.reset()
        view_manager.add(
            View("system_info", system_info.run, system_info.start, system_info.stop)
        )
        view_manager.switch_to("system_info")
    elif button in (BUTTON_CENTER, BUTTON_UP):
        from picoware.applications import library

        input_manager.reset()
        view_manager.add(View("library", library.run, library.start, library.stop))
        view_manager.switch_to("library")


def stop(view_manager) -> None:
    """Stop the loading animation."""
    from gc import collect

    global _desktop
    global _desktop_http
    global _desktop_picoware

    if _desktop:
        del _desktop
        _desktop = None
    if _desktop_http:
        del _desktop_http
        _desktop_http = None
    if _desktop_picoware:
        del _desktop_picoware
        _desktop_picoware = None

    collect()
