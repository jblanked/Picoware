# picoware/apps/menu-simple.py

_menu = None


def start(view_manager) -> bool:
    """Start the App"""
    from picoware.gui.menu import Menu

    global _menu

    if not _menu:
        draw = view_manager.draw
        # set menu
        _menu = Menu(
            draw,  # draw instance
            "Menu Simple",  # title
            0,  # y position
            draw.size.y,  # height
            view_manager.foreground_color,  # text color
            view_manager.background_color,  # background color
            view_manager.selected_color,    # selected item color
            view_manager.foreground_color,  # border color
        )

        # add items
        _menu.add_item("First Item")
        _menu.add_item("Second Item")
        _menu.add_item("Third Item")

        # quick add 4-19
        for i in range(4, 20):
            _menu.add_item(f"Item {i}")

        _menu.set_selected(0)

    return True


def run(view_manager) -> None:
    """Run the App"""
    from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_BACK

    button = view_manager.button

    if button == BUTTON_UP:
        _menu.scroll_up()
    elif button == BUTTON_DOWN:
        _menu.scroll_down()
    elif button == BUTTON_BACK:
        view_manager.back()


def stop(view_manager) -> None:
    """Stop the App"""
    from gc import collect

    global _menu

    if _menu:
        del _menu
        _menu = None

    collect()
