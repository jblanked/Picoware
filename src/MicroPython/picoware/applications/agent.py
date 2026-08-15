"""Picoware Agent - LLM-powered assistant with chat GUI."""
import micropython
from utime import ticks_diff, ticks_ms
from picoware.system.buttons import (
    BUTTON_UP, BUTTON_DOWN, BUTTON_CENTER, BUTTON_BACK, BUTTON_TAB,
)
from picoware.system.colors import TFT_WHITE, TFT_DARKGREY, TFT_LIGHTGREY, TFT_GREEN

STATE_MENU = micropython.const(0)
STATE_CHAT = micropython.const(1)
STATE_TYPE = micropython.const(2)
STATE_SETTINGS = micropython.const(3)
STATE_SETTINGS_PROVIDER = micropython.const(4)
STATE_SETTINGS_MODEL = micropython.const(5)
STATE_SETTINGS_INTEGRATION = micropython.const(6)
STATE_WAITING = micropython.const(7)
STATE_SETTINGS_SCAN = micropython.const(8)

ACTIVITY_FRAME_MS = micropython.const(250)
ACTIVITY_SEGMENTS = micropython.const(8)

_agent          = None
_menu           = None
_state          = STATE_MENU
_conversation   = None
_mode_label     = ""
_agent_mode     = None
_scroll_offset  = 0
_max_scroll     = 0
_settings_menu  = None
_settings       = None
_choice         = None
_integration_ids = None
_integration_toggle_list = None
_agent_task      = None
_pending_result  = None
_pending_error   = ""
_pending_done    = False
_last_phase      = ""
_activity_started_ms = 0
_activity_last_ms = 0
_activity_frame  = 0
_chat_cache      = None
_chat_cache_key  = None
_scan_agent       = None
_scan_task        = None
_scan_result      = None
_scan_error       = ""
_scan_done        = False


@micropython.native
def _wrap_text(text: str, max_chars: int):
    """Wrap text to max_chars per line, preserving words.

    Args:
        text (str): The text to wrap.
        max_chars (int): Maximum characters per line.

    Returns:
        list: Wrapped lines of text.
    """
    if not text:
        return [""]
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        cur = ""
        for w in words:
            if len(w) > max_chars:
                if cur:
                    lines.append(cur)
                    cur = ""
                for i in range(0, len(w), max_chars):
                    lines.append(w[i:i + max_chars])
                continue
            trial = (cur + " " + w) if cur else w
            if len(trial) <= max_chars:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
    return lines if lines else [""]


