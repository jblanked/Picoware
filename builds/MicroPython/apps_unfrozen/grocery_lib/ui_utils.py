from picoware.system.vector import Vector
from micropython import const

# --- Unified Marshmallow Design System ---
C_BG = const(0xF79E)      # System Gray 6 (Background)
C_CARD = const(0xFFFF)    # White (Content Area)
C_SEL = const(0x041F)     # System Blue (Selection)
C_TEXT = const(0x2104)    # Charcoal (Primary Label)
C_PAPER = const(0xCE59)   # Toolbar Gray (Header/Footer)
C_SHADOW = const(0x7BEF)  # Dark Grey (Readable on Toolbar Gray)
C_ACCENT = const(0x041F)  # System Blue (Icons)
C_RED = const(0xD000)     # System Red (Warnings)

VEC_ZERO = Vector(0, 0)

# Global Scratch Vectors to prevent allocation churn
_V1 = Vector(0, 0)
_V2 = Vector(0, 0)

_WIDTH_CACHE = {}

def _get_width(draw, text):
    if text not in _WIDTH_CACHE:
        _WIDTH_CACHE[text] = draw.len(text, 0)
    return _WIDTH_CACHE[text]

_LCD_SEGS = {
    '0': (1,1,1,1,1,1,0), '1': (0,1,1,0,0,0,0), '2': (1,1,0,1,1,0,1),
    '3': (1,1,1,1,0,0,1), '4': (0,1,1,0,0,1,1), '5': (1,0,1,1,0,1,1),
    '6': (1,0,1,1,1,1,1), '7': (1,1,1,0,0,0,0), '8': (1,1,1,1,1,1,1),
    '9': (1,1,1,1,0,1,1), '-': (0,0,0,0,0,0,1), ' ': (0,0,0,0,0,0,0)
}

def draw_lcd_segment(draw, pos, size, horizontal, color):
    if horizontal: draw.fill_rectangle(pos, Vector(size.x, size.y), color)
    else: draw.fill_rectangle(pos, Vector(size.y, size.x), color)

