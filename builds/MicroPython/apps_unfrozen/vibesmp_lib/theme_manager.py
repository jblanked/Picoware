from picoware.system.vector import Vector
from vibesmp_lib.themes import THEMES

def load_theme(settings):
    """Resolve and return the current theme dictionary."""
    # Handle case-insensitivity and provide a safe fallback
    theme_name = settings.config.get("theme", "dark").lower().replace(" ", "_")

    if theme_name in THEMES:
        return THEMES[theme_name]

    # Fallback to standard dark theme if key is missing
    return THEMES["dark"]

def draw_battery_icon(draw, pos, percent, color):
    """Draw a small battery icon with fill level."""
    w, h = 16, 8
    draw.rect(pos, Vector(w, h), color)
    draw.fill_rectangle(Vector(pos.x + w, pos.y + 2), Vector(2, 4), color)
    if percent > 0:
        fill_w = max(1, int((percent / 100) * (w - 4)))
        draw.fill_rectangle(Vector(pos.x + 2, pos.y + 2), Vector(fill_w, 4), color)

def draw_clock_icon(draw, pos, color):
    """Draw a small clock icon."""
    draw.rect(pos, Vector(8, 8), color)
    draw.fill_rectangle(Vector(pos.x + 3, pos.y + 1), Vector(1, 4), color)
    draw.fill_rectangle(Vector(pos.x + 3, pos.y + 4), Vector(4, 1), color)

_last_fetch_attempt = 0

def render_header_extras(ui, sw, bar_h):
    """Draw battery and time in the header area."""
    global _last_fetch_attempt
    curr_x = sw - 10

    # Battery
    if ui.view_manager and ui.view_manager.input_manager:
        try:
            bat = ui.view_manager.input_manager.battery
            bat_str = f"{bat}%"
            curr_x -= (len(bat_str) * 6 + 2)
            ui.draw.text(Vector(curr_x, (bar_h - 12) // 2 + 1), bat_str, ui.theme["footer_text"])
            curr_x -= 20
            draw_battery_icon(ui.draw, Vector(curr_x, (bar_h - 8) // 2), bat, ui.theme["footer_text"])
        except Exception as e:
            print(f"[DEBUG] Header Battery Error: {e}")

    # Time
    if ui.view_manager and ui.view_manager.time:
        t_obj = ui.view_manager.time

        # Auto-fetch if WiFi is connected but time has not been set yet
        if not t_obj.is_set and not t_obj.is_fetching:
            import time
            now = time.ticks_ms()
            if time.ticks_diff(now, _last_fetch_attempt) > 15000:
                _last_fetch_attempt = now
                try:
                    if ui.view_manager.wifi and ui.view_manager.wifi.is_connected():
                        t_obj.fetch(ui.view_manager.gmt_offset)
                except Exception:
                    pass

        if t_obj.is_set:
            try:
                date = t_obj.rtc.datetime()
                time_str = f"{date[4]:02d}:{date[5]:02d}"
                curr_x -= (len(time_str) * 6 + 15)
                ui.draw.text(Vector(curr_x + 12, (bar_h - 12) // 2 + 1), time_str, ui.theme["footer_text"])
                draw_clock_icon(ui.draw, Vector(curr_x, (bar_h - 8) // 2), ui.theme["footer_text"])
            except Exception as e:
                print(f"[DEBUG] Header Time Error: {e}")
