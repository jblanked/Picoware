"""
WikiReader - A Wikipedia reader app for Picoware

Allows searching and reading articles from Wikipedia.
"""

import gc
from json import loads, dumps
from time import sleep
from utime import ticks_ms, ticks_diff
from picoware.system.buttons import (
    BUTTON_UP,
    BUTTON_DOWN,
    BUTTON_LEFT,
    BUTTON_RIGHT,
    BUTTON_CENTER,
    BUTTON_BACK,
    BUTTON_L,
    BUTTON_F,
    BUTTON_R,
    BUTTON_T,
    BUTTON_D,
    BUTTON_0,
    BUTTON_9,
    BUTTON_1,
    BUTTON_W,
    BUTTON_N,
    BUTTON_C,
    BUTTON_H,
    BUTTON_COMMA,
    BUTTON_PERIOD,
    BUTTON_S,
)
import _thread

# --- App Globals ---
_VERSION = "1.5_b"

# State management
STATE_EXIT = -1
STATE_INIT = 0
STATE_MAIN_MENU = 1
STATE_SEARCH_KEYBOARD = 2
STATE_SEARCH_RESULTS = 3
STATE_VIEW_ARTICLE = 4
STATE_SETTINGS = 5
STATE_LANGUAGES = 6
STATE_LOADING = 8
STATE_LIST_VIEW = 9
STATE_HELP = 12
STATE_CLEAR_DATA = 14
STATE_QUICK_ACTIONS = 17

# Request Types
REQ_SEARCH = 1
REQ_ARTICLE_FILE = 2
REQ_ARTICLE_RAM = 3
REQ_LANGLINKS = 4
REQ_ARTICLE_FILE_BY_TITLE = 5
REQ_RANDOM = 6
REQ_PRELOAD_LINKS = 7

current_state = STATE_INIT
_current_request_type = REQ_SEARCH

# Network
http_client = None
WIKI_API_URL = "https://{lang}.wikipedia.org/w/api.php"
# Guardian RAM Rules: Force server to close socket immediately to free CYW43 hardware buffers
WIKI_HEADERS = {
    "User-Agent": f"Picoware-WikiReader/{_VERSION} (RP2350)",
    "Connection": "close"
}
_http_lock = None
_http_response_data = None
_target_language = None
_request_start_time = 0
_is_random_article = False
_last_header_status = ""
# Data
search_results = []
current_article_title = ""
current_article_page_id = -1

THEMES = ["system", "light", "gray", "night", "solarized", "high contrast", "terminal green", "terminal orange", "terminal blue"]
_sys_bg = None
_sys_fg = None

# Settings
SETTINGS_FILE = "picoware/wikireader/settings.json"
settings = {"full_article": True, "language": "en", "theme": "system", "text_margin": 10, "font_size": 0, "history": [], "favorites": [], "offline": []}
_settings_dirty = False

# GUI Components
active_ui = None
article_textbox = None
links_data = []
loading_spinner = None
language_menu_origin_state = STATE_MAIN_MENU
article_origin_state = STATE_SEARCH_RESULTS
help_origin_state = STATE_MAIN_MENU
article_nav_stack = []
current_list_type = None

# --- App Globals ---
_vm_ref = None

_UMLAUT_MAP = {
    # Whitespace & invisible chars
    '\xa0': ' ', '\t': ' ', '\u200b': '', '\u200c': '', '\u200d': '', '\u200e': '',
    '\u200f': '', '\u2009': ' ', '\u202f': ' ', '\u2028': '\n', '\u2029': '\n', '\xad': '',
    # Dashes & punctuation (VERY common in Wikipedia)
    '\u2013': '-', '\u2014': '-', '\u2012': '-', '\u2015': '-', '\u2212': '-',
    # Quotes (appear in nearly every article)
    '\u2018': "'", '\u2019': "'", '\u201a': ',', '\u201b': "'",
    '\u201c': '"', '\u201d': '"', '\u201e': '"', '\u201f': '"',
    '\u2039': '<', '\u203a': '>',
    # Ellipsis
    '\u2026': '...',
    # German umlauts
    '\xe4': 'ae', '\xf6': 'oe', '\xfc': 'ue',
    '\xc4': 'Ae', '\xd6': 'Oe', '\xdc': 'Ue', '\xdf': 'ss',
    # German umlauts (Literal form for JSON strings)
    'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'Ä': 'Ae', 'Ö': 'Oe', 'Ü': 'Ue', 'ß': 'ss',
    # French / other accented (Unicode)
    '\u0153': 'oe', '\u0152': 'Oe',
    '\u00e9': 'e', '\u00e8': 'e', '\u00ea': 'e', '\u00eb': 'e',
    '\u00e0': 'a', '\u00e2': 'a', '\u00e1': 'a',
    '\u00ee': 'i', '\u00ef': 'i', '\u00ed': 'i', '\u00ec': 'i',
    '\u00f4': 'o', '\u00f3': 'o', '\u00f2': 'o',
    '\u00f9': 'u', '\u00fb': 'u', '\u00fa': 'u',
    '\u00e7': 'c', '\u00f1': 'n',
    '\u00c9': 'E', '\u00c8': 'E', '\u00ca': 'E', '\u00cb': 'E',
    '\u00c0': 'A', '\u00c2': 'A', '\u00c1': 'A',
    '\u00ce': 'I', '\u00cf': 'I', '\u00cd': 'I',
    '\u00d4': 'O', '\u00d3': 'O',
    '\u00d9': 'U', '\u00db': 'U', '\u00da': 'U',
    '\u00c7': 'C', '\u00d1': 'N',
    # French / other accented (Literal form for JSON strings)
    'œ': 'oe', 'Œ': 'Oe', 'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
    'à': 'a', 'â': 'a', 'á': 'a', 'î': 'i', 'ï': 'i', 'í': 'i', 'ì': 'i',
    'ô': 'o', 'ó': 'o', 'ò': 'o', 'ù': 'u', 'û': 'u', 'ú': 'u',
    'ç': 'c', 'ñ': 'n', 'É': 'E', 'È': 'E', 'Ê': 'E', 'Ë': 'E',
    'À': 'A', 'Â': 'A', 'Á': 'A', 'Î': 'I', 'Ï': 'I', 'Í': 'I',
    'Ô': 'O', 'Ó': 'O', 'Ù': 'U', 'Û': 'U', 'Ú': 'U', 'Ç': 'C', 'Ñ': 'N',
    # Symbols (°, ×, ², etc.)
    '\xb0': ' deg', '\xd7': 'x', '\xf7': '/',
    '\xb2': '2', '\xb3': '3', '\xb9': '1',
    '\xbc': '1/4', '\xbd': '1/2', '\xbe': '3/4',
    '\xb7': '.', '\u2022': '*', '\u2023': '*',
    '\u2020': '+', '\u2021': '+',
    '\u2116': 'No.', '\u00a7': 'S.',
    '\u2190': '<-', '\u2192': '->', '\u2194': '<->',
    '\u2191': '^', '\u2193': 'v',
}


def _replace_umlauts(text):
    """Replaces special characters and accents with ASCII equivalents to prevent rendering glitches."""
    if not text:
        return text

    for k, v in _UMLAUT_MAP.items():
        if k in text:
            text = text.replace(k, v)

    if '&' in text:
        text = text.replace('&amp;', '&').replace('&quot;', '"').replace('&ndash;', '-').replace('&mdash;', '-').replace('&lt;', '<').replace('&gt;', '>')

    # Safety net: strip any remaining non-ASCII bytes the font cannot render.
    has_non_ascii = False
    for ch in text:
        if ord(ch) > 127:
            has_non_ascii = True
            break

    if has_non_ascii:
        buf = bytearray(len(text))
        n = 0
        for ch in text:
            if ord(ch) < 128:
                buf[n] = ord(ch)
                n += 1
        text = buf[:n].decode('ascii')
        del buf

    return text


def _remove_latex(text):
    """Strips out unrendered LaTeX math formulas from Wikipedia plaintext."""
    t1 = "{\\displaystyle"
    t2 = "{\\textstyle"

    if t1 not in text and t2 not in text:
        return text

    # Guardian RAM Rules: Single-pass bytearray accumulation to bypass multi-pass list allocation & join fragmentation
    out_bytes = bytearray()
    idx = 0
    length = len(text)

    while idx < length:
        s1 = text.find(t1, idx)
        s2 = text.find(t2, idx)

        if s1 == -1 and s2 == -1:
            out_bytes.extend(text[idx:].encode('utf-8'))
            break

        if s1 != -1 and s2 != -1:
            start = s1 if s1 < s2 else s2
            t_len = len(t1) if start == s1 else len(t2)
        elif s1 != -1:
            start = s1
            t_len = len(t1)
        else:
            start = s2
            t_len = len(t2)

        if start > idx:
            out_bytes.extend(text[idx:start].encode('utf-8'))

        brace_count = 1
        i = start + t_len

        while i < length and brace_count > 0:
            next_open = text.find('{', i)
            next_close = text.find('}', i)

            if next_close == -1:
                i = length
                break

            if next_open != -1 and next_open < next_close:
                brace_count += 1
                i = next_open + 1
            else:
                brace_count -= 1
                i = next_close + 1

        idx = i

    res = out_bytes.decode('utf-8')
    del out_bytes
    gc.collect()
    return res


_BOILERPLATE_ENDINGS = (
    # English
    "see also", "references", "external links", "further reading", "notes",
    # German
    "weblinks", "einzelnachweise", "literatur", "siehe auch", "quellen", "anmerkungen",
    # French
    "voir aussi", "notes et références", "notes et references", "liens externes", "bibliographie", "articles connexes", "références", "references",
    # Spanish
    "véase también", "vease tambien", "referencias", "enlaces externos", "bibliografía", "bibliografia", "notas",
    # Italian
    "voci correlate", "note", "bibliografia", "collegamenti esterni", "altri progetti", "referenze"
)

def get_view_manager():
    """Helper to get the view_manager instance, for async callbacks."""
    return _vm_ref


_toast_msg = None
_toast_end_time = 0

def show_toast(view_manager, message, duration=1):
    """Queues a non-blocking toast to be drawn by the main loop."""
    global _toast_msg, _toast_end_time
    from utime import ticks_ms
    _toast_msg = message
    _toast_end_time = ticks_ms() + int(duration * 1000)


def _save_reading_progress(view_manager):
    """Saves the current line index to the article's entry in the lists."""
    global settings, article_textbox, current_article_page_id, _settings_dirty
    if not article_textbox or current_article_page_id == -1:
        return
    prog = article_textbox.top_line
    updated = False
    for lst in ("history", "favorites", "offline"):
        for item in settings[lst]:
            # Guardian RAM Rules: Direct list indexing [0]=pageid, [1]=title, [2]=progress
            if item[0] == current_article_page_id:
                old_prog = item[2]
                if old_prog != prog:
                    if old_prog == -1 and prog == 0:
                        item[2] = 0
                    else:
                        item[2] = prog
                        updated = True
    if updated:
        _settings_dirty = True
        save_settings_to_sd(view_manager)


def _go_back_from_article(view_manager):
    """Returns to the previous article in the navigation stack, or the origin state."""
    global current_article_page_id, current_article_title, article_origin_state, article_textbox, loading_spinner, article_nav_stack, _is_random_article
    if article_nav_stack:
        packed = article_nav_stack.pop()
        prev_id = packed >> 1
        _is_random_article = bool(packed & 1)

        # Guardian RAM Rules: Recover title from history to prevent storing strings in the nav stack
        prev_title = "Article"
        for item in settings.get("history", []):
            if item[0] == prev_id:
                prev_title = item[1]
                break

        # Guardian RAM Rules: Proactively update global tracking to prevent cache mismatches
        current_article_page_id = prev_id
        current_article_title = prev_title

        if article_textbox:
            _save_reading_progress(view_manager)
            del article_textbox
            article_textbox = None
        change_state(view_manager, STATE_LOADING)
        if loading_spinner:
            loading_spinner.text = _replace_umlauts(f"Restoring '{prev_title}'...")
        fetch_article(view_manager, prev_id)
    else:
        change_state(view_manager, article_origin_state)


def change_state(view_manager, new_state):
    """Cleans up old state and sets up the new one."""
    global current_state, active_ui, article_textbox, _request_start_time, loading_spinner, links_data, article_nav_stack

    if new_state == STATE_MAIN_MENU:
        del article_nav_stack[:]

    # Clean up current state's resources
    if active_ui:
        del active_ui
        active_ui = None

    if current_state == STATE_VIEW_ARTICLE and article_textbox:
        # Prevent destroying the article when just viewing the ToC overlay
        keep_article = new_state in (STATE_HELP, STATE_QUICK_ACTIONS, STATE_LANGUAGES) or (new_state == STATE_LIST_VIEW and current_list_type in ("toc", "links"))
        if not keep_article and _current_request_type != REQ_PRELOAD_LINKS:
            _save_reading_progress(view_manager)
            del article_textbox
            article_textbox = None
    elif current_state == STATE_LIST_VIEW:
        if current_list_type == "links":
            del links_data[:]
    elif current_state == STATE_LOADING and loading_spinner:
        del loading_spinner
        loading_spinner = None

    gc.collect()

    current_state = new_state

    if new_state == STATE_EXIT:
        return

    view_manager.draw.fill_screen(view_manager.background_color)

    # Set up new state
    if new_state == STATE_MAIN_MENU:
        setup_main_menu(view_manager)
    elif new_state == STATE_SEARCH_KEYBOARD:
        setup_search_keyboard(view_manager)
    elif new_state == STATE_SEARCH_RESULTS:
        setup_search_results(view_manager)
    elif new_state == STATE_SETTINGS:
        setup_settings(view_manager)
    elif new_state == STATE_LANGUAGES:
        setup_languages(view_manager)
    elif new_state == STATE_LIST_VIEW:
        setup_list_view(view_manager)
    elif new_state == STATE_QUICK_ACTIONS:
        setup_quick_actions(view_manager)
    elif new_state == STATE_HELP:
        setup_help(view_manager)
    elif new_state == STATE_CLEAR_DATA:
        setup_clear_data(view_manager)
    elif new_state == STATE_LOADING:
        _request_start_time = ticks_ms()
        from picoware.gui.loading import Loading
        loading_spinner = Loading(
            view_manager.draw,
            view_manager.foreground_color,
            view_manager.background_color,
        )

    if new_state == STATE_VIEW_ARTICLE and article_textbox:
        article_textbox._force_full_redraw = True

    # Push the fully rendered backbuffer to the physical screen
    view_manager.draw.swap()


# --- API & Data Handling ---


