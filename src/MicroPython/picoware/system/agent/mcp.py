"""Bounded, provider-neutral MCP integration gateway support."""

import json
from micropython import const


MAX_MCP_CALLS = const(4)
# Compatibility name retained; all enforcement uses UTF-8 bytes, not codepoints.
MAX_MCP_EVIDENCE_CHARS = const(8192)
MAX_MCP_EVENT_BYTES = const(16384)
# Raw SSE is useful only as a bounded diagnostic spool on SD.  It is not a
# heap limit: complete events are parsed incrementally and discarded.
MAX_MCP_STREAM_BYTES = const(262144)
MAX_MCP_STREAM_EVENTS = const(2048)
MAX_BROWSER_MCP_CALLS = const(3)
MAX_DISCOVERED_INTEGRATIONS = const(64)
MAX_SELECTED_INTEGRATIONS = const(8)
MAX_MATCH_TOKEN_CHARS = const(24)
MAX_MATCH_USER_TOKENS = const(16)
MAX_MCP_TOOL_ID_CHARS = const(256)
MAX_MCP_ERROR_CHARS = const(256)
MAX_MCP_RECORD_ID_CHARS = const(256)
MAX_MCP_RECORD_LABEL_CHARS = const(96)
MAX_MCP_RECORD_URL_CHARS = const(512)
MAX_MCP_CAPABILITY_CHARS = const(32)
MAX_MCP_ALLOWED_TOOL_CHARS = const(128)
MAX_MCP_BROWSER_CONTEXT_CHARS = const(3072)

_MATCH_IGNORED = (
    "plugin", "local", "server", "integration", "integrations", "mcp",
    "tool", "tools", "instruction", "selection", "confirmation",
    "clarification", "original", "previous", "request", "topic", "user",
    "search", "research", "browser", "fetch", "time", "current",
    "web", "page", "website", "visit", "open", "read", "navigate",
    "result", "private", "use", "using", "with", "via", "try", "this",
    "that", "the", "a", "an", "my", "please", "and", "or", "instead",
    "rather", "than", "from", "configured",
)
_EXPLICIT_MARKERS = (" use ", " using ", " with ", " via ", " try ")


def _unique_strings(
    value, limit: int = 16, max_chars: int = MAX_MCP_ALLOWED_TOOL_CHARS,
) -> list[str]:
    """Return a bounded list of non-empty unique strings."""
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple)):
        return []
    result = []
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


def _normalized_words(value: str):
    """Return bounded-comparison words without provider-specific aliases."""
    if not isinstance(value, str):
        return "", []
    value = value.lower()
    for separator in ("/", "-", "_", ".", ",", ";", ":", "(", ")", "[", "]"):
        value = value.replace(separator, " ")
    words = value.split()
    return " ".join(words), words


def _record_match_values(record) -> list[str]:
    """Return dynamic display and identity values for one scanned record."""
    values = []
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


def _shared_record_words(records) -> list[str]:
    """Return identity words that cannot distinguish configured records."""
    seen = []
    shared = []
    for record in records:
        record_words = []
        for value in _record_match_values(record):
            _normalized, words = _normalized_words(value)
            for word in words:
                if word not in _MATCH_IGNORED and word not in record_words:
                    record_words.append(word)
        for word in record_words:
            if word in seen:
                if word not in shared:
                    shared.append(word)
            else:
                seen.append(word)
    return shared


