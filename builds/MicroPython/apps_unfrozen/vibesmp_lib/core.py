# Consolidated VibesMP support modules.

import json

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


# ---- utils.py ----

import os

# Dynamic path resolution to avoid hardcoding /sd/...
_base_path = ""
try:
    _f = __file__
    if _f.startswith("/"):
        if "/" in _f:
            _base_path = _f.rsplit("/", 1)[0] + "/"
        else:
            _base_path = "/"
    else:
        _cwd = os.getcwd()
        if not _cwd.endswith("/"): _cwd += "/"
        if _f.startswith("./"): _f = _f[2:]
        if "/" in _f:
            _base_path = _cwd + _f.rsplit("/", 1)[0] + "/"
        else:
            _base_path = _cwd
except (NameError, AttributeError, OSError):
    # Fallback to standard path if __file__ resolution fails
    _base_path = "picoware/apps/vibesmp_lib/"

# Ensure _base_path doesn't have /sd/ for Storage API compatibility
if _base_path.startswith("/sd/"):
    _base_path = _base_path[4:]
elif _base_path.startswith("sd/"):
    _base_path = _base_path[3:]

def get_path(subpath):
    """Resolve an absolute path within the app package."""
    path = _base_path + subpath
    # Final safety check: remove leading / for Storage API
    if path.startswith("/"):
        path = path[1:]
    return path

def format_time(seconds):
    """Format seconds into MM:SS string."""
    seconds = int(seconds)
    return f"{seconds // 60:02}:{seconds % 60:02}"

def get_filename(path):
    """Get just the filename or folder name from a full path."""
    if not path:
        return ""
    p = path.rstrip("/")
    res = p.split("/")[-1]
    if res.lower().endswith(".mp3"):
        res = res[:-4]
    return res

def get_parent_path(path):
    """Get parent directory path with trailing slash."""
    if not path or path in ("/", "/sd/"):
        return "/sd/"
    parts = path.strip("/").split("/")
    if len(parts) <= 1:
        return "/sd/"
    return "/" + "/".join(parts[:-1]) + "/"

def mkdir_p(storage, path):
    """Create directory and its parents if they don't exist."""
    if not path or path == "/":
        return True

    clean_path = path.replace("\\", "/").strip("/")
    while "//" in clean_path:
        clean_path = clean_path.replace("//", "/")

    if not clean_path:
        return True

    if storage.is_directory(clean_path):
        return True

    parts = clean_path.split("/")
    for i in range(len(parts)):
        curr = "/".join(parts[:i+1])
        if not storage.is_directory(curr):
            if not storage.mkdir(curr):
                return False
    return True


# ---- themes.py ----

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


# ---- storage_manager.py ----

"""
Storage Manager - Centralized background writer for VibesMP
Prevents race conditions, file corruption, and SD card wear.
"""

import time
import json
from picoware.system.storage import Storage

