"""Bounded direct MCP client for remote Streamable HTTP servers."""

import json
from micropython import const

from picoware.system.agent.mcp import (
    MAX_MCP_EVIDENCE_CHARS,
    MAX_MCP_EVENT_BYTES,
    _append_bounded_evidence,
    _current_time_grounding,
    _hint_capabilities,
    _utf8_size,
    integration_key,
    tool_hints_from_definitions,
)
from picoware.system.agent.authorization import (
    tool_effect,
)
from gc import collect


MCP_PROTOCOL_MODERN = "2026-07-28"
MCP_PROTOCOL_LEGACY = "2025-11-25"
MCP_PROTOCOL_LEGACY_FALLBACK = "2025-06-18"
MCP_PROTOCOL_2025_03 = "2025-03-26"
MCP_PROTOCOL_LEGACY_VERSIONS = (
    MCP_PROTOCOL_LEGACY, MCP_PROTOCOL_LEGACY_FALLBACK,
    MCP_PROTOCOL_2025_03,
)
MAX_MCP_JSON_BYTES = const(8192)
MAX_MCP_TOOLS = const(24)
MAX_MCP_TOOL_SCHEMA_BYTES = const(2048)
MAX_MCP_TOOL_CATALOG_BYTES = const(8192)
MAX_MCP_PLANNER_TOOLS = const(12)
MAX_MCP_PLANNER_SCHEMA_BYTES = const(12288)
MAX_MCP_LIST_PAGES = const(4)
MAX_MCP_PLANNER_TOKENS = const(256)
MAX_MCP_DIRECT_TOOL_NAME_CHARS = const(128)


def _event_data(raw):
    """Extract SSE data fields while leaving plain JSON untouched."""
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


def _trim_data(data):
    start = 0
    end = len(data)
    while start < end and data[start] in (9, 10, 13, 32):
        start += 1
    while end > start and data[end - 1] in (9, 10, 13, 32):
        end -= 1
    return data if start == 0 and end == len(data) else data[start:end]


class BoundedJSONSink:
    """Collect one bounded JSON or SSE JSON-RPC response."""

    __slots__ = ("http", "buffer", "payload", "error", "total", "limit")

    def __init__(self, http, limit: int = MAX_MCP_JSON_BYTES):
        self.http = http
        self.buffer = bytearray()
        self.payload = None
        self.error = ""
        self.total = 0
        self.limit = max(1024, min(int(limit), MAX_MCP_JSON_BYTES))

    def _stop(self, message: str) -> None:
        if not self.error:
            self.error = message
        self.http.close()

    def _consume_buffered(self, event_end: int, delimiter: int) -> None:
        raw = self.buffer[:event_end]
        self.buffer = self.buffer[event_end + delimiter:]
        if not raw:
            return
        data = _event_data(raw)
        raw = None
        if data is None:
            return
        data = _trim_data(data)
        if not data or data == b"[DONE]":
            return
        try:
            text = data.decode("utf-8")
            # The decoded JSON is the required semantic working set. Release
            # the raw byte buffer before the parser creates its object graph.
            raw = None
            data = None
            collect()
            value = json.loads(text)
            text = ""
        except (UnicodeError, ValueError):
            self._stop("MCP server returned invalid JSON")
            return
        if isinstance(value, dict) and (
            "id" in value or "result" in value or "error" in value
            or "choices" in value
        ):
            self.payload = value

    def write(self, value) -> None:
        """Consume one raw response fragment."""
        if self.error or not isinstance(value, (bytes, bytearray)) or not value:
            return
        self.total += len(value)
        if self.total > self.limit:
            self._stop("MCP response exceeded the device limit")
            return
        self.buffer.extend(value)
        while True:
            end = self.buffer.find(b"\n\n")
            delimiter = 2
            if end < 0:
                end = self.buffer.find(b"\r\n\r\n")
                delimiter = 4
            if end < 0:
                break
            if end > MAX_MCP_EVENT_BYTES:
                self._stop("MCP streaming event exceeded the device limit")
                return
            self._consume_buffered(end, delimiter)

    def flush(self) -> None:
        """Consume a final JSON body or unterminated SSE event."""
        if self.buffer and not self.error:
            self._consume_buffered(len(self.buffer), 0)


def _header_value(headers, name: str) -> str:
    """Return a response header without relying on key casing."""
    if not isinstance(headers, dict):
        return ""
    lower = name.lower()
    for key, value in headers.items():
        if isinstance(key, str) and key.lower() == lower:
            return str(value)
    return ""


