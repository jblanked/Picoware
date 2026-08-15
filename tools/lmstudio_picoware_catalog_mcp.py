#!/usr/bin/env python3
"""Read-only LM Studio integration catalog for the Picoware Agent.

The server intentionally returns names and integration types only. It never
returns MCP commands, arguments, environment variables, paths, or secrets.
It uses MCP over stdio and depends only on the Python standard library.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


SERVER_NAME = "picoware-integration-catalog"
TOOL_NAME = "list_integrations"


def _plugin_has_tools_provider(plugin_dir: Path) -> bool:
    """Return whether a plugin's own source registers a tools provider.

    Bundled dependencies are intentionally ignored because the LM Studio SDK
    itself contains ``setToolsProvider`` even when the plugin never uses it.
    """
    source_root = plugin_dir / "src"
    if not source_root.is_dir():
        return False

    for suffix in ("*.ts", "*.js", "*.mjs", "*.cjs"):
        for source_path in source_root.rglob(suffix):
            try:
                if source_path.stat().st_size > 512 * 1024:
                    continue
                source = source_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if "withToolsProvider(" in source or "setToolsProvider(" in source:
                return True
    return False


def discover_integrations(home: Path | None = None) -> list[dict[str, str]]:
    """Return stable, non-secret IDs for configured MCPs and installed plugins."""
    base = home if home is not None else Path.home()
    found: dict[str, dict[str, str]] = {}

    mcp_path = base / ".lmstudio" / "mcp.json"
    try:
        config = json.loads(mcp_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        config = {}

    servers = config.get("mcpServers", {}) if isinstance(config, dict) else {}
    if isinstance(servers, dict):
        for label in servers:
            if not isinstance(label, str) or not label.strip():
                continue
            if "/" in label:
                # LM Studio removes separators when it creates the runtime
                # mcpBridge artifact. Its manifest below is authoritative.
                continue
            integration_id = "mcp/" + label.strip()
            if integration_id == "mcp/" + SERVER_NAME:
                continue
            found[integration_id] = {
                "id": integration_id,
                "type": "mcp",
                "label": label.strip(),
            }

    plugin_root = base / ".lmstudio" / "extensions" / "plugins"
    for manifest_path in sorted(plugin_root.glob("*/*/manifest.json")):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(manifest, dict):
            continue
        if manifest.get("runner") == "mcpBridge":
            owner = manifest.get("owner")
            name = manifest.get("name")
            if not isinstance(owner, str) or not isinstance(name, str):
                continue
            if not owner.strip() or not name.strip():
                continue
            integration_id = owner.strip() + "/" + name.strip()
            if integration_id == "mcp/" + SERVER_NAME:
                continue
            found[integration_id] = {
                "id": integration_id,
                "type": "mcp",
                "label": name.strip(),
            }
            continue
        if not _plugin_has_tools_provider(manifest_path.parent):
            continue
        owner = manifest.get("owner")
        name = manifest.get("name")
        if not isinstance(owner, str) or not isinstance(name, str):
            continue
        if not owner.strip() or not name.strip():
            continue
        runtime_id = owner.strip() + "/" + name.strip()
        stored_id = "plugin:" + runtime_id
        found[stored_id] = {
            "id": stored_id,
            "type": "plugin",
            "label": runtime_id,
        }

    return [found[key] for key in sorted(found)]


def _result(request_id, result: dict) -> None:
    print(
        json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result}, separators=(",", ":")),
        flush=True,
    )


def _error(request_id, code: int, message: str) -> None:
    print(
        json.dumps(
            {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}},
            separators=(",", ":"),
        ),
        flush=True,
    )


def handle(message: dict) -> None:
    """Handle one JSON-RPC message from LM Studio."""
    method = message.get("method")
    request_id = message.get("id")

    if method == "initialize":
        requested = message.get("params", {}).get("protocolVersion", "2024-11-05")
        _result(
            request_id,
            {
                "protocolVersion": requested,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": "1.0.0"},
            },
        )
    elif method == "ping":
        _result(request_id, {})
    elif method == "tools/list":
        _result(
            request_id,
            {
                "tools": [
                    {
                        "name": TOOL_NAME,
                        "description": "List configured LM Studio MCP and plugin IDs without secrets.",
                        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
                    }
                ]
            },
        )
    elif method == "tools/call":
        params = message.get("params", {})
        if params.get("name") != TOOL_NAME:
            _error(request_id, -32602, "Unknown tool")
            return
        payload = json.dumps(discover_integrations(), separators=(",", ":"))
        _result(request_id, {"content": [{"type": "text", "text": payload}]})
    elif request_id is not None:
        _error(request_id, -32601, "Method not found")


def main() -> int:
    """Run the line-delimited MCP stdio loop."""
    for line in sys.stdin:
        try:
            message = json.loads(line)
        except ValueError:
            _error(None, -32700, "Parse error")
            continue
        if isinstance(message, dict):
            handle(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