def _near_embedded_token(user_token: str, candidate: str) -> int:
    """Return a bounded anchored typo score against a dynamic ID fragment."""
    size = len(user_token)
    if size < 6 or size > MAX_MATCH_TOKEN_CHARS:
        return 99
    if len(candidate) < 6:
        return 99
    if user_token in candidate:
        return 0
    limit = 4 if size >= 8 else 3 if size >= 7 else 1
    anchor = user_token[:4]
    start = candidate.find(anchor)
    if start < 0:
        return 99
    fragment = candidate[start:start + size + 2]
    fragment_size = len(fragment)
    if fragment_size < 4:
        return 99

    shared_pairs = 0
    for user_index in range(size - 1):
        for candidate_index in range(fragment_size - 1):
            if (
                user_token[user_index] == fragment[candidate_index]
                and user_token[user_index + 1]
                == fragment[candidate_index + 1]
            ):
                shared_pairs += 1
                break
    # The four-character anchor contributes three pairs. Requiring one more
    # prevents a distant word with the same prefix from becoming a typo match.
    if shared_pairs < min(4, size - 1):
        return 99

    # The anchor is already exact. Compute one bounded Levenshtein row for the
    # remaining characters in the bounded dynamic-ID fragment.
    candidate_tail_size = fragment_size - 4
    distances = list(range(candidate_tail_size + 1))
    for user_index in range(4, size):
        diagonal = distances[0]
        distances[0] = user_index - 3
        for candidate_index in range(1, candidate_tail_size + 1):
            above = distances[candidate_index]
            substitution = diagonal
            if (
                user_token[user_index]
                != fragment[candidate_index + 3]
            ):
                substitution += 1
            insertion = distances[candidate_index - 1] + 1
            deletion = above + 1
            distances[candidate_index] = min(
                insertion, deletion, substitution
            )
            diagonal = above

    score = distances[candidate_tail_size]
    return score if score <= limit else 99


def _record_exact_match_level(
    record, padded_user_message: str, user_words, shared_words=(),
) -> int:
    """Return 2 for a full identity match, 1 for a unique product word."""
    for value in _record_match_values(record):
        candidate, candidate_words = _normalized_words(value)
        if candidate and (" " + candidate + " ") in padded_user_message:
            return 2
        for candidate_word in candidate_words:
            if (
                candidate_word in _MATCH_IGNORED
                or candidate_word in shared_words
            ):
                continue
            for user_word in user_words:
                if user_word in _MATCH_IGNORED:
                    continue
                if user_word == candidate_word:
                    return 1
                if (
                    len(user_word) >= 6
                    and len(candidate_word) >= len(user_word)
                    and user_word in candidate_word
                ):
                    return 1
    return 0


def _record_token_fuzzy_score(
    record, user_word: str, shared_words=(),
) -> int:
    """Return one user token's best typo score for a dynamic record."""
    best = 99
    for value in _record_match_values(record):
        _candidate, candidate_words = _normalized_words(value)
        for candidate_word in candidate_words:
            if (
                candidate_word in _MATCH_IGNORED
                or candidate_word in shared_words
            ):
                continue
            score = _near_embedded_token(user_word, candidate_word)
            if score < best:
                best = score
    return best


