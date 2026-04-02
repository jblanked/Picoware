"""
WikiReader - A Wikipedia reader app for Picoware

Allows searching and reading articles from Wikipedia.
"""

import gc
import struct
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
    BUTTON_S,
    BUTTON_L,
    BUTTON_F,
    BUTTON_R,
    BUTTON_T,
    BUTTON_D,
)
import _thread

# --- App Globals ---

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
STATE_HISTORY = 9
STATE_FAVORITES = 10
STATE_TOC = 11
STATE_HELP = 12
STATE_OFFLINE = 13
STATE_CLEAR_DATA = 14

# Request Types
REQ_SEARCH = 1
REQ_ARTICLE_FILE = 2
REQ_ARTICLE_RAM = 3
REQ_LANGLINKS = 4
REQ_ARTICLE_FILE_BY_TITLE = 5

current_state = STATE_INIT
_current_request_type = REQ_SEARCH

# Network
http_client = None
WIKI_API_URL = "https://{lang}.wikipedia.org/w/api.php"
WIKI_HEADERS = {"User-Agent": "Picoware-WikiReader/1.0 (RP2350)"}
_http_lock = None
_http_response_data = None
_pending_action = None
_target_language = None
_request_start_time = 0
# Data
search_results = []
current_article_title = ""
current_article_page_id = -1

THEMES = ["system", "light", "gray", "night", "solarized", "high contrast", "terminal green", "terminal orange", "terminal blue"]
_sys_bg = None
_sys_fg = None

# Settings
SETTINGS_FILE = "picoware/wikireader/settings.json"
settings = {"full_article": False, "language": "en", "default_font_size": 0, "theme": "system", "history": [], "favorites": [], "offline": []}

# GUI Components
main_menu = None
search_results_list = None
article_textbox = None
settings_menu = None
languages_list = None
history_list = None
favorites_list = None
offline_list = None
toc_list = None
toc_data = []
help_textbox = None
loading_spinner = None
clear_data_menu = None
language_menu_origin_state = STATE_MAIN_MENU
article_origin_state = STATE_SEARCH_RESULTS

# --- App Globals ---
_vm_ref = None


def _replace_umlauts(text):
    """Replaces German umlauts with ASCII equivalents to prevent rendering glitches."""
    if not text:
        return text

    # In-place check to bypass expensive temporary string allocations when characters aren't present
    if 'ä' in text: text = text.replace('ä', 'ae')
    if 'ö' in text: text = text.replace('ö', 'oe')
    if 'ü' in text: text = text.replace('ü', 'ue')
    if 'Ä' in text: text = text.replace('Ä', 'Ae')
    if 'Ö' in text: text = text.replace('Ö', 'Oe')
    if 'Ü' in text: text = text.replace('Ü', 'Ue')
    if 'ß' in text: text = text.replace('ß', 'ss')
    return text


def get_view_manager():
    """Helper to get the view_manager instance, for async callbacks."""
    return _vm_ref


def show_toast(view_manager, message, duration=1):
    """Displays a non-blocking alert that disappears after a set duration."""
    from picoware.gui.alert import Alert
    toast = Alert(view_manager.draw, message, view_manager.foreground_color, view_manager.background_color)
    toast.draw("Notice")
    sleep(duration)
    del toast
    gc.collect()


def change_state(view_manager, new_state):
    """Cleans up old state and sets up the new one."""
    global current_state, main_menu, search_results_list, article_textbox, settings_menu, clear_data_menu, languages_list, history_list, favorites_list, offline_list, toc_list, toc_data, help_textbox, _request_start_time

    # Clean up current state's resources
    if current_state == STATE_MAIN_MENU and main_menu:
        del main_menu
        main_menu = None
    elif current_state == STATE_SEARCH_RESULTS and search_results_list:
        del search_results_list
        search_results_list = None
    elif current_state == STATE_VIEW_ARTICLE and article_textbox:
        # Prevent destroying the article when just viewing the ToC overlay
        if new_state not in (STATE_TOC,):
            del article_textbox
            article_textbox = None
    elif current_state == STATE_SETTINGS and settings_menu:
        del settings_menu
        settings_menu = None
    elif current_state == STATE_LANGUAGES and languages_list:
        del languages_list
        languages_list = None
    elif current_state == STATE_HISTORY and history_list:
        del history_list
        history_list = None
    elif current_state == STATE_FAVORITES and favorites_list:
        del favorites_list
        favorites_list = None
    elif current_state == STATE_OFFLINE and offline_list:
        del offline_list
        offline_list = None
    elif current_state == STATE_TOC and toc_list:
        del toc_list
        toc_list = None
        del toc_data[:]
    elif current_state == STATE_HELP and help_textbox:
        del help_textbox
        help_textbox = None
    elif current_state == STATE_CLEAR_DATA and clear_data_menu:
        del clear_data_menu
        clear_data_menu = None

    gc.collect()

    current_state = new_state

    if new_state == STATE_EXIT:
        return

    view_manager.clear()

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
    elif new_state == STATE_HISTORY:
        setup_history(view_manager)
    elif new_state == STATE_FAVORITES:
        setup_favorites(view_manager)
    elif new_state == STATE_OFFLINE:
        setup_offline(view_manager)
    elif new_state == STATE_TOC:
        setup_toc(view_manager)
    elif new_state == STATE_HELP:
        setup_help(view_manager)
    elif new_state == STATE_CLEAR_DATA:
        setup_clear_data(view_manager)
    elif new_state == STATE_LOADING:
        from time import ticks_ms
        _request_start_time = ticks_ms()
        if loading_spinner:
            loading_spinner.animating = False
            loading_spinner.time_elapsed = 0

    # Push the fully rendered backbuffer to the physical screen
    view_manager.draw.swap()


# --- API & Data Handling ---


def _add_to_history(view_manager):
    """Adds the currently viewed article to the history list."""
    global settings
    if not current_article_title or current_article_page_id == -1:
        return
    history = settings.setdefault("history", [])

    # Guardian RAM Rules: Modify in-place to prevent list duplication overhead
    for i in range(len(history) - 1, -1, -1):
        if history[i].get("pageid") == current_article_page_id:
            del history[i]

    history.insert(0, {"title": current_article_title, "pageid": current_article_page_id})
    while len(history) > 15: history.pop()
    save_settings_to_sd(view_manager)


def _toggle_favorite(view_manager):
    """Toggles the currently viewed article in the favorites list."""
    global settings
    if not current_article_title or current_article_page_id == -1:
        return
    favorites = settings.setdefault("favorites", [])

    removed = False
    for i in range(len(favorites) - 1, -1, -1):
        if favorites[i].get("pageid") == current_article_page_id:
            del favorites[i]
            removed = True

    if removed:
        msg = "Removed from Favorites"
    else:
        favorites.insert(0, {"title": current_article_title, "pageid": current_article_page_id})
        while len(favorites) > 50: favorites.pop()
        msg = "Added to Favorites"
    save_settings_to_sd(view_manager)
    show_toast(view_manager, msg, 1)


