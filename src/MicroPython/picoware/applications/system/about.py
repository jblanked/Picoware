_about = None


def start(view_manager) -> bool:
    """Start the app."""
    from picoware.gui.textbox import TextBox
    from picoware.system.system import System

    global _about
    if _about is None:
        _about = TextBox(
            view_manager.draw,
            0,
            view_manager.draw.size.y,
            view_manager.foreground_color,
            view_manager.background_color,
        )
        sys = System()
        version = sys.version
        _about.set_text(
            (
                "Picoware\n"
                f"Version: {version}\n"
                "A custom firmware for the PicoCalc, Video Game Module, Waveshare Touch LCD, and other Raspberry Pi Pico devices, originally created by JBlanked on 2025-05-13.\n"
                "This firmware was made with MicroPython and is open source on GitHub. Developers are welcome to contribute.\n"
                "Picoware is a work in progress and is not yet complete. Some features may not work as expected. Picoware is not affiliated with ClockworkPI, the Raspberry Pi Foundation, or any other organization.\n"
                "Discord: https://discord.gg/5aN9qwkEc6\n"
                "GitHub: https://www.github.com/jblanked/Picoware\n"
                "Instagram: @jblanked"
            )
        )
    return True


def run(view_manager) -> None:
    """Run the app."""
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
    )

    if not _about:
        return

    button: int = view_manager.button

    if button in (BUTTON_LEFT, BUTTON_BACK):
        view_manager.back()
    elif button == BUTTON_DOWN:
        _about.scroll_down()
    elif button == BUTTON_UP:
        _about.scroll_up()


def stop(view_manager) -> None:
    """Stop the app."""
    from gc import collect

    global _about
    if _about:
        del _about
        _about = None
    collect()
