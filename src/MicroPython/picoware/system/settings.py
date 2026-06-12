import json

class Settings:
    """Settings management for Picoware."""

    __slots__ = ["_storage"]

    def __init__(self, storage):
        self._storage = storage
    
    @property
    def dark_mode(self) -> bool:
        """Return True if dark mode is enabled, False otherwise."""
        _path = "picoware/settings/dark_mode.json"

        return bool(self.__fetch_setting(_path, "dark_mode", True))
    
    @dark_mode.setter
    def dark_mode(self, value: bool):
        """Set dark mode."""
        self.__save_setting(
            "picoware/settings/dark_mode.json",
            "dark_mode",
            value,
        )

    @property
    def debug(self) -> bool:
        """Return True if debug mode is enabled, False otherwise."""
        _path = "picoware/settings/debug.json"

        return bool(self.__fetch_setting(_path, "debug", False))
    
    @debug.setter
    def debug(self, value: bool):
        """Set debug mode."""
        self.__save_setting(
            "picoware/settings/debug.json",
            "debug",
            value,
        )

    @property
    def exit_button(self) -> str:
        """Return the current exit button setting."""
        from picoware.system.buttons import BUTTON_BACK
        
        _path = "picoware/settings/exit_button.json"

        return int(self.__fetch_setting(_path, "exit_button", BUTTON_BACK))
    
    @exit_button.setter
    def exit_button(self, value: int):
        """Set the exit button setting."""
        return self.__save_setting(
            "picoware/settings/exit_button.json",
            "exit_button",
            value,
        )
    
    @property
    def gmt_offset(self) -> int:
        """Return the current GMT offset."""
        _path = "picoware/settings/gmt_offset.json"

        return int(self.__fetch_setting(_path, "gmt_offset", 0))
    
    @gmt_offset.setter
    def gmt_offset(self, value: int):
        """Set GMT offset."""
        self.__save_setting(
            "picoware/settings/gmt_offset.json",
            "gmt_offset",
            value,
        )
    
     @property
    def onscreen_keyboard(self) -> bool:
        """Return True if onscreen keyboard is enabled, False otherwise."""
        _path = "picoware/settings/onscreen_keyboard.json"

        return bool(self.__fetch_setting(_path, "onscreen_keyboard", False))
    
    @onscreen_keyboard.setter
    def onscreen_keyboard(self, value: bool):
        """Set onscreen keyboard."""
        self.__save_setting(
            "picoware/settings/onscreen_keyboard.json",
            "onscreen_keyboard",
            value,
        )

    @property
    def lvgl_mode(self) -> bool:
        """Return True if LVGL mode is enabled, False otherwise."""
        _path = "picoware/settings/lvgl_mode.json"

        return bool(self.__fetch_setting(_path, "lvgl_mode", False))
    
    @lvgl_mode.setter
    def lvgl_mode(self, value: bool):
        """Set LVGL mode."""
        self.__save_setting(
            "picoware/settings/lvgl_mode.json",
            "lvgl_mode",
            value,
        )

    @property
    def server_settings(self) -> dict:
        """Return the current server settings."""
        _user_path = "picoware/settings/server_username.json"
        _pass_path = "picoware/settings/server_password.json"

        username = self.__fetch_setting(_user_path, "username", "")
        password = self.__fetch_setting(_pass_path, "password", "")

        return {"username": username, "password": password}
    
    @server_settings.setter
    def server_settings(self, value: dict):
        """Set the server settings."""
        username = value.get("username", "")
        password = value.get("password", "")
        self.__save_setting("picoware/settings/server_username.json", "username", username)
        self.__save_setting("picoware/settings/server_password.json", "password", password)
        
    @property
    def theme_color(self) -> int:
        """Return the current theme color."""
        _path = "picoware/settings/theme_color.json"
        
        return int(self.__fetch_setting(_path, "theme_color", 0x001F))
            
    
    @theme_color.setter
    def theme_color(self, value: int):
        """Set the theme color."""
        self.__save_setting(
            "picoware/settings/theme_color.json",
            "theme_color",
            value,
        )


    
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
    
    def __save_setting(self, path: str, key: str, value) -> bool:
        """Helper method to save a setting value to storage."""
        return self._storage.write(
            path,
            json.dumps({key: value}),
        )