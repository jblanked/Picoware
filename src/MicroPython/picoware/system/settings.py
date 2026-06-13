import json

class Settings:
    """Settings management for Picoware."""

    __slots__ = ["_storage", "_path", "_settings"]

    def __init__(self, storage):
        from picoware.system.buttons import BUTTON_BACK
        self._storage = storage
        self._path = "picoware/settings/picoware.json" 
        self._settings = {
            "dark_mode": True,
            "deepseek_api_key": "",
            "debug": False,
            "exit_button": BUTTON_BACK,
            "gmt_offset": 0,
            "lvgl_mode": False,
            "onscreen_keyboard": False,
            "openai_api_key": "",
            "server_username": "",
            "server_password": "",
            "theme_color": 0x001F,
            "wifi_ssid": "",
            "wifi_password": "",
        }
        if not self._storage.exists(self._path):
            self._settings = {
                "dark_mode":  bool(self.__fetch_setting("picoware/settings/dark_mode.json", "dark_mode", True)),
                "debug": bool(self.__fetch_setting("picoware/settings/debug.json", "debug", False)),
                "deepseek_api_key": "",
                "exit_button": int(self.__fetch_setting("picoware/settings/exit_button.json", "exit_button", BUTTON_BACK)),
                "gmt_offset": int(self.__fetch_setting("picoware/settings/gmt_offset.json", "gmt_offset", 0)),
                "lvgl_mode": bool(self.__fetch_setting("picoware/settings/lvgl_mode.json", "lvgl_mode", False)),
                "onscreen_keyboard": bool(self.__fetch_setting("picoware/settings/onscreen_keyboard.json", "onscreen_keyboard", False)),
                "openai_api_key": "",
                "server_username": self.__fetch_setting("picoware/settings/server_username.json", "username", ""),
                "server_password": self.__fetch_setting("picoware/settings/server_password.json", "password", ""),
                "theme_color": int(self.__fetch_setting("picoware/settings/theme_color.json", "theme_color", 0x001F)),
                "wifi_ssid": self.__fetch_setting("picoware/wifi/ssid.json", "ssid", ""),
                "wifi_password": self.__fetch_setting("picoware/wifi/password.json", "password", ""),
            }
            self.__save_settings()
        else:
            _data = self._storage.read(self._path)
            if _data is not None:
                try:
                    obj = json.loads(_data)
                    self._settings.update(obj)
                except Exception:
                    pass
    
    @property
    def dark_mode(self) -> bool:
        """Return True if dark mode is enabled, False otherwise."""
        return bool(self._settings.get("dark_mode", True))
    
    @dark_mode.setter
    def dark_mode(self, value: bool):
        """Set dark mode."""
        self._settings["dark_mode"] = value
        self.__save_settings()

    @property
    def debug(self) -> bool:
        """Return True if debug mode is enabled, False otherwise."""
        return bool(self._settings.get("debug", False))
    
    @debug.setter
    def debug(self, value: bool):
        """Set debug mode."""
        self._settings["debug"] = value
        self.__save_settings()
    
    @property
    def deepseek_api_key(self) -> str:
        """Return the current DeepSeek API key."""
        return self._settings.get("deepseek_api_key", "")
    
    @deepseek_api_key.setter
    def deepseek_api_key(self, value: str):
        """Set the DeepSeek API key."""
        self._settings["deepseek_api_key"] = value
        self.__save_settings()

    @property
    def exit_button(self) -> int:
        """Return the current exit button setting."""
        from picoware.system.buttons import BUTTON_BACK
        return int(self._settings.get("exit_button", BUTTON_BACK))
    
    @exit_button.setter
    def exit_button(self, value: int):
        """Set the exit button setting."""
        self._settings["exit_button"] = value
        self.__save_settings()
        
    @property
    def gmt_offset(self) -> int:
        """Return the current GMT offset."""
        return int(self._settings.get("gmt_offset", 0))
    
    @gmt_offset.setter
    def gmt_offset(self, value: int):
        """Set GMT offset."""
        self._settings["gmt_offset"] = value
        self.__save_settings()
    

    @property
    def lvgl_mode(self) -> bool:
        """Return True if LVGL mode is enabled, False otherwise."""
        return bool(self._settings.get("lvgl_mode", False))
    
    @lvgl_mode.setter
    def lvgl_mode(self, value: bool):
        """Set LVGL mode."""
        self._settings["lvgl_mode"] = value
        self.__save_settings()

    @property
    def onscreen_keyboard(self) -> bool:
        """Return True if onscreen keyboard is enabled, False otherwise."""
        return bool(self._settings.get("onscreen_keyboard", False))
    
    @onscreen_keyboard.setter
    def onscreen_keyboard(self, value: bool):
        """Set onscreen keyboard."""
        self._settings["onscreen_keyboard"] = value
        self.__save_settings()
    
    @property
    def openai_api_key(self) -> str:
        """Return the current OpenAI API key."""
        return self._settings.get("openai_api_key", "")
    
    @openai_api_key.setter
    def openai_api_key(self, value: str):
        """Set the OpenAI API key."""
        self._settings["openai_api_key"] = value
        self.__save_settings()

    @property
    def server_settings(self) -> dict:
        """Return the current server settings."""
        username = self._settings.get("server_username", "") 
        password = self._settings.get("server_password", "")

        return {"username": username, "password": password}
    
    @server_settings.setter
    def server_settings(self, value: dict):
        """Set the server settings."""
        username = value.get("username", "")
        password = value.get("password", "")
        self._settings["server_username"] = username
        self._settings["server_password"] = password
        self.__save_settings()
    
    @property
    def settings(self) -> dict:
        """Return all settings as a dictionary."""
        return self._settings

    @property
    def theme_color(self) -> int:
        """Return the current theme color."""
        return int(self._settings.get("theme_color", 0x001F))
    
    @theme_color.setter
    def theme_color(self, value: int):
        """Set the theme color."""
        self._settings["theme_color"] = value
        self.__save_settings()
    
    @property
    def wifi_settings(self) -> dict:
        """Return the current WiFi settings."""
        ssid = self._settings.get("wifi_ssid", "")
        password = self._settings.get("wifi_password", "")
        return {"ssid": ssid, "password": password}
    
    @wifi_settings.setter
    def wifi_settings(self, value: dict):
        """Set the WiFi settings."""
        ssid = value.get("ssid", "")
        password = value.get("password", "")
        self._settings["wifi_ssid"] = ssid
        self._settings["wifi_password"] = password
        self.__save_settings()
    
    def __fetch_setting(self, path: str, key: str, default=""):
        """Helper method to fetch a setting value from storage."""
        if not self._storage.exists(path):
            return default

        data = self._storage.read(path)
        if data is not None:
            try:
                obj = json.loads(data)
                if key in obj:
                    return obj[key]
            except Exception:
                pass

        return default
    
    def __save_settings(self) -> bool:
        """Save settings to storage."""
        return self._storage.write(
            self._path,
            json.dumps(self._settings),
        )