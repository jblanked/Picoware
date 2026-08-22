"""Bounded, provider-neutral MCP integration gateway support."""

import json
from micropython import const
from picoware.system.agent.authorization import (
    request_authorizes_mutation,
    tool_effect,
)


MAX_MCP_CALLS = const(4)
# Compatibility name retained; all enforcement uses UTF-8 bytes, not codepoints.
MAX_MCP_EVIDENCE_CHARS = const(8192)
MAX_MCP_EVENT_BYTES = const(16384)
# Raw SSE is useful only as a bounded diagnostic spool on SD.  It is not a
# heap limit: complete events are parsed incrementally and discarded.
MAX_MCP_STREAM_BYTES = const(262144)
MAX_MCP_STREAM_EVENTS = const(2048)
MAX_DISCOVERED_INTEGRATIONS = const(64)
MAX_SELECTED_INTEGRATIONS = const(8)
MAX_MCP_TOOL_ID_CHARS = const(256)
MAX_MCP_ERROR_CHARS = const(256)
MAX_MCP_RECORD_ID_CHARS = const(256)
MAX_MCP_RECORD_LABEL_CHARS = const(96)
MAX_MCP_RECORD_URL_CHARS = const(512)
MAX_MCP_CAPABILITY_CHARS = const(32)
MAX_MCP_ALLOWED_TOOL_CHARS = const(128)
MAX_MCP_BROWSER_CONTEXT_CHARS = const(3072)
MAX_TOOL_HINTS = const(12)
MAX_TOOL_HINT_DESC_BYTES = const(160)
MAX_TOOL_HINT_INPUT_COUNT = const(8)
MAX_TOOL_HINT_INPUT_BYTES = const(48)
MAX_TOOL_HINT_CAPABILITY_COUNT = const(4)

MCP_OUTCOME_COMPLETED = "completed"
MCP_OUTCOME_NOT_NEEDED = "not_needed"
MCP_OUTCOME_PARTIAL = "partial"
MCP_OUTCOME_FAILED = "failed"


def mcp_outcome(
    status: str, evidence: str = "", error: str = "", calls: int = 0,
) -> dict:
    """Return one bounded structured result from the MCP agent loop."""
    return {
        "status": status,
        "evidence": evidence if isinstance(evidence, str) else "",
        "error": error if isinstance(error, str) else str(error),
        "calls": max(0, int(calls)),
    }


def _unique_strings(
    value: str | list[str] | tuple[str, ...],
    limit: int = 16,
    max_chars: int = MAX_MCP_ALLOWED_TOOL_CHARS,
) -> list[str]:
    """Return a bounded list of non-empty unique strings."""
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple)):
        return []
    result: list[str] = []
    inspected = 0
    for item in value:
        inspected += 1
        if inspected > limit * 4:
            break
        if not isinstance(item, str):
            continue
        item = item.strip()
        if (
            item and _utf8_size(item, max_chars) <= max_chars
            and item not in result
        ):
            result.append(item)
        if len(result) >= limit:
            break
    return result


def _normalized_identity(value: str) -> str:
    """Return one stable comparison form for a discovered identity."""
    if not isinstance(value, str):
        return ""
    value = value.lower()
    for separator in ("/", "-", "_", ".", ",", ";", ":", "(", ")", "[", "]"):
        value = value.replace(separator, " ")
    return " ".join(value.split())


def _record_match_values(record: dict) -> list[str]:
    """Return dynamic display and identity values for one scanned record."""
    values: list[str] = []
    for value in (
        record.get("label", ""),
        record.get("id", record.get("server_label", "")),
    ):
        if isinstance(value, str) and value and value not in values:
            values.append(value)
            basename = value.rsplit("/", 1)[-1]
            if basename and basename != value and basename not in values:
                values.append(basename)
    return values


def explicit_integration_records(records, user_message: str):
    """Return the single longest exact discovered identity in the request."""
    selectable = [
        record for record in records
        if "catalog" not in record.get("capabilities", [])
    ]
    padded = " " + _normalized_identity(user_message) + " "
    longest = 0
    matches = []
    for record in selectable:
        record_best = 0
        for value in _record_match_values(record):
            candidate = _normalized_identity(value)
            if candidate and (" " + candidate + " ") in padded:
                record_best = max(record_best, len(candidate))
        if record_best > longest:
            longest = record_best
            matches = [record]
        elif record_best and record_best == longest:
            matches.append(record)
    if not matches:
        return [], False
    return (matches, False) if len(matches) == 1 else ([], True)


def _legacy_capabilities(integration_id: str) -> list[str]:
    """Retain only the explicit catalog migration for old ID-only entries."""
    lower = integration_id.lower()
    if "catalog" in lower or "list-integrations" in lower:
        return ["catalog"]
    return ["generic"]


def _bounded_text(value: str | int | float | bool | None, maximum: int) -> str:
    """Return stripped text bounded by UTF-8 bytes."""
    if not isinstance(value, str):
        return ""
    value = value.strip()
    return _utf8_prefix(value, maximum)[0]