class StorageManager:
    """Singleton manager for background storage operations."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.storage = None
        self.audio = None
        self.pending_writes = {} # {path: {"data": ..., "on_success": ..., "on_error": ...}}
        self._last_write_time = {} # {path: ticks_ms}

        # Throttling configuration (ms)
        self._min_delay = {
            'settings.json': 5000,
            'playback_state.json': 2000,
            'default.json': 30000,
        }

        self._initialized = True

    def set_storage(self, storage):
        """Set the underlying storage instance."""
        self.storage = storage

    def set_audio(self, audio):
        """Set the audio instance for SD bus contention detection."""
        self.audio = audio

    def request_write(self, filepath, data, on_success=None, on_error=None):
        """Buffer a write request. Overwrites existing pending data for the same path."""
        self.pending_writes[filepath] = {
            "data": data,
            "on_success": on_success,
            "on_error": on_error,
        }
        return True

    def cancel_write(self, filepath):
        """Cancel any pending write for the given filepath."""
        return self.pending_writes.pop(filepath, None)

    def tick(self):
        """Process one pending write if its throttle period has elapsed."""
        if not self.storage or not self.pending_writes:
            return
        # Defer all writes while Core 1 is actively reading SD
        try:
            if self.audio and self.audio.is_sd_busy:
                return
        except AttributeError:
            pass

        now = time.ticks_ms()

        for filepath in list(self.pending_writes.keys()):
            # Determine throttle delay
            filename = filepath.rsplit("/", 1)[-1]
            delay = self._min_delay.get(filepath, self._min_delay.get(filename, 500))

            last_time = self._last_write_time.get(filepath, 0)
            if time.ticks_diff(now, last_time) >= delay:
                entry = self.pending_writes.pop(filepath)
                if self._do_write(filepath, entry):
                    self._last_write_time[filepath] = time.ticks_ms()
                break # Process only one write per tick to maintain UI responsiveness

    def _do_write(self, filepath, entry):
        """Perform the actual write with atomic-swap protection."""
        data = entry["data"]
        on_success = entry.get("on_success")
        on_error = entry.get("on_error")
        try:
            temp_path = f"{filepath}.tmp"
            bak_path = f"{filepath}.bak"

            # 1. Write to temp
            if not self.storage.write(temp_path, data, "w"):
                print(f"[ERROR] StorageManager: Write to {temp_path} failed")
                if on_error:
                    on_error()
                return False

            # 2. Backup existing file
            has_existing = self.storage.exists(filepath)
            if has_existing:
                if self.storage.exists(bak_path):
                    self.storage.remove(bak_path)
                if not self.storage.rename(filepath, bak_path):
                    print(f"[ERROR] StorageManager: Failed to backup {filepath}")
                    if on_error:
                        on_error()
                    return False

            # 3. Rename temp to live file
            if self.storage.rename(temp_path, filepath):
                # 4. Remove backup
                if has_existing and self.storage.exists(bak_path):
                    self.storage.remove(bak_path)
                if on_success:
                    on_success()
                return True
            else:
                print(f"[ERROR] StorageManager: Rename {temp_path} -> {filepath} failed")
                # Rollback if possible
                if has_existing and self.storage.exists(bak_path):
                    self.storage.rename(bak_path, filepath)
                if on_error:
                    on_error()
                return False

        except (OSError, ValueError) as e:
            import sys
            print(f"[ERROR] StorageManager: Failed to write {filepath}: {e}")
            sys.print_exception(e)
            if on_error:
                on_error()
            return False

    def close(self):
        """Flush all pending writes immediately (blocking)."""
        if not self._initialized or not self.storage:
            return True

        print(f"[DEBUG] StorageManager: Flushing {len(self.pending_writes)} pending writes...")
        flushed = True
        pending = self.pending_writes
        self.pending_writes = {}

        while pending:
            filepath, entry = pending.popitem()
            if self._do_write(filepath, entry):
                self._last_write_time[filepath] = time.ticks_ms()
            else:
                self.pending_writes[filepath] = entry
                flushed = False

        if flushed:
            self._last_write_time.clear()

        return flushed


# ---- settings.py ----

import json

class Settings:
    def __init__(self, storage):
        self.storage = storage
        self.config = {
            "auto_play_next": True,
            "shuffle": False,
            "language": "en",
            "theme": "dark",
            "volume": 100,
            "seek_length": 5,
            "first_run": True,
            "auto_expand_library": True,
            "loop_mode": 0,
            "focus_timeout": 10,
            "time_24h": True,
            "list_view_policy": "offset",
            "list_scroll_offset": 2
        }
        self._is_dirty = False
        self._save_pending = False
        self.available_themes = ["dark", "midnight", "nord", "forest", "solarized", "coffee"]
        self.available_volumes = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        self.load()

    def next_time_format(self):
        self.config["time_24h"] = not self.config.get("time_24h", True)
        self._is_dirty = True

    def next_focus_timeout(self):
        try:
            curr = self.config.get("focus_timeout", 10)
            new_v = curr + 5
            if new_v > 20: new_v = 5
            self.config["focus_timeout"] = new_v
            self._is_dirty = True
        except TypeError:
            self.config["focus_timeout"] = 10
            self._is_dirty = True

    def next_seek_length(self):
        try:
            curr = self.config.get("seek_length", 5)
            # Cycle 1 to 15
            new_v = curr + 1
            if new_v > 15: new_v = 1
            self.config["seek_length"] = new_v
            self._is_dirty = True
        except TypeError:
            self.config["focus_length"] = 5  # note: original was setting seek_length but fallback is same
            self.config["seek_length"] = 5
            self._is_dirty = True

    def next_volume(self):
        try:
            curr = self.config.get("volume", 100)
            # Find nearest 10% step
            idx = 0
            for i, v in enumerate(self.available_volumes):
                if v >= curr:
                    idx = i
                    break
            idx = (idx + 1) % len(self.available_volumes)
            self.config["volume"] = self.available_volumes[idx]
            self._is_dirty = True
        except (ValueError, TypeError, IndexError):
            self.config["volume"] = 100
            self._is_dirty = True

    def load(self):
        try:
            data = self.storage.read("picoware/vibesmp/settings.json")
            if data:
                saved = json.loads(data)
                del data
                from gc import collect
                collect()
                self.config.update(saved)
        except (OSError, ValueError) as e:
            import sys
            print("[ERROR] load_settings:", e)
            sys.print_exception(e)
        self.discover_languages()

    def discover_languages(self):
        self.available_langs = []
        paths = ["picoware/vibesmp/lang/", "picoware/apps/vibesmp_lib/lang/", "vibesmp_lib/lang/"]
        for p in paths:
            try:
                check_path = p[:-1] if p.endswith("/") else p
                if hasattr(self.storage, "exists") and not self.storage.exists(check_path):
                    continue
                files = self.storage.listdir(check_path)
                for f in files:
                    if f.endswith(".json"):
                        lang = f[:-5]
                        if lang not in self.available_langs:
                            self.available_langs.append(lang)
            except OSError:
                continue

        if not self.available_langs:
            self.available_langs = ["en"]
        if "en" not in self.available_langs:
            self.available_langs.append("en")
        self.available_langs.sort()

    def next_lang(self):
        if not self.available_langs:
            self.available_langs = ["en"]
            self.config["language"] = "en"
            self._is_dirty = True
            return
        try:
            curr = self.config.get("language", self.available_langs[0])
            if curr not in self.available_langs:
                idx = 0
            else:
                idx = self.available_langs.index(curr)
                idx = (idx + 1) % len(self.available_langs)
            self.config["language"] = self.available_langs[idx]
            self._is_dirty = True
        except (ValueError, IndexError):
            self.config["language"] = self.available_langs[0]
            self._is_dirty = True

    def next_theme(self):
        # THEMES is provided by consolidated core
        t_keys = list(THEMES.keys())
        if not t_keys:
            self.config["theme"] = "dark"
            self._is_dirty = True
            return
        try:
            curr = self.config.get("theme", "dark").lower().replace(" ", "_")
            if curr not in t_keys:
                idx = 0
            else:
                idx = t_keys.index(curr)
                idx = (idx + 1) % len(t_keys)
            self.config["theme"] = t_keys[idx]
            self._is_dirty = True
        except (ValueError, IndexError):
            self.config["theme"] = "dark"
            self._is_dirty = True

    def save(self, force=False, storage_manager=None):
        if not self._is_dirty and not force: return
        try:
            data = json.dumps(self.config)
            if storage_manager:
                def _mark_saved():
                    self._save_pending = False

                def _mark_failed():
                    self._save_pending = False
                    self._is_dirty = True

                storage_manager.request_write(
                    "picoware/vibesmp/settings.json",
                    data,
                    on_success=_mark_saved,
                    on_error=_mark_failed,
                )
                self._save_pending = True
                self._is_dirty = False
            else:
                if self.storage.write("picoware/vibesmp/settings.json", data, "w"):
                    self._save_pending = False
                    self._is_dirty = False
                else:
                    self._save_pending = False
                    self._is_dirty = True
        except OSError as e:
            import sys
            print("[ERROR] save_settings:", e)
            sys.print_exception(e)
            self._save_pending = False
            self._is_dirty = True

    def toggle(self, key):
        if key in self.config:
            self.config[key] = not self.config[key]
            self._is_dirty = True

    def set(self, key, value):
        if key in self.config:
            if self.config[key] != value:
                self.config[key] = value
                self._is_dirty = True
        else:
            self.config[key] = value
            self._is_dirty = True


# ---- playlist.py ----

import random
import json

class Playlist:
    def __init__(self, storage=None, filename="default.json"):
        self.storage = storage
        self.filename = filename
        self.tracks = []
        self._current_index = 0
        self.base_dir = "picoware/vibesmp/playlists/"
        self.editor_playlist_idx = 0
        self.editor_library_idx = 0   # Cursor in the library pane of the editor
        self.active_pane = 0          # 0 = library pane, 1 = playlist pane
        self._is_dirty = False # Structural dirty (tracks added/removed)
        self._index_dirty = False # Volatile dirty (index changed)
        self._save_pending = False

    @property
    def current_index(self):
        return self._current_index

    @current_index.setter
    def current_index(self, value):
        if self._current_index != value:
            self._current_index = value
            self._index_dirty = True

    def __del__(self):
        self.tracks = []
        self.storage = None

    def add_track(self, file_path):
        if file_path:
            self.tracks.append(file_path)
            self._is_dirty = True

    def remove_track(self, index):
        if 0 <= index < len(self.tracks):
            del self.tracks[index]
            if index < self.current_index:
                self.current_index -= 1
            if len(self.tracks) == 0:
                self.current_index = 0
            elif self.current_index >= len(self.tracks):
                self.current_index = len(self.tracks) - 1
            self._is_dirty = True

    def clear(self):
        if self.tracks or self.current_index != 0:
            self.tracks = []
            self.current_index = 0
            self.editor_playlist_idx = 0
            self._is_dirty = True

    def move_track(self, from_idx, to_idx):
        if 0 <= from_idx < len(self.tracks) and 0 <= to_idx < len(self.tracks):
            curr_track = self.get_current()
            track = self.tracks.pop(from_idx)
            self.tracks.insert(to_idx, track)
            self._is_dirty = True

            # Update current_index if it was moved
            if curr_track:
                for i, t in enumerate(self.tracks):
                    if t == curr_track:
                        self.current_index = i
                        break
            return True
        return False

    def next_track(self, loop_mode, shuffle=False, auto_advance=False):
        if not self.tracks:
            return None

        if loop_mode == 1 and auto_advance:  # Loop One
            return self.tracks[self.current_index]

        if shuffle:
            self.current_index = random.randint(0, len(self.tracks) - 1)
        else:
            if self.current_index + 1 >= len(self.tracks):
                if loop_mode == 2:  # Loop All
                    self.current_index = 0
                else:
                    # No loop: stay on last track but return None to stop auto-advance
                    if auto_advance:
                        return None
                    else:
                        # Manual 'next' on last track: stop.
                        return None
            else:
                self.current_index += 1

        return self.tracks[self.current_index]

    def prev_track(self):
        if not self.tracks:
            return None
        self.current_index -= 1
        if self.current_index < 0:
            self.current_index = len(self.tracks) - 1
        return self.tracks[self.current_index]

    def get_current(self):
        if not self.tracks or self.current_index < 0 or self.current_index >= len(self.tracks):
            return None
        return self.tracks[self.current_index]

    def save_as(self, filename, storage_manager=None):
        """Save current tracks to a new playlist file."""
        if not filename: return
        self.filename = filename
        self._is_dirty = True
        self.save(force=True, storage_manager=storage_manager)

    def save(self, force=False, storage_manager=None):
        if not self.storage: return
        if not self._is_dirty and not force: return
        from gc import collect
        collect()
        try:
            # Ensure filename doesn't repeat base_dir
            fname = self.filename
            if fname.startswith(self.base_dir):
                fname = fname[len(self.base_dir):]

            full_path = self.base_dir + fname
            state = {
                "tracks": self.tracks,
                "current_index": self.current_index
            }
            data = json.dumps(state)
            if storage_manager:
                def _mark_saved():
                    self._save_pending = False

                def _mark_failed():
                    self._save_pending = False
                    self._is_dirty = True

                storage_manager.request_write(
                    full_path,
                    data,
                    on_success=_mark_saved,
                    on_error=_mark_failed,
                )
                self._save_pending = True
                self._is_dirty = False
            else:
                if self.storage.write(full_path, data, "w"):
                    self._save_pending = False
                    self._is_dirty = False
                else:
                    self._save_pending = False
                    self._is_dirty = True
            del data
            collect()
        except OSError as e:
            import sys
            print("[ERROR] playlist.save OSError:", e)
            sys.print_exception(e)
            self._save_pending = False
            self._is_dirty = True
        except (ValueError, TypeError) as e:
            import sys
            print("[ERROR] playlist.save unexpected:", e)
            sys.print_exception(e)
            self._save_pending = False
            self._is_dirty = True

    def load(self, filename=None, storage_manager=None):
        if self._is_dirty: self.save(storage_manager=storage_manager)

        if filename:
            self.filename = filename
        if not self.storage: return

        from gc import collect
        collect()

        fname = self.filename
        if fname.startswith(self.base_dir):
            fname = fname[len(self.base_dir):]

        path = self.base_dir + fname
        try:
            data = self.storage.read(path)
            if data:
                parsed = json.loads(data)
                if isinstance(parsed, dict):
                    self.tracks = parsed.get("tracks", [])
                    self._current_index = parsed.get("current_index", 0)
                elif isinstance(parsed, list):
                    self.tracks = parsed
                    self._current_index = 0

                # Bounds check
                if self.current_index >= len(self.tracks):
                    self.current_index = 0

            self._is_dirty = False
            del data
            collect()
        except (OSError, ValueError) as e:
            import sys
            print(f"[ERROR] Playlist: Load failed {path}: {e}")
            sys.print_exception(e)
            self.tracks = []
            self.current_index = 0


# ---- scanner.py ----

def _perf_set(library, name, value):
    counters = getattr(library, "perf_counters", None)
    if counters is not None:
        counters[name] = value

def scan(library, path=None, loading=None, progress_callback=None, quick=False, remove_missing=False):
    from gc import collect
    import time
    collect()
    start = time.ticks_ms()
    scan_path = ""
    print(f"[DEBUG] library: scanning SD root")
    old_tracks = [library._normalize_track_path(p) for p in getattr(library, "tracks", [])]
    old_set = set(old_tracks)
    found = []
    added = []
    if not quick:
        library.tracks = []
    library._tree_structure = None
    library._flat_tree_cache = None
    library._count = 0
    library._scan_dirs = 0
    library._scan_last_path = scan_path
    library._scan_progress_force = False

    try:
        _recursive_scan(library, scan_path, loading, progress_callback, found, old_set, added, quick)
        if quick:
            library.tracks = old_tracks + added
        elif remove_missing:
            library.tracks = found
        if progress_callback:
            library._scan_progress_force = True
            try:
                progress_callback(getattr(library, "_scan_last_path", scan_path), library._count)
            finally:
                library._scan_progress_force = False
        library.save()
        if hasattr(library, "_sync_state_with_tracks"):
            library._sync_state_with_tracks(save=True)
        deferred = 0
        if hasattr(library, "queue_metadata_for_tracks"):
            deferred = library.queue_metadata_for_tracks(library.tracks)
        found_set = set(found)
        removed = len([p for p in old_tracks if p not in found_set])
        if remove_missing:
            before = len(library.tracks)
            library.tracks = [p for p in library.tracks if p in found_set]
            if quick:
                removed = before - len(library.tracks)
        new_tracks = len([p for p in library.tracks if p not in old_set])
        unchanged = len([p for p in library.tracks if p in old_set])
        library.last_scan_summary = {
            "total": len(library.tracks),
            "found": len(found),
            "added": new_tracks,
            "removed": removed,
            "unchanged": unchanged,
            "failed": 0,
        }
        _perf_set(library, "scan_ms", time.ticks_diff(time.ticks_ms(), start))
        _perf_set(library, "scan_tracks", len(library.tracks))
        _perf_set(library, "scan_dirs", getattr(library, "_scan_dirs", 0))
        _perf_set(library, "scan_metadata_deferred", deferred)
        print(f"[DEBUG] library: found {len(library.tracks)} tracks, {new_tracks} new, {removed} removed")
        return new_tracks if new_tracks > 0 else 0
    except OSError as e:
        print(f"[ERROR] library.scan fail:", e)
        library.last_scan_summary = {
            "total": len(library.tracks),
            "found": 0,
            "added": 0,
            "removed": 0,
            "unchanged": 0,
            "failed": 1,
        }
        return 0

def _recursive_scan(library, start_path, loading=None, progress_callback=None, found=None, old_set=None, added=None, quick=False):
    from gc import collect
    stack = [start_path]
    skip_dirs = ("__pycache__", ".git", "System Volume Information", "picoware/apps/vibesmp_lib")

    while stack:
        path = stack.pop()
        library._scan_dirs += 1
        library._scan_last_path = path
        if progress_callback: progress_callback(path, library._count)
        try:
            entries = library.storage.read_directory(path)
            if not entries:
                continue

            for entry in entries:
                if loading: loading.animate()
                item = entry.get("filename")
                if not item or item.startswith(".") or item in skip_dirs:
                    continue

                if not path:
                    full_path = item
                else:
                    full_path = path.rstrip("/") + "/" + item

                if entry.get("is_directory"):
                    if full_path not in skip_dirs:
                        stack.append(full_path)
                elif item.lower().endswith(".mp3"):
                    library._count += 1
                    library._scan_last_path = full_path
                    if progress_callback: progress_callback(full_path, library._count)

                    save_path = "/sd/" + full_path
                    if found is not None:
                        found.append(save_path)
                    if quick:
                        if save_path not in old_set:
                            added.append(save_path)
                    else:
                        library.tracks.append(save_path)

                    if library._count % 50 == 0: collect()
        except OSError: pass
        except ValueError as e:
            print(f"[ERROR] library.scan unexpected {path}:", e)


# ---- id3.py ----

import time
_id3_cache = {}
_perf_counters = None


def set_perf_counters(counters):
    global _perf_counters
    _perf_counters = counters


def _perf_inc(name):
    if _perf_counters is not None:
        _perf_counters[name] = _perf_counters.get(name, 0) + 1

def clear_cache():
    global _id3_cache
    _id3_cache.clear()


def _extract_cover_chunked(storage, file_obj, img_offset, img_size, cover_path):
    chunk_size = 2048
    mounted_vfs = False
    temp_rel = cover_path + ".tmp"
    temp_vfs = None
    try:
        if cover_path.startswith("/sd/"):
            cover_path = cover_path[4:]
        elif cover_path.startswith("sd/"):
            cover_path = cover_path[3:]
        cover_path = cover_path.lstrip("/")
        temp_rel = cover_path + ".tmp"
        temp_vfs = storage.vfs_prefix.rstrip("/") + "/" + temp_rel.lstrip("/")

        if not storage.vfs_mounted:
            mounted_vfs = storage.mount_vfs()

        with open(temp_vfs, "wb") as out:
            remaining = img_size
            offset = img_offset
            while remaining > 0:
                chunk = storage.file_read(file_obj, offset, min(chunk_size, remaining), False)
                if not chunk:
                    raise OSError("short APIC read")
                out.write(chunk)
                offset += len(chunk)
                remaining -= len(chunk)

        if storage.exists(cover_path):
            storage.remove(cover_path)
        if not storage.rename(temp_rel, cover_path):
            raise OSError("cover rename failed")
        return True
    except Exception:
        if storage.exists(temp_rel):
            storage.remove(temp_rel)
        raise
    finally:
        if mounted_vfs:
            try:
                storage.unmount_vfs()
            except OSError:
                pass


def parse_id3(storage, file_path, extract_cover=False):
    """
    Optimized ID3 parser for RP2350.
    Uses chunked tag scanning to minimize SD bus lockout.
    """
    if not extract_cover and file_path in _id3_cache:
        return _id3_cache[file_path]

    if len(_id3_cache) > 100:
        _id3_cache.clear()

    sd_path = file_path
    if sd_path.startswith("/sd/"): sd_path = sd_path[4:]
    elif sd_path.startswith("sd/"): sd_path = sd_path[3:]

    # Ensure path starts with / for C driver consistency
    if not sd_path.startswith("/"):
        sd_path = "/" + sd_path

    from gc import collect
    res = {"title": "", "artist": "", "album": "", "year": "", "genre": "", "track": "", "cover": False}

    f = None
    try:
        f = storage.file_open(sd_path)
        if not f: return res

        # 1. Header (Fast check)
        header = storage.file_read(f, 0, 10, False)
        if len(header) == 10 and header[:3] == b"ID3":
            version = header[3]
            tag_size = (header[6] << 21) | (header[7] << 14) | (header[8] << 7) | header[9]

            # Scan entire ID3 tag frame by frame
            pos = 0
            while pos < tag_size - 10:
                # Read frame header (10 bytes for v3/v4, 6 bytes for v2)
                h_sz = 6 if version == 2 else 10
                h = storage.file_read(f, 10 + pos, h_sz, False)
                if len(h) < h_sz or h[0] == 0: break # End of frames or EOF

                fid = ""
                fs = 0
                if version == 2:
                    fid = h[0:3].decode('ascii', 'ignore')
                    fs = (h[3] << 16) | (h[4] << 8) | h[5]
                else:
                    fid = h[0:4].decode('ascii', 'ignore')
                    if version == 3:
                        fs = (h[4] << 24) | (h[5] << 16) | (h[6] << 8) | h[7]
                    else: # v2.4 (Synchsafe)
                        fs = (h[4] << 21) | (h[5] << 14) | (h[6] << 7) | h[7]

                if fs <= 0 or fs > tag_size: break

                norm_id = fid
                if version == 2:
                    if fid == "TT2": norm_id = "TIT2"
                    elif fid == "TP1": norm_id = "TPE1"
                    elif fid == "TAL": norm_id = "TALB"
                    elif fid == "TYE": norm_id = "TYER"
                    elif fid == "TCO": norm_id = "TCON"
                    elif fid == "TRK": norm_id = "TRCK"
                    elif fid == "PIC": norm_id = "APIC"

                text_frames = set(["TIT2", "TPE1", "TALB", "TYER", "TCON", "TRCK"])
                if norm_id in text_frames:
                    data = storage.file_read(f, 10 + pos + h_sz, min(fs, 128), False)
                    if data and len(data) > 1:
                        enc = data[0]
                        raw = data[1:]
                        try:
                            if enc == 1 or enc == 2:
                                val = raw.decode('utf-16', 'ignore').strip('\x00').strip()
                            else:
                                val = raw.decode('latin-1', 'ignore').strip('\x00').strip()
                        except (UnicodeError, LookupError):
                            val = ""
                        if norm_id == "TIT2": res["title"] = val
                        elif norm_id == "TPE1": res["artist"] = val
                        elif norm_id == "TALB": res["album"] = val
                        elif norm_id == "TYER": res["year"] = val
                        elif norm_id == "TCON": res["genre"] = val
                        elif norm_id == "TRCK": res["track"] = val

                elif norm_id == "APIC" and extract_cover:
                    if not res["cover"]:
                        apic_hdr = storage.file_read(f, 10 + pos + h_sz, min(fs, 64), False)
                        if apic_hdr:
                            # Find end of mime type (null terminator)
                            null1 = -1
                            for bi in range(len(apic_hdr)):
                                if apic_hdr[bi] == 0:
                                    null1 = bi
                                    break
                            if null1 >= 0:
                                # Skip: encoding(1) + mime + null(1) + picture_type(1) + description + null(1)
                                null2 = -1
                                for bi in range(null1 + 3, len(apic_hdr)):
                                    if apic_hdr[bi] == 0:
                                        null2 = bi
                                        break
                                if null2 >= 0:
                                    data_offset = null2 + 1
                                    img_offset = 10 + pos + h_sz + data_offset
                                    img_size = fs - data_offset
                                    if img_size > 0 and isinstance(extract_cover, str):
                                        _perf_inc("cover_extract_attempts")
                                        cover_path = extract_cover
                                        try:
                                            if _extract_cover_chunked(storage, f, img_offset, img_size, cover_path):
                                                res["cover"] = extract_cover
                                                _perf_inc("cover_extract_success")
                                                collect()
                                        except Exception as e:
                                            print("[ERROR] parse_id3 cover extract:", e)
                                            _perf_inc("cover_extract_fail")

                pos += h_sz + fs

    except OSError as e:
        print("[ERROR] parse_id3:", e)
    finally:
        if f:
            try: storage.file_close(f)
            except OSError: pass

    if not extract_cover:
        _id3_cache[file_path] = res
    return res


# ---- metadata_engine.py ----

import json
import binascii
from gc import collect

_cover_decoder = None
_cover_decoder_size = None
_perf_counters = None


def set_perf_counters(counters):
    global _perf_counters
    _perf_counters = counters


def _perf_inc(name):
    if _perf_counters is not None:
        _perf_counters[name] = _perf_counters.get(name, 0) + 1

def get_track_hash(path):
    """Generate a consistent 8-char hex hash for a track path."""
    if isinstance(path, str):
        path = path.encode()
    return str(binascii.crc32(path) & 0xFFFFFFFF)

def get_meta_paths(library, path):
    """Return (meta_json_path, cover_jpg_path) for a track."""
    h = get_track_hash(path)
    return library.meta_dir + h + ".json", library.cover_dir + h + ".jpg"

def get_cached_title(storage, library, path):
    """Return ID3 title for path from cached meta JSON, or empty string."""
    try:
        meta_path, _ = get_meta_paths(library, path)
        n = meta_path
        if n.startswith("/sd/"): n = n[4:]
        elif n.startswith("sd/"): n = n[3:]
        if not storage.exists(n): return ""
        data = json.loads(storage.read(n))
        return data.get("title", "") or ""
    except (OSError, ValueError):
        return ""

def draw_cover(draw, cover_path, x, y, size=68):
    """Memory-efficient cover drawing with automatic scaling and zero persistence."""
    if not cover_path: return False

    # Normalize path for VFS
    sd_path = cover_path
    if sd_path.startswith("/sd/"): sd_path = sd_path[4:]
    elif sd_path.startswith("sd/"): sd_path = sd_path[3:]
    sd_path = sd_path.lstrip("/")

    try:
        from picoware.gui.jpeg import JPEG
        global _cover_decoder, _cover_decoder_size

        _perf_inc("cover_draw_attempts")
        res = False

        try:
            if _cover_decoder is None or _cover_decoder_size != size:
                _cover_decoder = JPEG(screen_width=size, screen_height=size)
                _cover_decoder_size = size
            res = _cover_decoder.draw(x, y, sd_path)
        except (ValueError, OSError, AttributeError) as e:
            print(f"[ERROR] draw_cover shared decoder exception: {e}")
            _cover_decoder = None
            _cover_decoder_size = None

        if not res:
            _perf_inc("cover_decoder_fallbacks")
            decoder = JPEG(screen_width=size, screen_height=size)
            try:
                res = decoder.draw(x, y, sd_path)
            finally:
                del decoder

        if res:
            _perf_inc("cover_draw_success")
        else:
            _perf_inc("cover_draw_fail")
        return res

    except (ImportError, ValueError, OSError) as e:
        print(f"[ERROR] draw_cover native exception: {e}")
        _perf_inc("cover_draw_fail")
        from gc import collect
        collect()
        return False

def cleanup_engine():
    global _cover_decoder, _cover_decoder_size
    _cover_decoder = None
    _cover_decoder_size = None
    from gc import collect
    collect()

def extract_metadata(storage, path, library):
    """Extract and save metadata/cover for a new track."""
    meta_path, cover_path = get_meta_paths(library, path)

    # Normalize paths for Storage API (no /sd/)
    n_meta = meta_path
    if n_meta.startswith("/sd/"): n_meta = n_meta[4:]
    elif n_meta.startswith("sd/"): n_meta = n_meta[3:]

    n_path = path
    if n_path.startswith("/sd/"): n_path = n_path[4:]
    elif n_path.startswith("sd/"): n_path = n_path[3:]

    # If meta exists, check if it has valid cover info.
    if storage.exists(n_meta):
        try:
            data = json.loads(storage.read(n_meta))
            # If we have a cover, verify the file still exists
            c_path = data.get("cover")
            if c_path:
                nc_path = c_path
                if nc_path.startswith("/sd/"): nc_path = nc_path[4:]
                elif nc_path.startswith("sd/"): nc_path = nc_path[3:]

                if storage.exists(nc_path):
                    return True
            else:
                # No cover info, but maybe the scanner previously failed.
                # If it's not an MP3, we don't expect a cover anyway.
                if not n_path.lower().endswith(".mp3"):
                    return True
        except (OSError, ValueError): pass

    try:
        from vibesmp_lib.id3 import parse_id3
        # ID3 parser handles its own /sd/ normalization for storage
        id3_data = parse_id3(storage, n_path, extract_cover=cover_path)
        if id3_data["title"] or id3_data["artist"] or id3_data["album"] or id3_data["cover"]:
            storage.write(n_meta, json.dumps(id3_data), "w")
        del id3_data; collect()
        return True
    except (OSError, ValueError) as e:
        print(f"[ERROR] extract_metadata {n_path}: {e}")
        return False


# ---- vibes_library.py ----

import json

DEBUG_LIBRARY = False

class Library:
    def __init__(self, storage):
        self.storage = storage
        self.db_path = "picoware/vibesmp/library/database.json"
        self.state_path = "picoware/vibesmp/library/state.json"
        self.meta_dir = "picoware/vibesmp/library/meta/"
        self.cover_dir = "picoware/vibesmp/library/covers/"
        if DEBUG_LIBRARY:
            print(f"[DEBUG] Library: Init. Paths: meta={self.meta_dir} cover={self.cover_dir}")
        self.tracks = []
        self.favorites = set()
        self.added_order = {}
        self.next_added_id = 1
        self.expanded_paths = set(["/sd/"]) # Root expanded by default
        self._tree_structure = None # Internal structure
        self._flat_tree_cache = None # Final list of tuples
        self._title_cache = {} # path -> ID3 title string
        self._meta_cache = {} # path -> parsed metadata dict
        self._category_cache = {}
        self._child_cache = {}
        self._track_info_cache = {}
        self._display_cache_version = 0
        self._count = 0
        self.perf_counters = None
        self._metadata_queue = []
        self._metadata_queue_idx = 0
        self.last_search = ""
        self.last_scan_summary = {
            "total": 0,
            "found": 0,
            "added": 0,
            "removed": 0,
            "unchanged": 0,
            "failed": 0,
        }
        mkdir_p(self.storage, self.meta_dir)
        mkdir_p(self.storage, self.cover_dir)
        self.load()
        self.load_state()

    def __del__(self):
        self.tracks = []
        self._tree_structure = None
        self._flat_tree_cache = None
        self._title_cache = {}
        self._meta_cache = {}
        self._category_cache = {}
        self._child_cache = {}
        self._track_info_cache = {}
        self._metadata_queue = []
        self.storage = None

    def set_perf_counters(self, counters):
        self.perf_counters = counters

    def _perf_inc(self, name):
        if self.perf_counters is not None:
            self.perf_counters[name] = self.perf_counters.get(name, 0) + 1

    def _perf_timing(self, prefix, elapsed):
        counters = self.perf_counters
        if counters is None:
            return
        count_key = prefix + "_count"
        total_key = prefix + "_total_ms"
        max_key = prefix + "_max_ms"
        counters[count_key] = counters.get(count_key, 0) + 1
        counters[total_key] = counters.get(total_key, 0) + elapsed
        if elapsed > counters.get(max_key, 0):
            counters[max_key] = elapsed

    def _invalidate_display_cache(self):
        self._category_cache = {}
        self._child_cache = {}
        self._track_info_cache = {}
        self._display_cache_version += 1

    def _metadata_affects_display(self, md):
        if not isinstance(md, dict):
            return False
        for key in ("title", "artist", "album", "genre", "year", "track", "cover"):
            if md.get(key):
                return True
        return False

    def _normalize_track_path(self, path):
        if not path:
            return ""
        return path if path.startswith("/sd/") else ("/sd/" + path.lstrip("/"))

    def _filename_title(self, path):
        name = path.rsplit("/", 1)[-1]
        if name.lower().endswith(".mp3"):
            name = name[:-4]
        return name

    def _path_parts(self, path):
        path = self._normalize_track_path(path)
        parts = [p for p in path.split("/") if p and p != "sd"]
        return parts

    def _path_fallback_meta(self, path):
        parts = self._path_parts(path)
        title = self._filename_title(path)
        album = ""
        artist = ""
        if len(parts) >= 2:
            album = parts[-2]
        if len(parts) >= 3:
            artist = parts[-3]
        return title, artist, album

    def load_state(self):
        """Load persistent browser state without requiring a database migration."""
        try:
            if self.storage.exists(self.state_path):
                data = self.storage.read(self.state_path)
                if data:
                    state = json.loads(data)
                    fav = state.get("favorites", [])
                    self.favorites = set([self._normalize_track_path(p) for p in fav if p])
                    self.added_order = state.get("added_order", {}) or {}
                    self.next_added_id = int(state.get("next_added_id", 1) or 1)
            self._sync_state_with_tracks(save=False)
        except (OSError, ValueError, TypeError) as e:
            print("[ERROR] library.load_state:", e)
            self.favorites = set()
            self.added_order = {}
            self.next_added_id = 1
            self._sync_state_with_tracks(save=False)

    def save_state(self):
        try:
            parts = self.state_path.split("/")
            base_dir = "/".join(parts[:-1]) + "/"
            mkdir_p(self.storage, base_dir)
            data = json.dumps({
                "favorites": list(self.favorites),
                "added_order": self.added_order,
                "next_added_id": self.next_added_id,
            })
            self.storage.write(self.state_path, data, "w")
            del data
        except (OSError, ValueError, TypeError) as e:
            print("[ERROR] library.save_state:", e)

    def _sync_state_with_tracks(self, save=True):
        """Assign first-seen order to tracks and drop stale favorite/order entries."""
        seen = set()
        changed = False
        for track in self.tracks:
            path = self._normalize_track_path(track)
            seen.add(path)
            if path not in self.added_order:
                self.added_order[path] = self.next_added_id
                self.next_added_id += 1
                changed = True

        for path in list(self.added_order.keys()):
            if path not in seen:
                del self.added_order[path]
                changed = True
        for path in list(self.favorites):
            if path not in seen:
                self.favorites.remove(path)
                changed = True

        if changed and save:
            self.save_state()

    def load(self):
        from gc import collect
        collect()
        try:
            if not self.storage.exists(self.db_path): return
            data = self.storage.read(self.db_path)
            if data:
                self.tracks = json.loads(data)
            del data
            self._tree_structure = None
            self._flat_tree_cache = None
            self._title_cache = {}
            self._meta_cache = {}
            self._invalidate_display_cache()
            self.expanded_paths = set(["/sd/"]) # Reset expansion state
            collect()
        except (OSError, ValueError) as e:
            print("[ERROR] library.load OSError/ValueError:", e)
            self.tracks = []
        except TypeError as e:
            print("[ERROR] library.load unexpected:", e)
            self.tracks = []

    def save(self):
        from gc import collect
        collect()
        try:
            parts = self.db_path.split("/")
            base_dir = "/".join(parts[:-1]) + "/"
            mkdir_p(self.storage, base_dir)

            data = json.dumps(self.tracks)
            self.storage.write(self.db_path, data, "w")
            del data
            collect()
        except OSError as e:
            print("[ERROR] library.save OSError:", e)
        except ValueError as e:
            print("[ERROR] library.save unexpected:", e)

    def scan(self, path=None, loading=None, progress_callback=None, quick=False, remove_missing=False, summary=False):
        import vibesmp_lib.scanner as scanner
        res = scanner.scan(
            self,
            path,
            loading,
            progress_callback=progress_callback,
            quick=quick,
            remove_missing=remove_missing,
        )
        self._title_cache = {}
        self._meta_cache = {}
        self._sync_state_with_tracks(save=True)
        self._invalidate_display_cache()
        import sys
        if "vibesmp_lib.scanner" in sys.modules:
            del sys.modules["vibesmp_lib.scanner"]
        from gc import collect
        collect()
        if summary:
            return self.last_scan_summary
        return res

    def get_title(self, path):
        """Return ID3 title for a track path, with caching. Falls back to empty string."""
        if path in self._title_cache:
            return self._title_cache[path]
        title = ""
        try:
            from vibesmp_lib.metadata_engine import get_cached_title
            title = get_cached_title(self.storage, self, path)
        except (ImportError, OSError, ValueError):
            pass
        self._title_cache[path] = title
        return title

    @property
    def display_cache_version(self):
        return self._display_cache_version

    def get_track_display(self, path, allow_io=True):
        """Return (title, artist) for a track path using cached metadata."""
        path = self._normalize_track_path(path)
        if path in self._meta_cache:
            md = self._meta_cache[path]
        else:
            md = {}
            if allow_io:
                md = self.load_track_metadata(path)

        title = ""
        artist = ""
        if isinstance(md, dict):
            title = md.get("title", "") or ""
            artist = md.get("artist", "") or ""
        if not title:
            title = path.rsplit("/", 1)[-1]
            if title.lower().endswith(".mp3"):
                title = title[:-4]
        return title, artist

    def _get_meta(self, path, allow_io=True):
        path = self._normalize_track_path(path)
        if path in self._meta_cache:
            return self._meta_cache[path]
        md = {}
        if allow_io:
            md = self.load_track_metadata(path)
        return md

    def load_track_metadata(self, path):
        """Load cached metadata for one track from SD and update display caches."""
        path = self._normalize_track_path(path)
        if path in self._meta_cache:
            return self._meta_cache[path]
        md = {}
        try:
            from vibesmp_lib.metadata_engine import get_meta_paths
            meta_path, _ = get_meta_paths(self, path)
            n = meta_path
            if n.startswith("/sd/"):
                n = n[4:]
            elif n.startswith("sd/"):
                n = n[3:]
            if self.storage.exists(n):
                data = self.storage.read(n)
                if data:
                    md = json.loads(data)
        except (ImportError, OSError, ValueError, TypeError):
            md = {}
        self._meta_cache[path] = md
        if self._metadata_affects_display(md):
            self._invalidate_display_cache()
            self._perf_inc("library_metadata_display_invalidate")
        else:
            self._perf_inc("library_metadata_empty_cached")
        return md

    def has_track_metadata(self, path):
        return self._normalize_track_path(path) in self._meta_cache

    def _metadata_file_exists(self, path):
        try:
            from vibesmp_lib.metadata_engine import get_meta_paths
            meta_path, _ = get_meta_paths(self, self._normalize_track_path(path))
            if meta_path.startswith("/sd/"):
                meta_path = meta_path[4:]
            elif meta_path.startswith("sd/"):
                meta_path = meta_path[3:]
            return self.storage.exists(meta_path)
        except (ImportError, OSError, ValueError, TypeError):
            return False

    def queue_metadata_for_tracks(self, tracks=None):
        queue = []
        source = tracks if tracks is not None else self.tracks
        for path in source:
            n_path = self._normalize_track_path(path)
            if n_path and not self._metadata_file_exists(n_path):
                queue.append(n_path)
        self._metadata_queue = queue
        self._metadata_queue_idx = 0
        return len(queue)

    def metadata_queue_pending(self):
        return max(0, len(self._metadata_queue) - self._metadata_queue_idx)

    def extract_next_metadata(self):
        import time
        while self._metadata_queue_idx < len(self._metadata_queue):
            path = self._metadata_queue[self._metadata_queue_idx]
            self._metadata_queue_idx += 1
            if self._metadata_file_exists(path):
                self.load_track_metadata(path)
                self._perf_inc("metadata_idle_cached")
                return True
            start = time.ticks_ms() if self.perf_counters is not None else 0
            try:
                from vibesmp_lib.metadata_engine import extract_metadata
                ok = extract_metadata(self.storage, path, self)
                if start:
                    self._perf_timing("metadata_idle_extract", time.ticks_diff(time.ticks_ms(), start))
                self._perf_inc("metadata_idle_extract_ok" if ok else "metadata_idle_extract_fail")
                if path in self._meta_cache:
                    del self._meta_cache[path]
                self.load_track_metadata(path)
                return True
            except (ImportError, OSError, ValueError, TypeError) as e:
                print("[ERROR] library.extract_next_metadata:", e)
                self._perf_inc("metadata_idle_extract_fail")
                return False
        self._metadata_queue = []
        self._metadata_queue_idx = 0
        return False

    def get_track_info(self, path, allow_io=True):
        """Return normalized display metadata for one track."""
        path = self._normalize_track_path(path)
        if not allow_io:
            cached = self._track_info_cache.get(path)
            if cached is not None:
                self._perf_inc("library_track_info_cache_hit")
                return cached
        md = self._get_meta(path, allow_io=allow_io)
        if not isinstance(md, dict):
            md = {}
        f_title, f_artist, f_album = self._path_fallback_meta(path)
        title = md.get("title", "") or f_title
        artist = md.get("artist", "") or f_artist or "Unknown Artist"
        album = md.get("album", "") or f_album or "Unknown Album"
        genre = md.get("genre", "") or "Unknown Genre"
        info = {
            "kind": "track",
            "path": path,
            "label": title,
            "title": title,
            "artist": artist,
            "album": album,
            "genre": genre,
            "year": md.get("year", "") or "",
            "track": md.get("track", "") or "",
            "cover": md.get("cover", False),
            "favorite": path in self.favorites,
        }
        if not allow_io:
            self._track_info_cache[path] = info
            self._perf_inc("library_track_info_cache_miss")
        return info

    def get_categories(self):
        return [
            ("all_songs", "All Songs"),
            ("artists", "Artists"),
            ("albums", "Albums"),
            ("folders", "Folders"),
            ("genres", "Genres"),
            ("recently_added", "Recently Added"),
            ("favorites", "Favorites"),
            ("search", "Search"),
            ("scan_options", "Scan Options"),
            ("sort", "Sort"),
            ("filters", "Filters"),
            ("stats", "Library Stats"),
            ("cleanup", "Cleanup"),
            ("scan", "Scan Library"),
        ]

    def get_sort_modes(self):
        return [
            ("title", "Title"),
            ("artist", "Artist"),
            ("album", "Album"),
            ("recent", "Recently Added"),
            ("folder", "Folder Order"),
        ]

    def _sort_track_items(self, items, sort_mode):
        if sort_mode == "recent":
            items.sort(key=lambda x: self.added_order.get(x["path"], 0), reverse=True)
        elif sort_mode == "artist":
            items.sort(key=lambda x: (x.get("artist", "").lower(), x.get("album", "").lower(), x.get("title", "").lower()))
        elif sort_mode == "album":
            items.sort(key=lambda x: (x.get("album", "").lower(), x.get("track", ""), x.get("title", "").lower()))
        elif sort_mode == "folder":
            items.sort(key=lambda x: x.get("path", "").lower())
        else:
            items.sort(key=lambda x: (x.get("title", "").lower(), x.get("artist", "").lower()))

    def _track_entries(self, tracks, query=None, sort_mode=None, allow_io=False):
        q = query.lower() if query else ""
        items = []
        for path in tracks:
            info = self.get_track_info(path, allow_io=allow_io)
            if q:
                hay = (
                    info["title"] + " " + info["artist"] + " " +
                    info["album"] + " " + info["genre"] + " " + path
                ).lower()
                if q not in hay:
                    continue
            items.append(info)

        self._sort_track_items(items, sort_mode)
        return items

    def _bucket_entries(self, field, category, unknown_label, allow_io=False):
        buckets = {}
        for path in self.tracks:
            info = self.get_track_info(path, allow_io=allow_io)
            key = info.get(field, "") or unknown_label
            if key not in buckets:
                buckets[key] = []
            buckets[key].append(info["path"])
        items = []
        for key in sorted(buckets.keys(), key=lambda x: x.lower()):
            items.append({
                "kind": "bucket",
                "category": category,
                "key": key,
                "label": key,
                "count": len(buckets[key]),
                "tracks": buckets[key],
            })
        return items

    def get_category_items(self, category, query=None, sort_mode=None):
        key = (
            self._display_cache_version,
            category,
            query or "",
            sort_mode or "",
            len(self.tracks),
        )
        cached = self._category_cache.get(key)
        if cached is not None:
            self._perf_inc("library_category_cache_hit")
            return cached
        self._perf_inc("library_category_cache_miss")

        if category == "all_songs":
            items = self._track_entries(self.tracks, query=query, sort_mode=sort_mode, allow_io=False)
        elif category == "recently_added":
            items = self._track_entries(self.tracks, query=query, sort_mode="recent", allow_io=False)
        elif category == "favorites":
            tracks = [p for p in self.tracks if self._normalize_track_path(p) in self.favorites]
            items = self._track_entries(tracks, query=query, sort_mode=sort_mode, allow_io=False)
        elif category == "search":
            items = self._track_entries(self.tracks, query=query, sort_mode=sort_mode, allow_io=False)
        elif category == "filters":
            items = [
                {"kind": "category_filter", "filter": "favorites", "label": "Favorites Only"},
                {"kind": "category_filter", "filter": "unknown_artist", "label": "Unknown Artist"},
                {"kind": "category_filter", "filter": "missing_metadata", "label": "Missing Metadata"},
                {"kind": "category_filter", "filter": "duplicates", "label": "Duplicates"},
                {"kind": "category_filter", "filter": "broken_files", "label": "Missing Files"},
            ]
        elif category == "sort":
            items = [
                {"kind": "sort_mode", "sort_mode": mode, "label": label}
                for mode, label in self.get_sort_modes()
            ]
        elif category == "scan_options":
            items = [
                {"kind": "scan_action", "scan_mode": "quick", "label": "Quick Scan New Files"},
                {"kind": "scan_action", "scan_mode": "missing", "label": "Remove Missing Files"},
                {"kind": "scan_action", "scan_mode": "full", "label": "Full Rescan"},
            ]
        elif category == "stats":
            items = self.get_stats_items()
        elif category == "cleanup":
            items = self.get_cleanup_items()
        elif category == "artists":
            items = self._bucket_entries("artist", "artists", "Unknown Artist", allow_io=False)
        elif category == "albums":
            items = self._bucket_entries("album", "albums", "Unknown Album", allow_io=False)
        elif category == "genres":
            items = self._bucket_entries("genre", "genres", "Unknown Genre", allow_io=False)
        elif category == "folders":
            items = []
            for path, depth, is_dir, is_exp, name in self.get_tree_view():
                items.append({
                    "kind": "folder" if is_dir else "track",
                    "path": path,
                    "label": name,
                    "depth": depth,
                    "expanded": is_exp,
                })
        else:
            items = []

        if len(self._category_cache) > 16:
            self._category_cache.clear()
        self._category_cache[key] = items
        return items

    def get_filtered_items(self, filter_name, sort_mode=None):
        if filter_name == "favorites":
            tracks = [p for p in self.tracks if self._normalize_track_path(p) in self.favorites]
            return self._track_entries(tracks, sort_mode=sort_mode, allow_io=False)
        if filter_name == "unknown_artist":
            tracks = []
            for path in self.tracks:
                md = self._get_meta(path, allow_io=False)
                if not isinstance(md, dict) or not md.get("artist"):
                    tracks.append(path)
            return self._track_entries(tracks, sort_mode=sort_mode, allow_io=False)
        if filter_name == "missing_metadata":
            tracks = [p for p in self.tracks if not self._metadata_file_exists(p)]
            return self._track_entries(tracks, sort_mode=sort_mode, allow_io=False)
        if filter_name == "duplicates":
            tracks = []
            for item in self.get_duplicate_items():
                tracks.extend(item.get("tracks", []))
            return self._track_entries(tracks, sort_mode=sort_mode, allow_io=False)
        if filter_name == "broken_files":
            return self._track_entries(self.find_missing_files(), sort_mode=sort_mode, allow_io=False)
        return []

    def tracks_under_folder(self, folder_path):
        folder_path = self._normalize_track_path(folder_path)
        if not folder_path.endswith("/"):
            folder_path += "/"
        return [p for p in self.tracks if self._normalize_track_path(p).startswith(folder_path)]

    def _track_exists(self, path):
        p = self._normalize_track_path(path)
        rel = p[4:] if p.startswith("/sd/") else p
        try:
            return self.storage.exists(rel)
        except OSError:
            return False

    def find_missing_files(self):
        return [p for p in self.tracks if not self._track_exists(p)]

    def remove_tracks(self, tracks):
        remove = set([self._normalize_track_path(p) for p in tracks if p])
        if not remove:
            return 0
        before = len(self.tracks)
        self.tracks = [p for p in self.tracks if self._normalize_track_path(p) not in remove]
        for path in list(self.favorites):
            if path in remove:
                self.favorites.remove(path)
        for path in list(self.added_order.keys()):
            if path in remove:
                del self.added_order[path]
        removed = before - len(self.tracks)
        if removed:
            self.save()
            self.save_state()
            self._tree_structure = None
            self._flat_tree_cache = None
            self._invalidate_display_cache()
        return removed

    def clear_favorites(self):
        count = len(self.favorites)
        self.favorites = set()
        self.save_state()
        self._invalidate_display_cache()
        return count

    def get_duplicate_items(self):
        buckets = {}
        for path in self.tracks:
            info = self.get_track_info(path, allow_io=False)
            key = (
                info.get("title", "").lower(),
                info.get("artist", "").lower(),
            )
            if key not in buckets:
                buckets[key] = []
            buckets[key].append(path)
        items = []
        for key, tracks in buckets.items():
            if len(tracks) > 1:
                label = self.get_track_info(tracks[0], allow_io=False).get("title", "Duplicate")
                items.append({
                    "kind": "collection",
                    "label": label,
                    "tracks": tracks,
                    "count": len(tracks),
                })
        items.sort(key=lambda x: x.get("label", "").lower())
        return items

    def get_cleanup_items(self):
        missing = self.find_missing_files()
        duplicates = self.get_duplicate_items()
        return [
            {"kind": "cleanup_action", "cleanup": "remove_missing", "label": "Remove Missing Files ({})".format(len(missing)), "tracks": missing},
            {"kind": "collection", "label": "Duplicate Tracks ({})".format(len(duplicates)), "tracks": [p for d in duplicates for p in d.get("tracks", [])], "count": len(duplicates)},
            {"kind": "cleanup_action", "cleanup": "clear_favorites", "label": "Clear Favorites ({})".format(len(self.favorites))},
        ]

    def get_stats_items(self):
        artists = set()
        albums = set()
        genres = set()
        for path in self.tracks:
            info = self.get_track_info(path, allow_io=False)
            artists.add(info.get("artist", "Unknown Artist"))
            albums.add(info.get("album", "Unknown Album"))
            genres.add(info.get("genre", "Unknown Genre"))
        missing = len(self.find_missing_files())
        missing_meta = len([p for p in self.tracks if not self._metadata_file_exists(p)])
        summary = self.last_scan_summary or {}
        return [
            {"kind": "info", "label": "Tracks: {}".format(len(self.tracks))},
            {"kind": "info", "label": "Artists: {}".format(len(artists))},
            {"kind": "info", "label": "Albums: {}".format(len(albums))},
            {"kind": "info", "label": "Genres: {}".format(len(genres))},
            {"kind": "info", "label": "Favorites: {}".format(len(self.favorites))},
            {"kind": "info", "label": "Missing files: {}".format(missing)},
            {"kind": "info", "label": "Missing metadata: {}".format(missing_meta)},
            {"kind": "info", "label": "Last scan added: {}".format(summary.get("added", 0))},
            {"kind": "info", "label": "Last scan removed: {}".format(summary.get("removed", 0))},
        ]

    def get_child_items(self, category, item):
        if not item:
            return []
        cache_key = (
            self._display_cache_version,
            category or "",
            item.get("kind", ""),
            item.get("key", ""),
            item.get("label", ""),
            tuple(item.get("tracks", [])),
        )
        cached = self._child_cache.get(cache_key)
        if cached is not None:
            self._perf_inc("library_child_cache_hit")
            return cached
        self._perf_inc("library_child_cache_miss")
        result = []
        if item.get("kind") == "bucket":
            tracks = item.get("tracks", [])
            if category == "artists":
                albums = {}
                for path in tracks:
                    info = self.get_track_info(path, allow_io=False)
                    key = info.get("album", "") or "Unknown Album"
                    if key not in albums:
                        albums[key] = []
                    albums[key].append(path)
                entries = [{
                    "kind": "collection",
                    "label": "All Artist Songs",
                    "tracks": tracks,
                    "count": len(tracks),
                }]
                for album in sorted(albums.keys(), key=lambda x: x.lower()):
                    entries.append({
                        "kind": "collection",
                        "label": album,
                        "tracks": albums[album],
                        "count": len(albums[album]),
                    })
                result = entries
            else:
                label = "All Tracks"
                if category == "albums":
                    label = "All Album Tracks"
                elif category == "genres":
                    label = "All Genre Tracks"
                result = [{
                    "kind": "collection",
                    "label": label,
                    "tracks": tracks,
                    "count": len(tracks),
                }] + self._track_entries(tracks, sort_mode=None, allow_io=False)
        elif item.get("kind") == "collection":
            result = self._track_entries(item.get("tracks", []), sort_mode=None, allow_io=False)
        if len(self._child_cache) > 16:
            self._child_cache.clear()
        self._child_cache[cache_key] = result
        return result

    def toggle_favorite(self, path):
        path = self._normalize_track_path(path)
        if path in self.favorites:
            self.favorites.remove(path)
            fav = False
        else:
            self.favorites.add(path)
            fav = True
        self._invalidate_display_cache()
        self.save_state()
        return fav

    def is_favorite(self, path):
        return self._normalize_track_path(path) in self.favorites

    def toggle_expanded(self, path):
        """Toggle a folder's expanded state."""
        if path in self.expanded_paths:
            self.expanded_paths.remove(path)
            # Recursively collapse all children
            to_remove = [p for p in self.expanded_paths if p.startswith(path)]
            for p in to_remove:
                self.expanded_paths.remove(p)
        else:
            self.expanded_paths.add(path)

        self._flat_tree_cache = None # Invalidate flat view cache
        self._invalidate_display_cache()

    def _build_internal_tree(self):
        """Build a compressed tree using only folders that directly contain MP3 files."""
        from gc import collect
        collect()
        # Root is virtual and hidden in view.
        self._tree_structure = {"folders": {}, "files": [], "path": "/sd/", "name": ""}

        # 1) Gather folders that DIRECTLY contain mp3s, and files per folder.
        files_by_dir = {}
        mp3_dirs = set()
        for track in self.tracks:
            t_path = track if track.startswith("/sd/") else ("/sd/" + track.lstrip("/"))
            slash = t_path.rfind("/")
            if slash < 0:
                continue
            d_path = t_path[:slash + 1]
            fname = t_path[slash + 1:]
            mp3_dirs.add(d_path)
            if d_path not in files_by_dir:
                files_by_dir[d_path] = []
            files_by_dir[d_path].append(fname)

        # 2) Build compressed parent links:
        # parent is nearest ancestor that is also an mp3 folder; skip non-mp3 parents.
        parent_map = {}
        for d_path in mp3_dirs:
            parent = "/sd/"
            search = d_path.rstrip("/")
            while True:
                p = search.rfind("/")
                if p <= 3:  # stop at /sd
                    break
                anc = search[:p + 1]
                if anc in mp3_dirs:
                    parent = anc
                    break
                search = anc.rstrip("/")
            parent_map[d_path] = parent

        # 3) Create nodes and attach to compressed parents.
        nodes = {}
        for d_path in mp3_dirs:
            name = d_path.rstrip("/").split("/")[-1]
            nodes[d_path] = {
                "folders": {},
                "files": files_by_dir.get(d_path, []),
                "path": d_path,
                "name": name
            }

        for d_path, node in nodes.items():
            p_path = parent_map.get(d_path, "/sd/")
            if p_path in nodes:
                nodes[p_path]["folders"][node["name"]] = node
            else:
                self._tree_structure["folders"][node["name"]] = node
        collect()

    def get_tree_view(self, auto_expand=True):
        """Return a list of (path, depth, is_dir, is_expanded, name) for the tree."""
        if self._flat_tree_cache is not None:
            return self._flat_tree_cache

        from gc import collect
        collect()

        if self._tree_structure is None:
            self._build_internal_tree()

        root_node = self._tree_structure
        visible_expanded = set(self.expanded_paths)

        self._flat_tree_cache = []
        # Show only MP3-containing folders as top-level entries (no SD/picoware chain).
        stack = []
        for f_name in sorted(root_node["folders"].keys(), reverse=True):
            stack.append((True, f_name, root_node["folders"][f_name], 0))

        while stack:
            is_folder, name, data, depth = stack.pop()
            if not is_folder:
                self._flat_tree_cache.append((data, depth, False, False, name))
                continue

            node = data
            path = node.get("path")
            is_expanded = path in visible_expanded
            self._flat_tree_cache.append((path, depth, True, is_expanded, name))

            if is_expanded:
                # Maintain alpha order: Files then Folders (pushed in reverse)
                files = sorted(node["files"], reverse=True)
                for f_name in files:
                    full_path = path + f_name
                    display_name = f_name
                    if display_name.lower().endswith(".mp3"):
                        display_name = display_name[:-4]
                    stack.append((False, display_name, full_path, depth + 1))

                f_keys = sorted(node["folders"].keys(), reverse=True)
                for f_name in f_keys:
                    stack.append((True, f_name, node["folders"][f_name], depth + 1))

        collect()
        return self._flat_tree_cache


