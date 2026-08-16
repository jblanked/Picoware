"""LM Studio compatibility adapter for Agent MCP integrations."""

import json

from picoware.system.agent.mcp import (
    MAX_BROWSER_MCP_CALLS,
    MAX_MCP_CALLS,
    MAX_MCP_EVIDENCE_CHARS,
    MAX_MCP_EVENT_BYTES,
    MAX_MCP_STREAM_BYTES,
    MAX_MCP_STREAM_EVENTS,
    MAX_MCP_ERROR_CHARS,
    MAX_MCP_TOOL_ID_CHARS,
    MAX_MCP_BROWSER_CONTEXT_CHARS,
    _append_bounded_evidence,
    _current_time_grounding,
    _utf8_prefix,
    _tool_loop_issue,
    merge_integration_records,
    parse_integration_catalog,
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


def gateway_url(configured_url: str, model_url: str) -> str:
    """Return the explicit LM Studio endpoint or its local-model fallback."""
    explicit = (configured_url or "").strip()
    if explicit:
        return explicit
    url = (model_url or "").rstrip("/")
    for suffix in ("/api/v1/chat", "/v1/chat/completions"):
        if url.endswith(suffix):
            return url[:-len(suffix)] + "/api/v1/chat"
    if url.endswith("/v1"):
        url = url[:-3]
    return url + "/api/v1/chat"


class IntegrationStreamSink:
    """Consume bounded LM Studio SSE without materializing the response."""

    __slots__ = (
        "http", "buffer", "history", "issue", "error", "call_count",
        "success_count", "evidence", "evidence_chars", "storage", "path",
        "file", "total_bytes", "spooled_bytes", "event_count", "max_calls",
        "complete",
    )

    def __init__(
        self, http, storage=None, path: str = "",
        max_calls: int = MAX_MCP_CALLS,
    ):
        self.http = http
        self.buffer = bytearray()
        self.history = []
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
        self.event_count = 0
        self.max_calls = max(1, min(int(max_calls), MAX_MCP_CALLS))
        self.complete = False
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

    @property
    def evidence_bytes(self) -> int:
        """Return retained evidence size in UTF-8 bytes."""
        return self.evidence_chars

    def _stop(self, issue: str) -> None:
        if not self.issue:
            self.issue = issue
        self.http.close()

    def _consume_buffered_event(self, event_end: int, delimiter: int) -> None:
        self.event_count += 1
        if self.event_count > MAX_MCP_STREAM_EVENTS:
            self._stop("MCP stream exceeded the bounded event limit")
            return
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
            from gc import collect
            collect()
            event = json.loads(text)
            text = ""
        except (UnicodeError, ValueError):
            self._stop("MCP gateway returned an invalid streaming event")
            return
        if not isinstance(event, dict):
            return
        event_type = event.get("type")
        if event_type == "chat.end":
            self.complete = True
            return
        if event_type == "tool_call.arguments":
            provider = event.get("provider_info", {})
            if not isinstance(provider, dict):
                provider = {}
            provider_id = provider.get(
                "plugin_id", provider.get("server_label", "")
            )
            name = (
                (str(provider_id) + ":" if provider_id else "")
                + str(event.get("tool", "unknown"))
            )
            if len(name) > MAX_MCP_TOOL_ID_CHARS:
                self._stop("MCP tool identity exceeded the device limit")
                return
            if self.call_count >= self.max_calls:
                self._stop("MCP tool-call budget exceeded")
                return
            issue = _tool_loop_issue(
                self.history, name, event.get("arguments", {})
            )
            if issue:
                self._stop(issue)
                return
            self.call_count += 1
        elif event_type == "tool_call.success":
            if self.success_count >= self.call_count:
                if self.call_count >= self.max_calls:
                    self._stop("MCP tool-call budget exceeded")
                    return
                self.call_count += 1
            self.success_count += 1
            output = event.get("output", "")
            if isinstance(output, (dict, list)):
                output = json.dumps(output)
            elif not isinstance(output, str):
                output = str(output)
            remaining = MAX_MCP_EVIDENCE_CHARS - self.evidence_chars
            if remaining > 0 and output:
                value, value_bytes = _utf8_prefix(output, remaining)
                if value:
                    self.evidence.append(value)
                    self.evidence_chars += value_bytes
            if self.call_count >= self.max_calls:
                self.complete = True
                self.http.close()
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
                if event_end < 0:
                    break
                if event_end > MAX_MCP_EVENT_BYTES:
                    self._stop("MCP streaming event exceeded the device limit")
                    return
                self._consume_buffered_event(event_end, delimiter)
                if self.issue or self.complete:
                    break
            if len(self.buffer) > MAX_MCP_EVENT_BYTES:
                self._stop("MCP streaming event exceeded the device limit")

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

    __slots__ = (
        "view_manager", "http", "llm", "gateway_url", "request_path",
        "spool_path",
    )

    def __init__(self, view_manager, http, llm, configured_url=""):
        self.view_manager = view_manager
        self.http = http
        self.llm = llm
        self.gateway_url = gateway_url(configured_url, llm.url)
        self.request_path = "picoware/settings/agent_mcp_request.json"
        self.spool_path = "picoware/settings/agent_mcp_stream.tmp"

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
    ) -> None:
        instruction = (
            "The previous attempt returned no tool call. You must call exactly "
            "one provided integration tool now. Do not answer from memory. "
            if force_retry else
            "Call at least one provided integration tool before answering. "
        )
        guard = (
            instruction + "Call any individual tool at most once. Never repeat "
            "a successful call with identical arguments. For web search, use "
            "one concise query and no more than 3 results. Open only the most "
            "relevant result. Use browser tools only to read. If a result is "
            "empty, stop and report the limitation.\n\nUser request:\n"
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
                "Gather concise factual evidence with only the configured "
                "integrations. Preserve direct URLs and do not perform device "
                "actions." + _current_time_grounding(self.view_manager)
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
            '],"temperature":0,"store":false,"stream":true,'
            '"max_output_tokens":768}',
            mode="a",
        )

    def run_stage_once(
        self, user_message: str, integrations,
        max_calls: int, force_retry: bool = False,
    ):
        """Run one bounded LM Studio integration stage."""
        storage = self.view_manager.storage
        sink = None
        response = None
        status_code = 0
        reason = ""
        try:
            self._write_request(user_message, integrations, force_retry)
            sink = IntegrationStreamSink(
                self.http, storage, self.spool_path, max_calls=max_calls
            )
            if not sink.issue:
                response = self.http.post(
                    self.gateway_url,
                    payload=None,
                    headers=self.llm.headers,
                    timeout=90,
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
            sink.complete or sink.evidence or sink.issue or sink.error
        ):
            return "", sink.call_count, "MCP gateway returned no response."
        if status_code and not 200 <= status_code <= 299:
            return "", sink.call_count, sink.http_error(status_code, reason)
        if sink.issue:
            if sink.evidence:
                return "\n\n".join(sink.evidence), sink.call_count, ""
            return "", sink.call_count, "MCP gateway stopped: " + sink.issue
        if sink.error:
            return "", sink.call_count, "MCP gateway error: " + sink.error
        evidence = "\n\n".join(sink.evidence).strip()
        if sink.call_count == 0:
            return "", 0, "MCP gateway returned no tool calls."
        if not evidence:
            return "", sink.call_count, "MCP gateway returned no evidence."
        return evidence, sink.call_count, ""

    def run_stage(
        self, user_message: str, integrations,
        max_calls: int = MAX_MCP_CALLS,
    ):
        """Run one stage with a bounded no-tool retry."""
        result = self.run_stage_once(
            user_message, integrations, max_calls, False
        )
        if result[1] == 0 and result[2] == "MCP gateway returned no tool calls.":
            self.view_manager.log("[Agent] MCP retry after no tool call")
            result = self.run_stage_once(
                user_message, integrations, max_calls, True
            )
        return result

    def research(self, user_message: str, records):
        """Run selected LM Studio integrations and return bounded evidence."""
        if not records:
            return "", ""
        search = []
        browser = []
        other = []
        for record in records:
            capabilities = record.get("capabilities", ["generic"])
            item = self.gateway_item(record)
            routed = False
            if "search" in capabilities:
                search.append(item)
                routed = True
            if "browser" in capabilities or "fetch" in capabilities:
                browser.append(item)
                routed = True
            if not routed:
                other.append(item)

        parts = []
        used = 0
        calls = 0
        search_evidence = ""
        if search:
            search_evidence, count, error = self.run_stage(
                user_message, search, max_calls=1
            )
            calls += count
            if error:
                return "", error
            if search_evidence:
                if browser or other:
                    search_evidence, _search_bytes = _utf8_prefix(
                        search_evidence, MAX_MCP_BROWSER_CONTEXT_CHARS
                    )
                used = _append_bounded_evidence(
                    parts, "# Search evidence", search_evidence, used
                )
        if browser and calls < MAX_MCP_CALLS:
            browser_request = user_message
            if search_evidence:
                browser_request = (
                    "Open the single most relevant direct URL from the search "
                    "evidence. Call one navigation or fetch tool and return the "
                    "page title, final URL, and relevant page evidence.\n\n"
                    "Original request:\n" + user_message
                    + "\n\nSearch evidence:\n"
                    + search_evidence
                )
            browser_evidence, count, error = self.run_stage(
                browser_request, browser,
                max_calls=min(MAX_BROWSER_MCP_CALLS, MAX_MCP_CALLS - calls),
            )
            calls += count
            if error:
                if parts:
                    used = _append_bounded_evidence(
                        parts, "# Browser limitation", error, used
                    )
                else:
                    return "", error
            elif browser_evidence:
                used = _append_bounded_evidence(
                    parts, "# Browser evidence", browser_evidence, used
                )
        if other and calls < MAX_MCP_CALLS:
            other_evidence, count, error = self.run_stage(
                user_message, other, max_calls=min(2, MAX_MCP_CALLS - calls)
            )
            calls += count
            if error:
                used = _append_bounded_evidence(
                    parts, "# Integration limitation", error, used
                )
            elif other_evidence:
                used = _append_bounded_evidence(
                    parts, "# Additional evidence", other_evidence, used
                )
        evidence = "\n\n".join(parts).strip()
        if not evidence:
            return "", "MCP integrations returned no evidence."
        return evidence, ""

    def scan_integrations(self, records):
        """Run configured LM Studio catalog integrations."""
        catalog = [
            record for record in records
            if "catalog" in record.get("capabilities", [])
        ]
        if not catalog:
            return list(records), ""
        evidence, _calls, error = self.run_stage(
            "Call the catalog listing tool exactly once and return complete "
            "plugin or ephemeral MCP records without commentary.",
            [self.gateway_item(record) for record in catalog],
            max_calls=1,
        )
        if error:
            return list(records), error
        discovered = parse_integration_catalog(evidence)
        if not discovered:
            return list(records), "Integration catalog returned no integrations."
        return merge_integration_records(records, discovered), ""