def normalize_tool_hint(value: dict) -> dict | None:
    """Return one compact, credential-free discovered tool description."""
    if not isinstance(value, dict):
        return None
    name = _bounded_text(value.get("name", ""), MAX_MCP_ALLOWED_TOOL_CHARS)
    if not name:
        return None
    description = _bounded_text(
        value.get("description", value.get("title", "")),
        MAX_TOOL_HINT_DESC_BYTES,
    )
    raw_inputs = value.get("inputs", [])
    if not raw_inputs and isinstance(value.get("inputSchema"), dict):
        properties = value["inputSchema"].get("properties", {})
        if isinstance(properties, dict):
            raw_inputs = []
            for property_name in properties:
                raw_inputs.append(property_name)
                if len(raw_inputs) >= MAX_TOOL_HINT_INPUT_COUNT * 2:
                    break
    inputs = []
    if isinstance(raw_inputs, (list, tuple)):
        for raw_input in raw_inputs[:MAX_TOOL_HINT_INPUT_COUNT * 2]:
            input_name = _bounded_text(raw_input, MAX_TOOL_HINT_INPUT_BYTES)
            if input_name and input_name not in inputs:
                inputs.append(input_name)
            if len(inputs) >= MAX_TOOL_HINT_INPUT_COUNT:
                break
    result: dict = {"name": name, "description": description, "inputs": inputs}
    annotations = value.get("annotations", {})
    if not isinstance(annotations, dict):
        annotations = {}
    read_only = value.get("read_only", annotations.get("readOnlyHint"))
    destructive = value.get(
        "destructive", annotations.get("destructiveHint")
    )
    # Absence means unknown; it must not be silently treated as read-only.
    if isinstance(read_only, bool):
        result["read_only"] = read_only
    if isinstance(destructive, bool):
        result["destructive"] = destructive
    open_world = value.get(
        "open_world", annotations.get("openWorldHint")
    )
    if isinstance(open_world, bool):
        result["open_world"] = open_world
    if value.get("request_scoped") is True:
        result["request_scoped"] = True
    capabilities = _unique_strings(
        value.get("capabilities", []),
        MAX_TOOL_HINT_CAPABILITY_COUNT,
        MAX_MCP_CAPABILITY_CHARS,
    )
    if capabilities:
        result["capabilities"] = capabilities
    return result


def tool_hints_from_definitions(values: list[dict] | tuple[dict, ...]) -> list[dict]:
    """Return bounded hints from catalog or direct tools/list definitions."""
    if not isinstance(values, (list, tuple)):
        return []
    hints: list[dict] = []
    names: list[str] = []
    inspected = 0
    for value in values:
        inspected += 1
        if inspected > MAX_TOOL_HINTS * 4:
            break
        hint = normalize_tool_hint(value)
        if hint is None or hint["name"] in names:
            continue
        hints.append(hint)
        names.append(hint["name"])
        if len(hints) >= MAX_TOOL_HINTS:
            break
    return hints


def _hint_capabilities(hint: dict) -> list[str]:
    """Infer portable routing hints from discovered tool metadata."""
    if not isinstance(hint, dict):
        return []
    name = hint.get("name", "")
    description = hint.get("description", "")
    inputs = hint.get("inputs", [])
    text = (str(name) + " " + str(description)).lower()
    input_text = " ".join(inputs).lower() if isinstance(inputs, list) else ""
    capabilities = _unique_strings(
        hint.get("capabilities", []),
        MAX_TOOL_HINT_CAPABILITY_COUNT,
        MAX_MCP_CAPABILITY_CHARS,
    )
    page_local_search = any(marker in text for marker in (
        "current page", "current document", "accessibility snapshot",
        "search within", "find text on", "find text in",
    ))
    if not page_local_search and any(word in text for word in (
        "search", "lookup", "query", "find documents", "find pages",
    )):
        capabilities.append("search")
    url_input = any(word in (" " + input_text + " ") for word in (
        " url ", " uri ", " href ", " link ", " address ",
    ))
    if url_input or any(word in text for word in (
        "page content", "resource content", "retrieve content", "read url",
        "read page", "read website", "open page", "open url", "navigate",
        "fetch", "visit", "get page",
    )):
        capabilities.append("fetch")
    if any(word in text for word in (
        "current time", "current date", "clock", "timezone",
    )):
        capabilities.append("time")
    return capabilities


def _hint_requires_prior_context(hint: dict) -> bool:
    """Return whether discovered metadata describes a resource-local action."""
    if not isinstance(hint, dict):
        return False
    text = (
        str(hint.get("name", "")) + " "
        + str(hint.get("description", ""))
    ).lower()
    return any(marker in text for marker in (
        "current page", "current document", "accessibility snapshot",
        "search within", "find text on", "find text in",
        "console messages", "network requests", "since loading",
        "single network request", "text to appear", "text to disappear",
        "on page", "on a web page", "previous page",
    ))


def _hint_observes_current_resource(hint: dict) -> bool:
    """Return whether a read-only hint returns current resource contents."""
    if not isinstance(hint, dict) or hint.get("read_only") is not True:
        return False
    text = (
        str(hint.get("name", "")) + " "
        + str(hint.get("description", ""))
    ).lower()
    action_text = " " + text.replace("_", " ").replace("-", " ") + " "
    if any(marker in text for marker in (
        "search within", "find text", "wait for", "click", "type into",
    )) or any(marker in action_text for marker in (
        " search ", " find ", " wait ", " click ", " type ",
    )):
        return False
    return any(marker in text for marker in (
        "accessibility snapshot", "current page content",
        "current document content", "current resource content",
    ))


def _record_capabilities(record: dict) -> list[str]:
    """Return saved and metadata-derived capabilities without hard gating."""
    if not isinstance(record, dict):
        return []
    capabilities: list[str] = _unique_strings(record.get("capabilities", []), 8, 32)
    for hint in record.get("tool_hints", []):
        for capability in _hint_capabilities(hint):
            if capability not in capabilities:
                capabilities.append(capability)
    return capabilities or ["generic"]


def _contains_url(value: str) -> bool:
    """Return whether bounded evidence contains a directly usable URL."""
    return isinstance(value, str) and (
        "http://" in value.lower() or "https://" in value.lower()
    )


