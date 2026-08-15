"""LLM - Multi-provider language model interface."""

from micropython import const

OPENAI = const(0)
DEEPSEEK = const(1)
ANTHROPIC = const(2)
GEMINI = const(3)
LOCAL = const(4)
XAI = const(5)
LOCAL_MCP = const(6)


def native_mcp_url(local_url: str) -> str:
    """Return LM Studio's native chat endpoint for a configured local URL.

    Args:
        local_url (str): Local provider URL or server base URL.

    Returns:
        str: URL ending in /api/v1/chat.
    """
    url = (local_url or "").rstrip("/")
    for suffix in ("/api/v1/chat", "/v1/chat/completions", "/v1/responses"):
        if url.endswith(suffix):
            return url[: -len(suffix)] + "/api/v1/chat"
    if url.endswith("/v1"):
        url = url[:-3]
    return url + "/api/v1/chat"


def responses_url(local_url: str) -> str:
    """Return LM Studio's OpenAI-compatible Responses endpoint."""
    url = (local_url or "").rstrip("/")
    for suffix in ("/api/v1/chat", "/v1/chat/completions", "/v1/responses"):
        if url.endswith(suffix):
            return url[: -len(suffix)] + "/v1/responses"
    if url.endswith("/v1"):
        return url + "/responses"
    return url + "/v1/responses"


def parse_mcp_integrations(value: str, limit: int = 16) -> list[str]:
    """Normalize comma-separated LM Studio integration IDs.

    Args:
        value (str): Comma- or newline-separated server IDs.
        limit (int): Maximum number of integrations to expose. Defaults to 16.

    Returns:
        list[str]: Unique LM Studio integration IDs.

    Notes:
        Plain values remain backward-compatible MCP labels and receive the
        ``mcp/`` prefix. Hub plugins use an explicit ``plugin:owner/name``
        spelling because MCP labels may also contain slashes.
    """
    if not isinstance(value, str):
        return []

    integrations = []
    for raw in value.replace("\n", ",").split(","):
        server_id = raw.strip()
        if not server_id:
            continue
        if server_id.startswith("plugin:"):
            server_id = server_id[7:].strip()
            if not server_id:
                continue
        else:
            if not server_id.startswith("mcp/"):
                server_id = "mcp/" + server_id
            # LM Studio canonicalizes MCP labels containing slashes when it
            # generates the mcpBridge artifact (for example,
            # microsoft/markitdown -> mcp/microsoftmarkitdown).
            server_id = "mcp/" + server_id[4:].replace("/", "")
        if server_id not in integrations:
            integrations.append(server_id)
        if len(integrations) >= limit:
            break
    return integrations

