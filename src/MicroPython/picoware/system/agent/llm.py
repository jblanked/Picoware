from micropython import const

OPENAI = const(0)
DEEPSEEK = const(1)
ANTHROPIC = const(2)
GEMINI = const(3)
LOCAL = const(4)

class LLM:
    """LLM config"""
    __slots__ = ["_api_key", "_current_model", "_id", "_name", "_url", "_models", "_headers"]
    def __init__(self, storage, llm_id: int, model: str = None):
        self._api_key = ""
        self._current_model = model
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
    def name(self) -> str:
        """Return the name of the LLM."""
        return self._name
    
    @property
    def url(self) -> str:
        """Return the URL of the LLM."""
        return self._url

    def __set(self, storage):
        """Set model name, url, and headers based on model_id."""
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
            self._url = "https://api.anthropic.com/v1/messages"
            self._models = ["claude-sonnet-5", "claude-sonnet-4-6", "claude-opus-4-8", "claude-opus-5", "claude-fable-5", "claude-haiku-4-5-20251001"]
            self._api_key = settings.anthropic_api_key
        elif self._id == GEMINI:
            self._name = "Gemini"
            self._url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
            self._models = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-3.1-pro-preview"]
            self._api_key = settings.gemini_api_key
        elif self._id == LOCAL:
            self._name = "Local"
            self._url = "http://127.0.0.1:8080/v1/chat/completions"
            self._models = ["local-model"]
        
        if self._id == ANTHROPIC:
            self._headers["x-api-key"] = self._api_key
            self._headers["anthropic-version"] = "2023-06-01"
        elif self._id != LOCAL:
            self._headers["Authorization"] = f"Bearer {self._api_key}"
        
        if self._current_model is None:
            self._current_model = self._models[0]
        else:
            if self._current_model not in self._models:
                self._models.append(self._current_model)
        