def _add_to_history(view_manager):
    """Adds the currently viewed article to the history list."""
    global settings, _settings_dirty
    if not current_article_title or current_article_page_id == -1:
        return
    history = settings.setdefault("history", [])

    # Guardian RAM Rules: Modify in-place to prevent list duplication overhead
    for i in range(len(history) - 1, -1, -1):
        if history[i][0] == current_article_page_id:
            del history[i]

    lang = settings.get("language", "en")
    history.insert(0, [current_article_page_id, current_article_title, -1, lang])
    while len(history) > 15: history.pop()
    _settings_dirty = True
    save_settings_to_sd(view_manager)


def _toggle_favorite(view_manager):
    """Toggles the currently viewed article in the favorites list."""
    global settings, _settings_dirty
    if not current_article_title or current_article_page_id == -1:
        return
    favorites = settings.setdefault("favorites", [])

    removed = False
    for i in range(len(favorites) - 1, -1, -1):
        if favorites[i][0] == current_article_page_id:
            del favorites[i]
            removed = True

    if removed:
        msg = "Removed from Favorites"
    else:
        lang = settings.get("language", "en")
        favorites.insert(0, [current_article_page_id, current_article_title, -1, lang])
        while len(favorites) > 50: favorites.pop()
        msg = "Added to Favorites"
    _settings_dirty = True
    save_settings_to_sd(view_manager)
    show_toast(view_manager, msg, 1)


def _toggle_offline(view_manager):
    """Toggles the offline saved status of the currently viewed article."""
    global settings, _settings_dirty
    if not current_article_title or current_article_page_id == -1:
        return

    offline = settings.setdefault("offline", [])

    removed = False
    for i in range(len(offline) - 1, -1, -1):
        if offline[i][0] == current_article_page_id:
            del offline[i]
            removed = True

    if not view_manager.storage or not view_manager.has_sd_card:
        view_manager.alert("SD Card required!")
        if article_textbox: article_textbox._force_full_redraw = True
        return

    lang = settings["language"]
    encoded_title = url_encode(current_article_title)
    cache_path = f"picoware/wikireader/cache_{lang}_{current_article_page_id}_{encoded_title}.json"
    offline_path = f"picoware/wikireader/offline_{lang}_{current_article_page_id}_{encoded_title}.json"

    try:
        if removed:
            if view_manager.storage.exists(offline_path):
                view_manager.storage.remove(offline_path)
            else:
                # Legacy cleanup
                legacy_path = f"picoware/wikireader/offline_{current_article_page_id}_{encoded_title}.json"
                try: view_manager.storage.remove(legacy_path)
                except Exception: pass
            msg = "Removed from Offline"
        else:
            legacy_cache = f"picoware/wikireader/cache_{current_article_page_id}_{encoded_title}.json"
            if view_manager.storage.exists(cache_path) or view_manager.storage.exists(legacy_cache):
                if view_manager.storage.exists(cache_path):
                    view_manager.storage.copy(cache_path, offline_path)
                else:
                    view_manager.storage.copy(legacy_cache, offline_path)

                offline.insert(0, [current_article_page_id, current_article_title, -1, lang])
                while len(offline) > 50:
                    popped = offline.pop()
                    # Clean up orphaned file on the SD card!
                    if view_manager.storage and view_manager.has_sd_card:
                        encoded = url_encode(popped[1])
                        popped_lang = popped[3] if len(popped) > 3 else lang
                        popped_path_new = f"picoware/wikireader/offline_{popped_lang}_{popped[0]}_{encoded}.json"
                        popped_path_old = f"picoware/wikireader/offline_{popped[0]}_{encoded}.json"
                        try: view_manager.storage.remove(popped_path_new)
                        except Exception: pass
                        try: view_manager.storage.remove(popped_path_old)
                        except Exception: pass
                msg = "Saved for Offline"
            else:
                view_manager.alert("Error: Cache missing.", back=True)
                if article_textbox: article_textbox._force_full_redraw = True
                return
        _settings_dirty = True
        save_settings_to_sd(view_manager)
        show_toast(view_manager, msg, 1)
    except Exception as e:
        view_manager.alert("Storage Error")
        if article_textbox: article_textbox._force_full_redraw = True


def url_encode(s):
    """A simple URL encoder for query strings."""
    if not isinstance(s, str):
        s = str(s)

    # Guardian RAM Rules: Use bytearray to prevent massive string fragmentation
    out = bytearray()
    for b in s.encode('utf-8'):
        if (97 <= b <= 122) or (65 <= b <= 90) or (48 <= b <= 57) or b in b'-_.~':
            out.append(b)
        else:
            out.extend(b'%%%02X' % b)
    res = out.decode('ascii')
    del out
    return res


def _parse_search_results(vm, query_data):
    """Parses search results from the API response."""
    global search_results
    if "search" in query_data:
        # Guardian RAM Rules: Strip bulky unused API metadata to save heap space
        # Cap at 15 items to prevent persistent list memory bloat
        search_results = [(item.get("title", "Unknown"), item.get("pageid", -1)) for item in query_data.get("search", [])[:15]]
        change_state(vm, STATE_SEARCH_RESULTS)
    else:
        show_toast(vm, "Invalid search response", 2)
        change_state(vm, STATE_MAIN_MENU)


def _parse_article_content(vm, query_data):
    """Parses article content from the API response."""
    global current_article_title, current_article_page_id, _current_request_type, loading_spinner
    if "pages" in query_data:
        pages = query_data["pages"]
        if not pages:
            show_toast(vm, "Article not found.", 2)
            _go_back_from_article(vm)
            return

        if isinstance(pages, list):
            page_data = pages[0]
            if page_data.get("missing"):
                show_toast(vm, "Article not found.", 2)
                _go_back_from_article(vm)
                return
            current_article_page_id = int(page_data.get("pageid", -1))
        else:
            page_id_str = list(pages.keys())[0]
            if page_id_str == "-1":
                show_toast(vm, "Article not found.", 2)
                _go_back_from_article(vm)
                return
            current_article_page_id = int(page_id_str)
            page_data = pages[page_id_str]

        if "title" in page_data:
            current_article_title = page_data["title"]

        if "extract" in page_data:
            article_text = page_data["extract"]
            if not article_text.strip():
                show_toast(vm, "Article has no text.", 2)
                _go_back_from_article(vm)
                return

            if not setup_article_view(vm, article_text):
                change_state(vm, article_origin_state)
                return
            _add_to_history(vm)

            if settings.get("preload_links", True):
                _current_request_type = REQ_PRELOAD_LINKS
                if loading_spinner:
                    loading_spinner.text = "Scanning & Highlighting..."
                    loading_spinner.animate()
                fetch_links_preload(vm, current_article_page_id)
            else:
                change_state(vm, STATE_VIEW_ARTICLE)
                if article_textbox:
                    article_textbox.draw_viewer(current_article_title)
                else:
                    show_toast(vm, "Article has no text.", 2)
                    _go_back_from_article(vm)
        else:
            show_toast(vm, "Article not found.", 2)
            _go_back_from_article(vm)


def _extract_text_from_file(view_manager, file_path):
    """Stream-parses JSON string from file without loading JSON into RAM."""
    global loading_spinner

    storage = view_manager.storage
    if not storage or not storage.exists(file_path):
        return ["Error: Article file not found."]

    file = storage.file_open(file_path)
    if not file:
        return ["Error: Could not open article file."]

    file_size = storage.size(file_path)
    chunk_size = 2048  # smaller chunk, less RAM
    target = b'"extract":"'
    found_start = False
    escape = False

    high_surrogate = None
    paragraphs = []
    extracted = bytearray()

    # Guardian RAM Rules: Pre-allocate static chunk buffer to prevent dynamic bytes fragmentation
    chunk_buf = bytearray(chunk_size)
    buffer = bytearray()

    last_update_time = ticks_ms()
    offset = 0

    try:
        while True:
            # Check for user cancellation
            if view_manager.input_manager.button == BUTTON_BACK:
                view_manager.input_manager.reset()
                return None

            now = ticks_ms()
            if ticks_diff(now, last_update_time) > 150:  # Update UI regularly to prevent freeze
                last_update_time = now
                percent = int((offset / max(1, file_size)) * 100)
                if loading_spinner:
                    view_manager.draw.fill_screen(view_manager.background_color)
                    loading_spinner.text = f"Parsing... {percent}%"
                    loading_spinner.animate()
                    view_manager.draw.swap()
                gc.collect()

            bytes_read = storage.file_readinto(file, chunk_buf)
            if bytes_read <= 0:
                break
            offset += bytes_read

            if bytes_read < chunk_size:
                buffer.extend(chunk_buf[:bytes_read])
            else:
                buffer.extend(chunk_buf)

            i = 0
            if not found_start:
                start_idx = buffer.find(target)
                if start_idx != -1:
                    found_start = True
                    i = start_idx + len(target)
                else:
                    # Keep trailing chars in case the target is split across chunks
                    keep_len = len(target) - 1
                    if len(buffer) > keep_len:
                        buffer = buffer[-keep_len:]
                    continue

            while i < len(buffer):
                if escape:
                    # Guardian RAM Rules: Read byte directly as int to bypass 1-byte string fragmentations
                    c = buffer[i]
                    if c == 110: # b'n'
                        extracted.extend(b'\n')
                        para_str = extracted.decode('utf-8')
                        if '{\\displaystyle' in para_str or '{\\textstyle' in para_str:
                            para_str = _remove_latex(para_str)
                        # para_str = _replace_umlauts(para_str)
                        para_str = _replace_umlauts(para_str)

                        # Filter out boilerplate tail sections
                        p_strip = para_str.strip()
                        if p_strip.startswith("==") and p_strip.endswith("=="):
                            p_title = p_strip.strip("= \t\r\n").lower()
                            if p_title in _BOILERPLATE_ENDINGS:
                                return paragraphs

                        paragraphs.append(para_str)
                        extracted = bytearray()
                        if len(paragraphs) % 20 == 0:
                            gc.collect()
                    elif c == 114: pass # b'r' - Drop Carriage Return to prevent overlapping text!
                    elif c == 116: extracted.extend(b'\t') # b't'
                    elif c == 34: extracted.extend(b'"')  # b'"'
                    elif c == 92: extracted.extend(b'\\') # b'\\'
                    elif c == 47: extracted.extend(b'/')  # b'/'
                    elif c == 98: extracted.extend(b'\b') # b'b'
                    elif c == 102: extracted.extend(b'\f') # b'f'
                    elif c == 117: # b'u'
                        if i + 5 <= len(buffer):
                            # Guardian RAM Rules: Convert bytes to hex directly to bypass string allocation
                            try:
                                codepoint = int(buffer[i+1:i+5].decode('ascii'), 16)
                                if 0xD800 <= codepoint <= 0xDBFF:
                                    high_surrogate = codepoint
                                elif 0xDC00 <= codepoint <= 0xDFFF and high_surrogate:
                                    # Combine UTF-16 surrogate pairs into a single 32-bit Unicode codepoint
                                    full_cp = 0x10000 + ((high_surrogate - 0xD800) << 10) + (codepoint - 0xDC00)
                                    extracted.extend(chr(full_cp).encode('utf-8'))
                                    high_surrogate = None
                                else:
                                    high_surrogate = None
                                    extracted.extend(chr(codepoint).encode('utf-8'))
                            except Exception:
                                pass
                            i += 4
                        else:
                            # Need more data for unicode, break to next chunk
                            escape = True
                            break
                    else:
                        extracted.append(c)
                    escape = False
                    i += 1
                else:
                    next_escape = buffer.find(b'\\', i)
                    next_quote = buffer.find(b'"', i)

                    if next_escape == -1 and next_quote == -1:
                        extracted.extend(buffer[i:])
                        i = len(buffer)
                        break

                    end_idx = len(buffer)
                    if next_escape != -1: end_idx = min(end_idx, next_escape)
                    if next_quote != -1 and next_quote < end_idx: end_idx = next_quote

                    if end_idx > i:
                        extracted.extend(buffer[i:end_idx])
                        i = end_idx
                    else:
                        if buffer[i] == 92: # b'\\'
                            escape = True
                            i += 1
                        elif buffer[i] == 34: # b'"'
                            if extracted:
                                para_str = extracted.decode('utf-8')
                                if '{\\displaystyle' in para_str or '{\\textstyle' in para_str:
                                    para_str = _remove_latex(para_str)
                                # para_str = _replace_umlauts(para_str)
                                para_str = _replace_umlauts(para_str)

                                p_strip = para_str.strip()
                                if p_strip.startswith("==") and p_strip.endswith("=="):
                                    p_title = p_strip.strip("= \t\r\n").lower()
                                    if p_title in _BOILERPLATE_ENDINGS:
                                        return paragraphs

                                paragraphs.append(para_str)
                            return paragraphs

            # Guardian RAM Rules: Shift unprocessed bytes down to prevent massive buffer bloat
            if i > 0 and i <= len(buffer):
                buffer = buffer[i:]

    finally:
        storage.file_close(file)

    if extracted:
        para_str = extracted.decode('utf-8')
        if '{\\displaystyle' in para_str or '{\\textstyle' in para_str:
            para_str = _remove_latex(para_str)
        para_str = _replace_umlauts(para_str)
        paragraphs.append(para_str)
    return paragraphs if paragraphs else ["Article text not found in response."]


def _api_callback(response, state, error):
    """Callback for async HTTP requests."""
    global _http_response_data, _http_lock

    # Safely drop trailing callbacks if the app has already closed and deleted the lock
    if _http_lock:
        _http_lock.acquire()
        try:
            _http_response_data = (response, state, error)
        except Exception: pass
        finally:
            _http_lock.release()

def _reset_http_response():
    """Clears any pending HTTP response data safely to prevent stale thread lockouts."""
    global _http_response_data, _http_lock
    if _http_lock:
        _http_lock.acquire()
        try:
            _http_response_data = None
        finally:
            _http_lock.release()


def _extract_metadata_from_file(storage, file_path):
    """Extracts pageid and title from the first chunk of a Wikipedia JSON file."""
    file = storage.file_open(file_path)
    if not file: return None, None
    try:
        buffer = storage.file_read(file, 0, 2048, decode=True)
        pageid = -1
        title = ""

        # Guardian RAM Rules: Parse directly to bypass loading dictionary hierarchies
        pid_str = '"pageid":'
        pid_idx = buffer.find(pid_str)
        if pid_idx != -1:
            start = pid_idx + len(pid_str)
            end = buffer.find(',', start)
            if end == -1: end = buffer.find('}', start)
            if end != -1:
                try: pageid = int(buffer[start:end].strip())
                except ValueError: pass

        title_str = '"title":"'
        title_idx = buffer.find(title_str)
        if title_idx != -1:
            start = title_idx + len(title_str)
            end = buffer.find('"', start)
            if end != -1:
                title = buffer[start:end]

        return pageid, title
    finally:
        storage.file_close(file)


