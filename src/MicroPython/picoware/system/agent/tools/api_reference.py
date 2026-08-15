"""On-demand access to the large App Creator API reference."""
from picoware.system.agent.tools.tool import Tool, Parameters, Property

MAX_REFERENCE_RESULT_BYTES = 12000


def _sections():
    from picoware.system.agent.context import app_creator

    raw = app_creator.CONTEXT
    marker = b"\n#### "
    start = raw.find(marker)
    while start >= 0:
        title_start = start + len(marker)
        title_end = raw.find(b"\n", title_start)
        if title_end < 0:
            break
        next_start = raw.find(marker, title_end)
        end = len(raw) if next_start < 0 else next_start
        yield raw[title_start:title_end].decode("utf-8"), title_end + 1, end, raw
        start = next_start


def _query_tokens(query: str):
    tokens = []
    for token in query.lower().replace("_", " ").replace("-", " ").split():
        if len(token) >= 3 and token not in tokens:
            tokens.append(token)
    return tokens[:8]


def picoware_api_search(_view_manager, query, limit: int = 6):
    """Return the best matching App Creator API section names."""
    if not isinstance(query, str) or not query.strip():
        return {"ok": False, "error": "invalid_query", "message": "query is empty"}
    if not isinstance(limit, int):
        limit = 6
    limit = max(1, min(limit, 10))
    tokens = _query_tokens(query)
    matches = []
    for title, start, end, raw in _sections():
        title_lower = title.lower()
        body = raw[start:end].lower()
        score = 0
        for token in tokens:
            encoded = token.encode("utf-8")
            if token in title_lower:
                score += 10
            if body.find(encoded) >= 0:
                score += 1
        if score:
            matches.append((score, title))
    matches.sort(key=lambda item: (-item[0], item[1]))
    return {
        "ok": True,
        "query": query,
        "sections": [title for _score, title in matches[:limit]],
    }


def picoware_api_read(_view_manager, section, max_bytes: int = MAX_REFERENCE_RESULT_BYTES):
    """Return one named App Creator API section with a strict size bound."""
    if not isinstance(section, str) or not section.strip():
        return {"ok": False, "error": "invalid_section", "message": "section is empty"}
    if not isinstance(max_bytes, int):
        max_bytes = MAX_REFERENCE_RESULT_BYTES
    max_bytes = max(512, min(max_bytes, MAX_REFERENCE_RESULT_BYTES))
    requested = section.strip().lower()
    fallback = None
    for title, start, end, raw in _sections():
        title_lower = title.lower()
        if title_lower == requested:
            fallback = (title, start, end, raw)
            break
        if requested in title_lower and fallback is None:
            fallback = (title, start, end, raw)
    if fallback is None:
        return {
            "ok": False,
            "error": "section_not_found",
            "message": "call picoware_api_search to find a section name",
        }
    title, start, end, raw = fallback
    truncated = end - start > max_bytes
    content = raw[start : min(end, start + max_bytes)].decode("utf-8")
    return {
        "ok": True,
        "section": title,
        "content": content,
        "truncated": truncated,
    }


def picoware_app_validate(view_manager, file_path):
    """Validate syntax and the required Picoware SD-app module contract."""
    from picoware.system.agent.tools.storage import _normalize_path

    try:
        path = _normalize_path(file_path)
        storage = view_manager.storage
        if not storage.exists(path) or storage.is_directory(path):
            return {
                "ok": False,
                "path": path,
                "error": "not_found",
                "message": "app source does not exist",
            }
        size = storage.size(path)
        if size > 65536:
            return {
                "ok": False,
                "path": path,
                "error": "too_large",
                "message": "app source exceeds 65536 bytes",
                "size": size,
            }
        source = storage.read(path, "r")
        if not isinstance(source, str) or not source:
            return {
                "ok": False,
                "path": path,
                "error": "read_failed",
                "message": "could not read app source as UTF-8",
            }
        issues = []
        for callback in ("def start(view_manager", "def run(view_manager", "def stop(view_manager"):
            if callback not in source:
                issues.append("missing " + callback.split("(", 1)[0])
        if "return True" not in source:
            issues.append("start must return True")
        if "view_manager.back()" not in source:
            issues.append("run must provide view_manager.back() exit")
        forbidden = (
            "from picoware import",
            "ViewManager.add",
            "view_manager.add(",
            "view = View(",
        )
        for pattern in forbidden:
            if pattern in source:
                issues.append("app module must not register views: " + pattern)
        syntax_error = ""
        try:
            compile(source, path, "exec")
        except Exception as exc:
            syntax_error = str(exc)
            issues.append("syntax error: " + syntax_error)
        return {
            "ok": not issues,
            "path": path,
            "size": size,
            "syntax_ok": not syntax_error,
            "contract_ok": not issues,
            "issues": issues,
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": "validation_failed",
            "message": str(exc),
        }


TOOL_PICOWARE_API_SEARCH = Tool(
    "picoware_api_search",
    "Search Picoware's App Creator API reference for relevant section names.",
    Parameters([
        Property("query", "string", "API, module, widget, or feature to find.", True),
        Property("limit", "integer", "Maximum section names to return, from 1 to 10."),
    ]),
)

TOOL_PICOWARE_API_READ = Tool(
    "picoware_api_read",
    "Read one exact section returned by picoware_api_search.",
    Parameters([
        Property("section", "string", "Section name returned by picoware_api_search.", True),
        Property("max_bytes", "integer", "Maximum bytes to return, up to 12000."),
    ]),
)

TOOL_PICOWARE_APP_VALIDATE = Tool(
    "picoware_app_validate",
    "Compile-check a saved Picoware app and validate its lifecycle module contract.",
    Parameters([
        Property("file_path", "string", "Saved Picoware .py app path on the SD card.", True),
    ]),
)
