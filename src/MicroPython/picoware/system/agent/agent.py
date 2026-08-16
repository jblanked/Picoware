"""Agent - LLM-powered assistant with tools."""

import json
from micropython import const
from picoware.system.agent.tools import dispatch
from picoware.system.agent.llm import LLM, DEEPSEEK
from picoware.system.agent.context import chat, app_creator, device_manager

MODE_CHAT = const(0) # general chat mode
MODE_APP_CREATOR = const(1) # creates/edits Picoware apps
MODE_DEVICE_MANAGER = const(2) # manages files, has network access, can run commands, etc.

MAX_TOOL_ITERATIONS = const(12)
MAX_TOOL_CALLS_PER_RUN = const(16)
MAX_IDENTICAL_TOOL_CALLS = const(2)
MAX_CONVERSATION_MESSAGES = const(20)
MAX_CONVERSATION_BYTES = const(32768)
MAX_MESSAGE_CHARS = const(8192)
# Raw SSE is retained only as a bounded temporary SD diagnostic spool.  It is
# not a heap limit; parsed events are discarded as the stream progresses.
MAX_CHAT_STREAM_BYTES = const(262144)
MAX_CHAT_STREAM_EVENTS = const(4096)
MAX_CHAT_EVENT_BYTES = const(12288)
MAX_CHAT_TOOL_ARGUMENT_CHARS = const(8192)
MAX_CHAT_TOOL_ID_CHARS = const(128)
MAX_CHAT_TOOL_NAME_CHARS = const(128)
MAX_CHAT_TOOL_TYPE_CHARS = const(32)
MAX_CHAT_ERROR_CHARS = const(256)
MAX_CHAT_WRITE_CHUNK_BYTES = const(4096)
MAX_CHAT_OUTPUT_TOKENS = const(1536)
MAX_MANAGER_OUTPUT_TOKENS = const(1536)
MAX_APP_OUTPUT_TOKENS = const(2048)

APP_CREATOR_TOOL_NAMES = (
    "storage_get_info",
    "storage_listdir",
    "storage_mkdir",
    "storage_read",
    "storage_remove",
    "storage_write",
    "picoware_api_search",
    "picoware_api_read",
    "picoware_app_validate",
)
DEVICE_MANAGER_TOOL_NAMES = (
    "storage_get_info",
    "storage_listdir",
    "storage_mkdir",
    "storage_read",
    "storage_remove",
    "storage_write",
    "network_get_info",
    "network_scan_wifi",
    "network_scan_ble",
    "network_send_request",
)
ERROR_RESPONSE_PREFIXES = (
    "API error",
    "An error occurred during processing:",
    "Tool loop stopped before execution:",
    "Error:",
)
MCP_AFFIRMATIVE_REPLIES = (
    "yes", "yes please", "ok", "okay", "sure", "please do", "go ahead",
    "do it", "continue", "go on", "proceed", "retry", "ja", "ja bitte",
    "bitte", "mach weiter",
)
MCP_CONTINUATION_QUESTIONS = (
    "would you like me to", "do you want me to", "want me to", "shall i",
    "should i", "may i", "soll ich", "moechtest du", "möchtest du",
)
MCP_CONTINUATION_ACTIONS = (
    "search", "research", " try ", "attempt", "continue", "open", "navigate",
    "look up", "fetch", "browse", " use ", " call ", " run ", " perform ",
    " suche ", "recherch", "versuch", "öffn",
)
MCP_DEFERRAL_MARKERS = (
    "please confirm", "would you like me to", "do you want me to",
    "want me to", "shall i", "should i", "may i", "i'll now",
    "i’ll now", "i will now", "i need to", "i'm going to", "i’m going to",
    "i am going to", "i can now", "let me", "please wait", "soll ich",
    "moechtest du", "möchtest du",
)
MCP_CLARIFICATION_MARKERS = (
    "exact integration label", " search topic", " search query",
    "specify a search", "specify the topic", "specify the page or topic",
    "clarify your request", "what should i search",
    "what would you like me to search", "do not have access",
    "don't have access", "cannot access", "can't access",
)
MCP_EXACT_LABEL_CLARIFICATION = (
    "Please use the exact integration label from settings; the requested name "
    "was not found or matched more than one configured integration."
)
MCP_TOPIC_CLARIFICATION = (
    "Please specify the page or topic for the requested integration."
)
MCP_FINAL_ANSWER_GUARD = (
    "The configured integrations already completed for this turn. Answer from "
    "their supplied evidence now. Do not ask for confirmation, promise a "
    "future search, describe a next step, or tell the user to wait. If the "
    "evidence is insufficient, state that limitation as the final answer."
)
MCP_FINAL_RETRY_GUARD = (
    "The previous completion deferred work that was already completed. Do not "
    "request confirmation or another user message. Give the final "
    "evidence-based answer now, or state the evidence limitation as the final "
    "answer."
)
MCP_EVIDENCE_PREAMBLE = (
    "\n\n# Current integration evidence\n"
    "This evidence was retrieved for this turn by the configured MCP "
    "integrations. Use it as tool output and do not claim unsupported facts. "
    "Answer the user's request directly now without requesting another tool. "
    "Disregard earlier claims that these integrations were unavailable because "
    "retrieval succeeded for this turn. Never claim that you lack access to a "
    "configured tool or to the evidence below. Tool execution does not prove "
    "that the evidence is complete or on-topic; state that limitation as the "
    "final answer when necessary. If no page-opening tool ran, do not claim "
    "page contents. If a source failed but no current fact is required, provide "
    "the useful answer instead of a research-status report.\n"
)
MCP_DEFERRAL_PREAMBLES = (
    "sure", "certainly", "okay", "ok", "i understand", "understood",
    "of course", "absolutely", "i can help with that", "to continue",
    "before i continue",
)
MCP_PENDING_LIMITATION_PREAMBLES = (
    "no evidence yet", "do not have evidence yet", "don't have evidence yet",
    "haven't searched yet", "have not searched yet",
)
MCP_LIMITATION_PREAMBLES = (
    "evidence is insufficient", "evidence is incomplete", "no evidence",
    "no reliable evidence", "could not find", "did not find",
)
MCP_NEGATIVE_PREFIXES = (
    "no", "nope", "do not", "don't", "dont", "never mind", "cancel",
    "stop", "nein", "abbrechen",
)


def _contains_any(text: str, values) -> bool:
    for value in values:
        if value in text:
            return True
    return False