def _record_accepts_url(record: dict) -> bool:
    """Return whether discovered metadata describes a URL consumer."""
    if not isinstance(record, dict):
        return False
    if "fetch" in _record_capabilities(record):
        return True
    for hint in record.get("tool_hints", []):
        inputs = hint.get("inputs", []) if isinstance(hint, dict) else []
        for name in inputs:
            if name.lower() in ("url", "uri", "href", "link", "address"):
                return True
    return False


def _tool_is_request_scoped_fetch(record: dict, tool_name: str) -> bool:
    """Return whether one actually called tool is a bounded URL action."""
    if not isinstance(record, dict) or not isinstance(tool_name, str):
        return False
    for hint in record.get("tool_hints", []):
        if (
            isinstance(hint, dict)
            and hint.get("name") == tool_name
            and hint.get("request_scoped") is True
            and "fetch" in _hint_capabilities(hint)
        ):
            return True
    return False


def _tool_is_session_observer(record: dict, tool_name: str) -> bool:
    """Return whether a called tool completes a request-scoped read session."""
    if not isinstance(record, dict) or not isinstance(tool_name, str):
        return False
    has_action = any(
        isinstance(hint, dict)
        and hint.get("request_scoped") is True
        and "fetch" in _hint_capabilities(hint)
        for hint in record.get("tool_hints", [])
    )
    if not has_action:
        return False
    return any(
        isinstance(hint, dict)
        and hint.get("name") == tool_name
        and _hint_observes_current_resource(hint)
        for hint in record.get("tool_hints", [])
    )


def _tool_has_capability(record: dict, tool_name: str, capability: str) -> bool:
    """Return whether discovered metadata assigns a capability to one tool."""
    if not isinstance(record, dict) or not isinstance(tool_name, str):
        return False
    for hint in record.get("tool_hints", []):
        if (
            isinstance(hint, dict)
            and hint.get("name") == tool_name
            and capability in _hint_capabilities(hint)
        ):
            return True
    return False


def _authorized_tool_names(
    record: dict, names, role: str = "request",
    allow_mutation: bool = False,
) -> list[str]:
    """Return role-selected tools permitted by effects and host policy."""
    selected = list(names) if isinstance(names, (list, tuple)) else []
    if allow_mutation:
        return selected
    hints = {}
    for hint in record.get("tool_hints", []):
        if isinstance(hint, dict) and hint.get("name"):
            hints[hint["name"]] = hint
    allowed = []
    expected = "fetch" if role == "url" else role
    for name in selected:
        hint = hints.get(name, {})
        if tool_effect(hint) == "read":
            allowed.append(name)
            continue
        if (
            hint.get("request_scoped") is True
            and (
                expected in _hint_capabilities(hint)
                or (
                    role == "request"
                    and hint.get("open_world") is True
                    and bool(_hint_capabilities(hint))
                )
            )
        ):
            allowed.append(name)
    return allowed


def _record_has_authorized_tool(record: dict) -> bool:
    """Return whether metadata exposes a tool safe for model selection."""
    if not isinstance(record, dict):
        return False
    for hint in record.get("tool_hints", []):
        if not isinstance(hint, dict):
            continue
        if tool_effect(hint) == "read":
            return True
        if (
            hint.get("request_scoped") is True
            and hint.get("open_world") is True
            and bool(_hint_capabilities(hint))
        ):
            return True
    return False


def _url_candidate_records(records, excluded_tools=()) -> list[dict]:
    """Return enabled URL consumers with at least one unused tool."""
    excluded = list(excluded_tools) if isinstance(
        excluded_tools, (list, tuple)
    ) else []
    result = []
    for record in records:
        if (
            not isinstance(record, dict)
            or "catalog" in _record_capabilities(record)
            or not _record_accepts_url(record)
        ):
            continue
        key = integration_key(record)
        if any(
            isinstance(hint, dict)
            and "fetch" in _hint_capabilities(hint)
            and key + "|" + hint.get("name", "") not in excluded
            for hint in record.get("tool_hints", [])
        ):
            result.append(record)
        if len(result) >= MAX_SELECTED_INTEGRATIONS:
            break
    return result


def _tool_names_for_role(
    record: dict,
    role: str,
) -> list[str]:
    """Return discovered tools for the initial or URL follow-on stage."""
    names: list[str] = []
    for hint in record.get("tool_hints", []):
        if not isinstance(hint, dict):
            continue
        include = role == "request" and not _hint_requires_prior_context(hint)
        capabilities = _hint_capabilities(hint)
        if role == "url" and "fetch" in capabilities:
            include = True
        name = hint.get("name", "")
        if include and name and name not in names:
            names.append(name)
    return names[:MAX_TOOL_HINTS]


def _continuation_plan(record: dict, staged: dict, role: str) -> dict:
    """Describe a metadata-derived request action followed by observation."""
    if role not in ("request", "url") or not isinstance(staged, dict):
        return {}
    allowed = staged.get("allowed_tools", [])
    if not isinstance(allowed, list):
        return {}
    actions = [
        name for name in allowed
        if _tool_is_request_scoped_fetch(record, name)
    ]
    observers = []
    for hint in record.get("tool_hints", []):
        if not isinstance(hint, dict):
            continue
        name = hint.get("name", "")
        if (
            name in allowed and _hint_observes_current_resource(hint)
            and name not in observers
        ):
            observers.append(name)
    if not actions or not observers:
        return {}
    provider = record.get("id", "")
    if record.get("type") == "ephemeral_mcp":
        provider = record.get("server_label", "")
    return {
        "provider": provider,
        "actions": actions[:MAX_TOOL_HINTS],
        "observers": observers[:MAX_TOOL_HINTS],
    }


