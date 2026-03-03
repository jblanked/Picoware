import gc # Import garbage collector to heavily optimize RAM
import time # Import time module for deferred save timers
import json # Import json for delta-check state saving

from picoware.system.vector import Vector # Import Vector class required for Picoware drawing coordinates
from picoware.system.colors import TFT_WHITE, TFT_BLACK, TFT_BLUE, TFT_YELLOW, TFT_CYAN # Import official Picoware 16-bit color constants including Cyan for MC theme
from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_CENTER, BUTTON_BACK # Import official button constants
from picoware.gui.menu import Menu # Import the official Picoware Menu component for the context popup

_app_state = None # Global dictionary to hold our application state dynamically
_last_saved_json = "{}" # Global string to hold the last saved state for delta-checking
_last_save_time = 0 # Global integer tracking the last time we checked for auto-save
_is_help_screen = False # Global boolean flag to track if we are showing the help screen
_context_menu = None # Global variable to hold the instantiated Menu object when active
_confirm_menu = None # Global variable to hold the confirmation Menu object
_context_target_path = "" # Global string to store the absolute path of the file being acted upon
_pending_action = "" # Global string to track what action is awaiting confirmation

def _init_state(): # Function to initialize state, keeping RAM usage low
    global _app_state # Declare global to modify the state dictionary
    _app_state = { # Create the state dictionary
        "left_path": "/", # String for left pane current directory, natively handled by vm.storage
        "right_path": "/", # String for right pane current directory, natively handled by vm.storage
        "left_files": [], # List of tuples to hold left pane file items (name, is_dir)
        "right_files": [], # List of tuples to hold right pane file items (name, is_dir)
        "left_index": 0, # Integer for left pane cursor position
        "right_index": 0, # Integer for right pane cursor position
        "active_pane": "left" # String to track which pane has focus ('left' or 'right')
    } # End of dictionary creation

def _load_dir(vm, path): # Function to load directory contents efficiently using Picoware SDK
    items = [] # Initialize empty list for items
    if path != "/": # Check if we are not at the root directory
        items.append(("..", True)) # Append parent directory shortcut as a folder tuple
    try: # Try block to catch permission or missing directory errors
        dir_list = vm.storage.listdir(path) # Use official Picoware storage API to list files
        for item in dir_list: # Iterate through the directory yield
            if item == "." or item == "..": # Filter out raw OS relative path pointers to prevent duplication
                continue # Skip to the next item
            full_path = "/" + item if path == "/" else path + "/" + item # Construct full path for directory check
            is_dir = False # Default flag to false
            try: # Try block for OS check
                if vm.storage.is_directory(full_path): # Check if the item is a folder
                    is_dir = True # Set flag to true
            except Exception: # Catch filesystem errors gracefully
                pass # Ignore unreadable items silently
            items.append((item, is_dir)) # Append tuple with filename and directory boolean to save RAM during draw loop
        del dir_list # Explicitly delete iterator to free memory
    except Exception as e: # Catch any exceptions to prevent crashes
        print("Dir load error:", e) # Print error to Thonny for debugging
        items.append(("<ERROR>", False)) # Show error string if directory read fails
    gc.collect() # Aggressively collect garbage after reading directory
    return items # Return the populated list of file tuples

