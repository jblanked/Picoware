"""LLM - Multi-provider language model interface."""

from micropython import const

OPENAI = const(0)
DEEPSEEK = const(1)
ANTHROPIC = const(2)
GEMINI = const(3)
LOCAL = const(4)
XAI = const(5)
# Backward-compatible provider ID for existing Agent settings. MCP execution
# is implemented by the Agent integration layer, not by this LLM transport.
LOCAL_MCP = const(6)

MAX_LOCAL_MODELS = const(32)
LEGACY_OLLAMA_MODEL_IDS = (
    "qwen3.5:9b", "qwen3.5:4b", "qwen3.5:0.8b", "qwen3.5:2b",
    "llama3.2:3b", "llama3.2:1b",
)


def local_model_catalog_url(chat_url: str) -> str:
    """Return the llama.cpp-compatible model-list URL for a chat endpoint."""
    url = (chat_url or "").strip().rstrip("/")
    for suffix in ("/v1/chat/completions",):
        if url.endswith(suffix):
            return url[:-len(suffix)] + "/v1/models"
    if url.endswith("/v1"):
        return url + "/models"
    return url + "/v1/models"


def parse_local_models(value, limit: int = MAX_LOCAL_MODELS) -> list[str]:
    """Extract bounded, unique model IDs from an OpenAI-compatible catalog."""
    if not isinstance(value, dict):
        return []
    entries = value.get("data", [])
    if not isinstance(entries, list):
        return []
    models = []
    maximum = max(1, min(int(limit), MAX_LOCAL_MODELS))
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        model_id = entry.get("id", "")
        if isinstance(model_id, str):
            model_id = model_id.strip()
        if model_id and model_id not in models:
            models.append(model_id)
        if len(models) >= maximum:
            break
    return models


def is_legacy_ollama_model(model: str) -> bool:
    """Return whether a model came from the removed Ollama-style defaults."""
    return model in LEGACY_OLLAMA_MODEL_IDS

class LLM:
    """LLM config"""
    __slots__ = ["_api_key", "_current_model", "_id", "_name", "_url", "_models", "_headers", "_thinking"]
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
            return "Local + MCP"
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
        elif self._id in (LOCAL, LOCAL_MCP):
            self._name = "Local + MCP" if self._id == LOCAL_MCP else "Local"
            self._url = settings.local_url
            # Local model identifiers are server-defined. Keep only the exact
            # saved value here; the Agent settings view discovers /v1/models.
            self._models = []
            self._api_key = settings.local_api_key
        elif self._id == XAI:
            self._name = "xAI"
            self._url = "https://api.x.ai/v1"
            self._models = ["grok-4.5", "grok-4.3", "grok-build-0.1", "grok-4.20", "grok-4.20-non-reasoning"]
            self._api_key = settings.xai_api_key
        
        if self._id not in (LOCAL, LOCAL_MCP) or self._api_key:
            self._headers["Authorization"] = f"Bearer {self._api_key}"
        
        if self._current_model is None:
            self._current_model = self._models[0] if self._models else ""
        elif self._current_model and self._current_model not in self._models:
            self._models.append(self._current_model)
