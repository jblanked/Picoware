"""Picoware Agent -- LLM-powered assistant with chat GUI."""
from micropython import const
from picoware.system.buttons import (
    BUTTON_UP, BUTTON_DOWN, BUTTON_CENTER, BUTTON_BACK,
)
from picoware.system.colors import TFT_WHITE, TFT_DARKGREY, TFT_LIGHTGREY

STATE_MENU = const(0)
STATE_CHAT = const(1)
STATE_TYPE = const(2)

_agent          = None
_menu           = None
_state          = STATE_MENU
_conversation   = None       
_mode_label     = ""       
_agent_mode     = None
_scroll_offset  = 0      
_max_scroll     = 0 


def _wrap_text(text, max_chars):
    """Wrap text to max_chars per line, preserving words."""
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
    """Return layout metrics derived from screen size and default font."""
    draw = view_manager.draw
    w, h = draw.size.x, draw.size.y

    font = draw.get_font(draw.font)

    header_h = max(22, h * 8 // 100)
    prompt_h = max(26, h * 11 // 100)
    chat_y   = header_h + 2
    chat_h   = h - header_h - prompt_h - 4

    bubble_w = w * 78 // 100
    pad      = max(4, w // 60)
    text_w   = bubble_w - pad * 2
    char_w   = font.width + font.spacing
    max_chars = text_w // char_w if char_w > 0 else 30

    return header_h, prompt_h, chat_y, chat_h, max_chars, font, bubble_w, pad


def _draw_bubble(draw, x, y, w, text_lines, font, bg_color, text_color, pad,
                  clip_top=0):
    """Draw a rounded-rect bubble clipped to screen bounds."""
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


def _render_chat(view_manager):
    """Draw conversation as chat bubbles with scroll and prompt bar."""
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

    # Build line list
    all_lines = []
    for msg in _conversation:
        wrapped = _wrap_text(msg["content"], max_chars)
        is_user = (msg["role"] == "user")
        for line in wrapped:
            all_lines.append((line, is_user))
        all_lines.append(("", None))

    if all_lines and all_lines[-1][1] is None:
        all_lines.pop()

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
    prompt = "OK=Type   BACK=Menu"
    pw = draw.len(prompt)
    draw._text((w - pw) // 2, bar_y + (prompt_h - font.height) // 2,
               prompt, TFT_LIGHTGREY, font.size)

    draw.swap()


def _show_thinking(view_manager):
    """Clear screen and display a centred thinking indicator."""
    draw = view_manager.draw
    w, h = draw.size.x, draw.size.y
    bg = view_manager.background_color

    draw.fill_screen(bg)
    msg = "Thinking..."
    mw = draw.len(msg)
    fh = draw.font_size.y
    draw._text((w - mw) // 2, (h - fh) // 2, msg,
               view_manager.foreground_color, draw.font)
    draw.swap()


def start(view_manager) -> bool:
    """Build main menu. Return True on success."""
    from picoware.system.boards import BOARD_CARDPUTER, BOARD_CROWPANEL_10_1
    if view_manager.board_id not in (BOARD_CARDPUTER, BOARD_CROWPANEL_10_1):
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
    _menu.add_item("App Creator")
    _menu.add_item("Device Manager")
    _menu.draw()

    view_manager.input_manager.reset()
    return True


def run(view_manager) -> None:
    """Main frame handler, delegates to current state."""
    global _state, _agent, _agent_mode, _mode_label, _conversation
    global _scroll_offset, _max_scroll

    btn = view_manager.button

    if _state == STATE_MENU:
        if btn == BUTTON_UP:
            _menu.scroll_up()
        elif btn == BUTTON_DOWN:
            _menu.scroll_down()
        elif btn == BUTTON_CENTER:
            from picoware.system.agent.agent import Agent, MODE_APP_CREATOR, MODE_DEVICE_MANAGER
            idx = _menu.selected_index
            if idx == 0:
                _agent_mode = MODE_APP_CREATOR
                _mode_label = "App Creator"
            else:
                _agent_mode = MODE_DEVICE_MANAGER
                _mode_label = "Device Manager"

            _agent = Agent(view_manager, mode=_agent_mode)
            _conversation = []
            _scroll_offset = 0
            _max_scroll = 0
            _state = STATE_CHAT
            _render_chat(view_manager)
        elif btn == BUTTON_BACK:
            view_manager.back()

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
            kb = view_manager.keyboard
            kb.reset()
            kb.title = _mode_label
            _state = STATE_TYPE
            view_manager.input_manager.reset()
            view_manager.keyboard.run(force=True)
        elif btn == BUTTON_BACK:
            _state = STATE_MENU
            _menu.draw()

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
            _show_thinking(view_manager)

            try:
                result = _agent.run_payload({
                    "message": user_text,
                    "conversation": _conversation,
                })
                if result["status"] == "completed":
                    _conversation = result["conversation"]
                else:
                    _conversation.append({
                        "role": "assistant",
                        "content": result["message"],
                    })
            except Exception as exc:
                _conversation.append({
                    "role": "assistant",
                    "content": "Error: " + str(exc),
                })

        _scroll_offset = 32767
        _state = STATE_CHAT
        _render_chat(view_manager)
        _render_chat(view_manager)


def stop(view_manager) -> None:
    """Tear down widgets and agent, reset state."""
    from picoware.system.boards import BOARD_CARDPUTER, BOARD_CROWPANEL_10_1
    from gc import collect
    global _agent, _menu, _conversation, _scroll_offset, _max_scroll

    _conversation = None
    _scroll_offset = 0
    _max_scroll = 0

    if _agent is not None:
        del _agent
        _agent = None
    if _menu is not None:
        del _menu
        _menu = None
    
    if view_manager.board_id not in (BOARD_CARDPUTER, BOARD_CROWPANEL_10_1):
        view_manager.freq(False)

    collect()