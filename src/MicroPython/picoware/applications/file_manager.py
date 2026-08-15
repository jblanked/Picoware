"""File Manager - Browse and manage files."""

_file_browser = None


def start(view_manager) -> bool:
    """Start the app.

    Args:
        view_manager (ViewManager): The view manager context.

    Returns:
        bool: True on success.
    """
    if not view_manager.has_sd_card:
        view_manager.alert("File Browser app requires an SD card")
        return False

    global _file_browser

    if _file_browser is None:
        from picoware.gui.file_browser import FileBrowser, FILE_BROWSER_MANAGER

        _file_browser = FileBrowser(view_manager, FILE_BROWSER_MANAGER)

    return True


def run(view_manager) -> None:
    """Run the app.

    Args:
        view_manager (ViewManager): The view manager context.
    """

    if not _file_browser.run():
        view_manager.back()


def stop(view_manager) -> None:
    """Stop the app.

    Args:
        view_manager (ViewManager): The view manager context.
    """
    from gc import collect

    global _file_browser

    if _file_browser is not None:
        del _file_browser
        _file_browser = None

    # Clean up memory
    collect()
