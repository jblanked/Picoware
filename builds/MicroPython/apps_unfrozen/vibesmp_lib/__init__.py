# Consolidated VibesMP package aliases.
import sys
from . import core as _core

for _name in (
    "utils", "i18n", "themes", "theme_manager", "storage_manager",
    "settings", "settings_view", "playlist", "scanner", "id3",
    "metadata_engine", "vibes_library", "loading", "app_navigation", "dialogs",
):
    sys.modules["vibesmp_lib." + _name] = _core
    globals()[_name] = _core

from . import ui as _ui

for _name in (
    "ui_utils", "ui_elements", "ui_dialogs", "ui_library",
    "ui_player", "ui_playlist",
):
    sys.modules["vibesmp_lib." + _name] = _ui
    globals()[_name] = _ui