def normalize_integration_record(value: str | dict) -> dict | None:
    """Normalize one saved plugin or ephemeral MCP record."""
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text[:1] in ("[", "{"):
            try:
                parsed = json.loads(text)
            except ValueError:
                return None
            if isinstance(parsed, dict):
                return normalize_integration_record(parsed)
            return None
        if text.startswith("server:") or text.startswith("ephemeral:"):
            details = text.split(":", 1)[1]
            parts = details.split("|", 1)
            if len(parts) != 2:
                return None
            label = parts[0].strip()
            url = parts[1].strip()
            if (
                not label
                or _utf8_size(label, MAX_MCP_RECORD_LABEL_CHARS)
                > MAX_MCP_RECORD_LABEL_CHARS
                or _utf8_size(url, MAX_MCP_RECORD_URL_CHARS)
                > MAX_MCP_RECORD_URL_CHARS
                or not url.startswith(("http://", "https://"))
            ):
                return None
            return {
                "type": "ephemeral_mcp",
                "server_label": label,
                "server_url": url,
                "capabilities": _legacy_capabilities(label),
            }
        integration_id = text[7:].strip() if text.startswith("plugin:") else text
        if (
            not integration_id
            or _utf8_size(integration_id, MAX_MCP_RECORD_ID_CHARS)
            > MAX_MCP_RECORD_ID_CHARS
        ):
            return None
        return {
            "type": "plugin",
            "id": integration_id,
            "capabilities": _legacy_capabilities(integration_id),
        }

    if not isinstance(value, dict):
        return None
    record_type = value.get("type", "plugin")
    if record_type in ("ephemeral_mcp", "mcp_server") or value.get("server_url"):
        label = value.get("server_label", value.get("label", ""))
        url = value.get("server_url", "")
        if not isinstance(label, str) or not isinstance(url, str):
            return None
        label = label.strip()
        url = url.strip()
        if (
            not label
            or _utf8_size(label, MAX_MCP_RECORD_LABEL_CHARS)
            > MAX_MCP_RECORD_LABEL_CHARS
            or _utf8_size(url, MAX_MCP_RECORD_URL_CHARS)
            > MAX_MCP_RECORD_URL_CHARS
            or not url.startswith(("http://", "https://"))
        ):
            return None
        # Older direct-server records are intentionally normalized onto the
        # sole supported transport: LM Studio ephemeral MCP integrations.
        record: dict = {
            "type": "ephemeral_mcp",
            "server_label": label,
            "server_url": url,
        }
    else:
        integration_id = value.get("id", "")
        if not isinstance(integration_id, str) or not integration_id.strip():
            return None
        integration_id = integration_id.strip()
        if integration_id.startswith("plugin:"):
            integration_id = integration_id[7:].strip()
        if (
            not integration_id
            or _utf8_size(integration_id, MAX_MCP_RECORD_ID_CHARS)
            > MAX_MCP_RECORD_ID_CHARS
        ):
            return None
        record = {"type": "plugin", "id": integration_id}

    label = value.get("label", "")
    if isinstance(label, str) and label.strip():
        label = label.strip()
        if (
            _utf8_size(label, MAX_MCP_RECORD_LABEL_CHARS)
            <= MAX_MCP_RECORD_LABEL_CHARS
        ):
            record["label"] = label
    allowed_tools = _unique_strings(
        value.get("allowed_tools", []), 12, MAX_MCP_ALLOWED_TOOL_CHARS
    )
    raw_hints = value.get("tool_hints", [])
    if not raw_hints:
        raw_hints = value.get("tools", [])
    if not raw_hints and allowed_tools:
        raw_hints = [{"name": name} for name in allowed_tools]
    tool_hints = tool_hints_from_definitions(raw_hints)
    capabilities = _unique_strings(
        value.get("capabilities", []), 8, MAX_MCP_CAPABILITY_CHARS
    )
    for hint in tool_hints:
        for capability in _hint_capabilities(hint):
            if capability not in capabilities:
                capabilities.append(capability)
    if not capabilities:
        identity = record.get("id", record.get("server_label", ""))
        capabilities = _legacy_capabilities(identity)
    record["capabilities"] = capabilities
    if allowed_tools:
        record["allowed_tools"] = allowed_tools
    if tool_hints:
        record["tool_hints"] = tool_hints
    return record


def parse_integration_records(
    value: str | dict | list,
    limit: int = 16,
) -> list[dict]:
    """Parse JSON records or legacy comma/newline integration settings."""
    maximum = max(1, min(int(limit), MAX_DISCOVERED_INTEGRATIONS))
    if isinstance(value, str):
        text = value.strip()
        parsed = None
        if text[:1] in ("[", "{"):
            try:
                parsed = json.loads(text)
            except ValueError:
                return []
            if isinstance(parsed, dict):
                values = parsed.get("integrations", [parsed])
            elif isinstance(parsed, list):
                values = parsed
            else:
                return []
        else:
            values = text.replace("\n", ",").split(",")
    elif isinstance(value, dict):
        values = value.get("integrations", [value])
    elif isinstance(value, list):
        values = value
    else:
        return []

    if isinstance(values, str):
        return parse_integration_records(values, maximum)
    if isinstance(values, dict):
        values = [values]
    if not isinstance(values, (list, tuple)):
        return []

    records: list[dict] = []
    keys: list[str] = []
    for item in values:
        record = normalize_integration_record(item)
        if record is None:
            continue
        key = integration_key(record)
        if key and key not in keys:
            records.append(record)
            keys.append(key)
        if len(records) >= maximum:
            break
    return records