def explicit_integration_records(records, user_message: str):
    """Return explicit dynamic matches and token-local fuzzy ambiguity."""
    selectable = [
        record for record in records
        if "catalog" not in record.get("capabilities", [])
    ]
    shared_words = _shared_record_words(selectable)
    normalized, words = _normalized_words(user_message)
    padded = " " + normalized + " "

    # Only names in explicit integration positions participate when the user
    # says "use/with/via".  Topic words after "to/for/about" are not MCP names.
    explicit_words = []
    collecting = False
    integration_clause = False
    for word in words:
        if word in ("use", "using", "with", "via", "try"):
            collecting = True
            integration_clause = True
            continue
        if collecting and word in ("to", "so", "because"):
            collecting = False
            integration_clause = False
            continue
        if collecting and word in ("for", "on", "about"):
            collecting = False
            continue
        if integration_clause and not collecting and word in ("and", "then"):
            collecting = True
            continue
        if collecting and word in ("and", "or", "then"):
            continue
        if collecting:
            explicit_words.append(word)
    has_explicit_marker = any(marker in padded for marker in _EXPLICIT_MARKERS)
    match_words = explicit_words if has_explicit_marker else words
    match_padded = " " + " ".join(match_words) + " "
    exact_levels = [
        _record_exact_match_level(
            record, match_padded, match_words, shared_words
        )
        for record in selectable
    ]
    best_exact = max(exact_levels) if exact_levels else 0
    matched = [
        selectable[index] for index in range(len(selectable))
        if best_exact and exact_levels[index] == best_exact
    ]

    if not has_explicit_marker:
        return matched[:MAX_SELECTED_INTEGRATIONS], False

    # Resolve each independently named token.  Two different typos may safely
    # select two different scanned records; only a tie for the same token is
    # ambiguous.  This stays provider-neutral because all candidates come from
    # the scanned labels/IDs rather than firmware aliases.
    # Only typo-match words in explicit integration-name positions.  Topic
    # words after "to research", for example, must not silently select another
    # scanned integration that happens to resemble the topic.
    user_words = []
    for word in explicit_words:
        if (
            word not in _MATCH_IGNORED
            and 6 <= len(word) <= MAX_MATCH_TOKEN_CHARS
            and word not in user_words
        ):
            user_words.append(word)
        if len(user_words) >= MAX_MATCH_USER_TOKENS:
            break

    for user_word in user_words:
        best = 99
        winners = []
        for record in selectable:
            score = _record_token_fuzzy_score(
                record, user_word, shared_words
            )
            if score < best:
                best = score
                winners = [record]
            elif score == best and score < 99:
                winners.append(record)
        if best == 99:
            continue
        if len(winners) != 1:
            # A later exact label safely resolves an older ambiguous spelling
            # retained only as context in a clarification carry.
            if any(record in matched for record in winners):
                continue
            return [], True
        if winners[0] not in matched:
            matched.append(winners[0])

    # Preserve configured order even when the names appeared in another order.
    return [
        record for record in selectable if record in matched
    ][:MAX_SELECTED_INTEGRATIONS], False


def _has_unknown_explicit_name(user_message: str) -> bool:
    """Return whether an explicit clause contains a provider name candidate."""
    normalized, words = _normalized_words(user_message)
    if not any(marker in (" " + normalized + " ") for marker in _EXPLICIT_MARKERS):
        return False
    collecting = False
    integration_clause = False
    for word in words:
        if word in ("use", "using", "with", "via", "try"):
            collecting = True
            integration_clause = True
            continue
        if collecting and word in ("to", "so", "because"):
            collecting = False
            integration_clause = False
            continue
        if collecting and word in ("for", "on", "about"):
            collecting = False
            continue
        if integration_clause and not collecting and word in ("and", "then"):
            collecting = True
            continue
        if collecting and word not in _MATCH_IGNORED and len(word) >= 3:
            return True
    return False


def _legacy_capabilities(integration_id: str) -> list[str]:
    """Give old ID-only entries useful migration metadata."""
    lower = integration_id.lower()
    if "catalog" in lower or "list-integrations" in lower:
        return ["catalog"]
    capabilities = []
    if "search" in lower:
        capabilities.append("search")
    if "browser" in lower or "navigate" in lower:
        capabilities.append("browser")
    if "fetch" in lower or "visit" in lower:
        capabilities.append("fetch")
    if "current-time" in lower or "clock" in lower:
        capabilities.append("time")
    return capabilities or ["generic"]


def normalize_integration_record(value):
    """Normalize one saved plugin or ephemeral MCP record."""
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text[:1] in ("[", "{"):
            try:
                parsed = json.loads(text)
            except ValueError:
                parsed = None
            if isinstance(parsed, dict):
                return normalize_integration_record(parsed)
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
        record = {
            "type": (
                "mcp_server" if record_type == "mcp_server"
                else "ephemeral_mcp"
            ),
            "server_label": label,
            "server_url": url,
        }
        if record["type"] == "mcp_server":
            protocol = value.get("protocol", "auto")
            if protocol not in ("auto", "2026-07-28", "legacy"):
                protocol = "auto"
            record["protocol"] = protocol
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
    capabilities = _unique_strings(
        value.get("capabilities", []), 8, MAX_MCP_CAPABILITY_CHARS
    )
    if not capabilities:
        identity = record.get("id", record.get("server_label", ""))
        capabilities = _legacy_capabilities(identity)
    record["capabilities"] = capabilities
    allowed_tools = _unique_strings(
        value.get("allowed_tools", []), 12, MAX_MCP_ALLOWED_TOOL_CHARS
    )
    if allowed_tools:
        record["allowed_tools"] = allowed_tools
    if record.get("type") == "mcp_server":
        raw_headers = value.get("headers", {})
        if isinstance(raw_headers, dict):
            headers = {}
            for key, header_value in raw_headers.items():
                if (
                    isinstance(key, str) and isinstance(header_value, str)
                    and key and _utf8_size(key, 64) <= 64
                    and _utf8_size(header_value, 512) <= 512
                ):
                    headers[key] = header_value
                if len(headers) >= 8:
                    break
            if headers:
                record["headers"] = headers
    return record


