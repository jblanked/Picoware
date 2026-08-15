"""Agent - LLM-powered assistant with tools."""

import json
from micropython import const
from picoware.system.agent.tools import dispatch
from picoware.system.agent.llm import LLM, DEEPSEEK, native_mcp_url
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
MAX_NATIVE_RESPONSE_ID_LENGTH = const(512)
MAX_MODEL_OUTPUT_TOKENS = const(4096)
MAX_NATIVE_RESEARCH_TOKENS = const(768)
MAX_NATIVE_MCP_CALLS = const(4)
MAX_NATIVE_EVIDENCE_CHARS = const(8192)
MAX_PROVIDER_RESPONSE_BYTES = const(262144)
MAX_NATIVE_SSE_EVENT_BYTES = const(16384)
MAX_NATIVE_STREAM_BYTES = const(262144)
MAX_SCAN_RESPONSE_BYTES = const(32768)
INTEGRATION_CATALOG_ID = "mcp/picoware-integration-catalog"


def _current_time_grounding(view_manager) -> str:
    """Build cutoff-safe current-time guidance for LM Studio MCP requests."""
    from picoware.system.agent.tools.network import network_get_time_info

    info = network_get_time_info(view_manager)
    current = info["current_local_datetime"]
    if info["clock_is_set"] and current:
        return (
            "\n\n# Current date and time\n"
            "The Picoware device clock is set. The current local date and "
            "time is " + current + " (configured UTC offset "
            + info["utc_offset"] + "). Use this date when interpreting "
            "words such as today, latest, current, tomorrow, and yesterday. "
            "For facts newer than the model's training cutoff, use an "
            "available web or research tool instead of relying on model "
            "memory."
        )

    return (
        "\n\n# Current date and time\n"
        "The Picoware device clock is not set. Do not guess the current date "
        "from model training data. For requests involving today, latest, "
        "current, tomorrow, or yesterday, call an available current-time "
        "tool first. Use an available web or research tool for facts newer "
        "than the model's training cutoff."
    )


def _tool_loop_policy() -> str:
    """Return preventive tool-use rules for LM Studio's internal MCP loop."""
    return (
        "\n\n# Tool loop protection\n"
        "Use no more than 16 tool calls for this request. Never repeat a "
        "successful tool call with identical arguments. If a tool fails, "
        "retry at most once and only when the retry can provide new "
        "information. When the available result is sufficient, stop calling "
        "tools and answer. Never repeat a completed action."
    )


def _argument_signature(arguments):
    """Return a bounded signature without retaining large tool arguments."""
    try:
        value = json.dumps(arguments)
    except Exception:
        value = str(arguments)
    checksum = 2166136261
    for char in value:
        checksum ^= ord(char)
        checksum = (checksum * 16777619) & 0xFFFFFFFF
    return len(value), checksum


def _tool_loop_issue(history, name: str, arguments) -> str:
    """Record one tool call and return a loop/budget violation if present."""
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


def _native_tool_loop_issue(output) -> str:
    """Audit LM Studio's completed MCP trace for repeated or excessive calls."""
    history = []
    if not isinstance(output, list):
        return ""

    for item in output:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        if item_type in ("tool_call", "mcp_call", "mcp_tool_call"):
            name = item.get("tool", item.get("name", "unknown"))
            arguments = item.get("arguments", {})
            provider = item.get("provider_info", {})
        elif item_type == "invalid_tool_call":
            metadata = item.get("metadata", {})
            name = metadata.get("tool_name", "invalid_tool_call")
            arguments = metadata.get("arguments", {})
            provider = item.get("provider_info", {})
        else:
            continue

        if not isinstance(provider, dict):
            provider = {}
        provider_id = provider.get("plugin_id", provider.get("server_label", ""))
        qualified_name = (str(provider_id) + ":" if provider_id else "") + str(name)
        issue = _tool_loop_issue(history, qualified_name, arguments)
        if issue:
            return issue
    return ""


def _native_response_id(value) -> str:
    """Return a bounded LM Studio response ID or an empty string."""
    if not isinstance(value, str):
        return ""
    response_id = value.strip()
    if not response_id or len(response_id) > MAX_NATIVE_RESPONSE_ID_LENGTH:
        return ""
    return response_id