def _process_http_response(view_manager):
    """Process the HTTP response data in the main thread."""
    global _http_response_data, _current_request_type, _target_language, current_article_page_id, current_article_title, article_origin_state, links_data, article_textbox, settings, _settings_dirty, _is_random_article

    if _http_lock:
        _http_lock.acquire()
        try:
            if _http_response_data is None:
                return
            response, state, error = _http_response_data
            _http_response_data = None  # Consume the data
        finally:
            _http_lock.release()

    if error or not response or response.status_code != 200:
        status = response.status_code if response else "No Response"
        msg = error if error else f"HTTP {status}"

        if status == 0 or msg == "HTTP 0":
            msg = "Connection Dropped (Low RAM)"
        elif "-2" in msg:
            msg = "DNS/Network Offline"

        if _current_request_type == REQ_PRELOAD_LINKS:
            change_state(view_manager, STATE_VIEW_ARTICLE)
            if article_textbox:
                article_textbox.draw_viewer(current_article_title)
            return

        if _current_request_type == REQ_LANGLINKS:
            show_toast(view_manager, f"API Error: {msg}", 2)
            change_state(view_manager, STATE_VIEW_ARTICLE)
            if article_textbox:
                article_textbox.draw_viewer(current_article_title)
            return

        if _current_request_type == REQ_SEARCH:
            show_toast(view_manager, f"API Error: {msg}", 2)
            change_state(view_manager, STATE_MAIN_MENU)
            return

        if _current_request_type == REQ_RANDOM:
            show_toast(view_manager, f"API Error: {msg}", 2)
            change_state(view_manager, STATE_MAIN_MENU)
            return

        show_toast(view_manager, f"API Error: {msg}", 2)
        if _current_request_type in (REQ_ARTICLE_RAM, REQ_ARTICLE_FILE, REQ_ARTICLE_FILE_BY_TITLE):
            _go_back_from_article(view_manager)
        else:
            change_state(view_manager, STATE_MAIN_MENU)
        return

    # Guardian RAM Rules: Extract the body and immediately destroy the response object.
    # This guarantees the CYW43 socket is closed *before* chaining the next request!
    raw_text = response.text if response and hasattr(response, 'text') and response.text else ""
    try: response.close()
    except Exception: pass
    del response
    gc.collect()

    # Handle unparsed chunked encoding universally before JSON parsing
    if raw_text:
        start_idx = 0
        text_len = len(raw_text)
        # Safely bypass leading whitespace without creating a massive string duplicate
        while start_idx < text_len and raw_text[start_idx] in ' \t\n\r':
            start_idx += 1

        if start_idx < text_len:
            first_char = raw_text[start_idx]
            if first_char not in ('{', '['):
                crlf = raw_text.find('\r\n', start_idx)
                if crlf != -1 and (crlf - start_idx) <= 10:
                    try:
                        int(raw_text[start_idx:crlf].split(';')[0].strip(), 16)
                        if start_idx == 0: raw_bytes = raw_text.encode('utf-8')
                        else: raw_bytes = raw_text[start_idx:].encode('utf-8')
                        raw_text = None
                        gc.collect()

                        # Guardian RAM Rules: extend() bytearray dynamically to bypass restrictive MicroPython slice assignment bounds
                        total_len = len(raw_bytes)
                        decoded = bytearray()
                        idx = 0

                        while idx < total_len:
                            next_crlf = raw_bytes.find(b'\r\n', idx)
                            if next_crlf == -1: break
                            header = raw_bytes[idx:next_crlf]
                            semi = header.find(b';')
                            if semi != -1: header = header[:semi]

                            try: chunk_size = int(header.strip().decode('ascii'), 16)
                            except Exception: break
                            if chunk_size == 0: break

                            start = next_crlf + 2
                            end = start + chunk_size
                            if end <= total_len:
                                decoded.extend(raw_bytes[start:end])
                            idx = end + 2

                        raw_text = decoded.decode('utf-8')
                        raw_bytes = None
                        decoded = None
                        gc.collect()
                    except ValueError:
                        pass

    if _current_request_type == REQ_LANGLINKS:
        try:
            new_title = ""
            # In formatversion=2, langlinks use "title" instead of "*"
            # We must find the "langlinks" array first to bypass the source page's title
            ll_array_idx = raw_text.find('"langlinks":')
            if ll_array_idx != -1:
                ll_str = '"title":"'
                ll_idx = raw_text.find(ll_str, ll_array_idx)
                if ll_idx != -1:
                    start = ll_idx + len(ll_str)
                    end = start
                    while end < len(raw_text):
                        end = raw_text.find('"', end)
                        if end == -1 or raw_text[end-1] != '\\': break
                        end += 1
                if end != -1:
                    # Guardian RAM Rules: Look-before-you-leap to bypass exception overhead
                    slash_idx = raw_text.find('\\', start)
                    if slash_idx != -1 and slash_idx < end:
                        snippet = raw_text[start-1:end+1]
                        try: new_title = loads(snippet)
                        except Exception: new_title = raw_text[start:end]
                    else:
                        new_title = raw_text[start:end]

            del raw_text
            gc.collect()

            if new_title:
                del article_nav_stack[:]

                settings["language"] = _target_language
                _settings_dirty = True
                _target_language = None
                save_settings_to_sd(view_manager)

                if loading_spinner:
                    loading_spinner.text = "Loading translation..."
                _is_random_article = False

                # Guardian RAM Rules: Free the old article memory before fetching the translated one
                if article_textbox:
                    _save_reading_progress(view_manager)
                    del article_textbox
                    article_textbox = None
                gc.collect()

                fetch_article_by_title(view_manager, new_title)
            else:
                show_toast(view_manager, "No translation available.", 2)
                _target_language = None
                gc.collect()

                # Instant recovery: bypass network re-fetch, article is already in RAM!
                change_state(view_manager, STATE_VIEW_ARTICLE)
                if article_textbox:
                    article_textbox.draw_viewer(current_article_title)
        except Exception as e:
            show_toast(view_manager, "Translation failed.", 2)
            _target_language = None

            # Instant recovery: bypass network re-fetch
            change_state(view_manager, STATE_VIEW_ARTICLE)
            if article_textbox:
                article_textbox.draw_viewer(current_article_title)
        return

    if _current_request_type in (REQ_ARTICLE_FILE, REQ_ARTICLE_FILE_BY_TITLE):
        gc.collect()
        if loading_spinner:
            loading_spinner.text = "Parsing... 0%"
            loading_spinner.animate()

        pageid, title = _extract_metadata_from_file(view_manager.storage, "picoware/wikireader/temp.json")
        if pageid and pageid != -1:
            current_article_page_id = pageid
        if title:
            current_article_title = title

        lang = settings["language"]
        cache_path = f"picoware/wikireader/cache_{lang}_{current_article_page_id}_{url_encode(current_article_title)}.json"
        try:
            if view_manager.storage.exists(cache_path):
                view_manager.storage.remove(cache_path)
            view_manager.storage.rename("picoware/wikireader/temp.json", cache_path)
        except Exception as e:
            cache_path = "picoware/wikireader/temp.json"

        text = _extract_text_from_file(view_manager, cache_path)
        if text is None or not setup_article_view(view_manager, text):
            change_state(view_manager, article_origin_state)
            return

        _add_to_history(view_manager)

        if settings.get("preload_links", True):
            _current_request_type = REQ_PRELOAD_LINKS
            if loading_spinner:
                loading_spinner.text = "Scanning & Highlighting..."
                loading_spinner.animate()
            fetch_links_preload(view_manager, current_article_page_id)
        else:
            change_state(view_manager, STATE_VIEW_ARTICLE)
            if article_textbox:
                article_textbox.draw_viewer(current_article_title)
        return

    if _current_request_type == REQ_RANDOM:
        try:
            pid_str = '"id":'
            pid_idx = raw_text.find(pid_str)
            if pid_idx != -1:
                start = pid_idx + len(pid_str)
                end = raw_text.find(',', start)
                if end == -1: end = raw_text.find('}', start)
                if end != -1:
                    try: current_article_page_id = int(raw_text[start:end].strip())
                    except ValueError: pass

            title_str = '"title":"'
            title_idx = raw_text.find(title_str)
            if title_idx != -1:
                start = title_idx + len(title_str)
                end = start
                while end < len(raw_text):
                    end = raw_text.find('"', end)
                    if end == -1 or raw_text[end-1] != '\\': break
                    end += 1
                if end != -1:
                    # Guardian RAM Rules: Look-before-you-leap to bypass exception overhead
                    slash_idx = raw_text.find('\\', start)
                    if slash_idx != -1 and slash_idx < end:
                        snippet = raw_text[start-1:end+1]
                        try: current_article_title = loads(snippet)
                        except Exception: current_article_title = raw_text[start:end]
                    else:
                        current_article_title = raw_text[start:end]

            del raw_text
            gc.collect()

            if current_article_page_id != -1:
                article_origin_state = STATE_MAIN_MENU
                if loading_spinner:
                    loading_spinner.text = _replace_umlauts(f"Loading '{current_article_title}'...")
                fetch_article(view_manager, current_article_page_id)
            else:
                show_toast(view_manager, "No random article found.", 2)
                change_state(view_manager, STATE_MAIN_MENU)
        except Exception as e:
            show_toast(view_manager, "Random fetch failed.", 2)
            change_state(view_manager, STATE_MAIN_MENU)
        return

    try:
        data = loads(raw_text)
        # Guardian RAM Rules: Destroy the raw JSON string immediately after parsing!
        del raw_text
        gc.collect()

        if "query" in data:
            if "search" in data.get("query", {}):
                _parse_search_results(view_manager, data["query"])
            elif "pages" in data.get("query", {}):
                if _current_request_type == REQ_PRELOAD_LINKS:
                    pages = data["query"]["pages"]
                    if isinstance(pages, list):
                        page_data = pages[0] if pages else {}
                    else:
                        page_data = list(pages.values())[0] if pages else {}
                    links = page_data.get("links", [])
                    if article_textbox:
                        article_textbox.links_preloaded = True
                        del article_textbox.page_links[:]

                        links_to_check = []
                        for item in links:
                            if item.get("ns", 0) == 0:
                                title = item.get("title", "")
                                short_title = title.lower().split(" (")[0].split(", ")[0]
                                links_to_check.append((title, short_title))

                        for p_idx, p in enumerate(article_textbox.paragraphs):
                            lp = p.lower()
                            remaining_links = []
                            for title, short_title in links_to_check:
                                if short_title in lp:
                                    found = False
                                    for ext in article_textbox.page_links:
                                        if ext[0] == title:
                                            found = True
                                            break
                                    if not found:
                                        article_textbox.page_links.append((title, short_title))
                                else:
                                    remaining_links.append((title, short_title))
                            links_to_check = remaining_links
                            del lp
                            gc.collect()
                            if not links_to_check:
                                break
                        del links_to_check

                    change_state(view_manager, STATE_VIEW_ARTICLE)
                    if article_textbox:
                        article_textbox.draw_viewer(current_article_title)
                else:
                    _parse_article_content(view_manager, data["query"])

        # Guardian RAM Rules: Destroy the heavy dictionary after the UI is built
        del data
        gc.collect()
    except Exception as e:
        print("[ERROR] _process_http_response:", e)
        if _current_request_type == REQ_SEARCH:
            show_toast(view_manager, "Search failed (Bad API Response)", 2)
            change_state(view_manager, STATE_MAIN_MENU)
        else:
            show_toast(view_manager, "Invalid API Response", 2)
            if _current_request_type in (REQ_ARTICLE_RAM, REQ_ARTICLE_FILE, REQ_ARTICLE_FILE_BY_TITLE):
                _go_back_from_article(view_manager)
            else:
                change_state(view_manager, STATE_MAIN_MENU)


def clear_cache(view_manager):
    """Removes all cached article JSON files from the SD card."""
    if not view_manager.storage or not view_manager.has_sd_card:
        return
    try:
        directory = "picoware/wikireader"
        entries = view_manager.storage.read_directory(directory)
        if entries:
            for entry in entries:
                filename = entry.get("filename", "")
                if not entry.get("is_directory") and filename.startswith("cache_") and filename.endswith(".json"):
                    try: view_manager.storage.remove(f"{directory}/{filename}")
                    except Exception: pass
            del entries
        gc.collect()
    except Exception as e:
        pass


def enforce_cache_limit(view_manager, limit=10):
    """Ensures the cache directory does not exceed the file limit."""
    if not view_manager.storage or not view_manager.has_sd_card:
        return
    try:
        directory = "picoware/wikireader"
        entries = view_manager.storage.read_directory(directory)
        cache_files = []
        if entries:
            for entry in entries:
                filename = entry.get("filename", "")
                if not entry.get("is_directory") and filename.startswith("cache_") and filename.endswith(".json"):
                    # Guardian RAM Rules: Store flat tuples to eliminate lambda dictionary sorts
                    cache_files.append((entry.get("date", 0), entry.get("time", 0), filename))
            del entries

        if len(cache_files) > limit:
            # Native flat tuple sort eliminates heavy lambda memory overhead
            cache_files.sort()
            files_to_delete = len(cache_files) - limit
            for i in range(files_to_delete):
                file_to_del = cache_files[i][2]
                try: view_manager.storage.remove(f"{directory}/{file_to_del}")
                except Exception: pass
        del cache_files
        gc.collect()
    except Exception as e:
        pass


def fetch_search_results(view_manager, term):
    """Fetch search results from Wikipedia."""
    global _current_request_type, http_client, settings, _request_start_time
    if not http_client:
        return
    _current_request_type = REQ_SEARCH
    encoded_term = url_encode(term)
    gc.collect()
    lang = settings["language"]
    url = f"{WIKI_API_URL.format(lang=lang)}?action=query&list=search&srlimit=15&srsearch={encoded_term}&format=json&formatversion=2"
    _reset_http_response()
    _request_start_time = ticks_ms()
    if not http_client.get_async(url, headers=WIKI_HEADERS, timeout=20):
        show_toast(view_manager, "Search request failed (Low RAM)", 2)
        change_state(view_manager, STATE_MAIN_MENU)


def fetch_links_preload(view_manager, page_id):
    """Fetch wikilinks after the article text is loaded."""
    global _current_request_type, http_client, settings, current_state, current_article_title, article_textbox, _request_start_time
    if not http_client:
        return
    _current_request_type = REQ_PRELOAD_LINKS
    gc.collect()
    lang = settings["language"]
    encoded_title = url_encode(current_article_title)
    url = f"{WIKI_API_URL.format(lang=lang)}?action=query&prop=links&titles={encoded_title}&redirects=1&pllimit=250&format=json&formatversion=2"
    _reset_http_response()
    _request_start_time = ticks_ms()
    if not http_client.get_async(url, headers=WIKI_HEADERS, timeout=20):
        if current_state == STATE_LOADING:
            change_state(view_manager, STATE_VIEW_ARTICLE)
            if article_textbox:
                article_textbox.draw_viewer(current_article_title)


