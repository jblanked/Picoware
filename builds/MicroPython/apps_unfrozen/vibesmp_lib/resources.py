import json

# ---- theme resources ----

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

LANG_DATA = {'de': {'menu_player': 'Player', 'menu_playlist': 'Wiedergabeliste', 'menu_play_file': 'Datei abspielen', 'menu_library': 'Bibliothek', 'menu_editor': 'Editor', 'menu_settings': 'Einstellungen', 'menu_help': 'Hilfe', 'menu_playlist_manager': 'Listen-Manager', 'now_playing': 'Wird abgespielt', 'no_track': 'Kein Titel', 'playing': 'Play', 'paused': 'Pause', 'stopped': 'Stop', 'loop_none': 'Wiederholung: Aus', 'loop_one': 'Wiederholung: Eins', 'loop_all': 'Wiederholung: Alle', 'editor_color': 'Farbe aendern', 'editor_bg': 'Hintergrund', 'editor_save': 'Speichern', 'set_autoplay': 'Auto-Play', 'set_shuffle': 'Zufall', 'set_auto_expand': 'Bibl. auto-ausklappen', 'set_lang': 'Sprache', 'set_volume': 'Lautstaerke', 'set_seek': 'Sprungweite', 'set_focus_timeout': 'Fokus Timeout', 'refresh_library': 'Bibl. aktualisieren', 'back': 'Zurueck', 'on': 'AN', 'off': 'AUS', 'menu_playlist_editor': 'Listen-Editor', 'menu_playlists': 'Wiedergabelisten', 'library': 'Bibliothek', 'playlist': 'Titel', 'playlists': 'Listen', 'new_playlist': '+ Neue Liste', 'playlist_new': 'Neue Liste', 'playlist_del': 'Liste loeschen', 'playlist_selector': 'Liste waehlen', 'playlist_editor': 'Listen-Editor', 'hint_np_controls': 'TAB:Listen P:Pause ESC:Stop [/:Seek <>:Titel L:Loop S:Mix V:.,', 'hint_np_lib': 'TAB:Player UD:Scroll LR:Bereich OK:Add/Auf', 'hint_np_trk': 'TAB:Player UD:Scroll LR:Bereich OK:Play DEL:Entf', 'hint_np_pls': 'TAB:Player UD:Scroll LR:Bereich OK:Laden N:Neu DEL:Loesch', 'hint_playlist_sel': 'UD:Scroll OK:Laden DEL:Loeschen BACK:Menue', 'hint_playlist_ed': 'LR:Bereich UD:Wahl OK:Add/Entf BACK:Menue', 'hint_continue': 'ENT:Weiter', 'hint_confirm': 'LR:Waehlen ENT:Bestaetigen', 'confirm': 'Bestaetigen', 'delete': 'Loeschen'}, 'en': {'app_name': 'VibesMP', 'menu_player': 'Player', 'menu_playlist': 'Playlist', 'menu_play_file': 'Play File', 'menu_library': 'Library', 'menu_editor': 'Editor', 'menu_settings': 'Settings', 'menu_help': 'Help', 'first_run_title': 'VibesMP', 'first_run_msg': 'Scan SD card for music now?', 'scanning_title': 'Scanning SD Card...', 'scan_complete_title': 'Scan Complete', 'scan_complete_msg': 'Found {} MP3 files.', 'menu_playlist_manager': 'Playlist Manager', 'now_playing': 'Now Playing', 'no_track': 'No Track', 'playing': 'Playing', 'paused': 'Paused', 'stopped': 'Stopped', 'loop_none': 'Loop: No', 'loop_one': 'Loop: One', 'loop_all': 'Loop: All', 'editor_color': 'Change Color', 'editor_bg': 'Background', 'editor_save': 'Save', 'set_autoplay': 'Auto-Play Next', 'set_shuffle': 'Shuffle', 'set_auto_expand': 'Auto-Expand Lib', 'set_lang': 'Language', 'set_volume': 'Volume', 'set_seek': 'Seek Step', 'set_focus_timeout': 'Focus Timeout', 'refresh_library': 'Refresh Library', 'lib_all_songs': 'All Songs', 'lib_artists': 'Artists', 'lib_albums': 'Albums', 'lib_folders': 'Folders', 'lib_genres': 'Genres', 'lib_recently_added': 'Recently Added', 'lib_favorites': 'Favorites', 'lib_search': 'Search', 'lib_scan_options': 'Scan Options', 'lib_sort': 'Sort', 'lib_filters': 'Filters', 'lib_stats': 'Library Stats', 'lib_cleanup': 'Cleanup', 'lib_scan': 'Scan Library', 'lib_actions': 'Actions', 'lib_action_play_now': 'Play Now', 'lib_action_play_next': 'Play Next', 'lib_action_add_current': 'Add to Current Playlist', 'lib_action_create_playlist': 'Create Playlist', 'lib_action_remove_library': 'Remove from Library', 'lib_action_add_favorite': 'Add Favorite', 'lib_action_remove_favorite': 'Remove Favorite', 'lib_action_show_info': 'Show Info', 'lib_info': 'Track Info', 'lib_tracks': 'Tracks', 'lib_scan_total': 'Total', 'lib_scan_added': 'Added', 'lib_scan_removed': 'Removed', 'lib_scan_unchanged': 'Unchanged', 'lib_scan_found': 'Found', 'lib_scan_failed': 'Failed', 'lib_removed': 'Removed', 'lib_favorites_cleared': 'Favorites cleared', 'hint_library': 'UD:Scroll LR:Folder OK:Open/Action BACK:Back', 'back': 'Back', 'on': 'ON', 'off': 'OFF', 'menu_playlist_editor': 'Playlist Editor', 'menu_playlists': 'Playlists', 'library': 'Library', 'playlist': 'Tracks', 'playlists': 'Playlists', 'new_playlist': '+ New Playlist', 'playlist_new': 'New Playlist', 'playlist_del': 'Delete Playlist', 'playlist_selector': 'Select Playlist', 'playlist_editor': 'Playlist Editor', 'hint_np_controls': 'TAB:Lists P:Pause ESC:Stop [/:Seek <>:Trk L:Loop S:Shuf V:.,', 'hint_np_lib': 'TAB:Player UD:Scroll LR:Panels OK:Add/Expand', 'hint_np_trk': 'TAB:Player UD:Scroll LR:Panels OK:Play DEL:Rem', 'hint_np_pls': 'TAB:Player UD:Scroll LR:Panels OK:Load N:New DEL:Del', 'hint_playlist_sel': 'UD:Scroll OK:Load DEL:Delete BACK:Menu', 'hint_playlist_ed': 'LR:Panel UD:Sel OK:Add/Rem BACK:Menu', 'hint_continue': 'ENT:Continue', 'hint_confirm': 'LR:Choose ENT:Confirm', 'confirm': 'Confirm', 'delete': 'Delete'}, 'es': {'menu_player': 'Reproductor', 'menu_playlist': 'Lista', 'menu_play_file': 'Reproducir archivo', 'menu_library': 'Biblioteca', 'menu_editor': 'Editor', 'menu_settings': 'Ajustes', 'menu_help': 'Ayuda', 'menu_playlist_manager': 'Gestor de listas', 'now_playing': 'Reproduciendo', 'no_track': 'Sin pista', 'playing': 'Reproduciendo', 'paused': 'Pausa', 'stopped': 'Detenido', 'loop_none': 'Bucle: No', 'loop_one': 'Bucle: Uno', 'loop_all': 'Bucle: Todo', 'editor_color': 'Cambiar color', 'editor_bg': 'Fondo', 'editor_save': 'Guardar', 'set_autoplay': 'Auto-reproducir', 'set_shuffle': 'Aleatorio', 'set_auto_expand': 'Auto-expandir bibl.', 'set_lang': 'Idioma', 'set_volume': 'Volumen', 'set_seek': 'Salto', 'set_focus_timeout': 'Tiempo Foco', 'refresh_library': 'Actualizar bibl.', 'back': 'Atrás', 'on': 'ON', 'off': 'OFF', 'menu_playlist_editor': 'Editor de listas', 'menu_playlists': 'Listas', 'library': 'Biblioteca', 'playlist': 'Pistas', 'playlists': 'Listas', 'new_playlist': '+ Nueva lista', 'playlist_new': 'Nueva lista', 'playlist_del': 'Borrar lista', 'playlist_selector': 'Seleccionar lista', 'playlist_editor': 'Editor de listas', 'hint_np_controls': 'TAB:Listas P:Pause ESC:Stop [/:Seek <>:Pista L:Loop S:Shuf V:.,', 'hint_np_lib': 'TAB:Repro UD:Scroll LR:Panel OK:Add/Abrir', 'hint_np_trk': 'TAB:Repro UD:Scroll LR:Panel OK:Repro DEL:Borrar', 'hint_np_pls': 'TAB:Repro UD:Scroll LR:Panel OK:Cargar N:Nueva DEL:Borrar', 'hint_playlist_sel': 'UD:Scroll OK:Cargar DEL:Borrar BACK:Menu', 'hint_playlist_ed': 'LR:Panel UD:Sel OK:Add/Rem BACK:Menu', 'hint_continue': 'ENT:Continuar', 'hint_confirm': 'LR:Elegir ENT:Confirmar', 'confirm': 'Confirmar', 'delete': 'Borrar'}, 'fr': {'menu_player': 'Lecteur', 'menu_playlist': 'Liste', 'menu_play_file': 'Lire fichier', 'menu_library': 'Bibliothèque', 'menu_editor': 'Éditeur', 'menu_settings': 'Réglages', 'menu_help': 'Aide', 'menu_playlist_manager': 'Gestionnaire', 'now_playing': 'En lecture', 'no_track': 'Aucun titre', 'playing': 'Lecture', 'paused': 'Pause', 'stopped': 'Arrêté', 'loop_none': 'Boucle: Non', 'loop_one': 'Boucle: Un', 'loop_all': 'Boucle: Tout', 'editor_color': 'Changer couleur', 'editor_bg': 'Fond', 'editor_save': 'Enregistrer', 'set_autoplay': 'Lecture auto', 'set_shuffle': 'Aléatoire', 'set_auto_expand': 'Auto-développer bibl.', 'set_lang': 'Langue', 'set_volume': 'Volume std', 'set_seek': 'Saut', 'set_focus_timeout': 'Delai Focus', 'refresh_library': 'Actualiser bibl.', 'back': 'Retour', 'on': 'ON', 'off': 'OFF', 'menu_playlist_editor': 'Éditeur de listes', 'menu_playlists': 'Listes', 'library': 'Bibliothèque', 'playlist': 'Titres', 'playlists': 'Listes', 'new_playlist': '+ Nouvelle liste', 'playlist_new': 'Nouvelle liste', 'playlist_del': 'Supprimer liste', 'playlist_selector': 'Choisir liste', 'playlist_editor': 'Éditeur de listes', 'hint_np_controls': 'TAB:Listes P:Pause ESC:Stop [/:Seek <>:Titre L:Boucle S:Rand V:.,', 'hint_np_lib': 'TAB:Lect UD:Scroll LR:Panneau OK:Add/Ouvr', 'hint_np_trk': 'TAB:Lect UD:Scroll LR:Panneau OK:Lire DEL:Suppr', 'hint_np_pls': 'TAB:Lect UD:Scroll LR:Panneau OK:Charg N:Nouv DEL:Suppr', 'hint_playlist_sel': 'UD:Scroll OK:Charger DEL:Suppr BACK:Menu', 'hint_playlist_ed': 'LR:Panneau UD:Sel OK:Add/Suppr BACK:Menu', 'hint_continue': 'ENT:Continuer', 'hint_confirm': 'LR:Choisir ENT:Confirmer', 'confirm': 'Confirmer', 'delete': 'Supprimer'}}

