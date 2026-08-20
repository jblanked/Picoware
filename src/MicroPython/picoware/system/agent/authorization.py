"""Deterministic authorization helpers for Agent tool execution."""


MUTATING_BUILTIN_TOOLS = (
    "storage_mkdir",
    "storage_remove",
    "storage_write",
)

_MUTATION_STEMS = (
    "append", "apply", "build", "chang", "creat", "delet", "edit",
    "fix", "implement", "install", "modif", "overwrit", "publish",
    "remov", "renam", "replac", "schedul", "upload", "updat",
    "aktualisier", "aender", "ander", "bearbeit", "bau", "erstell",
    "füg", "fueg", "installier", "kauf", "loesch", "losch", "lösch",
    "mach", "schreib", "send", "speicher", "verschieb", "änder",
)
_MUTATION_WORDS = (
    "add", "added", "adding", "adds", "bought", "buy", "buying", "made",
    "make", "making", "move", "moved", "moves", "moving", "post",
    "posted", "posting", "save", "saved", "saves", "saving", "send", "set",
    "sending", "sent", "sync", "synced", "syncing", "write", "writes",
    "writing", "wrote", "wipe", "wiped", "wiping",
)
_NEGATION_WORDS = (
    "avoid", "dont", "keine", "keinen", "keiner", "nicht", "never",
    "no", "not", "nothing", "ohne", "readonly", "without",
)
_INSTRUCTIONAL_PREFIXES = (
    "can i ", "could i ", "describe how ", "erklaer mir wie ",
    "erkläre mir wie ", "explain how ", "how can i ", "how do i ",
    "how to ", "is it possible to ", "show me how ", "tell me how ",
    "what happens if ", "wie kann ich ", "wie loesche ich ",
    "wie lösche ich ",
)


def _words(value: str) -> list[str]:
    """Return normalized words for a bounded authorization decision."""
    if not isinstance(value, str):
        return []
    text = value.lower().strip()
    for separator in (
        "'", '"', "`", "/", "\\", "-", "_", ".", ",", ";", ":",
        "!", "?", "(", ")", "[", "]", "{", "}", "\n", "\r", "\t",
    ):
        text = text.replace(separator, " ")
    return text.split()


def request_authorizes_mutation(value: str) -> bool:
    """Return whether the current user request explicitly asks for a change."""
    if not isinstance(value, str):
        return False
    normalized = " ".join(_words(value))
    if not normalized or normalized.startswith(_INSTRUCTIONAL_PREFIXES):
        return False
    words = normalized.split()
    for index, word in enumerate(words):
        if (
            word not in _MUTATION_WORDS
            and not any(word.startswith(stem) for stem in _MUTATION_STEMS)
        ):
            continue
        previous = words[max(0, index - 3):index]
        if any(item in _NEGATION_WORDS for item in previous):
            continue
        return True
    return False


def tool_effect(tool: dict) -> str:
    """Return a tool's declared effect: read, write, or unknown."""
    if not isinstance(tool, dict):
        return "unknown"
    annotations = tool.get("annotations", {})
    if not isinstance(annotations, dict):
        annotations = {}
    read_only = tool.get("read_only", annotations.get("readOnlyHint"))
    destructive = tool.get(
        "destructive", annotations.get("destructiveHint")
    )
    if destructive is True or read_only is False:
        return "write"
    if read_only is True and destructive is not True:
        return "read"
    return "unknown"


def builtin_tool_requires_mutation(name: str, arguments=None) -> bool:
    """Return whether one built-in call can change device or remote state."""
    if name in MUTATING_BUILTIN_TOOLS:
        return True
    if name != "network_send_request":
        return False
    arguments = arguments if isinstance(arguments, dict) else {}
    method = str(arguments.get("method", "GET")).upper()
    return method not in ("GET", "HEAD", "OPTIONS")