def _normalized_reply(value: str) -> str:
    """Return a compact form for bounded continuation matching."""
    return " ".join(value.lower().strip().rstrip(".!?").split())


def _utf8_char_size(char: str) -> int:
    code = ord(char)
    if code <= 0x7F:
        return 1
    if code <= 0x7FF:
        return 2
    return 4 if code > 0xFFFF else 3


def _utf8_byte_size(value: str, stop_after: int = 0) -> int:
    """Count UTF-8 bytes without allocating an encoded copy."""
    used = 0
    for char in value:
        used += _utf8_char_size(char)
        if stop_after and used > stop_after:
            break
    return used


def _utf8_prefix(value: str, maximum: int) -> str:
    used = 0
    index = 0
    for char in value:
        size = _utf8_char_size(char)
        if used + size > maximum:
            break
        used += size
        index += 1
    return value if index == len(value) else value[:index]


def _utf8_suffix(value: str, maximum: int) -> str:
    used = 0
    index = len(value)
    while index > 0:
        size = _utf8_char_size(value[index - 1])
        if used + size > maximum:
            break
        used += size
        index -= 1
    return value[index:]


def _bounded_request_text(value: str) -> str:
    """Bound a request while preserving both its task and trailing selection."""
    if _utf8_byte_size(value, MAX_MESSAGE_CHARS) <= MAX_MESSAGE_CHARS:
        return value
    marker = "\n...[request truncated for device memory]...\n"
    remaining = MAX_MESSAGE_CHARS - len(marker)
    head = remaining * 2 // 3
    return (
        _utf8_prefix(value, head) + marker
        + _utf8_suffix(value, remaining - head)
    )


def _is_negative_reply(value: str) -> bool:
    """Return whether a short reply declines the pending action."""
    reply = _normalized_reply(value)
    for prefix in MCP_NEGATIVE_PREFIXES:
        if reply == prefix or reply.startswith(prefix + " "):
            remainder = reply[len(prefix):].strip(" ,;:-")
            replacements = (
                " and use ", "; use ", " instead use ", " and search ",
                "; search ", " instead search ", " and research ",
                "; research ", " instead research ",
            )
            if _contains_any(" " + remainder + " ", replacements):
                return False
            if prefix in ("no", "nope", "nein") and remainder.startswith(
                (
                    "use ", "using ", "search ", "research ", "open ",
                    "browse ", "navigate ", "suche ", "recherch",
                )
            ):
                return False
            return True
    return False


def _response_defers_completed_work(value: str) -> bool:
    """Return whether a short answer only promises or requests MCP work."""
    if not isinstance(value, str):
        return False
    text = " ".join(value.lower().strip().split())
    if not text or len(text) > 1200:
        return False
    # Look near the start so a useful answer followed by an optional offer is
    # not mistaken for a refusal to answer.
    opening = text[:384]
    marker_index = len(opening)
    for marker in MCP_DEFERRAL_MARKERS:
        index = opening.find(marker)
        if 0 <= index < marker_index:
            marker_index = index
    if marker_index == len(opening):
        return False
    deferred = opening[marker_index:]
    if deferred.startswith((
        "i need to state", "i need to note", "i need to explain",
        "i need to clarify",
    )):
        return False
    prefix = opening[:marker_index]
    if "." in prefix or "!" in prefix or "?" in prefix:
        preamble = prefix
        for separator in (".", "!", "?", ",", ":", ";"):
            preamble = preamble.replace(separator, " ")
        preamble = " ".join(preamble.split())
        if (
            preamble not in MCP_DEFERRAL_PREAMBLES
            and not _contains_any(
                preamble, MCP_PENDING_LIMITATION_PREAMBLES
            )
            and not _contains_any(preamble, MCP_LIMITATION_PREAMBLES)
        ):
            return False
    action_text = " " + opening + " "
    for separator in (".", "!", "?", ",", ":", ";"):
        action_text = action_text.replace(separator, " ")
    return _contains_any(action_text, MCP_CONTINUATION_ACTIONS)


def _assistant_needs_mcp_followup(value: str) -> bool:
    """Return whether the immediately preceding answer left MCP work pending."""
    if not isinstance(value, str):
        return False
    text = " " + value.lower().strip() + " "
    return (
        _response_defers_completed_work(value)
        or _contains_any(text, MCP_CLARIFICATION_MARKERS)
        or (
            _contains_any(text, MCP_CONTINUATION_QUESTIONS)
            and _contains_any(text, MCP_CONTINUATION_ACTIONS)
        )
    )


def _declines_pending_mcp(user_message: str, conversation) -> bool:
    """Return whether the user cancels the immediately pending MCP action."""
    return _is_negative_reply(user_message) and _has_pending_mcp_context(
        conversation
    )


def _has_pending_mcp_context(conversation) -> bool:
    """Return whether the latest visible answer is awaiting MCP follow-up."""
    if not conversation:
        return False
    previous = conversation[-1]
    return (
        isinstance(previous, dict)
        and previous.get("role") == "assistant"
        and _assistant_needs_mcp_followup(previous.get("content", ""))
    )


def _mcp_reference_needs_topic(user_message: str) -> bool:
    """Return whether a short explicit integration reference lacks a target."""
    if len(user_message) > 64:
        return False
    text = " " + user_message.lower().strip() + " "
    if _contains_any(text, ("http://", "https://", "www.")):
        return False
    if not _contains_any(
        text, (" use ", " using ", " with ", " via ", " try ")
    ):
        return False
    if _contains_any(
        text, (" for this ", " for that ", " with this ", " with that ")
    ):
        return True
    # A bare short label is a selection, not a task.  Dynamic names cannot be
    # hardcoded here, so retain any message that already contains a task verb.
    if _contains_any(
        text,
        (
            " search ", " research ", " open ", " navigate ", " browse ",
            " fetch ", " read ", " inspect ", " find ", " check ",
            " suche ", " recher", " öffn",
        ),
    ):
        return False
    return len(text.split()) <= 5


def _clean_model_content(value: str) -> str:
    """Remove hidden-reasoning tags from visible model output."""
    text = value if isinstance(value, str) else str(value)
    while True:
        start = text.find("<think>")
        if start < 0:
            break
        end = text.find("</think>", start + 7)
        text = text[:start] + (text[end + 8:] if end >= 0 else "")
    return text.replace("</think>", "").strip()


