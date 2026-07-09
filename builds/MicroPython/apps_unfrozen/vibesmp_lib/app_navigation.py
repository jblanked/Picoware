from vibesmp_lib.ui import (
    VIEW_MENU, VIEW_NOW_PLAYING, VIEW_SETTINGS, VIEW_LIBRARY,
    VIEW_PLAYLIST_SELECTOR, VIEW_PLAYLIST_EDITOR, VIEW_INPUT_MODAL, VIEW_CONFIRM, VIEW_ALERT
)

def _move_menu_selection(menu, delta):
    count = len(menu.items) if menu and menu.items else 0
    if count <= 0:
        return
    if getattr(menu, "use_lvgl", False) and getattr(menu, "_lvgl_list", None) is not None:
        if delta < 0:
            menu.scroll_up(swap=False)
        else:
            menu.scroll_down(swap=False)
        return
    menu._selected_index = (menu._selected_index + delta) % count

def switch_view(app, view_id):
    """Unified view switcher for VibesApp."""
    app.ui.current_view = view_id
    app.needs_refresh = True
    # View-specific reset logic
    if view_id == VIEW_MENU:
        if hasattr(app, "main_menu") and app.main_menu:
            app.main_menu.set_selected(0)
    elif view_id == VIEW_SETTINGS:
        from vibesmp_lib.settings_view import update_settings_menu
        update_settings_menu(app)
    elif view_id == VIEW_PLAYLIST_SELECTOR:
        app.refresh_playlists()
    elif view_id == VIEW_NOW_PLAYING:
        if hasattr(app, "_prime_now_playing_lists"):
            app._prime_now_playing_lists()
    return True

def handle_main_menu_input(app, button):
    from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_CENTER, BUTTON_BACK
    if button == BUTTON_BACK:
        app.view_manager.back()
        return True
    if button == BUTTON_UP:
        _move_menu_selection(app.main_menu, -1); app.needs_refresh = True
    elif button == BUTTON_DOWN:
        _move_menu_selection(app.main_menu, 1); app.needs_refresh = True
    elif button == BUTTON_CENTER:
        sel = app.main_menu.selected_index
        if sel == 0: switch_view(app, VIEW_NOW_PLAYING)
        elif sel == 1: switch_view(app, VIEW_LIBRARY)
        elif sel == 2: switch_view(app, VIEW_SETTINGS)
        elif sel == 3:
            import vibesmp_lib.dialogs as d
            from vibesmp_lib.utils import get_path
            from vibesmp_lib.i18n import t
            lang = app.settings.config.get("language", "en")
            h_path = get_path(f"help/{lang}.txt")
            if not app.view_manager.storage.exists(h_path): h_path = get_path("help/en.txt")
            help_text = app.view_manager.storage.read(h_path)
            d.open_alert(app, t("menu_help"), help_text)
        app.needs_refresh = True
    return True
