"""Applications - Central hub for all Picoware apps."""

_applications = None
_applications_index = 0


def start(view_manager) -> bool:
    """Start the app.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: True on success.
    """
    from picoware.gui.menu import Menu

    global _applications

    if _applications is None:
        _applications = Menu(
            view_manager.draw,
            "Applications",
            0,
            view_manager.draw.size.y,
            view_manager.foreground_color,
            view_manager.background_color,
            view_manager.selected_color,
            view_manager.foreground_color,
            2,
        )
        _applications.add_item("Agent")
        _applications.add_item("App Store")
        _applications.add_item("C")
        _applications.add_item("Custom")
        _applications.add_item("FlipSocial")
        _applications.add_item("Games")
        _applications.add_item("JavaScript")
        _applications.add_item("MMBasic")
        _applications.add_item("Screensavers")
        _applications.set_selected(_applications_index)

        _applications.draw()
    return True


def run(view_manager) -> None:
    """Run the app.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    from picoware.system.view import View
    from picoware.system.buttons import (
        BUTTON_BACK,
        BUTTON_UP,
        BUTTON_DOWN,
        BUTTON_LEFT,
        BUTTON_CENTER,
        BUTTON_RIGHT,
    )

    if not _applications:
        return

    global _applications_index

    button: int = view_manager.button

    if button in (BUTTON_UP, BUTTON_LEFT):
        _applications.scroll_up()
    elif button in (BUTTON_DOWN, BUTTON_RIGHT):
        _applications.scroll_down()
    elif button == BUTTON_BACK:
        _applications_index = 0
        view_manager.back()
    elif button == BUTTON_CENTER:
        _applications_index = _applications.selected_index
        if _applications.current_item == "Agent":
            from picoware.applications.applications import agent

            view_manager.add(View("agent", agent.run, agent.start, agent.stop))
            view_manager.switch_to("agent")
        elif _applications.current_item == "App Store":
            from picoware.applications.applications import app_store

            view_manager.add(
                View(
                    "app_store",
                    app_store.run,
                    app_store.start,
                    app_store.stop,
                )
            )
            view_manager.switch_to("app_store")
        elif _applications.current_item == "C":
            from picoware.applications.applications import c

            view_manager.add(
                View(
                    "c",
                    c.run,
                    c.start,
                    c.stop,
                )
            )
            view_manager.switch_to("c")
        elif _applications.current_item == "Custom":
            from picoware.applications.applications import custom

            view_manager.add(
                View(
                    "custom",
                    custom.run,
                    custom.start,
                    custom.stop,
                )
            )
            view_manager.switch_to("custom")
        elif _applications.current_item == "FlipSocial":
            from picoware.applications.applications import FlipSocial

            view_manager.add(
                View(
                    "flipsocial",
                    FlipSocial.run,
                    FlipSocial.start,
                    FlipSocial.stop,
                )
            )
            view_manager.switch_to("flipsocial")
        elif _applications.current_item == "Games":
            from picoware.applications.applications.games import games

            view_manager.add(View("games", games.run, games.start, games.stop))
            view_manager.switch_to("games")
        elif _applications.current_item == "JavaScript":
            from picoware.applications.applications import javascript

            view_manager.add(
                View(
                    "javascript",
                    javascript.run,
                    javascript.start,
                    javascript.stop,
                )
            )
            view_manager.switch_to("javascript")
        elif _applications.current_item == "MMBasic":
            from picoware.applications.applications import mmbasic

            view_manager.add(
                View(
                    "mmbasic",
                    mmbasic.run,
                    mmbasic.start,
                    mmbasic.stop,
                )
            )
            view_manager.switch_to("mmbasic")
        elif _applications.current_item == "Screensavers":
            from picoware.applications.applications import screensavers

            view_manager.add(
                View(
                    "screensavers",
                    screensavers.run,
                    screensavers.start,
                    screensavers.stop,
                )
            )
            view_manager.switch_to("screensavers")


def stop(view_manager) -> None:
    """Stop the app.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    from gc import collect

    global _applications
    if _applications:
        del _applications
        _applications = None
    collect()
