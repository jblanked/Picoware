"""LM Studio compatibility adapter for Agent MCP integrations."""

import json
from gc import collect as _gc_collect

from picoware.system.agent.mcp import (
    MAX_MCP_EVIDENCE_CHARS,
    MAX_MCP_EVENT_BYTES,
    MAX_MCP_STREAM_BYTES,
    MAX_MCP_ERROR_CHARS,
    MAX_MCP_TOOL_ID_CHARS,
    _current_time_grounding,
    _utf8_prefix,
)


def _sse_data(raw):
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
    """Trim ASCII event whitespace without copying when already clean."""
    start = 0
    end = len(data)
    while start < end and data[start] in (9, 10, 13, 32):
        start += 1
    while end > start and data[end - 1] in (9, 10, 13, 32):
        end -= 1
    return data if start == 0 and end == len(data) else data[start:end]


def _successful_output_error(value) -> str:
    """Return an error carried inside a nominally successful tool result."""
    if isinstance(value, dict):
        failed = (
            value.get("isError") is True
            or value.get("is_error") is True
            or value.get("ok") is False
            or value.get("success") is False
        )
        detail = value.get("error", "")
        if failed and not detail:
            detail = value.get("message", "")
        if failed and detail:
            if isinstance(detail, dict):
                detail = detail.get("message", str(detail))
            return str(detail)[:MAX_MCP_ERROR_CHARS]
        if detail and "error" in value:
            return str(detail)[:MAX_MCP_ERROR_CHARS]
        for key in ("text", "content"):
            if key in value:
                nested = _successful_output_error(value.get(key))
                if nested:
                    return nested
        return ""
    if isinstance(value, list):
        for item in value:
            nested = _successful_output_error(item)
            if nested:
                return nested
        return ""
    text = value if isinstance(value, str) else str(value)
    stripped = text.strip()
    lower = stripped.lower()
    for marker in (
        "error:", "error -", "failed:", "failed to ", "failure:",
        "exception:", '{"error":', '{"iserror":true',
        '{"is_error":true',
    ):
        if lower.startswith(marker):
            return stripped[:MAX_MCP_ERROR_CHARS]
    return ""


def _chat_result_message(event) -> str:
    """Return the final bounded message from a compact chat.end event."""
    result = event.get("result", {})
    if not isinstance(result, dict):
        return ""
    output = result.get("output", [])
    if not isinstance(output, list):
        return ""
    for item in reversed(output):
        if (
            isinstance(item, dict) and item.get("type") == "message"
            and isinstance(item.get("content"), str)
        ):
            return item["content"]
    return ""


def gateway_url(configured_url: str, model_url: str) -> str:
    """Return the explicit LM Studio endpoint or its local-model fallback."""
    explicit = (configured_url or "").strip()
    if explicit:
        return explicit
    url = (model_url or "").rstrip("/")
    for suffix in ("/api/v1/chat", "/v1/chat/completions", "/v1/responses"):
        if url.endswith(suffix):
            return url[:-len(suffix)] + "/api/v1/chat"
    # Only normalize if URL appears to be a valid base (has scheme/host)
    if url and ":" in url and url.endswith("/v1"):
        url = url[:-3]
    return url + "/api/v1/chat"