def _sse_event_data(raw):
    """Extract SSE data fields with one bounded copy."""
    data = None
    saw_field = False
    start = 0
    total = len(raw)
    while start <= total:
        end = raw.find(b"\n", start)
        if end < 0:
            end = total
        line_end = end - 1 if end > start and raw[end - 1] == 13 else end
        if raw[start:start + 5] == b"data:":
            saw_field = True
            value_start = start + 5
            if value_start < line_end and raw[value_start] == 32:
                value_start += 1
            if data is None:
                data = bytearray()
            elif data:
                data.extend(b"\n")
            data.extend(raw[value_start:line_end])
        elif raw[start:start + 1] == b":" or raw[start:start + 6] in (
            b"event:", b"retry:",
        ) or raw[start:start + 3] == b"id:":
            saw_field = True
        if end >= total:
            break
        start = end + 1
    if data is not None:
        return data
    return None if saw_field else raw


def _trim_event_data(data):
    """Trim ASCII event whitespace without copying clean data."""
    start = 0
    end = len(data)
    while start < end and data[start] in (9, 10, 13, 32):
        start += 1
    while end > start and data[end - 1] in (9, 10, 13, 32):
        end -= 1
    return data if start == 0 and end == len(data) else data[start:end]


def _request_tool_names(mode: int, topic: str, has_evidence: bool = False):
    """Return only tools relevant to the current Agent mode and request."""
    if mode == MODE_APP_CREATOR:
        return APP_CREATOR_TOOL_NAMES
    if mode == MODE_DEVICE_MANAGER:
        return DEVICE_MANAGER_TOOL_NAMES
    if mode != MODE_CHAT or has_evidence:
        return ()

    text = topic.lower()
    names = []
    if _contains_any(
        text,
        (
            "device info", "system info", "network info", "wifi status",
            "wi-fi status", "free heap", "free memory", "board info",
            "current time", "what time", "current date", "what date",
        ),
    ):
        names.append("network_get_info")
    if ("wifi" in text or "wi-fi" in text) and _contains_any(
        text, ("scan", "nearby", "available network", "list network")
    ):
        names.append("network_scan_wifi")
    if ("bluetooth" in text or " ble " in " " + text + " ") and _contains_any(
        text, ("scan", "nearby", "available device", "list device")
    ):
        names.append("network_scan_ble")
    if "http://" in text or "https://" in text:
        names.append("network_send_request")
    return tuple(names)