def _draw_ui(vm): # Function to render the UI using classic Midnight Commander styling
    draw = vm.draw # Get the Draw instance from the ViewManager
    draw.clear(color=TFT_BLUE) # Clear the screen with the classic MC blue background
    
    screen_w = draw.size.x # Dynamically get actual screen width to fix offset issues
    screen_h = draw.size.y # Dynamically get actual screen height for scrolling
    mid_x = screen_w // 2 # Calculate true mathematical center of the screen
    
    char_limit = (mid_x - 8) // 8 # Calculate max characters based on dynamic pane width
    max_items = (screen_h - 38) // 12 # Calculate max visible items safely between top and bottom cyan bars
    
    if _is_help_screen: # Check if the help screen flag is active
        draw.text(Vector(10, 10), "PicoCommander Help", TFT_WHITE) # Draw title text
        draw.text(Vector(10, 30), "Up/Down: Scroll", TFT_WHITE) # Draw control instructions
        draw.text(Vector(10, 40), "Left/Right: Switch Pane", TFT_WHITE) # Draw control instructions
        draw.text(Vector(10, 50), "Center: Enter/Menu", TFT_WHITE) # Draw control instructions
        draw.text(Vector(10, screen_h - 40), "made by Slasher006", TFT_WHITE) # Draw required creator credits dynamically positioned
        draw.text(Vector(10, screen_h - 30), "with the help of Gemini", TFT_WHITE) # Draw required AI credits dynamically positioned
        draw.text(Vector(10, screen_h - 20), "Date: 2026-03-03", TFT_WHITE) # Draw required current date dynamically positioned
        draw.swap() # Swap the framebuffer to display the changes
        return # Exit drawing early for help screen

    if _confirm_menu is not None: # Check if the safeguard confirmation menu is active
        _confirm_menu.draw() # Render the confirmation menu full-screen
        draw.swap() # Swap the framebuffer to display the menu immediately
        return # Exit drawing early to completely skip rendering background panes, massively saving CPU and RAM

    if _context_menu is not None: # Check if the context menu object is currently active
        _context_menu.draw() # Call the official Picoware SDK draw method to render the full-screen menu
        draw.swap() # Swap the framebuffer to display the menu immediately
        return # Exit drawing early to completely skip rendering background panes, massively saving CPU and RAM

    draw.fill_rectangle(Vector(0, 0), Vector(screen_w, 12), TFT_CYAN) # Draw top classic MC cyan menu bar
    draw.text(Vector(2, 2), " Left    File    Command    Options    Right", TFT_BLACK) # Draw classic top menu text in black

    draw.fill_rectangle(Vector(mid_x, 12), Vector(1, screen_h - 24), TFT_CYAN) # Draw a 1px vertical cyan line down the true middle

    if _app_state["active_pane"] == "left": # Check if left pane is currently active
        draw.fill_rectangle(Vector(0, 12), Vector(mid_x, 12), TFT_CYAN) # Draw cyan highlight behind active path header
    draw.text(Vector(2, 14), _app_state["left_path"][:char_limit], TFT_BLACK if _app_state["active_pane"] == "left" else TFT_WHITE) # Draw left path safely truncated
    left_start = max(0, _app_state["left_index"] - (max_items - 1)) # Calculate dynamic scrolling offset
    y_offset = 26 # Set starting Y offset for left files below the header
    for i, item_data in enumerate(_app_state["left_files"][left_start : left_start + max_items]): # Slice array dynamically, saving RAM
        f_name, is_dir = item_data # Unpack the tuple
        actual_idx = i + left_start # Calculate the true index of the item being drawn
        display_name = "/" + f_name if is_dir else f_name # Prepend slash visually to match MC directory style
        base_color = TFT_YELLOW if is_dir else TFT_WHITE # Use yellow for folders, white for files
        text_color = base_color if _app_state["active_pane"] == "right" or actual_idx != _app_state["left_index"] else TFT_BLACK # Invert text color if selected
        if _app_state["active_pane"] == "left" and actual_idx == _app_state["left_index"]: # If this is the active item
            draw.fill_rectangle(Vector(0, y_offset-1), Vector(mid_x - 2, 10), TFT_CYAN) # Dynamic cyan highlight matching MC cursor
        draw.text(Vector(2, y_offset), display_name[:char_limit], text_color) # Draw dynamically truncated filename
        y_offset += 12 # Increment Y offset for next file
        
    if _app_state["active_pane"] == "right": # Check if right pane is currently active
        draw.fill_rectangle(Vector(mid_x + 1, 12), Vector(mid_x - 1, 12), TFT_CYAN) # Draw cyan highlight behind active path header
    draw.text(Vector(mid_x + 4, 14), _app_state["right_path"][:char_limit], TFT_BLACK if _app_state["active_pane"] == "right" else TFT_WHITE) # Draw right path safely truncated
    right_start = max(0, _app_state["right_index"] - (max_items - 1)) # Calculate dynamic scrolling offset
    y_offset = 26 # Reset Y offset for right pane files
    for i, item_data in enumerate(_app_state["right_files"][right_start : right_start + max_items]): # Slice array dynamically
        f_name, is_dir = item_data # Unpack the tuple
        actual_idx = i + right_start # Calculate the true index of the item being drawn
        display_name = "/" + f_name if is_dir else f_name # Prepend slash visually to match MC directory style
        base_color = TFT_YELLOW if is_dir else TFT_WHITE # Use yellow for folders, white for files
        text_color = base_color if _app_state["active_pane"] == "left" or actual_idx != _app_state["right_index"] else TFT_BLACK # Invert text color if selected
        if _app_state["active_pane"] == "right" and actual_idx == _app_state["right_index"]: # If this is the active item
            draw.fill_rectangle(Vector(mid_x + 2, y_offset-1), Vector(mid_x - 4, 10), TFT_CYAN) # Dynamic cyan highlight matching MC cursor
        draw.text(Vector(mid_x + 4, y_offset), display_name[:char_limit], text_color) # Draw dynamically truncated filename
        y_offset += 12 # Increment Y offset for next file

    draw.fill_rectangle(Vector(0, screen_h - 12), Vector(screen_w, 12), TFT_CYAN) # Draw bottom classic MC cyan shortcut bar
    draw.text(Vector(2, screen_h - 10), "1Help 3View 4Edit 5Copy 6RenMov 8Delete", TFT_BLACK) # Draw classic bottom shortcuts in black

    draw.swap() # Swap the framebuffer to push all drawing operations to the hardware display

