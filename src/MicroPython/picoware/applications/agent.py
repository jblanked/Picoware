"""Picoware Agent - LLM-powered assistant with chat GUI."""
import micropython
from utime import ticks_diff, ticks_ms
from picoware.system.buttons import (
    BUTTON_UP, BUTTON_DOWN, BUTTON_CENTER, BUTTON_BACK,
)
from picoware.system.colors import (
    TFT_WHITE, TFT_DARKGREY, TFT_LIGHTGREY, TFT_GREEN,
)

STATE_MENU = micropython.const(0)
STATE_CHAT = micropython.const(1)
STATE_TYPE = micropython.const(2)
STATE_SETTINGS = micropython.const(3)
STATE_SETTINGS_PROVIDER = micropython.const(4)
STATE_SETTINGS_MODEL = micropython.const(5)
STATE_WAITING = micropython.const(6)
STATE_SETTINGS_INTEGRATION = micropython.const(7)
STATE_SETTINGS_SCAN = micropython.const(8)
STATE_SETTINGS_SERVER = micropython.const(9)

ACTIVITY_FRAME_MS = micropython.const(250)
ACTIVITY_SEGMENTS = micropython.const(8)
AGENT_BUTTON_CTRL_N = micropython.const(1001)
AGENT_BUTTON_CTRL_R = micropython.const(1002)
CTRL_N_RAW = micropython.const(14)
CTRL_R_RAW = micropython.const(18)
_SHORTCUT_MISSING = object()

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
_model_ids      = None
_integration_ids = None
_integration_toggle_list = None
_integration_staged_records = None
_integration_initial_keys = None
_integration_dirty = False
_agent_task     = None
_pending_result = None
_pending_error  = ""
_pending_done   = False
_activity_started_ms = 0
_activity_last_ms = 0
_activity_frame = 0
_activity_cancellable = False
_last_phase = ""
_scan_client = None
_scan_task = None
_scan_result = None
_scan_error = ""
_scan_done = False
_server_is_catalog = False
_shortcut_previous_n = _SHORTCUT_MISSING
_shortcut_previous_r = _SHORTCUT_MISSING
_shortcuts_installed = False


def _install_agent_shortcuts(input_manager) -> None:
    """Install Ctrl shortcuts only in this Agent app's Input instance."""
    global _shortcut_previous_n, _shortcut_previous_r, _shortcuts_installed
    if _shortcuts_installed:
        return
    mapping = input_manager._button_map
    _shortcut_previous_n = mapping.get(CTRL_N_RAW, _SHORTCUT_MISSING)
    _shortcut_previous_r = mapping.get(CTRL_R_RAW, _SHORTCUT_MISSING)
    mapping[CTRL_N_RAW] = AGENT_BUTTON_CTRL_N
    mapping[CTRL_R_RAW] = AGENT_BUTTON_CTRL_R
    _shortcuts_installed = True