def fetch_article(view_manager, page_id):
    """Fetch a single article from Wikipedia."""
    global _current_request_type, http_client, settings, current_article_title, article_textbox, _request_start_time

    cache_path = None
    if view_manager.storage and view_manager.has_sd_card:
        try:
            lang = settings["language"]
            encoded_title = url_encode(current_article_title)

            path = f"picoware/wikireader/offline_{lang}_{page_id}_{encoded_title}.json"
            if view_manager.storage.exists(path):
                cache_path = path
            else:
                path = f"picoware/wikireader/offline_{page_id}_{encoded_title}.json"
                if view_manager.storage.exists(path):
                    cache_path = path
                else:
                    path = f"picoware/wikireader/cache_{lang}_{page_id}_{encoded_title}.json"
                    if view_manager.storage.exists(path):
                        cache_path = path
                    else:
                        path = f"picoware/wikireader/cache_{page_id}_{encoded_title}.json"
                        if view_manager.storage.exists(path):
                            cache_path = path
                        else:
                            path = f"picoware/wikireader/cache_{page_id}.json"
                            if view_manager.storage.exists(path):
                                cache_path = path
        except Exception: pass

    # Check local SD cache first to bypass network and save RAM
    if cache_path:
        gc.collect()
        text = _extract_text_from_file(view_manager, cache_path)
        if text is None or not setup_article_view(view_manager, text):
            change_state(view_manager, article_origin_state)
            return

        _add_to_history(view_manager)

        if settings.get("preload_links", True):
            _current_request_type = REQ_PRELOAD_LINKS
            if loading_spinner:
                loading_spinner.text = "Scanning & Highlighting..."
                loading_spinner.animate()
            fetch_links_preload(view_manager, page_id)
        else:
            change_state(view_manager, STATE_VIEW_ARTICLE)
            if article_textbox:
                article_textbox.draw_viewer(current_article_title)
        return

    if not http_client:
        return
    lang = settings["language"]
    gc.collect()
    exintro = "&exintro=true" if not settings["full_article"] else ""
    url = f"{WIKI_API_URL.format(lang=lang)}?action=query&prop=extracts&explaintext=true&redirects=1&pageids={page_id}{exintro}&format=json&formatversion=2"

    # Evict oldest caches (max 9 to leave room for this 1), then route large payloads to SD
    if view_manager.storage and view_manager.has_sd_card:
        _current_request_type = REQ_ARTICLE_FILE
        enforce_cache_limit(view_manager, limit=9)
        _reset_http_response()
        _request_start_time = ticks_ms()
        if not http_client.get_async(url, headers=WIKI_HEADERS, timeout=20, save_to_file="picoware/wikireader/temp.json", storage=view_manager.storage):
            show_toast(view_manager, "Failed to start request (Low RAM)", 2)
            _go_back_from_article(view_manager)
    else:
        _current_request_type = REQ_ARTICLE_RAM
        _reset_http_response()
        _request_start_time = ticks_ms()
        if not http_client.get_async(url, headers=WIKI_HEADERS, timeout=20):
            show_toast(view_manager, "Failed to start request (Low RAM)", 2)
            _go_back_from_article(view_manager)


def fetch_random_article(view_manager):
    """Fetch a random article from Wikipedia."""
    global _current_request_type, http_client, settings, _request_start_time
    if not http_client:
        return
    _current_request_type = REQ_RANDOM
    gc.collect()
    lang = settings["language"]
    url = f"{WIKI_API_URL.format(lang=lang)}?action=query&list=random&rnlimit=1&rnnamespace=0&format=json&formatversion=2"
    _reset_http_response()
    _request_start_time = ticks_ms()
    if not http_client.get_async(url, headers=WIKI_HEADERS, timeout=20):
        view_manager.draw.fill_screen(view_manager.background_color)
        view_manager.draw.swap()
        view_manager.alert("Failed to start request (Low RAM)", back=True)
        change_state(view_manager, STATE_MAIN_MENU)


def fetch_article_by_title(view_manager, title):
    """Fetch a target translated article by exactly matched title."""
    global _current_request_type, current_article_title, current_article_page_id, http_client, settings, article_textbox, article_origin_state, _request_start_time

    # Guardian RAM Rules: Proactively assign the title so that if the network or JSON parser fails,
    # the cache file doesn't accidentally overwrite the previous article's cache!
    current_article_title = title
    current_article_page_id = -1

    cache_path = None
    if view_manager.storage and view_manager.has_sd_card:
        lang = settings["language"]
        encoded_title = url_encode(title)
        try:
            entries = view_manager.storage.read_directory("picoware/wikireader")
            suffix = f"_{encoded_title}.json"
            prefix_off = f"offline_{lang}_"
            prefix_cac = f"cache_{lang}_"
            for entry in entries:
                filename = entry.get("filename", "")
                if filename.endswith(suffix):
                    if filename.startswith(prefix_off):
                        cache_path = f"picoware/wikireader/{filename}"
                        break
                    elif filename.startswith(prefix_cac) and not cache_path:
                        cache_path = f"picoware/wikireader/{filename}"
            del entries
            gc.collect()
        except Exception: pass

    if cache_path:
        gc.collect()
        try:
            parts = cache_path.split('/')[-1].replace('.json', '').split('_')
            if len(parts) >= 4 and parts[0] in ("cache", "offline"):
                current_article_page_id = int(parts[2])
            elif len(parts) >= 3:
                current_article_page_id = int(parts[1])
        except Exception: pass
        current_article_title = title

        text = _extract_text_from_file(view_manager, cache_path)
        if text is None or not setup_article_view(view_manager, text):
            change_state(view_manager, article_origin_state)
            return

        _add_to_history(view_manager)

        if settings.get("preload_links", True):
            _current_request_type = REQ_PRELOAD_LINKS
            if loading_spinner:
                loading_spinner.text = "Scanning & Highlighting..."
                loading_spinner.animate()
            fetch_links_preload(view_manager, current_article_page_id)
        else:
            change_state(view_manager, STATE_VIEW_ARTICLE)
            if article_textbox:
                article_textbox.draw_viewer(current_article_title)
        return

    if not http_client:
        return
    lang = settings["language"]
    gc.collect()
    exintro = "&exintro=true" if not settings["full_article"] else ""
    encoded_title = url_encode(title)
    url = f"{WIKI_API_URL.format(lang=lang)}?action=query&prop=extracts&explaintext=true&redirects=1&titles={encoded_title}{exintro}&format=json&formatversion=2"

    if view_manager.storage and view_manager.has_sd_card:
        _current_request_type = REQ_ARTICLE_FILE_BY_TITLE
        enforce_cache_limit(view_manager, limit=9)
        _reset_http_response()
        _request_start_time = ticks_ms()
        if not http_client.get_async(url, headers=WIKI_HEADERS, timeout=20, save_to_file="picoware/wikireader/temp.json", storage=view_manager.storage):
            show_toast(view_manager, "Failed to start request (Low RAM)", 2)
            _go_back_from_article(view_manager)
    else:
        _current_request_type = REQ_ARTICLE_RAM
        _reset_http_response()
        _request_start_time = ticks_ms()
        if not http_client.get_async(url, headers=WIKI_HEADERS, timeout=20):
            show_toast(view_manager, "Failed to start request (Low RAM)", 2)
            _go_back_from_article(view_manager)

def save_settings_to_sd(view_manager):
    """Saves the settings dictionary to the SD card."""
    global settings, _settings_dirty
    if view_manager.storage and _settings_dirty:
        gc.collect()
        try:
            # Guardian RAM Rules: Manually serialize flat schema to bypass heavy json.dumps dictionary introspection
            parts = [
                '{"full_article":', 'true' if settings.get("full_article") else 'false',
                ',"preload_links":', 'true' if settings.get("preload_links", True) else 'false',
                ',"language":"', settings.get("language", "en"), '"',
                ',"theme":"', settings.get("theme", "system"), '"',
                ',"text_margin":', str(settings.get("text_margin", 10)),
                ',"font_size":', str(settings.get("font_size", 0)),
                ',"history":', dumps(settings.get("history", [])),
                ',"favorites":', dumps(settings.get("favorites", [])),
                ',"offline":', dumps(settings.get("offline", [])), '}'
            ]
            json_str = "".join(parts)
            view_manager.storage.write(SETTINGS_FILE, json_str)
            del parts
            del json_str
            _settings_dirty = False
        except Exception as e:
            pass
        finally:
            gc.collect()


def load_settings_from_sd(view_manager):
    """Loads settings from the SD card if the file exists."""
    global settings, _settings_dirty
    if view_manager.storage and view_manager.storage.exists(SETTINGS_FILE):
        try:
            content = view_manager.storage.read(SETTINGS_FILE)
            loaded_settings = loads(content)
            settings.update(loaded_settings)

            # Guardian RAM Rules: Migrate legacy dictionaries to flat lists [pageid, title, progress] to save RAM
            for lst in ("history", "favorites", "offline"):
                if lst in settings:
                    sanitized = []
                    for item in settings[lst]:
                        if isinstance(item, dict):
                            sanitized.append([item.get("pageid", -1), item.get("title", ""), item.get("progress", -1)])
                        elif isinstance(item, list):
                            pid = item[0] if len(item) > 0 else -1
                            ttl = item[1] if len(item) > 1 else "Unknown"
                            prg = item[2] if len(item) > 2 else -1
                            lng = item[3] if len(item) > 3 else loaded_settings.get("language", "en")
                            sanitized.append([pid, ttl, prg, lng])
                    settings[lst] = sanitized

            # Guardian RAM Rules: Clean up loaded strings
            del content
            del loaded_settings
            _settings_dirty = False
            gc.collect()
        except Exception as e:
            pass


def _apply_theme(view_manager):
    """Applies the current theme colors to the view manager."""
    theme = settings.get('theme', 'system')
    from picoware.system.colors import TFT_BLACK, TFT_WHITE, TFT_LIGHTGREY, TFT_YELLOW, TFT_GREEN, TFT_ORANGE, TFT_CYAN
    if theme == 'light':
        view_manager.background_color = TFT_WHITE
        view_manager.foreground_color = TFT_BLACK
    elif theme == 'gray':
        view_manager.background_color = TFT_LIGHTGREY
        view_manager.foreground_color = TFT_BLACK
    elif theme == 'night':
        view_manager.background_color = TFT_BLACK
        view_manager.foreground_color = TFT_LIGHTGREY
    elif theme == 'solarized':
        view_manager.background_color = 0x0146
        view_manager.foreground_color = 0x84B2
    elif theme == 'high contrast':
        view_manager.background_color = TFT_BLACK
        view_manager.foreground_color = TFT_YELLOW
    elif theme == 'terminal green':
        view_manager.background_color = TFT_BLACK
        view_manager.foreground_color = TFT_GREEN
    elif theme == 'terminal orange':
        view_manager.background_color = TFT_BLACK
        view_manager.foreground_color = TFT_ORANGE
    elif theme == 'terminal blue':
        view_manager.background_color = TFT_BLACK
        view_manager.foreground_color = TFT_CYAN
    else:  # system or legacy 'dark'
        view_manager.background_color = _sys_bg if _sys_bg is not None else TFT_BLACK
        view_manager.foreground_color = _sys_fg if _sys_fg is not None else TFT_WHITE


# --- UI Setup Functions ---