def _auto_save(vm): # Function to handle deferred saving to protect SD card
    global _last_saved_json, _last_save_time # Access global save state variables
    current_time = time.time() # Get current system time
    if current_time - _last_save_time > 5: # Check if 5 seconds have passed (deferred timer)
        current_json = json.dumps({"left": _app_state["left_path"], "right": _app_state["right_path"]}) # Dump minimal state to JSON string
        if current_json != _last_saved_json: # Delta-check: only write if state changed to save SD card wear
            try: # Try block for file I/O
                vm.storage.write("picocmd_state.json", current_json, "w") # Write the JSON string to SD card using official SDK
                _last_saved_json = current_json # Update cached string to prevent redundant future writes
            except Exception: # Catch file system errors
                pass # Ignore errors silently to prevent crashes
        _last_save_time = current_time # Reset the deferred timer

def start(vm): # Required start function for ViewManager application lifecycle
    _init_state() # Initialize the RAM-efficient state dictionary
    _app_state["left_files"] = _load_dir(vm, _app_state["left_path"]) # Load initial left directory contents using SDK
    _app_state["right_files"] = _load_dir(vm, _app_state["right_path"]) # Load initial right directory contents using SDK
    gc.collect() # Force garbage collection after initial heavy string loading
    return True # Must return True to allow the application to launch successfully

