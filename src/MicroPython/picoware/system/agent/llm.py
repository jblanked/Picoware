"""LLM - Multi-provider language model interface."""

from micropython import const

OPENAI = const(0)
DEEPSEEK = const(1)
ANTHROPIC = const(2)
GEMINI = const(3)
LOCAL = const(4)
XAI = const(5)
JBLANKED = const(6)
CUSTOM = const(7)

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
            elif self._id in (LOCAL, JBLANKED):
                _payload["think"] = True
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
            elif self._id in (LOCAL, JBLANKED):
                _payload["think"] = False
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
        return [OPENAI, DEEPSEEK, ANTHROPIC, GEMINI, LOCAL, XAI, JBLANKED, CUSTOM]

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
        if provider_id == XAI:
            return "xAI"
        if provider_id == JBLANKED:
            return "JBlanked"
        if provider_id == CUSTOM:
            return "Custom"
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
            self._models = ["ornith-1.5:9b", "ornith-1.5:35b", "qwen3.8:27b", "qwen3.5:9b","qwen3.5:4b", "llama3.2:3b", "llama3.2:1b"]
            self._api_key = settings.local_api_key 
        elif self._id == XAI:
            self._name = "xAI"
            self._url = "https://api.x.ai/v1"
            self._models = ["grok-4.5", "grok-4.3", "grok-build-0.1", "grok-4.20", "grok-4.20-non-reasoning"]
            self._api_key = settings.xai_api_key
        elif self._id == JBLANKED:
            self._name = "JBlanked"
            self._url = "https://www.jblanked.com/ai/v1/chat/completions"
            self._models = ["none"]
            self._api_key = settings.jblanked_api_key
        elif self._id == CUSTOM:
            self._name = "Custom"
            _path = "picoware/agent/custom.json"
            if not storage.exists(_path):
                raise Exception(f"Custom configuration file not found at {_path}")
            _config = storage.deserialize(_path)
            self._url = _config.get("url", "")
            self._models = _config.get("models", ["none"])
            self._api_key = _config.get("api_key", "")
        
        self._headers["Authorization"] = f"Bearer {self._api_key}"
        
        if self._current_model is None:
            self._current_model = self._models[0]
        else:
            if self._current_model not in self._models:
                self._models.append(self._current_model)
        