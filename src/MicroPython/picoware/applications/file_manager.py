import gc # Import garbage collector to heavily optimize RAM usage

_file_browser = None # Global pointer to hold the FileBrowser instance during runtime

def start(view_manager) -> bool: # Define the required start lifecycle method
    """Start the app""" # Docstring for the start method
    if not view_manager.has_sd_card: # Verify physical hardware has an SD card inserted
        view_manager.alert("File Browser app requires an SD card") # Show system alert if missing
        return False # Abort the application launch to prevent crashes

    global _file_browser # Declare intent to modify the global instance pointer

    if _file_browser is None: # Check if the browser object needs to be created
        from picoware.gui.file_browser import FileBrowser, FILE_BROWSER_MANAGER # Import locally to save RAM (globals to locals concept)
        _file_browser = FileBrowser(view_manager, FILE_BROWSER_MANAGER) # Instantiate the browser in full Commander mode

    return True # Return True to tell the OS the app successfully started

def run(view_manager) -> None: # Define the required run lifecycle loop method
    """Run the app""" # Docstring for the run method
    
    global _file_browser # Access the global instance pointer
    
    if not _file_browser.run(): # Execute the browser's internal loop and check if it returned False (exit signal)
        view_manager.back() # Tell the system OS to return to the previous screen (Home Menu)

def stop(view_manager) -> None: # Define the required stop lifecycle method
    """Stop the app""" # Docstring for the stop method
    
    global _file_browser # Access the global instance pointer

    if _file_browser is not None: # Verify the object exists before trying to destroy it
        del _file_browser # Explicitly delete the object from RAM
        _file_browser = None # Reset the global pointer to None safely

    gc.collect() # Aggressively collect garbage to prevent memory leaks and RAM buildup
