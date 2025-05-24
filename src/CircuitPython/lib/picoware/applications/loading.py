from picogui.loading import Loading

load: Loading = None


def main(view_manager):
    """Animate the loading spinner."""
    global load
    if load is None:
        load = Loading(view_manager.draw, 0x000000, 0xFFFFFF)
    load.animate()