class _NativeResearchSink:
    """Consume LM Studio native SSE while enforcing the tool-loop policy."""

    __slots__ = (
        "http", "buffer", "history", "result", "issue", "error", "call_count",
        "evidence", "evidence_chars", "storage", "path", "file", "total_bytes",
        "max_calls", "complete",
    )

    def __init__(
        self, http, storage=None, path: str = "",
        max_calls: int = MAX_NATIVE_MCP_CALLS,
    ):
        self.http = http
        self.buffer = bytearray()
        self.history = []
        self.result = None
        self.issue = ""
        self.error = ""
        self.call_count = 0
        self.evidence = []
        self.evidence_chars = 0
        self.storage = storage
        self.path = path
        self.file = None
        self.total_bytes = 0
        self.max_calls = max(1, min(int(max_calls), MAX_NATIVE_MCP_CALLS))
        self.complete = False
        if storage is not None and path:
            storage.remove(path)
            self.file = storage.file_open(path)
            if self.file is None:
                self.issue = "could not open the MCP SD spool"

    def close(self) -> None:
        """Close the temporary SD spool without retaining its contents in RAM."""
        if self.file is not None:
            try:
                self.storage.file_close(self.file)
            except Exception:
                pass
            self.file = None

    def _stop(self, issue: str) -> None:
        if not self.issue:
            self.issue = issue
        self.http.close()

    def _consume_event(self, raw) -> None:
        # chat.end can contain the complete trace again. Tool evidence was
        # already captured from bounded success events, so do not materialize
        # this duplicate response tree on the Pico heap.
        if raw.find(b'"chat.end"') >= 0:
            self.result = {}
            return
        start = raw.find(b"data:")
        if start < 0:
            return
        start += 5
        while start < len(raw) and raw[start] in (9, 32):
            start += 1
        try:
            event = json.loads(raw[start:].decode("utf-8"))
        except (UnicodeError, ValueError):
            self._stop("LM Studio MCP returned an invalid streaming event")
            return
        if not isinstance(event, dict):
            return
        event_type = event.get("type")
        if event_type == "tool_call.arguments":
            provider = event.get("provider_info", {})
            if not isinstance(provider, dict):
                provider = {}
            provider_id = provider.get("plugin_id", provider.get("server_label", ""))
            name = (str(provider_id) + ":" if provider_id else "") + str(event.get("tool", "unknown"))
            if self.call_count >= self.max_calls:
                self._stop("native MCP tool-call budget exceeded")
                return
            issue = _tool_loop_issue(self.history, name, event.get("arguments", {}))
            if issue:
                self._stop(issue)
                return
            self.call_count += 1
        elif event_type == "tool_call.success":
            output = event.get("output", "")
            if not isinstance(output, str):
                output = str(output)
            remaining = MAX_NATIVE_EVIDENCE_CHARS - self.evidence_chars
            if remaining > 0 and output:
                value = output[:remaining]
                self.evidence.append(value)
                self.evidence_chars += len(value)
            if self.call_count >= self.max_calls:
                # The completed tool output is the evidence needed by the
                # next deterministic stage. End this generation before the
                # model can request another variation of the same tool.
                self.complete = True
                self.http.close()
        elif event_type == "error":
            detail = event.get("error", {})
            self.error = detail.get("message", str(detail)) if isinstance(detail, dict) else str(detail)

    def write(self, value) -> None:
        if self.issue or self.complete:
            return
        if isinstance(value, str):
            # Ignore HTTP's UART-style progress markers.
            return
        if not isinstance(value, (bytes, bytearray)):
            return
        next_total = self.total_bytes + len(value)
        if next_total > MAX_NATIVE_STREAM_BYTES:
            self._stop("LM Studio MCP stream exceeded the 262144-byte device limit")
            return
        if self.file is not None:
            if not self.storage.file_write(self.file, value, "wb"):
                self._stop("could not write the MCP stream to SD")
                return
        self.total_bytes = next_total
        self.buffer.extend(value)
        while True:
            end = self.buffer.find(b"\n\n")
            delimiter = 2
            if end < 0:
                end = self.buffer.find(b"\r\n\r\n")
                delimiter = 4
            if end < 0:
                break
            if end > MAX_NATIVE_SSE_EVENT_BYTES:
                self._stop("LM Studio MCP streaming event exceeded the device limit")
                return
            raw_event = self.buffer[:end]
            # MicroPython bytearray does not implement slice deletion. The
            # remainder is bounded by MAX_NATIVE_SSE_EVENT_BYTES, so replacing
            # this small buffer remains heap-safe.
            self.buffer = self.buffer[end + delimiter:]
            self._consume_event(raw_event)
            if self.issue:
                break
        if len(self.buffer) > MAX_NATIVE_SSE_EVENT_BYTES:
            self._stop("LM Studio MCP streaming event exceeded the device limit")

    def flush(self) -> None:
        return


