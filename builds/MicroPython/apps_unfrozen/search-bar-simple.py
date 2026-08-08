# picoware/apps/search-bar-simple.py

_search_bar = None


def start(view_manager) -> bool:
    """Start the app"""
    from picoware.gui.search_bar import SearchBar

    global _search_bar

    if _search_bar is None:
        items = [
            "Apple",
            "Banana",
            "Cherry",
            "Grape",
            "Lemon",
            "Orange",
            "Peach",
            "Strawberry",
        ]
        _search_bar = SearchBar(view_manager, items)

    view_manager.input_manager.reset()
    return _search_bar.run(force=True)


def run(view_manager) -> None:
    """Run the app"""
    from picoware.system.buttons import BUTTON_BACK

    button = view_manager.button
    search_bar = _search_bar

    if button == BUTTON_BACK or not search_bar.run():
        if search_bar.is_finished:
            print("Selected:", search_bar.selected_item)
        view_manager.back()


def stop(view_manager) -> None:
    """Stop the app"""
    from gc import collect

    global _search_bar

    if _search_bar:
        _search_bar.reset()

    collect()
