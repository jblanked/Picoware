# VibesMP themes and theme helpers.

# ---- themes.py ----

from micropython import const

# VibesMP Theme Presets (RGB565 via RGB888 conversion)
# Calculated using: ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

THEMES = {
    "dark": { # Classic Refined
        "bg_c": const(0x18E3),      # rgb(24, 28, 24)
        "well": const(0x0821),      # Black
        "text_c": const(0xDEFB),    # rgb(220, 220, 220)
        "accent_c": const(0xFC00),  # rgb(255, 128, 0)
        "highlight_c": const(0x07FF), # Cyan
        "panel_c": const(0x2965),   # rgb(40, 44, 40)
        "footer_bg": const(0xFC00), # Orange
        "footer_text": const(0x0821) # Black
    },
    "midnight": { # OLED Black + Neon Blue
        "bg_c": const(0x0821),      # Near Black
        "well": const(0x1082),      # rgb(20, 20, 20)
        "text_c": const(0xDEFB),    # Muted White
        "accent_c": const(0x05FF),  # rgb(0, 191, 255)
        "highlight_c": const(0xF81F), # Magenta
        "panel_c": const(0x0841),   # rgb(15, 15, 15)
        "footer_bg": const(0x05FF), # Neon Blue
        "footer_text": const(0x0821) # Black
    },
    "nord": { # Frosty Arctic
        "bg_c": const(0x2AD6),      # rgb(46, 52, 64)
        "well": const(0x3A32),      # rgb(59, 66, 82)
        "text_c": const(0xEF79),    # rgb(236, 239, 244)
        "accent_c": const(0x8E38),  # rgb(136, 192, 208)
        "highlight_c": const(0x8318), # rgb(129, 161, 193)
        "panel_c": const(0x426B),   # rgb(67, 76, 94)
        "footer_bg": const(0x8E38), # Frost Blue
        "footer_text": const(0x2AD6) # Darker Blue
    },
    "forest": { # Deep Moss + Brass
        "bg_c": const(0x10E2),      # rgb(20, 30, 20)
        "well": const(0x0841),      # rgb(10, 15, 10)
        "text_c": const(0xD75A),    # rgb(210, 230, 210)
        "accent_c": const(0xB50A),  # rgb(180, 160, 80)
        "highlight_c": const(0x07E0), # Green
        "panel_c": const(0x1B63),   # rgb(30, 45, 30)
        "footer_bg": const(0xB50A), # Brass
        "footer_text": const(0x10E2) # Deep Green
    },
    "solarized": { # Official Solarized Dark
        "bg_c": const(0x0166),      # base03
        "well": const(0x01AA),      # base02
        "text_c": const(0x84B2),    # base0
        "accent_c": const(0xB440),  # Yellow
        "highlight_c": const(0x245A), # Blue
        "panel_c": const(0x01AA),   # base02
        "footer_bg": const(0xB440), # Yellow
        "footer_text": const(0x0166) # base03
    },
    "apocalypse": { # Rust & Ash
        "bg_c": const(0x2104),      # Charcoal
        "well": const(0x1082),      # Deep Gray
        "text_c": const(0xBDD7),    # Ash Gray
        "accent_c": const(0xA145),  # Rust Red
        "highlight_c": const(0x8200), # Blood Red
        "panel_c": const(0x3186),   # Medium Gray
        "footer_bg": const(0xA145), # Rust
        "footer_text": const(0x2104) # Charcoal
    },
    "toxic_green": { # Matrix Glow
        "bg_c": const(0x0000),      # Pure Black
        "well": const(0x0040),      # Dark Emerald
        "text_c": const(0x07E0),    # Bright Green
        "accent_c": const(0xAD60),  # Acid Yellow-Green
        "highlight_c": const(0xFFFF), # White
        "panel_c": const(0x0821),   # Dark Gray
        "footer_bg": const(0xAD60), # Acid
        "footer_text": const(0x0000) # Black
    },
    "romance": { # Velvet & Wine
        "bg_c": const(0x4008),      # Deep Plum
        "well": const(0x600C),      # Muted Wine
        "text_c": const(0xFDB8),    # Rose Pink
        "accent_c": const(0xF80F),  # Hot Pink
        "highlight_c": const(0xFFFF), # White
        "panel_c": const(0x8010),   # Berry
        "footer_bg": const(0xF80F), # Rose
        "footer_text": const(0x4008) # Plum
    },
    "silent_forest": { # Misty Pine
        "bg_c": const(0x0104),      # Foggy Blue-Green
        "well": const(0x1106),      # Deep Moss
        "text_c": const(0xBDF7),    # Mist Gray
        "accent_c": const(0x4410),  # Dark Pine
        "highlight_c": const(0x07E0), # Vivid Green
        "panel_c": const(0x2208),   # Forest Floor
        "footer_bg": const(0x4410), # Pine
        "footer_text": const(0x0104) # Fog
    },
    "rainy_forest": { # Wet Slate & Teal
        "bg_c": const(0x0841),      # Wet Rock
        "well": const(0x0020),      # Deep Water
        "text_c": const(0x94B2),    # Rainy Sky
        "accent_c": const(0x2410),  # Wet Teal
        "highlight_c": const(0x041F), # Storm Blue
        "panel_c": const(0x10A2),   # Wet Pine
        "footer_bg": const(0x2410), # Teal
        "footer_text": const(0x0841) # Slate
    },
    "mellow_green": { # Sage & Cream
        "bg_c": const(0x6420),      # Sage Green
        "well": const(0x4380),      # Deep Sage
        "text_c": const(0xFFFF),    # Pure White
        "accent_c": const(0xB50A),  # Brass
        "highlight_c": const(0xE73F), # Rich Cream
        "panel_c": const(0x84E4),   # Soft Leaf
        "footer_bg": const(0xB50A), # Brass
        "footer_text": const(0x6420) # Sage
    },
    "orange_terminal": { # Retro CRT
        "bg_c": const(0x0000),      # Black
        "well": const(0x0821),      # Scanline Gray
        "text_c": const(0xFC00),    # Amber Orange
        "accent_c": const(0xFD40),  # Bright Amber
        "highlight_c": const(0xFFFF), # White Glow
        "panel_c": const(0x0821),   # Dark Gray
        "footer_bg": const(0xFC00), # Amber
        "footer_text": const(0x0000) # Black
    },
    "candy": { # Neon Pop
        "bg_c": const(0x4010),      # Deep Candy Blue
        "well": const(0x0210),      # Midnight Blue
        "text_c": const(0xFFFF),    # White
        "accent_c": const(0xF81F),  # Bubblegum
        "highlight_c": const(0x07FF), # Electric Cyan
        "panel_c": const(0x801F),   # Grape
        "footer_bg": const(0xF81F), # Bubblegum
        "footer_text": const(0xFFFF) # White
    },
    "psycho": { # Chaos Theory
        "bg_c": const(0x0000),      # Void
        "well": const(0x8000),      # Maroon
        "text_c": const(0x07E0),    # Toxic Green
        "accent_c": const(0xF81F),  # Hot Magenta
        "highlight_c": const(0xFFE0), # Acid Yellow
        "panel_c": const(0x001F),   # Electric Blue
        "footer_bg": const(0xF81F), # Magenta
        "footer_text": const(0x0000) # Void
    },
    "strawberry_cheesecake": { # Pastry Shop
        "bg_c": const(0xF79E),      # Biscuit
        "well": const(0xE71C),      # Dark Crust
        "text_c": const(0x4208),    # Cocoa Brown
        "accent_c": const(0xF800),  # Strawberry Red
        "highlight_c": const(0xFB24), # Whipped Pink
        "panel_c": const(0xFFF0),   # Cream Yellow
        "footer_bg": const(0xF800), # Strawberry
        "footer_text": const(0xFFFF) # White
    },
    "cannabis": { # High Grade
        "bg_c": const(0x0100),      # Skunk Black
        "well": const(0x0841),      # Pine Bark
        "text_c": const(0xBDD7),    # Silver Leaf
        "accent_c": const(0x07E0),  # Sticky Green
        "highlight_c": const(0x8010), # Purple Punch
        "panel_c": const(0x2304),   # Soil Brown
        "footer_bg": const(0x07E0), # Sticky Green
        "footer_text": const(0x0100) # Black
    }
}

# ---- theme_manager.py ----

from picoware.system.vector import Vector

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