HELP_TEXT = {'de.txt': 'VibesMP ist eine spezialisierte MicroPython-Audioanwendung, die für RP2350-Mikrocontroller entwickelt wurde. Sie bietet hochpräzise MP3-Wiedergabe unter Nutzung hardwarebeschleunigter Dekodierungsfunktionen bei gleichzeitig geringem Speicherverbrauch und hoher Reaktionsfähigkeit während gleichzeitiger SD-Karten-Dateioperationen und Benutzeroberflächen-Rendering-Aufgaben auf eingebetteten Hardwareplattformen.\n\nDie Anwendung implementiert ID3v2-Tag-Parsing zur Metadaten-Extraktion, Echtzeit-Skalierung und Anzeige von JPEG- und BMP-Albumcovern, lückenlose Wiedergabe-Übergangslogik, dynamische Playlist-Verwaltung einschließlich Erstellung und Modifikation sowie ein Drei-Spalten-Navigationssystem für effizientes Durchsuchen der Bibliothek, Titelauswahl und Playlist-Wechsel über verschiedene Speicherverzeichnisse.\n\nVerfügbare Konfigurationsparameter umfassen Auto-Play-Umschaltung für sequenzielles Vorrücken der Titel, Auswahl von Shuffle- und Loop-Modi, Sprachlokalisierung für Englisch, Deutsch, Französisch und Spanisch, visuelle Themen-Voreinstellungen unter Verwendung von RGB565-Paletten, einstellbare Suchintervalle von einer bis fünfzehn Sekunden, Fokus-Timeout-Management und persistente Speicherung aller Präferenzen.\n\nNavigationssteuerungen nutzen das Standard-D-Pad-Mapping: Auf und Ab für vertikales Listen-Scrollen, Links und Rechts für Spaltenwechsel und Lautstärkeeinstellung, Mitteltaste für Auswahlbestätigung und Wiedergabe-Pause-Umschaltung, Zurück-Taste für Ansichts-Regression oder Beendigung der Anwendung und spezialisierte alphanumerische Zuweisung für die Playlist-Benennung.\n\nErstellt von Slasher006 mit der Hilfe von Gemini, 2026. Dieses Projekt zeigt fortschrittliche MicroPython-Implementierungstechniken, effiziente Strategien für die Speicherverwaltung für ressourcenbeschränkte eingebettete Systeme und die kollaborative Softwareentwicklung zwischen menschlichen Ingenieuren und künstlicher Intelligenz zur Bereitstellung eines überlegenen Multimedia-Erlebnisses auf der RP2350-Plattform.\n', 'en.txt': 'VibesMP is a dedicated MicroPython audio application engineered for RP2350 microcontrollers. It provides high-fidelity MP3 playback leveraging hardware-accelerated decoding capabilities while maintaining a low memory footprint and high responsiveness during concurrent SD card file operations and user interface rendering tasks on embedded hardware platforms.\n\nThe application implements ID3v2 tag parsing for metadata extraction, real-time JPEG and BMP album art scaling and display, gapless playback transition logic, dynamic playlist management including creation and modification, and a three-column navigational system for efficient library browsing, track selection, and playlist switching across various storage directories.\n\nAvailable configuration parameters include auto-play toggle for sequential track advancement, shuffle and loop mode selection, language localization for English, German, French, and Spanish, visual theme presets using RGB565 palettes, adjustable seek intervals from one to fifteen seconds, focus timeout management, and persistent storage of all preferences.\n\nNavigational controls utilize the standard D-Pad mapping: Up and Down for vertical list scrolling, Left and Right for column switching and volume adjustment, Center button for selection confirmation and play and pause toggling, Back button for view regression or application termination, and specialized alphanumeric mapping for naming.\n\nMade by Slasher006 with the help of Gemini, 2026. This project showcases advanced MicroPython implementation techniques, efficient memory management strategies for resource-constrained embedded systems, and collaborative software development between human engineers and artificial intelligence to deliver a superior multimedia experience on the RP2350 microcontroller platform.\n', 'es.txt': 'VibesMP es una aplicación de audio MicroPython dedicada, diseñada para microcontroladores RP2350. Proporciona una reproducción de MP3 de alta fidelidad aprovechando las capacidades de decodificación acelerada por hardware, manteniendo una baja huella de memoria y una alta capacidad de respuesta durante las operaciones simultáneas de archivos en la tarjeta SD y las tareas de renderizado de la interfaz de usuario en plataformas de hardware integradas.\n\nLa aplicación implementa el análisis de etiquetas ID3v2 para la extracción de metadatos, el escalado y la visualización en tiempo real de portadas de álbumes en formato JPEG y BMP, la lógica de transición de reproducción sin interrupciones, la gestión dinámica de listas de reproducción incluyendo creación y modificación, y un sistema de navegación de tres columnas para la exploración eficiente de la biblioteca, la selección de pistas y el cambio de lista de reproducción a través de diversos directorios de almacenamiento.\n\nLos parámetros de configuración disponibles incluyen la alternancia de reproducción automática para el avance secuencial de pistas, la selección de modos de reproducción aleatoria y en bucle, la localización de idiomas para inglés, alemán, francés y español, ajustes visuales preestablecidos mediante paletas RGB565, intervalos de búsqueda ajustables de uno a quince segundos, gestión del tiempo de espera de enfoque y almacenamiento persistente de todas las preferencias.\n\nLos controles de navegación utilizan el mapeo estándar del D-Pad: arriba y abajo para el desplazamiento vertical de la lista, izquierda y derecha para el cambio de columna y el ajuste de volumen, el botón central para la confirmación de la selección y la alternancia de reproducción y pausa, el botón de retroceso para la regresión de vista o la terminación de la aplicación, y un mapeo alfanumérico especializado para el nombramiento.\n\nRealizado por Slasher006 con la ayuda de Gemini, 2026. Este proyecto muestra técnicas avanzadas de implementación de MicroPython, estrategias eficientes de gestión de memoria para sistemas integrados con recursos limitados y el desarrollo colaborativo de software entre ingenieros humanos e inteligencia artificial para ofrecer una experiencia multimedia superior en la plataforma del microcontrolador RP2350.\n', 'first_start_de.txt': 'Willkommen bei VibesMP! Um Ihre musikalische Reise zu beginnen, führen Sie bitte einen ersten Scan Ihrer SD-Karte durch, um alle verfügbaren MP3-Dateien zu indizieren. Wenn Sie später neue Titel hinzufügen, verwenden Sie einfach die Option "Bibliothek scannen" im Hauptmenü, um Ihre Datenbank zu aktualisieren und sicherzustellen, dass alle neuen Tracks korrekt erkannt und in der Anwendung angezeigt werden.\n', 'first_start_en.txt': 'Welcome to VibesMP! To begin your musical journey, please perform an initial scan of your SD card to index all available MP3 files. If you add new tracks to your collection later, simply use the "Scan Library" option in the main menu to refresh your database and ensure all new music is correctly detected and displayed within the application.\n', 'first_start_es.txt': '¡Bienvenido a VibesMP! Para comenzar su viaje musical, realice un escaneo inicial de su tarjeta SD para indexar todos los archivos MP3 disponibles. Si agrega pistas nuevas más tarde, simplemente use la opción "Escanear biblioteca" en el menú principal para actualizar su base de datos y asegurarse de que toda la música nueva se detecte y se muestre correctamente dentro de la aplicación.\n', 'first_start_fr.txt': 'Bienvenue sur VibesMP ! Pour commencer votre voyage musical, veuillez effectuer un premier scan de votre carte SD pour indexer tous les fichiers MP3 disponibles. Si vous ajoutez de nouvelles pistes plus tard, utilisez simplement l\'option "Scanner la bibliothèque" dans le menu principal pour actualiser votre base de données et garantir que toute nouvelle musique est correctement détectée et affichée dans l\'application.\n', 'fr.txt': "VibesMP est une application audio MicroPython dédiée, conçue pour les microcontrôleurs RP2350. Elle offre une lecture MP3 haute fidélité en exploitant les capacités de décodage accélérées par le matériel, tout en maintenant une faible empreinte mémoire et une grande réactivité lors des opérations simultanées sur les fichiers de la carte SD et des tâches de rendu de l'interface utilisateur sur les plateformes matérielles embarquées.\n\nL'application implémente l'analyse des balises ID3v2 pour l'extraction des métadonnées, la mise à l'échelle et l'affichage en temps réel des pochettes d'album au format JPEG et BMP, la logique de transition pour la lecture sans interruption, la gestion dynamique des listes de lecture comprenant la création et la modification, et un système de navigation à trois colonnes pour l'exploration efficace de la bibliothèque, la sélection des pistes et le changement de liste de lecture à travers divers répertoires de stockage.\n\nLes paramètres de configuration disponibles incluent l'activation de la lecture automatique pour l'avancement séquentiel des pistes, la sélection du mode aléatoire ou en boucle, la localisation linguistique pour l'anglais, l'allemand, le français et l'espagnol, les thèmes visuels prédéfinis utilisant des palettes RGB565, des intervalles de recherche réglables de une à quinze secondes, la gestion du délai de mise au point et le stockage persistant de toutes les préférences.\n\nLes commandes de navigation utilisent le mappage standard du D-Pad : haut et bas pour le défilement vertical des listes, gauche et droite pour le changement de colonne et le réglage du volume, le bouton central pour la confirmation de la sélection et le basculement lecture et pause, le bouton retour pour le retour à la vue précédente ou l'arrêt de l'application, et un mappage alphanumérique spécialisé pour le nommage.\n\nRéalisé par Slasher006 avec l'aide de Gemini, 2026. Ce projet met en évidence des techniques avancées d'implémentation MicroPython, des stratégies de gestion de mémoire efficaces pour les systèmes embarqués à ressources limitées, et un développement logiciel collaboratif entre des ingénieurs humains et l'intelligence artificielle pour offrir une expérience multimédia supérieure sur la plateforme du microcontrôleur RP2350.\n"}


