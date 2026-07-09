from picoware.system.vector import Vector
from vibesmp_lib.i18n import t
from vibesmp_lib.ui_utils import draw_scrollable_list


def format_library_item(i, item):
    if isinstance(item, tuple):
        label = item[1] if len(item) > 1 else str(item)
        return label
    if not isinstance(item, dict):
        return str(item)

    kind = item.get("kind", "")
    label = item.get("label", "") or item.get("title", "") or item.get("path", "")

    if kind == "category":
        return label
    if kind == "bucket":
        return "{} ({})".format(label, item.get("count", 0))
    if kind == "collection":
        return "{} ({})".format(label, item.get("count", len(item.get("tracks", []))))
    if kind == "folder":
        depth = int(item.get("depth", 0))
        prefix = "  " * depth
        prefix += "- " if item.get("expanded", False) else "+ "
        return prefix + label
    if kind == "track":
        depth = int(item.get("depth", 0))
        prefix = "  " * depth
        fav = "* " if item.get("favorite", False) else ""
        title = item.get("title", label)
        artist = item.get("artist", "")
        if artist and artist != "Unknown Artist":
            return prefix + fav + title + " - " + artist
        return prefix + fav + title
    return label


def render_library_browser(ui, title, items, selected_idx, force_full=False, swap=True, nav_fast=False):
    sw, sh = ui.draw.size.x, ui.draw.size.y
    header_updated = False
    item_h = 18
    list_pos = Vector(8, 26)
    list_size = Vector(sw - 16, sh - 68)

    if force_full:
        ui.draw_background()
        ui.render_header_footer(title)
    else:
        header_updated = ui.check_header_update(title)

    drew = force_full or header_updated
    cache_token = ("library_browser", title, len(items))
    draw_scrollable_list(
        ui.draw,
        list_pos,
        list_size,
        items,
        selected_idx,
        True,
        ui.theme,
        lambda i, x: format_library_item(i, x),
        item_h=item_h,
        row_cache=getattr(ui, "list_row_cache", None),
        cache_token=cache_token,
    )
    drew = True

    if force_full or header_updated:
        footer_y = sh - 16
        ui.draw.text(Vector(10, footer_y + 2), t("hint_library"), ui.theme["footer_text"])

    ui._library_browser_state = {"selected_idx": selected_idx, "count": len(items)}
    if swap and drew:
        ui.draw.swap()