class LLM:
    """LLM config"""
    __slots__ = ["_api_key", "_current_model", "_id", "_name", "_url", "_models", "_headers", "_thinking", "_mcp_integrations"]
    def __init__(self, storage, llm_id: int, model: str = None, thinking: str = "none"):
        """Initialize the LLM config for the given provider ID.

        Args:
            storage (Storage): The storage interface for settings.
            llm_id (int): The provider ID constant.
            model (str): The model name to use. Defaults to None.
            thinking (str): The thinking level. Defaults to "none".
        """
        self._api_key = ""
        self._current_model = model
        if thinking not in ("none", "low", "medium", "high", "max") or thinking is None:
            self._thinking = "none"
        else:
            self._thinking = thinking
        self._id = llm_id
        self._name = ""
        self._url = ""
        self._models = []
        self._headers = {}
        self._mcp_integrations = []
        self.__set(storage)
    
    @property
    def api_key(self) -> str:
        """Return the current API key."""
        return self._api_key
    
    @property
    def headers(self) -> dict:
        """Return the headers for the LLM."""
        return self._headers
    
    @property
    def id(self) -> int:
        """Return the ID of the LLM."""
        return self._id
    
    @property
    def model(self) -> str:
        """Return the current model."""
        return self._current_model
    
    @property
    def models(self) -> list:
        """Return the list of models for the LLM."""
        return self._models

    @property
    def mcp_integrations(self) -> list[str]:
        """Return configured LM Studio MCP integration IDs."""
        return self._mcp_integrations

    @property
    def native_mcp(self) -> bool:
        """Return whether this provider uses LM Studio's native MCP API."""
        return self._id == LOCAL_MCP

    @property
    def payload(self) -> dict:
        """Return a payload for the chat agent based on the provider."""
        _payload = {
            "model": self._current_model,
            "stream": False,
        }
        _payload.update(self.thinking_payload)

        return _payload

    @property
    def thinking(self) -> str:
        """Return the current thinking setting for the LLM."""
        return self._thinking

    @property
    def thinking_payload(self) -> dict:
        """Return the thinking-related payload for the LLM."""
        _payload = {}
        if self._thinking != "none":
            if self._id == DEEPSEEK:
                _payload["thinking"] = {"type": "enabled"}
                _payload["reasoning_effort"] = self._thinking
            elif self._id == LOCAL:
                _payload["think"] = True
            elif self._id == LOCAL_MCP:
                _payload["reasoning"] = "on"
            elif self._id in (OPENAI, GEMINI):
                _payload["reasoning_effort"] = self._thinking
            elif self._id == ANTHROPIC:
                _payload["thinking"] = {
                    "type": "enabled"
                }
            elif self._id == GEMINI:
                _payload["generation_config"] = {
                    "thinking_level": self._thinking
                }
        else:
            if self._id == DEEPSEEK:
                _payload["thinking"] = {"type": "disabled"}
            elif self._id == LOCAL:
                _payload["think"] = False
            elif self._id == LOCAL_MCP:
                _payload["reasoning"] = "off"
            elif self._id in (OPENAI, GEMINI):
                _payload["reasoning_effort"] = self._thinking
            elif self._id == ANTHROPIC:
                _payload["thinking"] = {
                    "type": "disabled"
                }
        return _payload
    
    @property
    def name(self) -> str:
        """Return the name of the LLM."""
        return self._name
    
    @property
    def url(self) -> str:
        """Return the URL of the LLM."""
        return self._url

    @staticmethod
    def providers() -> list:
        """Return a list of available LLM providers."""
        return [OPENAI, DEEPSEEK, ANTHROPIC, GEMINI, LOCAL, LOCAL_MCP, XAI]

    @staticmethod
    def provider_name(provider_id: int) -> str:
        """Return the name of the LLM provider given its ID.

        Args:
            provider_id (int): The provider ID constant.

        Returns:
            str: The provider name, or "Unknown" if not recognized.
        """
        if provider_id == OPENAI:
            return "OpenAI"
        if provider_id == DEEPSEEK:
            return "DeepSeek"
        if provider_id == ANTHROPIC:
            return "Anthropic"
        if provider_id == GEMINI:
            return "Gemini"
        if provider_id == LOCAL:
            return "Local"
        if provider_id == LOCAL_MCP:
            return "LM Studio MCP"
        if provider_id == XAI:
            return "xAI"
        return "Unknown"

    def __set(self, storage):
        """Set model name, url, and headers based on the provider ID.

        Args:
            storage (Storage): The storage interface for settings.
        """
        from picoware.system.settings import Settings

        settings = Settings(storage)
        self._headers = {"Content-Type": "application/json"}

        if self._id == OPENAI:
            self._name = "OpenAI"
            self._url = "https://api.openai.com/v1/chat/completions"
            self._models = ["gpt-5.4-mini", "gpt-5.4-nano", "gpt-5.4", "gpt-5.5", "gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"]
            self._api_key = settings.openai_api_key
        elif self._id == DEEPSEEK:
            self._name = "DeepSeek"
            self._url = "https://api.deepseek.com/chat/completions"
            self._models = ["deepseek-v4-flash", "deepseek-v4-pro"]
            self._api_key = settings.deepseek_api_key
        elif self._id == ANTHROPIC:
            self._name = "Anthropic"
            self._url = "https://api.anthropic.com/v1/chat/completions"
            self._models = ["claude-sonnet-5", "claude-sonnet-4-6", "claude-opus-4-8", "claude-opus-5", "claude-fable-5", "claude-haiku-4-5-20251001"]
            self._api_key = settings.anthropic_api_key
        elif self._id == GEMINI:
            self._name = "Gemini"
            self._url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
            self._models = ["gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-3.1-pro-preview"]
            self._api_key = settings.gemini_api_key
        elif self._id == LOCAL:
            self._name = "Local"
            self._url = settings.local_url
            self._models = ["qwen3.5:9b", "qwen3.5:4b", "qwen3.5:0.8b", "qwen3.5:2b", "llama3.2:3b", "llama3.2:1b"]
            self._api_key = settings.local_api_key
        elif self._id == LOCAL_MCP:
            self._name = "LM Studio MCP"
            self._url = responses_url(settings.local_url)
            self._models = ["qwen/qwen3.5-9b", "qwen/qwen3.5-4b", "qwen/qwen3.5-2b", "qwen/qwen3.5-0.8b"]
            self._api_key = settings.local_api_key
            self._mcp_integrations = parse_mcp_integrations(settings.local_mcp_servers)
        elif self._id == XAI:
            self._name = "xAI"
            self._url = "https://api.x.ai/v1"
            self._models = ["grok-4.5", "grok-4.3", "grok-build-0.1", "grok-4.20", "grok-4.20-non-reasoning"]
            self._api_key = settings.xai_api_key
        
        if self._id not in (LOCAL, LOCAL_MCP) or self._api_key:
            self._headers["Authorization"] = f"Bearer {self._api_key}"
        
        if self._current_model is None:
            self._current_model = self._models[0]
        else:
            if self._current_model not in self._models:
                self._models.append(self._current_model)