def _toggle_offline(view_manager):
    """Toggles the offline saved status of the currently viewed article."""
    global settings
    if not current_article_title or current_article_page_id == -1:
        return

    offline = settings.setdefault("offline", [])

    removed = False
    for i in range(len(offline) - 1, -1, -1):
        if offline[i].get("pageid") == current_article_page_id:
            del offline[i]
            removed = True

    if not view_manager.storage or not view_manager.has_sd_card:
        view_manager.alert("SD Card required!")
        return

    encoded_title = url_encode(current_article_title)
    cache_path = f"picoware/wikireader/cache_{current_article_page_id}_{encoded_title}.json"
    offline_path = f"picoware/wikireader/offline_{current_article_page_id}_{encoded_title}.json"

    try:
        if removed:
            if view_manager.storage.exists(offline_path):
                view_manager.storage.remove(offline_path)
            msg = "Removed from Offline"
        else:
            if view_manager.storage.exists(cache_path):
                view_manager.storage.copy(cache_path, offline_path)
                offline.insert(0, {"title": current_article_title, "pageid": current_article_page_id})
                while len(offline) > 50: offline.pop()
                msg = "Saved for Offline"
            else:
                view_manager.alert("Error: Cache missing.", back=True)
                return
        save_settings_to_sd(view_manager)
        show_toast(view_manager, msg, 1)
    except Exception as e:
        print(f"[ERROR] Offline toggle failed: {e}")
        view_manager.alert("Storage Error")


def url_encode(s):
    """A simple URL encoder for query strings."""
    if not isinstance(s, str):
        s = str(s)

    # Guardian RAM Rules: Iterate over raw UTF-8 bytes to ensure correct API payload encoding
    return "".join(chr(b) if (97 <= b <= 122) or (65 <= b <= 90) or (48 <= b <= 57) or b in b'-_.~' else '%%%02X' % b for b in s.encode('utf-8'))


def _parse_search_results(vm, query_data):
    """Parses search results from the API response."""
    global search_results
    if "search" in query_data:
        # Guardian RAM Rules: Strip bulky unused API metadata to save heap space
        # Cap at 15 items to prevent persistent list memory bloat
        search_results = [{"title": item.get("title", "Unknown"), "pageid": item.get("pageid", -1)} for item in query_data.get("search", [])[:15]]
        change_state(vm, STATE_SEARCH_RESULTS)
    else:
        vm.alert("Invalid search response", back=True)
        change_state(vm, STATE_MAIN_MENU)


def _parse_article_content(vm, query_data):
    """Parses article content from the API response."""
    global current_article_title, current_article_page_id
    if "pages" in query_data:
        pages = query_data["pages"]
        if not pages:
            vm.alert("Article not found.", back=True)
            change_state(vm, STATE_SEARCH_RESULTS)
            return
        page_id_str = list(pages.keys())[0]
        if page_id_str == "-1":
            vm.alert("Article not found.", back=True)
            change_state(vm, STATE_SEARCH_RESULTS)
            return
        current_article_page_id = int(page_id_str)
        if "title" in pages[page_id_str]:
            current_article_title = pages[page_id_str]["title"]
        if "extract" in pages[page_id_str]:
            article_text = pages[page_id_str]["extract"]
            setup_article_view(vm, article_text)
            _add_to_history(vm)
            change_state(vm, STATE_VIEW_ARTICLE)
            if article_textbox:
                article_textbox.draw_viewer(current_article_title)
        else:
            vm.alert("Article has no text.", back=True)
            change_state(vm, STATE_SEARCH_RESULTS)


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
    offset = 0
    target = b'"extract":"'
    found_start = False
    escape = False

    paragraphs = []
    extracted = bytearray()
    buffer = b""

    last_percent = -1
    last_update_time = ticks_ms()

    try:
        while offset < file_size:
            now = ticks_ms()
            if ticks_diff(now, last_update_time) > 100:  # Update UI every 100ms
                last_update_time = now
                percent = int((offset / file_size) * 100)
                if percent > last_percent:
                    last_percent = percent
                    if loading_spinner:
                        loading_spinner.text = f"Parsing... {percent}%"
                        loading_spinner.animate()

            read_len = min(chunk_size, file_size - offset)
            chunk = storage.file_read(file, offset, read_len, decode=False)
            if not chunk:
                break
            offset += read_len
            buffer += chunk

            i = 0
            if not found_start:
                start_idx = buffer.find(target)
                if start_idx != -1:
                    found_start = True
                    i = start_idx + len(target)
                else:
                    # Keep trailing chars in case the target is split across chunks
                    buffer = buffer[-(len(target)-1):] if len(buffer) >= len(target) else buffer
                    continue

            while i < len(buffer):
                if escape:
                    c = buffer[i:i+1]
                    if c == b'n':
                        extracted.extend(b'\n')
                        # Memory Optimization: Store line-by-line to avoid huge contiguous allocations
                        paragraphs.append(extracted.decode('utf-8'))
                        extracted = bytearray()
                    elif c == b'r': extracted.extend(b'\r')
                    elif c == b't': extracted.extend(b'\t')
                    elif c == b'"': extracted.extend(b'"')
                    elif c == b'\\': extracted.extend(b'\\')
                    elif c == b'u':
                        if i + 5 <= len(buffer):
                            hex_str = buffer[i+1:i+5].decode('ascii')
                            try:
                                codepoint = int(hex_str, 16)
                                extracted.extend(chr(codepoint).encode('utf-8'))
                            except: pass
                            i += 4
                        else:
                            # Need more data for unicode, break to next chunk
                            buffer = buffer[i:]
                            i = len(buffer)
                            escape = True
                            continue
                    else:
                        extracted.extend(c)
                    escape = False
                    i += 1
                else:
                    next_escape = buffer.find(b'\\', i)
                    next_quote = buffer.find(b'"', i)

                    if next_escape == -1 and next_quote == -1:
                        extracted.extend(buffer[i:])
                        buffer = b""
                        break

                    end_idx = len(buffer)
                    if next_escape != -1: end_idx = min(end_idx, next_escape)
                    if next_quote != -1 and next_quote < end_idx: end_idx = next_quote

                    if end_idx > i:
                        extracted.extend(buffer[i:end_idx])
                        i = end_idx
                    else:
                        if buffer[i:i+1] == b'\\':
                            escape = True
                            i += 1
                        elif buffer[i:i+1] == b'"':
                                if extracted:
                                    paragraphs.append(extracted.decode('utf-8'))
                                return paragraphs
    finally:
        storage.file_close(file)

    if extracted:
        paragraphs.append(extracted.decode('utf-8'))
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


def _extract_metadata_from_file(storage, file_path):
    """Extracts pageid and title from the first chunk of a Wikipedia JSON file."""
    file = storage.file_open(file_path)
    if not file: return None, None
    try:
        buffer = storage.file_read(file, 0, 1024, decode=True)
        extract_idx = buffer.find('"extract":')
        if extract_idx != -1:
            json_str = buffer[:extract_idx] + '"extract":""}}}}'
            try:
                data = loads(json_str)
                pages = data.get("query", {}).get("pages", {})
                if pages:
                    page = list(pages.values())[0]
                    return page.get("pageid", -1), page.get("title", "")
            except Exception:
                pass
        return None, None
    finally:
        storage.file_close(file)


