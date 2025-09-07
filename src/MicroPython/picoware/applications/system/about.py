_about = None
_about_text = (
    "Picoware\n"
    "Version: 1.0.0\n"
    "A custom firmware for the PicoCalc, Video Game Module, and other Raspberry Pi Pico devices, originally created by JBlanked on 2025-05-13.\n"
    "This firmware was made with Arduino IDE/C++ and is open source on GitHub. Developers are welcome to contribute.\n"
    "Picoware is a work in progress and is not yet complete. Some features may not work as expected. Picoware is not affiliated with ClockworkPI, the Raspberry Pi Foundation, or any other organization.\n"
    "Discord: https://discord.gg/5aN9qwkEc6\n"
    "GitHub: https://www.github.com/jblanked/Picoware\n"
    "Instagram: @jblanked"
)


def start(view_manager) -> bool:
    """Start the app."""
    from picoware.gui.textbox import TextBox

    global _about
    if _about is None:
        _about = TextBox(
            view_manager.draw,
            0,
            320,
            view_manager.get_foreground_color(),
            view_manager.get_background_color(),
        )
        _about.set_text(_about_text)
    return True


def run(view_manager) -> None:
    """Run the app."""
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
    )

    global _about
    if not _about:
        return

    input_manager = view_manager.input_manager
    button: int = input_manager.get_last_button()

    if button in (BUTTON_LEFT, BUTTON_BACK):
        input_manager.reset(True)
        view_manager.back()
    elif button == BUTTON_DOWN:
        input_manager.reset(True)
        _about.scroll_down()
    elif button == BUTTON_UP:
        input_manager.reset(True)
        _about.scroll_up()


def stop(view_manager) -> None:
    """Stop the app."""
    from gc import collect

    global _about
    if _about:
        del _about
        _about = None
    collect()
