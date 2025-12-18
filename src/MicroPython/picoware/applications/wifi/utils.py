WIFI_SETTINGS_PATH = "picoware/wifi/settings.json"
WIFI_SSID_PATH = "picoware/wifi/ssid.json"
WIFI_PASSWORD_PATH = "picoware/wifi/password.json"


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

    if not ssid or not password:
        return False

    return wifi.connect(ssid, password, sta_mode=True, is_async=True)


def load_wifi_settings(view_manager) -> dict:
    """Load the saved WiFi settings from storage."""
    from ujson import loads

    storage = view_manager.storage
    data = storage.read(WIFI_SETTINGS_PATH, "r")
    if not data:
        return {}
    try:
        return loads(data)
    except Exception as e:
        print("Error loading WiFi settings:", e)
        return {}


def load_wifi_ssid(view_manager) -> str:
    """Load the saved WiFi SSID from storage."""
    from ujson import loads

    storage = view_manager.storage
    data = storage.read(WIFI_SSID_PATH, "r")
    if not data:
        return ""
    try:
        return loads(data).get("ssid", "")
    except Exception as e:
        print("Error loading WiFi SSID:", e)
        return ""


def load_wifi_password(view_manager) -> str:
    """Load the saved WiFi password from storage."""
    from ujson import loads

    storage = view_manager.storage
    data = storage.read(WIFI_PASSWORD_PATH, "r")

    if not data:
        return ""
    try:
        return loads(data).get("password", "")
    except Exception as e:
        print("Error loading WiFi password:", e)
        return ""


def save_wifi_settings(storage, ssid: str, password: str) -> bool:
    """Save the WiFi settings to storage."""

    if not ssid or not password:
        print("SSID and password cannot be empty")
        return False

    from ujson import dumps

    settings = {"ssid": ssid, "password": password}
    try:
        if not storage.write(WIFI_SETTINGS_PATH, dumps(settings)):
            print("Error writing WiFi settings")
            return False
        if not storage.write(WIFI_SSID_PATH, dumps({"ssid": ssid})):
            print("Error writing WiFi SSID")
            return False
        if not storage.write(WIFI_PASSWORD_PATH, dumps({"password": password})):
            print("Error writing WiFi password")
            return False
        return True
    except Exception as e:
        print("Error saving WiFi settings:", e)
        return False


def save_wifi_ssid(storage, ssid: str) -> bool:
    """Save the WiFi SSID to storage."""

    if not ssid:
        print("SSID cannot be empty")
        return False

    from ujson import dumps

    try:
        storage.write(WIFI_SSID_PATH, dumps({"ssid": ssid}))
        return True
    except Exception as e:
        print("Error saving WiFi SSID:", e)
        return False


def save_wifi_password(storage, password: str) -> bool:
    """Save the WiFi password to storage."""

    if not password:
        print("Password cannot be empty")
        return False

    from ujson import dumps

    try:
        storage.write(WIFI_PASSWORD_PATH, dumps({"password": password}))
        return True
    except Exception as e:
        print("Error saving WiFi password:", e)
        return False