def run(vm): # Required run function called continuously in the main firmware loop
    global _is_help_screen, _context_menu, _confirm_menu, _context_target_path, _pending_action # Access global state flags and variables
    
    input_mgr = vm.input_manager # Get the input manager from the view manager
    btn = input_mgr.button # Get the currently pressed button
    
    if _confirm_menu is not None: # If the safety confirmation menu is currently open
        if btn == BUTTON_BACK: # Check if BACK button is pressed
            input_mgr.reset() # Reset input state to prevent double-triggering
            _confirm_menu = None # Destroy the confirmation menu to cancel
            _pending_action = "" # Clear the pending action state
            gc.collect() # Aggressively free RAM from the destroyed menu
            
        elif btn == BUTTON_UP: # Check if UP button is pressed in confirmation menu
            input_mgr.reset() # Reset input state
            _confirm_menu.scroll_up() # Trigger SDK menu scroll up method
            
        elif btn == BUTTON_DOWN: # Check if DOWN button is pressed in confirmation menu
            input_mgr.reset() # Reset input state
            _confirm_menu.scroll_down() # Trigger SDK menu scroll down method
            
        elif btn == BUTTON_CENTER: # Check if CENTER button is pressed in confirmation menu
            input_mgr.reset() # Reset input state
            selection = _confirm_menu.current_item # Retrieve the currently highlighted Yes/No string
            
            if selection == "Yes": # If the user confirmed the action
                if _pending_action == "delete": # Verify the action we are confirming is a deletion
                    try: # Try block to handle file deletion
                        vm.storage.remove(_context_target_path) # Issue official SDK command to delete the target file
                        _app_state["left_files"] = _load_dir(vm, _app_state["left_path"]) # Refresh left pane to reflect deletion
                        _app_state["right_files"] = _load_dir(vm, _app_state["right_path"]) # Refresh right pane to reflect deletion
                    except Exception: # Catch deletion errors (e.g., file locked)
                        pass # Silently ignore to prevent crashes
                        
            _confirm_menu = None # Destroy the confirmation menu after processing
            _pending_action = "" # Clear pending action
            _context_target_path = "" # Clear target path string from RAM
            gc.collect() # Force immediate garbage collection after menu destruction

    elif _context_menu is not None: # If the standard context popup menu is currently open
        if btn == BUTTON_BACK: # Check if BACK button is pressed
            input_mgr.reset() # Reset input state to prevent double-triggering
            _context_menu = None # Destroy the menu object to close it
            gc.collect() # Aggressively free RAM from the destroyed menu
            
        elif btn == BUTTON_UP: # Check if UP button is pressed in menu
            input_mgr.reset() # Reset input state
            _context_menu.scroll_up() # Trigger SDK menu scroll up method
            
        elif btn == BUTTON_DOWN: # Check if DOWN button is pressed in menu
            input_mgr.reset() # Reset input state
            _context_menu.scroll_down() # Trigger SDK menu scroll down method
            
        elif btn == BUTTON_CENTER: # Check if CENTER button is pressed in menu
            input_mgr.reset() # Reset input state
            action = _context_menu.current_item # Retrieve the currently highlighted menu string
            
            if action == "Cancel": # If user selects Cancel
                pass # Do nothing, letting the block end to destroy the menu cleanly
                
            elif action == "Delete": # If user selects Delete
                screen_h = vm.draw.size.y # Dynamically fetch screen height to make confirmation full-screen
                _pending_action = "delete" # Set global state so the confirm menu knows what to execute
                _confirm_menu = Menu(vm.draw, "Confirm Delete?", 0, screen_h, TFT_WHITE, TFT_BLUE, selected_color=TFT_CYAN, border_color=TFT_CYAN, border_width=2) # Instantiate SDK Menu component themed for MC
                _confirm_menu.add_item("No") # Add No as the first/default option to prevent accidental double-taps
                _confirm_menu.add_item("Yes") # Add Yes as the confirmation option
                _confirm_menu.set_selected(0) # Default cursor to "No" for safety
                    
            elif action == "Execute": # If user selects Execute placeholder
                pass # Execution logic will be implemented in the next phase
                
            elif action == "Copy": # If user selects Copy placeholder
                pass # Chunked copying logic will be implemented in the next phase
                
            elif action == "Move": # If user selects Move placeholder
                pass # File moving logic will be implemented in the next phase
                
            _context_menu = None # Always destroy the context menu after an action is selected
            gc.collect() # Force immediate garbage collection after menu destruction

    elif btn == BUTTON_BACK: # Check if BACK button is pressed while menus are closed
        input_mgr.reset() # Reset input to avoid multiple triggerings
        if _is_help_screen: # If help screen is open
            _is_help_screen = False # Close help screen
        else: # If help screen is not open
            vm.back() # Exit the application using Picoware framework
            return # Exit run loop early
        
    elif btn == BUTTON_LEFT and _is_help_screen == False: # Check if Left directional button is pressed and help is closed
        input_mgr.reset() # Reset input state
        _app_state["active_pane"] = "left" # Switch system focus to left pane
        
    elif btn == BUTTON_RIGHT and _is_help_screen == False: # Check if Right directional button is pressed and help is closed
        input_mgr.reset() # Reset input state
        _app_state["active_pane"] = "right" # Switch system focus to right pane
        
    elif btn == BUTTON_UP and _is_help_screen == False: # Check if Up directional button is pressed and help is closed
        input_mgr.reset() # Reset input state
        pane = _app_state["active_pane"] # Get currently active pane string identifier
        idx_key = pane + "_index" # Construct dictionary key for the index variable
        if _app_state[idx_key] > 0: # Ensure we don't move the cursor out of upper bounds
            _app_state[idx_key] -= 1 # Decrement index to move graphical cursor up
        
    elif btn == BUTTON_DOWN and _is_help_screen == False: # Check if Down directional button is pressed and help is closed
        input_mgr.reset() # Reset input state
        pane = _app_state["active_pane"] # Get currently active pane string identifier
        idx_key = pane + "_index" # Construct dictionary key for the index variable
        files_key = pane + "_files" # Construct dictionary key for files list array
        if _app_state[idx_key] < len(_app_state[files_key]) - 1: # Ensure we don't exceed list length
            _app_state[idx_key] += 1 # Increment index to move graphical cursor down

    elif btn == BUTTON_CENTER and _is_help_screen == False: # Check if Center button is pressed and help is closed
        input_mgr.reset() # Reset input state
        pane = _app_state["active_pane"] # Get currently active pane string identifier
        path_key = pane + "_path" # Construct dictionary key for the path variable
        files_key = pane + "_files" # Construct dictionary key for files list array
        idx_key = pane + "_index" # Construct dictionary key for the index variable
        
        current_path = _app_state[path_key] # Get current path string
        
        if len(_app_state[files_key]) > 0: # Robustness check: Ensure directory is not completely empty to prevent IndexError
            selected_file, is_dir = _app_state[files_key][_app_state[idx_key]] # Unpack the string and boolean of the currently selected file
            
            if selected_file == "..": # If user selected the parent directory shortcut
                parts = current_path.rstrip("/").split("/") # Split the path string by slashes
                folder_exited = parts[-1] if len(parts) > 1 else "" # Capture the name of the folder we are leaving to restore cursor position
                parent = "/" + "/".join(parts[1:-1]) # Reconstruct the parent path string
                if parent == "//" or parent == "": # Catch edge cases for root reconstruction
                    parent = "/" # Hard reset to root if needed
                _app_state[path_key] = parent # Update state dictionary with new path
                
                new_file_list = _load_dir(vm, parent) # Load new directory contents into local variable
                _app_state[files_key] = new_file_list # Store new array in state
                
                new_cursor_idx = 0 # Default cursor to top of the list
                for i, item_data in enumerate(new_file_list): # Iterate through new list to find where we left off
                    if item_data[0] == folder_exited: # Check if this item is the folder we just exited
                        new_cursor_idx = i # Set index to the matched folder
                        break # Stop searching to save CPU cycles
                _app_state[idx_key] = new_cursor_idx # Restore cursor to the previous folder position
                
            else: # If user selected a standard file or folder
                new_path = "/" + selected_file if current_path == "/" else current_path + "/" + selected_file # Safely construct new absolute path
                if is_dir: # Check if the item is a directory using the boolean we saved earlier
                    _app_state[path_key] = new_path # Update state dictionary with new directory path
                    _app_state[files_key] = _load_dir(vm, new_path) # Load new directory contents
                    _app_state[idx_key] = 0 # Reset cursor to the top for the newly entered directory
                else: # If item is a file instead of a directory
                    screen_h = vm.draw.size.y # Dynamically fetch screen height to make menu full-screen
                    _context_target_path = new_path # Save the targeted file path to the global variable
                    _context_menu = Menu(vm.draw, selected_file[:14], 0, screen_h, TFT_WHITE, TFT_BLUE, selected_color=TFT_CYAN, border_color=TFT_CYAN, border_width=2) # Instantiate SDK Menu component themed for MC
                    _context_menu.add_item("Execute") # Add placeholder execute action
                    _context_menu.add_item("Copy") # Add placeholder copy action
                    _context_menu.add_item("Move") # Add placeholder move action
                    _context_menu.add_item("Delete") # Add active delete action
                    _context_menu.add_item("Cancel") # Add active cancel action
                    _context_menu.set_selected(0) # Default cursor to the top of the menu

    elif btn == BUTTON_UP and _is_help_screen == True: # Hidden catch for opening help if up is pressed while in help (for testing toggle)
        _is_help_screen = False # Failsafe close

    _draw_ui(vm) # Call UI rendering function to update screen
    _auto_save(vm) # Call deferred auto-save function to evaluate delta changes
    gc.collect() # Periodically clean up leftover objects in RAM during the run loop

def stop(vm): # Required stop function for total application cleanup
    global _app_state, _last_saved_json, _context_menu, _confirm_menu, _pending_action # Access global state variables
    _app_state.clear() # Clear state dictionary heavily to free RAM usage
    _app_state = None # Remove reference completely to allow garbage collection
    _last_saved_json = None # Free string memory used for delta caching
    _context_menu = None # Guarantee context menu object is destroyed
    _confirm_menu = None # Guarantee confirm menu object is destroyed
    _pending_action = "" # Clear pending string
    gc.collect() # Perform final aggressive garbage collection before exit

# add this at the bottom of your app for testing
from picoware.system.view_manager import ViewManager
from picoware.system.view import View

vm = None

try:
    vm = ViewManager()
    vm.add(
        View(
            "app_tester",
            run,
            start,
            stop,
        )
    )
    vm.switch_to("app_tester")
    while True:
        vm.run()
except Exception as e:
    print("Error during testing:", e)
finally:
    del vm
    vm = None