_translations = {}
_fallback = LANG_DATA.get("en", {})
_current_lang = ""
_storage = None
DEBUG_I18N = False

def set_storage(storage):
    global _storage
    _storage = storage

def load_language(lang="en"):
    global _translations, _fallback, _current_lang
    _fallback = LANG_DATA.get("en", {})
    _translations = LANG_DATA.get(lang, _fallback)
    _current_lang = lang

def t(key):
    res = _translations.get(key)
    if res is not None:
        return res
    return _fallback.get(key, key)

def get_help_text(lang="en", first_start=False):
    prefix = "first_start_" if first_start else ""
    name = prefix + lang + ".txt"
    return HELP_TEXT.get(name) or HELP_TEXT.get(prefix + "en.txt") or ""

# ---- settings_view.py ----

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

def handle_settings_input(app, button):
    from vibesmp_lib.ui_utils import VIEW_MENU
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
            # load_theme is provided by consolidated core
            app.ui.theme = load_theme(app.settings)
            update_settings_menu(app)
        elif sel == 5: app.settings.next_time_format(); update_settings_menu(app)
        elif sel == 6: app.settings.next_volume(); update_settings_menu(app)
        elif sel == 7: app.settings.next_seek_length(); update_settings_menu(app)
        elif sel == 8: app.settings.next_focus_timeout(); update_settings_menu(app)
        elif sel == 9: app._switch_view(VIEW_MENU)
        app.needs_refresh = True