def _remove_agent_shortcuts(input_manager) -> None:
    """Restore the Input mapping that existed before Agent started."""
    global _shortcut_previous_n, _shortcut_previous_r, _shortcuts_installed
    if not _shortcuts_installed:
        return
    mapping = input_manager._button_map
    for raw, button, previous in (
        (CTRL_N_RAW, AGENT_BUTTON_CTRL_N, _shortcut_previous_n),
        (CTRL_R_RAW, AGENT_BUTTON_CTRL_R, _shortcut_previous_r),
    ):
        if mapping.get(raw) != button:
            continue
        if previous is _SHORTCUT_MISSING:
            mapping.pop(raw, None)
        else:
            mapping[raw] = previous
    _shortcut_previous_n = _SHORTCUT_MISSING
    _shortcut_previous_r = _SHORTCUT_MISSING
    _shortcuts_installed = False


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

    vertical_gap = max(font.height // 4, h // 160)
    header_h = max(font.height * 2, h * 8 // 100)
    prompt_h = max(font.height * 3 // 2, h * 7 // 100)
    chat_y   = header_h + vertical_gap
    chat_h   = h - header_h - prompt_h - vertical_gap * 2

    bubble_w = w * 78 // 100
    pad      = max(font.width // 2, w // 60)
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
    line_gap = max(font.height // 3, draw.size.y // 160)
    line_h = font.height + line_gap
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

    draw._fill_round_rectangle(x, y, w, bubble_h, pad, bg_color)

    ty = y + pad
    for line in text_lines:
        if ty + line_h > screen_h:
            break
        draw._text(x + pad, ty, line, text_color, font.size)
        ty += line_h

    return y + bubble_h + pad

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

    global _scroll_offset, _max_scroll

    draw.fill_screen(bg)

    # Header
    draw._fill_rectangle(0, 0, w, header_h, sel)
    draw._text(pad, (header_h - font.height) // 2,
               _mode_label, TFT_WHITE, font.size)
    if _conversation:
        draw._text(w - pad - font.width * 2, (header_h - font.height) // 2,
                   "++" if _scroll_offset > 0 else "  ", TFT_DARKGREY, font.size)

    # Measure one message at a time. Do not duplicate the complete conversation
    # into a second line list on memory-constrained boards.
    line_h  = font.height + max(font.height // 3, h // 160)
    gap_h   = pad * 3
    total_h = 0
    for message in _conversation:
        lines = _wrap_text(message["content"], max_chars)
        total_h += line_h * len(lines) + gap_h

    _max_scroll = max(0, total_h - chat_h) // line_h if line_h else 0
    _scroll_offset = min(_scroll_offset, _max_scroll)
    _scroll_offset = max(_scroll_offset, 0)

    # Draw bubbles
    scroll_px = _scroll_offset * line_h
    cur_y = chat_y - scroll_px

    for message in _conversation:
        block = _wrap_text(message["content"], max_chars)
        is_user = message["role"] == "user"
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

    # Prompt bar
    bar_y = h - prompt_h
    draw._fill_rectangle(0, bar_y, w, prompt_h, TFT_DARKGREY)
    prompt = "OK=Type  Ctrl+N=New  Ctrl+R=Resend  BACK=Menu"
    if draw.len(prompt) > w:
        prompt = "OK Type  ^N New  ^R Again  BACK"
    pw = draw.len(prompt)
    draw._text((w - pw) // 2, bar_y + (prompt_h - font.height) // 2,
               prompt, TFT_LIGHTGREY, font.size)

    draw.swap()


def _show_thinking(view_manager, phase="Preparing", frame=0, elapsed_seconds=0):
    """Display one responsive frame of the request activity indicator."""
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

    bar_w = w * 2 // 3
    gap = max(w // 160, fh // 4)
    segment_w = (bar_w - gap * (ACTIVITY_SEGMENTS - 1)) // ACTIVITY_SEGMENTS
    bar_x = (w - bar_w) // 2
    bar_y = h // 2
    bar_h = max(fh // 2, h // 64)
    for index in range(ACTIVITY_SEGMENTS):
        distance = (frame - index) % ACTIVITY_SEGMENTS
        color = active if distance < 2 else TFT_DARKGREY
        draw._fill_rectangle(
            bar_x + index * (segment_w + gap),
            bar_y,
            segment_w,
            bar_h,
            color,
        )

    alive = "Still working - " + str(elapsed_seconds) + "s"
    text_gap = max(fh // 2, h // 80)
    draw._text(
        (w - draw.len(alive)) // 2,
        bar_y + bar_h + text_gap,
        alive,
        TFT_LIGHTGREY,
        draw.font,
    )
    cancel = "BACK=Cancel" if _activity_cancellable else "Please wait"
    draw._text(
        (w - draw.len(cancel)) // 2,
        h - fh - text_gap,
        cancel,
        TFT_LIGHTGREY,
        draw.font,
    )
    draw.swap()


def _start_activity(view_manager, phase: str, cancellable: bool = False) -> None:
    """Initialize and draw the indeterminate activity animation."""
    global _last_phase, _activity_started_ms, _activity_last_ms, _activity_frame
    global _activity_cancellable
    now = ticks_ms()
    _last_phase = phase
    _activity_cancellable = cancellable
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
    """Run the Agent request and publish a single result for the UI."""
    global _pending_result, _pending_error, _pending_done
    try:
        _pending_result = _agent.run_payload(payload)
        _pending_error = ""
    except Exception as exc:
        _pending_result = None
        _pending_error = str(exc)
    _pending_done = True


def _background_requests_supported() -> bool:
    """Return whether this board can safely run the Agent on the second core."""
    from picoware.system.boards import (
        BOARD_ID,
        BOARD_PICOCALC_PICO_2W,
        BOARD_PICOCALC_PIMORONI_2W,
    )
    return BOARD_ID in (BOARD_PICOCALC_PICO_2W, BOARD_PICOCALC_PIMORONI_2W)


def _start_agent_request(view_manager, user_text: str) -> bool:
    """Start one request, using core 1 only on boards known to support it."""
    global _agent_task, _pending_result, _pending_error, _pending_done, _state
    from gc import collect

    payload = {"message": user_text, "conversation": _conversation}
    _pending_result = None
    _pending_error = ""
    _pending_done = False
    collect()
    manager = view_manager.thread_manager
    use_background = _background_requests_supported() and manager is not None
    _state = STATE_WAITING
    _start_activity(view_manager, "Preparing", use_background)

    if not use_background:
        _agent_worker(payload)
        _finish_agent_request(view_manager)
        return True

    from picoware.system.thread import ThreadTask
    _agent_task = ThreadTask(
        "Agent",
        function=_agent_worker,
        args=(payload,),
        timeout=190000,
        stack_size=64 * 1024,
    )
    manager.add_task(_agent_task)
    return True


def _finish_agent_request(view_manager) -> None:
    """Commit one request result to the visible conversation."""
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


def _open_chat_input(view_manager, initial_text: str = "") -> None:
    """Open the chat editor and preserve an initiating letter key."""
    global _state
    keyboard = view_manager.keyboard
    keyboard.reset()
    keyboard.response = initial_text
    keyboard.title = _mode_label
    _state = STATE_TYPE
    view_manager.input_manager.reset()
    keyboard.run(force=True)


def _confirm_new_session(view_manager) -> bool:
    """Confirm and clear the current mode's persisted conversation."""
    global _conversation, _scroll_offset, _max_scroll
    if not _conversation:
        _scroll_offset = 0
        _max_scroll = 0
        _render_chat(view_manager)
        return True
    message = "Start a new " + _mode_label + " session?\nOK=Yes  BACK=No"
    if not view_manager.alert(message, False):
        _render_chat(view_manager)
        return False
    _agent.reset_conversation()
    _conversation = _agent.conversation
    _scroll_offset = 0
    _max_scroll = 0
    _render_chat(view_manager)
    return True


def _last_user_request(conversation) -> str:
    """Return the most recent visible user request for Ctrl+R."""
    if not isinstance(conversation, list):
        return ""
    for message in reversed(conversation):
        if (
            isinstance(message, dict)
            and message.get("role") == "user"
            and isinstance(message.get("content"), str)
            and message["content"].strip()
        ):
            return message["content"].strip()
    return ""


def _open_new_chat_from_menu(view_manager) -> None:
    """Open Chat and discard persisted history only after confirmation."""
    global _agent, _agent_mode, _mode_label, _conversation, _state
    global _scroll_offset, _max_scroll
    from picoware.system.agent.agent import Agent, MODE_CHAT
    from picoware.system.agent.llm import LLM

    if _agent is None or _agent_mode != MODE_CHAT:
        if _agent is not None:
            _agent.cancel()
        _agent_mode = MODE_CHAT
        _mode_label = "Chat"
        _agent = Agent(
            view_manager,
            MODE_CHAT,
            LLM(
                view_manager.storage,
                _settings["provider"],
                _settings["model"],
            ),
            allow_followup_questions=_followup_questions_enabled(),
        )
    _conversation = _agent.conversation
    _state = STATE_CHAT
    if _conversation and not view_manager.alert(
        "Discard the old Chat conversation?\nOK=Discard  BACK=Keep", False
    ):
        _scroll_offset = 32767
        _render_chat(view_manager)
        return
    if _conversation:
        _agent.reset_conversation()
        _conversation = _agent.conversation
    _scroll_offset = 0
    _max_scroll = 0
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
            "provider": DEEPSEEK,
            "allow_followup_questions": False,
        }
        if not _save_settings(view_manager):
            view_manager.alert(
                "Failed to save default agent settings.", False
            )
    else:
        _settings = s.serialize("picoware/settings/current_agent.json")
        from picoware.system.agent.llm import JBLANKED, LOCAL, LOCAL_MCP
        if (
            isinstance(_settings, dict)
            and (
                _settings.get("provider") == LOCAL_MCP
                or (
                    _settings.get("provider") == JBLANKED
                    and _settings.get("model") not in ("", "none")
                )
            )
        ):
            # Provider ID 6 represented Local + MCP before JBlanked used it;
            # ID 7 was the transitional value after that collision.
            _settings["provider"] = LOCAL
            if not _save_settings(view_manager):
                view_manager.alert(
                    "Failed to migrate Local Agent settings.", False
                )


def _followup_questions_enabled() -> bool:
    """Return the saved model follow-up preference, defaulting off."""
    return bool(
        isinstance(_settings, dict)
        and _settings.get("allow_followup_questions", False)
    )


def _toggle_followup_questions(view_manager) -> None:
    """Toggle model follow-up questions and persist the preference."""
    global _agent
    previous = _followup_questions_enabled()
    _settings["allow_followup_questions"] = not previous
    if not _save_settings(view_manager):
        _settings["allow_followup_questions"] = previous
        view_manager.alert("Failed to save Agent settings.", False)
    elif _agent is not None:
        _agent.allow_followup_questions = not previous
    _start_settings_menu(view_manager)

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

def _get_llm_models(
    view_manager, llm_id: int, current_model: str = None, http=None,
) -> list:
    """Return a list of models for the specified LLM provider.

    Args:
        view_manager (ViewManager): The view manager context.
        llm_id (int): The provider ID.
        current_model (str): Saved model to validate against the live catalog.

    Returns:
        list: Available model names.
    """
    from picoware.system.agent.llm import (
        LLM, LOCAL, LOCAL_MCP, local_model_catalog_url, parse_local_models,
    )

    llm = LLM(view_manager.storage, llm_id, current_model)
    models = list(llm.models)
    if llm_id not in (LOCAL, LOCAL_MCP):
        return models

    response = None
    catalog_loaded = False
    try:
        if http is None:
            from picoware.system.http import HTTP
            http = HTTP(thread_manager=view_manager.thread_manager)
        response = http.get(
            local_model_catalog_url(llm.url),
            headers=llm.headers,
            timeout=5,
        )
        if response is not None and 200 <= response.status_code <= 299:
            models = parse_local_models(response.json())
            catalog_loaded = True
    except (OSError, TypeError, ValueError):
        pass
    finally:
        if response is not None:
            response.close()
    if current_model and current_model not in models and not catalog_loaded:
        models.append(current_model)
    return models


def _settings_menu_items(
    provider: int, allow_followup_questions: bool = False,
) -> list:
    """Return settings items available for the selected provider."""
    from picoware.system.agent.llm import LOCAL, LOCAL_MCP

    items = [
        "Agent Provider",
        "Agent Model",
        "Follow-up Questions: "
        + ("On" if allow_followup_questions else "Off"),
    ]
    if provider in (LOCAL, LOCAL_MCP):
        items.append("Scan Integrations")
        items.append("Add MCP Server")
        items.append("Add MCP Catalog")
    return items


def _provider_change_preserves_model(
    current_provider: int, selected_provider: int,
) -> bool:
    """Return whether a provider change should retain the current model."""
    from picoware.system.agent.llm import LOCAL, LOCAL_MCP

    if current_provider == selected_provider:
        return True
    return (
        current_provider in (LOCAL, LOCAL_MCP)
        and selected_provider in (LOCAL, LOCAL_MCP)
    )


def _model_at_index(models, index: int) -> str:
    """Return one model from the displayed snapshot, or an empty value."""
    if not isinstance(models, list) or index < 0 or index >= len(models):
        return ""
    return models[index]


def _start_settings_menu(view_manager):
    """Show the agent settings menu.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    from picoware.gui.menu import Menu
    global _state, _settings_menu
    _state = STATE_SETTINGS
    if _settings_menu is not None:
        del _settings_menu
        _settings_menu = None
    _settings_menu = Menu(
        view_manager.draw,
        "Settings",
        0,
        view_manager.draw.size.y,
        text_color=view_manager.foreground_color,
        background_color=view_manager.background_color,
        selected_color=view_manager.selected_color,
    )
    for item in _settings_menu_items(
        _settings["provider"], _followup_questions_enabled()
    ):
        _settings_menu.add_item(item)
    _settings_menu.draw()


def _open_provider_choice(view_manager):
    """Open a Choice sub-view for selecting the LLM provider.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    global _state, _choice, _model_ids
    from picoware.gui.choice import Choice
    from picoware.system.vector import Vector
    from picoware.system.agent.llm import LLM

    draw = view_manager.draw
    draw.fill_screen(view_manager.background_color)
    if _choice is not None:
        del _choice
        _choice = None
    _model_ids = None

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
    global _state, _choice, _model_ids
    from picoware.gui.choice import Choice
    from picoware.system.vector import Vector

    draw = view_manager.draw
    draw.fill_screen(view_manager.background_color)
    if _choice is not None:
        del _choice
        _choice = None

    current_model = _settings["model"]
    models = _get_llm_models(
        view_manager, _settings["provider"], current_model
    )
    if not models:
        view_manager.alert(
            "No local models found. Check Local URL and load a model.", False
        )
        _back_to_settings_menu(view_manager)
        return
    _model_ids = models
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
    """Scan the configured integration gateway outside the UI thread."""
    global _scan_result, _scan_error, _scan_done
    try:
        _scan_result, _scan_error = scanner.scan_integrations()
    except Exception as exc:
        message = str(exc)
        if len(message) > 120:
            message = message[:120] + "..."
        _scan_result, _scan_error = [], "Scan failed: " + message
    _scan_done = True


def _open_integration_choice(view_manager) -> None:
    """Scan available integrations and open the activation list."""
    global _state, _scan_client, _scan_task
    global _scan_result, _scan_error, _scan_done
    from gc import collect
    from picoware.system.agent.llm import LLM, LOCAL
    from picoware.system.agent.mcp import MCPClient
    from picoware.system.http import HTTP

    if _settings["provider"] != LOCAL:
        view_manager.alert("Select Local first", False)
        _back_to_settings_menu(view_manager)
        return

    _scan_result = None
    _scan_error = ""
    _scan_done = False
    collect()
    llm = LLM(view_manager.storage, LOCAL, _settings["model"])
    _scan_client = MCPClient(view_manager, HTTP(), llm)
    _state = STATE_SETTINGS_SCAN
    _start_activity(view_manager, "Scanning integrations", True)

    manager = view_manager.thread_manager
    if _background_requests_supported() and manager is not None:
        from picoware.system.thread import ThreadTask
        _scan_task = ThreadTask(
            "Agent MCP scan",
            function=_integration_scan_worker,
            args=(_scan_client,),
            timeout=190000,
            stack_size=64 * 1024,
        )
        manager.add_task(_scan_task)
        return

    _scan_task = None
    _integration_scan_worker(_scan_client)
    _finish_integration_scan(view_manager)


def _integration_runtime_id(integration_id) -> str:
    """Return the stable key for one integration record."""
    from picoware.system.agent.mcp import integration_key

    return integration_key(integration_id)


def _selectable_integration_records(records) -> list:
    """Return tool records that may be enabled or disabled by the user."""
    return [
        record for record in records
        if "catalog" not in record.get("capabilities", [])
    ]


def _refresh_enabled_integration_metadata(current, scanned) -> list:
    """Refresh metadata without enabling newly discovered integrations."""
    from picoware.system.agent.mcp import (
        integration_key, merge_integration_records, parse_integration_records,
    )

    enabled = parse_integration_records(current)
    if not enabled:
        return []
    merged = merge_integration_records(enabled, scanned)
    by_key = {integration_key(record): record for record in merged}
    return [
        by_key.get(integration_key(record), record)
        for record in enabled
    ]


def _finish_integration_scan(view_manager) -> None:
    """Create integration toggles after a successful catalog scan."""
    global _state, _integration_ids, _integration_toggle_list
    global _integration_staged_records, _integration_initial_keys
    global _integration_dirty
    global _scan_client, _scan_task, _scan_result, _scan_error, _scan_done
    from picoware.gui.toggle_list import ToggleList
    from picoware.system.agent.mcp import (
        integration_key, integration_label, parse_integration_records,
        serialize_integration_records,
    )
    from picoware.system.settings import Settings

    scan_records = _scan_result or []
    error = _scan_error
    _scan_client = None
    _scan_task = None
    _scan_result = None
    _scan_error = ""
    _scan_done = False

    if error:
        view_manager.alert(error, False)
        _back_to_settings_menu(view_manager)
        return
    if not scan_records:
        view_manager.alert("No integrations found", False)
        _back_to_settings_menu(view_manager)
        return

    draw = view_manager.draw
    draw.fill_screen(view_manager.background_color)
    if _integration_toggle_list is not None:
        del _integration_toggle_list
        _integration_toggle_list = None

    settings = Settings(view_manager.storage)
    current_records = parse_integration_records(settings.mcp_integrations)
    _integration_staged_records = _refresh_enabled_integration_metadata(
        current_records, scan_records
    )
    serialized = serialize_integration_records(_integration_staged_records)
    if serialized != serialize_integration_records(current_records):
        settings.mcp_integrations = serialized
    _integration_initial_keys = [
        integration_key(record)
        for record in _integration_staged_records
    ]
    _integration_dirty = False
    _integration_ids = _selectable_integration_records(scan_records)
    if not _integration_ids:
        view_manager.alert("No selectable integrations found", False)
        _back_to_settings_menu(view_manager)
        return

    _integration_toggle_list = ToggleList(
        view_manager,
        TFT_DARKGREY,
        view_manager.background_color,
        TFT_GREEN,
        TFT_DARKGREY,
        callback=lambda index, state: _set_integration_active(
            view_manager, index, state
        ),
    )
    for integration_id in _integration_ids:
        _integration_toggle_list.add_toggle(
            integration_label(integration_id),
            _integration_runtime_id(integration_id) in _integration_initial_keys,
        )
    _state = STATE_SETTINGS_INTEGRATION
    view_manager.input_manager.reset()


def _set_integration_active(view_manager, index: int, active: bool) -> None:
    """Stage one integration toggle without changing persistent settings."""
    global _integration_staged_records, _integration_dirty
    from picoware.system.agent.mcp import (
        integration_key, integration_label,
    )

    integration_id = _integration_ids[index]
    if "catalog" in integration_id.get("capabilities", []):
        view_manager.alert("Catalog providers are required for scanning", False)
        _integration_toggle_list.update_toggle(
            index, integration_label(integration_id), True
        )
        return
    runtime_id = _integration_runtime_id(integration_id)
    records = _integration_staged_records or []
    enabled = [integration_key(record) for record in records]
    if active:
        if runtime_id in enabled:
            return
        if len(enabled) >= 16:
            view_manager.alert("Maximum of 16 integrations enabled", False)
            _integration_toggle_list.update_toggle(
                index, integration_label(integration_id), False
            )
            return
        records.append(integration_id)
    else:
        records = [
            record for record in records
            if integration_key(record) != runtime_id
        ]
    _integration_staged_records = records
    staged_keys = [integration_key(record) for record in records]
    _integration_dirty = staged_keys != (_integration_initial_keys or [])


def _commit_integration_changes(view_manager) -> None:
    """Persist staged tool selections while retaining catalog providers."""
    global _integration_staged_records, _integration_initial_keys
    global _integration_dirty
    from picoware.system.agent.mcp import (
        integration_key, parse_integration_records, preserve_catalog_records,
        serialize_integration_records,
    )
    from picoware.system.settings import Settings

    settings = Settings(view_manager.storage)
    current = parse_integration_records(settings.mcp_integrations)
    records = preserve_catalog_records(
        current, _integration_staged_records or [], 16
    )
    settings.mcp_integrations = serialize_integration_records(records)
    _integration_staged_records = records
    _integration_initial_keys = [integration_key(record) for record in records]
    _integration_dirty = False


def _catalog_input_record(value: str):
    """Parse a catalog plugin ID or a Label|URL ephemeral MCP endpoint."""
    from picoware.system.agent.mcp import normalize_integration_record

    text = (value or "").strip()
    if not text:
        return None
    if "|" in text:
        record = normalize_integration_record("server:" + text)
    else:
        record = normalize_integration_record(text)
    if record is not None:
        record["capabilities"] = ["catalog"]
    return record


def _open_mcp_server_input(view_manager, catalog: bool = False) -> None:
    """Open a compact Label|URL editor for an LM Studio MCP record."""
    global _state, _server_is_catalog
    keyboard = view_manager.keyboard
    keyboard.reset()
    _server_is_catalog = bool(catalog)
    keyboard.title = "Catalog ID or Label|URL" if catalog else "MCP Label|URL"
    keyboard.response = ""
    _state = STATE_SETTINGS_SERVER
    view_manager.input_manager.reset()
    keyboard.run(force=True)


def _save_mcp_server(
    view_manager, value: str, catalog: bool = False,
) -> bool:
    """Validate and activate an LM Studio MCP server or catalog record."""
    from picoware.system.agent.mcp import (
        integration_key, normalize_integration_record,
        parse_integration_records, serialize_integration_records,
    )
    from picoware.system.settings import Settings

    if catalog:
        record = _catalog_input_record(value)
    else:
        text = (value or "").strip()
        parts = text.split("|", 1)
        record = None
        if len(parts) == 2:
            record = normalize_integration_record({
                "type": "ephemeral_mcp",
                "server_label": parts[0].strip(),
                "server_url": parts[1].strip(),
                "capabilities": ["generic"],
            })
    if record is None:
        message = (
            "Use plugin ID or Label|http://server-url"
            if catalog else "Use Label|http://server-url"
        )
        view_manager.alert(message, False)
        return False
    settings = Settings(view_manager.storage)
    records = parse_integration_records(settings.mcp_integrations)
    keys = [integration_key(item) for item in records]
    record_key = integration_key(record)
    if record_key in keys:
        if catalog:
            index = keys.index(record_key)
            if "catalog" not in records[index].get("capabilities", []):
                records[index] = record
                settings.mcp_integrations = serialize_integration_records(records)
    else:
        if len(records) >= 16:
            view_manager.alert("Maximum of 16 integrations enabled", False)
            return False
        records.append(record)
        settings.mcp_integrations = serialize_integration_records(records)
    return True


def _back_to_settings_menu(view_manager):
    """Clean up the Choice sub-view and return to the settings menu.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    global _state, _choice, _model_ids, _integration_ids
    global _integration_toggle_list, _integration_staged_records
    global _integration_initial_keys, _integration_dirty

    draw = view_manager.draw
    draw.fill_screen(view_manager.background_color)

    if _choice is not None:
        del _choice
        _choice = None
    _model_ids = None
    if _integration_toggle_list is not None:
        del _integration_toggle_list
        _integration_toggle_list = None
    _integration_ids = None
    _integration_staged_records = None
    _integration_initial_keys = None
    _integration_dirty = False

    _start_settings_menu(view_manager)


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
    _install_agent_shortcuts(view_manager.input_manager)
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
    global _pending_error, _pending_done
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
                _open_new_chat_from_menu(view_manager)
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
                allow_followup_questions=_followup_questions_enabled(),
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
            settings_items = _settings_menu_items(
                _settings["provider"], _followup_questions_enabled()
            )
            if idx == 0:
                _open_provider_choice(view_manager)
            elif idx == 1:
                _open_model_choice(view_manager)
            elif idx == 2:
                _toggle_followup_questions(view_manager)
            elif idx == 3 and len(settings_items) == 6:
                _open_integration_choice(view_manager)
            elif idx == 4 and len(settings_items) == 6:
                _open_mcp_server_input(view_manager, False)
            elif idx == 5 and len(settings_items) == 6:
                _open_mcp_server_input(view_manager, True)

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
            current_provider = _settings["provider"]
            current_model = _settings["model"]
            models = []
            preserve_model = (
                current_model
                and _provider_change_preserves_model(
                    current_provider, selected_provider
                )
            )
            from picoware.system.agent.llm import (
                LOCAL, LOCAL_MCP, LLM,
            )
            if (
                preserve_model
                and selected_provider in (LOCAL, LOCAL_MCP)
            ):
                models = _get_llm_models(
                    view_manager, selected_provider, current_model
                )
                preserve_model = current_model in models
                if not preserve_model and models:
                    _settings["model"] = models[0]
                elif not preserve_model:
                    view_manager.alert(
                        "No local models found. Check Local URL and load a model.",
                        False,
                    )
                    _choice.draw()
                    return
            if not preserve_model:
                if selected_provider in (LOCAL, LOCAL_MCP):
                    if not _settings.get("model") or not models:
                        models = _get_llm_models(
                            view_manager, selected_provider, None
                        )
                    if not models:
                        view_manager.alert(
                            "No local models found. Check Local URL and load a model.",
                            False,
                        )
                        _choice.draw()
                        return
                    _settings["model"] = models[0]
                else:
                    _settings["model"] = LLM(
                        view_manager.storage, selected_provider
                    ).model
            _settings["provider"] = selected_provider
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
            selected_model = _model_at_index(_model_ids, _choice.state)
            if not selected_model:
                view_manager.alert("Model list is no longer available", False)
                _back_to_settings_menu(view_manager)
                return
            _settings["model"] = selected_model
            _save_settings(view_manager)
            _back_to_settings_menu(view_manager)

    elif _state == STATE_SETTINGS_INTEGRATION:
        if not _integration_toggle_list.run():
            if _integration_dirty and view_manager.alert(
                "Save integration changes?\nOK=Save  BACK=Discard", False
            ):
                _commit_integration_changes(view_manager)
            _back_to_settings_menu(view_manager)

    elif _state == STATE_SETTINGS_SCAN:
        if btn == BUTTON_BACK and _scan_client is not None:
            _scan_client.cancel()
            manager = view_manager.thread_manager
            if (
                _scan_task is not None
                and manager is not None
                and manager.remove_task(_scan_task.id)
            ):
                _scan_error = "Scan cancelled."
                _scan_done = True
            elif _scan_task is not None:
                _scan_task.stop()
        _animate_activity(view_manager, "Scanning integrations")
        if _scan_done:
            _finish_integration_scan(view_manager)

    elif _state == STATE_SETTINGS_SERVER:
        keyboard = view_manager.keyboard
        if not keyboard.run():
            keyboard.reset()
            _back_to_settings_menu(view_manager)
            return
        if not keyboard.is_finished:
            return
        value = keyboard.response
        keyboard.reset()
        if _save_mcp_server(view_manager, value, _server_is_catalog):
            _back_to_settings_menu(view_manager)
        else:
            _open_mcp_server_input(view_manager, _server_is_catalog)

    elif _state == STATE_WAITING:
        if btn == BUTTON_BACK and _agent_task is not None:
            _agent.cancel()
            manager = view_manager.thread_manager
            if manager is not None and manager.remove_task(_agent_task.id):
                _pending_error = "Request cancelled."
                _pending_done = True
            else:
                _agent_task.stop()
        _animate_activity(view_manager, _agent.status if _agent is not None else "Working")
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
        elif btn == AGENT_BUTTON_CTRL_N:
            _confirm_new_session(view_manager)
        elif btn == AGENT_BUTTON_CTRL_R:
            request = _last_user_request(_conversation)
            if request:
                _start_agent_request(view_manager, request)
            else:
                view_manager.alert("No previous request to resend", False)
                _render_chat(view_manager)
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
            _start_agent_request(view_manager, user_text)
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
    global _settings_menu, _settings, _choice, _model_ids, _agent_task
    global _integration_ids, _integration_toggle_list
    global _integration_staged_records, _integration_initial_keys
    global _integration_dirty
    global _scan_client, _scan_task, _scan_result, _scan_error, _scan_done
    global _server_is_catalog

    _save_settings(view_manager)
    _remove_agent_shortcuts(view_manager.input_manager)

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
    if _scan_client is not None:
        _scan_client.cancel()
        _scan_client = None
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
    _model_ids = None
    if _integration_toggle_list is not None:
        del _integration_toggle_list
        _integration_toggle_list = None
    _integration_ids = None
    _integration_staged_records = None
    _integration_initial_keys = None
    _integration_dirty = False
    _scan_result = None
    _scan_error = ""
    _scan_done = False
    _server_is_catalog = False
    if _settings is not None:
        del _settings
        _settings = None

    if BOARD_HAS_ESP32 == 0:
        view_manager.freq(False)

    collect()