class ChatCompletionStreamSink:
    """Incrementally retain bounded Chat Completions answer/tool deltas."""

    __slots__ = (
        "http", "buffer", "content", "tool_calls", "tool_argument_chars",
        "total_bytes", "spooled_bytes", "event_count", "error", "complete",
        "finish_reason", "storage", "path", "file",
    )

    def __init__(self, http, storage=None, path: str = ""):
        self.http = http
        self.buffer = bytearray()
        self.content = bytearray()
        self.tool_calls = []
        self.tool_argument_chars = 0
        self.total_bytes = 0
        self.spooled_bytes = 0
        self.event_count = 0
        self.error = ""
        self.complete = False
        self.finish_reason = None
        self.storage = storage
        self.path = path
        self.file = None
        if storage is not None and path:
            storage.remove(path)
            self.file = storage.file_open(path)
            if self.file is None:
                self.error = "could not open the temporary model stream spool"

    def close(self) -> None:
        if self.file is not None:
            try:
                self.storage.file_close(self.file)
            except OSError:
                pass
            self.file = None

    def _stop(self, error: str) -> None:
        if not self.error:
            self.error = error
        self.http.close()

    def _tool_call(self, index: int):
        if index < 0 or index >= MAX_TOOL_CALLS_PER_RUN:
            self._stop("model returned too many streamed tool calls")
            return None
        while len(self.tool_calls) <= index:
            self.tool_calls.append({
                "id": "",
                "type": "function",
                "function": {"name": "", "arguments": bytearray()},
            })
        return self.tool_calls[index]

    def _append_content(self, value) -> None:
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    self._append_content(item.get("text", ""))
            return
        if not isinstance(value, str) or not value:
            return
        remaining = MAX_MESSAGE_CHARS - len(self.content)
        if remaining > 0:
            encoded = value.encode("utf-8")
            self.content.extend(encoded[:remaining])

    def _append_tool_calls(self, values) -> None:
        if not isinstance(values, list):
            return
        for position, value in enumerate(values):
            if not isinstance(value, dict):
                continue
            try:
                index = int(value.get("index", position))
            except (TypeError, ValueError):
                index = position
            call = self._tool_call(index)
            if call is None:
                return
            call_id = value.get("id", "")
            if isinstance(call_id, str) and call_id:
                if len(call["id"]) + len(call_id) > MAX_CHAT_TOOL_ID_CHARS:
                    self._stop("streamed tool-call ID exceeded the device limit")
                    return
                call["id"] += call_id
            call_type = value.get("type")
            if isinstance(call_type, str) and call_type:
                if len(call_type) > MAX_CHAT_TOOL_TYPE_CHARS:
                    self._stop(
                        "streamed tool-call type exceeded the device limit"
                    )
                    return
                call["type"] = call_type
            function = value.get("function", {})
            if not isinstance(function, dict):
                continue
            name = function.get("name", "")
            if isinstance(name, str) and name:
                if (
                    len(call["function"]["name"]) + len(name)
                    > MAX_CHAT_TOOL_NAME_CHARS
                ):
                    self._stop(
                        "streamed tool name exceeded the device limit"
                    )
                    return
                call["function"]["name"] += name
            arguments = function.get("arguments", "")
            if not isinstance(arguments, str) or not arguments:
                continue
            encoded = arguments.encode("utf-8")
            next_total = self.tool_argument_chars + len(encoded)
            if next_total > MAX_CHAT_TOOL_ARGUMENT_CHARS:
                self._stop("streamed tool arguments exceeded the device limit")
                return
            call["function"]["arguments"].extend(encoded)
            self.tool_argument_chars = next_total

    def _consume_buffered_event(self, event_end: int, delimiter: int) -> None:
        self.event_count += 1
        if self.event_count > MAX_CHAT_STREAM_EVENTS:
            self._stop("model stream exceeded the bounded event limit")
            return
        raw = self.buffer[:event_end]
        self.buffer = self.buffer[event_end + delimiter:]
        data = _sse_event_data(raw)
        raw = None
        if data is None:
            return
        data = _trim_event_data(data)
        if not data:
            return
        if data == b"[DONE]":
            self.complete = True
            return
        try:
            text = data.decode("utf-8")
            data = None
            from gc import collect
            collect()
            payload = json.loads(text)
            text = ""
        except (UnicodeError, ValueError):
            self._stop("model returned an invalid streaming event")
            return
        if not isinstance(payload, dict):
            return
        detail = payload.get("error")
        if detail:
            message = (
                detail.get("message", str(detail))
                if isinstance(detail, dict) else str(detail)
            )
            self._stop(str(message)[:MAX_CHAT_ERROR_CHARS])
            return
        choices = payload.get("choices", [])
        if not isinstance(choices, list):
            return
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            delta = choice.get("delta")
            if not isinstance(delta, dict):
                delta = choice.get("message", {})
            if isinstance(delta, dict):
                self._append_content(delta.get("content", ""))
                self._append_tool_calls(delta.get("tool_calls", []))
            finish_reason = choice.get("finish_reason")
            if finish_reason is not None:
                if isinstance(finish_reason, str):
                    self.finish_reason = finish_reason[:32]
                else:
                    self.finish_reason = "complete"

    def write(self, value) -> None:
        if self.error or self.complete:
            return
        if not isinstance(value, (bytes, bytearray)) or not value:
            return
        offset = 0
        while offset < len(value) and not self.error and not self.complete:
            end_offset = min(
                offset + MAX_CHAT_WRITE_CHUNK_BYTES, len(value)
            )
            chunk = value[offset:end_offset]
            offset = end_offset
            self.total_bytes += len(chunk)

            # Keep a bounded raw diagnostic trace on SD.  Filling this file is
            # non-fatal because the parsed semantic state has its own RAM caps.
            if (
                self.file is not None
                and self.spooled_bytes < MAX_CHAT_STREAM_BYTES
            ):
                remaining = MAX_CHAT_STREAM_BYTES - self.spooled_bytes
                spool_chunk = chunk[:remaining]
                if spool_chunk and not self.storage.file_write(
                    self.file, spool_chunk, "wb"
                ):
                    self._stop(
                        "could not write the temporary model stream spool"
                    )
                    return
                self.spooled_bytes += len(spool_chunk)

            self.buffer.extend(chunk)
            while True:
                event_end = self.buffer.find(b"\n\n")
                delimiter = 2
                if event_end < 0:
                    event_end = self.buffer.find(b"\r\n\r\n")
                    delimiter = 4
                if event_end < 0:
                    break
                if event_end > MAX_CHAT_EVENT_BYTES:
                    self._stop(
                        "model streaming event exceeded the device limit"
                    )
                    return
                self._consume_buffered_event(event_end, delimiter)
                if self.error or self.complete:
                    break
            if len(self.buffer) > MAX_CHAT_EVENT_BYTES:
                self._stop("model streaming event exceeded the device limit")

    def flush(self) -> None:
        if self.buffer and not self.error and not self.complete:
            self._consume_buffered_event(len(self.buffer), 0)

    def result(self):
        if self.error:
            return None, self.error
        if not self.complete and self.finish_reason is None:
            return None, "model stream ended before completion"
        calls = []
        for call in self.tool_calls:
            function = call.get("function", {})
            if not function.get("name"):
                continue
            arguments = function.get("arguments")
            if isinstance(arguments, (bytes, bytearray)):
                try:
                    arguments = bytes(arguments).decode("utf-8")
                except UnicodeError:
                    return None, "streamed tool arguments were not valid UTF-8"
            function["arguments"] = arguments or "{}"
            calls.append(call)
        raw_content = bytes(self.content)
        content = None
        for trim in range(4):
            try:
                value = raw_content[:-trim] if trim else raw_content
                content = value.decode("utf-8")
                break
            except UnicodeError:
                pass
        if content is None:
            return None, "model content was not valid UTF-8"
        message = {"content": content}
        if calls:
            message["tool_calls"] = calls
        return message, ""

    def http_error(self, status_code: int, reason="") -> str:
        prefix = "model API HTTP " + str(status_code)
        if self.error:
            return prefix + ": " + self.error
        if isinstance(reason, bytes):
            try:
                reason = reason.decode("utf-8")
            except UnicodeError:
                reason = ""
        reason = str(reason).strip()
        return prefix + ((" " + reason) if reason else "")


def _argument_signature(arguments):
    """Return a compact signature without retaining large tool arguments."""
    try:
        value = json.dumps(arguments)
    except (TypeError, ValueError):
        value = str(arguments)
    checksum = 2166136261
    for char in value:
        checksum ^= ord(char)
        checksum = (checksum * 16777619) & 0xFFFFFFFF
    return len(value), checksum


def _tool_loop_issue(history, name: str, arguments) -> str:
    """Record a tool call and return a loop or budget violation."""
    if len(history) >= MAX_TOOL_CALLS_PER_RUN:
        return "tool-call budget exceeded"

    signature = _argument_signature(arguments)
    repeated = 0
    for previous_name, previous_signature in history:
        if previous_name == name and previous_signature == signature:
            repeated += 1
    if repeated >= MAX_IDENTICAL_TOOL_CALLS:
        return "tool '" + name + "' repeated with identical arguments"

    history.append((name, signature))
    return ""


