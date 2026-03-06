_file_browser = None

def start(view_manager) -> bool:
    """Initialize the app and ensure hardware prerequisites are met."""
    if not view_manager.has_sd_card:
        view_manager.alert("File Browser app requires an SD card")
        return False

    global _file_browser

    if _file_browser is None:
        from picoware.gui.file_browser import FileBrowser, FILE_BROWSER_MANAGER
        _file_browser = FileBrowser(view_manager, FILE_BROWSER_MANAGER)

    return True

def run(view_manager) -> None:
    """Tick the active file browser loop."""
    if not _file_browser.run():
        view_manager.back()

def stop(view_manager) -> None:
    """Aggressively clean up memory to prevent PSRAM/RAM leaks upon exit."""
    from gc import collect
    global _file_browser

    if _file_browser is not None:
        del _file_browser
        _file_browser = None

    collect()