def parse_integration_records(value, limit: int = 16) -> list[dict]:
    """Parse JSON records or legacy comma/newline integration settings."""
    maximum = max(1, min(int(limit), MAX_DISCOVERED_INTEGRATIONS))
    if isinstance(value, str):
        text = value.strip()
        parsed = None
        if text[:1] in ("[", "{"):
            try:
                parsed = json.loads(text)
            except ValueError:
                parsed = None
        if isinstance(parsed, dict):
            values = parsed.get("integrations", [parsed])
        elif isinstance(parsed, list):
            values = parsed
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

    records = []
    keys = []
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


def parse_integrations(value: str, limit: int = 16) -> list[str]:
    """Return exact plugin IDs for legacy callers without rewriting them."""
    integrations = []
    for record in parse_integration_records(value, limit):
        if record.get("type") == "plugin":
            integrations.append(record.get("id", ""))
        else:
            integrations.append(integration_key(record))
    return integrations


def serialize_integration_records(records) -> str:
    """Serialize normalized records for persistent settings."""
    return json.dumps(parse_integration_records(records))


def integration_key(record) -> str:
    """Return a stable identity without altering an opaque provider ID."""
    if not isinstance(record, dict):
        record = normalize_integration_record(record)
    if not record:
        return ""
    if record.get("type") in ("ephemeral_mcp", "mcp_server"):
        return (
            "server:" + record.get("server_label", "")
            + "|" + record.get("server_url", "")
        )
    return "plugin:" + record.get("id", "")


def integration_label(record) -> str:
    """Return a compact display label for one integration record."""
    if not isinstance(record, dict):
        record = normalize_integration_record(record)
    if not record:
        return "Invalid integration"
    label = record.get("label", "")
    if label:
        return label
    if record.get("type") in ("ephemeral_mcp", "mcp_server"):
        return record.get("server_label", "MCP server")
    return record.get("id", "Integration")


def merge_integration_records(current, discovered, limit: int = 64) -> list[dict]:
    """Merge discovered records without removing or replacing saved entries."""
    return parse_integration_records(
        parse_integration_records(current, limit)
        + parse_integration_records(discovered, limit),
        limit,
    )


def preserve_catalog_records(previous, updated, limit: int = 16) -> list[dict]:
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


def integration_gateway_url(configured_url: str, model_url: str) -> str:
    """Return the legacy gateway URL for compatibility callers."""
    from picoware.system.agent.mcp_lmstudio import gateway_url

    return gateway_url(configured_url, model_url)


def parse_integration_catalog(
    value, limit: int = MAX_DISCOVERED_INTEGRATIONS,
) -> list[dict]:
    """Extract integration records from a bounded catalog tool result."""
    records = []
    record_keys = []
    maximum = max(1, min(int(limit), MAX_DISCOVERED_INTEGRATIONS))

    def collect(item) -> None:
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


from picoware.system.agent.mcp_lmstudio import (
    IntegrationStreamSink as IntegrationStreamSink,
)


def create_mcp_client(view_manager, http, llm):
    """Create the configured MCP facade without coupling Agent to a provider."""
    from picoware.system.agent.llm import LOCAL_MCP

    if llm.id != LOCAL_MCP:
        return None
    return MCPClient(view_manager, http, llm)