def serialize_integration_records(records) -> str:
    """Serialize normalized records for persistent settings."""
    return json.dumps(parse_integration_records(records))


def integration_key(record) -> str:
    """Return a stable identity without altering an opaque provider ID."""
    if not isinstance(record, dict):
        record = normalize_integration_record(record)
    if not record:
        return ""
    if record.get("type") == "ephemeral_mcp":
        return (
            "ephemeral:" + record.get("server_label", "")
            + "|" + record.get("server_url", "")
        )
    return "plugin:" + record.get("id", "")


def integration_label(record: dict) -> str:
    """Return a compact display label for one integration record."""
    if not isinstance(record, dict):
        record = normalize_integration_record(record)
    if not record:
        return "Invalid integration"
    label = record.get("label", "")
    if label:
        return label
    if record.get("type") == "ephemeral_mcp":
        return record.get("server_label", "MCP server")
    return record.get("id", "Integration")


def merge_integration_records(
    current: list[dict],
    discovered: list[dict],
    limit: int = 64,
) -> list[dict]:
    """Merge discovery metadata while preserving configured identity and secrets."""
    merged = parse_integration_records(current, limit)
    positions: dict[str, int] = {
        integration_key(record): index for index, record in enumerate(merged)
    }
    for discovered_record in parse_integration_records(discovered, limit):
        key = integration_key(discovered_record)
        if key not in positions:
            positions[key] = len(merged)
            merged.append(discovered_record)
        else:
            index = positions[key]
            refreshed = dict(merged[index])
            for field in ("label", "allowed_tools", "tool_hints"):
                if discovered_record.get(field):
                    refreshed[field] = discovered_record[field]
            current_capabilities = refreshed.get("capabilities", [])
            discovered_capabilities = discovered_record.get("capabilities", [])
            if (
                "catalog" not in current_capabilities
                and discovered_capabilities
                and (
                    discovered_capabilities != ["generic"]
                    or not current_capabilities
                    or current_capabilities == ["generic"]
                )
            ):
                refreshed["capabilities"] = discovered_capabilities
            normalized = normalize_integration_record(refreshed)
            if normalized is not None:
                merged[index] = normalized
        if len(merged) >= limit:
            break
    return merged[:limit]


def preserve_catalog_records(
    previous: list[dict],
    updated: list[dict],
    limit: int = 16,
) -> list[dict]:
    """Return updated records while retaining configured catalog providers.

    Catalog integrations are scanner infrastructure, not ordinary tools.  A
    tool-selection edit must therefore never make the next scan unable to
    discover integrations.
    """
    previous_records = parse_integration_records(previous, limit)
    updated_records = parse_integration_records(updated, limit)
    catalogs = [
        record for record in previous_records + updated_records
        if "catalog" in record.get("capabilities", [])
    ]
    selectable = [
        record for record in updated_records
        if "catalog" not in record.get("capabilities", [])
    ]
    return parse_integration_records(catalogs + selectable, limit)


def parse_integration_catalog(
    value: str | dict | list,
    limit: int = MAX_DISCOVERED_INTEGRATIONS,
) -> list[dict]:
    """Extract integration records from a bounded catalog tool result."""
    records: list[dict] = []
    record_keys: list[str] = []
    maximum = max(1, min(int(limit), MAX_DISCOVERED_INTEGRATIONS))

    def collect(item: str | dict | list) -> None:
        if len(records) >= maximum:
            return
        if isinstance(item, str):
            text = item.strip()
            if not text:
                return
            try:
                parsed = json.loads(text)
            except ValueError:
                start = text.find("[")
                end = text.rfind("]")
                if start < 0 or end <= start:
                    return
                try:
                    parsed = json.loads(text[start:end + 1])
                except ValueError:
                    return
            collect(parsed)
            return
        if isinstance(item, list):
            for child in item:
                collect(child)
                if len(records) >= maximum:
                    break
            return
        if not isinstance(item, dict):
            return

        if item.get("id") or item.get("server_url"):
            record = normalize_integration_record(item)
            if record is not None and "catalog" not in record.get(
                "capabilities", []
            ):
                key = integration_key(record)
                if key not in record_keys:
                    records.append(record)
                    record_keys.append(key)
        for key in ("integrations", "text", "content", "output", "result"):
            if key in item:
                collect(item[key])
                if len(records) >= maximum:
                    break

    collect(value)
    return records


def _argument_signature(arguments):
    """Return a bounded signature without retaining large tool arguments."""
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
    """Record a gateway tool call and return a loop violation if present."""
    signature = _argument_signature(arguments)
    repeated = 0
    for previous_name, previous_signature in history:
        if previous_name == name and previous_signature == signature:
            repeated += 1
    if repeated >= 1:
        return "tool '" + name + "' repeated with identical arguments"
    history.append((name, signature))
    return ""


def _utf8_prefix(value, max_bytes: int):
    """Return a UTF-8 byte-bounded prefix without encoding the whole string."""
    if not isinstance(value, str):
        value = str(value)
    maximum = max(0, int(max_bytes))
    used = 0
    index = 0
    for char in value:
        code = ord(char)
        size = 1 if code <= 0x7F else 2 if code <= 0x7FF else 3
        if code > 0xFFFF:
            size = 4
        if used + size > maximum:
            break
        used += size
        index += 1
    if index == len(value):
        return value, used
    return value[:index], used


def _utf8_size(value, stop_after: int = 0) -> int:
    """Count UTF-8 bytes without materializing an encoded copy."""
    if not isinstance(value, str):
        value = str(value)
    used = 0
    for char in value:
        code = ord(char)
        used += 1 if code <= 0x7F else 2 if code <= 0x7FF else 3
        if code > 0xFFFF:
            used += 1
        if stop_after and used > stop_after:
            break
    return used


