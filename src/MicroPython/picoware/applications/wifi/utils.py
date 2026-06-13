def connect_to_saved_wifi(view_manager) -> bool:
    """Attempt to connect to the saved WiFi network."""
    wifi = view_manager.wifi
    if not wifi:
        return False

    if wifi.is_connected():
        return True

    settings = load_wifi_settings(view_manager)
    ssid = settings.get("ssid", "")
    password = settings.get("password", "")

    if not ssid:
        return False

    return wifi.connect_async(ssid, password, sta_mode=True)


def load_wifi_settings(view_manager) -> dict:
    """Load the saved WiFi settings from storage."""
    from picoware.system.settings import Settings
    storage = view_manager.storage
    settings = Settings(storage)
    return settings.wifi_settings


def load_wifi_ssid(view_manager) -> str:
    """Load the saved WiFi SSID from storage."""
    from picoware.system.settings import Settings
    storage = view_manager.storage
    settings = Settings(storage)
    return settings.wifi_settings.get("ssid", "")


def load_wifi_password(view_manager) -> str:
    """Load the saved WiFi password from storage."""
    from picoware.system.settings import Settings
    storage = view_manager.storage
    settings = Settings(storage)
    return settings.wifi_settings.get("password", "")


def save_wifi_settings(storage, ssid: str, password: str = "") -> bool:
    """Save the WiFi settings to storage."""
    from picoware.system.settings import Settings

    if not ssid or not password:
        print("SSID or password cannot be empty")
        return False
    settings = {"ssid": ssid, "password": password}
    _set = Settings(storage)
    _set.wifi_settings = settings
    return True
    


def save_wifi_ssid(storage, ssid: str) -> bool:
    """Save the WiFi SSID to storage."""
    from picoware.system.settings import Settings

    if not ssid:
        print("SSID cannot be empty")
        return False

    settings = Settings(storage)
    current_settings = settings.wifi_settings
    current_settings["ssid"] = ssid
    settings.wifi_settings = current_settings
    return True


def save_wifi_password(storage, password: str) -> bool:
    """Save the WiFi password to storage."""
    from picoware.system.settings import Settings

    if not password:
        print("Password cannot be empty")
        return False

    settings = Settings(storage)
    current_settings = settings.wifi_settings
    current_settings["password"] = password
    settings.wifi_settings = current_settings
    return True