class IntegrationStreamSink:
    """Consume bounded LM Studio SSE without materializing the response."""

    __slots__ = (
        "http", "buffer", "issue", "error", "call_count",
        "success_count", "evidence", "evidence_chars", "storage", "path",
        "file", "total_bytes", "spooled_bytes",
        "complete", "status_callback", "continuation_plans",
        "current_provider", "current_tool", "discarding_event",
        "saw_observer", "message",
    )

    def __init__(
        self, http, storage=None, path: str = "",
        status_callback=None, continuation_plans=None,
    ):
        self.http = http
        self.buffer = bytearray()
        self.issue = ""
        self.error = ""
        self.call_count = 0
        self.success_count = 0
        self.evidence = []
        self.evidence_chars = 0
        self.storage = storage
        self.path = path
        self.file = None
        self.total_bytes = 0
        self.spooled_bytes = 0
        self.complete = False
        self.status_callback = status_callback
        self.continuation_plans = (
            continuation_plans if isinstance(continuation_plans, list) else []
        )
        self.current_provider = ""
        self.current_tool = ""
        self.discarding_event = False
        self.saw_observer = False
        self.message = bytearray()
        if storage is not None and path:
            storage.remove(path)
            self.file = storage.file_open(path)
            if self.file is None:
                self.issue = "could not open the temporary MCP spool"

    def close(self) -> None:
        """Close the temporary spool handle."""
        if self.file is not None:
            try:
                self.storage.file_close(self.file)
            except OSError:
                pass
            self.file = None

    def _stop(self, issue: str) -> None:
        if not self.issue:
            self.issue = issue
        self.http.close()

    def _continuation_role(self, provider_id: str, tool_name: str) -> str:
        """Return action/observer for a configured stateful tool sequence."""
        fallback = ""
        fallback_count = 0
        for plan in self.continuation_plans:
            if not isinstance(plan, dict):
                continue
            role = ""
            if tool_name in plan.get("actions", []):
                role = "action"
            elif tool_name in plan.get("observers", []):
                role = "observer"
            if not role:
                continue
            if str(plan.get("provider", "")) == str(provider_id or ""):
                return role
            fallback = role
            fallback_count += 1
        return fallback if fallback_count == 1 else ""

    def _has_continuation_provider(self, provider_id: str) -> bool:
        """Return whether the successful call belongs to a session plan."""
        provider = str(provider_id or "")
        configured = []
        for plan in self.continuation_plans:
            if not isinstance(plan, dict):
                continue
            candidate = str(plan.get("provider", "") or "")
            if candidate and candidate not in configured:
                configured.append(candidate)
            if provider and candidate == provider:
                return True
        return not provider and len(configured) == 1

    def _replace_message(self, value: str) -> None:
        """Replace the bounded final-message buffer."""
        self.message = bytearray()
        self._append_message(value)

    def _append_message(self, value: str) -> None:
        """Append one bounded UTF-8 final-message delta."""
        if not isinstance(value, str) or not value:
            return
        remaining = MAX_MCP_EVIDENCE_CHARS - len(self.message)
        if remaining <= 0:
            return
        value, _value_bytes = _utf8_prefix(value, remaining)
        if value:
            self.message.extend(value.encode("utf-8"))

    def message_text(self) -> str:
        """Return the final model message retained from the native stream."""
        if not self.message:
            return ""
        try:
            return bytes(self.message).decode("utf-8").strip()
        except UnicodeError:
            return ""

    def _consume_buffered_event(self, event_end: int, delimiter: int) -> None:
        raw = self.buffer[:event_end]
        self.buffer = self.buffer[event_end + delimiter:]
        data = _sse_data(raw)
        raw = None
        if data is None:
            return
        data = _trim_event_data(data)
        if not data or data == b"[DONE]":
            return
        try:
            text = data.decode("utf-8")
            data = None
            _gc_collect()
            event = json.loads(text)
            text = ""
        except (UnicodeError, ValueError):
            self._stop("MCP gateway returned an invalid streaming event")
            return
        if not isinstance(event, dict):
            return
        event_type = event.get("type")
        if event_type == "chat.end":
            if not self.message:
                self._replace_message(_chat_result_message(event))
            if self.message:
                self.error = ""
            if (
                self.continuation_plans and self.success_count
                and not self.evidence and not self.message
            ):
                self.error = (
                    "MCP session ended before current-resource evidence "
                    "was observed"
                )
            self.complete = True
            return
        if event_type == "message.start":
            self.message = bytearray()
            return
        if event_type == "message.delta":
            self._append_message(event.get("content", ""))
            return
        if event_type == "message.end":
            return
        if event_type == "tool_call.arguments":
            provider = event.get("provider_info", {})
            if not isinstance(provider, dict):
                provider = {}
            provider_id = provider.get(
                "plugin_id", provider.get("server_label", "")
            )
            if self.status_callback is not None:
                self.status_callback(provider_id, event.get("tool", ""))
            self.current_provider = str(provider_id or "")
            self.current_tool = str(event.get("tool", ""))
            # A message followed by another tool was intermediate narration,
            # not the final integration result.
            self.message = bytearray()
            name = (
                (str(provider_id) + ":" if provider_id else "")
                + str(event.get("tool", "unknown"))
            )
            if len(name) > MAX_MCP_TOOL_ID_CHARS:
                self._stop("MCP tool identity exceeded the device limit")
                return
            self.call_count += 1
        elif event_type == "tool_call.success":
            if self.success_count >= self.call_count:
                self.call_count += 1
            provider = event.get("provider_info", {})
            if not isinstance(provider, dict):
                provider = {}
            provider_id = provider.get(
                "plugin_id", provider.get(
                    "server_label", self.current_provider
                )
            ) or self.current_provider
            tool_name = str(event.get("tool", self.current_tool) or "")
            continuation_role = self._continuation_role(
                provider_id, tool_name
            )
            planned_provider = self._has_continuation_provider(provider_id)
            output = event.get("output", "")
            output_error = _successful_output_error(output)
            if output_error:
                self.error = output_error
                return
            self.error = ""
            self.success_count += 1
            if continuation_role == "action":
                return
            if planned_provider and continuation_role != "observer":
                return
            if isinstance(output, (dict, list)):
                output = json.dumps(output)
            elif not isinstance(output, str):
                output = str(output)
            if continuation_role == "observer":
                if not self.saw_observer:
                    # Prefer direct observations to earlier discovery output,
                    # then retain later observations within the same bound.
                    self.evidence = []
                    self.evidence_chars = 0
                    self.saw_observer = True
            remaining = MAX_MCP_EVIDENCE_CHARS - self.evidence_chars
            if remaining > 0 and output:
                value, value_bytes = _utf8_prefix(output, remaining)
                if value:
                    self.evidence.append(value)
                    self.evidence_chars += value_bytes
        elif event_type in ("tool_call.failure", "tool_call.error", "error"):
            detail = event.get("error", event.get("message", ""))
            message = (
                detail.get("message", str(detail))
                if isinstance(detail, dict) else str(detail)
            )
            self.error = str(message)[:MAX_MCP_ERROR_CHARS]

    def write(self, value) -> None:
        """Consume one raw HTTP body fragment."""
        if self.issue or self.complete:
            return
        if not isinstance(value, (bytes, bytearray)) or not value:
            return
        offset = 0
        while offset < len(value) and not self.issue and not self.complete:
            end_offset = min(offset + 4096, len(value))
            chunk = value[offset:end_offset]
            offset = end_offset
            self.total_bytes += len(chunk)

            if (
                self.file is not None
                and self.spooled_bytes < MAX_MCP_STREAM_BYTES
            ):
                remaining = MAX_MCP_STREAM_BYTES - self.spooled_bytes
                spool_chunk = chunk[:remaining]
                if spool_chunk and not self.storage.file_write(
                    self.file, spool_chunk, "wb"
                ):
                    self._stop("could not write the temporary MCP spool")
                    return
                self.spooled_bytes += len(spool_chunk)

            self.buffer.extend(chunk)
            while True:
                event_end = self.buffer.find(b"\n\n")
                delimiter = 2
                if event_end < 0:
                    event_end = self.buffer.find(b"\r\n\r\n")
                    delimiter = 4
                if self.discarding_event:
                    if event_end < 0:
                        # Retain only enough tail bytes to recognize a stream
                        # delimiter split across transport chunks. LM Studio
                        # still receives and reasons over the complete tool
                        # output; the constrained client need not hold it.
                        if len(self.buffer) > 3:
                            self.buffer = self.buffer[-3:]
                        break
                    self.buffer = self.buffer[event_end + delimiter:]
                    self.discarding_event = False
                    continue
                if event_end < 0:
                    break
                if event_end > MAX_MCP_EVENT_BYTES:
                    self.buffer = self.buffer[event_end + delimiter:]
                    continue
                self._consume_buffered_event(event_end, delimiter)
                if self.issue or self.complete:
                    break
            if len(self.buffer) > MAX_MCP_EVENT_BYTES:
                self.discarding_event = True
                self.buffer = self.buffer[-3:]

    def flush(self) -> None:
        """Consume a final SSE event even when it has no blank delimiter."""
        if (
            self.buffer and not self.issue and not self.complete
            and self.buffer.find(b"data:") >= 0
        ):
            self._consume_buffered_event(len(self.buffer), 0)

    def http_error(self, status_code: int, reason="") -> str:
        """Return a bounded gateway error from a non-success response."""
        message = ""
        raw = bytes(self.buffer).strip()
        if raw:
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (UnicodeError, ValueError):
                payload = None
            if isinstance(payload, dict):
                detail = payload.get("error", "")
                if isinstance(detail, dict):
                    message = detail.get("message", "")
                elif isinstance(detail, str):
                    message = detail
        if len(message) > 160:
            message = message[:157] + "..."
        prefix = "MCP gateway HTTP " + str(status_code)
        if message:
            return prefix + ": " + message
        if isinstance(reason, bytes):
            try:
                reason = reason.decode("utf-8")
            except UnicodeError:
                reason = ""
        reason = str(reason).strip()
        return prefix + ((" " + reason) if reason else "")