def _append_bounded_evidence(
    parts, heading: str, value, used: int,
    limit: int = MAX_MCP_EVIDENCE_CHARS,
) -> int:
    """Append one evidence section without exceeding the turn-wide limit."""
    if not value or used >= limit:
        return used
    if not isinstance(value, str):
        value = str(value)
    separator = 2 if parts else 0
    remaining = limit - used - separator
    if remaining <= 0:
        return used
    prefix = (heading + "\n") if heading else ""
    if len(prefix) > remaining:
        prefix = prefix[:remaining]
    value, value_bytes = _utf8_prefix(value, remaining - len(prefix))
    section = (prefix + value).strip()
    if not section:
        return used
    parts.append(section)
    # Prefix/separators are ASCII. Stripping can only make this conservative.
    return used + separator + len(prefix) + value_bytes


def _current_time_grounding(view_manager) -> str:
    """Return current-time guidance from the device clock."""
    from picoware.system.agent.tools.network import network_get_time_info

    info = network_get_time_info(view_manager)
    current = info["current_local_datetime"]
    if info["clock_is_set"] and current:
        return (
            "\n\nThe device clock is set to " + current
            + " with UTC offset " + info["utc_offset"] + "."
        )
    return (
        "\n\nThe device clock is not set. Do not guess the current date; "
        "use an available current-time tool when the request depends on it."
    )


def create_mcp_client(view_manager, http, llm, status_callback=None):
    """Create the configured MCP facade without coupling Agent to a provider."""
    from picoware.system.agent.llm import LOCAL_MCP

    if llm.id != LOCAL_MCP:
        return None
    return MCPClient(view_manager, http, llm, status_callback)


