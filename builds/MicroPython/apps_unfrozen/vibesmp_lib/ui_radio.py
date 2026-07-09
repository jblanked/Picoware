from picoware.system.vector import Vector
from vibesmp_lib.i18n import t
from vibesmp_lib.ui_utils import draw_player_button, draw_scrollable_list


def _format_radio_item(i, item):
    if not isinstance(item, dict):
        return str(item)
    kind = item.get("kind", "station")
    if kind == "action":
        return item.get("label", "")
    name = item.get("name", item.get("url", ""))
    genre = item.get("genre", "")
    if genre:
        return "{} - {}".format(name, genre)
    return name


def _clip(text, chars):
    text = "" if text is None else str(text)
    if chars <= 0:
        return ""
    if len(text) <= chars:
        return text
    if chars <= 3:
        return text[:chars]
    return text[:chars - 3] + "..."


def render_radio(ui, stations, selected_idx, status, active_name="", force_full=False, swap=True, items=None):
    sw, sh = ui.draw.size.x, ui.draw.size.y
    title = t("menu_radio")
    header_updated = False
    item_h = 18

    if force_full:
        ui.draw_background()
        ui.render_header_footer(title)
    else:
        header_updated = ui.check_header_update(title)

    info_y = 25
    ui.draw.fill_rectangle(Vector(8, info_y), Vector(sw - 16, 32), ui.theme["bg_c"])
    state = status or t("radio_stopped")
    if active_name:
        state = "{}: {}".format(active_name, state)
    ui.draw.text(Vector(10, info_y), state[:max(1, (sw - 20) // 6)], ui.theme["accent_c"])

    if items is None:
        render_items = []
        for st in stations:
            render_items.append(st)
        render_items.append({"kind": "action", "action": "add", "label": t("radio_add_station")})
        render_items.append({"kind": "action", "action": "stop", "label": t("radio_stop")})
    else:
        render_items = items

    list_pos = Vector(8, 62)
    list_size = Vector(sw - 16, sh - 104)
    draw_scrollable_list(
        ui.draw,
        list_pos,
        list_size,
        render_items,
        selected_idx,
        True,
        ui.theme,
        _format_radio_item,
        item_h=item_h,
    )

    footer_y = sh - 16
    if force_full or header_updated:
        ui.draw.text(Vector(10, footer_y + 2), t("hint_radio"), ui.theme["footer_text"])
    if swap:
        ui.draw.swap()


def render_radio_player(ui, station, status, selected_idx=1, force_full=False, swap=True):
    sw, sh = ui.draw.size.x, ui.draw.size.y
    title = t("menu_radio")
    header_updated = False
    max_chars = max(1, (sw - 28) // 6)

    if force_full:
        ui.draw_background()
        ui.render_header_footer(title)
    else:
        header_updated = ui.check_header_update(title)

    name = ""
    url = ""
    if isinstance(station, dict):
        name = station.get("name", "")
        url = station.get("url", "")
    if not name:
        name = t("radio_stopped")

    panel_y = 28
    panel_h = sh - 92
    ui.draw.fill_rectangle(Vector(8, panel_y), Vector(sw - 16, panel_h), ui.theme.get("panel_c", ui.theme["well"]))

    ui.draw.text(Vector(14, panel_y + 10), _clip(name, max_chars), ui.theme["accent_c"])
    ui.draw.text(Vector(14, panel_y + 30), _clip(status or t("radio_stopped"), max_chars), ui.theme["text_c"])
    if url:
        ui.draw.text(Vector(14, panel_y + 50), _clip(url, max_chars), ui.theme.get("muted_c", ui.theme["text_c"]))

    btn_w = min(48, max(38, (sw - 60) // 2))
    btn_h = 22
    btn_gap = 18
    btn_y = sh - 62
    play_x = (sw - (btn_w * 2 + btn_gap)) // 2
    stop_x = play_x + btn_w + btn_gap
    draw_player_button(
        ui.draw,
        Vector(play_x, btn_y),
        Vector(btn_w, btn_h),
        "play",
        active=False,
        highlighted=selected_idx == 0,
        colors=ui.theme,
    )
    draw_player_button(
        ui.draw,
        Vector(stop_x, btn_y),
        Vector(btn_w, btn_h),
        "stop",
        active=False,
        highlighted=selected_idx == 1,
        colors=ui.theme,
    )

    if force_full or header_updated:
        ui.draw.text(Vector(10, sh - 18), t("hint_radio_player"), ui.theme["footer_text"])
    if swap:
        ui.draw.swap()
