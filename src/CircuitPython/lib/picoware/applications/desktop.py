from picogui.desktop import Desktop

desktop = None


def main(view_manager) -> None:
    """Draw the desktop environment with a BMP image from disk."""
    global desktop
    if desktop is None:
        desktop = Desktop(view_manager.draw, 0x000000, 0xFFFFFF, "/sd/desktop.bmp")
    desktop.draw()