def _chat_layout(view_manager):
    """Return layout metrics derived from screen size and default font.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        tuple: Header/prompt/chat geometry and font metrics.
    """
    draw = view_manager.draw
    w, h = draw.size.x, draw.size.y

    font = draw.get_font(draw.font)

    header_h = max(22, h * 8 // 100)
    # Keep the shortcut bar only tall enough for one readable text line.  The
    # old 11% footer used 35 px on PicoCalc and needlessly hid chat content.
    prompt_h = max(font.height + 6, h * 7 // 100)
    chat_y   = header_h + 2
    chat_h   = h - header_h - prompt_h - 4

    bubble_w = w * 78 // 100
    pad      = max(4, w // 60)
    text_w   = bubble_w - pad * 2
    char_w   = font.width + font.spacing
    max_chars = text_w // char_w if char_w > 0 else 30

    return header_h, prompt_h, chat_y, chat_h, max_chars, font, bubble_w, pad


@micropython.native
def _draw_bubble(draw, x, y, w, text_lines, font, bg_color, text_color, pad,
                  clip_top=0):
    """Draw a rounded-rect bubble clipped to screen bounds.

    Args:
        draw (Draw): The drawing context.
        x (int): Left position of the bubble.
        y (int): Top position of the bubble.
        w (int): Width of the bubble.
        text_lines (list): Lines of text to draw.
        font (Font): The font to use.
        bg_color (int): Bubble background color.
        text_color (int): Text color.
        pad (int): Inner padding in pixels.
        clip_top (int): Y position to clip lines above. Defaults to 0.

    Returns:
        int: The next Y position after the bubble.
    """
    line_h = font.height + 3
    screen_h = draw.size.y

    # Clip top -- skip lines above clip_top (e.g. under the header)
    if y < clip_top:
        skip = (clip_top - y + line_h - 1) // line_h
        if skip >= len(text_lines):
            return y
        text_lines = text_lines[skip:]
        y = clip_top

    bubble_h = line_h * len(text_lines) + pad * 2

    if y >= screen_h or bubble_h <= 0:
        return y
    if y + bubble_h > screen_h:
        bubble_h = screen_h - y

    draw._fill_round_rectangle(x, y, w, bubble_h, 6, bg_color)

    ty = y + pad
    for line in text_lines:
        if ty + line_h > screen_h:
            break
        draw._text(x + pad, ty, line, text_color, font.size)
        ty += line_h

    return y + bubble_h + 4

@micropython.native
def _render_chat(view_manager):
    """Draw conversation as chat bubbles with scroll and prompt bar.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    draw = view_manager.draw
    w, h = draw.size.x, draw.size.y
    bg  = view_manager.background_color
    sel = view_manager.selected_color

    header_h, prompt_h, chat_y, chat_h, max_chars, font, bubble_w, pad = \
        _chat_layout(view_manager)

    global _scroll_offset, _max_scroll, _chat_cache, _chat_cache_key

    draw.fill_screen(bg)

    # Header
    draw._fill_rectangle(0, 0, w, header_h, sel)
    draw._text(pad, (header_h - font.height) // 2,
               _mode_label, TFT_WHITE, font.size)
    if _conversation:
        draw._text(w - pad - font.width * 2, (header_h - font.height) // 2,
                   "++" if _scroll_offset > 0 else "  ", TFT_DARKGREY, font.size)

    # Wrapping is expensive on Pico; reuse it while only the scroll changes.
    cache_key = (id(_conversation), len(_conversation), max_chars)
    if _chat_cache_key != cache_key:
        all_lines = []
        for msg in _conversation:
            wrapped = _wrap_text(msg["content"], max_chars)
            is_user = (msg["role"] == "user")
            for line in wrapped:
                all_lines.append((line, is_user))
            all_lines.append(("", None))
        if all_lines and all_lines[-1][1] is None:
            all_lines.pop()
        _chat_cache = all_lines
        _chat_cache_key = cache_key
    else:
        all_lines = _chat_cache

    # Content height
    line_h  = font.height + 3
    gap_h   = pad * 2 + 4
    total_h = 0
    i = 0
    while i < len(all_lines):
        line_text, is_user = all_lines[i]
        if is_user is None:
            total_h += 6
            i += 1
            continue
        j = i
        while j < len(all_lines) and all_lines[j][1] == is_user:
            j += 1
        total_h += line_h * (j - i) + gap_h
        i = j

    _max_scroll = max(0, total_h - chat_h) // line_h if line_h else 0
    _scroll_offset = min(_scroll_offset, _max_scroll)
    _scroll_offset = max(_scroll_offset, 0)

    # Draw bubbles
    scroll_px = _scroll_offset * line_h
    cur_y = chat_y - scroll_px

    i = 0
    while i < len(all_lines):
        line_text, is_user = all_lines[i]
        if is_user is None:
            cur_y += 6
            i += 1
            continue

        j = i
        while j < len(all_lines) and all_lines[j][1] == is_user:
            j += 1
        block = [t for t, _ in all_lines[i:j]]

        block_h = line_h * len(block) + gap_h
        visible = (cur_y + block_h > chat_y) and (cur_y < chat_y + chat_h)

        if visible:
            if is_user:
                bx = w - bubble_w - pad
            else:
                bx = pad
            _draw_bubble(draw, bx, cur_y, bubble_w, block, font,
                         view_manager.selected_color if is_user else TFT_DARKGREY,
                         TFT_WHITE, pad, clip_top=chat_y)

        cur_y += block_h
        i = j

    # Prompt bar
    bar_y = h - prompt_h
    draw._fill_rectangle(0, bar_y, w, prompt_h, TFT_DARKGREY)
    prompt = "OK=Type  TAB=New  BACK=Menu"
    pw = draw.len(prompt)
    draw._text((w - pw) // 2, bar_y + (prompt_h - font.height) // 2,
               prompt, TFT_LIGHTGREY, font.size)

    draw.swap()


def _show_thinking(
    view_manager,
    phase: str = "Preparing",
    frame: int = 0,
    elapsed_seconds: int = 0,
):
    """Display one frame of the non-blocking Agent activity indicator.

    Args:
        view_manager (ViewManager): The view manager context.
        phase (str): Current Agent execution phase.
        frame (int): Highlighted activity-bar segment.
        elapsed_seconds (int): Seconds since the request started.
    """
    draw = view_manager.draw
    w, h = draw.size.x, draw.size.y
    bg = view_manager.background_color
    fg = view_manager.foreground_color
    active = view_manager.selected_color

    draw.fill_screen(bg)
    msg = phase or "Working..."
    if len(msg) > 28:
        msg = msg[:25] + "..."
    fh = draw.font_size.y

    title = "Request in progress"
    draw._text((w - draw.len(title)) // 2, h // 5, title, fg, draw.font)
    draw._text((w - draw.len(msg)) // 2, h // 2 - fh * 2, msg, fg, draw.font)

    # This is deliberately indeterminate: movement proves the UI is alive
    # without suggesting a completion percentage the model cannot provide.
    bar_w = min(w * 2 // 3, 192)
    gap = max(2, w // 160)
    segment_w = (bar_w - gap * (ACTIVITY_SEGMENTS - 1)) // ACTIVITY_SEGMENTS
    bar_x = (w - bar_w) // 2
    bar_y = h // 2
    for index in range(ACTIVITY_SEGMENTS):
        distance = (frame - index) % ACTIVITY_SEGMENTS
        color = active if distance < 2 else TFT_DARKGREY
        draw._fill_rectangle(
            bar_x + index * (segment_w + gap),
            bar_y,
            segment_w,
            max(5, fh // 2),
            color,
        )

    alive = "Still working - " + str(elapsed_seconds) + "s"
    draw._text(
        (w - draw.len(alive)) // 2,
        bar_y + fh + 4,
        alive,
        TFT_LIGHTGREY,
        draw.font,
    )
    cancel = "BACK=Cancel"
    draw._text(
        (w - draw.len(cancel)) // 2,
        h - fh - 6,
        cancel,
        TFT_LIGHTGREY,
        draw.font,
    )
    draw.swap()


def _start_activity(view_manager, phase: str) -> None:
    """Initialize and draw an indeterminate activity animation."""
    global _last_phase, _activity_started_ms, _activity_last_ms, _activity_frame
    now = ticks_ms()
    _last_phase = phase
    _activity_started_ms = now
    _activity_last_ms = now
    _activity_frame = 0
    _show_thinking(view_manager, phase, 0, 0)


def _animate_activity(view_manager, phase: str) -> None:
    """Advance the activity display at a bounded refresh rate."""
    global _last_phase, _activity_last_ms, _activity_frame
    now = ticks_ms()
    phase = phase or "Working..."
    if (
        phase == _last_phase
        and ticks_diff(now, _activity_last_ms) < ACTIVITY_FRAME_MS
    ):
        return
    _last_phase = phase
    _activity_last_ms = now
    _activity_frame = (_activity_frame + 1) % ACTIVITY_SEGMENTS
    elapsed = max(0, ticks_diff(now, _activity_started_ms)) // 1000
    _show_thinking(view_manager, phase, _activity_frame, elapsed)


def _agent_worker(payload) -> None:
    """Run the complete multi-request Agent loop away from the UI thread."""
    global _pending_result, _pending_error, _pending_done
    try:
        _pending_result = _agent.run_payload(payload)
        _pending_error = ""
    except Exception as exc:
        _pending_result = None
        _pending_error = str(exc)
    finally:
        _pending_done = True


def _start_agent_request(view_manager, user_text: str) -> bool:
    """Queue one Agent request on Picoware's shared thread manager."""
    global _agent_task, _pending_result, _pending_error, _pending_done
    global _state, _last_phase, _chat_cache, _chat_cache_key
    from picoware.system.thread import ThreadTask
    from gc import collect

    manager = view_manager.thread_manager
    if manager is None:
        return False
    # Wrapped display lines can be rebuilt after the request. Releasing them
    # here leaves the maximum heap available for HTTP/MCP parsing.
    _chat_cache = None
    _chat_cache_key = None
    collect()
    _pending_result = None
    _pending_error = ""
    _pending_done = False
    _agent_task = ThreadTask(
        "Agent",
        function=_agent_worker,
        args=({"message": user_text, "conversation": list(_conversation)},),
        timeout=190000,
        stack_size=64 * 1024,
    )
    manager.add_task(_agent_task)
    _state = STATE_WAITING
    _start_activity(view_manager, "Preparing")
    return True


def _finish_agent_request(view_manager) -> None:
    """Commit one background result to the visible conversation exactly once."""
    global _conversation, _state, _scroll_offset, _agent_task
    global _pending_result, _pending_error, _pending_done
    if _pending_result is not None:
        _conversation = _pending_result.get("conversation", _conversation)
    elif _pending_error:
        _conversation.append({"role": "assistant", "content": "Error: " + _pending_error})
    _pending_result = None
    _pending_error = ""
    _pending_done = False
    _agent_task = None
    _scroll_offset = 32767
    _state = STATE_CHAT
    _render_chat(view_manager)

def _set_settings(view_manager):
    """Load or create the agent settings.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    global _settings
    s = view_manager.storage
    if not s.exists("picoware/settings/current_agent.json"):
        from picoware.system.agent.llm import DEEPSEEK, LLM
        _settings = {
            "model": LLM(view_manager.storage, DEEPSEEK).model,
            "provider": DEEPSEEK
        }
        _save_settings(view_manager)
    else:
        _settings = s.serialize("picoware/settings/current_agent.json")

def _save_settings(view_manager) -> bool:
    """Persist the current agent settings to storage.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: True on success.
    """
    if _settings is None:
        return False
    s = view_manager.storage
    return s.deserialize(_settings, "picoware/settings/current_agent.json")

def _get_llm_providers() -> list:
    """Return a list of available LLM providers."""
    from picoware.system.agent.llm import LLM
    return LLM.providers()

def _get_llm_models(view_manager, llm_id: int) -> list:
    """Return a list of models for the specified LLM provider.

    Args:
        view_manager (ViewManager): The view manager context.
        llm_id (int): The provider ID.

    Returns:
        list: Available model names.
    """
    from picoware.system.agent.llm import LLM
    return LLM(view_manager.storage, llm_id).models

def _start_settings_menu(view_manager):
    """Show the agent settings menu.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    from picoware.gui.menu import Menu
    global _state, _settings_menu
    _state = STATE_SETTINGS
    if _settings_menu is not None:
        _settings_menu.draw()
        return
    _settings_menu = Menu(
        view_manager.draw,
        "Settings",
        0,
        view_manager.draw.size.y,
        text_color=view_manager.foreground_color,
        background_color=view_manager.background_color,
        selected_color=view_manager.selected_color,
    )
    _settings_menu.add_item("Agent Provider")
    _settings_menu.add_item("Agent Model")
    _settings_menu.add_item("Scan Integrations")
    _settings_menu.draw()


def _open_provider_choice(view_manager):
    """Open a Choice sub-view for selecting the LLM provider.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    global _state, _choice
    from picoware.gui.choice import Choice
    from picoware.system.vector import Vector
    from picoware.system.agent.llm import LLM

    draw = view_manager.draw
    draw.fill_screen(view_manager.background_color)
    if _choice is not None:
        del _choice
        _choice = None

    provider_ids = _get_llm_providers()
    provider_names = [LLM.provider_name(pid) for pid in provider_ids]
    current_provider = _settings["provider"]
    try:
        initial_idx = provider_ids.index(current_provider)
    except ValueError:
        initial_idx = 0

    _choice = Choice(
        draw,
        Vector(0, 0),
        draw.size,
        "Agent Provider",
        provider_names,
        initial_idx,
        view_manager.foreground_color,
        view_manager.background_color,
    )
    _choice.draw()
    _state = STATE_SETTINGS_PROVIDER


def _open_model_choice(view_manager):
    """Open a Choice sub-view for selecting the LLM model.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    global _state, _choice
    from picoware.gui.choice import Choice
    from picoware.system.vector import Vector

    draw = view_manager.draw
    draw.fill_screen(view_manager.background_color)
    if _choice is not None:
        del _choice
        _choice = None

    models = _get_llm_models(view_manager, _settings["provider"])
    current_model = _settings["model"]
    try:
        initial_idx = models.index(current_model)
    except ValueError:
        initial_idx = 0

    _choice = Choice(
        draw,
        Vector(0, 0),
        draw.size,
        "Agent Model",
        models,
        initial_idx,
        view_manager.foreground_color,
        view_manager.background_color,
    )
    _choice.draw()
    _state = STATE_SETTINGS_MODEL


def _integration_scan_worker(scanner) -> None:
    """Scan LM Studio integrations outside the UI thread."""
    global _scan_result, _scan_error, _scan_done
    try:
        _scan_result, _scan_error = scanner.scan_integrations()
    except Exception as exc:
        message = str(exc)
        if len(message) > 120:
            message = message[:120] + "..."
        _scan_result, _scan_error = [], "Scan failed: " + message
    finally:
        _scan_done = True


def _open_integration_choice(view_manager):
    """Start a non-blocking LM Studio integration scan."""
    global _state, _scan_agent, _scan_task, _scan_result, _scan_error, _scan_done
    global _chat_cache, _chat_cache_key
    from picoware.system.agent.agent import Agent, MODE_CHAT
    from picoware.system.agent.llm import LLM, LOCAL_MCP
    from picoware.system.thread import ThreadTask
    from gc import collect

    if _settings["provider"] != LOCAL_MCP:
        view_manager.alert("Select LM Studio MCP first", False)
        _back_to_settings_menu(view_manager)
        return

    draw = view_manager.draw
    draw.fill_screen(view_manager.background_color)
    font = draw.get_font(draw.font)
    draw._text(
        draw.scale_x(10),
        draw.scale_y(10),
        "Scanning LM Studio...",
        view_manager.foreground_color,
        font.size,
    )
    draw.swap()

    manager = view_manager.thread_manager
    if manager is None:
        view_manager.alert("Background tasks unavailable", False)
        _back_to_settings_menu(view_manager)
        return

    _scan_result = None
    _scan_error = ""
    _scan_done = False
    _chat_cache = None
    _chat_cache_key = None
    collect()
    _scan_agent = Agent(
        view_manager,
        MODE_CHAT,
        LLM(view_manager.storage, LOCAL_MCP, _settings["model"]),
        file_path="picoware/settings/agent_scan.json",
        cleanup=False,
    )
    _scan_task = ThreadTask(
        "Agent MCP scan",
        function=_integration_scan_worker,
        args=(_scan_agent,),
        timeout=190000,
        stack_size=64 * 1024,
    )
    manager.add_task(_scan_task)
    _state = STATE_SETTINGS_SCAN


def _finish_integration_scan(view_manager):
    """Create the integration toggles after a background scan finishes."""
    global _state, _integration_ids, _integration_toggle_list
    global _scan_agent, _scan_task, _scan_result, _scan_error, _scan_done
    from picoware.gui.toggle_list import ToggleList
    from picoware.system.agent.llm import parse_mcp_integrations
    from picoware.system.settings import Settings

    _integration_ids = _scan_result or []
    error = _scan_error
    _scan_agent = None
    _scan_task = None
    _scan_result = None
    _scan_error = ""
    _scan_done = False

    if error:
        view_manager.alert(error, False)
        _back_to_settings_menu(view_manager)
        return
    if not _integration_ids:
        view_manager.alert("No integrations found", False)
        _back_to_settings_menu(view_manager)
        return

    draw = view_manager.draw
    draw.fill_screen(view_manager.background_color)
    if _integration_toggle_list is not None:
        del _integration_toggle_list
        _integration_toggle_list = None
    settings = Settings(view_manager.storage)
    enabled = parse_mcp_integrations(settings.local_mcp_servers)
    available_entries = []
    for integration_id in _integration_ids:
        runtime_id = (
            integration_id[7:]
            if integration_id.startswith("plugin:")
            else integration_id
        )
        if runtime_id in enabled:
            available_entries.append(integration_id)
    if len(available_entries) != len(enabled):
        settings.local_mcp_servers = ",".join(available_entries)
        enabled = parse_mcp_integrations(settings.local_mcp_servers)
    _integration_toggle_list = ToggleList(
        view_manager,
        TFT_DARKGREY,
        view_manager.background_color,
        TFT_GREEN,
        TFT_DARKGREY,
        callback=lambda index, state: _set_integration_active(
            view_manager, index, state
        ),
        state_text_color=True,
    )
    for integration_id in _integration_ids:
        runtime_id = (
            integration_id[7:]
            if integration_id.startswith("plugin:")
            else integration_id
        )
        _integration_toggle_list.add_toggle(
            integration_id,
            runtime_id in enabled,
        )
    _state = STATE_SETTINGS_INTEGRATION


def _set_integration_active(view_manager, index: int, active: bool):
    """Persist one integration toggle immediately."""
    from picoware.system.settings import Settings
    from picoware.system.agent.llm import parse_mcp_integrations

    integration_id = _integration_ids[index]
    runtime_id = (
        integration_id[7:]
        if integration_id.startswith("plugin:")
        else integration_id
    )
    settings = Settings(view_manager.storage)
    raw_entries = []
    for raw in settings.local_mcp_servers.replace("\n", ",").split(","):
        entry = raw.strip()
        if entry and entry not in raw_entries:
            raw_entries.append(entry)

    enabled = parse_mcp_integrations(settings.local_mcp_servers)
    if active:
        if runtime_id in enabled:
            return
        if len(enabled) >= 16:
            view_manager.alert("Maximum of 16 integrations enabled", False)
            _integration_toggle_list.update_toggle(index, integration_id, False)
            return
        raw_entries.append(integration_id)
    else:
        filtered = []
        for entry in raw_entries:
            parsed = parse_mcp_integrations(entry, 1)
            if not parsed or parsed[0] != runtime_id:
                filtered.append(entry)
        raw_entries = filtered

    settings.local_mcp_servers = ",".join(raw_entries)


def _back_to_settings_menu(view_manager):
    """Clean up the Choice sub-view and return to the settings menu.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    global _state, _choice, _integration_toggle_list

    draw = view_manager.draw
    draw.fill_screen(view_manager.background_color)

    if _choice is not None:
        del _choice
        _choice = None
    if _integration_toggle_list is not None:
        del _integration_toggle_list
        _integration_toggle_list = None

    _state = STATE_SETTINGS
    if _settings_menu is not None:
        _settings_menu.draw()


def _open_chat_input(view_manager, initial_text: str = "") -> None:
    """Open the chat editor and preserve an initiating letter key."""
    global _state
    kb = view_manager.keyboard
    kb.reset()
    kb.response = initial_text
    kb.title = _mode_label
    _state = STATE_TYPE
    view_manager.input_manager.reset()
    kb.run(force=True)


def _confirm_new_session(view_manager) -> bool:
    """Confirm and clear the current mode's persisted conversation."""
    global _conversation, _scroll_offset, _max_scroll
    global _chat_cache, _chat_cache_key

    message = "Start a new " + _mode_label + " session?\nOK=Yes  BACK=No"
    if not view_manager.alert(message, False):
        _render_chat(view_manager)
        return False

    _agent.reset_conversation()
    _conversation = _agent.conversation
    _scroll_offset = 0
    _max_scroll = 0
    _chat_cache = None
    _chat_cache_key = None
    _render_chat(view_manager)
    return True


def start(view_manager) -> bool:
    """Build main menu. Return True on success.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: True on success.
    """
    if not view_manager.has_sd_card:
        view_manager.alert("Agent app requires an SD card", False)
        return False

    wifi = view_manager.wifi

    # if not a wifi device, return
    if not wifi:
        view_manager.alert("WiFi not available...", False)
        return False

    # if wifi isn't connected, return
    if not wifi.is_connected():
        from picoware.applications.wifi.utils import connect_to_saved_wifi

        view_manager.alert("WiFi not connected", False)
        connect_to_saved_wifi(view_manager)
        return False

    from picoware.system.boards import BOARD_HAS_ESP32
    if BOARD_HAS_ESP32 == 0:
        view_manager.freq(True)

    from picoware.gui.menu import Menu

    global _state, _conversation, _menu, _scroll_offset, _max_scroll
    _state = STATE_MENU
    _conversation = []
    _scroll_offset = 0
    _max_scroll = 0

    _menu = Menu(
        view_manager.draw,
        "Picoware Agent",
        0,
        view_manager.draw.size.y,
        text_color=view_manager.foreground_color,
        background_color=view_manager.background_color,
        selected_color=view_manager.selected_color,
    )
    _menu.add_item("Chat")
    _menu.add_item("App Creator")
    _menu.add_item("Device Manager")
    _menu.add_item("New Conversation")
    _menu.add_item("Settings")
    _menu.draw()

    view_manager.input_manager.reset()

    _set_settings(view_manager)
    return True


def run(view_manager) -> None:
    """Main frame handler, delegates to current state.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    global _state, _agent, _agent_mode, _mode_label, _conversation
    global _scroll_offset, _max_scroll
    global _pending_error, _pending_done, _last_phase
    global _scan_error, _scan_done

    btn = view_manager.button

    if _state == STATE_MENU:
        if btn == BUTTON_UP:
            _menu.scroll_up()
        elif btn == BUTTON_DOWN:
            _menu.scroll_down()
        elif btn == BUTTON_CENTER:
            idx = _menu.selected_index
            if idx == 4:
                _start_settings_menu(view_manager)
                return
            if idx == 3:
                if _agent is None:
                    view_manager.alert("Open an Agent mode first", False)
                    _menu.draw()
                    return
                _agent.reset_conversation()
                _conversation = []
                _scroll_offset = 0
                _max_scroll = 0
                _state = STATE_CHAT
                _render_chat(view_manager)
                return
            from picoware.system.agent.agent import Agent, MODE_CHAT, MODE_APP_CREATOR, MODE_DEVICE_MANAGER
            from picoware.system.agent.llm import LLM
            if idx == 0:
                _agent_mode = MODE_CHAT
                _mode_label = "Chat"
            elif idx == 1:
                _agent_mode = MODE_APP_CREATOR
                _mode_label = "App Creator"
            elif idx == 2:
                _agent_mode = MODE_DEVICE_MANAGER
                _mode_label = "Device Manager"
            else:
                view_manager.alert("Invalid selection", False)
                _state = STATE_MENU
                _menu.draw()
                return
            
            if _agent is not None:
                _agent.cancel()
            _agent = Agent(
                view_manager,
                _agent_mode,
                LLM(view_manager.storage, _settings["provider"], _settings["model"]),
            )
            _conversation = _agent.conversation
            _scroll_offset = 0
            _max_scroll = 0
            _state = STATE_CHAT
            _render_chat(view_manager)
        elif btn == BUTTON_BACK:
            view_manager.back()

    elif _state == STATE_SETTINGS:
        if btn == BUTTON_BACK:
            _back_to_settings_menu(view_manager)
            _state = STATE_MENU
            _menu.draw()
        elif btn == BUTTON_UP:
            _settings_menu.scroll_up()
        elif btn == BUTTON_DOWN:
            _settings_menu.scroll_down()
        elif btn == BUTTON_CENTER:
            idx = _settings_menu.selected_index
            if idx == 0:
                _open_provider_choice(view_manager)
            elif idx == 1:
                _open_model_choice(view_manager)
            elif idx == 2:
                _open_integration_choice(view_manager)

    elif _state == STATE_SETTINGS_PROVIDER:
        if btn == BUTTON_BACK:
            _back_to_settings_menu(view_manager)
        elif btn == BUTTON_UP:
            _choice.scroll_up()
        elif btn == BUTTON_DOWN:
            _choice.scroll_down()
        elif btn == BUTTON_CENTER:
            provider_ids = _get_llm_providers()
            selected_provider = provider_ids[_choice.state]
            _settings["provider"] = selected_provider
            from picoware.system.agent.llm import LLM
            llm = LLM(view_manager.storage, selected_provider)
            _settings["model"] = llm.model
            _save_settings(view_manager)
            _back_to_settings_menu(view_manager)

    elif _state == STATE_SETTINGS_MODEL:
        if btn == BUTTON_BACK:
            _back_to_settings_menu(view_manager)
        elif btn == BUTTON_UP:
            _choice.scroll_up()
        elif btn == BUTTON_DOWN:
            _choice.scroll_down()
        elif btn == BUTTON_CENTER:
            models = _get_llm_models(view_manager, _settings["provider"])
            _settings["model"] = models[_choice.state]
            _save_settings(view_manager)
            _back_to_settings_menu(view_manager)

    elif _state == STATE_SETTINGS_INTEGRATION:
        if not _integration_toggle_list.run():
            _back_to_settings_menu(view_manager)

    elif _state == STATE_SETTINGS_SCAN:
        if btn == BUTTON_BACK and _scan_agent is not None:
            _scan_agent.cancel()
            if _scan_task is not None:
                manager = view_manager.thread_manager
                if manager is not None and manager.remove_task(_scan_task.id):
                    _scan_error = "Scan cancelled."
                    _scan_done = True
                else:
                    _scan_task.stop()
        if _scan_done:
            _finish_integration_scan(view_manager)

    elif _state == STATE_WAITING:
        if btn == BUTTON_BACK:
            _agent.cancel()
            if _agent_task is not None:
                manager = view_manager.thread_manager
                if manager is not None and manager.remove_task(_agent_task.id):
                    _pending_error = "Request cancelled."
                    _pending_done = True
                else:
                    _agent_task.stop()
        phase = _agent.status if _agent is not None else "Working"
        _animate_activity(view_manager, phase)
        if _pending_done:
            _finish_agent_request(view_manager)

    elif _state == STATE_CHAT:
        if btn == BUTTON_UP:
            if _scroll_offset > 0:
                _scroll_offset -= 1
                _render_chat(view_manager)
        elif btn == BUTTON_DOWN:
            if _scroll_offset < 999 and _scroll_offset != _max_scroll:
                _scroll_offset += 1
                _render_chat(view_manager)
        elif btn == BUTTON_CENTER:
            _open_chat_input(view_manager)
        elif btn == BUTTON_TAB:
            _confirm_new_session(view_manager)
        elif btn == BUTTON_BACK:
            _state = STATE_MENU
            _menu.draw()
        else:
            first_char = view_manager.input_manager.button_to_char(btn)
            if first_char and first_char.isalpha():
                _open_chat_input(view_manager, first_char)

    elif _state == STATE_TYPE:
        kb = view_manager.keyboard
        if not kb.run():
            # exit back to chat
            _state = STATE_CHAT
            _render_chat(view_manager)
            return

        if not kb.is_finished:
            return

        user_text = (kb.response or "").strip()

        if user_text:
            if not _start_agent_request(view_manager, user_text):
                _conversation.append({
                    "role": "assistant",
                    "content": "Error: Agent background task could not start.",
                })
                _scroll_offset = 32767
                _state = STATE_CHAT
                _render_chat(view_manager)
            return

        _state = STATE_CHAT
        _render_chat(view_manager)


def stop(view_manager) -> None:
    """Tear down widgets and agent, reset state.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    from picoware.system.boards import BOARD_HAS_ESP32
    from gc import collect
    global _agent, _menu, _conversation, _scroll_offset, _max_scroll
    global _settings_menu, _settings, _choice, _integration_ids
    global _integration_toggle_list, _agent_task, _chat_cache, _chat_cache_key
    global _scan_agent, _scan_task, _scan_result, _scan_error, _scan_done

    _save_settings(view_manager)

    _conversation = None
    _scroll_offset = 0
    _max_scroll = 0

    if _agent is not None:
        _agent.cancel()
        del _agent
        _agent = None
    if _agent_task is not None:
        _agent_task.stop()
        _agent_task = None
    if _scan_agent is not None:
        _scan_agent.cancel()
        _scan_agent = None
    if _scan_task is not None:
        _scan_task.stop()
        _scan_task = None
    if _menu is not None:
        del _menu
        _menu = None
    if _settings_menu is not None:
        del _settings_menu
        _settings_menu = None
    if _choice is not None:
        del _choice
        _choice = None
    if _settings is not None:
        del _settings
        _settings = None
    if _integration_toggle_list is not None:
        del _integration_toggle_list
        _integration_toggle_list = None
    _integration_ids = None
    _chat_cache = None
    _chat_cache_key = None
    _scan_result = None
    _scan_error = ""
    _scan_done = False

    if BOARD_HAS_ESP32 == 0:
        view_manager.freq(False)

    collect()