def _rpc_error(payload) -> str:
    """Return a bounded JSON-RPC error message."""
    if not isinstance(payload, dict):
        return ""
    detail = payload.get("error")
    if not isinstance(detail, dict):
        return ""
    message = detail.get("message", "MCP request failed")
    message = str(message)
    if len(message) > 160:
        message = message[:157] + "..."
    return message


def _bounded_tool(value):
    """Return a compact tool definition suitable for Pico-class devices."""
    if not isinstance(value, dict):
        return None
    name = value.get("name", "")
    if not isinstance(name, str) or not name.strip():
        return None
    name = name.strip()
    if len(name) > MAX_MCP_DIRECT_TOOL_NAME_CHARS:
        return None
    description = value.get("description", value.get("title", ""))
    description = str(description)[:512]
    schema = value.get("inputSchema", {"type": "object", "properties": {}})
    if not isinstance(schema, dict):
        schema = {"type": "object", "properties": {}}
    try:
        schema_size = _utf8_size(
            json.dumps(schema), MAX_MCP_TOOL_SCHEMA_BYTES
        )
    except (TypeError, ValueError):
        schema_size = MAX_MCP_TOOL_SCHEMA_BYTES + 1
    if schema_size > MAX_MCP_TOOL_SCHEMA_BYTES:
        schema = {"type": "object", "properties": {}}
    tool = {
        "name": name,
        "description": description,
        "inputSchema": schema,
    }
    annotations = value.get("annotations")
    if isinstance(annotations, dict):
        effect = {}
        for key in ("readOnlyHint", "destructiveHint"):
            if isinstance(annotations.get(key), bool):
                effect[key] = annotations[key]
        if effect:
            tool["annotations"] = effect
    return tool