# ---- loading.py ----

from picoware.system.vector import Vector

class MusicLoader:
    """Branded loading screen with a rotating musical note."""
    def __init__(self, draw, text="", accent_color=None):
        self.draw = draw
        self.angle = 0
        self.center = Vector(draw.size.x // 2, draw.size.y // 2 - 10)
        self.current_text = text
        self.fg_color = getattr(draw, "foreground", 0xFFFF)
        self.bg_color = getattr(draw, "background", 0x0000)
        self.accent_color = accent_color if accent_color is not None else self.fg_color

    def set_text(self, text):
        self.current_text = text

    def animate(self, swap=True):
        self.draw.erase()
        from vibesmp_lib.ui import draw_musical_note
        draw_musical_note(self.draw, self.center, self.angle, self.fg_color, self.accent_color)

        if self.current_text:
            tw = self.draw.len(self.current_text, 0)
            self.draw.text(Vector(self.center.x - tw // 2, self.center.y + 45), self.current_text, self.fg_color, 0)

        if swap:
            self.draw.swap()
        self.angle = (self.angle + 20) % 360

    def stop(self, swap=True):
        self.draw.erase()
        if swap:
            self.draw.swap()


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
    from vibesmp_lib.ui import VIEW_MENU, VIEW_SETTINGS, VIEW_PLAYLIST_SELECTOR, VIEW_NOW_PLAYING
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
    from vibesmp_lib.ui import VIEW_NOW_PLAYING, VIEW_LIBRARY, VIEW_SETTINGS
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
            from vibesmp_lib.core import get_help_text, t
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
    from vibesmp_lib.ui import VIEW_INPUT_MODAL, VIEW_CONFIRM, VIEW_ALERT
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

def render_dialog(app, ui):
    if app.dialog_type == "confirm":
        ui.render_confirm(app.dialog_title, app.dialog_message, app.dialog_selected_idx, app.dialog_scroll_idx)
    elif app.dialog_type == "alert":
        ui.render_modal(app.dialog_title, app.dialog_message, "OK", app.dialog_scroll_idx)
    elif app.dialog_type == "input":
        ui.render_input_dialog(app.dialog_title, app.dialog_buffer, app.dialog_cursor_pos, False)