class Agent:
    """Agent that can perform tasks using tools and LLMs."""
    __slots__ = [
        "mode", "tools", "llm", "mcp", "view_manager", "http", "_file_path",
        "_conv_path", "_mem_path", "_msg_path", "_state_path",
        "_conversation", "_status", "_cancelled",
    ]

    def __init__(self, view_manager, mode: int = MODE_CHAT, llm: LLM = None, file_path: str = "picoware/settings/agent_request.json"):
        """Initialize the agent with a mode, LLM, and request file path.

        Args:
            view_manager (ViewManager): The view manager for storage and threading.
            mode (int): The agent mode constant. Defaults to MODE_CHAT.
            llm (LLM): The LLM client to use. Defaults to None.
            file_path (str): Path to the API request file. Defaults to "picoware/settings/agent_request.json".
        """
        from picoware.system.http import HTTP
        self.view_manager = view_manager
        self.mode = mode
        self.tools = []
        self.llm = llm if llm is not None else LLM(view_manager.storage, DEEPSEEK)
        self.http = HTTP(thread_manager=view_manager.thread_manager)
        from picoware.system.agent.mcp import create_mcp_client
        self.mcp = create_mcp_client(view_manager, self.http, self.llm)
        self._file_path = file_path
        self._conv_path = "picoware/settings/agent_conv.json"
        self._mem_path = "picoware/settings/agent_mem.json"
        self._msg_path = "picoware/settings/agent_msg.json"
        self._state_path = "picoware/settings/agent_state_" + str(mode) + ".json"
        self._conversation = []
        self._status = "Ready"
        self._cancelled = False

        s = self.view_manager.storage
        s.remove(self._conv_path)
        s.remove(self._mem_path)
        s.remove(self._msg_path)
        self._load_state()

    def __del__(self):
        """Cleanup resources on deletion."""
        self.tools.clear()
        self.mcp = None
        self.llm = None
        self.http = None

    @property
    def file_path(self) -> str:
        """Get the file path associated with the agent."""
        return self._file_path

    @property
    def conversation(self) -> list:
        """Return a copy of the visible persisted conversation."""
        return list(self._conversation)

    @property
    def status(self) -> str:
        """Return the current user-facing execution phase."""
        return self._status

    def cancel(self) -> None:
        """Request cancellation of the active HTTP/tool loop."""
        self._cancelled = True
        self._status = "Cancelling..."
        if self.http is not None:
            self.http.close()

    def reset_conversation(self) -> None:
        """Clear the current mode's persisted conversation."""
        self._conversation = []
        self.view_manager.storage.remove(self._state_path)

    def _fingerprint(self) -> str:
        """Identify the provider, model, and Agent mode for persisted state."""
        integrations = ""
        if self.mcp is not None:
            integrations = ",".join(self.mcp.integrations)
        return (
            str(self.llm.id) + "|" + str(self.mode) + "|" + self.llm.model
            + "|" + integrations
        )

    def _load_state(self) -> None:
        storage = self.view_manager.storage
        if not storage.exists(self._state_path):
            return
        state = storage.serialize(self._state_path)
        if not isinstance(state, dict) or state.get("fingerprint") != self._fingerprint():
            return
        self._conversation = self._sanitize_conversation(state.get("conversation"))

    def _save_state(self) -> None:
        self.view_manager.storage.deserialize(
            {
                "fingerprint": self._fingerprint(),
                "conversation": self._conversation,
            },
            self._state_path,
        )

    def _parse_tool_arguments(self, raw_args) -> dict:
        """Parse tool-call arguments defensively into a dict.

        Args:
            raw_args (str or dict): Raw arguments from the model call.

        Returns:
            dict: The parsed arguments, or an empty dict if unparseable.
        """
        if isinstance(raw_args, dict):
            return raw_args

        if not isinstance(raw_args, str):
            return {}

        text = raw_args.strip()
        if not text:
            return {}

        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {}
        except ValueError:
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return {}
            try:
                parsed = json.loads(text[start : end + 1])
                return parsed if isinstance(parsed, dict) else {}
            except ValueError:
                return {}

    def _conv_write_initial(self, messages: list[dict]) -> None:
        """Write the initial conversation messages to the conversation file.

        Args:
            messages (list[dict]): The initial messages to store.
        """
        storage = self.view_manager.storage

        for i, msg in enumerate(messages):
            if i == 0:
                if msg.get("role") == "system":
                    self._write_system_message(storage)
                else:
                    storage.write(self._conv_path, json.dumps(msg), mode="w")
            else:
                storage.write(self._conv_path, ',' + json.dumps(msg), mode="a")

    def _conv_append(self, message: dict) -> None:
        """Append one message to the conversation file.

        Args:
            message (dict): The message to append.
        """
        storage = self.view_manager.storage

        if not storage.exists(self._conv_path):
            storage.write(self._conv_path, json.dumps(message), mode="w")
        else:
            storage.write(self._conv_path, ',' + json.dumps(message), mode="a")

    @staticmethod
    def _append_json_escaped_text(storage, path: str, text: str) -> None:
        """Append text to a JSON string in small temporary heap chunks."""
        if not isinstance(text, str):
            text = str(text)
        for offset in range(0, len(text), 1024):
            storage.write(
                path,
                Agent._json_escape(text[offset:offset + 1024]),
                mode="a",
            )

    def _conv_append_user_request(self, request: str, evidence: str = "") -> None:
        """Append the final user request while keeping evidence SD-first."""
        storage = self.view_manager.storage
        prefix = ',' if storage.exists(self._conv_path) else ''
        storage.write(
            self._conv_path,
            prefix + '{"role":"user","content":"',
            mode="a" if prefix else "w",
        )
        self._append_json_escaped_text(storage, self._conv_path, request)
        if evidence:
            self._append_json_escaped_text(
                storage, self._conv_path, MCP_EVIDENCE_PREAMBLE
            )
            self._append_json_escaped_text(storage, self._conv_path, evidence)
        storage.write(self._conv_path, '"}', mode="a")

    @staticmethod
    def _json_escape(text: str) -> str:
        """Escape a string for embedding in JSON.

        Args:
            text (str): The raw string to escape.

        Returns:
            str: The JSON-escaped string.
        """
        # Delegate the full U+0000..U+001F set to the JSON implementation.
        # Callers pass at most a small chunk, so the temporary string is bounded.
        encoded = json.dumps(text)
        return encoded[1:-1]

    @staticmethod
    def _stream_file_json_escaped(storage, src_path: str, dst_path: str) -> None:
        """Stream a file to the destination with JSON escaping.

        Args:
            storage (Storage): The storage interface.
            src_path (str): The source file path.
            dst_path (str): The destination file path.
        """
        src = storage.file_open(src_path)
        if src is None:
            return
        try:
            buf = bytearray(2048)
            pending = b""
            while True:
                n = storage.file_readinto(src, buf)
                if not n:
                    break
                raw = pending + bytes(buf[:n])
                chunk = None
                used = 0
                for trim in range(4):
                    candidate = raw[:-trim] if trim else raw
                    try:
                        chunk = candidate.decode("utf-8")
                        used = len(candidate)
                        break
                    except UnicodeError:
                        pass
                if chunk is None:
                    # Raise the original decoding failure for invalid data that
                    # is not merely a split trailing UTF-8 code point.
                    raw.decode("utf-8")
                pending = raw[used:]
                if not chunk:
                    continue
                storage.write(dst_path, Agent._json_escape(chunk), mode="a")
            if pending:
                storage.write(
                    dst_path,
                    Agent._json_escape(pending.decode("utf-8")),
                    mode="a",
                )
        finally:
            storage.file_close(src)

    def _write_system_message(self, storage) -> None:
        """Write the system message to the conversation file.

        Args:
            storage (Storage): The storage interface.
        """
        storage.write(self._conv_path, '{"role":"system","content":"', mode="w")
        if storage.exists(self._mem_path):
            self._stream_file_json_escaped(storage, self._mem_path, self._conv_path)
        storage.write(self._conv_path, '"}', mode="a")

    def _build_request(
        self, tools: list[dict], require_visible_answer: bool = False,
        correct_deferral: bool = False,
    ) -> None:
        """Stream the conversation and metadata into the API request file.

        Args:
            tools (list[dict]): The tool schemas to include in the request.
        """
        storage = self.view_manager.storage

        # Preamble: model + messages open
        storage.write(
            self._file_path,
            '{"model":' + json.dumps(self.llm.model) + ',"messages":[',
            mode="w",
        )

        # Stream conversation file
        conv_file = storage.file_open(self._conv_path)
        if conv_file is not None:
            try:
                buf = bytearray(2048)
                while True:
                    n = storage.file_readinto(conv_file, buf)
                    if not n:
                        break
                    storage.write(self._file_path, buf[:n], mode="ab")
            finally:
                storage.file_close(conv_file)

        if require_visible_answer:
            storage.write(
                self._file_path,
                ',{"role":"user","content":"The previous completion '
                'contained no visible answer. Return one concise visible '
                'answer now."}',
                mode="a",
            )
        if correct_deferral:
            storage.write(
                self._file_path,
                ',{"role":"user","content":'
                + json.dumps(MCP_FINAL_RETRY_GUARD) + "}",
                mode="a",
            )
        storage.write(self._file_path, "]", mode="a")
        if tools:
            storage.write(
                self._file_path,
                ',"tools":' + json.dumps(tools) + ',"tool_choice":"auto"',
                mode="a",
            )
        if self.mode == MODE_APP_CREATOR:
            max_tokens = MAX_APP_OUTPUT_TOKENS
        elif self.mode == MODE_DEVICE_MANAGER:
            max_tokens = MAX_MANAGER_OUTPUT_TOKENS
        else:
            max_tokens = MAX_CHAT_OUTPUT_TOKENS
        storage.write(
            self._file_path,
            ',"stream":true,"max_tokens":' + str(max_tokens),
            mode="a",
        )

        payload = self.llm.thinking_payload
        if payload:
            payload_str = json.dumps(payload)[1:-1]
            storage.write(self._file_path, "," + payload_str, mode="a")

        # close
        storage.write(self._file_path, "}", mode="a")


    def _mode_tool_limit(self, name: str) -> int:
        """Return small per-turn limits for expensive reference/network tools."""
        if name in (
            "network_get_info", "network_scan_wifi", "network_scan_ble",
            "network_send_request",
        ):
            return 1
        if self.mode != MODE_APP_CREATOR:
            return 0
        if name == "picoware_api_search":
            return 2
        if name in ("picoware_api_read", "picoware_app_validate"):
            return 4
        return 0

    def _chat_completion_tools(self, counts, allowed_names=None) -> list:
        """Return Chat Completions schemas, hiding exhausted one-shot tools."""
        if allowed_names is None:
            allowed_names = _request_tool_names(self.mode, "")
        tools = []
        for tool in dispatch.get_tool_list():
            if tool.name not in allowed_names:
                continue
            limit = self._mode_tool_limit(tool.name)
            if not limit or counts.get(tool.name, 0) < limit:
                tools.append(tool.json_openai)
        return tools

    def _execute_tool(self, history, cache, counts, name: str, arguments):
        """Execute one guarded tool call and reuse same-batch successful results."""
        signature = (name, _argument_signature(arguments))
        limit = self._mode_tool_limit(name)
        if limit and counts.get(name, 0) >= limit:
            if signature in cache:
                return cache[signature]
            return {
                "ok": False,
                "error": "tool_budget_exhausted",
                "message": name + " reached its per-turn limit",
            }

        issue = _tool_loop_issue(history, name, arguments)
        if issue:
            raise RuntimeError("Tool loop stopped before execution: " + issue + ".")
        if self._cancelled:
            raise RuntimeError("Agent request cancelled.")

        counts[name] = counts.get(name, 0) + 1
        self._status = "Tool: " + name
        self.view_manager.log("[Agent] Executing " + name)
        try:
            result = dispatch.execute_tool(self.view_manager, name, arguments)
        except (KeyError, OSError, TypeError, ValueError) as exc:
            result = {
                "ok": False,
                "error": "tool_error",
                "message": str(exc),
            }
        if not isinstance(result, dict) or result.get("ok", True):
            cache[signature] = result
        self.view_manager.log("[Agent] " + name + " completed")
        return result

    def _run_loop(
        self, allowed_tool_names=None, has_evidence: bool = False,
    ) -> str:
        """Run a provider-neutral Chat Completions tool loop."""
        storage = self.view_manager.storage
        history = []
        cache = {}
        counts = {}
        empty_response_retried = False
        deferred_response_retried = False
        if allowed_tool_names is None:
            allowed_tool_names = _request_tool_names(self.mode, "")

        for _ in range(MAX_TOOL_ITERATIONS):
            if self._cancelled:
                return "An error occurred during processing: Agent request cancelled."

            self._status = "Model request"
            self._build_request(
                self._chat_completion_tools(counts, allowed_tool_names),
                require_visible_answer=empty_response_retried,
                correct_deferral=deferred_response_retried,
            )
            sink = ChatCompletionStreamSink(
                self.http, storage, self._msg_path
            )
            response = None
            status_code = 0
            reason = ""
            try:
                if not sink.error:
                    response = self.http.post(
                        self.llm.url,
                        headers=self.llm.headers,
                        payload=None,
                        timeout=120,
                        storage=storage,
                        send_file=self._file_path,
                        stream_sink=sink,
                    )
                    if response is not None:
                        status_code = response.status_code
                        reason = response.reason
            finally:
                if response is not None:
                    response.close()
                sink.close()
                storage.remove(self._msg_path)
                from gc import collect
                collect()
            if response is None:
                if sink.error:
                    return "API error: " + sink.error
                return "API error: model API returned no response."
            if not 200 <= status_code <= 299:
                return "API error: " + sink.http_error(status_code, reason)
            message, stream_error = sink.result()
            if stream_error:
                return "API error: " + stream_error

            tool_calls = message.get("tool_calls")
            if not tool_calls:
                content = _clean_model_content(message.get("content", ""))
                if not content:
                    if not empty_response_retried:
                        empty_response_retried = True
                        self.view_manager.log(
                            "[Agent] Retrying empty model response"
                        )
                        continue
                    return "API error: model returned no visible response."
                if has_evidence and _response_defers_completed_work(content):
                    if not deferred_response_retried:
                        deferred_response_retried = True
                        self.view_manager.log(
                            "[Agent] Correcting deferred MCP answer"
                        )
                        continue
                    return (
                        "API error: model did not provide a final answer from "
                        "the completed integration evidence."
                    )
                self._conv_append({"role": "assistant", "content": content})
                self.view_manager.log("[Agent] Final response complete")
                return content
            if not isinstance(tool_calls, list):
                return "API error: model API returned invalid tool calls."

            parsed_calls = []
            for tool_call in tool_calls:
                try:
                    function = tool_call["function"]
                    name = function["name"]
                    arguments = self._parse_tool_arguments(
                        function.get("arguments", "{}")
                    )
                except (KeyError, TypeError):
                    return "API error: model API returned an invalid tool call."
                if name not in allowed_tool_names:
                    return "API error: model requested an unavailable tool: " + name
                parsed_calls.append((tool_call, name, arguments))

            assistant_message = {"role": "assistant", "tool_calls": tool_calls}
            if message.get("content") is not None:
                assistant_message["content"] = message["content"]
            self._conv_append(assistant_message)

            for tool_call, name, arguments in parsed_calls:
                try:
                    result = self._execute_tool(
                        history, cache, counts, name, arguments
                    )
                except RuntimeError as exc:
                    return str(exc)
                content = json.dumps(result) if isinstance(result, (dict, list)) else str(result)
                self._conv_append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", "unknown_tool_call"),
                        "content": content,
                    }
                )

        return "An error occurred during processing: Tool loop exceeded max iterations."
    
    def _sanitize_conversation(
        self,
        conversation: list[dict] | None,
        max_messages: int = MAX_CONVERSATION_MESSAGES,
    ) -> list[dict[str, str]]:
        """Normalize history to user and assistant text messages only.

        Args:
            conversation (list[dict] or None): Raw message history. Defaults to None.
            max_messages (int): Maximum messages to keep. Defaults to MAX_CONVERSATION_MESSAGES.

        Returns:
            list[dict[str, str]]: The sanitized message list.
        """
        if not isinstance(conversation, list):
            return []

        sanitized: list[dict[str, str]] = []
        for message in conversation:
            if not isinstance(message, dict):
                continue

            role = message.get("role")
            content = message.get("content")
            if role not in {"user", "assistant"}:
                continue
            if not isinstance(content, str):
                continue

            text = content.strip()
            if not text:
                continue

            if role == "assistant":
                text = _clean_model_content(text)
                if not text:
                    continue

            if role == "assistant" and text.startswith(ERROR_RESPONSE_PREFIXES):
                if sanitized and sanitized[-1].get("role") == "user":
                    sanitized.pop()
                continue
            text = _bounded_request_text(text)

            sanitized.append({"role": role, "content": text})

        if len(sanitized) > max_messages > 0:
            sanitized = sanitized[-max_messages:]

        # The UI supplies the new prompt separately. A trailing user message
        # here is an incomplete turn left by an interrupted request.
        while sanitized and sanitized[-1].get("role") == "user":
            sanitized.pop()

        bounded = []
        total = 0
        for message in reversed(sanitized):
            size = _utf8_byte_size(message["content"])
            if bounded and total + size > MAX_CONVERSATION_BYTES:
                break
            bounded.append(message)
            total += size
        bounded.reverse()
        return bounded

    def _write_mode_context(self, context=None) -> None:
        """Write one compact provider-neutral system context to SD."""
        storage = self.view_manager.storage
        storage.remove(self._mem_path)
        if context is not None:
            storage.write(self._mem_path, context.strip() + "\n", mode="w")
            return

        file_obj = storage.file_open(self._mem_path)
        if file_obj is None:
            raise OSError("could not create Agent context file")
        try:
            if self.mode == MODE_CHAT:
                values = (chat.PROMPT, chat.WORKFLOW, chat.CONTEXT)
            elif self.mode == MODE_APP_CREATOR:
                values = (
                    app_creator.PROMPT,
                    app_creator.WORKFLOW,
                    app_creator.COMPACT_CONTEXT,
                )
            else:
                values = (
                    device_manager.PROMPT,
                    device_manager.WORKFLOW,
                    device_manager.CONTEXT,
                )
            for value in values:
                storage.file_write(file_obj, value, mode="wb")
                storage.file_write(file_obj, b"\n", mode="wb")
        finally:
            storage.file_close(file_obj)

    def _mcp_request_message(self, user_message: str) -> str:
        """Resolve a bounded pending MCP task from visible conversation."""
        if self.mcp is None:
            return user_message
        conversation = self._conversation
        current_selected = self.mcp.selected_integrations(user_message)
        explicit_selector = getattr(self.mcp, "explicit_selection", None)
        if explicit_selector is None:
            current_explicit = current_selected
        else:
            current_explicit, _ambiguous = explicit_selector(user_message)
        if len(conversation) < 2:
            return user_message

        previous_answer = conversation[-1]
        previous_request = conversation[-2]
        if (
            previous_answer.get("role") != "assistant"
            or previous_request.get("role") != "user"
        ):
            return user_message
        answer = previous_answer.get("content", "")
        if not _assistant_needs_mcp_followup(answer):
            return user_message
        if _is_negative_reply(user_message):
            return user_message
        answer_text = " " + answer.lower().strip() + " "
        is_clarification = _contains_any(
            answer_text, MCP_CLARIFICATION_MARKERS
        )

        prior_text = previous_request.get("content", "")
        prior_selected = self.mcp.selected_integrations(prior_text)

        # An exact-label response to our own clarification must retain the
        # substantive request that caused the clarification.
        if current_explicit:
            return (
                "Complete the preceding request. The selected configured "
                "integrations are in the user instruction.\n\nPrevious topic:\n"
                + prior_text
                + "\n\nUser instruction:\n" + user_message
            )

        reply = _normalized_reply(user_message)
        if reply in MCP_AFFIRMATIVE_REPLIES:
            # Walk only the local pending-action chain.  Every skipped user
            # turn must itself be an affirmative response, and every skipped
            # assistant turn must still describe pending integration work.
            user_index = len(conversation) - 2
            minimum = max(-1, len(conversation) - 7)
            while user_index > minimum:
                candidate = conversation[user_index]
                if candidate.get("role") != "user":
                    break
                candidate_text = candidate.get("content", "")
                candidate_selected = self.mcp.selected_integrations(
                    candidate_text
                )
                if candidate_selected:
                    original_text = candidate_text
                    if user_index >= 2:
                        clarification = conversation[user_index - 1]
                        original = conversation[user_index - 2]
                        if (
                            clarification.get("role") == "assistant"
                            and original.get("role") == "user"
                            and "exact integration label" in clarification.get(
                                "content", ""
                            ).lower()
                        ):
                            original_text = original.get("content", "")
                    return (
                        "Continue the pending integration request and answer it "
                        "without another approval step.\n\nOriginal request:\n"
                        + original_text + "\n\nIntegration selection:\n"
                        + candidate_text + "\n\nUser confirmation:\n"
                        + user_message
                    )
                if _normalized_reply(candidate_text) not in MCP_AFFIRMATIVE_REPLIES:
                    break
                assistant_index = user_index - 1
                if assistant_index < 0:
                    break
                pending_answer = conversation[assistant_index]
                if (
                    pending_answer.get("role") != "assistant"
                    or not _assistant_needs_mcp_followup(
                        pending_answer.get("content", "")
                    )
                ):
                    break
                user_index -= 2

        if prior_selected and is_clarification:
            return (
                "Continue the immediately preceding integration request. "
                "Apply the user's clarification.\n\nPrevious request:\n"
                + prior_text + "\n\nUser clarification:\n" + user_message
            )
        return user_message


    def run(self, topic: str, conversation: list[dict] | None = None, context=None) -> str:
        """Run the agent for a prompt and return the response text.

        Args:
            topic (str): The user prompt.
            conversation (list[dict] or None): Prior message history. Defaults to None.
            context (str or None): Extra context prepended to the system prompt. Defaults to None.

        Returns:
            str: The assistant response text, or an error message.
        """
        user_message = _bounded_request_text(topic.strip())
        if not user_message:
            return "No message provided."
        if not self.llm.model:
            return (
                "API error: No local model is configured. Open Agent Settings, "
                "load a model on the local server, and select its exact ID."
            )
        
        self._cancelled = False
        self._status = "Preparing"
        self._conversation = self._sanitize_conversation(conversation)
        declined_mcp = _declines_pending_mcp(
            user_message, self._conversation
        )
        storage = self.view_manager.storage
        try:
            if (
                self.mcp is not None and self.mcp.enabled
                and not declined_mcp
            ):
                explicit_selector = getattr(
                    self.mcp, "explicit_selection", None
                )
                if explicit_selector is not None:
                    explicit, ambiguous = explicit_selector(user_message)
                    if ambiguous:
                        return MCP_EXACT_LABEL_CLARIFICATION
                    if (
                        explicit
                        and _mcp_reference_needs_topic(user_message)
                        and not _has_pending_mcp_context(self._conversation)
                    ):
                        return MCP_TOPIC_CLARIFICATION
            self._write_mode_context(context)
            effective_request = _bounded_request_text(
                self._mcp_request_message(user_message)
            )
            has_evidence = False
            evidence = ""
            if (
                self.mcp is not None and self.mcp.enabled
                and not declined_mcp
            ):
                self._status = "MCP research"
                evidence, error = self.mcp.research(effective_request)
                if error:
                    return "API error: " + error
                if evidence:
                    has_evidence = True
                    self.view_manager.storage.write(
                        self._mem_path,
                        "\n" + MCP_FINAL_ANSWER_GUARD + "\n",
                        mode="a",
                    )
            messages = [{"role": "system", "content": ""}]
            messages.extend(self._conversation)
            self._conv_write_initial(messages)
            self._conv_append_user_request(effective_request, evidence)
            # The evidence is now in the temporary SD conversation file; do
            # not retain a duplicate while the final model stream is running.
            evidence = ""
            effective_request = ""
            from gc import collect
            collect()
            return self._run_loop(
                _request_tool_names(self.mode, user_message, has_evidence),
                has_evidence=has_evidence,
            )
        except Exception as exc:
            self._status = "Error"
            return f"An error occurred during processing: {exc}"
        finally:
            for path in (
                self._file_path, self._conv_path,
                self._mem_path, self._msg_path,
            ):
                storage.remove(path)
            from gc import collect
            collect()

    def run_payload(self, payload: dict) -> dict:
        """Run the agent with a JSON payload and return a structured response.

        Args:
            payload (dict): The request payload with message and conversation keys.

        Returns:
            dict: The response with status, message, and conversation keys.
        """
        if not isinstance(payload, dict):
            return {
                "status": "error",
                "message": "Invalid payload format.",
                "conversation": [],
            }

        topic = payload.get("message") or payload.get("topic")
        raw_conversation = payload.get("conversation")
        conversation = (
            self._sanitize_conversation(raw_conversation)
            if raw_conversation is not None
            else list(self._conversation)
        )

        if not isinstance(topic, str) or not topic.strip():
            return {
                "status": "error",
                "message": "No message provided.",
                "conversation": conversation,
            }

        topic = _bounded_request_text(topic.strip())
        message = self.run(topic, conversation=conversation)
        status = (
            "error"
            if isinstance(message, str)
            and message.startswith(ERROR_RESPONSE_PREFIXES)
            else "completed"
        )

        turn = [
            {"role": "user", "content": topic},
            {"role": "assistant", "content": message},
        ]
        if status == "error":
            # Show the failure for this UI session, but do not save it as
            # model history for the next request.
            turn_conversation = list(conversation)
            turn_conversation.extend(turn)
        else:
            turn_conversation = self._sanitize_conversation(
                conversation + turn
            )

        self._conversation = conversation if status == "error" else turn_conversation
        self._status = "Error" if status == "error" else "Complete"
        self._save_state()

        return {
            "status": status,
            "message": message,
            "conversation": turn_conversation,
        }
