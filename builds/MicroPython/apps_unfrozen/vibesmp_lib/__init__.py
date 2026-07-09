# Consolidated VibesMP package aliases.
import sys
from . import core as _core

for _name in (
    "utils", "i18n", "themes", "theme_manager", "storage_manager",
    "settings", "playlist", "scanner", "id3",
    "metadata_engine", "vibes_library", "loading", "app_navigation",
):
    sys.modules["vibesmp_lib." + _name] = _core
    globals()[_name] = _core

class _CompatModule:
    pass

def _compat_module(name):
    module = _CompatModule()
    module.__name__ = "vibesmp_lib." + name
    sys.modules["vibesmp_lib." + name] = module
    globals()[name] = module
    return module

settings_view = _compat_module("settings_view")
settings_view.update_settings_menu = _core.update_settings_menu
settings_view.handle_input = _core.handle_settings_input
settings_view.render = _core.render_settings

dialogs = _compat_module("dialogs")
dialogs.open_alert = _core.open_alert
dialogs.open_confirm = _core.open_confirm
dialogs.open_input = _core.open_input
dialogs.handle_input = _core.handle_dialog_input
dialogs.render = _core.render_dialog

from . import ui as _ui

for _name in (
    "ui_utils", "ui_elements", "ui_dialogs", "ui_library",
    "ui_player", "ui_playlist",
):
    sys.modules["vibesmp_lib." + _name] = _ui
    globals()[_name] = _ui
