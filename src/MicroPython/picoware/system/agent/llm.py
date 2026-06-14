from micropython import const

OPENAI = const(0)
DEEPSEEK = const(1)

class LLM:
    """LLM provider config with endpoint URL, model name, and API key."""
    __slots__ = ["provider_id", "id", "label", "model", "url", "api_key"]

    def __init__(self, storage, provider_id: int = DEEPSEEK):
        self.provider_id = provider_id

        self.api_key = ""
        self.id = ""
        self.label = ""
        self.model = ""
        self.url = ""

        from picoware.system.settings import Settings

        settings = Settings(storage)

        o_len = len(settings.openai_api_key)
        d_len = len(settings.deepseek_api_key)


        if o_len < 3 and d_len < 3:
            raise ValueError("No API key set in settings for OpenAI or DeepSeek.")
        
        try_other = False

        if self.provider_id == OPENAI:
            if o_len < 3:
                try_other = True
            else:
                self.id = "openai"
                self.label = "OpenAI"
                self.model = "gpt-5.4-mini"
                self.url = "https://api.openai.com/v1/chat/completions"
            self.api_key = settings.openai_api_key
        elif self.provider_id == DEEPSEEK:
            if d_len < 3:
                try_other = True
            else:
                self.id = "deepseek"
                self.label = "DeepSeek"
                self.model = "deepseek-v4-flash"
                self.url = "https://api.deepseek.com/chat/completions"
                self.api_key = settings.deepseek_api_key
        
        if try_other:
            if self.provider_id == OPENAI and d_len >= 3:
                self.provider_id = DEEPSEEK
                self.id = "deepseek"
                self.label = "DeepSeek"
                self.model = "deepseek-v4-flash"
                self.url = "https://api.deepseek.com/chat/completions"
                self.api_key = settings.deepseek_api_key
            elif self.provider_id == DEEPSEEK and o_len >= 3:
                self.provider_id = OPENAI
                self.id = "openai"
                self.label = "OpenAI"
                self.model = "gpt-5.4-mini"
                self.url = "https://api.openai.com/v1/chat/completions"
                self.api_key = settings.openai_api_key
            else:
                raise ValueError("No valid API key found for the selected provider.")