def render_settings(app, ui, force_full=False):
    ui.render_menu(app.settings_menu, t("menu_settings"), force_full=force_full)

# ---- app_navigation.py ----


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
    from vibesmp_lib.ui_utils import VIEW_MENU, VIEW_SETTINGS, VIEW_PLAYLIST_SELECTOR, VIEW_NOW_PLAYING
    """Unified view switcher for VibesApp."""
    app.ui.current_view = view_id
    app.needs_refresh = True
    # View-specific reset logic
    if view_id == VIEW_MENU:
        if hasattr(app, "main_menu") and app.main_menu:
            app.main_menu.set_selected(0)
    elif view_id == VIEW_SETTINGS:
        from vibesmp_lib.resources import update_settings_menu
        update_settings_menu(app)
    elif view_id == VIEW_PLAYLIST_SELECTOR:
        app.refresh_playlists()
    elif view_id == VIEW_NOW_PLAYING:
        if hasattr(app, "_prime_now_playing_lists"):
            app._prime_now_playing_lists()
    return True

def handle_main_menu_input(app, button):
    from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_CENTER, BUTTON_BACK
    from vibesmp_lib.ui_utils import VIEW_NOW_PLAYING, VIEW_LIBRARY, VIEW_SETTINGS
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
            import vibesmp_lib.resources as d
            from vibesmp_lib.resources import get_help_text, t
            lang = app.settings.config.get("language", "en")
            help_text = get_help_text(lang)
            d.open_alert(app, t("menu_help"), help_text)
        app.needs_refresh = True
    return True