def draw_lcd_digit(draw, pos_x, pos_y, digit, w, h, color):
    t = max(2, w // 8)
    mw, mh = w - (t * 2), (h // 2) - t
    active = _LCD_SEGS.get(digit, _LCD_SEGS[' '])

    _V1.x, _V1.y = pos_x + t, pos_y
    _V2.x, _V2.y = mw, t
    if active[0]: draw_lcd_segment(draw, _V1, _V2, True, color)

    _V1.x, _V1.y = pos_x + w - t, pos_y + t
    _V2.x, _V2.y = mh, t
    if active[1]: draw_lcd_segment(draw, _V1, _V2, False, color)

    _V1.x, _V1.y = pos_x + w - t, pos_y + h//2 + t//2
    if active[2]: draw_lcd_segment(draw, _V1, _V2, False, color)

    _V1.x, _V1.y = pos_x + t, pos_y + h - t
    _V2.x, _V2.y = mw, t
    if active[3]: draw_lcd_segment(draw, _V1, _V2, True, color)

    _V1.x, _V1.y = pos_x, pos_y + h//2 + t//2
    _V2.x, _V2.y = mh, t
    if active[4]: draw_lcd_segment(draw, _V1, _V2, False, color)

    _V1.x, _V1.y = pos_x, pos_y + t
    if active[5]: draw_lcd_segment(draw, _V1, _V2, False, color)

    _V1.x, _V1.y = pos_x + t, pos_y + h//2 - t//2
    _V2.x, _V2.y = mw, t
    if active[6]: draw_lcd_segment(draw, _V1, _V2, True, color)

def draw_lcd_string(draw, pos, text, digit_w, digit_h, spacing, color):
    curr_x = pos.x
    for char in text:
        if char in (".", ","):
            dot_size = max(2, digit_w // 10)
            dx = curr_x - spacing + 1
            dy = pos.y + digit_h - dot_size
            _V1.x, _V1.y = dx, dy
            _V2.x, _V2.y = dot_size, dot_size
            draw.fill_rectangle(_V1, _V2, color)
            if char == ",":
                _V1.x, _V1.y = dx - 1, dy + 1
                draw.fill_rectangle(_V1, _V2, color)
        else:
            draw_lcd_digit(draw, curr_x, pos.y, char, digit_w, digit_h, color)
            curr_x += digit_w + spacing

def draw_text_centered(draw, rx, ry, rw, rh, text, color, font_size=0):
    """Draws text centered within a rectangular area."""
    tw = _get_width(draw, text) if font_size == 0 else draw.len(text, font_size)
    fs_y = draw.font_size.y # Assuming default font for now as per current usage
    _V1.x, _V1.y = rx + (rw - tw) // 2, ry + (rh - fs_y) // 2
    draw.text(_V1, text, color, font_size)

def draw_header(draw, title, height, right_text="", center_title=True):
    _V1.x, _V1.y = draw.size.x, height
    draw.fill_round_rectangle(VEC_ZERO, _V1, 8, C_PAPER)

    if center_title:
        draw_text_centered(draw, 0, 0, draw.size.x, height, title, C_TEXT, 0)
    else:
        _V1.x, _V1.y = 8, (height - draw.font_size.y) // 2
        draw.text(_V1, title, C_TEXT, 0)

    if right_text:
        rt_w = _get_width(draw, right_text)
        _V1.x = draw.size.x - rt_w - 8
        _V1.y = (height - draw.font_size.y) // 2
        draw.text(_V1, right_text, C_SHADOW, 0)

def draw_progress_bar(draw, y, height, percentage, bg_color=C_SHADOW, fill_color=C_SEL):
    """Draws a horizontal progress bar."""
    _V1.x, _V1.y = 0, y
    _V2.x, _V2.y = draw.size.x, height
    draw.fill_rectangle(_V1, _V2, bg_color)
    
    fill_w = int(draw.size.x * (max(0, min(100, percentage)) / 100.0))
    if fill_w > 0:
        _V2.x = fill_w
        draw.fill_rectangle(_V1, _V2, fill_color)

def draw_footer(draw, hint, height):
    w, h = draw.size.x, draw.size.y
    y = h - height

    _V1.x, _V1.y = 0, y
    _V2.x, _V2.y = w - 2, height - 1
    draw.fill_round_rectangle(_V1, _V2, 8, C_PAPER)

    draw_text_centered(draw, 0, y, w, height, hint, C_TEXT, 0)

def draw_scrollbar(draw, total_items, visible_count, scroll_offset, y_start, height):
    if total_items <= visible_count: return

    bar_w = 3
    bar_x = draw.size.x - bar_w - 1

    _V1.x, _V1.y = bar_x, y_start
    _V2.x, _V2.y = bar_w, height
    draw.fill_rectangle(_V1, _V2, C_SHADOW)

    thumb_h = max(4, int((visible_count / total_items) * height))
    thumb_y = y_start + int((scroll_offset / total_items) * height)

    _V1.x, _V1.y = bar_x, thumb_y
    _V2.x, _V2.y = bar_w, thumb_h
    draw.fill_rectangle(_V1, _V2, C_SEL)

def draw_card(draw, pos, size, radius, is_selected):
    px, py = pos.x, pos.y
    sx, sy = size.x, size.y

    if is_selected:
        draw.fill_round_rectangle(pos, size, radius, C_SEL)
        _V1.x, _V1.y = px + 2, py + 2
        _V2.x, _V2.y = sx - 4, sy - 4
        draw.fill_rectangle(_V1, _V2, C_CARD)
    else:
        draw.fill_round_rectangle(pos, size, radius, C_CARD)
        _V1.x, _V1.y = px + radius, py
        _V2.x, _V2.y = px + sx - radius, py
        draw.line_custom(_V1, _V2, 0xFFFF)

        _V1.x, _V1.y = px, py + radius
        _V2.x, _V2.y = px, py + sy - radius
        draw.line_custom(_V1, _V2, 0xFFFF)

def draw_modal_frame(draw, title, w, h, header_bg=None):
    x, y = (draw.size.x - w) // 2, (draw.size.y - h) // 2
    radius = 10

    # Rounded Shadow
    _V2.x, _V2.y = w, h
    _V1.x, _V1.y = x + 3, y + 3
    draw.fill_round_rectangle(_V1, _V2, radius, C_SHADOW)

    # Main Rounded Background
    _V1.x, _V1.y = x, y
    draw.fill_round_rectangle(_V1, _V2, radius, 0xFFFF)

    _V1.x, _V1.y = x + 2, y + 2
    _V2.x, _V2.y = w - 4, h - 4
    draw.fill_round_rectangle(_V1, _V2, radius - 2, C_BG)

    # Header (Top Rounding)
    header_h = 24
    _V1.x, _V1.y = x + 2, y + 2
    _V2.x, _V2.y = w - 4, header_h
    h_bg = header_bg if header_bg is not None else C_PAPER
    draw.fill_round_rectangle(_V1, _V2, radius - 2, h_bg)
    # Fill bottom of header to keep it flat where it meets body
    _V1.y = y + 2 + header_h // 2
    _V2.y = header_h // 2
    draw.fill_rectangle(_V1, _V2, h_bg)

    # Footer (Bottom Rounding)
    footer_h = 32
    _V1.x, _V1.y = x + 2, y + h - footer_h
    _V2.x, _V2.y = w - 4, footer_h - 2
    draw.fill_round_rectangle(_V1, _V2, radius - 2, C_PAPER)
    # Fill top of footer to keep it flat where it meets body
    _V2.y = (footer_h - 2) // 2
    draw.fill_rectangle(_V1, _V2, C_PAPER)

    draw_text_centered(draw, x, y + 2, w, header_h, title, C_TEXT if header_bg is None else 0xFFFF, 0)

    return x, y, w, h, footer_h

def _line(draw, x1, y1, x2, y2, color):
    _V1.x, _V1.y = x1, y1
    _V2.x, _V2.y = x2, y2
    draw.line_custom(_V1, _V2, color)

def _rect(draw, x, y, w, h, color):
    _V1.x, _V1.y = x, y
    _V2.x, _V2.y = w, h
    draw.rect(_V1, _V2, color)

def _circle(draw, x, y, r, color):
    _V1.x, _V1.y = x, y
    draw.circle(_V1, r, color)

def _pixel(draw, x, y, color):
    _V1.x, _V1.y = x, y
    draw.pixel(_V1, color)

def _icon_sl(draw, x, y, color, bg):
    _line(draw, x, y + 4, x + 12, y + 4, color)
    _line(draw, x, y + 10, x + 12, y + 10, color)

def _icon_add(draw, x, y, color, bg):
    _line(draw, x + 6, y, x + 6, y + 12, color)
    _line(draw, x, y + 6, x + 12, y + 6, color)

def _icon_pantry(draw, x, y, color, bg):
    _rect(draw, x, y, 12, 12, color)
    _line(draw, x + 6, y, x + 6, y + 11, color)
    _pixel(draw, x + 4, y + 6, color)
    _pixel(draw, x + 8, y + 6, color)

def _icon_calc(draw, x, y, color, bg):
    _circle(draw, x + 6, y + 6, 6, color)
    _line(draw, x + 6, y + 6, x + 6, y + 2, color)

def _icon_settings(draw, x, y, color, bg):
    _rect(draw, x + 4, y, 4, 12, color)
    _rect(draw, x, y + 4, 12, 4, color)
    _circle(draw, x + 6, y + 6, 3, bg)

def _icon_euro(draw, x, y, color, bg):
    _line(draw, x + 2, y, x + 4, y, color)
    _line(draw, x + 1, y + 1, x + 1, y + 5, color)
    _line(draw, x + 2, y + 6, x + 4, y + 6, color)
    _line(draw, x, y + 2, x + 4, y + 2, color)
    _line(draw, x, y + 4, x + 4, y + 4, color)

def _icon_dollar(draw, x, y, color, bg):
    _line(draw, x + 2, y + 2, x + 10, y + 2, color)
    _line(draw, x + 2, y + 6, x + 10, y + 6, color)
    _line(draw, x + 2, y + 10, x + 10, y + 10, color)
    _line(draw, x + 10, y + 2, x + 10, y + 6, color)
    _line(draw, x + 2, y + 6, x + 2, y + 10, color)
    _line(draw, x + 6, y, x + 6, y + 12, color)

def _icon_checkmark(draw, x, y, color, bg):
    _line(draw, x + 2, y + 6, x + 5, y + 9, color)
    _line(draw, x + 5, y + 9, x + 10, y + 2, color)

def _icon_edit(draw, x, y, color, bg):
    _line(draw, x + 8, y + 2, x + 10, y, color)
    _line(draw, x, y + 10, x + 8, y + 2, color)

def _icon_lang(draw, x, y, color, bg):
    _circle(draw, x + 6, y + 6, 6, color)
    _line(draw, x, y + 6, x + 12, y + 6, color)
    _line(draw, x + 6, y, x + 6, y + 12, color)

def _icon_sep(draw, x, y, color, bg):
    _pixel(draw, x + 3, y + 3, color)
    _line(draw, x + 8, y + 8, x + 6, y + 10, color)

def _icon_tax(draw, x, y, color, bg):
    _pixel(draw, x + 3, y + 3, color)
    _pixel(draw, x + 9, y + 9, color)
    _line(draw, x + 10, y + 2, x + 2, y + 10, color)

def _icon_percent(draw, x, y, color, bg):
    _circle(draw, x + 3, y + 3, 2, color)
    _line(draw, x + 10, y + 2, x + 2, y + 10, color)
    _circle(draw, x + 9, y + 9, 2, color)

def _icon_box(draw, x, y, color, bg):
    _rect(draw, x, y, 12, 12, color)

def _icon_star(draw, x, y, color, bg):
    _pixel(draw, x + 6, y + 2, color)
    _line(draw, x + 5, y + 3, x + 7, y + 3, color)
    _line(draw, x + 2, y + 4, x + 10, y + 4, color)
    _line(draw, x + 3, y + 5, x + 9, y + 5, color)
    _line(draw, x + 5, y + 6, x + 7, y + 6, color)
    _line(draw, x + 4, y + 7, x + 8, y + 7, color)
    _pixel(draw, x + 3, y + 8, color)
    _pixel(draw, x + 9, y + 8, color)

def _icon_trash(draw, x, y, color, bg):
    _line(draw, x + 4, y, x + 8, y, color)
    _line(draw, x, y + 1, x + 12, y + 1, color)
    _line(draw, x + 2, y + 2, x + 2, y + 11, color)
    _line(draw, x + 10, y + 2, x + 10, y + 11, color)
    _line(draw, x + 2, y + 11, x + 10, y + 11, color)
    _line(draw, x + 5, y + 4, x + 5, y + 9, color)
    _line(draw, x + 7, y + 4, x + 7, y + 9, color)

def _icon_sweep(draw, x, y, color, bg):
    _line(draw, x + 6, y, x + 6, y + 7, color)
    _line(draw, x + 2, y + 8, x + 10, y + 8, color)
    _line(draw, x + 2, y + 9, x + 2, y + 12, color)
    _line(draw, x + 4, y + 9, x + 4, y + 12, color)
    _line(draw, x + 6, y + 9, x + 6, y + 12, color)
    _line(draw, x + 8, y + 9, x + 8, y + 12, color)
    _line(draw, x + 10, y + 9, x + 10, y + 12, color)

_ICON_MAP = {
    "shopping_list": _icon_sl,
    "add_item": _icon_add,
    "pantry": _icon_pantry,
    "calculators": _icon_calc,
    "settings": _icon_settings,
    "euro": _icon_euro,
    "dollar": _icon_dollar,
    "checkmark": _icon_checkmark,
    "box": _icon_box,
    "edit": _icon_edit,
    "language": _icon_lang,
    "decimal_separator": _icon_sep,
    "tax_region": _icon_tax,
    "star": _icon_star,
    "percent": _icon_percent,
    "trash": _icon_trash,
    "sweep": _icon_sweep
}

EURO_SYMBOL = "\x01"

def draw_icon(draw, key, x, y, color=C_TEXT, bg_color=C_BG):
    func = _ICON_MAP.get(key)
    if func:
        func(draw, x, y, color, bg_color)
    else:
        _icon_settings(draw, x, y, color, bg_color)

def draw_text_price(draw, pos, text, color):
    """Draws text, replacing EURO_SYMBOL with the custom icon."""
    if EURO_SYMBOL in text:
        parts = text.split(EURO_SYMBOL)
        draw.text(pos, parts[0], color, 0)
        w = draw.len(parts[0], 0)
        # Center 7px high icon in 16px font
        ix = pos.x + w + 1
        iy = pos.y + (draw.font_size.y - 7) // 2
        _icon_euro(draw, ix, iy, color, C_BG)
        if len(parts) > 1 and parts[1]:
            _V1.x, _V1.y = ix + 7, pos.y
            draw.text(_V1, parts[1], color, 0)
    else:
        draw.text(pos, text, color, 0)