class MCPClient:
    """Provider-neutral facade over LM Studio MCP integrations."""

    __slots__ = (
        "view_manager", "http", "llm", "records", "integrations",
        "lmstudio", "status_callback", "_last_gateway_provider",
        "_last_gateway_tool",
    )

    def __init__(self, view_manager, http, llm, status_callback=None):
        from picoware.system.agent.mcp_lmstudio import LMStudioMCPAdapter
        from picoware.system.settings import Settings

        settings = Settings(view_manager.storage)
        self.view_manager = view_manager
        self.http = http
        self.llm = llm
        self.status_callback = status_callback
        self._last_gateway_provider = ""
        self._last_gateway_tool = ""
        self.records = parse_integration_records(settings.mcp_integrations)
        self.integrations = [integration_key(item) for item in self.records]
        self.lmstudio = LMStudioMCPAdapter(
            view_manager, http, llm, settings.mcp_gateway_url,
            self._gateway_tool_status,
        )

    @property
    def enabled(self) -> bool:
        """Return whether at least one integration transport is configured."""
        return bool(self.records)

    def cancel(self) -> None:
        """Cancel the currently active adapter operation."""
        self.http.close()

    def _report_status(self, value) -> None:
        """Publish one structured MCP activity event to the Agent UI."""
        callback = getattr(self, "status_callback", None)
        if callback is not None:
            callback(value)

    def _gateway_tool_status(self, provider_id: str, tool_name: str) -> None:
        """Resolve LM Studio's actual provider identity to its runtime label."""
        provider_id = str(provider_id or "")
        self._last_gateway_provider = provider_id
        self._last_gateway_tool = str(tool_name or "")
        label = provider_id or "integration"
        for record in self.records:
            if not isinstance(record, dict):
                continue
            if provider_id in (
                record.get("id", ""), record.get("server_label", ""),
                integration_key(record),
            ):
                label = integration_label(record)
                break
        self._report_status({
            "phase": "mcp_call",
            "provider": label,
            "tool": str(tool_name or ""),
        })

    def _stage_status(self, records) -> None:
        """Show the selected integration or an honest multi-provider phase."""
        values = [
            record for record in records
            if isinstance(record, dict)
        ]
        if len(values) == 1:
            self._report_status({
                "phase": "mcp_select",
                "provider": integration_label(values[0]),
                "tool": "",
            })
        elif values:
            self._report_status({
                "phase": "mcp_select",
                "provider": str(len(values)) + " integrations",
                "tool": "",
            })

    def refresh_integrations(self, records=None) -> None:
        """Synchronize self.integrations with current self.records.

        Must be called after scan_integrations() to keep the integration
        identity list in sync with discovered records.
        """
        if records is not None:
            self.records = list(records) if isinstance(records, list) else []
        if not isinstance(self.records, list):
            return
        self.integrations = [integration_key(item) for item in self.records]

    def explicit_selection(self, user_message: str):
        """Return explicitly named records and an ambiguity flag."""
        return explicit_integration_records(self.records, user_message)

    @staticmethod
    def _gateway_item(record) -> dict:
        """Return one LM Studio integration request record."""
        from picoware.system.agent.mcp_lmstudio import LMStudioMCPAdapter

        return LMStudioMCPAdapter.gateway_item(record)

    def selected_records(self, user_message: str) -> list[dict]:
        """Return an exact named record or all enabled execution records."""
        explicit, ambiguous = self.explicit_selection(user_message)
        if explicit:
            return explicit[:MAX_SELECTED_INTEGRATIONS]
        if ambiguous:
            return []
        return [
            record for record in self.records
            if "catalog" not in _record_capabilities(record)
        ][:MAX_SELECTED_INTEGRATIONS]

    def _run_stage(
        self, user_message, integrations, max_calls=MAX_MCP_CALLS,
        optional=False, conversation_context="", continuation_plans=None,
    ):
        return self.lmstudio.run_stage(
            user_message, integrations, max_calls, optional,
            conversation_context, continuation_plans=continuation_plans,
        )

    @staticmethod
    def _stage_record(
        record, role: str, allow_mutation: bool = False, excluded_tools=(),
    ) -> dict:
        """Restrict one stage to discovered tools compatible with its role."""
        staged = dict(record)
        names = _tool_names_for_role(record, role)
        names = _authorized_tool_names(
            record, names, role, allow_mutation
        )
        if (
            role in ("request", "url")
            and any(
                _tool_is_request_scoped_fetch(record, name) for name in names
            )
        ):
            observers = [
                hint.get("name", "")
                for hint in record.get("tool_hints", [])
                if isinstance(hint, dict)
                and _hint_observes_current_resource(hint)
            ]
            observers = _authorized_tool_names(
                record, observers, "evidence", allow_mutation
            )
            for name in observers:
                if name and name not in names:
                    names.append(name)
        configured = record.get("allowed_tools", [])
        if configured and names:
            names = [name for name in names if name in configured]
        record_key = integration_key(record)
        names = [
            name for name in names
            if record_key + "|" + name not in excluded_tools
        ]
        if names or record.get("tool_hints") or configured:
            staged["allowed_tools"] = names
        return staged

    def _run_record_stage(
        self, record, role: str, request: str, evidence: str,
        excluded_tools, peer_records=None, optional: bool = False,
        conversation_context: str = "", allow_mutation: bool = False,
        remaining_calls: int = MAX_MCP_CALLS,
    ):
        """Execute one provider-neutral stage and return bounded provenance."""
        staged = self._stage_record(
            record, role, allow_mutation, excluded_tools
        )
        chosen_plan = _continuation_plan(record, staged, role)
        if role == "url" and chosen_plan:
            instruction = (
                "Use the configured request-scoped URL action on the most "
                "relevant direct URL in the evidence, then use its read-only "
                "current-resource observation tool. Return the observed page "
                "title, final URL, and relevant inline content."
            )
        elif role == "url":
            instruction = (
                "Use one configured URL-reading tool on the most relevant direct "
                "URL in the evidence. Return the page title, final URL, and "
                "relevant page content."
            )
        else:
            instruction = (
                "Use the configured request-scoped action, then its read-only "
                "current-resource observation tool, and return the observed "
                "inline content."
                if chosen_plan else
                "Use one configured tool to gather evidence for the request."
            )
        stage_request = instruction + "\n\nOriginal request:\n" + request
        context_block = ""
        if conversation_context:
            context_block = (
                "\n\nConversation context (reference only):\n"
                "Use this only to resolve follow-up references. Only the "
                "Original request above can authorize creating, changing, "
                "sending, or deleting anything.\n" + conversation_context
            )
        if evidence:
            bounded, _bounded_bytes = _utf8_prefix(
                evidence, MAX_MCP_BROWSER_CONTEXT_CHARS
            )
            stage_request += "\n\nPrior evidence:\n" + bounded
        if not staged.get("allowed_tools"):
            return (
                "", 0,
                "Integration metadata exposes no tool authorized for this "
                "request. Scan integrations again or update the host MCP "
                "tool policy.",
                "",
            )
        peers = (
            peer_records if isinstance(peer_records, list) and peer_records
            else [record]
        )
        items = []
        continuation_plans = []
        for peer in peers[:MAX_SELECTED_INTEGRATIONS]:
            if not isinstance(peer, dict):
                continue
            peer_staged = self._stage_record(
                peer, role, allow_mutation, excluded_tools
            )
            if not peer_staged.get("allowed_tools"):
                continue
            items.append(self._gateway_item(peer_staged))
            plan = _continuation_plan(peer, peer_staged, role)
            if plan:
                continuation_plans.append(plan)
        if not items:
            return "", 0, "No compatible LM Studio integrations.", ""
        self._last_gateway_provider = ""
        self._last_gateway_tool = ""
        remaining_calls = max(
            1, min(int(remaining_calls), MAX_MCP_CALLS)
        )
        max_calls = remaining_calls if continuation_plans else 1
        if optional:
            result, calls, error = self._run_stage(
                stage_request, items, max_calls=max_calls, optional=True,
                conversation_context=conversation_context,
                continuation_plans=continuation_plans,
            )
        else:
            result, calls, error = self._run_stage(
                stage_request, items, max_calls=max_calls,
                conversation_context=conversation_context,
                continuation_plans=continuation_plans,
            )
        provenance = ""
        actual_provider = self._last_gateway_provider
        actual_tool = self._last_gateway_tool
        if actual_tool:
            matching = []
            for peer in peers[:MAX_SELECTED_INTEGRATIONS]:
                if not isinstance(peer, dict):
                    continue
                if actual_provider in (
                    peer.get("id", ""), peer.get("server_label", ""),
                    integration_key(peer),
                ):
                    matching = [peer]
                    break
                if any(
                    isinstance(hint, dict)
                    and hint.get("name") == actual_tool
                    for hint in peer.get("tool_hints", [])
                ):
                    matching.append(peer)
            if len(matching) == 1:
                provenance = integration_key(matching[0]) + "|" + actual_tool
        return result, calls, error, provenance

    def research_result(
        self, user_message: str, conversation_context: str = "",
        allow_mutation=None, require_tool: bool = False,
    ) -> dict:
        """Run the minimum bounded request and optional URL follow-on."""
        if allow_mutation is None:
            allow_mutation = request_authorizes_mutation(user_message)
        else:
            allow_mutation = bool(allow_mutation)
        explicit, ambiguous = self.explicit_selection(user_message)
        if ambiguous:
            return mcp_outcome(
                MCP_OUTCOME_FAILED,
                error="Use the exact label of one enabled integration.",
            )

        records = explicit or [
            record for record in self.records
            if "catalog" not in _record_capabilities(record)
        ]
        blocked = False
        if not allow_mutation:
            blocked = any(
                not _record_has_authorized_tool(record) for record in records
            )
            records = [
                record for record in records
                if _record_has_authorized_tool(record)
            ]
            if explicit and not records:
                return mcp_outcome(
                    MCP_OUTCOME_FAILED, error=(
                        "The selected integration has no tool metadata authorized "
                        "for this request. Scan integrations again or update the "
                        "host MCP tool policy."
                    )
                )
        records = records[:MAX_SELECTED_INTEGRATIONS]
        if not records:
            if explicit or require_tool or blocked:
                return mcp_outcome(
                    MCP_OUTCOME_FAILED, error=(
                        "No enabled integration exposes an authorized tool for "
                        "this request. Scan integrations again or update the "
                        "host MCP tool policy."
                    )
                )
            return mcp_outcome(MCP_OUTCOME_NOT_NEEDED)
        request_message, _request_bytes = _utf8_prefix(
            user_message, MAX_MCP_EVIDENCE_CHARS
        )
        context_message, _context_message_bytes = _utf8_prefix(
            conversation_context, MAX_MCP_BROWSER_CONTEXT_CHARS
        )
        optional_call = not require_tool and not explicit
        self.view_manager.log("[Agent] MCP integration research")
        parts = []
        used_bytes = 0
        call_count = 0
        used_tools = []
        first_error = ""
        self._stage_status(records)
        evidence, calls, error, provenance = self._run_record_stage(
            records[0], "request", request_message, "", used_tools, records,
            optional_call, context_message, allow_mutation,
            remaining_calls=MAX_MCP_CALLS,
        )
        call_count += max(0, int(calls))
        if provenance:
            used_tools.append(provenance)
        if error:
            first_error = error
        if optional_call and calls == 0 and not evidence and not error:
            return mcp_outcome(
                MCP_OUTCOME_NOT_NEEDED, calls=call_count
            )
        if not evidence:
            return mcp_outcome(
                MCP_OUTCOME_FAILED,
                error=error or "MCP integrations returned no evidence.",
                calls=call_count,
            )

        used_bytes = _append_bounded_evidence(
            parts, "# Integration evidence", evidence,
            used_bytes, MAX_MCP_EVIDENCE_CHARS,
        )
        called_record = None
        called_tool = ""
        if provenance and "|" in provenance:
            called_key, called_tool = provenance.rsplit("|", 1)
            for record in records:
                if integration_key(record) == called_key:
                    called_record = record
                    break
        already_opened = (
            _tool_has_capability(called_record, called_tool, "fetch")
            or _tool_is_session_observer(called_record, called_tool)
        )
        if (
            not explicit and not already_opened and _contains_url(evidence)
            and call_count < MAX_MCP_CALLS
        ):
            follow_records = _url_candidate_records(records, used_tools)
            if follow_records:
                evidence_context, _context_bytes = _utf8_prefix(
                    "\n\n".join(parts), MAX_MCP_BROWSER_CONTEXT_CHARS
                )
                self._stage_status(follow_records)
                opened, calls, error, provenance = self._run_record_stage(
                    follow_records[0], "url", request_message,
                    evidence_context, used_tools, follow_records, False,
                    context_message, allow_mutation,
                    remaining_calls=MAX_MCP_CALLS - call_count,
                )
                call_count += max(0, int(calls))
                if provenance and provenance not in used_tools:
                    used_tools.append(provenance)
                if opened:
                    used_bytes = _append_bounded_evidence(
                        parts, "# Opened page evidence", opened,
                        used_bytes, MAX_MCP_EVIDENCE_CHARS,
                    )
                else:
                    first_error = error or "URL integration returned no evidence."
                    used_bytes = _append_bounded_evidence(
                        parts, "# Integration limitation", first_error,
                        used_bytes, MAX_MCP_EVIDENCE_CHARS,
                    )

        result = "\n\n".join(parts).strip()
        self.view_manager.log("[Agent] MCP integration research complete")
        return mcp_outcome(
            MCP_OUTCOME_PARTIAL if first_error else MCP_OUTCOME_COMPLETED,
            evidence=result, error=first_error, calls=call_count,
        )

    def scan_integrations(self):
        """Refresh integration metadata through one LM Studio catalog."""
        updated = list(self.records)
        catalog = [
            record for record in self.records
            if "catalog" in record.get("capabilities", [])
        ]
        if not catalog:
            return [], (
                "No integration catalog configured. Add an MCP Catalog in "
                "Agent Settings, then scan again."
            )
        configured_ids = [
            integration_key(record) for record in self.records
            if "catalog" not in record.get("capabilities", [])
        ]
        evidence, _calls, error = self._run_stage(
            "Call the catalog listing tool exactly once and return complete "
            "plugin or ephemeral MCP records without commentary. Include "
            "bounded tool metadata for these currently configured integration "
            "IDs: " + json.dumps(configured_ids),
            [self._gateway_item(record) for record in catalog],
            max_calls=1,
        )
        if error:
            return updated, error
        if not isinstance(evidence, str) or not evidence.strip():
            return updated, "Integration catalog returned empty evidence."
        discovered = parse_integration_catalog(evidence)
        if not discovered:
            return updated, "Integration catalog returned no integrations."
        updated = merge_integration_records(updated, discovered)
        self.refresh_integrations(updated)
        return updated, ""
