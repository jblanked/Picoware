from vibesmp_lib.i18n import load_language, t
from vibesmp_lib.themes import THEMES
from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_CENTER

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

def update_settings_menu(app):
    curr_idx = app.settings_menu.selected_index if app.settings_menu else 0
    app.settings_menu.clear()
    app.settings_menu.add_item(f"{t('set_autoplay')}: {t('on') if app.settings.config['auto_play_next'] else t('off')}")
    app.settings_menu.add_item(f"{t('set_shuffle')}: {t('on') if app.settings.config['shuffle'] else t('off')}")
    app.settings_menu.add_item(f"{t('set_auto_expand')}: {t('on') if app.settings.config.get('auto_expand_library', True) else t('off')}")
    app.settings_menu.add_item(f"{t('set_lang')}: {app.settings.config['language'].upper()}")
    # Format theme name for display: replace underscore with space and uppercase
    display_theme = app.settings.config['theme'].replace('_', ' ').upper()
    app.settings_menu.add_item(f"Theme: {display_theme}")
    app.settings_menu.add_item(f"Time Format: {'24H' if app.settings.config.get('time_24h', True) else '12H'}")
    app.settings_menu.add_item(f"{t('set_volume')}: {app.settings.config.get('volume', 100)}%")
    app.settings_menu.add_item(f"{t('set_seek')}: {app.settings.config.get('seek_length', 5)}s")
    app.settings_menu.add_item(f"{t('set_focus_timeout')}: {app.settings.config.get('focus_timeout', 10)}s")
    app.settings_menu.add_item(t("back"))
    if curr_idx < len(app.settings_menu.items): app.settings_menu.set_selected(curr_idx)

def handle_input(app, button):
    from vibesmp_lib.ui import VIEW_MENU
    from picoware.system.buttons import BUTTON_BACK
    if button == BUTTON_BACK:
        app._switch_view(VIEW_MENU)
        return
    if button == BUTTON_UP: _move_menu_selection(app.settings_menu, -1); app.needs_refresh = True
    elif button == BUTTON_DOWN: _move_menu_selection(app.settings_menu, 1); app.needs_refresh = True
    elif button == BUTTON_CENTER:
        sel = app.settings_menu.selected_index
        if sel == 0: app.settings.toggle("auto_play_next"); update_settings_menu(app)
        elif sel == 1: app.settings.toggle("shuffle"); update_settings_menu(app)
        elif sel == 2: app.settings.toggle("auto_expand_library"); update_settings_menu(app)
        elif sel == 3:
            app.settings.next_lang()
            load_language(app.settings.config["language"])
            app.update_menus()
            update_settings_menu(app)
        elif sel == 4:
            app.settings.next_theme()
            from vibesmp_lib.theme_manager import load_theme
            app.ui.theme = load_theme(app.settings)
            update_settings_menu(app)
        elif sel == 5: app.settings.next_time_format(); update_settings_menu(app)
        elif sel == 6: app.settings.next_volume(); update_settings_menu(app)
        elif sel == 7: app.settings.next_seek_length(); update_settings_menu(app)
        elif sel == 8: app.settings.next_focus_timeout(); update_settings_menu(app)
        elif sel == 9: app._switch_view(VIEW_MENU)
        app.needs_refresh = True

def render(app, ui, force_full=False):
    ui.render_menu(app.settings_menu, t("menu_settings"), force_full=force_full)
