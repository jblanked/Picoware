"""Decorators for feature availability checks."""

import micropython
import picoware_boards

def audio_required(func: callable) -> callable:
    """Decorator to check if Audio is available.

    Args:
        func (callable): The function to decorate.

    Returns:
        callable: The wrapped function, or a stub that raises when audio is missing.

    Raises:
        RuntimeError: If the decorated function is called without audio support.
    """
    if picoware_boards.BOARD_HAS_AUDIO == 0:
        def unavailable(*args, **kwargs):
            """Raise an error because audio is not available.

            Raises:
                RuntimeError: If audio support is missing on the board.
            """
            raise RuntimeError(f"{func.__name__} requires Audio, which is not available")
        return unavailable
    def wrapper(*args, **kwargs):
        """Call the wrapped function with the given arguments.

        Returns:
            object: The result of the wrapped function.
        """
        return func(*args, **kwargs)
    return wrapper

def native(func: callable) -> callable:
    """Decorator to wrap a function with micropython.native.

    Args:
        func (callable): The function to decorate.

    Returns:
        callable: The function, wrapped with micropython.native on supported boards.
    """
    if picoware_boards.BOARD_HAS_RP2040 == 1:
        return func
    @micropython.native
    def wrapper(*args, **kwargs):
        """Call the wrapped function with the given arguments.

        Returns:
            object: The result of the wrapped function.
        """
        return func(*args, **kwargs)
    return wrapper

def psram_required(func: callable) -> callable:
    """Decorator to check if PSRAM is available.

    Args:
        func (callable): The function to decorate.

    Returns:
        callable: The wrapped function, or a stub that raises when PSRAM is missing.

    Raises:
        RuntimeError: If the decorated function is called without PSRAM support.
    """
    if picoware_boards.BOARD_HAS_PSRAM == 0:
        def unavailable(*args, **kwargs):
            """Raise an error because PSRAM is not available.

            Raises:
                RuntimeError: If PSRAM support is missing on the board.
            """
            raise RuntimeError(f"{func.__name__} requires PSRAM, which is not available")
        return unavailable
    def wrapper(*args, **kwargs):
        """Call the wrapped function with the given arguments.

        Returns:
            object: The result of the wrapped function.
        """
        return func(*args, **kwargs)
    return wrapper

def storage_required(func: callable) -> callable:
    """Decorator to check if storage is available.

    Args:
        func (callable): The function to decorate.

    Returns:
        callable: The wrapped function, or a stub that raises when storage is missing.

    Raises:
        RuntimeError: If the decorated function is called without SD storage support.
    """
    if picoware_boards.BOARD_HAS_SD == 0:
        def unavailable(*args, **kwargs):
            """Raise an error because SD storage is not available.

            Raises:
                RuntimeError: If SD storage support is missing on the board.
            """
            raise RuntimeError(f"{func.__name__} requires SD storage, which is not available")
        return unavailable
    def wrapper(*args, **kwargs):
        """Call the wrapped function with the given arguments.

        Returns:
            object: The result of the wrapped function.
        """
        return func(*args, **kwargs)
    return wrapper

def viper(func: callable) -> callable:
    """Decorator to wrap a function with micropython.viper.

    Args:
        func (callable): The function to decorate.

    Returns:
        callable: The function, wrapped with micropython.viper on supported boards.
    """
    if picoware_boards.BOARD_HAS_RP2040 == 1:
        return func
    try:
        @micropython.viper
        def wrapper():
            """Call the wrapped function.

            Returns:
                object: The result of the wrapped function.
            """
            return func()
        return wrapper
    except Exception:
        return func

def bluetooth_required(func: callable) -> callable:
    """Decorator to check if Bluetooth is available.

    Args:
        func (callable): The function to decorate.  
    
    Returns:
        callable: The wrapped function, or a stub that raises when Bluetooth is missing.
    Raises:
        RuntimeError: If the decorated function is called without Bluetooth support.
    """
    if picoware_boards.BOARD_HAS_BLUETOOTH == 0:
        def unavailable(*args, **kwargs):
            """Raise an error because Bluetooth is not available.

            Raises:
                RuntimeError: If Bluetooth support is missing on the board.
            """
            raise RuntimeError(f"{func.__name__} requires Bluetooth, which is not available")
        return unavailable
    def wrapper(*args, **kwargs):
        """Call the wrapped function with the given arguments.

        Returns:
            object: The result of the wrapped function.
        """
        return func(*args, **kwargs)
    return wrapper

def wifi_required(func: callable) -> callable:
    """Decorator to check if WiFi is available.

    Args:
        func (callable): The function to decorate.

    Returns:
        callable: The wrapped function, or a stub that raises when WiFi is missing.

    Raises:
        RuntimeError: If the decorated function is called without WiFi connected.
    """
    if picoware_boards.BOARD_HAS_WIFI == 0:
        def unavailable(*args, **kwargs):
            """Raise an error because WiFi is not available.

            Raises:
                RuntimeError: If WiFi support is missing on the board.
            """
            raise RuntimeError(f"{func.__name__} requires WiFi, which is not available")
        return unavailable
    def wrapper(*args, **kwargs):
        """Connect to saved WiFi and call the wrapped function.

        Args:
            *args: Positional arguments passed to the wrapped function.
            **kwargs: Keyword arguments passed to the wrapped function.

        Returns:
            object: The result of the wrapped function.

        Raises:
            RuntimeError: If WiFi is not connected.
        """
        view_manager = args[0]
        wifi = view_manager.wifi
        if not wifi.is_connected():
            raise RuntimeError(f"{func.__name__} requires WiFi, but it is not connected yet.")
        from picoware.applications.wifi.utils import connect_to_saved_wifi
        connect_to_saved_wifi(args[0])
        return func(*args, **kwargs)
    return wrapper