# ---- dialogs.py ----

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
    from vibesmp_lib.ui_utils import VIEW_INPUT_MODAL, VIEW_CONFIRM, VIEW_ALERT
    # Only save last view if we are not already in a modal dialog
    # This ensures chained dialogs (Confirm -> Alert) return to the original view
    curr = app.ui.current_view
    if curr not in (VIEW_INPUT_MODAL, VIEW_CONFIRM, VIEW_ALERT):
        app.dialog_last_view = curr

    view = VIEW_INPUT_MODAL if app.dialog_type == "input" else VIEW_CONFIRM if app.dialog_type == "confirm" else VIEW_ALERT
    app._switch_view(view)
    app.needs_refresh = True

def handle_dialog_input(app, button):
    from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN
    from vibesmp_lib.ui_utils import VIEW_INPUT_MODAL, VIEW_CONFIRM, VIEW_ALERT
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

def render_dialog(app, ui):
    if app.dialog_type == "confirm":
        ui.render_confirm(app.dialog_title, app.dialog_message, app.dialog_selected_idx, app.dialog_scroll_idx)
    elif app.dialog_type == "alert":
        ui.render_modal(app.dialog_title, app.dialog_message, "OK", app.dialog_scroll_idx)
    elif app.dialog_type == "input":
        ui.render_input_dialog(app.dialog_title, app.dialog_buffer, app.dialog_cursor_pos, False)