def _process_http_response(view_manager):
    """Process the HTTP response data in the main thread."""
    global _http_response_data, search_results, _current_request_type, _target_language, current_article_page_id, current_article_title

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
        view_manager.alert(f"API Error: {msg}", back=True)
        change_state(view_manager, STATE_MAIN_MENU)
        return

    if _current_request_type == REQ_LANGLINKS:
        try:
            data = loads(response.text)
            pages = data.get("query", {}).get("pages", {})
            page_data = list(pages.values())[0] if pages else {}
            langlinks = page_data.get("langlinks", [])

            if langlinks:
                new_title = langlinks[0].get("*", "")
                settings["language"] = _target_language
                _target_language = None
                save_settings_to_sd(view_manager)

                if loading_spinner:
                    loading_spinner.text = "Loading translation..."
                fetch_article_by_title(view_manager, new_title)
            else:
                view_manager.alert("No translation available.", back=True)
                _target_language = None
                change_state(view_manager, STATE_LOADING)
                if loading_spinner: loading_spinner.text = "Restoring article..."
                fetch_article(view_manager, current_article_page_id)
        except Exception as e:
            print(f"[ERROR] Langlinks parsing failed: {e}")
            view_manager.alert("Translation failed", back=True)
            _target_language = None
            change_state(view_manager, STATE_LOADING)
            if loading_spinner: loading_spinner.text = "Restoring article..."
            fetch_article(view_manager, current_article_page_id)
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

        cache_path = f"picoware/wikireader/cache_{current_article_page_id}_{url_encode(current_article_title)}.json"
        try:
            if view_manager.storage.exists(cache_path):
                view_manager.storage.remove(cache_path)
            view_manager.storage.rename("picoware/wikireader/temp.json", cache_path)
        except Exception as e:
            print(f"[ERROR] Failed to rename temp cache: {e}")
            cache_path = "picoware/wikireader/temp.json"

        text = _extract_text_from_file(view_manager, cache_path)
        setup_article_view(view_manager, text)
        _add_to_history(view_manager)
        change_state(view_manager, STATE_VIEW_ARTICLE)
        if article_textbox:
            article_textbox.draw_viewer(current_article_title)
        return

    raw_text = response.text.strip() if response and response.text else ""

    # Handle unparsed chunked encoding (DA2\r\n... data ... \r\n0\r\n\r\n)
    if not raw_text.startswith('{') and not raw_text.startswith('['):
        crlf = raw_text.find('\r\n')
        if crlf != -1:
            try:
                # Check if first line is a valid hex size
                int(raw_text[:crlf].split(';')[0].strip(), 16)
                decoded = []
                idx = 0
                while idx < len(raw_text):
                    next_crlf = raw_text.find('\r\n', idx)
                    if next_crlf == -1:
                        break
                    try:
                        chunk_size = int(raw_text[idx:next_crlf].split(';')[0].strip(), 16)
                    except ValueError:
                        break
                    if chunk_size == 0:
                        break
                    start = next_crlf + 2
                    end = start + chunk_size
                    decoded.append(raw_text[start:end])
                    idx = end + 2
                raw_text = "".join(decoded)
                # Guardian RAM Rules: Destroy the heavy string array before dict parsing
                del decoded
                gc.collect()
            except ValueError:
                pass

    try:
        data = loads(raw_text)
        # Guardian RAM Rules: Destroy the raw JSON string immediately after parsing!
        del raw_text
        gc.collect()

        if "query" in data:
            if "search" in data.get("query", {}):
                _parse_search_results(view_manager, data["query"])
            elif "pages" in data.get("query", {}):
                _parse_article_content(view_manager, data["query"])

        # Guardian RAM Rules: Destroy the heavy dictionary after the UI is built
        del data
        gc.collect()
    except Exception as e:
        print(f"[ERROR] Failed to parse API response: {e}")
        view_manager.alert("Invalid API Response", back=True)
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
                    view_manager.storage.remove(f"{directory}/{filename}")
            del entries
        gc.collect()
    except Exception as e:
        print(f"[ERROR] Failed to clear cache: {e}")


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
                    cache_files.append(entry)
            del entries

        if len(cache_files) > limit:
            # Sort by date then time (oldest first)
            cache_files.sort(key=lambda x: (x.get("date", 0), x.get("time", 0)))
            files_to_delete = len(cache_files) - limit
            for i in range(files_to_delete):
                file_to_del = cache_files[i].get("filename", "")
                view_manager.storage.remove(f"{directory}/{file_to_del}")
        del cache_files
        gc.collect()
    except Exception as e:
        print(f"[ERROR] Cache eviction failed: {e}")


def fetch_search_results(view_manager, term):
    """Fetch search results from Wikipedia."""
    global _current_request_type, http_client, settings
    if not http_client:
        return
    _current_request_type = REQ_SEARCH
    encoded_term = url_encode(term)
    gc.collect()
    lang = settings["language"]
    url = f"{WIKI_API_URL.format(lang=lang)}?action=query&list=search&srlimit=15&srsearch={encoded_term}&format=json"
    http_client.get_async(url, headers=WIKI_HEADERS)


def fetch_article(view_manager, page_id):
    """Fetch a single article from Wikipedia."""
    global _current_request_type, http_client, settings, current_article_title, article_textbox

    cache_path = None
    if view_manager.storage and view_manager.has_sd_card:
        try:
            entries = view_manager.storage.read_directory("picoware/wikireader")
            prefix = f"cache_{page_id}_"
            prefix_offline = f"offline_{page_id}_"
            for entry in entries:
                filename = entry.get("filename", "")
                if filename.startswith(prefix_offline) and filename.endswith(".json"):
                    cache_path = f"picoware/wikireader/{filename}"
                    break
                elif filename.startswith(prefix) and filename.endswith(".json") and not cache_path:
                    cache_path = f"picoware/wikireader/{filename}"
            del entries
            # Fallback for old caches
            if not cache_path and view_manager.storage.exists(f"picoware/wikireader/cache_{page_id}.json"):
                cache_path = f"picoware/wikireader/cache_{page_id}.json"
        except Exception: pass

    # Check local SD cache first to bypass network and save RAM
    if cache_path:
        gc.collect()
        text = _extract_text_from_file(view_manager, cache_path)
        setup_article_view(view_manager, text)
        _add_to_history(view_manager)
        change_state(view_manager, STATE_VIEW_ARTICLE)
        if article_textbox:
            article_textbox.draw_viewer(current_article_title)
        return

    if not http_client:
        return
    lang = settings["language"]
    gc.collect()
    exintro = "&exintro=true" if not settings["full_article"] else ""
    url = f"{WIKI_API_URL.format(lang=lang)}?action=query&prop=extracts&explaintext=true&pageids={page_id}{exintro}&format=json"

    # Evict oldest caches (max 9 to leave room for this 1), then route large payloads to SD
    if view_manager.storage and view_manager.has_sd_card:
        _current_request_type = REQ_ARTICLE_FILE
        enforce_cache_limit(view_manager, limit=9)
        http_client.get_async(url, headers=WIKI_HEADERS, save_to_file="picoware/wikireader/temp.json", storage=view_manager.storage)
    else:
        _current_request_type = REQ_ARTICLE_RAM
        http_client.get_async(url, headers=WIKI_HEADERS)


def fetch_article_by_title(view_manager, title):
    """Fetch a target translated article by exactly matched title."""
    global _current_request_type, current_article_title, current_article_page_id, http_client, settings, article_textbox, article_origin_state

    cache_path = None
    if view_manager.storage and view_manager.has_sd_card:
        encoded_title = url_encode(title)
        try:
            entries = view_manager.storage.read_directory("picoware/wikireader")
            suffix = f"_{encoded_title}.json"
            for entry in entries:
                filename = entry.get("filename", "")
                if filename.endswith(suffix):
                    if filename.startswith("offline_"):
                        cache_path = f"picoware/wikireader/{filename}"
                        break
                    elif filename.startswith("cache_") and not cache_path:
                        cache_path = f"picoware/wikireader/{filename}"
            del entries
        except Exception: pass

    if cache_path:
        gc.collect()
        try:
            parts = cache_path.split('/')[-1].replace('.json', '').split('_')
            if len(parts) >= 3:
                current_article_page_id = int(parts[1])
        except Exception: pass
        current_article_title = title

        text = _extract_text_from_file(view_manager, cache_path)
        setup_article_view(view_manager, text)
        _add_to_history(view_manager)
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
    url = f"{WIKI_API_URL.format(lang=lang)}?action=query&prop=extracts&explaintext=true&titles={encoded_title}{exintro}&format=json"

    if view_manager.storage and view_manager.has_sd_card:
        _current_request_type = REQ_ARTICLE_FILE_BY_TITLE
        enforce_cache_limit(view_manager, limit=9)
        http_client.get_async(url, headers=WIKI_HEADERS, save_to_file="picoware/wikireader/temp.json", storage=view_manager.storage)
    else:
        _current_request_type = REQ_ARTICLE_RAM
        http_client.get_async(url, headers=WIKI_HEADERS)

