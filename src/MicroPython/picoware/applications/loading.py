load = None


def start(view_manager) -> bool:
    """Start the loading animation."""
    from picoware.gui.loading import Loading
    from picoware.system.colors import TFT_BLACK, TFT_WHITE

    global load
    if load is None:
        load = Loading(view_manager.draw, TFT_WHITE, TFT_BLACK)
    return True


def run(view_manager) -> None:
    """Animate the loading spinner."""
    global load
    if load:
        load.animate()


def stop(view_manager) -> None:
    """Stop the loading animation."""
    global load
    if load:
        load.stop()
        del load