class StandardMCPAdapter:
    """Connect directly to modern or legacy remote MCP HTTP servers."""

    __slots__ = (
        "view_manager", "http", "llm", "request_id", "planner_path",
    )

    def __init__(self, view_manager, http, llm):
        self.view_manager = view_manager
        self.http = http
        self.llm = llm
        self.request_id = 0
        self.planner_path = "picoware/settings/agent_mcp_planner.json"

    def cancel(self) -> None:
        """Cancel the active direct-server request."""
        self.http.close()

    def _next_id(self) -> int:
        self.request_id += 1
        return self.request_id

    @staticmethod
    def _headers(record, method="", name="", protocol="") -> dict:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        custom = record.get("headers", {})
        if isinstance(custom, dict):
            headers.update(custom)
        if protocol:
            headers["MCP-Protocol-Version"] = protocol
        if protocol == MCP_PROTOCOL_MODERN:
            headers["Mcp-Method"] = method
            if name:
                headers["Mcp-Name"] = name
        return headers

    def _post_json(
        self, url, payload, headers, timeout=60, send_file: str = "",
    ):
        sink = BoundedJSONSink(self.http)
        response = None
        status = 0
        reason = ""
        response_headers = {}
        try:
            response = self.http.post(
                url,
                payload=payload,
                headers=headers,
                timeout=timeout,
                storage=(self.view_manager.storage if (send_file and self.view_manager.storage) else None),
                send_file=send_file or None,
                stream_sink=sink,
            )
            sink.flush()
            if response is not None:
                status = response.status_code
                reason = response.reason
                response_headers = response.headers
        finally:
            if response is not None:
                response.close()
        if sink.error:
            return None, status, response_headers, sink.error
        if response is None and sink.payload is None:
            return None, 0, {}, "MCP server returned no response"
        if status and not 200 <= status <= 299:
            message = _rpc_error(sink.payload)
            if not message:
                message = "HTTP " + str(status)
                if reason:
                    message += " " + str(reason)
            return sink.payload, status, response_headers, message
        error = _rpc_error(sink.payload)
        return sink.payload, status, response_headers, error

    @staticmethod
    def _modern_params(params) -> dict:
        result = dict(params) if isinstance(params, dict) else {}
        meta = result.get("_meta", {})
        if not isinstance(meta, dict):
            meta = {}
        meta["io.modelcontextprotocol/clientInfo"] = {
            "name": "Picoware Agent",
            "version": "2",
        }
        meta["io.modelcontextprotocol/protocolVersion"] = MCP_PROTOCOL_MODERN
        result["_meta"] = meta
        return result

    def _rpc(
        self, record, method: str, params=None,
        protocol: str = MCP_PROTOCOL_MODERN, session="",
    ):
        tool_name = ""
        if method == "tools/call" and isinstance(params, dict):
            tool_name = str(params.get("name", ""))
        body_params = params or {}
        if protocol == MCP_PROTOCOL_MODERN:
            body_params = self._modern_params(body_params)
        body = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": body_params,
        }
        headers = self._headers(record, method, tool_name, protocol)
        if session:
            headers["Mcp-Session-Id"] = session
        return self._post_json(record.get("server_url", ""), body, headers)

    def _notify_initialized(
        self, record, session="", protocol=MCP_PROTOCOL_LEGACY,
    ) -> str:
        body = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        headers = self._headers(
            record, "notifications/initialized", "", protocol
        )
        if session:
            headers["Mcp-Session-Id"] = session
        _payload, status, _headers, error = self._post_json(
            record.get("server_url", ""), body, headers
        )
        if error and status != 202:
            return error
        return ""

    def _legacy_context(self, record, requested_protocol=MCP_PROTOCOL_LEGACY):
        params = {
            "protocolVersion": requested_protocol,
            "capabilities": {},
            "clientInfo": {"name": "Picoware Agent", "version": "2"},
        }
        payload, _status, headers, error = self._rpc(
            record, "initialize", params, requested_protocol
        )
        if error:
            return None, error
        if not isinstance(payload, dict) or not isinstance(
            payload.get("result"), dict
        ):
            return None, "MCP initialize returned no result"
        result = payload.get("result", {})
        protocol = result.get("protocolVersion", requested_protocol)
        if protocol not in MCP_PROTOCOL_LEGACY_VERSIONS:
            return None, "MCP server negotiated an unsupported protocol"
        session = _header_value(headers, "Mcp-Session-Id")
        error = self._notify_initialized(record, session, protocol)
        if error:
            return None, error
        return {"protocol": protocol, "session": session}, ""

    def _list_pages(self, record, context, tool_limit=MAX_MCP_TOOLS):
        tools = []
        tool_bytes = 0
        maximum = max(1, min(int(tool_limit), MAX_MCP_TOOLS))
        cursor = ""
        for _ in range(MAX_MCP_LIST_PAGES):
            params = {"cursor": cursor} if cursor else {}
            payload, _status, _headers, error = self._rpc(
                record,
                "tools/list",
                params,
                context["protocol"],
                context.get("session", ""),
            )
            if error:
                return [], error
            result = payload.get("result", {}) if isinstance(payload, dict) else {}
            values = result.get("tools", []) if isinstance(result, dict) else []
            if not isinstance(values, list):
                return [], "MCP tools/list returned an invalid tool list"
            for value in values:
                tool = _bounded_tool(value)
                if tool is not None:
                    try:
                        size = _utf8_size(
                            json.dumps(tool), MAX_MCP_TOOL_CATALOG_BYTES
                        )
                    except (TypeError, ValueError):
                        size = MAX_MCP_TOOL_CATALOG_BYTES + 1
                    if tool_bytes + size <= MAX_MCP_TOOL_CATALOG_BYTES:
                        tools.append(tool)
                        tool_bytes += size
                if len(tools) >= maximum:
                    return tools, ""
            cursor = result.get("nextCursor", "")
            if not isinstance(cursor, str) or not cursor:
                break
        return tools, ""

    def list_tools(self, record, tool_limit=MAX_MCP_TOOLS):
        """List bounded tools and return the negotiated protocol context."""
        preference = record.get("protocol", "auto")
        if preference in ("auto", MCP_PROTOCOL_MODERN):
            # Discovery is optional; tools/list is the decisive modern probe.
            self._rpc(record, "server/discover", {}, MCP_PROTOCOL_MODERN)
            context = {"protocol": MCP_PROTOCOL_MODERN, "session": ""}
            tools, error = self._list_pages(record, context, tool_limit)
            if not error:
                return tools, context, ""
            if preference == MCP_PROTOCOL_MODERN:
                return [], None, error
        versions = MCP_PROTOCOL_LEGACY_VERSIONS
        if preference in MCP_PROTOCOL_LEGACY_VERSIONS:
            versions = (preference,)
        last_error = "MCP protocol negotiation failed"
        for protocol in versions:
            context, error = self._legacy_context(record, protocol)
            if error:
                last_error = error
                continue
            tools, error = self._list_pages(record, context, tool_limit)
            if not error:
                return tools, context, ""
            last_error = error
        return [], None, last_error

    @staticmethod
    def _planner_tools(server_tools):
        schemas = []
        mapping = {}
        schema_bytes = 0
        for server_index, entry in enumerate(server_tools):
            record, tools, context = entry
            for tool_index, tool in enumerate(tools):
                alias = "mcp_%d_%d" % (server_index, tool_index)
                schema = {
                    "type": "function",
                    "function": {
                        "name": alias,
                        "description": (
                            "MCP server " + record.get("server_label", "")
                            + ": " + tool.get("description", "")
                        )[:640],
                        "parameters": tool.get("inputSchema", {}),
                    },
                }
                try:
                    size = _utf8_size(
                        json.dumps(schema),
                        MAX_MCP_PLANNER_SCHEMA_BYTES,
                    )
                except (TypeError, ValueError):
                    size = MAX_MCP_PLANNER_SCHEMA_BYTES + 1
                if size > MAX_MCP_PLANNER_SCHEMA_BYTES:
                    continue
                if schema_bytes + size > MAX_MCP_PLANNER_SCHEMA_BYTES:
                    return schemas, mapping
                schemas.append(schema)
                schema_bytes += size
                mapping[alias] = (record, tool, context)
                if len(schemas) >= MAX_MCP_PLANNER_TOOLS:
                    return schemas, mapping
        return schemas, mapping

    @staticmethod
    def _append_json_text(storage, path: str, value: str) -> None:
        """Append one JSON string in small temporary heap chunks."""
        if not isinstance(value, str):
            value = str(value)
        for offset in range(0, len(value), 1024):
            encoded = json.dumps(value[offset:offset + 1024])
            storage.write(path, encoded[1:-1], mode="a")

    def _write_planner_request(self, user_message: str, schemas, instruction) -> None:
        """Write the potentially large planner payload incrementally to SD."""
        storage = self.view_manager.storage
        path = self.planner_path
        storage.write(
            path,
            '{"model":' + json.dumps(self.llm.model)
            + ',"messages":[{"role":"system","content":"',
            mode="w",
        )
        self._append_json_text(
            storage, path,
            instruction + " Use concise valid arguments for the selected tool."
            + _current_time_grounding(self.view_manager),
        )
        storage.write(path, '"},{"role":"user","content":"', mode="a")
        self._append_json_text(storage, path, user_message)
        storage.write(path, '"}],"tools":[', mode="a")
        for index, schema in enumerate(schemas):
            storage.write(
                path,
                ("," if index else "") + json.dumps(schema),
                mode="a",
            )
        storage.write(
            path,
            '],"tool_choice":"required","temperature":0,"stream":false,'
            '"max_tokens":' + str(MAX_MCP_PLANNER_TOKENS) + '}',
            mode="a",
        )

    def _plan_call(self, user_message: str, schemas, force_retry=False):
        instruction = (
            "The previous attempt returned no tool call. Call exactly one "
            "provided MCP tool now. Do not answer in text."
            if force_retry else
            "Select and call exactly one provided MCP tool. Do not answer in text."
        )
        storage = self.view_manager.storage
        try:
            self._write_planner_request(user_message, schemas, instruction)
            result, _status, _headers, error = self._post_json(
                self.llm.url, None, self.llm.headers, timeout=90,
                send_file=self.planner_path,
            )
        finally:
            try:
                storage.remove(self.planner_path)
                collect()
            except Exception:
                pass  # Ignore removal/GC failures; file may already be gone
        if error:
            return "", {}, error
        choices = result.get("choices", []) if isinstance(result, dict) else []
        if not choices or not isinstance(choices[0], dict):
            return "", {}, "Direct MCP planner returned no tool call"
        message = choices[0].get("message", {})
        calls = message.get("tool_calls", []) if isinstance(message, dict) else []
        if not calls or not isinstance(calls[0], dict):
            return "", {}, "Direct MCP planner returned no tool call"
        function = calls[0].get("function", {})
        if not isinstance(function, dict):
            return "", {}, "Direct MCP planner returned an invalid tool call"
        name = function.get("name", "")
        arguments = function.get("arguments", {})
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except ValueError:
                return "", {}, "Direct MCP planner returned invalid arguments"
        if not isinstance(arguments, dict):
            return "", {}, "Direct MCP planner returned invalid arguments"
        return name, arguments, ""

    @staticmethod
    def _tool_evidence(payload):
        if not isinstance(payload, dict):
            return "", "MCP tools/call returned no response"
        result = payload.get("result", {})
        if not isinstance(result, dict):
            return "", "MCP tools/call returned no result"
        parts = []
        used = 0
        evidence_limit = MAX_MCP_EVIDENCE_CHARS - len(
            "# Direct MCP evidence\n"
        )
        content = result.get("content", [])
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text", "")
                    if isinstance(text, str) and text:
                        used = _append_bounded_evidence(
                            parts, "", text, used, evidence_limit
                        )
        structured = result.get("structuredContent")
        if structured is not None:
            try:
                used = _append_bounded_evidence(
                    parts, "", json.dumps(structured), used, evidence_limit
                )
            except (TypeError, ValueError):
                pass
        evidence = "\n\n".join(parts).strip()
        if result.get("isError"):
            return "", evidence or "MCP tool reported an error"
        if not evidence:
            return "", "MCP tool returned no text evidence"
        return evidence, ""

    def research_stage(
        self, user_message: str, records, excluded_tools=(),
        allow_mutation: bool = False,
    ):
        """Plan and execute one direct MCP call with bounded provenance."""
        server_tools = []
        errors = []
        authorization_blocked = False
        excluded = list(excluded_tools)
        per_server = max(
            1, MAX_MCP_PLANNER_TOOLS // max(1, len(records))
        )
        for record in records:
            tools, context, error = self.list_tools(record, per_server)
            if error:
                errors.append(record.get("server_label", "MCP") + ": " + error)
            elif tools:
                allowed = record.get("allowed_tools", [])
                filtered = []
                for tool in tools:
                    signature = integration_key(record) + "|" + tool["name"]
                    if signature in excluded:
                        continue
                    if allowed and tool["name"] not in allowed:
                        continue
                    if not allow_mutation and tool_effect(tool) != "read":
                        authorization_blocked = True
                        continue
                    filtered.append(tool)
                if filtered:
                    server_tools.append((record, filtered, context))
        schemas, mapping = self._planner_tools(server_tools)
        if not schemas:
            return (
                "", 0,
                "; ".join(errors) or (
                    "Direct MCP tools are not declared read-only; the current "
                    "user request does not authorize mutation."
                    if authorization_blocked else
                    "Direct MCP servers exposed no tools"
                ),
                "",
            )
        name, arguments, error = self._plan_call(user_message, schemas)
        if error == "Direct MCP planner returned no tool call":
            name, arguments, error = self._plan_call(
                user_message, schemas, force_retry=True
            )
        if error:
            return "", 0, error, ""
        target = mapping.get(name)
        if target is None:
            return "", 0, "Direct MCP planner selected an unknown tool", ""
        record, tool, context = target
        provenance = integration_key(record) + "|" + tool["name"]
        if not allow_mutation and tool_effect(tool) != "read":
            return (
                "", 0,
                "Direct MCP mutation was not authorized by the current user "
                "request.",
                provenance,
            )
        payload, _status, _headers, error = self._rpc(
            record,
            "tools/call",
            {"name": tool["name"], "arguments": arguments},
            context["protocol"],
            context.get("session", ""),
        )
        if error:
            return "", 1, error, provenance
        evidence, error = self._tool_evidence(payload)
        if error:
            return "", 1, error, provenance
        return "# Direct MCP evidence\n" + evidence, 1, "", provenance

    def scan_integrations(self, records):
        """Refresh direct server tool names and routing capabilities."""
        scanned = []
        errors = []
        for record in records:
            tools, _context, error = self.list_tools(record)
            if error:
                errors.append(record.get("server_label", "MCP") + ": " + error)
                continue
            updated = dict(record)
            updated["allowed_tools"] = [tool["name"] for tool in tools[:12]]
            updated["tool_hints"] = tool_hints_from_definitions(tools)
            capabilities = []
            for tool in tools:
                hint = tool_hints_from_definitions([tool])
                inferred = _hint_capabilities(hint[0]) if hint else []
                for capability in (inferred or ["generic"]):
                    if capability not in capabilities:
                        capabilities.append(capability)
            updated["capabilities"] = capabilities or ["generic"]
            scanned.append(updated)
        if not scanned and errors:
            return list(records), "; ".join(errors)
        # Preserve failed records and replace successful records by key.
        replacements = {integration_key(item): item for item in scanned}
        return [
            replacements.get(integration_key(item), item) for item in records
        ], ""