def save_settings_to_sd(view_manager):
    """Saves the settings dictionary to the SD card."""
    global settings
    if view_manager.storage:
        gc.collect()
        try:
            json_str = dumps(settings)
            view_manager.storage.write(SETTINGS_FILE, json_str)
            del json_str
        except Exception as e:
            print(f"[ERROR] Could not save settings: {e}")
        finally:
            gc.collect()


def load_settings_from_sd(view_manager):
    """Loads settings from the SD card if the file exists."""
    global settings
    if view_manager.storage and view_manager.storage.exists(SETTINGS_FILE):
        try:
            content = view_manager.storage.read(SETTINGS_FILE)
            loaded_settings = loads(content)
            settings.update(loaded_settings)
            # Guardian RAM Rules: Clean up loaded strings
            del content
            del loaded_settings
            gc.collect()
        except Exception as e:
            print(f"[ERROR] Could not load or parse settings: {e}")


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
        self.paragraphs = []
        self.line_indices = []
        self.num_lines = 0
        self.top_line = 0

        self.font_size = settings.get("default_font_size", 0)
        font = draw.get_font(self.font_size)
        self.line_height = font.height + 2

        # Define and reserve space for header/footer
        self.header_footer_height = 18
        self.text_area_y = self.y + self.header_footer_height
        self.text_area_height = self.height - (self.header_footer_height * 2)
        self.visible_lines = self.text_area_height // self.line_height

    def cycle_font_size(self):
        """Cycles through available font sizes and re-wraps the text."""
        self.font_size = (self.font_size + 1) % 3  # Cycle through 3 font sizes (0-2)
        font = self.draw.get_font(self.font_size)
        self.line_height = font.height + 2
        self.visible_lines = self.text_area_height // self.line_height
        # Re-wrap text with the new font size
        self._wrap_text()

    def set_text(self, text_data):
        """Handles both strings (RAM fetch) and lists (SD chunked fetch)."""
        if isinstance(text_data, str):
            text_data = _replace_umlauts(text_data)
            lines = text_data.split('\n')
            self.paragraphs = [p + '\n' for p in lines[:-1]]
            if lines[-1]:
                self.paragraphs.append(lines[-1])
        else:
            # Modifying the list in-place to prevent Out-Of-Memory list duplication
            for i in range(len(text_data)):
                text_data[i] = _replace_umlauts(text_data[i])
            self.paragraphs = text_data
        self._wrap_text()

    def _wrap_text(self):
        """Zero-allocation word wrapping: stores chunk index and offsets in raw bytearrays to prevent fragmentation."""
        # Guardian RAM Rules: Clean up previous wrap artifacts before re-allocating
        del self.line_indices[:]
        gc.collect()
        self.line_indices = []
        self.num_lines = 0

        LINES_PER_CHUNK = 200
        BYTES_PER_LINE = 6 # 3 unsigned shorts (H)
        CHUNK_BYTES = LINES_PER_CHUNK * BYTES_PER_LINE
        # Pre-allocate exactly 1200 bytes natively. Bypasses list creation overhead entirely.
        curr_chunk = bytearray(CHUNK_BYTES)
        curr_offset = 0

        font = self.draw.get_font(self.font_size)
        char_width = font.width + font.spacing
        max_w = self.draw.size.x - 10
        # Reduce max_chars by 2 to add a safety buffer for wide characters in proportional fonts
        max_chars = max(1, (max_w // char_width) - 2 if char_width > 0 else 1)

        for p_idx, para in enumerate(self.paragraphs):
            text_len = len(para)
            if text_len == 0:
                continue

            current_line_start = 0
            while current_line_start < text_len:
                if (text_len - current_line_start) <= max_chars:
                    curr_chunk, curr_offset = self._add_line(p_idx, current_line_start, text_len, curr_chunk, curr_offset, CHUNK_BYTES, BYTES_PER_LINE)
                    # Add an empty line for spacing between paragraphs
                    if para.endswith('\n'):
                        curr_chunk, curr_offset = self._add_line(p_idx, text_len, text_len, curr_chunk, curr_offset, CHUNK_BYTES, BYTES_PER_LINE)
                    break

                end_pos = current_line_start + max_chars
                last_space = para.rfind(' ', current_line_start, end_pos + 1)

                if last_space != -1 and last_space >= current_line_start:
                    curr_chunk, curr_offset = self._add_line(p_idx, current_line_start, last_space, curr_chunk, curr_offset, CHUNK_BYTES, BYTES_PER_LINE)
                    current_line_start = last_space + 1
                else:
                    # Word is too long to fit on one line. Force break and leave room for a hyphen.
                    break_pos = current_line_start + max_chars - 1
                    if break_pos <= current_line_start:
                        break_pos = current_line_start + 1
                    curr_chunk, curr_offset = self._add_line(p_idx, current_line_start, break_pos, curr_chunk, curr_offset, CHUNK_BYTES, BYTES_PER_LINE)
                    current_line_start = break_pos

                while current_line_start < text_len and para[current_line_start] == ' ':
                    current_line_start += 1

        if curr_offset > 0:
            # Guardian RAM Rules: Trim the last chunk to avoid wasting up to 1.1KB of unused overallocation
            self.line_indices.append(curr_chunk[:curr_offset])

        self.top_line = 0

        del curr_chunk
        gc.collect()

    def _add_line(self, p, s, e, chunk, offset, chunk_bytes, bytes_per_line):
        chunk[offset:offset+bytes_per_line] = struct.pack('HHH', p, s, e)
        offset += bytes_per_line
        self.num_lines += 1
        if offset >= chunk_bytes:
            self.line_indices.append(chunk)
            return bytearray(chunk_bytes), 0
        return chunk, offset

    def generate_toc(self):
        """Scans the loaded paragraphs to build a table of contents mapping to line indices."""
        toc = []
        last_p_idx = -1
        for i in range(self.num_lines):
            chunk = self.line_indices[i // 200]
            offset = (i % 200) * 6
            p_idx = struct.unpack('H', chunk[offset:offset+2])[0]
            if p_idx != last_p_idx:
                last_p_idx = p_idx
                para = self.paragraphs[p_idx]
                if "==" in para[:5]:
                    para_str = para.strip()
                    if para_str.startswith("==") and para_str.endswith("=="):
                        title = para_str.strip("=").strip()
                        # Guardian RAM Rules: Count '=' natively without string slicing fragmentation
                        level = len(para_str) - len(para_str.lstrip("="))
                        prefix = "  " * (level - 2) if level >= 2 else ""
                        toc.append((prefix + title, i))

        gc.collect()
        return toc

    def jump_to_line(self, line_idx):
        """Jumps the viewer to a specific line index safely."""
        max_top = max(0, self.num_lines - self.visible_lines)
        self.top_line = min(max_top, line_idx)

    def draw_viewer(self, title):
        from picoware.system.vector import Vector

        self.draw.clear(Vector(0, self.y), Vector(self.draw.size.x, self.height), self.bg_color)

        total_lines = self.num_lines
        max_top = max(0, total_lines - self.visible_lines)
        if max_top == 0:
            pct = 100
        else:
            pct = int((self.top_line / max_top) * 100)
            pct = max(0, min(100, pct))
        pct_str = f"{pct}%"

        # Header
        self.draw.fill_rectangle(Vector(0, self.y), Vector(self.draw.size.x, self.header_footer_height), self.theme_color)
        safe_title = _replace_umlauts(title)

        bat_pct = "--"
        try:
            vm = get_view_manager()
            if vm and hasattr(vm, 'input_manager'):
                bat_pct = str(vm.input_manager.battery)
        except Exception: pass

        # Draw reading percentage anchored to the right
        pct_x = self.draw.size.x - self.draw.len(pct_str, 0) - 5
        self.draw.text(Vector(pct_x, self.y + 4), pct_str, self.bg_color, 0)

        # Draw battery anchored to the left of the reading percentage
        bat_str = f"B:{bat_pct}%"
        bat_x = pct_x - self.draw.len(bat_str, 0) - 15
        self.draw.text(Vector(bat_x, self.y + 4), bat_str, self.bg_color, 0)

        # Safely expand title width now that WiFi icon is gone
        self.draw.text(Vector(5, self.y + 4), safe_title[:15], self.bg_color, 0)

        # Text Body
        for i in range(self.visible_lines):
            line_idx = self.top_line + i
            if line_idx < total_lines:
                offset = (line_idx % 200) * 6
                chunk = self.line_indices[line_idx // 200]
                p_idx, start, end = struct.unpack('HHH', chunk[offset:offset+6])
                if start != end:
                    line_str = self.paragraphs[p_idx][start:end]
                    if line_str.endswith('\n'):
                        line_str = line_str[:-1]

                    # Hyphenate if we force-broke a long word
                    para = self.paragraphs[p_idx]
                    if end < len(para) and para[end] not in (' ', '\n') and line_str and not line_str.endswith('-'):
                        line_str += "-"

                    self.draw.text(Vector(5, self.text_area_y + (i * self.line_height) + 2), line_str, self.text_color, self.font_size)

        # Scrollbar
        if max_top > 0:
            scroll_w = 4
            scroll_h = max(10, int((self.visible_lines / total_lines) * self.text_area_height))
            max_scroll_y = self.text_area_height - scroll_h
            scroll_y = self.text_area_y + int((self.top_line / max_top) * max_scroll_y)
            track_x = self.draw.size.x - scroll_w
            self.draw.fill_rectangle(Vector(track_x, scroll_y), Vector(scroll_w, scroll_h), self.theme_color)

        # Footer
        footer_y = self.y + self.height - self.header_footer_height
        self.draw.fill_rectangle(Vector(0, footer_y), Vector(self.draw.size.x, self.header_footer_height), self.theme_color)

        total_pages = max(1, (self.num_lines + self.visible_lines - 1) // self.visible_lines)
        current_page = (self.top_line // self.visible_lines) + 1
        footer_text = f"Pg {current_page}/{total_pages} | F:Fav D:Save T:ToC R:Rld"
        self.draw.text(Vector(5, footer_y + 4), footer_text, self.bg_color, 0)

        self.draw.swap()

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
    global main_menu
    from picoware.gui.menu import Menu

    draw = view_manager.draw
    main_menu = Menu(
        draw,
        "WikiReader",
        0,
        draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
        view_manager.selected_color,
    )
    main_menu.add_item("Search")
    main_menu.add_item("History")
    fav_count = len(settings.get("favorites", []))
    main_menu.add_item(f"Favorites ({fav_count}/50)")
    off_count = len(settings.get("offline", []))
    main_menu.add_item(f"Offline ({off_count}/50)")
    main_menu.add_item("Settings")
    main_menu.add_item("Help")
    main_menu.add_item("Exit")
    main_menu.set_selected(0)
    main_menu.draw()


def setup_search_keyboard(view_manager):
    """Prepare the on-screen keyboard for searching."""
    kb = view_manager.keyboard
    kb.reset()
    kb.title = "Enter search term"
    kb.response = ""
    kb.run(force=True)


def setup_search_results(view_manager):
    """Display the list of search results."""
    global search_results_list
    from picoware.gui.list import List

    draw = view_manager.draw
    search_results_list = List(
        draw,
        0,
        draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
        view_manager.selected_color,
    )
    if not search_results:
        search_results_list.add_item("No results found.")
    else:
        for result in search_results:
            search_results_list.add_item(_replace_umlauts(result["title"]))
    search_results_list.set_selected(0)
    search_results_list.draw()


def setup_article_view(view_manager, text):
    """Create the CustomArticleViewer for viewing an article."""
    global article_textbox

    draw = view_manager.draw
    article_textbox = CustomArticleViewer(
        draw,
        0,
        draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
        view_manager.selected_color,
    )
    article_textbox.set_text(text)

    # Restore reading progress
    prog = 0
    for lst in ("history", "favorites", "offline"):
        for item in settings.get(lst, []):
            if item.get("pageid") == current_article_page_id:
                if "progress" in item:
                    prog = item["progress"]
                    break
        if prog > 0:
            break

    if prog > 0:
        article_textbox.jump_to_line(prog)


def setup_settings(view_manager):
    """Create the settings UI using a Menu."""
    global settings_menu
    from picoware.gui.menu import Menu

    settings_menu = Menu(
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
    global settings_menu, settings
    if not settings_menu: return
    settings_menu.clear()
    settings_menu.add_item(f"Full Article: {'On' if settings['full_article'] else 'Off'}")
    settings_menu.add_item(f"Language: {settings['language']}")
    font_size_str = ["Small", "Medium", "Large"][settings.get("default_font_size", 0)]
    settings_menu.add_item(f"Default Font: {font_size_str}")
    theme_str = settings.get('theme', 'system')
    if theme_str == 'dark': theme_str = 'system'
    settings_menu.add_item(f"Theme: {theme_str[0].upper() + theme_str[1:]}")
    settings_menu.add_item("Clear Data...")
    settings_menu.add_item("Save and Back")
    settings_menu.draw()
    view_manager.draw.swap()


def setup_clear_data(view_manager):
    """Create the clear data submenu."""
    global clear_data_menu, settings
    from picoware.gui.menu import Menu
    clear_data_menu = Menu(
        view_manager.draw,
        "Clear Data",
        0,
        view_manager.draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color,
        view_manager.selected_color,
    )
    clear_data_menu.add_item("Clear Cache")
    clear_data_menu.add_item("Clear History")
    clear_data_menu.add_item("Clear Favorites")
    clear_data_menu.add_item("Clear Offline")
    clear_data_menu.add_item("Clear All Data")
    clear_data_menu.add_item("Back")
    clear_data_menu.set_selected(0)
    clear_data_menu.draw()


def setup_languages(view_manager):
    """Create the language selection list."""
    global languages_list
    from picoware.gui.list import List

    draw = view_manager.draw
    languages_list = List(
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
        languages_list.add_item(lang)

    try:
        selected_index = supported_langs.index(settings["language"])
        languages_list.set_selected(selected_index)
    except ValueError:
        languages_list.set_selected(0)
    languages_list.draw()


def setup_history(view_manager):
    """Create the history selection list."""
    global history_list
    from picoware.gui.list import List

    draw = view_manager.draw
    history_list = List(
        draw, 0, draw.size.y, view_manager.foreground_color,
        view_manager.background_color, view_manager.selected_color
    )
    history = settings.get("history", [])
    if not history:
        history_list.add_item("History is empty.")
    else:
        cached_ids = {}
        storage = view_manager.storage
        has_sd = view_manager.has_sd_card
        if storage and has_sd:
            try:
                entries = storage.read_directory("picoware/wikireader")
                for entry in entries:
                    filename = entry.get("filename", "")
                    if filename.endswith(".json") and (filename.startswith("cache_") or filename.startswith("offline_")):
                        parts = filename.replace('.json', '').split('_')
                        if len(parts) >= 2:
                            cached_ids[int(parts[1])] = True
                del entries
            except Exception: pass

        for item in history:
            title = _replace_umlauts(item["title"])
            pageid = item["pageid"]
            display_text = title
            if pageid in cached_ids:
                display_text = f"[*] {title}"
            history_list.add_item(display_text)
        del cached_ids
    history_list.set_selected(0)
    history_list.draw()


def setup_favorites(view_manager):
    """Create the favorites selection list."""
    global favorites_list
    from picoware.gui.list import List

    draw = view_manager.draw
    favorites_list = List(
        draw, 0, draw.size.y, view_manager.foreground_color,
        view_manager.background_color, view_manager.selected_color
    )
    favorites = settings.get("favorites", [])
    if not favorites:
        favorites_list.add_item("Favorites list is empty (0/50).")
    else:
        cached_ids = {}
        storage = view_manager.storage
        has_sd = view_manager.has_sd_card
        if storage and has_sd:
            try:
                entries = storage.read_directory("picoware/wikireader")
                for entry in entries:
                    filename = entry.get("filename", "")
                    if filename.endswith(".json") and (filename.startswith("cache_") or filename.startswith("offline_")):
                        parts = filename.replace('.json', '').split('_')
                        if len(parts) >= 2:
                            cached_ids[int(parts[1])] = True
                del entries
            except Exception: pass

        for item in favorites:
            title = _replace_umlauts(item["title"])
            pageid = item["pageid"]
            display_text = title
            if pageid in cached_ids:
                display_text = f"[*] {title}"
            favorites_list.add_item(display_text)
        del cached_ids
    favorites_list.set_selected(0)
    favorites_list.draw()


def setup_offline(view_manager):
    """Create the offline selection list."""
    global offline_list
    from picoware.gui.list import List

    draw = view_manager.draw
    offline_list = List(
        draw, 0, draw.size.y, view_manager.foreground_color,
        view_manager.background_color, view_manager.selected_color
    )
    offline = settings.get("offline", [])
    if not offline:
        offline_list.add_item("Offline list is empty (0/50).")
    else:
        # Because they are strictly guaranteed to exist physically,
        # we can safely prefix all of them without directory scanning!
        for item in offline:
            title = _replace_umlauts(item["title"])
            pageid = item["pageid"]
            # Always prepend the indicator so you know it's hard-saved
            display_text = f"[*] {title}"
            offline_list.add_item(display_text)

    offline_list.set_selected(0)
    offline_list.draw()


def setup_toc(view_manager):
    """Create the Table of Contents selection list."""
    global toc_list, toc_data
    from picoware.gui.list import List

    draw = view_manager.draw
    toc_list = List(
        draw, 0, draw.size.y, view_manager.foreground_color,
        view_manager.background_color, view_manager.selected_color
    )

    toc_data = article_textbox.generate_toc() if article_textbox else []
    if not toc_data:
        toc_list.add_item("No sections found.")
    else:
        for title, _ in toc_data:
            toc_list.add_item(title)
    toc_list.set_selected(0)
    toc_list.draw()


def setup_help(view_manager):
    """Create the help screen UI."""
    global help_textbox
    from picoware.gui.textbox import TextBox

    draw = view_manager.draw
    help_textbox = TextBox(
        draw, 0, draw.size.y,
        view_manager.foreground_color,
        view_manager.background_color
    )

    help_text = (
        "WIKI READER MANUAL\n"
        "------------------\n\n"
        "PURPOSE:\n"
        "Search, read & translate\n"
        "Wikipedia articles.\n\n"
        "GLOBAL CONTROLS:\n"
        "[UP/DN] : Scroll Menus\n"
        "[ENTER] : Select Option\n"
        "[BACK]  : Go Back / Exit\n\n"
        "READER CONTROLS:\n"
        "[UP/DN] : Scroll Line\n"
        "[L/R]   : Scroll Page\n"
        "[S] Key : Font Size\n"
        "[L] Key : Language/Translate\n"
        "[T] Key : Table of Contents\n"
        "[D] Key : Save Offline\n"
        "[F] Key : Toggle Favorite\n"
        "[R] Key : Force Reload\n\n"
        "INDICATORS:\n"
        "[*] = Saved to SD Card\n\n"
        "CREDITS:\n"
        "made by Slasher006\n"
        "with the help of GeminiAi."
    )
    help_textbox.set_text(_replace_umlauts(help_text))
    help_textbox.refresh()


# --- State-specific Run Functions ---


def run_main_menu(view_manager):
    """Handle input and drawing for the main menu."""
    global main_menu, settings
    if not main_menu:
        return
    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_UP:
        main_menu.scroll_up()
        inp.reset()
    elif button == BUTTON_DOWN:
        main_menu.scroll_down()
        inp.reset()
    elif button == BUTTON_BACK:
        inp.reset()
        change_state(view_manager, STATE_EXIT)
    elif button == BUTTON_CENTER:
        selected = main_menu.current_item
        inp.reset()
        if selected == "Search":
            change_state(view_manager, STATE_SEARCH_KEYBOARD)
        elif selected == "History":
            change_state(view_manager, STATE_HISTORY)
        elif selected.startswith("Favorites"):
            change_state(view_manager, STATE_FAVORITES)
        elif selected.startswith("Offline"):
            change_state(view_manager, STATE_OFFLINE)
        elif selected == "Settings":
            change_state(view_manager, STATE_SETTINGS)
        elif selected == "Help":
            change_state(view_manager, STATE_HELP)
        elif selected == "Exit":
            change_state(view_manager, STATE_EXIT)


def run_search_keyboard(view_manager):
    """Handle the search input keyboard."""
    global loading_spinner
    kb = view_manager.keyboard
    if not kb.run():  # run() returns False when BACK is pressed
        change_state(view_manager, STATE_MAIN_MENU)
        return

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


def run_loading(view_manager):
    """Display the loading animation."""
    global http_client, _http_response_data, current_state, _request_start_time, _http_lock, loading_spinner

    _process_http_response(view_manager)

    if current_state == STATE_LOADING:
        if ticks_diff(ticks_ms(), _request_start_time) > 10000:
            print("[ERROR] Request timed out after 10 seconds.")
            if http_client:
                http_client.close()
                del http_client

            from picoware.system.http import HTTP
            http_client = HTTP(thread_manager=view_manager.thread_manager, chunk_size=8 * 1024)
            http_client.callback = _api_callback

            if _http_lock:
                _http_lock.acquire()
                try:
                    _http_response_data = None
                finally:
                    _http_lock.release()

            gc.collect()
            view_manager.alert("Request timed out!", back=True)
            change_state(view_manager, STATE_MAIN_MENU)
            return

        if loading_spinner:
            loading_spinner.animate()


def run_search_results(view_manager):
    """Handle the search results list."""
    global current_article_title, current_article_page_id, article_origin_state, search_results_list, search_results, loading_spinner
    if not search_results_list:
        return
    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_UP:
        search_results_list.scroll_up()
        inp.reset()
    elif button == BUTTON_DOWN:
        search_results_list.scroll_down()
        inp.reset()
    elif button == BUTTON_BACK:
        inp.reset()
        change_state(view_manager, STATE_MAIN_MENU)
    elif button == BUTTON_CENTER:
        if search_results:
            selected_index = search_results_list.selected_index
            selected_article = search_results[selected_index]
            current_article_title = selected_article["title"]
            current_article_page_id = selected_article["pageid"]
            inp.reset()

            article_origin_state = STATE_SEARCH_RESULTS
            change_state(view_manager, STATE_LOADING)
            if loading_spinner:
                loading_spinner.text = _replace_umlauts(f"Loading '{current_article_title}'...")
            fetch_article(view_manager, current_article_page_id)


def run_view_article(view_manager):
    """Handle the article reading view."""
    global language_menu_origin_state, article_textbox, current_article_title, current_article_page_id
    if not article_textbox:
        return
    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_UP:
        article_textbox.scroll_up(2)
        article_textbox.draw_viewer(current_article_title)
        inp.reset()
    elif button == BUTTON_DOWN:
        article_textbox.scroll_down(2)
        article_textbox.draw_viewer(current_article_title)
        inp.reset()
    elif button == BUTTON_LEFT:
        article_textbox.page_up()
        article_textbox.draw_viewer(current_article_title)
        inp.reset()
    elif button == BUTTON_RIGHT:
        article_textbox.page_down()
        article_textbox.draw_viewer(current_article_title)
        inp.reset()
    elif button == BUTTON_BACK:
        inp.reset()
        change_state(view_manager, article_origin_state)
    elif button == BUTTON_S:
        article_textbox.cycle_font_size()
        article_textbox.draw_viewer(current_article_title)
        inp.reset()
    elif button == BUTTON_L:
        language_menu_origin_state = STATE_VIEW_ARTICLE
        change_state(view_manager, STATE_LANGUAGES)
        inp.reset()
    elif button == BUTTON_F:
        inp.reset()
        _toggle_favorite(view_manager)
        if article_textbox:
            article_textbox.draw_viewer(current_article_title)
    elif button == BUTTON_D:
        inp.reset()
        _toggle_offline(view_manager)
        if article_textbox:
            article_textbox.draw_viewer(current_article_title)
    elif button in (BUTTON_CENTER, BUTTON_T):
        inp.reset()
        change_state(view_manager, STATE_TOC)
    elif button == BUTTON_R:
        inp.reset()
        # Force reload by deleting the cache file first if it exists
        if view_manager.storage and view_manager.has_sd_card:
            try:
                entries = view_manager.storage.read_directory("picoware/wikireader")
                prefix = f"cache_{current_article_page_id}_"
                for entry in entries:
                    filename = entry.get("filename", "")
                    if filename.startswith(prefix) and filename.endswith(".json"):
                        try: view_manager.storage.remove(f"picoware/wikireader/{filename}")
                        except Exception: pass
                del entries
                # Fallback for old legacy caches
                try: view_manager.storage.remove(f"picoware/wikireader/cache_{current_article_page_id}.json")
                except Exception: pass
            except Exception as e:
                print(f"[ERROR] Failed to delete cache for reload: {e}")
        change_state(view_manager, STATE_LOADING)
        if loading_spinner: loading_spinner.text = "Reloading..."
        fetch_article(view_manager, current_article_page_id)


def run_settings(view_manager):
    """Handle the settings menu."""
    global language_menu_origin_state, settings_menu, settings
    if not settings_menu:
        return
    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_UP:
        settings_menu.scroll_up()
        inp.reset()
    elif button == BUTTON_DOWN:
        settings_menu.scroll_down()
        inp.reset()
    elif button == BUTTON_BACK:
        inp.reset()
        # Don't save on back
        change_state(view_manager, STATE_MAIN_MENU)
    elif button == BUTTON_CENTER:
        inp.reset()
        selected_index = settings_menu.selected_index
        if selected_index == 0:  # Full Article
            settings["full_article"] = not settings["full_article"]
            _refresh_settings_menu_items(view_manager)
        elif selected_index == 1:  # Language
            language_menu_origin_state = STATE_SETTINGS
            change_state(view_manager, STATE_LANGUAGES)
        elif selected_index == 2:  # Font Size
            settings["default_font_size"] = (settings.get("default_font_size", 0) + 1) % 3
            _refresh_settings_menu_items(view_manager)
        elif selected_index == 3:  # Theme
            current_theme = settings.get('theme', 'system')
            try:
                idx = THEMES.index(current_theme)
            except ValueError:
                idx = 0
            settings['theme'] = THEMES[(idx + 1) % len(THEMES)]
            _apply_theme(view_manager)
            change_state(view_manager, STATE_SETTINGS)
            if settings_menu:
                settings_menu.set_selected(3)
                settings_menu.draw()
                view_manager.draw.swap()
        elif selected_index == 4:  # Clear Data...
            change_state(view_manager, STATE_CLEAR_DATA)
        elif selected_index == 5:  # Save and Back
            save_settings_to_sd(view_manager)
            change_state(view_manager, STATE_MAIN_MENU)


def run_clear_data(view_manager):
    """Handle the clear data submenu."""
    global clear_data_menu, settings
    if not clear_data_menu:
        return
    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_UP:
        clear_data_menu.scroll_up()
        inp.reset()
    elif button == BUTTON_DOWN:
        clear_data_menu.scroll_down()
        inp.reset()
    elif button == BUTTON_BACK:
        inp.reset()
        change_state(view_manager, STATE_SETTINGS)
    elif button == BUTTON_CENTER:
        inp.reset()
        selected_index = clear_data_menu.selected_index
        if selected_index == 0:  # Clear Cache
            clear_cache(view_manager)
            show_toast(view_manager, "Cache cleared successfully!", 1)
            view_manager.clear()
            clear_data_menu.draw()
            view_manager.draw.swap()
        elif selected_index == 1:  # Clear History
            settings["history"] = []
            save_settings_to_sd(view_manager)
            show_toast(view_manager, "History cleared successfully!", 1)
            view_manager.clear()
            clear_data_menu.draw()
            view_manager.draw.swap()
        elif selected_index == 2:  # Clear Favorites
            settings["favorites"] = []
            save_settings_to_sd(view_manager)
            show_toast(view_manager, "Favorites cleared successfully!", 1)
            view_manager.clear()
            clear_data_menu.draw()
            view_manager.draw.swap()
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
                except Exception: pass
            settings["offline"] = []
            save_settings_to_sd(view_manager)
            show_toast(view_manager, "Offline files deleted!", 1)
            view_manager.clear()
            clear_data_menu.draw()
            view_manager.draw.swap()
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
                except Exception: pass
            settings["history"] = []
            settings["favorites"] = []
            settings["offline"] = []
            save_settings_to_sd(view_manager)
            show_toast(view_manager, "All data cleared!", 1)
            view_manager.clear()
            clear_data_menu.draw()
            view_manager.draw.swap()
        elif selected_index == 5:  # Back
            change_state(view_manager, STATE_SETTINGS)


def run_languages(view_manager):
    """Handle the language selection list."""
    global _target_language, _current_request_type, languages_list, settings, language_menu_origin_state, loading_spinner, http_client, current_article_page_id
    if not languages_list:
        return
    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_UP:
        languages_list.scroll_up()
        inp.reset()
    elif button == BUTTON_DOWN:
        languages_list.scroll_down()
        inp.reset()
    elif button == BUTTON_BACK:
        inp.reset()
        if language_menu_origin_state == STATE_VIEW_ARTICLE:
            change_state(view_manager, STATE_LOADING)
            if loading_spinner:
                loading_spinner.text = "Restoring article..."
            fetch_article(view_manager, current_article_page_id)
        else:
            change_state(view_manager, language_menu_origin_state)
    elif button == BUTTON_CENTER:
        new_lang = languages_list.current_item
        old_lang = settings["language"]
        inp.reset()
        if language_menu_origin_state == STATE_VIEW_ARTICLE and new_lang != old_lang:
            _target_language = new_lang
            change_state(view_manager, STATE_LOADING)
            if loading_spinner:
                loading_spinner.text = f"Locating in {new_lang}..."

            _current_request_type = REQ_LANGLINKS
            url = f"{WIKI_API_URL.format(lang=old_lang)}?action=query&prop=langlinks&lllang={new_lang}&pageids={current_article_page_id}&format=json"
            http_client.get_async(url, headers=WIKI_HEADERS)
        elif new_lang != old_lang:
            settings["language"] = new_lang
            change_state(view_manager, language_menu_origin_state)
        else:
            if language_menu_origin_state == STATE_VIEW_ARTICLE:
                change_state(view_manager, STATE_LOADING)
                if loading_spinner: loading_spinner.text = "Restoring article..."
                fetch_article(view_manager, current_article_page_id)
            else:
                change_state(view_manager, language_menu_origin_state)


def run_history(view_manager):
    """Handle the history list."""
    global current_article_title, current_article_page_id, article_origin_state, history_list, settings, loading_spinner
    if not history_list:
        return
    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_UP:
        history_list.scroll_up()
        inp.reset()
    elif button == BUTTON_DOWN:
        history_list.scroll_down()
        inp.reset()
    elif button == BUTTON_BACK:
        inp.reset()
        change_state(view_manager, STATE_MAIN_MENU)
    elif button == BUTTON_CENTER:
        inp.reset()
        history = settings.get("history", [])
        if history and history_list.selected_index < len(history):
            item = history[history_list.selected_index]
            current_article_title = item["title"]
            current_article_page_id = item["pageid"]
            article_origin_state = STATE_HISTORY
            change_state(view_manager, STATE_LOADING)
            if loading_spinner:
                loading_spinner.text = _replace_umlauts(f"Loading '{current_article_title}'...")
            fetch_article(view_manager, current_article_page_id)


def run_favorites(view_manager):
    """Handle the favorites list."""
    global current_article_title, current_article_page_id, article_origin_state, favorites_list, settings, loading_spinner
    if not favorites_list:
        return
    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_UP:
        favorites_list.scroll_up()
        inp.reset()
    elif button == BUTTON_DOWN:
        favorites_list.scroll_down()
        inp.reset()
    elif button == BUTTON_BACK:
        inp.reset()
        change_state(view_manager, STATE_MAIN_MENU)
    elif button == BUTTON_CENTER:
        inp.reset()
        favorites = settings.get("favorites", [])
        if favorites and favorites_list.selected_index < len(favorites):
            item = favorites[favorites_list.selected_index]
            current_article_title = item["title"]
            current_article_page_id = item["pageid"]
            article_origin_state = STATE_FAVORITES
            change_state(view_manager, STATE_LOADING)
            if loading_spinner:
                loading_spinner.text = _replace_umlauts(f"Loading '{current_article_title}'...")
            fetch_article(view_manager, current_article_page_id)


def run_offline(view_manager):
    """Handle the offline articles list."""
    global current_article_title, current_article_page_id, article_origin_state, offline_list, settings, loading_spinner
    if not offline_list:
        return
    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_UP:
        offline_list.scroll_up()
        inp.reset()
    elif button == BUTTON_DOWN:
        offline_list.scroll_down()
        inp.reset()
    elif button == BUTTON_BACK:
        inp.reset()
        change_state(view_manager, STATE_MAIN_MENU)
    elif button == BUTTON_CENTER:
        inp.reset()
        offline = settings.get("offline", [])
        if offline and offline_list.selected_index < len(offline):
            item = offline[offline_list.selected_index]
            current_article_title = item["title"]
            current_article_page_id = item["pageid"]
            article_origin_state = STATE_OFFLINE
            change_state(view_manager, STATE_LOADING)
            if loading_spinner:
                loading_spinner.text = _replace_umlauts(f"Loading '{current_article_title}'...")
            fetch_article(view_manager, current_article_page_id)


def run_toc(view_manager):
    """Handle the Table of Contents list."""
    global toc_list, toc_data, article_textbox, current_article_title
    if not toc_list:
        return
    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_UP:
        toc_list.scroll_up()
        inp.reset()
    elif button == BUTTON_DOWN:
        toc_list.scroll_down()
        inp.reset()
    elif button == BUTTON_BACK:
        inp.reset()
        change_state(view_manager, STATE_VIEW_ARTICLE)
        if article_textbox:
            article_textbox.draw_viewer(current_article_title)
    elif button == BUTTON_CENTER:
        inp.reset()
        if toc_data and toc_list.selected_index < len(toc_data):
            target_line = toc_data[toc_list.selected_index][1]
            change_state(view_manager, STATE_VIEW_ARTICLE)
            if article_textbox:
                article_textbox.jump_to_line(target_line)
                article_textbox.draw_viewer(current_article_title)


def run_help(view_manager):
    """Handle the Help screen."""
    global help_textbox
    if not help_textbox:
        return
    inp = view_manager.input_manager
    button = inp.button

    if button == BUTTON_UP:
        help_textbox.scroll_up()
        inp.reset()
    elif button == BUTTON_DOWN:
        help_textbox.scroll_down()
        inp.reset()
    elif button == BUTTON_BACK:
        inp.reset()
        change_state(view_manager, STATE_MAIN_MENU)

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
    loading_spinner = Loading(
        view_manager.draw,
        view_manager.selected_color,
        view_manager.background_color,
    )

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
    global http_client, loading_spinner, main_menu, search_results_list, settings_menu, settings, language_menu_origin_state, clear_data_menu, _sys_bg, _sys_fg, article_textbox, languages_list, _vm_ref, _http_lock, _pending_action, _target_language, history_list, favorites_list, offline_list, toc_list, help_textbox, article_origin_state, _request_start_time
    if http_client:
        http_client.close()
        # Give the background thread a moment to exit
        sleep(0.1)
        del http_client
        http_client = None
    if loading_spinner:
        del loading_spinner
        loading_spinner = None
    if main_menu:
        del main_menu
        main_menu = None
    if search_results_list:
        del search_results_list
        search_results_list = None
    if article_textbox:
        del article_textbox
        article_textbox = None
    if settings_menu:
        del settings_menu
        settings_menu = None
    if languages_list:
        del languages_list
        languages_list = None
    if history_list:
        del history_list
        history_list = None
    if favorites_list:
        del favorites_list
        favorites_list = None
    if offline_list:
        del offline_list
        offline_list = None
    if toc_list:
        del toc_list
        toc_list = None
    if help_textbox:
        del help_textbox
        help_textbox = None
    if clear_data_menu:
        del clear_data_menu
        clear_data_menu = None

    # Save settings after cleaning up all large UI objects to prevent MemoryError
    save_settings_to_sd(view_manager)

    # Clear the reference
    _vm_ref = None
    if _http_lock:
        del _http_lock
        _http_lock = None
    _pending_action = None
    language_menu_origin_state = STATE_MAIN_MENU
    _target_language = None
    article_origin_state = STATE_SEARCH_RESULTS

    # Restore the original system colors before wiping the cache
    if _sys_bg is not None:
        view_manager.background_color = _sys_bg
    if _sys_fg is not None:
        view_manager.foreground_color = _sys_fg

    _sys_bg = None
    _sys_fg = None
    _request_start_time = 0

    # Guarantee the heap is swept clean for the next app
    gc.collect()



def run(view_manager):
    """Called repeatedly while the application is running."""
    global current_state
    if current_state == STATE_EXIT:
        current_state = STATE_INIT  # Prevent infinite loop of back() calls
        view_manager.back(True, False, True)  # Exit without clearing screen to black
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
    elif current_state == STATE_HISTORY:
        run_history(view_manager)
    elif current_state == STATE_FAVORITES:
        run_favorites(view_manager)
    elif current_state == STATE_OFFLINE:
        run_offline(view_manager)
    elif current_state == STATE_TOC:
        run_toc(view_manager)
    elif current_state == STATE_HELP:
        run_help(view_manager)
    elif current_state == STATE_CLEAR_DATA:
        run_clear_data(view_manager)

from picoware.system.view_manager import ViewManager
from picoware.system.view import View

vm = None

try:
    vm = ViewManager()
    vm.add(
        View(
            "app_tester",
            run,
            start,
            stop,
        )
    )
    vm.switch_to("app_tester")
    while True:
        vm.run()
except Exception as e:
    print("Error during testing:", e)
finally:
    del vm
    vm = None