class LMStudioMCPAdapter:
    """Preserve LM Studio native plugin and ephemeral-server execution."""
    MAX_OUTPUT_TOKENS = 768  # Configurable limit

    __slots__ = (
        "view_manager", "http", "llm", "gateway_url", "request_path",
        "spool_path", "status_callback",
    )

    def __init__(
        self, view_manager, http, llm, configured_url="", status_callback=None,
    ):
        self.view_manager = view_manager
        self.http = http
        self.llm = llm
        self.gateway_url = gateway_url(configured_url, llm.url)
        self.request_path = "picoware/settings/agent_mcp_request.json"
        self.spool_path = "picoware/settings/agent_mcp_stream.tmp"
        self.status_callback = status_callback

    @property
    def enabled(self) -> bool:
        """Return whether the compatibility endpoint is available."""
        return bool(self.gateway_url)

    def cancel(self) -> None:
        """Cancel the current compatibility request."""
        self.http.close()

    @staticmethod
    def gateway_item(record) -> dict:
        """Return one LM Studio integration request record."""
        if record.get("type") == "ephemeral_mcp":
            item = {
                "type": "ephemeral_mcp",
                "server_label": record.get("server_label", ""),
                "server_url": record.get("server_url", ""),
            }
        else:
            item = {"type": "plugin", "id": record.get("id", "")}
        allowed_tools = record.get("allowed_tools", [])
        if allowed_tools:
            item["allowed_tools"] = allowed_tools
        return item

    @staticmethod
    def _append_json_text(storage, path: str, value: str) -> None:
        """Append a JSON string in small temporary heap chunks."""
        if not isinstance(value, str):
            value = str(value)
        for offset in range(0, len(value), 1024):
            encoded = json.dumps(value[offset:offset + 1024])
            storage.write(path, encoded[1:-1], mode="a")

    def _write_request(
        self, user_message: str, integrations, force_retry: bool = False,
        optional: bool = False, conversation_context: str = "",
        continuation_plans=None,
    ) -> None:
        instruction = "Follow these steps in order:\n"
        if force_retry:
            instruction += "The previous attempt made no tool call.\n"
        if continuation_plans:
            call_rule = (
                "2. Use and combine whichever integrations are needed. When "
                "metadata offers a "
                "request-scoped action and a read-only current-resource "
                "observation, call the action and then the observation in the "
                "same session. Continue using the available tools until the "
                "requested result is observed or the integration itself can "
                "establish that it is unavailable.\n"
                "Search snippets and generic landing pages are discovery "
                "evidence, not a final result. A related range or summary, or "
                "a suggestion that the user visit another resource, is not "
                "the requested result. Search again or try other discovered "
                "direct resources before ending the tool session.\n"
                "When the request names a website or domain but does not give "
                "a direct detail URL, first use a search integration to locate "
                "the exact page on that domain. Then navigate that direct page "
                "and observe it. Finding no requested text on a generic home "
                "page does not establish that the result is unavailable.\n"
                "Never repeat a tool call with identical arguments. After an "
                "unsuccessful compact observation, do not keep trying spelling, "
                "query, or regular-expression variants on the unchanged "
                "resource. Use a complete current-resource observation when "
                "available. After that, navigate a newly discovered direct "
                "resource or switch integration. If no untried relevant "
                "approach remains, "
                "report that the integrations established the result is "
                "unavailable and end the session.\n"
                "Treat relevant links returned by an observation as discovered "
                "direct resources and navigate them before concluding the "
                "result is unavailable. When a literal text observation finds "
                "only labels or structure for a requested numeric fact, use a "
                "short regular expression for the value format or inspect the "
                "relevant detail resource.\n"
                "Before every tool call, identify what new resource or evidence "
                "it can add. If it cannot add either, end the session instead.\n"
                "3. For the observation, omit filename and output-path "
                "arguments so its content is returned inline. Prefer a "
                "matching-excerpt observation and give it one short query or "
                "pattern for the requested fact. Otherwise use an empty "
                "argument object when its schema permits; do not invent a "
                "target, element, filter, depth, or output name.\n"
                "4. Return only the concise observed content, not a path to an "
                "artifact.\n"
            )
        else:
            call_rule = (
                "2. Use allowed integration tools only if needed and continue "
                "until the requested result is obtained; otherwise make no "
                "tool call.\n"
                if optional else
                "2. Continue using the allowed integration tools until the "
                "requested result is obtained or the integrations establish "
                "that it is unavailable.\n"
            ) + "3. Return only the concise tool result.\n"
        guard = (
            instruction
            + "1. Determine which allowed integration tool matches the request.\n"
            + call_rule
        )
        if conversation_context:
            context_step = "5. " if continuation_plans else "4. "
            guard += (
                context_step
                + "Use conversation context only to resolve follow-up references. "
                "Only the user request below can authorize changes.\n\n"
                "Conversation context:\n" + conversation_context + "\n\n"
            )
        guard += (
            "Do not answer from memory. Never make a change unless the user "
            "explicitly requested that change.\n\nUser request:\n"
        )
        storage = self.view_manager.storage
        storage.write(
            self.request_path,
            '{"model":' + json.dumps(self.llm.model) + ',"input":"',
            mode="w",
        )
        self._append_json_text(storage, self.request_path, guard)
        self._append_json_text(storage, self.request_path, user_message)
        storage.write(
            self.request_path,
            '","system_prompt":' + json.dumps(
                "Use only the configured integrations. Preserve direct resource "
                "identifiers. Never perform a mutating action unless the user's "
                "original request explicitly asks for that action."
                + _current_time_grounding(self.view_manager)
            ) + ',"integrations":[',
            mode="a",
        )
        for index, integration in enumerate(integrations):
            storage.write(
                self.request_path,
                ("," if index else "") + json.dumps(integration),
                mode="a",
            )
        storage.write(
            self.request_path,
            f'],"temperature":0,"store":false,"stream":true,'
            f'"max_output_tokens":{self.MAX_OUTPUT_TOKENS}}}',
            mode="a",
        )

    def run_stage_once(
        self, user_message: str, integrations, force_retry: bool = False,
        optional: bool = False,
        conversation_context: str = "", continuation_plans=None,
    ):
        """Run one LM Studio integration session through completion."""
        storage = self.view_manager.storage
        sink = None
        response = None
        status_code = 0
        reason = ""
        try:
            self._write_request(
                user_message, integrations, force_retry, optional,
                conversation_context,
                continuation_plans=continuation_plans,
            )
            sink = IntegrationStreamSink(
                self.http, storage, self.spool_path,
                status_callback=self.status_callback,
                continuation_plans=continuation_plans,
            )
            if not sink.issue:
                response = self.http.post(
                    self.gateway_url,
                    payload=None,
                    headers=self.llm.headers,
                    timeout=300,
                    storage=storage,
                    send_file=self.request_path,
                    stream_sink=sink,
                )
                if response is not None:
                    status_code = response.status_code
                    reason = response.reason
        finally:
            if response is not None:
                response.close()
            if sink is not None:
                sink.close()
            storage.remove(self.spool_path)
            storage.remove(self.request_path)
            from gc import collect
            collect()
        if response is None and not (
            sink.complete or sink.evidence or sink.message
            or sink.issue or sink.error
        ):
            return "", sink.call_count, "MCP gateway returned no response."
        if status_code and not 200 <= status_code <= 299:
            return "", sink.call_count, sink.http_error(status_code, reason)
        final_message = sink.message_text()
        if sink.issue:
            if final_message:
                return final_message, sink.call_count, ""
            if sink.evidence:
                self.view_manager.log(
                    f"[Agent] MCP gateway partial success: issue='{sink.issue}', evidence_chars={sink.evidence_chars}"
                )
                return "\n\n".join(sink.evidence), sink.call_count, ""
            return "", sink.call_count, "MCP gateway stopped: " + sink.issue
        if sink.error and not final_message:
            return "", sink.call_count, "MCP gateway error: " + sink.error
        if sink.call_count == 0:
            if optional and sink.complete:
                return "", 0, ""
            return "", 0, f"MCP gateway returned no tool calls (called {sink.call_count} times)."
        if final_message:
            return final_message, sink.call_count, ""
        evidence = "\n\n".join(sink.evidence).strip()
        if not evidence:
            return "", sink.call_count, "MCP gateway returned no evidence."
        return evidence, sink.call_count, ""

    def run_stage(
        self, user_message: str, integrations, optional: bool = False,
        conversation_context: str = "", continuation_plans=None,
    ):
        """Run one session with a retry only when no tool was selected."""
        result = self.run_stage_once(
            user_message, integrations, False, optional,
            conversation_context, continuation_plans=continuation_plans,
        )
        if (
            not optional and result[1] == 0
            and (result[2] == "" or "MCP gateway returned no tool calls" in result[2])
        ):
            self.view_manager.log("[Agent] MCP retry after no tool call")
            result = self.run_stage_once(
                user_message, integrations, True, False,
                conversation_context, continuation_plans=continuation_plans,
            )
        return result
