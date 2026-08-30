"""MCP - Standard MCP client over HTTP."""

import json


MCP_PROTOCOL_VERSION = "2025-11-25"
MCP_LIST_SERVERS_TOOL_NAME = "mcp_list_servers"
MCP_SELECT_SERVER_TOOL_NAME = "mcp_select_server"
MAX_TOOL_LIST_PAGES = 20

MCP_LIST_SERVERS_TOOL = {
    "type": "function",
    "function": {
        "name": MCP_LIST_SERVERS_TOOL_NAME,
        "description": (
            "List the configured MCP servers. Call this before selecting a server "
            "when you need MCP tools."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

MCP_SELECT_SERVER_TOOL = {
    "type": "function",
    "function": {
        "name": MCP_SELECT_SERVER_TOOL_NAME,
        "description": (
            "Select one MCP server by its server_id. This initializes the server "
            "and discovers its tools. Call mcp_list_servers first when needed."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "server_id": {
                    "type": "string",
                    "description": "The id returned by mcp_list_servers.",
                },
            },
            "required": ["server_id"],
        },
    },
}


class MCPError(Exception):
    """Raised when an MCP request or response is invalid."""


class MCPClient:
    """Client for standard MCP JSON-RPC requests over HTTP."""

    __slots__ = [
        "_http",
        "_servers",
        "_next_id",
        "_selected_server",
        "_session_id",
        "_protocol_version",
    ]

    def __init__(
        self,
        http,
        servers: list[dict] | None = None,
    ) -> None:
        """Initialize an MCP client from the configured endpoints.

        Args:
            http (HTTP): The Picoware HTTP client.
            servers (list[dict] or None): Configured MCP endpoint entries.
        """
        self._http = http
        self._servers = self._normalize_servers(servers)
        self._next_id = 0
        self._selected_server = None
        self._session_id = None
        self._protocol_version = MCP_PROTOCOL_VERSION

    @property
    def enabled(self) -> bool:
        """Return whether at least one MCP endpoint is configured."""
        return bool(self._servers)

    def reset(self) -> None:
        """Reset the selected server and MCP session for a new agent run."""
        self._next_id = 0
        self._selected_server = None
        self._session_id = None
        self._protocol_version = MCP_PROTOCOL_VERSION

    def list_servers(self) -> list[dict]:
        """Return configured servers without exposing their API keys."""
        return [self._public_server(server) for server in self._servers]

    def select_server(self, server_id: str) -> tuple[dict, list[dict]]:
        """Initialize a server and return its public details and MCP tools.

        Args:
            server_id (str): The id of the configured server to select.

        Returns:
            tuple[dict, list[dict]]: Public server details and raw MCP tool schemas.
        """
        if not isinstance(server_id, str) or not server_id:
            raise MCPError("A valid MCP server_id is required.")

        server = self._find_server(server_id)
        if server is None:
            raise MCPError("MCP server not found: " + server_id)

        self._selected_server = None
        self._session_id = None
        self._protocol_version = MCP_PROTOCOL_VERSION

        initialize_result, initialize_response = self._request(
            server,
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "Picoware",
                    "version": "1.0.0",
                },
            },
        )
        initialize_data = initialize_result.get("result")
        if not isinstance(initialize_data, dict):
            raise MCPError("MCP initialize returned no result.")

        self._session_id = self._header(
            getattr(initialize_response, "headers", None),
            "Mcp-Session-Id",
        )
        selected_protocol = initialize_data.get("protocolVersion")
        if isinstance(selected_protocol, str) and selected_protocol:
            self._protocol_version = selected_protocol

        self._request(
            server,
            "notifications/initialized",
            {},
            include_id=False,
        )
        tools = self._list_tools(server)
        self._selected_server = server
        return self._public_server(server), tools

    def call_tool(self, server_id: str, tool_name: str, arguments: dict) -> str:
        """Call a discovered tool on the selected MCP server.

        Args:
            server_id (str): The selected server id.
            tool_name (str): The original MCP tool name.
            arguments (dict): Tool arguments from the model.

        Returns:
            str: The JSON-encoded MCP tool result.
        """
        if self._selected_server is None:
            raise MCPError("Select an MCP server before calling its tools.")
        if self._selected_server.get("id") != server_id:
            raise MCPError("MCP tool belongs to a different selected server.")
        if not isinstance(tool_name, str) or not tool_name:
            raise MCPError("A valid MCP tool name is required.")
        if not isinstance(arguments, dict):
            raise MCPError("MCP tool arguments must be an object.")

        response, _ = self._request(
            self._selected_server,
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments,
            },
        )
        result = response.get("result")
        if not isinstance(result, dict):
            raise MCPError("MCP tools/call returned no result.")
        return json.dumps(result)

    def _list_tools(self, server: dict) -> list[dict]:
        tools = []
        params = {}
        for _ in range(MAX_TOOL_LIST_PAGES):
            response, _ = self._request(server, "tools/list", params)
            result = response.get("result")
            if not isinstance(result, dict):
                raise MCPError("MCP tools/list returned no result.")

            page_tools = result.get("tools", [])
            if not isinstance(page_tools, list):
                raise MCPError("MCP tools/list returned invalid tools.")
            for tool in page_tools:
                if isinstance(tool, dict) and isinstance(tool.get("name"), str):
                    tools.append(tool)

            cursor = result.get("nextCursor")
            if not isinstance(cursor, str) or not cursor:
                return tools
            params = {"cursor": cursor}

        raise MCPError("MCP tools/list returned too many pages.")

    def _request(
        self,
        server: dict,
        method: str,
        params: dict | None = None,
        include_id: bool = True,
    ) -> tuple[dict | None, object]:
        request_id = None
        payload = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if include_id:
            self._next_id += 1
            request_id = self._next_id
            payload["id"] = request_id
        if params is not None:
            payload["params"] = params

        try:
            response = self._http.post(
                server["endpoint"],
                payload,
                headers=self._headers(server, method != "initialize"),
                timeout=120,
            )
        except Exception as exc:
            raise MCPError("MCP request failed for " + method + ": " + str(exc)) from exc

        if response is None:
            raise MCPError("MCP request failed for " + method + ": no response.")

        status_code = getattr(response, "status_code", 0)
        if isinstance(status_code, int) and status_code >= 400:
            raise MCPError(
                "MCP request failed for "
                + method
                + " with HTTP status "
                + str(status_code)
                + "."
            )

        data = self._decode_response(response, request_id)
        if data is None:
            if include_id:
                raise MCPError("MCP request returned an empty response for " + method + ".")
            return None, response
        if not isinstance(data, dict):
            raise MCPError("MCP returned an invalid response for " + method + ".")
        if "error" in data:
            error = data.get("error")
            if isinstance(error, dict):
                message = error.get("message", str(error))
            else:
                message = str(error)
            raise MCPError("MCP request failed for " + method + ": " + str(message))
        if include_id and "result" not in data:
            raise MCPError("MCP response has no result for " + method + ".")
        return data, response

    def _headers(self, server: dict, include_protocol: bool = True) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            headers["MCP-Session-Id"] = self._session_id
        if include_protocol and self._protocol_version:
            headers["MCP-Protocol-Version"] = self._protocol_version

        api_key = server.get("api_key", "")
        if isinstance(api_key, str) and api_key:
            if api_key.lower().startswith("bearer "):
                headers["Authorization"] = api_key
            else:
                headers["Authorization"] = "Bearer " + api_key
        return headers

    @staticmethod
    def _decode_response(response, expected_id: int | None) -> dict | None:
        text = getattr(response, "text", "")
        if isinstance(text, bytes):
            text = text.decode("utf-8")
        if not isinstance(text, str):
            text = str(text)
        if not text.strip():
            return None

        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except (TypeError, ValueError):
            pass

        events = []
        data_lines = []
        for line in text.split("\n"):
            line = line.rstrip("\r")
            if line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
            elif not line.strip() and data_lines:
                MCPClient._append_sse_event(events, data_lines)
                data_lines = []
        if data_lines:
            MCPClient._append_sse_event(events, data_lines)

        if expected_id is not None:
            for event in events:
                if event.get("id") == expected_id:
                    return event
        if events:
            return events[-1]
        raise MCPError("MCP returned invalid JSON or SSE data.")

    @staticmethod
    def _append_sse_event(events: list[dict], data_lines: list[str]) -> None:
        event_data = "\n".join(data_lines).strip()
        if not event_data or event_data == "[DONE]":
            return
        try:
            event = json.loads(event_data)
        except (TypeError, ValueError):
            return
        if isinstance(event, dict):
            events.append(event)

    @staticmethod
    def _normalize_servers(servers: list[dict] | None) -> list[dict]:
        normalized = []
        used_ids = []

        if not isinstance(servers, list):
            return normalized

        for index, entry in enumerate(servers):
            if not isinstance(entry, dict):
                continue
            endpoint = entry.get("endpoint")
            if not isinstance(endpoint, str) or not endpoint.strip():
                endpoint = entry.get("path")
            if not isinstance(endpoint, str) or not endpoint.strip():
                continue

            server_id = entry.get("id")
            if not isinstance(server_id, str) or not server_id:
                server_id = "server_" + str(index)
            base_id = server_id
            suffix = 1
            while server_id in used_ids:
                server_id = base_id + "_" + str(suffix)
                suffix += 1
            used_ids.append(server_id)

            name = entry.get("name")
            if not isinstance(name, str) or not name.strip():
                name = "MCP Server " + str(index + 1)
            api_key = entry.get("api_key", "")
            if not isinstance(api_key, str):
                api_key = ""
            description = entry.get("description", "")
            if not isinstance(description, str):
                description = ""
            normalized.append(
                {
                    "id": server_id,
                    "name": name.strip(),
                    "endpoint": endpoint.strip(),
                    "api_key": api_key,
                    "description": description.strip(),
                }
            )
        return normalized

    def _find_server(self, server_id: str) -> dict | None:
        for server in self._servers:
            if server.get("id") == server_id:
                return server
        return None

    @staticmethod
    def _public_server(server: dict) -> dict:
        public_server = {
            "id": server.get("id", ""),
            "name": server.get("name", ""),
            "endpoint": server.get("endpoint", ""),
        }
        description = server.get("description", "")
        if description:
            public_server["description"] = description
        return public_server

    @staticmethod
    def _header(headers, name: str):
        if not isinstance(headers, dict):
            return None
        name = name.lower()
        for key, value in headers.items():
            if str(key).lower() == name:
                return value
        return None