class MCPClient:
    """Provider-neutral facade over configured MCP transport adapters."""

    __slots__ = (
        "view_manager", "http", "llm", "records", "integrations",
        "lmstudio", "direct", "gateway_url", "request_path", "spool_path",
    )

    def __init__(self, view_manager, http, llm):
        from picoware.system.agent.mcp_lmstudio import LMStudioMCPAdapter
        from picoware.system.settings import Settings

        settings = Settings(view_manager.storage)
        self.view_manager = view_manager
        self.http = http
        self.llm = llm
        self.records = parse_integration_records(settings.mcp_integrations)
        self.integrations = [integration_key(item) for item in self.records]
        self.lmstudio = LMStudioMCPAdapter(
            view_manager, http, llm, settings.mcp_gateway_url
        )
        direct_records = [
            record for record in self.records
            if record.get("type") == "mcp_server"
        ]
        self.direct = None
        if direct_records:
            from picoware.system.agent.mcp_standard import StandardMCPAdapter
            self.direct = StandardMCPAdapter(view_manager, http, llm)
        # Compatibility attributes for callers and existing tests.
        self.gateway_url = self.lmstudio.gateway_url
        self.request_path = self.lmstudio.request_path
        self.spool_path = self.lmstudio.spool_path

    @property
    def enabled(self) -> bool:
        """Return whether at least one integration transport is configured."""
        return bool(self.records)

    def cancel(self) -> None:
        """Cancel the currently active adapter operation."""
        self.http.close()

    @staticmethod
    def _request_capabilities(user_message: str) -> list[str]:
        text = " " + user_message.lower() + " "
        capabilities = []
        if any(marker in text for marker in (
            " web", " search", "research", "latest", " news", "price",
            "buy ", "shop", "online", "look up", "current information",
            "aktuell", "suche", "recherch",
        )):
            capabilities.append("search")
        if any(marker in text for marker in (
            "http://", "https://", "www.", "visit ", "open page",
            "open this page", "inspect the result", "read page",
            "read website", "fetch ", "this url", "this link",
        )):
            capabilities.append("fetch")
        if any(marker in text for marker in (
            " browser", "browse ", "navigate ", "open result",
            "open the result", "read result", "inspect result",
        )):
            capabilities.append("browser")
        if any(marker in text for marker in (
            " time ", " date ", " today", " tomorrow", " yesterday",
            " heute", " morgen", " gestern", " uhr", " datum",
        )):
            capabilities.append("time")
        return capabilities

    def explicit_selection(self, user_message: str):
        """Return explicitly named records and an ambiguity flag."""
        selected, ambiguous = explicit_integration_records(
            self.records, user_message
        )
        if not selected and not ambiguous and _has_unknown_explicit_name(
            user_message
        ):
            ambiguous = True
        return selected, ambiguous

    @staticmethod
    def _gateway_item(record) -> dict:
        """Return one legacy adapter request record."""
        from picoware.system.agent.mcp_lmstudio import LMStudioMCPAdapter

        return LMStudioMCPAdapter.gateway_item(record)

    def selected_records(self, user_message: str) -> list[dict]:
        """Return records selected by explicit name or generic capability."""
        explicit, ambiguous = self.explicit_selection(user_message)
        if explicit:
            return explicit[:MAX_SELECTED_INTEGRATIONS]
        if ambiguous:
            return []

        requested = self._request_capabilities(user_message)
        if not requested:
            return []
        selected = []
        for record in self.records:
            capabilities = record.get("capabilities", ["generic"])
            if "catalog" in capabilities:
                continue
            matched = False
            for capability in requested:
                if capability in capabilities:
                    matched = True
                elif capability == "fetch" and "browser" in capabilities:
                    matched = True
            if matched:
                selected.append(record)
            if len(selected) >= MAX_SELECTED_INTEGRATIONS:
                break
        return selected

    def selected_integrations(self, user_message: str) -> list[dict]:
        """Return selected records in their transport request form."""
        selected = []
        for record in self.selected_records(user_message):
            if record.get("type") == "mcp_server":
                selected.append(record)
            else:
                selected.append(self._gateway_item(record))
        return selected

    # Compatibility hooks retained for simulator subclasses and old callers.
    def _write_request(self, user_message, integrations, force_retry=False):
        return self.lmstudio._write_request(
            user_message, integrations, force_retry
        )

    def _run_stage_once(
        self, user_message, integrations, max_calls, force_retry=False,
    ):
        return self.lmstudio.run_stage_once(
            user_message, integrations, max_calls, force_retry
        )

    def _run_stage(self, user_message, integrations, max_calls=MAX_MCP_CALLS):
        return self.lmstudio.run_stage(
            user_message, integrations, max_calls
        )

    def _run_stage_items(
        self, user_message: str, items, call_budget: int,
        force_each: bool = False,
    ):
        """Run a gateway group, guaranteeing one call per explicit item."""
        if not items or call_budget <= 0:
            return "", 0, ""
        groups = [[item] for item in items[:call_budget]] if force_each else [items]
        parts = []
        used = 0
        calls = 0
        success = False
        first_error = ""
        for group in groups:
            available = call_budget - calls
            if available <= 0:
                break
            evidence, count, error = self._run_stage(
                user_message, group, max_calls=(1 if force_each else available)
            )
            calls += count
            if error:
                if not force_each:
                    return "\n\n".join(parts), calls, error
                if not first_error:
                    first_error = error
                used = _append_bounded_evidence(
                    parts, "# Integration limitation", error, used
                )
                continue
            if evidence:
                success = True
            used = _append_bounded_evidence(parts, "", evidence, used)
        if not success and first_error:
            return "", calls, first_error
        return "\n\n".join(parts), calls, ""

    def _research_legacy(
        self, user_message: str, records,
        evidence_limit: int = MAX_MCP_EVIDENCE_CHARS,
        force_each: bool = False,
    ):
        """Run legacy gateway records through the compatibility adapter."""
        if not records:
            return "", ""
        search = []
        browser = []
        other = []
        for record in records:
            capabilities = record.get("capabilities", ["generic"])
            item = self._gateway_item(record)
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
        success = False
        first_error = ""
        search_evidence = ""
        if search:
            search_budget = min(len(search), MAX_MCP_CALLS) if force_each else 1
            search_evidence, count, error = self._run_stage_items(
                user_message, search, search_budget, force_each
            )
            calls += count
            if error:
                first_error = error
                used = _append_bounded_evidence(
                    parts, "# Search limitation", error,
                    used, evidence_limit,
                )
            if search_evidence:
                success = True
                if browser or other:
                    search_evidence, _search_bytes = _utf8_prefix(
                        search_evidence,
                        min(MAX_MCP_BROWSER_CONTEXT_CHARS, evidence_limit),
                    )
                used = _append_bounded_evidence(
                    parts, "# Search evidence", search_evidence,
                    used, evidence_limit,
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
            browser_budget = min(
                MAX_BROWSER_MCP_CALLS, MAX_MCP_CALLS - calls
            )
            browser_evidence, count, error = self._run_stage_items(
                browser_request, browser, browser_budget, force_each
            )
            calls += count
            if error:
                if not first_error:
                    first_error = error
                if parts:
                    used = _append_bounded_evidence(
                        parts, "# Browser limitation", error,
                        used, evidence_limit,
                    )
                else:
                    return "", error
            elif browser_evidence:
                success = True
                used = _append_bounded_evidence(
                    parts, "# Browser evidence", browser_evidence,
                    used, evidence_limit,
                )
        if other and calls < MAX_MCP_CALLS:
            other_budget = min(2, MAX_MCP_CALLS - calls)
            other_evidence, count, error = self._run_stage_items(
                user_message, other, other_budget, force_each
            )
            calls += count
            if error:
                if not first_error:
                    first_error = error
                used = _append_bounded_evidence(
                    parts, "# Integration limitation", error,
                    used, evidence_limit,
                )
            elif other_evidence:
                success = True
                used = _append_bounded_evidence(
                    parts, "# Additional evidence", other_evidence,
                    used, evidence_limit,
                )
        evidence = "\n\n".join(parts).strip()
        if not success:
            return "", first_error or "MCP integrations returned no evidence."
        return evidence, ""

    def research(self, user_message: str):
        """Run selected records through their configured transport adapters."""
        records = self.selected_records(user_message)
        if not records:
            return "", ""
        request_message, _request_bytes = _utf8_prefix(
            user_message, MAX_MCP_EVIDENCE_CHARS
        )
        self.view_manager.log("[Agent] MCP integration research")
        legacy = [
            record for record in records
            if record.get("type") != "mcp_server"
        ]
        direct = [
            record for record in records
            if record.get("type") == "mcp_server"
        ]
        explicit, _ambiguous = self.explicit_selection(user_message)
        force_each = bool(explicit)
        parts = []
        used = 0
        success = False
        direct_errors = []
        legacy_limit = (
            MAX_MCP_EVIDENCE_CHARS - 2048 if direct
            else MAX_MCP_EVIDENCE_CHARS
        )
        evidence, error = self._research_legacy(
            request_message, legacy, legacy_limit, force_each
        )
        if error:
            if not direct:
                return "", error
            direct_errors.append(error)
            used = _append_bounded_evidence(
                parts, "# Integration limitation", error,
                used, MAX_MCP_EVIDENCE_CHARS,
            )
        if evidence:
            success = True
            used = _append_bounded_evidence(
                parts, "", evidence, used, MAX_MCP_EVIDENCE_CHARS
            )
        if direct and self.direct is not None:
            direct_groups = [[record] for record in direct] if force_each else [direct]
            for group in direct_groups[:MAX_MCP_CALLS]:
                evidence, error = self.direct.research(request_message, group)
                if error:
                    direct_errors.append(error)
                    used = _append_bounded_evidence(
                        parts, "# Direct MCP limitation", error,
                        used, MAX_MCP_EVIDENCE_CHARS,
                    )
                    continue
                if evidence:
                    success = True
                used = _append_bounded_evidence(
                    parts, "", evidence, used, MAX_MCP_EVIDENCE_CHARS
                )
        result = "\n\n".join(parts).strip()
        if not success:
            return "", (
                direct_errors[0] if direct_errors
                else "MCP integrations returned no evidence."
            )
        self.view_manager.log("[Agent] MCP integration research complete")
        return result, ""

    def scan_integrations(self):
        """Scan legacy catalogs and direct MCP server tool catalogs."""
        legacy = [
            record for record in self.records
            if record.get("type") != "mcp_server"
        ]
        direct = [
            record for record in self.records
            if record.get("type") == "mcp_server"
        ]
        updated = list(self.records)
        catalog = [
            record for record in legacy
            if "catalog" in record.get("capabilities", [])
        ]
        if catalog:
            evidence, _calls, error = self._run_stage(
                "Call the catalog listing tool exactly once and return complete "
                "plugin or ephemeral MCP records without commentary.",
                [self._gateway_item(record) for record in catalog],
                max_calls=1,
            )
            if error:
                return updated, error
            discovered = parse_integration_catalog(evidence)
            if not discovered:
                return updated, "Integration catalog returned no integrations."
            updated = merge_integration_records(updated, discovered)
        if direct and self.direct is not None:
            scanned, error = self.direct.scan_integrations(direct)
            if error:
                return updated, error
            updated = merge_integration_records(updated, scanned)
            # Replace older copies so refreshed tool metadata wins.
            refreshed = {integration_key(item): item for item in scanned}
            updated = [
                refreshed.get(integration_key(item), item) for item in updated
            ]
        if not catalog and not direct:
            return [], (
                "No integration catalog configured. Add an MCP Catalog or "
                "direct MCP server in Agent Settings, then scan again."
            )
        return updated, ""
