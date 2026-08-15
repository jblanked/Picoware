"""WiFi utilities for connecting and saving credentials."""

def connect_to_saved_wifi(view_manager) -> bool:
    """Attempt to connect to the saved WiFi network.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.

    Returns:
        bool: True if connected or connection started, False otherwise.
    """
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
    """Load the saved WiFi settings from storage.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.

    Returns:
        dict: The saved WiFi settings.
    """
    from picoware.system.settings import Settings
    storage = view_manager.storage
    settings = Settings(storage)
    return settings.wifi_settings


def load_wifi_ssid(view_manager) -> str:
    """Load the saved WiFi SSID from storage.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.

    Returns:
        str: The saved SSID.
    """
    from picoware.system.settings import Settings
    storage = view_manager.storage
    settings = Settings(storage)
    return settings.wifi_settings.get("ssid", "")


def load_wifi_password(view_manager) -> str:
    """Load the saved WiFi password from storage.

    Args:
        view_manager (ViewManager): The view manager instance for display and storage access.

    Returns:
        str: The saved password.
    """
    from picoware.system.settings import Settings
    storage = view_manager.storage
    settings = Settings(storage)
    return settings.wifi_settings.get("password", "")


def save_wifi_ssid(storage, ssid: str) -> bool:
    """Save the WiFi SSID to storage.

    Args:
        storage (Storage): The storage to save to.
        ssid (str): The SSID to save.

    Returns:
        bool: True if the SSID was saved, False if it is empty.
    """
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
    """Save the WiFi password to storage.

    Args:
        storage (Storage): The storage to save to.
        password (str): The password to save.

    Returns:
        bool: True on success.
    """
    from picoware.system.settings import Settings

    if not password:
        print("Password is empty")

    settings = Settings(storage)
    current_settings = settings.wifi_settings
    current_settings["password"] = password
    settings.wifi_settings = current_settings
    return True