class Agent:
    """Agent that can perform tasks using tools and LLMs."""
    __slots__ = [
        "mode", "tools", "llm", "view_manager", "http", "_file_path",
        "_conv_path", "_mem_path", "_response_path", "_state_path",
        "_native_response_id", "_conversation", "_status", "_cancelled",
        "_last_stats",
    ]

    def __init__(
        self,
        view_manager,
        mode: int = MODE_CHAT,
        llm: LLM = None,
        file_path: str = "picoware/settings/agent_request.json",
        cleanup: bool = True,
    ):
        """Initialize the agent with a mode, LLM, and request file path.

        Args:
            view_manager (ViewManager): The view manager for storage and threading.
            mode (int): The agent mode constant. Defaults to MODE_CHAT.
            llm (LLM): The LLM client to use. Defaults to None.
            file_path (str): Path to the API request file. Defaults to "picoware/settings/agent_request.json".
            cleanup (bool): Remove prior conversation files. Defaults to True.
        """
        from picoware.system.http import HTTP
        self.view_manager = view_manager
        self.mode = mode
        self.tools = []
        self.llm = llm if llm is not None else LLM(view_manager.storage, DEEPSEEK)
        self.http = HTTP(thread_manager=view_manager.thread_manager)
        self._file_path = file_path
        self._conv_path = "picoware/settings/agent_conv.json"
        self._mem_path = "picoware/settings/agent_mem.json"
        self._response_path = "picoware/settings/agent_response.json"
        self._state_path = "picoware/settings/agent_state_" + str(mode) + ".json"
        self._native_response_id = ""
        self._conversation = []
        self._status = "Ready"
        self._cancelled = False
        self._last_stats = {}

        if cleanup:
            s = self.view_manager.storage
            s.remove(self._conv_path)
            s.remove(self._mem_path)
            s.remove(self._response_path)
        self._load_state()

    def __del__(self):
        """Cleanup resources on deletion."""
        self.tools.clear()
        self.llm = None
        self.http = None

    @property
    def conversation(self) -> list:
        """Return a copy of the persisted visible conversation."""
        return list(self._conversation)

    @property
    def status(self) -> str:
        """Return the current user-facing execution phase."""
        return self._status

    @property
    def last_stats(self) -> dict:
        """Return the last bounded provider statistics."""
        return dict(self._last_stats)

    def cancel(self) -> None:
        """Request cancellation of the active model/tool loop."""
        self._cancelled = True
        self._status = "Cancelling..."
        if self.http is not None:
            self.http.close()

    def reset_conversation(self) -> None:
        """Clear persisted visible and provider-side conversation state."""
        self._native_response_id = ""
        self._conversation = []
        self.view_manager.storage.remove(self._state_path)

    def _fingerprint(self) -> str:
        return (
            str(self.llm.id) + "|" + str(self.mode) + "|" + self.llm.model
            + "|" + ",".join(self.llm.mcp_integrations)
        )

    def _load_state(self) -> None:
        storage = self.view_manager.storage
        if not storage.exists(self._state_path):
            return
        state = storage.serialize(self._state_path)
        if not isinstance(state, dict) or state.get("fingerprint") != self._fingerprint():
            return
        self._native_response_id = _native_response_id(state.get("response_id"))
        self._conversation = self._sanitize_conversation(state.get("conversation"))

    def _save_state(self) -> None:
        self.view_manager.storage.deserialize(
            {
                "fingerprint": self._fingerprint(),
                "response_id": self._native_response_id,
                "conversation": self._conversation,
            },
            self._state_path,
        )
    @property
    def file_path(self) -> str:
        """Get the file path associated with the agent."""
        return self._file_path

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
    def _json_escape(text: str) -> str:
        """Escape a string for embedding in JSON.

        Args:
            text (str): The raw string to escape.

        Returns:
            str: The JSON-escaped string.
        """
        return (text
            .replace('\\', '\\\\')
            .replace('"', '\\"')
            .replace('\n', '\\n')
            .replace('\r', '\\r')
            .replace('\t', '\\t'))

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
            carry = ""
            while True:
                n = storage.file_readinto(src, buf)
                if not n:
                    break
                chunk = carry + buf[:n].decode('utf-8')
                if chunk.endswith('\\'):
                    carry = '\\'
                    chunk = chunk[:-1]
                else:
                    carry = ""
                if not chunk:
                    continue
                storage.write(dst_path, Agent._json_escape(chunk), mode="a")
            if carry:
                storage.write(dst_path, '\\\\', mode="a")
        finally:
            storage.file_close(src)

    @staticmethod
    def _write_file_fragment(storage, file_obj, value) -> None:
        """Write one bounded request fragment or fail the request build."""
        if not storage.file_write(file_obj, value, mode="w"):
            raise OSError("could not write Agent request file")

    @staticmethod
    def _write_json_string(storage, file_obj, value: str) -> None:
        """Write one JSON string without materializing its complete encoding."""
        Agent._write_file_fragment(storage, file_obj, '"')
        offset = 0
        while offset < len(value):
            chunk = value[offset:offset + 512]
            # json.dumps handles every JSON control character. Strip only the
            # surrounding quotes from this deliberately small fragment.
            escaped = json.dumps(chunk)[1:-1]
            Agent._write_file_fragment(storage, file_obj, escaped)
            offset += len(chunk)
        Agent._write_file_fragment(storage, file_obj, '"')

    @staticmethod
    def _write_json_value(storage, file_obj, value) -> None:
        """Recursively stream a JSON-compatible value in bounded fragments."""
        if isinstance(value, str):
            Agent._write_json_string(storage, file_obj, value)
            return
        if isinstance(value, list) or isinstance(value, tuple):
            Agent._write_file_fragment(storage, file_obj, "[")
            for index, item in enumerate(value):
                if index:
                    Agent._write_file_fragment(storage, file_obj, ",")
                Agent._write_json_value(storage, file_obj, item)
            Agent._write_file_fragment(storage, file_obj, "]")
            return
        if isinstance(value, dict):
            Agent._write_file_fragment(storage, file_obj, "{")
            for index, key in enumerate(value):
                if index:
                    Agent._write_file_fragment(storage, file_obj, ",")
                Agent._write_json_string(storage, file_obj, str(key))
                Agent._write_file_fragment(storage, file_obj, ":")
                Agent._write_json_value(storage, file_obj, value[key])
            Agent._write_file_fragment(storage, file_obj, "}")
            return
        Agent._write_file_fragment(storage, file_obj, json.dumps(value))

    def _write_system_message(self, storage) -> None:
        """Write the system message to the conversation file.

        Args:
            storage (Storage): The storage interface.
        """
        storage.write(self._conv_path, '{"role":"system","content":"', mode="w")
        if storage.exists(self._mem_path):
            self._stream_file_json_escaped(storage, self._mem_path, self._conv_path)
        storage.write(self._conv_path, '"}', mode="a")

    def _build_request(self, tools: list[dict]) -> None:
        """Stream the conversation and metadata into the API request file.

        Args:
            tools (list[dict]): The tool schemas to include in the request.
        """
        storage = self.view_manager.storage

        # Preamble: model + messages open
        storage.write(
            self._file_path,
            '{"model":"' + self.llm.model + '","messages":[',
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
                    storage.write(self._file_path, buf[:n], mode="b")
            finally:
                storage.file_close(conv_file)

        # tools
        storage.write(
            self._file_path,
            '],"tools":' + json.dumps(tools) + ',"tool_choice":"auto"',
            mode="a",
        )

        # thinking 
        _payload = self.llm.thinking_payload
        _payload_str = json.dumps(_payload)
        # strip { }
        _payload_str = _payload_str[1:-1]
        if _payload_str:
            storage.write(self._file_path, "," + _payload_str, mode="a")

        # close
        storage.write(self._file_path, "}", mode="a")


    @staticmethod
    def _native_message_content(item: dict) -> str:
        """Extract text from one LM Studio native message item.

        Args:
            item (dict): Native API output item.

        Returns:
            str: Extracted message text.
        """
        content = item.get("content", "")
        if isinstance(content, str):
            return content
        if not isinstance(content, list):
            return ""

        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                text = part.get("text", part.get("content", ""))
                if isinstance(text, str) and text:
                    parts.append(text)
        return "\n".join(parts)

    @staticmethod
    def _web_profile(user_message: str):
        """Return whether the turn needs search and/or page retrieval."""
        text = user_message.lower()
        search_markers = (
            " web", "search", "latest", "news", "amazon", "price",
            "buy", "shop", "online", "find item", "find product",
            "look up", "research", "current information", "current facts",
        )
        fetch_markers = (
            "http://", "https://", "www.", "visit ", "open page",
            "read page", "read website", "fetch ", "this url", "this link",
        )
        return (
            any(marker in text for marker in search_markers),
            any(marker in text for marker in fetch_markers),
        )

    @staticmethod
    def _integration_profile_needed(integration: str, user_message: str) -> bool:
        """Return whether a non-web MCP is relevant to this user turn."""
        lower = integration.lower()
        text = " " + user_message.lower() + " "
        if "nutrition" in lower:
            markers = (
                " nutrition", " nutrient", " calorie", " protein", " meal",
                " food", " diet", " ernahrung", " ernaehrung", " kalorie",
                " mahlzeit",
            )
        elif "markitdown" in lower:
            markers = (
                " markdown", " convert", " document", " pdf", " docx",
                " xlsx", " pptx", " datei umwandeln",
            )
        elif "filesystem" in lower:
            markers = (
                " host filesystem", " lm studio file", " local computer file",
                " host file", " host directory", " host folder",
            )
        elif "germany" in lower:
            markers = (
                " germany", " german ", " deutschland", " bundestag",
                " bundesregierung",
            )
        else:
            name = lower.rsplit("/", 1)[-1]
            for separator in ("-", "_", "."):
                name = name.replace(separator, " ")
            name = name.replace("modelcontextprotocol", "")
            markers = tuple(
                " " + token + " " for token in name.split() if len(token) >= 4
            )
        return any(marker in text for marker in markers)

    def _selected_integrations(self, user_message: str):
        """Return a bounded MCP profile with known tools explicitly allowed."""
        selected = []
        needs_search, needs_fetch = self._web_profile(" " + user_message)
        message_lower = user_message.lower()
        amazon_request = "amazon" in message_lower
        explicit_fetch = "fetch" in message_lower
        explicit_playwright = "playwright" in message_lower
        configured = self.llm.mcp_integrations
        has_fetch = any("fetch" in integration.lower() for integration in configured)
        has_playwright = any(
            "playwright" in integration.lower() for integration in configured
        )
        has_page_reader = has_fetch or has_playwright
        for integration in configured:
            lower = integration.lower()
            if "visit-website" in lower:
                if has_page_reader or not needs_fetch:
                    continue
            elif "duckduckgo" in lower:
                if not needs_search or (amazon_request and has_page_reader):
                    continue
            elif "playwright" in lower:
                if not needs_search and not needs_fetch and not explicit_playwright:
                    continue
            elif "fetch" in lower:
                if (
                    (not needs_fetch and not amazon_request)
                    or (has_playwright and not explicit_fetch)
                ):
                    continue
            elif "toolguard-current-time" not in lower:
                if not self._integration_profile_needed(integration, user_message):
                    continue
            item = {"type": "plugin", "id": integration}
            if "toolguard-current-time" in lower:
                item["allowed_tools"] = ["get_current_time"]
            elif "duckduckgo" in lower:
                item["allowed_tools"] = ["Web Search"]
            elif "playwright" in lower:
                item["allowed_tools"] = [
                    "browser_navigate", "browser_snapshot", "browser_wait_for",
                ]
            elif lower.startswith("mcp/") and "fetch" in lower:
                item["allowed_tools"] = ["fetch"]
            selected.append(item)
        return selected

    @staticmethod
    def _needs_native_research(integrations) -> bool:
        """Return whether selected integrations include more than clock grounding."""
        for integration in integrations:
            value = integration.get("id", "") if isinstance(integration, dict) else str(integration)
            if "toolguard-current-time" not in value.lower():
                return True
        return False

    def _has_time_integration(self, integrations) -> bool:
        for integration in integrations:
            value = integration.get("id", "") if isinstance(integration, dict) else str(integration)
            if "toolguard-current-time" in value.lower():
                return True
        return False

    def _responses_input(self, user_message: str):
        if self._native_response_id:
            return user_message
        messages = []
        for message in self._conversation:
            messages.append(
                {
                    "role": message["role"],
                    "content": message["content"],
                }
            )
        messages.append({"role": "user", "content": user_message})
        return messages

    def _build_responses_request(self, input_value, integrations, tools) -> None:
        """Build a Responses request in fragments to keep peak heap bounded."""
        storage = self.view_manager.storage
        if storage.exists(self._file_path) and not storage.remove(self._file_path):
            raise OSError("could not replace Agent request file")
        request_file = storage.file_open(self._file_path)
        if request_file is None:
            raise OSError("could not create Agent request file")
        try:
            self._write_file_fragment(storage, request_file, '{"model":')
            self._write_json_value(storage, request_file, self.llm.model)
            self._write_file_fragment(storage, request_file, ',"input":')
            self._write_json_value(storage, request_file, input_value)
            self._write_file_fragment(storage, request_file, ',"tools":')
            self._write_json_value(storage, request_file, tools)
            self._write_file_fragment(storage, request_file, ',"integrations":')
            self._write_json_value(storage, request_file, integrations)
            self._write_file_fragment(
                storage,
                request_file,
                ',"store":true,"stream":false,"temperature":0'
                ',"max_output_tokens":' + str(MAX_MODEL_OUTPUT_TOKENS)
                + ',"max_tool_calls":' + str(MAX_TOOL_CALLS_PER_RUN),
            )
            if self._native_response_id:
                self._write_file_fragment(
                    storage, request_file, ',"previous_response_id":'
                )
                self._write_json_value(
                    storage, request_file, self._native_response_id
                )
            # Responses instructions are turn-scoped and are not inherited by
            # previous_response_id, so include the compact policy every round.
            self._write_file_fragment(storage, request_file, ',"instructions":"')
        finally:
            storage.file_close(request_file)
        if storage.exists(self._mem_path):
            self._stream_file_json_escaped(storage, self._mem_path, self._file_path)
        grounding = _current_time_grounding(self.view_manager)
        request_file = storage.file_open(self._file_path)
        if request_file is None:
            raise OSError("could not reopen Agent request file")
        try:
            if not storage.file_seek(request_file, storage.size(self._file_path)):
                raise OSError("could not append Agent request file")
            policy = grounding + _tool_loop_policy()
            offset = 0
            while offset < len(policy):
                chunk = policy[offset:offset + 512]
                self._write_file_fragment(
                    storage, request_file, json.dumps(chunk)[1:-1]
                )
                offset += len(chunk)
            self._write_file_fragment(storage, request_file, '"}')
        finally:
            storage.file_close(request_file)

    def _build_native_research_request(
        self, user_message: str, integrations,
    ) -> None:
        """Build the LM Studio native request that executes installed MCPs."""
        guarded_input = (
            "Tool execution rule: Call each available integration tool at "
            "most once. Never repeat a tool with identical arguments. For "
            "web search, use one concise plain-language query without Boolean "
            "OR chains and request no more than 3 results. When visiting a "
            "page, request at most 8 links, no images, and at most 4000 text "
            "characters. When both search and browser tools are available, "
            "search once and open only the single most relevant result. Use "
            "browser tools only to read; do not submit forms or download files. "
            "If a result is empty or unhelpful, stop immediately "
            "and report that limitation.\n\nUser request:\n" + user_message
        )
        payload = {
            "model": self.llm.model,
            "input": guarded_input,
            "system_prompt": (
                "Use the configured integrations to gather current, factual "
                "evidence for the Picoware Agent. Call only relevant tools, "
                "respect the tool-call budget, preserve direct URLs, and then "
                "return a concise evidence summary. Do not perform or claim "
                "Picoware device actions."
                + _current_time_grounding(self.view_manager)
                + _tool_loop_policy()
            ),
            "integrations": integrations,
            "temperature": 0,
            "store": False,
            "stream": True,
            "max_output_tokens": MAX_NATIVE_RESEARCH_TOKENS,
        }
        thinking = self.llm.thinking_payload
        if thinking:
            payload.update(thinking)
        self.view_manager.storage.write(
            self._file_path, json.dumps(payload), mode="w"
        )

    def _run_native_research(
        self, user_message: str, integrations,
        max_tool_calls: int = MAX_NATIVE_MCP_CALLS,
    ):
        """Execute installed LM Studio integrations and return bounded evidence."""
        self._status = "MCP research"
        # LM Studio's /api/v1/chat rejects max_tool_calls. The streaming sink
        # below enforces this stage's hard device-side call limit instead.
        self._build_native_research_request(user_message, integrations)
        storage = self.view_manager.storage
        spool_path = "picoware/settings/agent_mcp_stream.tmp"
        sink = _NativeResearchSink(
            self.http, storage, spool_path, max_calls=max_tool_calls
        )
        response = None
        try:
            if not sink.issue:
                response = self.http.post(
                    native_mcp_url(self.llm.url),
                    headers=self.llm.headers,
                    payload=None,
                    timeout=90,
                    storage=storage,
                    send_file=self._file_path,
                    stream_sink=sink,
                )
        finally:
            try:
                if response is not None:
                    response.close()
            except Exception:
                pass
            sink.close()
            storage.remove(spool_path)
            from gc import collect
            collect()
        if sink.issue:
            if sink.evidence:
                evidence = (
                    "The device stopped LM Studio's MCP loop: " + sink.issue
                    + ". Use only the completed tool evidence below and "
                    "clearly state any limitation.\n\n"
                    + "\n\n".join(sink.evidence)
                )
                self.view_manager.log(
                    "[Agent] MCP loop stopped after " + str(sink.call_count)
                    + " calls; preserving completed evidence"
                )
                return evidence, sink.call_count, ""
            return "", sink.call_count, "API error: LM Studio MCP loop stopped: " + sink.issue + "."
        if sink.error:
            return "", sink.call_count, "API error: LM Studio MCP: " + sink.error
        if sink.evidence and sink.call_count:
            evidence = "\n\n".join(sink.evidence).strip()
            if evidence:
                self.view_manager.log(
                    "[Agent] MCP research complete with "
                    + str(sink.call_count) + " tool calls"
                )
                return evidence, sink.call_count, ""
        data = sink.result
        if not isinstance(data, dict):
            if sink.evidence and sink.call_count:
                evidence = "\n\n".join(sink.evidence).strip()
                if evidence:
                    return evidence, sink.call_count, ""
            return "", sink.call_count, "API error: LM Studio MCP stream ended without chat.end."
        error = self._error_message(data, "LM Studio MCP")
        if error:
            return "", 0, error
        output = data.get("output", []) if isinstance(data, dict) else []
        if not isinstance(output, list):
            return "", 0, "API error: LM Studio MCP returned invalid output."
        issue = _native_tool_loop_issue(output)
        if issue:
            return "", 0, "API error: LM Studio MCP loop detected: " + issue + "."

        messages = []
        call_count = sink.call_count
        output_call_count = 0
        for item in output:
            if not isinstance(item, dict):
                continue
            if item.get("type") in ("tool_call", "mcp_call", "mcp_tool_call"):
                output_call_count += 1
            elif item.get("type") == "message":
                content = self._native_message_content(item).strip()
                if content:
                    messages.append(content)
        if call_count == 0:
            call_count = output_call_count
        if call_count == 0:
            return "", 0, "API error: LM Studio MCP returned no tool calls."
        evidence = "\n\n".join(messages).strip()
        if not evidence:
            return "", call_count, "API error: LM Studio MCP returned no evidence."
        if len(evidence) > MAX_NATIVE_EVIDENCE_CHARS:
            evidence = evidence[:MAX_NATIVE_EVIDENCE_CHARS] + "..."
        self.view_manager.log(
            "[Agent] MCP research complete with " + str(call_count) + " tool calls"
        )
        return evidence, call_count, ""

    def _run_native_research_pipeline(self, user_message: str, integrations):
        """Run search and browser MCPs in deterministic, bounded stages."""
        search_integrations = []
        browser_integrations = []
        other_integrations = []
        for item in integrations:
            value = item.get("id", "") if isinstance(item, dict) else str(item)
            lower = value.lower()
            if "duckduckgo" in lower:
                search_integrations.append(item)
            elif "playwright" in lower:
                browser_integrations.append({
                    "type": "plugin",
                    "id": value,
                    "allowed_tools": ["browser_navigate"],
                })
            elif "toolguard-current-time" not in lower:
                other_integrations.append(item)

        # Non-web profiles keep their existing bounded multi-tool behavior.
        if not search_integrations and not browser_integrations:
            return self._run_native_research(user_message, integrations)

        parts = []
        total_calls = 0
        search_evidence = ""
        if search_integrations:
            search_evidence, calls, error = self._run_native_research(
                user_message, search_integrations, max_tool_calls=1
            )
            total_calls += calls
            if error:
                return "", total_calls, error
            if search_evidence:
                parts.append("# Search evidence\n" + search_evidence)

        if browser_integrations:
            browser_request = user_message
            if search_evidence:
                browser_request = (
                    "Open and read the single most relevant direct URL from "
                    "the search evidence below. Call browser_navigate exactly "
                    "once. Return the page title, final URL, and concise page "
                    "evidence relevant to the original request.\n\n"
                    "Original request:\n" + user_message
                    + "\n\nSearch evidence:\n"
                    + search_evidence[:MAX_NATIVE_EVIDENCE_CHARS]
                )
            browser_evidence, calls, error = self._run_native_research(
                browser_request, browser_integrations, max_tool_calls=1
            )
            total_calls += calls
            if error:
                if parts:
                    parts.append("# Browser limitation\n" + error)
                else:
                    return "", total_calls, error
            elif browser_evidence:
                parts.append("# Browser page evidence\n" + browser_evidence)

        if other_integrations:
            other_evidence, calls, error = self._run_native_research(
                user_message, other_integrations, max_tool_calls=2
            )
            total_calls += calls
            if error:
                parts.append("# Additional integration limitation\n" + error)
            elif other_evidence:
                parts.append("# Additional integration evidence\n" + other_evidence)

        evidence = "\n\n".join(parts).strip()
        if not evidence:
            return "", total_calls, "API error: web integrations returned no evidence."
        return evidence, total_calls, ""

    def _response_data(self, response):
        """Parse a response saved to SD, falling back to an in-memory test response."""
        storage = self.view_manager.storage
        try:
            if storage.exists(self._response_path):
                return storage.serialize(self._response_path)
            if response is not None:
                return response.json()
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass
        return {}

    def _post_request_file(self, url: str, timeout: int):
        storage = self.view_manager.storage
        storage.remove(self._response_path)
        response = self.http.post(
            url,
            headers=self.llm.headers,
            payload=None,
            timeout=timeout,
            storage=storage,
            send_file=self._file_path,
            save_to_file=self._response_path,
        )
        if self._cancelled:
            return {"error": {"message": "request cancelled"}}
        if (
            storage.exists(self._response_path)
            and storage.size(self._response_path) > MAX_PROVIDER_RESPONSE_BYTES
        ):
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass
            storage.remove(self._response_path)
            return {
                "error": {
                    "message": "response exceeds the 262144-byte device limit"
                }
            }
        return self._response_data(response)

    @staticmethod
    def _error_message(data, provider: str) -> str:
        error_detail = data.get("error") if isinstance(data, dict) else None
        if not error_detail:
            return ""
        if isinstance(error_detail, dict):
            message = error_detail.get("message", str(error_detail))
        else:
            message = str(error_detail)
        if len(message) > 500:
            message = message[:500] + "..."
        return "API error: " + provider + ": " + message

    def _execute_guarded_tool(self, history, cache, name: str, arguments):
        issue = _tool_loop_issue(history, name, arguments)
        if issue:
            raise RuntimeError("Tool loop stopped before execution: " + issue + ".")
        signature = (name, _argument_signature(arguments))
        if signature in cache:
            return cache[signature]
        if self._cancelled:
            raise RuntimeError("Agent request cancelled.")
        self._status = "Tool: " + name
        self.view_manager.log("[Agent] Executing " + name)
        try:
            result = dispatch.execute_tool(self.view_manager, name, arguments)
        except Exception as exc:
            result = {"ok": False, "error": "tool_error", "message": str(exc)}
        if not isinstance(result, dict) or result.get("ok", True):
            cache[signature] = result
        self.view_manager.log("[Agent] " + name + " completed")
        return result

    def _mode_tool_limit(self, name: str) -> int:
        """Return per-turn tool limits without restricting SD-card access."""
        if name == "network_get_info":
            return 1
        if name == "network_send_request":
            return 1
        if self.mode != MODE_APP_CREATOR:
            return 0
        if name == "picoware_api_search":
            return 2
        if name == "picoware_api_read":
            return 4
        if name == "picoware_app_validate":
            return 4
        return 0

    def _execute_mode_guarded_tool(
        self, history, cache, counts, name: str, arguments
    ):
        """Execute a tool with loop guards and compact-reference budgets."""
        limit = self._mode_tool_limit(name)
        if limit and counts.get(name, 0) >= limit:
            # A model can emit the same one-shot call more than once in a
            # single response batch. Reuse its successful result for each
            # call ID; the next request no longer advertises the tool.
            signature = (name, _argument_signature(arguments))
            if signature in cache:
                return cache[signature]
            issue = _tool_loop_issue(history, name, arguments)
            if issue:
                raise RuntimeError("Tool loop stopped before execution: " + issue + ".")
            counts[name] = counts.get(name, 0) + 1
            return {
                "ok": False,
                "error": "tool_budget_exhausted",
                "message": (
                    name + " reached its per-turn limit; use the results "
                    "already returned and continue without calling it again"
                ),
            }
        counts[name] = counts.get(name, 0) + 1
        return self._execute_guarded_tool(history, cache, name, arguments)

    def _response_tools(self, counts, excluded=None):
        """Return tool schemas, hiding tools exhausted for this turn."""
        tools = []
        for tool in dispatch.get_tool_list():
            if excluded and tool.name in excluded:
                continue
            limit = self._mode_tool_limit(tool.name)
            if limit and counts.get(tool.name, 0) >= limit:
                continue
            tools.append(tool.json_responses)
        return tools

    def _chat_completion_tools(self, counts):
        """Return Chat Completions schemas with the same reference budgets."""
        tools = []
        for tool in dispatch.get_tool_list():
            limit = self._mode_tool_limit(tool.name)
            if limit and counts.get(tool.name, 0) >= limit:
                continue
            tools.append(tool.json_openai)
        return tools

    def _run_responses_mcp(self, user_message: str) -> str:
        """Run LM Studio MCP and Picoware functions through one Responses loop."""
        integrations = self._selected_integrations(user_message)
        research = ""
        mcp_call_count = 0
        used_native_research = self._needs_native_research(integrations)
        if used_native_research:
            research, mcp_call_count, error = self._run_native_research_pipeline(
                user_message, integrations
            )
            if error:
                return error
        tool_counts = {}
        model_input = user_message
        if research:
            model_input += (
                "\n\n# Current integration evidence\n"
                "The following evidence was retrieved for this turn by LM "
                "Studio integrations. Use it as tool output; do not claim "
                "unsupported facts.\n" + research
            )
        input_value = self._responses_input(model_input)
        tool_history = []
        mcp_history = []
        cache = {}

        for round_index in range(MAX_TOOL_ITERATIONS):
            if self._cancelled:
                return "An error occurred during processing: Agent request cancelled."
            self._status = "LM Studio"
            # Installed LM Studio plugins execute on /api/v1/chat. This
            # Responses call carries their evidence plus Picoware functions.
            # Do not offer the generic URL fetcher after research: otherwise
            # a model can ignore the evidence and repeatedly probe alternate
            # search-engine endpoints with slightly different arguments.
            excluded = ("network_send_request",) if used_native_research else None
            self._build_responses_request(
                input_value, [], self._response_tools(tool_counts, excluded)
            )
            data = self._post_request_file(self.llm.url, 180)
            error = self._error_message(data, "LM Studio")
            if error:
                return error

            response_id = _native_response_id(data.get("id", data.get("response_id")))
            if not response_id:
                return "API error: LM Studio Responses omitted a usable response ID."
            output = data.get("output", [])
            if not isinstance(output, list):
                return "API error: LM Studio Responses returned invalid output."

            mcp_issue = ""
            for item in output:
                if not isinstance(item, dict):
                    continue
                if item.get("type") in ("mcp_call", "mcp_tool_call", "tool_call"):
                    mcp_call_count += 1
                    name = item.get("name", item.get("tool", "unknown"))
                    arguments = item.get("arguments", {})
                    provider = item.get("server_label", item.get("provider_info", {}))
                    qualified = str(provider) + ":" + str(name)
                    mcp_issue = _tool_loop_issue(mcp_history, qualified, arguments)
                    if mcp_issue:
                        break
            if mcp_issue:
                return "API error: LM Studio MCP loop detected: " + mcp_issue + "."

            calls = []
            messages = []
            for item in output:
                if not isinstance(item, dict):
                    continue
                item_type = item.get("type")
                if item_type in ("function_call", "custom_tool_call"):
                    calls.append(item)
                elif item_type == "message":
                    content = self._native_message_content(item).strip()
                    if content:
                        messages.append(content)

            stats = data.get("usage", data.get("stats", {}))
            self._last_stats = dict(stats) if isinstance(stats, dict) else {}
            self._last_stats["mcp_calls"] = mcp_call_count
            self._last_stats["device_tool_calls"] = len(tool_history)
            self._last_stats["response_rounds"] = round_index + 1
            self._native_response_id = response_id
            if calls:
                outputs = []
                for call in calls:
                    name = call.get("name", call.get("tool", ""))
                    call_id = call.get("call_id", call.get("id", ""))
                    if not isinstance(call_id, str) or not call_id:
                        return "API error: LM Studio Responses tool call omitted call_id."
                    arguments = self._parse_tool_arguments(call.get("arguments", {}))
                    try:
                        result = self._execute_mode_guarded_tool(
                            tool_history, cache, tool_counts, name, arguments
                        )
                    except RuntimeError as exc:
                        return str(exc)
                    outputs.append(
                        {
                            "type": "function_call_output",
                            "call_id": call_id,
                            "output": json.dumps(result),
                        }
                    )
                input_value = outputs
                continue

            final = "\n\n".join(messages)
            if not final:
                return "API error: LM Studio Responses returned no final message."
            self._status = "Complete"
            self.view_manager.log("[Agent] LM Studio response complete")
            return final

        return "An error occurred during processing: Tool loop exceeded max iterations."

    @staticmethod
    def _parse_integration_catalog(value) -> list[str]:
        """Extract stored integration IDs from a catalog tool result."""
        if isinstance(value, dict):
            if isinstance(value.get("id"), str):
                value = [value]
            elif "content" in value:
                return Agent._parse_integration_catalog(value.get("content"))
            else:
                return []

        if isinstance(value, str):
            text = value.strip()
            try:
                value = json.loads(text)
            except ValueError:
                start = text.find("[")
                end = text.rfind("]")
                if start == -1 or end <= start:
                    return []
                try:
                    value = json.loads(text[start : end + 1])
                except ValueError:
                    return []

        if not isinstance(value, list):
            return []

        integrations = []
        for item in value:
            if isinstance(item, dict) and item.get("type") == "text":
                for integration_id in Agent._parse_integration_catalog(item.get("text", "")):
                    if integration_id not in integrations:
                        integrations.append(integration_id)
                continue
            if not isinstance(item, dict):
                continue
            integration_id = item.get("id")
            if not isinstance(integration_id, str):
                continue
            if not (integration_id.startswith("mcp/") or integration_id.startswith("plugin:")):
                continue
            if integration_id == INTEGRATION_CATALOG_ID or integration_id in integrations:
                continue
            integrations.append(integration_id)
            if len(integrations) >= 64:
                break
        return integrations

    def scan_integrations(self) -> tuple[list[str], str]:
        """Ask the read-only catalog MCP for available LM Studio integrations.

        Returns:
            tuple: ``(integration IDs, error message)``. The error string is
            empty when discovery succeeds.
        """
        payload = {
            "model": self.llm.model,
            "input": "Call list_integrations exactly once. Do not call any other tool.",
            "integrations": [INTEGRATION_CATALOG_ID],
            "temperature": 0,
            "store": False,
        }
        thinking = self.llm.thinking_payload
        if thinking:
            payload.update(thinking)

        storage = self.view_manager.storage
        storage.remove(self._response_path)
        response = None
        try:
            response = self.http.post(
                native_mcp_url(self.llm.url),
                payload=payload,
                headers=self.llm.headers,
                timeout=180,
                save_to_file=self._response_path,
                storage=storage,
            )
            if not storage.exists(self._response_path):
                return [], "LM Studio returned no scan data."
            if storage.size(self._response_path) > MAX_SCAN_RESPONSE_BYTES:
                return [], "Scan response exceeded the 32768-byte device limit."
            from gc import collect
            collect()
            data = storage.serialize(self._response_path)
        except (MemoryError, ValueError):
            return [], "LM Studio scan data exceeded available device memory."
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass
            storage.remove(self._response_path)
            from gc import collect
            collect()

        error_detail = data.get("error") if isinstance(data, dict) else None
        if error_detail:
            if isinstance(error_detail, dict):
                error_detail = error_detail.get("message", str(error_detail))
            error_text = str(error_detail)
            if len(error_text) > 180:
                error_text = error_text[:180] + "..."
            return [], "Scan failed: " + error_text

        output = data.get("output", []) if isinstance(data, dict) else []
        for item in output:
            if not isinstance(item, dict) or item.get("type") != "tool_call":
                continue
            integrations = self._parse_integration_catalog(
                item.get("output", item.get("result", ""))
            )
            if integrations:
                return integrations, ""

        return [], "Catalog MCP returned no integrations."

    def _run_loop(self, user_message: str) -> str:
        """Run the model/tool loop until a final reply is produced.

        Returns:
            str: The final assistant text, or an error message.
        """
        if self.llm.native_mcp:
            return self._run_responses_mcp(user_message)

        tool_history = []
        cache = {}
        tool_counts = {}

        for _ in range(MAX_TOOL_ITERATIONS):
            if self._cancelled:
                return "An error occurred during processing: Agent request cancelled."
            # Build request from conversation
            self._status = "Local model"
            self._build_request(self._chat_completion_tools(tool_counts))
            data = self._post_request_file(self.llm.url, 120)
            error = self._error_message(data, "model API")
            if error:
                return error

            if "choices" not in data:
                error_detail = data.get("error", {})
                if isinstance(error_detail, dict):
                    error_msg = error_detail.get("message", str(data))
                else:
                    error_msg = str(data)
                if len(error_msg) > 500:
                    error_msg = error_msg[:500] + "..."
                return f"API error: {error_msg}"

            message = data["choices"][0]["message"]

            if not message.get("tool_calls"):
                content = message.get("content", "")
                # Store final reply
                self._conv_append({"role": "assistant", "content": content})
                self.view_manager.log(f"[Agent] Final response: {content}")
                return content if isinstance(content, str) else str(content)

            parsed_calls = []
            for tool_call in message["tool_calls"]:
                try:
                    function = tool_call["function"]
                    name = function["name"]
                    raw_args = function.get("arguments", "{}")
                except (KeyError, TypeError):
                    return "An error occurred during processing: Invalid tool call."
                args = self._parse_tool_arguments(raw_args)
                parsed_calls.append((tool_call, name, args))

            # Store assistant message after the whole tool batch passes guards.
            assistant_message: dict = {
                "role": "assistant",
                "tool_calls": message["tool_calls"],
            }
            if message.get("content") is not None:
                assistant_message["content"] = message["content"]
            self._conv_append(assistant_message)

            for tool_call, name, args in parsed_calls:
                try:
                    result = self._execute_mode_guarded_tool(
                        tool_history, cache, tool_counts, name, args
                    )
                except RuntimeError as exc:
                    return str(exc)

                # Store tool result
                self._conv_append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", "unknown_tool_call"),
                        "content": json.dumps(result),
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
            if len(text) > MAX_MESSAGE_CHARS:
                text = text[:MAX_MESSAGE_CHARS] + "..."

            sanitized.append({"role": role, "content": text})

        if len(sanitized) > max_messages > 0:
            sanitized = sanitized[-max_messages:]

        bounded = []
        total = 0
        for message in reversed(sanitized):
            size = len(message["content"].encode("utf-8"))
            if bounded and total + size > MAX_CONVERSATION_BYTES:
                break
            bounded.append(message)
            total += size
        bounded.reverse()
        return bounded

    def _write_mode_context(self, context=None) -> None:
        """Write one compact, provider-neutral system context to SD."""
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
                storage.file_write(file_obj, value, mode="b")
                storage.file_write(file_obj, b"\n", mode="b")
        finally:
            storage.file_close(file_obj)


    def run(self,topic: str, conversation: list[dict] | None = None, context=None) -> str:
        """Run the agent for a prompt and return the response text.

        Args:
            topic (str): The user prompt.
            conversation (list[dict] or None): Prior message history. Defaults to None.
            context (str or None): Extra context prepended to the system prompt. Defaults to None.

        Returns:
            str: The assistant response text, or an error message.
        """
        user_message = topic.strip()
        if not user_message:
            return "No message provided."
        
        self._cancelled = False
        self._status = "Preparing"
        self._conversation = self._sanitize_conversation(conversation)
        self._write_mode_context(context)

        # Write initial messages to storage
        messages = [{"role": "system", "content": ""}]
        messages.extend(self._conversation)
        messages.append({"role": "user", "content": user_message})

        try:
            if not self.llm.native_mcp:
                self._conv_write_initial(messages)
            return self._run_loop(user_message)
        except Exception as exc:
            self._status = "Error"
            return f"An error occurred during processing: {exc}"

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

        topic = topic.strip()
        message = self.run(topic, conversation=conversation)
        updated_conversation = self._sanitize_conversation(
            conversation
            + [
                {"role": "user", "content": topic},
                {"role": "assistant", "content": message},
            ]
        )

        status = (
            "error"
            if isinstance(message, str) and message.startswith((
            "API error",
            "An error occurred during processing:",
            "Tool loop stopped before execution:",
        ))
            else "completed"
        )

        self._conversation = updated_conversation
        if status == "error":
            # A failed request may not exist in the provider-side chain. The
            # next turn restarts from the bounded visible conversation.
            self._native_response_id = ""
            self._status = "Error"
        else:
            self._status = "Complete"
            total_bytes = sum(
                len(item["content"].encode("utf-8"))
                for item in updated_conversation
            )
            if (
                len(updated_conversation) >= MAX_CONVERSATION_MESSAGES
                or total_bytes >= (MAX_CONVERSATION_BYTES * 3 // 4)
            ):
                self._native_response_id = ""
        self._save_state()

        return {
            "status": status,
            "message": message,
            "conversation": updated_conversation,
        }
