from picoware.system.buttons import (
    BUTTON_CENTER, BUTTON_BACK, BUTTON_ENTER, BUTTON_LEFT, BUTTON_RIGHT,
    BUTTON_BACKSPACE, BUTTON_DELETE
)

def open_alert(app, title, message, callback=None):
    app.dialog_type = "alert"
    app.dialog_title = title
    app.dialog_message = message
    app.dialog_callback = callback
    app.dialog_scroll_idx = 0
    _show(app)

def open_confirm(app, title, message, callback, cancel_callback=None):
    app.dialog_type = "confirm"
    app.dialog_title = title
    app.dialog_message = message
    app.dialog_callback = callback
    app.dialog_cancel_callback = cancel_callback
    app.dialog_selected_idx = 0
    app.dialog_scroll_idx = 0
    _show(app)

def open_input(app, title, initial_text, callback, max_len=20):
    app.dialog_type = "input"
    app.dialog_title = title
    app.dialog_buffer = initial_text
    app.dialog_cursor_pos = len(initial_text)
    app.dialog_callback = callback
    app.dialog_max_len = max_len
    _show(app)

def _show(app):
    from vibesmp_lib.ui import VIEW_INPUT_MODAL, VIEW_CONFIRM, VIEW_ALERT
    # Only save last view if we are not already in a modal dialog
    # This ensures chained dialogs (Confirm -> Alert) return to the original view
    curr = app.ui.current_view
    if curr not in (VIEW_INPUT_MODAL, VIEW_CONFIRM, VIEW_ALERT):
        app.dialog_last_view = curr

    view = VIEW_INPUT_MODAL if app.dialog_type == "input" else VIEW_CONFIRM if app.dialog_type == "confirm" else VIEW_ALERT
    app._switch_view(view)
    app.needs_refresh = True

def handle_input(app, button):
    from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN
    from vibesmp_lib.ui import VIEW_INPUT_MODAL, VIEW_CONFIRM, VIEW_ALERT
    if button == BUTTON_BACK:
        app._switch_view(app.dialog_last_view)
        app.needs_refresh = True
        return True

    if app.dialog_type in ("confirm", "alert"):
        if button == BUTTON_UP:
            if app.dialog_scroll_idx > 0:
                app.dialog_scroll_idx -= 1; app.needs_refresh = True
            return True
        elif button == BUTTON_DOWN:
            # We don't have total lines here easily, but we'll cap it in render
            app.dialog_scroll_idx += 1; app.needs_refresh = True
            return True

    if app.dialog_type == "confirm":
        if button == BUTTON_LEFT: app.dialog_selected_idx = 0; app.needs_refresh = True
        elif button == BUTTON_RIGHT: app.dialog_selected_idx = 1; app.needs_refresh = True
        elif button in (BUTTON_CENTER, BUTTON_ENTER):
            old = (app.dialog_type, app.dialog_title, app.dialog_callback)
            if app.dialog_selected_idx == 0 and app.dialog_callback: app.dialog_callback()
            elif app.dialog_selected_idx == 1 and hasattr(app, "dialog_cancel_callback") and app.dialog_cancel_callback:
                app.dialog_cancel_callback()
            new_dialog = app.ui.current_view in (VIEW_INPUT_MODAL, VIEW_CONFIRM, VIEW_ALERT) and old != (app.dialog_type, app.dialog_title, app.dialog_callback)
            if not new_dialog:
                app._switch_view(app.dialog_last_view)
            app.needs_refresh = True
        return True

    elif app.dialog_type == "alert":
        if button in (BUTTON_CENTER, BUTTON_ENTER):
            old = (app.dialog_type, app.dialog_title, app.dialog_callback)
            if app.dialog_callback: app.dialog_callback()
            new_dialog = app.ui.current_view in (VIEW_INPUT_MODAL, VIEW_CONFIRM, VIEW_ALERT) and old != (app.dialog_type, app.dialog_title, app.dialog_callback)
            if not new_dialog:
                app._switch_view(app.dialog_last_view)
            app.needs_refresh = True
        return True

    elif app.dialog_type == "input":
        if button in (BUTTON_CENTER, BUTTON_ENTER):
            old = (app.dialog_type, app.dialog_title, app.dialog_callback)
            if app.dialog_callback: app.dialog_callback(app.dialog_buffer)
            new_dialog = app.ui.current_view in (VIEW_INPUT_MODAL, VIEW_CONFIRM, VIEW_ALERT) and old != (app.dialog_type, app.dialog_title, app.dialog_callback)
            if not new_dialog:
                app._switch_view(app.dialog_last_view)
            app.needs_refresh = True
        elif button == BUTTON_LEFT:
            if app.dialog_cursor_pos > 0: app.dialog_cursor_pos -= 1; app.needs_refresh = True
        elif button == BUTTON_RIGHT:
            if app.dialog_cursor_pos < len(app.dialog_buffer): app.dialog_cursor_pos += 1; app.needs_refresh = True
        elif button == BUTTON_BACKSPACE:
            if app.dialog_cursor_pos > 0:
                app.dialog_buffer = app.dialog_buffer[:app.dialog_cursor_pos-1] + app.dialog_buffer[app.dialog_cursor_pos:]
                app.dialog_cursor_pos -= 1; app.needs_refresh = True
        elif button == BUTTON_DELETE:
            if app.dialog_cursor_pos < len(app.dialog_buffer):
                app.dialog_buffer = app.dialog_buffer[:app.dialog_cursor_pos] + app.dialog_buffer[app.dialog_cursor_pos+1:]; app.needs_refresh = True
        elif button in app._char_map:
            max_len = getattr(app, "dialog_max_len", 20)
            if len(app.dialog_buffer) < max_len:
                char = app._char_map[button]
                if hasattr(app, "view_manager") and app.view_manager.input_manager.was_capitalized:
                    char = char.upper()
                app.dialog_buffer = app.dialog_buffer[:app.dialog_cursor_pos] + char + app.dialog_buffer[app.dialog_cursor_pos:]
                app.dialog_cursor_pos += 1; app.needs_refresh = True
        return True
    return False

def render(app, ui):
    if app.dialog_type == "confirm":
        ui.render_confirm(app.dialog_title, app.dialog_message, app.dialog_selected_idx, app.dialog_scroll_idx)
    elif app.dialog_type == "alert":
        ui.render_modal(app.dialog_title, app.dialog_message, "OK", app.dialog_scroll_idx)
    elif app.dialog_type == "input":
        ui.render_input_dialog(app.dialog_title, app.dialog_buffer, app.dialog_cursor_pos, False)
