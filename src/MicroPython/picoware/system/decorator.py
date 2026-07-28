import micropython
import picoware_boards

def audio_required(func: callable) -> callable:
    """Decorator to check if Audio is available"""
    if picoware_boards.BOARD_HAS_AUDIO == 0:
        def unavailable(*args, **kwargs):
            raise RuntimeError(f"{func.__name__} requires Audio, which is not available")
        return unavailable
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

def native(func: callable) -> callable:
    """Decorator to wrap a function with micropython.native"""
    if picoware_boards.BOARD_HAS_RP2040 == 1:
        return func
    @micropython.native
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

def psram_required(func: callable) -> callable:
    """Decorator to check if PSRAM is available"""
    if picoware_boards.BOARD_HAS_PSRAM == 0:
        def unavailable(*args, **kwargs):
            raise RuntimeError(f"{func.__name__} requires PSRAM, which is not available")
        return unavailable
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

def storage_required(func: callable) -> callable:
    """Decorator to check if storage is available"""
    if picoware_boards.BOARD_HAS_SD == 0:
        def unavailable(*args, **kwargs):
            raise RuntimeError(f"{func.__name__} requires SD storage, which is not available")
        return unavailable
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

def viper(func: callable) -> callable:
    """Decorator to wrap a function with micropython.viper"""
    if picoware_boards.BOARD_HAS_RP2040 == 1:
        return func
    try:
        @micropython.viper
        def wrapper():
            return func()
        return wrapper
    except Exception:
        return func

def wifi_required(func: callable) -> callable:
    """Decorator to check if WiFi is available"""
    if picoware_boards.BOARD_HAS_WIFI == 0:
        def unavailable(*args, **kwargs):
            raise RuntimeError(f"{func.__name__} requires WiFi, which is not available")
        return unavailable
    def wrapper(*args, **kwargs):
        view_manager = args[0]
        wifi = view_manager.wifi
        if not wifi.is_connected():
            raise RuntimeError(f"{func.__name__} requires WiFi, but it is not connected yet.")
        from picoware.applications.wifi.utils import connect_to_saved_wifi
        connect_to_saved_wifi(args[0])
        return func(*args, **kwargs)
    return wrapper