class CustomArticleViewer:
    """A custom, memory-efficient text viewer with Header and Footer."""
    def __init__(self, draw, y, height, text_color, bg_color, theme_color):
        self.draw = draw
        self.y = y
        self.height = height
        self.text_color = text_color
        self.bg_color = bg_color
        self.theme_color = theme_color

        # Guardian RAM Rules: Pre-calculate link color based on theme contrast
        self.link_color = 0x07FF  # TFT_CYAN
        if self.bg_color in (0xFFFF, 0xD69A):  # Light or Gray theme
            self.link_color = 0x001F  # TFT_BLUE
        elif self.text_color == 0x07FF:  # Terminal Blue theme
            self.link_color = 0xFFE0  # TFT_YELLOW

        self.para_tokens = []
        self.paragraphs = []
        self.line_indices = bytearray()
        self.num_lines = 0
        self.top_line = 0
        self.cached_toc = bytearray()
        self.page_links = []
        self.links_preloaded = False

        self._force_full_redraw = True
        self._last_header_state = None
        self._last_footer_state = None

        self.font_size = settings.get("font_size", 0)
        font = draw.get_font(self.font_size)
        self.line_height = font.height + 2

        # Define and reserve space for header/footer
        self.header_footer_height = 18
        self.text_area_y = self.y + self.header_footer_height
        self.text_area_height = self.height - (self.header_footer_height * 2)
        self.visible_lines = self.text_area_height // self.line_height

    def update_font_size(self, new_size):
        self.font_size = new_size
        font = self.draw.get_font(self.font_size)
        self.line_height = font.height + 2
        self.visible_lines = self.text_area_height // self.line_height
        self._force_full_redraw = True

        # Guardian RAM Rules: Preserve proportional reading progress during font reflow
        target_p_idx = 0
        if self.num_lines > 0 and self.top_line < self.num_lines:
            offset = self.top_line * 6
            target_p_idx = self.line_indices[offset] | (self.line_indices[offset+1] << 8)

        if self.paragraphs:
            self._tokenize_and_wrap()
            if target_p_idx > 0:
                for i in range(self.num_lines):
                    offset = i * 6
                    if (self.line_indices[offset] | (self.line_indices[offset+1] << 8)) == target_p_idx:
                        self.jump_to_line(i)
                        break

    def set_text(self, text_data):
        """Handles both strings (RAM fetch) and lists (SD chunked fetch)."""
        self._force_full_redraw = True
        self.page_links = []; self.links_preloaded = False
        if isinstance(text_data, str):
            del self.paragraphs[:]
            gc.collect()

            start_idx = 0
            text_len = len(text_data)
            while start_idx < text_len:
                end_idx = text_data.find('\n', start_idx)
                if end_idx == -1:
                    end_idx = text_len

                para_str = text_data[start_idx:end_idx]

                if "{\\displaystyle" in para_str or "{\\textstyle" in para_str:
                    para_str = _remove_latex(para_str)

                para_strip = para_str.strip()
                if para_strip:
                    if para_strip.startswith("==") and para_strip.endswith("=="):
                        title = para_strip.strip("= \t\n\r").lower()
                        if title in _BOILERPLATE_ENDINGS:
                            break

                    if end_idx < text_len:
                        self.paragraphs.append(para_strip + '\n')
                    else:
                        self.paragraphs.append(para_strip)

                start_idx = end_idx + 1
                if len(self.paragraphs) % 10 == 0:
                    gc.collect()
        else:
            # Guardian RAM Rules: Modify list in-place to prevent duplicating massive articles in RAM
            self.paragraphs = text_data
            i = 0
            while i < len(self.paragraphs):
                p = self.paragraphs[i]
                p_strip = p.strip()
                if not p_strip:
                    del self.paragraphs[i]
                    continue
                if p.endswith('\n'):
                    self.paragraphs[i] = p_strip + '\n'
                else:
                    self.paragraphs[i] = p_strip
                i += 1
                if i % 20 == 0:
                    gc.collect()
        return self._tokenize_and_wrap()

    def _tokenize_and_wrap(self):
        global loading_spinner
        self.line_indices = bytearray()
        self.cached_toc = bytearray()
        self.num_lines = 0
        gc.collect()

        margin = settings.get("text_margin", 10)
        max_w = self.draw.size.x - (margin * 2) - 10

        # Guardian RAM Rules: Native draw.len strictly assumes monospaced bounding grids.
        # To wrap proportional text cleanly, we calculate the average glyph width and use character counts!
        base_w = self.draw.len("A")
        if base_w <= 0: base_w = 6
        char_w = base_w * (self.font_size + 1)

        # Guardian RAM Rules: Large fonts need 1.4x packing, small fonts need 1.1x to strictly prevent hardware auto-wrap
        multiplier = 1.4 if self.font_size > 0 else 1.1
        max_chars = int((max_w // char_w) * multiplier)

        paragraphs = self.paragraphs
        total_paras = max(1, len(paragraphs))
        last_update_time = ticks_ms()

        # Cache methods and globals locally to bypass expensive dictionary lookups in the tight loop
        vm = get_view_manager()
        inp = vm.input_manager if vm else None

        for p_idx, para in enumerate(paragraphs):
            # Check for user cancellation
            if inp and inp.button == BUTTON_BACK:
                inp.reset()
                return False

            # UI Feedback to prevent App Freeze
            now = ticks_ms()
            if ticks_diff(now, last_update_time) > 150:
                last_update_time = now
                if loading_spinner:
                    if vm:
                        vm.draw.fill_screen(vm.background_color)
                    loading_spinner.text = f"Formatting... {int((p_idx / total_paras) * 100)}%"
                    loading_spinner.animate()
                    if vm:
                        vm.draw.swap()
                gc.collect()

            is_heading = para.startswith("==") and para.strip().endswith("==")
            if is_heading:
                # Guardian RAM Rules: Look ahead to skip rendering headings for empty sections.
                if p_idx + 1 < len(paragraphs):
                    next_para = paragraphs[p_idx + 1]
                    if next_para.startswith("==") and next_para.strip().endswith("=="):
                        continue # Skip this empty heading entirely.

                # Add a single blank line before the heading for spacing, if it's not the very first line.
                if self.num_lines > 0:
                    self.line_indices.extend(bytes([p_idx & 0xFF, (p_idx >> 8) & 0xFF, 0, 0, 0, 0]))
                    self.num_lines += 1

                self.cached_toc.extend(bytes([p_idx & 0xFF, (p_idx >> 8) & 0xFF, self.num_lines & 0xFF, (self.num_lines >> 8) & 0xFF]))

            text_len = len(para)
            start = 0
            while start < text_len:
                end = start + max_chars
                if end < text_len:
                    space_idx = para.rfind(' ', start, end)
                    nl_idx = para.rfind('\n', start, end)
                    if nl_idx != -1 and nl_idx > start:
                        end = nl_idx
                    elif space_idx != -1 and space_idx > start:
                        end = space_idx
                else:
                    end = text_len

                self.line_indices.extend(bytes([
                    p_idx & 0xFF, (p_idx >> 8) & 0xFF,
                    start & 0xFF, (start >> 8) & 0xFF,
                    end & 0xFF, (end >> 8) & 0xFF
                ]))
                self.num_lines += 1
                start = end + 1

            if is_heading:
                # Guardian RAM Rules: Add a virtual blank line after the heading for readability
                self.line_indices.extend(bytes([p_idx & 0xFF, (p_idx >> 8) & 0xFF, 0, 0, 0, 0]))
                self.num_lines += 1

        self.top_line = 0
        return True

    def _update_token_flags(self):
        pass

    def jump_to_line(self, line_idx):
        """Jumps the viewer to a specific line index safely."""
        max_top = max(0, self.num_lines - self.visible_lines)
        self.top_line = min(max_top, line_idx)

    def next_heading(self):
        """Jumps to the next major heading in the article."""
        if not self.cached_toc:
            return False
        for i in range(0, len(self.cached_toc), 4):
            line_idx = self.cached_toc[i+2] | (self.cached_toc[i+3] << 8)
            if line_idx > self.top_line:
                self.jump_to_line(line_idx)
                return True
        return False

    def prev_heading(self):
        """Jumps to the previous major heading in the article."""
        if not self.cached_toc:
            return False
        for i in range(len(self.cached_toc) - 4, -1, -4):
            line_idx = self.cached_toc[i+2] | (self.cached_toc[i+3] << 8)
            if line_idx < self.top_line:
                self.jump_to_line(line_idx)
                return True
        return False

    def get_visible_text(self):
        """Returns the exact contiguous text visible on the screen by querying paragraph bounds."""
        if self.num_lines == 0 or not self.paragraphs:
            return ""

        offset_start = self.top_line * 6
        start_p = self.line_indices[offset_start] | (self.line_indices[offset_start+1] << 8)
        start_char = self.line_indices[offset_start+2] | (self.line_indices[offset_start+3] << 8)

        last_line = min(self.top_line + self.visible_lines - 1, self.num_lines - 1)
        offset_end = last_line * 6
        end_p = self.line_indices[offset_end] | (self.line_indices[offset_end+1] << 8)
        end_char = self.line_indices[offset_end+4] | (self.line_indices[offset_end+5] << 8)

        text = ""
        for p in range(start_p, end_p + 1):
            s = start_char if p == start_p else 0
            e = end_char if p == end_p else len(self.paragraphs[p])
            text += self.paragraphs[p][s:e] + " "
        return text.lower()

    def draw_viewer(self, title):
        from picoware.system.vector import Vector

        # Guardian RAM Rules: Localize methods and variables to bypass dictionary lookups in the tight loop
        d_text = self.draw.text
        d_fill = self.draw.fill_rectangle
        bg_col = self.bg_color
        fg_col = self.text_color
        th_col = self.theme_color
        lnk_col = self.link_color
        f_size = self.font_size
        line_indices = self.line_indices
        paragraphs = self.paragraphs
        t_area_y = self.text_area_y
        t_area_h = self.text_area_height
        l_height = self.line_height
        draw_w = self.draw.size.x
        draw_h = self.draw.size.y

        # Guardian RAM Rules: Pre-allocate reusable Vectors to prevent heap fragmentation during rendering
        v_pos = Vector(0, 0)
        v_size = Vector(0, 0)

        v_pos.x = 0; v_pos.y = self.y
        v_size.x = draw_w; v_size.y = self.height

        if getattr(self, '_force_full_redraw', True):
            self.draw.clear(v_pos, v_size, bg_col)
        else:
            v_pos.x = 0; v_pos.y = self.text_area_y
            v_size.x = draw_w; v_size.y = self.text_area_height
            d_fill(v_pos, v_size, bg_col)
            v_pos.x = 0; v_pos.y = draw_h - 2
            v_size.x = draw_w; v_size.y = 2
            d_fill(v_pos, v_size, th_col)

        total_lines = self.num_lines
        max_top = max(0, total_lines - self.visible_lines)
        if max_top == 0:
            pct = 100
        else:
            pct = int((self.top_line / max_top) * 100)
            pct = max(0, min(100, pct))
        pct_str = f"{pct}%"

        safe_title = _replace_umlauts(title)

        bat_pct = "--"
        try:
            vm = get_view_manager()
            if vm and hasattr(vm, 'input_manager'):
                bat_pct = str(vm.input_manager.battery)
        except Exception: pass

        # Guardian RAM Rules: Pre-calculate fixed anchor points to prevent UI jitter
        # Max lengths: pct=4 ("100%"), bat=6 ("B:100%"), clock=5 ("23:59")
        pct_anchor_r = draw_w - 5
        bat_anchor_r = pct_anchor_r - self.draw.len("100%") - 15
        clock_anchor_r = bat_anchor_r - self.draw.len("B:100%") - 15

        pct_x = pct_anchor_r - self.draw.len(pct_str)

        bat_str = f"B:{bat_pct}%"
        bat_x = bat_anchor_r - self.draw.len(bat_str)

        clock_str = ""
        try:
            if vm and hasattr(vm, 'time'):
                clock_str = ":".join(vm.time.time.split(":")[:2])  # Just HH:MM
        except Exception: pass

        if clock_str:
            clock_x = clock_anchor_r - self.draw.len(clock_str)
            avail_w = clock_anchor_r - self.draw.len("23:59") - 15
        else:
            clock_x = 0
            avail_w = bat_anchor_r - self.draw.len("B:100%") - 15

        # Determine Current Chapter Context
        current_heading = ""
        for i in range(0, len(self.cached_toc), 4):
            l_idx = self.cached_toc[i+2] | (self.cached_toc[i+3] << 8)
            if l_idx <= self.top_line:
                p_idx = self.cached_toc[i] | (self.cached_toc[i+1] << 8)
                current_heading = paragraphs[p_idx].strip("= \t\n\r")
            else:
                break

        heading_str = f" : {current_heading}" if current_heading else ""

        disp_title = safe_title
        # Guardian RAM Rules: Prioritize truncating the article title to protect the dynamic chapter context
        max_chars = avail_w // max(1, self.draw.len("A"))
        req_chars = len(disp_title) + len(heading_str)
        if req_chars > max_chars:
            excess = req_chars - max_chars
            if len(disp_title) > excess + 3:
                disp_title = disp_title[:-(excess + 3)] + "..."
            else:
                disp_title = ""
                # If it's still too massive, truncate the chapter
                rem_req = len(heading_str)
                if rem_req > max_chars:
                    h_excess = rem_req - max_chars
                    if len(heading_str) > h_excess + 3:
                        heading_str = heading_str[:-(h_excess + 3)] + "..."
                    else:
                        heading_str = ""

        header_state = (pct_str, bat_str, clock_str, disp_title, heading_str)
        if getattr(self, '_force_full_redraw', True) or getattr(self, '_last_header_state', None) != header_state:
            v_pos.x = 0; v_pos.y = self.y
            v_size.x = draw_w; v_size.y = self.header_footer_height
            d_fill(v_pos, v_size, th_col)

            v_pos.x = pct_x; v_pos.y = self.y + 4
            d_text(v_pos, pct_str, bg_col, 0)

            v_pos.x = bat_x; v_pos.y = self.y + 4
            d_text(v_pos, bat_str, bg_col, 0)

            if clock_str:
                v_pos.x = clock_x; v_pos.y = self.y + 4
                d_text(v_pos, clock_str, bg_col, 0)

            v_pos.x = 5; v_pos.y = self.y + 4
            d_text(v_pos, disp_title + heading_str, bg_col, 0)
            self._last_header_state = header_state

        start_x = settings.get("text_margin", 10)
        # Guardian RAM Rules: Prime hardware font state using an off-screen visible character.
        # This forces LVGL to update its internal font state without drawing on-screen artifacts!
        d_text(Vector(-50, -50), "A", bg_col, f_size)

        # Text Body - Native Line Rendering guarantees flawless proportional TrueType kerning!
        for i in range(self.visible_lines):
            line_idx = self.top_line + i
            if line_idx < total_lines:
                offset = line_idx * 6
                p_idx = line_indices[offset] | (line_indices[offset+1] << 8)
                start = line_indices[offset+2] | (line_indices[offset+3] << 8)
                end = line_indices[offset+4] | (line_indices[offset+5] << 8)

                if start < end:
                    line_str = paragraphs[p_idx][start:end]
                    line_lower = line_str.lower()

                    has_link = False
                    if self.links_preloaded:
                        for title, short_title in self.page_links:
                            if short_title in line_lower:
                                has_link = True
                                break

                    if has_link:
                        v_pos.x = start_x; v_pos.y = t_area_y + (i * l_height) + 2
                        d_text(v_pos, line_str, lnk_col, f_size)
                    else:
                        v_pos.x = start_x; v_pos.y = t_area_y + (i * l_height) + 2
                        d_text(v_pos, line_str, fg_col, f_size)

        # Scrollbar
        if max_top > 0:
            scroll_w = 4
            scroll_h = max(10, int((self.visible_lines / total_lines) * t_area_h))
            max_scroll_y = t_area_h - scroll_h
            scroll_y = t_area_y + int((self.top_line / max_top) * max_scroll_y)
            track_x = draw_w - scroll_w
            v_pos.x = track_x; v_pos.y = scroll_y
            v_size.x = scroll_w; v_size.y = scroll_h
            d_fill(v_pos, v_size, th_col)

        # Footer
        total_pages = max(1, (total_lines + self.visible_lines - 1) // self.visible_lines)
        current_page = (self.top_line // self.visible_lines) + 1
        footer_text = f"Pg {current_page}/{total_pages} | [ENT]Menu S:Font L:Lang W:Links H:Help"

        footer_state = footer_text
        if getattr(self, '_force_full_redraw', True) or getattr(self, '_last_footer_state', None) != footer_state:
            footer_y = self.y + self.height - self.header_footer_height
            v_pos.x = 0; v_pos.y = footer_y
            v_size.x = draw_w; v_size.y = self.header_footer_height
            d_fill(v_pos, v_size, th_col)
            v_pos.x = 5; v_pos.y = footer_y + 4
            d_text(v_pos, footer_text, bg_col, 0)
            self._last_footer_state = footer_state

        # Visual Reading Progress Bar (Absolute Bottom Edge)
        if max_top > 0:
            prog_w = int((self.top_line / max_top) * draw_w)
            v_pos.x = 0; v_pos.y = draw_h - 2
            v_size.x = prog_w; v_size.y = 2
            d_fill(v_pos, v_size, bg_col)

        if not _toast_msg:
            self.draw.swap()

        self._force_full_redraw = False

    def scroll_up(self, lines=1):
        self.top_line = max(0, self.top_line - lines)

    def scroll_down(self, lines=1):
        max_top = max(0, self.num_lines - self.visible_lines)
        self.top_line = min(max_top, self.top_line + lines)

    def page_up(self):
        self.scroll_up(max(1, self.visible_lines - 1))

    def page_down(self):
        self.scroll_down(max(1, self.visible_lines - 1))


def setup_main_menu(view_manager):
    """Create the main menu UI."""
    global active_ui
    from picoware.gui.menu import Menu

    draw = view_manager.draw
    active_ui = Menu(
        draw,
        "WikiReader",
        0,
        draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
        view_manager.selected_color,
    )
    active_ui.add_item("Search")
    active_ui.add_item("Random Article")
    active_ui.add_item("On This Day")
    active_ui.add_item("History")
    fav_count = len(settings.get("favorites", []))
    active_ui.add_item(f"Favorites ({fav_count}/50)")
    off_count = len(settings.get("offline", []))
    active_ui.add_item(f"Offline ({off_count}/50)")
    active_ui.add_item("Settings")
    active_ui.add_item("Help")
    active_ui.add_item("Exit")
    active_ui.set_selected(0)
    active_ui.draw()


def setup_search_keyboard(view_manager):
    """Prepare the on-screen keyboard for searching."""
    kb = view_manager.keyboard
    kb.reset()
    kb.title = "Enter search term"
    kb.response = ""
    kb.run(force=True)


def setup_search_results(view_manager):
    """Display the list of search results."""
    global active_ui
    from picoware.gui.list import List

    draw = view_manager.draw
    active_ui = List(
        draw,
        0,
        draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
        view_manager.selected_color,
    )
    if not search_results:
        active_ui.add_item("0 Results. [ENT] to retry.")
    else:
        for i, (title, pageid) in enumerate(search_results):
            active_ui.add_item(_replace_umlauts(title))
            if i % 10 == 9:
                gc.collect()
    gc.collect()
    active_ui.set_selected(0)
    active_ui.draw()


def setup_article_view(view_manager, text):
    """Create the CustomArticleViewer for viewing an article."""
    global article_textbox

    gc.collect()

    draw = view_manager.draw
    article_textbox = CustomArticleViewer(
        draw,
        0,
        draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
        view_manager.selected_color,
    )
    if not article_textbox.set_text(text):
        # Guardian RAM Rules: Explicitly drop the aborted viewer to free fragmented heap bytearrays
        del article_textbox
        article_textbox = None
        return False

    # Restore reading progress
    prog = 0
    for lst in ("history", "favorites", "offline"):
        for item in settings.get(lst, []):
            if item[0] == current_article_page_id:
                prog = item[2]
                break
        if prog > 0:
            break

    if prog > 0:
        article_textbox.jump_to_line(prog)

    gc.collect()

    return True


def setup_settings(view_manager):
    """Create the settings UI using a Menu."""
    global active_ui
    from picoware.gui.menu import Menu

    active_ui = Menu(
        view_manager.draw,
        "Settings",
        0,
        view_manager.draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
        view_manager.selected_color,
    )
    _refresh_settings_menu_items(view_manager)


def _refresh_settings_menu_items(view_manager):
    """Helper to populate the settings menu based on current settings."""
    global active_ui, settings
    if not active_ui: return

    sel = active_ui.selected_index

    active_ui.clear()
    gc.collect()
    active_ui.add_item(f"Full Article: {'On' if settings['full_article'] else 'Off'}")
    active_ui.add_item(f"Auto-Highlight Links: {'On' if settings.get('preload_links', True) else 'Off'}")
    active_ui.add_item(f"Language: {settings['language']}")
    theme_str = settings.get('theme', 'system')
    if theme_str == 'dark': theme_str = 'system'
    active_ui.add_item(f"Theme: {theme_str[0].upper() + theme_str[1:]}")
    margin_val = settings.get("text_margin", 10)
    active_ui.add_item(f"Text Margin: {margin_val}px")
    font_sz_str = "Medium" if settings.get("font_size", 0) == 1 else "Small"
    active_ui.add_item(f"Font Size: {font_sz_str}")
    active_ui.add_item("Clear Data...")
    active_ui.add_item("Save and Back")

    active_ui.set_selected(sel)
    active_ui.draw()
    view_manager.draw.swap()


def setup_clear_data(view_manager):
    """Create the clear data submenu."""
    global active_ui, settings
    from picoware.gui.menu import Menu
    active_ui = Menu(
        view_manager.draw,
        "Clear Data",
        0,
        view_manager.draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
        view_manager.selected_color,
    )
    active_ui.add_item("Clear Cache")
    active_ui.add_item("Clear History")
    active_ui.add_item("Clear Favorites")
    active_ui.add_item("Clear Offline")
    active_ui.add_item("Clear All Data")
    active_ui.add_item("Back")
    active_ui.set_selected(0)
    active_ui.draw()


def setup_languages(view_manager):
    """Create the language selection list."""
    global active_ui
    from picoware.gui.list import List

    draw = view_manager.draw
    active_ui = List(
        draw,
        0,
        draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
        view_manager.selected_color,
    )

    # Removed "ja" and "ru" as the default Picoware fonts lack CJK and Cyrillic glyphs
    supported_langs = ["en", "de", "fr", "es", "it"]
    for lang in supported_langs:
        active_ui.add_item(lang)

    try:
        selected_index = supported_langs.index(settings["language"])
        active_ui.set_selected(selected_index)
    except ValueError:
        active_ui.set_selected(0)
    active_ui.draw()


def _get_local_files_set(view_manager):
    """Returns an O(1) lookup set of all cached and offline filenames."""
    local_files = set()
    if view_manager.storage and view_manager.has_sd_card:
        try:
            entries = view_manager.storage.read_directory("picoware/wikireader")
            if entries:
                for entry in entries:
                    if not entry.get("is_directory"):
                        local_files.add(entry.get("filename", ""))
                del entries
        except Exception: pass
    return local_files


def setup_list_view(view_manager):
    """Unified setup for History, Favorites, Offline, TOC, and Links lists."""
    global active_ui, links_data, current_list_type
    from picoware.gui.list import List

    draw = view_manager.draw
    active_ui = List(
        draw, 0, draw.size.y, view_manager.foreground_color,
        view_manager.background_color, view_manager.selected_color
    )

    if current_list_type in ("history", "favorites", "offline"):
        items = settings.get(current_list_type, [])
        if not items:
            msg = "History is empty." if current_list_type == "history" else f"{current_list_type[0].upper()}{current_list_type[1:]} list is empty (0/50)."
            active_ui.add_item(msg)
        else:
            storage = view_manager.storage
            has_sd = view_manager.has_sd_card
            local_files = _get_local_files_set(view_manager)
            for i, item in enumerate(items):
                pageid = item[0]
                title = _replace_umlauts(item[1])
                item_lang = item[3] if len(item) > 3 else settings.get("language", "en")
                display_text = title
                if storage and has_sd:
                    try:
                        encoded = url_encode(item[1])
                        if (f"offline_{item_lang}_{pageid}_{encoded}.json" in local_files or
                            f"cache_{item_lang}_{pageid}_{encoded}.json" in local_files or
                            f"offline_{pageid}_{encoded}.json" in local_files or
                            f"cache_{pageid}_{encoded}.json" in local_files or
                            f"cache_{pageid}.json" in local_files):
                            display_text = f"[*] {title}"
                        del encoded
                    except Exception: pass
                active_ui.add_item(display_text)
                if i % 10 == 9:
                    gc.collect()
            del local_files

    elif current_list_type == "toc":
        if not article_textbox or not article_textbox.cached_toc:
            active_ui.add_item("No sections found.")
        else:
            toc_bytes = article_textbox.cached_toc
            for i in range(0, len(toc_bytes), 4):
                p_idx = toc_bytes[i] | (toc_bytes[i+1] << 8)
                p_strip = article_textbox.paragraphs[p_idx].strip()
                level = len(p_strip) - len(p_strip.lstrip("="))
                title = p_strip.strip("=").strip()
                prefix = "  " * (level - 2) if level >= 2 else ""
                active_ui.add_item(prefix + title)
                if (i // 4) % 20 == 19:
                    gc.collect()

    elif current_list_type == "links":
        if not links_data:
            active_ui.add_item("No links available.")
        else:
            for i, title in enumerate(links_data):
                active_ui.add_item(_replace_umlauts(title))
                if i % 20 == 19:
                    gc.collect()

    gc.collect()
    active_ui.set_selected(0)
    active_ui.draw()


def setup_quick_actions(view_manager):
    """Create the Quick Actions selection list."""
    global active_ui
    from picoware.gui.menu import Menu

    draw = view_manager.draw
    active_ui = Menu(
        draw,
        "Quick Actions",
        0,
        draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
        view_manager.selected_color,
    )

    active_ui.add_item("Table of Contents")
    active_ui.add_item("Scan/Open Links")
    active_ui.add_item("Language/Translate")
    active_ui.add_item("Save Offline")
    active_ui.add_item("Toggle Favorite")
    active_ui.add_item("Force Reload")
    active_ui.add_item("Cancel")

    active_ui.set_selected(0)
    active_ui.draw()


def setup_help(view_manager):
    """Create the help screen UI."""
    global active_ui
    from picoware.gui.textbox import TextBox

    draw = view_manager.draw
    active_ui = TextBox(
        draw, 0, draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color
    )

    help_text = (
        f"WIKI READER MANUAL v{_VERSION}\n"
        "------------------\n\n"
        "PURPOSE:\n"
        "Search, read & translate\n"
        "Wikipedia articles.\n\n"
        "GLOBAL CONTROLS:\n"
        "[UP/DN] : Scroll Menus\n"
        "[ENTER] : Select Option\n"
        "[BACK]  : Go Back / Exit\n\n"
        "SEARCH TIPS:\n"
        "- Press [1] on ANY menu to\n"
        "  instantly search.\n"
        "- Press [ENT] on 0 Results\n"
        "  to quickly try again.\n\n"
        "READER CONTROLS:\n"
        "[UP/DN] : Scroll Line\n"
        "[L/R]   : Scroll Page\n"
        "[ENT]   : Quick Menu\n"
        "[0] Key : Jump to Top\n"
        "[9] Key : Jump to End\n"
        "[W] Key : Scan/Open Links\n"
        "[,] Key : Prev Heading\n"
        "[.] Key : Next Heading\n"
        "[S] Key : Toggle Font Size\n"
        "[L] Key : Language/Translate\n"
        "[T] Key : Table of Contents\n"
        "[H] Key : Open Help\n"
        "[D] Key : Save Offline\n"
        "[F] Key : Toggle Favorite\n"
        "[R] Key : Reload / New Random\n\n"
        "INDICATORS:\n"
        "[*] = Saved to SD Card\n\n"
        "PRO TIPS:\n"
        "- If Auto-Highlight Links\n"
        "  is OFF, press [W] while\n"
        "  reading to scan and\n"
        "  highlight links.\n\n"
        "CREDITS:\n"
        "made by Slasher006\n"
        "with the help of GeminiAi."
    )
    active_ui.set_text(_replace_umlauts(help_text))
    active_ui.refresh()


# --- State-specific Run Functions ---


def run_main_menu(view_manager):
    """Handle input and drawing for the main menu."""
    global active_ui, settings, help_origin_state, article_origin_state, _is_random_article, current_list_type
    if not active_ui:
        return
    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_UP:
        active_ui.scroll_up()
        inp.reset()
    elif button == BUTTON_DOWN:
        active_ui.scroll_down()
        inp.reset()
    elif button == BUTTON_BACK:
        inp.reset()
        change_state(view_manager, STATE_EXIT)
    elif button == BUTTON_1:
        inp.reset()
        change_state(view_manager, STATE_SEARCH_KEYBOARD)
    elif button == BUTTON_CENTER:
        selected = active_ui.current_item
        inp.reset()
        if selected == "Search":
            change_state(view_manager, STATE_SEARCH_KEYBOARD)
        elif selected == "Random Article":
            article_origin_state = STATE_MAIN_MENU
            _is_random_article = True
            del article_nav_stack[:]
            change_state(view_manager, STATE_LOADING)
            if loading_spinner:
                loading_spinner.text = "Feeling lucky..."
            fetch_random_article(view_manager)
        elif selected == "On This Day":
            try:
                date_str = view_manager.time.date
                m, d, _ = date_str.split('/')
                m_int = int(m)
                d_int = int(d)
                lang = settings.get("language", "en")

                if lang == "de":
                    months = ("", "Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember")
                    target_title = f"{d_int}. {months[m_int]}"
                elif lang == "fr":
                    months = ("", "janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre")
                    d_str = "1er" if d_int == 1 else str(d_int)
                    target_title = f"{d_str} {months[m_int]}"
                elif lang == "es":
                    months = ("", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")
                    target_title = f"{d_int} de {months[m_int]}"
                elif lang == "it":
                    months = ("", "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre")
                    target_title = f"{d_int} {months[m_int]}"
                else:
                    months = ("", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")
                    target_title = f"{months[m_int]} {d_int}"

                article_origin_state = STATE_MAIN_MENU
                _is_random_article = False
                del article_nav_stack[:]
                change_state(view_manager, STATE_LOADING)
                if loading_spinner:
                    loading_spinner.text = _replace_umlauts(f"Loading '{target_title}'...")
                fetch_article_by_title(view_manager, target_title)
            except Exception as e:
                view_manager.draw.fill_screen(view_manager.background_color)
                view_manager.alert("Could not read date.", back=True)
        elif selected == "History":
            current_list_type = "history"
            change_state(view_manager, STATE_LIST_VIEW)
        elif selected.startswith("Favorites"):
            current_list_type = "favorites"
            change_state(view_manager, STATE_LIST_VIEW)
        elif selected.startswith("Offline"):
            current_list_type = "offline"
            change_state(view_manager, STATE_LIST_VIEW)
        elif selected == "Settings":
            change_state(view_manager, STATE_SETTINGS)
        elif selected == "Help":
            help_origin_state = STATE_MAIN_MENU
            change_state(view_manager, STATE_HELP)
        elif selected == "Exit":
            change_state(view_manager, STATE_EXIT)


def run_search_keyboard(view_manager):
    """Handle the search input keyboard."""
    global loading_spinner
    kb = view_manager.keyboard
    is_running = kb.run()

    if kb.is_finished:
        search_term = kb.response
        kb.reset()
        if search_term:
            change_state(view_manager, STATE_LOADING)
            if loading_spinner:
                loading_spinner.text = _replace_umlauts(f"Searching for '{search_term}'...")
            fetch_search_results(view_manager, search_term)
        else:
            change_state(view_manager, STATE_MAIN_MENU)
    elif not is_running:
        change_state(view_manager, STATE_MAIN_MENU)


def run_loading(view_manager):
    """Display the loading animation."""
    global http_client, _http_response_data, current_state, _request_start_time, _http_lock, loading_spinner, _current_request_type, current_article_title, article_textbox

    inp = view_manager.input_manager
    if inp.button == BUTTON_BACK:
        inp.reset()

        # Guardian RAM Rules: Kill the active HTTP request immediately to stop background thread accumulation
        if http_client:
            http_client.callback = None  # Prevent stale callbacks!
            http_client.close()
            del http_client

        from picoware.system.http import HTTP
        http_client = HTTP(thread_manager=view_manager.thread_manager, chunk_size=8 * 1024)
        http_client.callback = _api_callback

        _reset_http_response()

        gc.collect()

        if _current_request_type == REQ_PRELOAD_LINKS:
            change_state(view_manager, STATE_VIEW_ARTICLE)
            if article_textbox:
                article_textbox.draw_viewer(current_article_title)
        elif _current_request_type in (REQ_ARTICLE_RAM, REQ_ARTICLE_FILE, REQ_ARTICLE_FILE_BY_TITLE):
            _go_back_from_article(view_manager)
        else:
            change_state(view_manager, STATE_MAIN_MENU)
        return

    _process_http_response(view_manager)

    if current_state == STATE_LOADING:
        if ticks_diff(ticks_ms(), _request_start_time) > 20000:
            if http_client:
                http_client.callback = None  # Prevent stale callbacks!
                http_client.close()
                del http_client

            from picoware.system.http import HTTP
            http_client = HTTP(thread_manager=view_manager.thread_manager, chunk_size=8 * 1024)
            http_client.callback = _api_callback

            _reset_http_response()

            gc.collect()
            if _current_request_type == REQ_PRELOAD_LINKS:
                change_state(view_manager, STATE_VIEW_ARTICLE)
                if article_textbox:
                    article_textbox.draw_viewer(current_article_title)
                return

            show_toast(view_manager, "Request timed out!", 2)
            if _current_request_type in (REQ_ARTICLE_RAM, REQ_ARTICLE_FILE, REQ_ARTICLE_FILE_BY_TITLE):
                _go_back_from_article(view_manager)
            else:
                change_state(view_manager, STATE_MAIN_MENU)
            return

        if loading_spinner:
            loading_spinner.animate()


def run_search_results(view_manager):
    """Handle the search results list."""
    global current_article_title, current_article_page_id, article_origin_state, active_ui, search_results, loading_spinner, _is_random_article
    if not active_ui:
        return
    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_UP:
        active_ui.scroll_up()
        inp.reset()
    elif button == BUTTON_DOWN:
        active_ui.scroll_down()
        inp.reset()
    elif button == BUTTON_BACK:
        inp.reset()
        change_state(view_manager, STATE_MAIN_MENU)
    elif button == BUTTON_1:
        inp.reset()
        change_state(view_manager, STATE_SEARCH_KEYBOARD)
    elif button == BUTTON_CENTER:
        if search_results:
            selected_index = active_ui.selected_index
            current_article_title, current_article_page_id = search_results[selected_index]
            inp.reset()

            article_origin_state = STATE_SEARCH_RESULTS
            _is_random_article = False
            del article_nav_stack[:]
            change_state(view_manager, STATE_LOADING)
            if loading_spinner:
                loading_spinner.text = _replace_umlauts(f"Loading '{current_article_title}'...")
            fetch_article(view_manager, current_article_page_id)
        else:
            inp.reset()
            change_state(view_manager, STATE_SEARCH_KEYBOARD)


def run_view_article(view_manager):
    """Handle the article reading view."""
    global language_menu_origin_state, article_textbox, current_article_title, current_article_page_id, help_origin_state, links_data, _current_request_type, loading_spinner, _is_random_article, current_list_type, settings, _settings_dirty
    if not article_textbox:
        return

    inp = view_manager.input_manager
    button = inp.button

    needs_redraw = False

    if button == BUTTON_UP:
        article_textbox.scroll_up(2)
        inp.reset()
        needs_redraw = True
    elif button == BUTTON_DOWN:
        article_textbox.scroll_down(2)
        inp.reset()
        needs_redraw = True
    elif button == BUTTON_LEFT:
        article_textbox.page_up()
        inp.reset()
        needs_redraw = True
    elif button == BUTTON_RIGHT:
        article_textbox.page_down()
        inp.reset()
        needs_redraw = True
    elif button == BUTTON_BACK:
        inp.reset()
        _go_back_from_article(view_manager)
        return
    elif button == BUTTON_0:
        inp.reset()
        if article_textbox:
            article_textbox.jump_to_line(0)
            needs_redraw = True
    elif button == BUTTON_9:
        inp.reset()
        if article_textbox and article_textbox.num_lines > 0:
            article_textbox.jump_to_line(article_textbox.num_lines - 1)
            needs_redraw = True
    elif button == BUTTON_COMMA:
        inp.reset()
        if article_textbox:
            if not article_textbox.prev_heading():
                show_toast(view_manager, "Top of article", 1)
            needs_redraw = True
    elif button == BUTTON_PERIOD:
        inp.reset()
        if article_textbox:
            if not article_textbox.next_heading():
                show_toast(view_manager, "Bottom of article", 1)
            needs_redraw = True
    elif button == BUTTON_S:
        inp.reset()
        settings["font_size"] = 1 if settings.get("font_size", 0) == 0 else 0
        _settings_dirty = True
        save_settings_to_sd(view_manager)
        if article_textbox:
            view_manager.draw.fill_screen(view_manager.background_color)
            from picoware.gui.loading import Loading
            spinner_existed = loading_spinner is not None
            if not loading_spinner:
                loading_spinner = Loading(view_manager.draw, view_manager.foreground_color, view_manager.background_color)
            loading_spinner.text = "Scaling text..."
            loading_spinner.animate()
            view_manager.draw.swap()

            article_textbox.update_font_size(settings["font_size"])

            if not spinner_existed:
                del loading_spinner
                loading_spinner = None
            gc.collect()
            needs_redraw = True
    elif button == BUTTON_H:
        inp.reset()
        help_origin_state = STATE_VIEW_ARTICLE
        change_state(view_manager, STATE_HELP)
        return
    elif button == BUTTON_L:
        language_menu_origin_state = STATE_VIEW_ARTICLE
        change_state(view_manager, STATE_LANGUAGES)
        inp.reset()
        return
    elif button == BUTTON_F:
        inp.reset()
        _toggle_favorite(view_manager)
        needs_redraw = True
    elif button == BUTTON_D:
        inp.reset()
        _toggle_offline(view_manager)
        needs_redraw = True
    elif button == BUTTON_T:
        inp.reset()
        current_list_type = "toc"
        change_state(view_manager, STATE_LIST_VIEW)
        return
    elif button == BUTTON_CENTER:
        inp.reset()
        change_state(view_manager, STATE_QUICK_ACTIONS)
        return
    elif button == BUTTON_W:
        inp.reset()

        if article_textbox and not article_textbox.links_preloaded:
            _current_request_type = REQ_PRELOAD_LINKS
            change_state(view_manager, STATE_LOADING)
            if loading_spinner:
                loading_spinner.text = "Scanning & Highlighting..."
            fetch_links_preload(view_manager, current_article_page_id)
            return

        del links_data[:]
        if article_textbox and hasattr(article_textbox, 'page_links'):
            visible_text = article_textbox.get_visible_text()
            for title, short_title in article_textbox.page_links:
                if short_title in visible_text:
                    links_data.append(title)
        if links_data:
            current_list_type = "links"
            change_state(view_manager, STATE_LIST_VIEW)
            return
        else:
            show_toast(view_manager, "No links on screen.", 1)
            needs_redraw = True
    elif button == BUTTON_R:
        inp.reset()
        if _is_random_article:
            if article_textbox:
                del article_textbox
                article_textbox = None
            gc.collect()
            change_state(view_manager, STATE_LOADING)
            if loading_spinner:
                loading_spinner.text = "Feeling lucky..."
            fetch_random_article(view_manager)
        else:
            # Force reload by deleting the cache file first if it exists
            if view_manager.storage and view_manager.has_sd_card:
                lang = settings["language"]
                encoded_title = url_encode(current_article_title)
                try: view_manager.storage.remove(f"picoware/wikireader/cache_{lang}_{current_article_page_id}_{encoded_title}.json")
                except Exception: pass
                try: view_manager.storage.remove(f"picoware/wikireader/cache_{current_article_page_id}_{encoded_title}.json")
                except Exception: pass
                try: view_manager.storage.remove(f"picoware/wikireader/cache_{current_article_page_id}.json")
                except Exception: pass

            if article_textbox:
                _save_reading_progress(view_manager)
                del article_textbox
                article_textbox = None
            gc.collect()

            change_state(view_manager, STATE_LOADING)
            if loading_spinner: loading_spinner.text = "Reloading..."
            if current_article_page_id == -1:
                fetch_article_by_title(view_manager, current_article_title)
            else:
                fetch_article(view_manager, current_article_page_id)
            return

    if needs_redraw and article_textbox:
        article_textbox.draw_viewer(current_article_title)


def run_settings(view_manager):
    """Handle the settings menu."""
    global language_menu_origin_state, active_ui, settings, _settings_dirty
    if not active_ui:
        return
    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_UP:
        active_ui.scroll_up()
        inp.reset()
    elif button == BUTTON_DOWN:
        active_ui.scroll_down()
        inp.reset()
    elif button == BUTTON_BACK:
        inp.reset()
        # Don't save on back
        change_state(view_manager, STATE_MAIN_MENU)
    elif button == BUTTON_CENTER:
        inp.reset()
        selected_index = active_ui.selected_index
        if selected_index == 0:  # Full Article
            settings["full_article"] = not settings["full_article"]
            _settings_dirty = True
            _refresh_settings_menu_items(view_manager)
        elif selected_index == 1:  # Auto-Highlight Links
            settings["preload_links"] = not settings.get("preload_links", True)
            _settings_dirty = True
            _refresh_settings_menu_items(view_manager)
        elif selected_index == 2:  # Language
            language_menu_origin_state = STATE_SETTINGS
            change_state(view_manager, STATE_LANGUAGES)
        elif selected_index == 3:  # Theme
            current_theme = settings.get('theme', 'system')
            try:
                idx = THEMES.index(current_theme)
            except ValueError:
                idx = 0
            settings['theme'] = THEMES[(idx + 1) % len(THEMES)]
            _settings_dirty = True
            _apply_theme(view_manager)
            change_state(view_manager, STATE_SETTINGS)
            if active_ui:
                active_ui.set_selected(3)
                active_ui.draw()
                view_manager.draw.swap()
        elif selected_index == 4:  # Text Margin
            margins = [10, 20, 30, 40, 50, 60]
            current_margin = settings.get("text_margin", 10)
            try:
                idx = margins.index(current_margin)
            except ValueError:
                idx = 0
            settings["text_margin"] = margins[(idx + 1) % len(margins)]
            _settings_dirty = True
            _refresh_settings_menu_items(view_manager)
        elif selected_index == 5:  # Font Size
            settings["font_size"] = 1 if settings.get("font_size", 0) == 0 else 0
            _settings_dirty = True
            _refresh_settings_menu_items(view_manager)
        elif selected_index == 6:  # Clear Data...
            change_state(view_manager, STATE_CLEAR_DATA)
        elif selected_index == 7:  # Save and Back
            save_settings_to_sd(view_manager)
            change_state(view_manager, STATE_MAIN_MENU)


def run_clear_data(view_manager):
    """Handle the clear data submenu."""
    global active_ui, settings, _settings_dirty
    if not active_ui:
        return
    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_UP:
        active_ui.scroll_up()
        inp.reset()
    elif button == BUTTON_DOWN:
        active_ui.scroll_down()
        inp.reset()
    elif button == BUTTON_BACK:
        inp.reset()
        change_state(view_manager, STATE_SETTINGS)
    elif button == BUTTON_CENTER:
        inp.reset()
        selected_index = active_ui.selected_index
        if selected_index == 0:  # Clear Cache
            clear_cache(view_manager)
            show_toast(view_manager, "Cache cleared successfully!", 1)
            view_manager.draw.fill_screen(view_manager.background_color)
            active_ui.draw()
        elif selected_index == 1:  # Clear History
            settings["history"] = []
            _settings_dirty = True
            save_settings_to_sd(view_manager)
            show_toast(view_manager, "History cleared successfully!", 1)
            view_manager.draw.fill_screen(view_manager.background_color)
            active_ui.draw()
        elif selected_index == 2:  # Clear Favorites
            settings["favorites"] = []
            _settings_dirty = True
            save_settings_to_sd(view_manager)
            show_toast(view_manager, "Favorites cleared successfully!", 1)
            view_manager.draw.fill_screen(view_manager.background_color)
            active_ui.draw()
        elif selected_index == 3:  # Clear Offline
            if view_manager.storage and view_manager.has_sd_card:
                try:
                    entries = view_manager.storage.read_directory("picoware/wikireader")
                    for entry in entries:
                        filename = entry.get("filename", "")
                        if filename.startswith("offline_") and filename.endswith(".json"):
                            try: view_manager.storage.remove(f"picoware/wikireader/{filename}")
                            except Exception: pass
                    del entries
                    gc.collect()
                except Exception: pass
            settings["offline"] = []
            _settings_dirty = True
            save_settings_to_sd(view_manager)
            show_toast(view_manager, "Offline files deleted!", 1)
            view_manager.draw.fill_screen(view_manager.background_color)
            active_ui.draw()
        elif selected_index == 4:  # Clear All Data
            clear_cache(view_manager)
            if view_manager.storage and view_manager.has_sd_card:
                try:
                    entries = view_manager.storage.read_directory("picoware/wikireader")
                    for entry in entries:
                        filename = entry.get("filename", "")
                        if filename.startswith("offline_") and filename.endswith(".json"):
                            try: view_manager.storage.remove(f"picoware/wikireader/{filename}")
                            except Exception: pass
                    del entries
                    gc.collect()
                except Exception: pass
            settings["history"] = []
            settings["favorites"] = []
            settings["offline"] = []
            _settings_dirty = True
            save_settings_to_sd(view_manager)
            show_toast(view_manager, "All data cleared!", 1)
            view_manager.draw.fill_screen(view_manager.background_color)
            active_ui.draw()
        elif selected_index == 5:  # Back
            change_state(view_manager, STATE_SETTINGS)


def run_languages(view_manager):
    """Handle the language selection list."""
    global _target_language, _current_request_type, active_ui, settings, language_menu_origin_state, loading_spinner, http_client, current_article_page_id, _request_start_time, _settings_dirty
    if not active_ui:
        return
    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_UP:
        active_ui.scroll_up()
        inp.reset()
    elif button == BUTTON_DOWN:
        active_ui.scroll_down()
        inp.reset()
    elif button == BUTTON_BACK:
        inp.reset()
        if language_menu_origin_state == STATE_VIEW_ARTICLE:
            change_state(view_manager, STATE_VIEW_ARTICLE)
            if article_textbox:
                article_textbox.draw_viewer(current_article_title)
        else:
            change_state(view_manager, language_menu_origin_state)
    elif button == BUTTON_CENTER:
        new_lang = active_ui.current_item
        old_lang = settings["language"]
        inp.reset()
        if language_menu_origin_state == STATE_VIEW_ARTICLE and new_lang != old_lang:
            _target_language = new_lang
            change_state(view_manager, STATE_LOADING)
            if loading_spinner:
                loading_spinner.text = f"Locating in {new_lang}..."

            _current_request_type = REQ_LANGLINKS
            encoded_title = url_encode(current_article_title)
            url = f"{WIKI_API_URL.format(lang=old_lang)}?action=query&prop=langlinks&lllang={new_lang}&redirects=1&titles={encoded_title}&format=json&formatversion=2"
            _reset_http_response()
            _request_start_time = ticks_ms()
            http_client.get_async(url, headers=WIKI_HEADERS, timeout=20)
        elif new_lang != old_lang:
            settings["language"] = new_lang
            _settings_dirty = True
            change_state(view_manager, language_menu_origin_state)
        else:
            if language_menu_origin_state == STATE_VIEW_ARTICLE:
                change_state(view_manager, STATE_VIEW_ARTICLE)
                if article_textbox:
                    article_textbox.draw_viewer(current_article_title)
            else:
                change_state(view_manager, language_menu_origin_state)


def run_list_view(view_manager):
    """Unified event loop for History, Favorites, Offline, TOC, and Links lists."""
    global active_ui, current_list_type, current_article_title, current_article_page_id, article_origin_state, loading_spinner, _is_random_article, settings, links_data, article_textbox, article_nav_stack
    if not active_ui:
        return
    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_UP:
        active_ui.scroll_up()
        inp.reset()
    elif button == BUTTON_DOWN:
        active_ui.scroll_down()
        inp.reset()
    elif button == BUTTON_BACK:
        inp.reset()
        if current_list_type in ("history", "favorites", "offline"):
            change_state(view_manager, STATE_MAIN_MENU)
        else:  # toc, links
            change_state(view_manager, STATE_VIEW_ARTICLE)
            if article_textbox:
                article_textbox.draw_viewer(current_article_title)
    elif button == BUTTON_1 and current_list_type in ("history", "favorites", "offline"):
        inp.reset()
        change_state(view_manager, STATE_SEARCH_KEYBOARD)
    elif button == BUTTON_CENTER:
        inp.reset()
        if current_list_type in ("history", "favorites", "offline"):
            items = settings.get(current_list_type, [])
            if items and active_ui.selected_index < len(items):
                item = items[active_ui.selected_index]
                current_article_page_id = item[0]
                current_article_title = item[1]
                item_lang = item[3] if len(item) > 3 else settings.get("language", "en")
                if settings.get("language") != item_lang:
                    settings["language"] = item_lang
                    _settings_dirty = True
                    save_settings_to_sd(view_manager)

                article_origin_state = STATE_LIST_VIEW
                _is_random_article = False
                del article_nav_stack[:]
                change_state(view_manager, STATE_LOADING)
                if loading_spinner:
                    loading_spinner.text = _replace_umlauts(f"Loading '{current_article_title}'...")
                fetch_article(view_manager, current_article_page_id)
        elif current_list_type == "toc":
            if article_textbox and article_textbox.cached_toc:
                sel_idx = active_ui.selected_index
                if sel_idx * 4 < len(article_textbox.cached_toc):
                    offset = sel_idx * 4
                    target_line = article_textbox.cached_toc[offset+2] | (article_textbox.cached_toc[offset+3] << 8)
                    change_state(view_manager, STATE_VIEW_ARTICLE)
                    if article_textbox:
                        article_textbox.jump_to_line(target_line)
                        article_textbox.draw_viewer(current_article_title)
        elif current_list_type == "links":
            if links_data and active_ui.selected_index < len(links_data):
                target_title = links_data[active_ui.selected_index]
                packed_state = (current_article_page_id << 1) | (1 if _is_random_article else 0)
                article_nav_stack.append(packed_state)
                if len(article_nav_stack) > 10:
                    del article_nav_stack[0]
                _is_random_article = False

                if article_textbox:
                    _save_reading_progress(view_manager)
                    del article_textbox
                    article_textbox = None

                change_state(view_manager, STATE_LOADING)
                if loading_spinner:
                    loading_spinner.text = _replace_umlauts(f"Loading '{target_title}'...")
                fetch_article_by_title(view_manager, target_title)


def run_quick_actions(view_manager):
    """Handle the Quick Actions menu."""
    global active_ui, article_textbox, current_article_title, links_data, _current_request_type, loading_spinner, current_article_page_id, _is_random_article, current_list_type
    if not active_ui:
        return
    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_UP:
        active_ui.scroll_up()
        inp.reset()
    elif button == BUTTON_DOWN:
        active_ui.scroll_down()
        inp.reset()
    elif button == BUTTON_BACK:
        inp.reset()
        change_state(view_manager, STATE_VIEW_ARTICLE)
        if article_textbox:
            article_textbox.draw_viewer(current_article_title)
    elif button == BUTTON_CENTER:
        selected = active_ui.current_item
        inp.reset()

        if selected == "Cancel":
            change_state(view_manager, STATE_VIEW_ARTICLE)
            if article_textbox:
                article_textbox.draw_viewer(current_article_title)
        elif selected == "Table of Contents":
            current_list_type = "toc"
            change_state(view_manager, STATE_LIST_VIEW)
        elif selected == "Scan/Open Links":
            if article_textbox and not article_textbox.links_preloaded:
                _current_request_type = REQ_PRELOAD_LINKS
                change_state(view_manager, STATE_LOADING)
                if loading_spinner:
                    loading_spinner.text = "Scanning & Highlighting..."
                fetch_links_preload(view_manager, current_article_page_id)
                return

            del links_data[:]
            if article_textbox and hasattr(article_textbox, 'page_links'):
                visible_text = article_textbox.get_visible_text()
                for title, short_title in article_textbox.page_links:
                    if short_title in visible_text:
                        links_data.append(title)
            if links_data:
                current_list_type = "links"
                change_state(view_manager, STATE_LIST_VIEW)
            else:
                from picoware.gui.alert import Alert
                toast = Alert(view_manager.draw, "No links on screen.", view_manager.foreground_color, view_manager.background_color)
                toast.draw("Notice")
                from time import sleep
                sleep(1)
                del toast
                import gc
                gc.collect()
                change_state(view_manager, STATE_VIEW_ARTICLE)
                if article_textbox:
                    article_textbox.draw_viewer(current_article_title)
        elif selected == "Language/Translate":
            language_menu_origin_state = STATE_VIEW_ARTICLE
            change_state(view_manager, STATE_LANGUAGES)
        elif selected == "Save Offline":
            _toggle_offline(view_manager)
            change_state(view_manager, STATE_VIEW_ARTICLE)
            if article_textbox:
                article_textbox.draw_viewer(current_article_title)
        elif selected == "Toggle Favorite":
            _toggle_favorite(view_manager)
            change_state(view_manager, STATE_VIEW_ARTICLE)
            if article_textbox:
                article_textbox.draw_viewer(current_article_title)
        elif selected == "Force Reload":
            if _is_random_article:
                if article_textbox:
                    del article_textbox
                    article_textbox = None
                gc.collect()
                del article_nav_stack[:]
                change_state(view_manager, STATE_LOADING)
                if loading_spinner:
                    loading_spinner.text = "Feeling lucky..."
                fetch_random_article(view_manager)
            else:
                if view_manager.storage and view_manager.has_sd_card:
                    _clear_article_caches(view_manager, current_article_page_id, current_article_title)

                if article_textbox:
                    _save_reading_progress(view_manager)
                    del article_textbox
                    article_textbox = None
                gc.collect()

                change_state(view_manager, STATE_LOADING)
                if loading_spinner: loading_spinner.text = "Reloading..."
                if current_article_page_id == -1:
                    fetch_article_by_title(view_manager, current_article_title)
                else:
                    fetch_article(view_manager, current_article_page_id)


def run_help(view_manager):
    """Handle the Help screen."""
    global active_ui, help_origin_state
    if not active_ui:
        return
    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_UP:
        active_ui.scroll_up()
        inp.reset()
    elif button == BUTTON_DOWN:
        active_ui.scroll_down()
        inp.reset()
    elif button == BUTTON_BACK:
        inp.reset()
        change_state(view_manager, help_origin_state)
        if help_origin_state == STATE_VIEW_ARTICLE and article_textbox:
            article_textbox.draw_viewer(current_article_title)

# --- Picoware App Lifecycle ---


def start(view_manager):
    """Called when the application is launched."""
    global http_client, loading_spinner, current_state, _http_lock, _vm_ref, _sys_bg, _sys_fg
    from picoware.system.http import HTTP
    from picoware.gui.loading import Loading
    from picoware.system.colors import TFT_BLACK, TFT_WHITE

    if not view_manager.wifi or not view_manager.wifi.is_connected():
        view_manager.alert("WiFi not connected!", back=True)
        return False

    # Store a reference to view_manager for the async callback
    _vm_ref = view_manager

    _http_lock = _thread.allocate_lock()

    # Create persistent objects
    # Route background networking to the OS ThreadManager
    http_client = HTTP(thread_manager=view_manager.thread_manager, chunk_size=8 * 1024)
    http_client.callback = _api_callback

    # Load settings
    if view_manager.storage:
        view_manager.storage.mkdir("picoware/wikireader")
    load_settings_from_sd(view_manager)

    # Store OS colors BEFORE applying theme
    _sys_bg = view_manager.background_color
    _sys_fg = view_manager.foreground_color

    _apply_theme(view_manager)

    gc.collect()

    # Set initial state
    change_state(view_manager, STATE_MAIN_MENU)

    return True


def stop(view_manager):
    """Called when the application is closed."""
    global http_client, loading_spinner, active_ui, search_results, settings, language_menu_origin_state, _sys_bg, _sys_fg, article_textbox, _vm_ref, _http_lock, _target_language, article_origin_state, help_origin_state, _request_start_time, article_nav_stack, links_data, _is_random_article, _last_header_status, current_list_type

    if http_client:
        http_client.callback = None
        http_client.close()
        # Give the background thread a moment to exit
        sleep(0.1)
        del http_client
        http_client = None
    if loading_spinner:
        del loading_spinner
        loading_spinner = None
    if article_textbox:
        _save_reading_progress(view_manager)
        del article_textbox
        article_textbox = None
    if active_ui:
        del active_ui
        active_ui = None

    view_manager.keyboard.reset()

    # Guardian RAM Rules: Explicitly clear global arrays to release object references
    del search_results[:]
    del links_data[:]
    del article_nav_stack[:]

    # Save settings after cleaning up all large UI objects to prevent MemoryError
    save_settings_to_sd(view_manager)

    current_article_title = ""
    # Clear the reference
    _vm_ref = None
    if _http_lock:
        del _http_lock
        _http_lock = None
    language_menu_origin_state = STATE_MAIN_MENU
    _target_language = None
    article_origin_state = STATE_SEARCH_RESULTS
    help_origin_state = STATE_MAIN_MENU

    # Restore the original system colors before wiping the cache
    if _sys_bg is not None:
        view_manager.background_color = _sys_bg
    if _sys_fg is not None:
        view_manager.foreground_color = _sys_fg

    _sys_bg = None
    _sys_fg = None
    _request_start_time = 0
    _is_random_article = False
    _last_header_status = ""
    current_list_type = None

    # Guarantee the heap is swept clean for the next app
    gc.collect()



def run(view_manager):
    """Called repeatedly while the application is running."""
    global current_state, _toast_msg, _toast_end_time, _last_header_status, active_view
    from utime import ticks_ms, ticks_diff
    if current_state == STATE_EXIT:
        current_state = STATE_INIT  # Prevent infinite loop of back() calls
        view_manager.back(True, False, True)  # Exit without clearing screen to black
        return

    needs_redraw = False
    if _toast_msg and ticks_diff(ticks_ms(), _toast_end_time) > 0:
        _toast_msg = None
        needs_redraw = True

    current_time = ""
    current_bat = ""
    try:
        if view_manager and hasattr(view_manager, 'time'):
            current_time = ":".join(view_manager.time.time.split(":")[:2])
        if view_manager and hasattr(view_manager, 'input_manager'):
            current_bat = str(view_manager.input_manager.battery)
    except Exception: pass

    new_status = current_time + current_bat
    if new_status != _last_header_status:
        _last_header_status = new_status
        if current_state == STATE_VIEW_ARTICLE:
            needs_redraw = True

    # Guardian CPU Rules: If no button is pressed, and we aren't in a state
    # that requires continuous polling (like loading/keyboard), instantly return!
    # This completely eliminates unnecessary function call overhead on idle ticks.
    if view_manager.input_manager.button == -1 and current_state not in (STATE_LOADING, STATE_SEARCH_KEYBOARD) and not needs_redraw:
        return

    # State machine
    if current_state == STATE_MAIN_MENU:
        run_main_menu(view_manager)
    elif current_state == STATE_SEARCH_KEYBOARD:
        run_search_keyboard(view_manager)
    elif current_state == STATE_LOADING:
        run_loading(view_manager)
    elif current_state == STATE_SEARCH_RESULTS:
        run_search_results(view_manager)
    elif current_state == STATE_VIEW_ARTICLE:
        run_view_article(view_manager)
    elif current_state == STATE_SETTINGS:
        run_settings(view_manager)
    elif current_state == STATE_LANGUAGES:
        run_languages(view_manager)
    elif current_state == STATE_LIST_VIEW:
        run_list_view(view_manager)
    elif current_state == STATE_QUICK_ACTIONS:
        run_quick_actions(view_manager)
    elif current_state == STATE_HELP:
        run_help(view_manager)
    elif current_state == STATE_CLEAR_DATA:
        run_clear_data(view_manager)

    if needs_redraw:
        # Redraw the underlying state when toast expires
        if current_state == STATE_VIEW_ARTICLE and article_textbox:
            article_textbox._force_full_redraw = True
            article_textbox.draw_viewer(current_article_title)
        elif active_ui:
            view_manager.draw.fill_screen(view_manager.background_color)
            if current_state == STATE_HELP:
                active_ui.refresh()
            else:
                active_ui.draw()
            if not _toast_msg: view_manager.draw.swap()

    if _toast_msg:
        from picoware.gui.alert import Alert
        import gc
        toast = Alert(view_manager.draw, _toast_msg, view_manager.foreground_color, view_manager.background_color)
        toast.draw("Notice")
        view_manager.draw.swap()
        del toast
        gc.collect()