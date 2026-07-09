# VibesMP dialog renderers.

# ---- ui_dialogs.py ----

from picoware.system.vector import Vector
from picoware.system.colors import TFT_BLACK, TFT_WHITE, TFT_GREEN
from vibesmp_lib.resources import t
from vibesmp_lib.ui_utils import (
    draw_metadata_well,
    draw_panel,
    draw_player_button,
    draw_progress_bar,
    draw_scrollbar,
)

def _wrap_text(text, limit):
    res = []
    # Handle both actual newlines and escaped newlines
    lines = text.replace("\\n", "\n").split("\n")
    for l in lines:
        if not l:
            res.append("")
            continue
        for i in range(0, len(l), limit):
            res.append(l[i:i+limit])
    return res

def _dialog_text_limit(width_px, inner_padding=20, scrollbar_w=8, char_w=6):
    usable_w = max(0, width_px - inner_padding - scrollbar_w)
    return max(1, usable_w // char_w)

def render_progress_modal(ui, title, current_item, count):
    sw, sh = ui.draw.size.x, ui.draw.size.y
    ui.draw_background()

    m_h, m_w = 120, sw - 40
    m_x, m_y = 20, (sh - m_h) // 2

    draw_panel(ui.draw, Vector(m_x, m_y), Vector(m_w, m_h), title, ui.theme["panel_c"], ui.theme["accent_c"], ui.theme["footer_text"])

    # Track Count
    ui.draw.text(Vector(m_x + 10, m_y + 30), f"Found: {count} tracks", ui.theme["text_c"])

    # Current Folder (Truncated)
    folder_text = current_item if len(current_item) < 25 else "..." + current_item[-22:]
    ui.draw.text(Vector(m_x + 10, m_y + 50), folder_text, ui.theme["footer_text"])

    # Pulsing Bar
    draw_progress_bar(ui.draw, Vector(m_x + 10, m_y + 75), Vector(m_w - 20, 10), ui.theme, pulse=True)

    ui.draw.swap()

def render_modal(ui, title, message, button_text="OK", scroll_idx=0):
    sw, sh = ui.draw.size.x, ui.draw.size.y
    ui.draw_background()
    m_w = sw - 40
    limit = _dialog_text_limit(m_w)
    wrapped = _wrap_text(message, limit)

    # Header(20) + Text Area + Button Area(35) + Footer(20)
    content_h = len(wrapped) * 15
    m_h = max(85, min(sh - 20, 85 + content_h))
    m_x, m_y = 20, (sh - m_h) // 2

    draw_panel(ui.draw, Vector(m_x, m_y), Vector(m_w, m_h), title, ui.theme["panel_c"], ui.theme["accent_c"], ui.theme["footer_text"])

    text_viewport_h = max(0, m_h - 85)
    max_v_lines = text_viewport_h // 15

    # Clamp scroll_idx
    if scroll_idx > len(wrapped) - max_v_lines: scroll_idx = max(0, len(wrapped) - max_v_lines)

    y_offset = 30
    visible_lines = wrapped[scroll_idx : scroll_idx + max_v_lines]

    for line in visible_lines:
        ui.draw.text(Vector(m_x + 10, m_y + y_offset), line, ui.theme["text_c"])
        y_offset += 15

    # Scrollbar
    draw_scrollbar(ui.draw, Vector(m_x + m_w - 5, m_y + 30), Vector(3, text_viewport_h), len(wrapped), max_v_lines, scroll_idx, ui.theme)

    char_w = 6
    padding = 20
    btn_w = (len(button_text) * char_w) + padding
    btn_h = 20
    btn_x = m_x + (m_w - btn_w) // 2
    btn_y = m_y + m_h - 45
    draw_player_button(ui.draw, Vector(btn_x, btn_y), Vector(btn_w, btn_h), "ok", active=True, highlighted=True, colors=ui.theme, radius=btn_h // 2)
    ui.draw.text(Vector(btn_x + (btn_w - len(button_text)*char_w)//2, btn_y + 4), button_text, ui.theme["footer_text"])

    # Footer Bar
    ui.draw.fill_rectangle(Vector(m_x + 2, m_y + m_h - 18), Vector(m_w - 4, 15), ui.theme["accent_c"])
    ui.draw.text(Vector(m_x + 10, m_y + m_h - 15), t("hint_continue"), ui.theme["footer_text"])
    ui.draw.swap()


def render_input_dialog(ui, title, text, cursor_pos=0, force_full=False):
    sw, sh = ui.draw.size.x, ui.draw.size.y
    if force_full:
        ui.draw_background()

    # Input dialog has mostly fixed vertical structure
    m_w, m_h = 200, 100
    m_x, m_y = (sw - m_w) // 2, (sh - m_h) // 2

    shadow_offset = 4
    ui.draw.fill_round_rectangle(Vector(m_x + shadow_offset, m_y + shadow_offset), Vector(m_w, m_h), 5, TFT_BLACK)
    draw_panel(ui.draw, Vector(m_x, m_y), Vector(m_w, m_h), title, ui.theme["panel_c"], ui.theme["accent_c"], ui.theme["footer_text"])

    well_w, well_h = m_w - 20, 24
    well_x, well_y = m_x + 10, m_y + 35
    draw_metadata_well(ui.draw, Vector(well_x, well_y), Vector(well_w, well_h), ui.theme)

    char_w = 6
    visible_chars = max(1, (well_w - 10) // char_w)
    start = 0
    if cursor_pos >= visible_chars:
        start = cursor_pos - visible_chars + 1
    shown = text[start:start + visible_chars]
    ui.draw.text(Vector(well_x + 5, well_y + 6), shown, ui.theme["accent_c"])

    import time
    if (time.ticks_ms() // 500) % 2:
        cursor_x = well_x + 5 + ((cursor_pos - start) * char_w)
        if cursor_x < well_x + well_w - 5:
            ui.draw.text(Vector(cursor_x, well_y + 6), "_", ui.theme["accent_c"])

    hint = "DEL:Rem LR:Move ENT:Save"
    ui.draw.fill_rectangle(Vector(m_x + 2, m_y + m_h - 18), Vector(m_w - 4, 15), ui.theme["accent_c"])
    ui.draw.text(Vector(m_x + 10, m_y + m_h - 15), hint, ui.theme["footer_text"])
    ui.draw.swap()


def render_confirm(ui, title, message, sel_idx=0, scroll_idx=0):
    sw, sh = ui.draw.size.x, ui.draw.size.y
    m_w = 180
    limit = _dialog_text_limit(m_w)
    wrapped = _wrap_text(message, limit)

    # Calculate height: Title(20) + Text(lines*15) + Buttons(35) + Footer(20) + Padding(10)
    m_h = max(85, min(sh - 20, 85 + (len(wrapped) * 15)))
    m_x, m_y = (sw - m_w) // 2, (sh - m_h) // 2

    ui.draw.fill_round_rectangle(Vector(m_x + 4, m_y + 4), Vector(m_w, m_h), 5, TFT_BLACK)
    draw_panel(ui.draw, Vector(m_x, m_y), Vector(m_w, m_h), title, ui.theme["panel_c"], ui.theme["accent_c"], ui.theme["footer_text"])

    y_offset = 30
    for line in wrapped:
        ui.draw.text(Vector(m_x + 10, m_y + y_offset), line, ui.theme["text_c"])
        y_offset += 15

    yes_txt, no_txt = "YES", "NO"
    char_w = 6
    padding = 20
    btn_h = 20
    yes_btn_w = (len(yes_txt) * char_w) + padding
    no_btn_w = (len(no_txt) * char_w) + padding

    spacing = (m_w - yes_btn_w - no_btn_w) // 3
    yes_x = m_x + spacing
    no_x = m_x + spacing * 2 + yes_btn_w
    btn_y = m_y + m_h - 42 # Positioned relative to bottom

    draw_player_button(ui.draw, Vector(yes_x, btn_y), Vector(yes_btn_w, btn_h), "ok", active=True, highlighted=(sel_idx == 0), colors=ui.theme, radius=btn_h // 2)
    ui.draw.text(Vector(yes_x + (yes_btn_w - len(yes_txt)*char_w)//2, btn_y + 4), yes_txt, ui.theme["footer_text"])

    draw_player_button(ui.draw, Vector(no_x, btn_y), Vector(no_btn_w, btn_h), "ok", active=True, highlighted=(sel_idx == 1), colors=ui.theme, radius=btn_h // 2)
    ui.draw.text(Vector(no_x + (no_btn_w - len(no_txt)*char_w)//2, btn_y + 4), no_txt, ui.theme["footer_text"])

    ui.draw.fill_rectangle(Vector(m_x + 2, m_y + m_h - 18), Vector(m_w - 4, 15), ui.theme["accent_c"])
    ui.draw.text(Vector(m_x + 10, m_y + m_h - 15), t("hint_confirm"), ui.theme["footer_text"])
    ui.draw.swap()
