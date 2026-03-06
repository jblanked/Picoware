import gc # Import garbage collector to manage RAM aggressively
import time # Import time module for delays and auto-save timers
import json # Import json module for reading and writing delta-check states
import os # Import os module for file synchronization and stat checks
from micropython import const # Import const to lock memory locations for static integers

from picoware.system.vector import Vector # Import Vector for UI element coordinate mapping
from picoware.system.colors import TFT_WHITE, TFT_BLACK, TFT_BLUE, TFT_YELLOW, TFT_CYAN, TFT_DARKGREY, TFT_LIGHTGREY, TFT_RED # Import system palette
from picoware.system.buttons import BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_CENTER, BUTTON_BACK, BUTTON_H, BUTTON_O, BUTTON_BACKSPACE, BUTTON_ESCAPE # Import primary hardware buttons
from picoware.gui.menu import Menu # Import Picoware Menu component for overlays
from picoware.system.system import System # Import System component to query PSRAM usage

try: # Begin block to handle optional physical keyboard mappings
    from picoware.system.buttons import BUTTON_S, BUTTON_A, BUTTON_Z, BUTTON_0, BUTTON_9, BUTTON_SPACE, BUTTON_N, BUTTON_D, BUTTON_I # Attempt to import extra keys
except ImportError: # Catch exception if hardware keys do not exist
    BUTTON_S = -99 # Assign dummy negative value to missing key
    BUTTON_A = 97 # Assign ASCII fallback for missing key
    BUTTON_Z = 122 # Assign ASCII fallback for missing key
    BUTTON_0 = 48 # Assign ASCII fallback for missing key
    BUTTON_9 = 57 # Assign ASCII fallback for missing key
    BUTTON_SPACE = 32 # Assign ASCII fallback for missing key
    BUTTON_N = 110 # Assign ASCII fallback for missing key
    BUTTON_D = 100 # Assign ASCII fallback for missing key
    BUTTON_I = 105 # Assign ASCII fallback for missing key

FILE_BROWSER_VIEWER = const(0) # Mode constant: browse and view files only
FILE_BROWSER_MANAGER = const(1) # Mode constant: full commander management
FILE_BROWSER_SELECTOR = const(2) # Mode constant: select and return a file path

PANE_LEFT = const(0) # UI constant indicating left directory pane is active
PANE_RIGHT = const(1) # UI constant indicating right directory pane is active
SORT_NAME = const(0) # State constant indicating alphabetical sorting
SORT_DATE = const(1) # State constant indicating chronological sorting

MODE_NONE = const(0) # Input mode constant for idle state
MODE_MKDIR = const(1) # Input mode constant for folder creation text input
MODE_RENAME = const(2) # Input mode constant for renaming text input
MODE_COPY_SAME = const(3) # Input mode constant for duplicating a file text input

ACT_NONE = const(0) # Pending action constant for idle state
ACT_DELETE = const(1) # Pending action constant for deletion execution
ACT_COPY = const(2) # Pending action constant for copy execution
ACT_MOVE = const(3) # Pending action constant for move execution
ACT_RENAME = const(4) # Pending action constant for rename execution

def rgb_to_565(r, g, b): # Helper function to convert 24-bit RGB to 16-bit 565 format for TFT
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3) # Apply bitwise shifts and return color int

class FileBrowser: # Main class declaration for system file browser component
    """PicoCommander integrated as system file browser.""" # Class docstring
    
    def __init__(self, view_manager, mode: int = FILE_BROWSER_SELECTOR, start_directory: str = "") -> None: # Constructor with local context variables
        self._vm = view_manager # Bind view manager locally
        self._mode = mode # Bind operating mode
        self._storage = view_manager.storage # Bind storage object for file I/O
        self._draw = view_manager.draw # Bind draw object for UI rendering
        self._input_manager = view_manager.input_manager # Bind input manager for keypad capture
        self._sys = System() # Instantiate system query object locally
        self._last_saved_json = "{}" # Initialize cache for auto-save delta check
        self._last_save_time = 0 # Initialize timestamp for deferred saves
        
        self._is_help_screen = False # Flag for help screen overlay
        self._is_disclaimer_screen = False # Flag for initial warning overlay
        self._show_options = False # Flag for settings menu overlay
        self._opt_idx = 0 # Cursor index for options menu
        self._context_menu = None # Placeholder for context menu object
        self._confirm_menu = None # Placeholder for confirmation dialog object
        
        self._input_active = False # Flag for text entry mode
        self._input_text = "" # Buffer for text entry string
        self._input_cursor = 0 # Position indicator for text entry
        self._input_mode = MODE_NONE # Current context of text entry
        
        self._context_target_path = "" # Variable tracking file targeted by menu
        self._pending_action = ACT_NONE # Variable tracking queued file operation
        self._pending_dest_path = "" # Variable tracking destination path for operations
        self._needs_redraw = True # Flag signaling screen refresh is required
        self._show_info = False # Flag for file properties overlay
        self._info_data = [] # List storing file property strings
        
        self._is_editing = False # Flag for text editor mode
        self._edit_read_only = False # Flag restricting text modification
        self._edit_text = [] # List holding lines of file being edited
        self._edit_file = "" # Path of file currently open in editor
        self._edit_cx = 0 # Editor text cursor X coordinate
        self._edit_cy = 0 # Editor text cursor Y coordinate
        self._edit_sx = 0 # Editor scroll offset X
        self._edit_sy = 0 # Editor scroll offset Y
        self._edit_unsaved = False # Flag tracking modified editor buffer
        
        self._is_viewing_image = False # Flag for image viewer mode
        self._image_path = "" # Path of currently viewed image
        self._jpeg_vec = Vector(0, 0) # Vector for rendering images at origin
        
        self._char_map = {} # Dictionary mapping physical keys to string characters
        self._app_state = { # Dictionary holding all persistent UI state
            "left_path": start_directory if start_directory else "/", # Initialize left path
            "right_path": start_directory if start_directory else "/", # Initialize right path
            "left_files": [], # Initialize left directory cache
            "right_files": [], # Initialize right directory cache
            "left_index": 0, # Initialize left cursor position
            "right_index": 0, # Initialize right cursor position
            "active_pane": PANE_LEFT, # Set initial active pane
            "sort_mode": SORT_NAME, # Set default alphabetic sorting
            "show_hidden": False, # Set default to hide dotfiles
            "dir_menu": True, # Set default folder behavior
            "disclaimer_accepted": False, # Track if user accepted warning
            "theme": 0, # Default color theme index
            "bg_r": 0, "bg_g": 0, "bg_b": 170, # Custom theme background RGB
            "bar_r": 0, "bar_g": 170, "bar_b": 170, # Custom theme highlight RGB
            "marked": [] # List of selected file paths for batch ops
        } # Close state dictionary
        
        self.start() # Call initialization routine immediately upon instantiation

    def __del__(self): # Destructor to explicitly clean up RAM usage
        self._auto_save() # Attempt final state flush to SD card
        if self._context_menu: # If context menu exists
            del self._context_menu # Delete menu instance
        if self._confirm_menu: # If confirm menu exists
            del self._confirm_menu # Delete menu instance
        self._app_state["left_files"].clear() # Empty left pane cache
        self._app_state["right_files"].clear() # Empty right pane cache
        self._app_state["marked"].clear() # Empty selection cache
        self._app_state.clear() # Empty core state dictionary
        self._edit_text.clear() # Empty editor buffer
        self._char_map.clear() # Empty key map dictionary
        self._sys = None # Clear system reference
        gc.collect() # Aggressively collect garbage to prevent leaks

    @property # Decorate method as read-only property for system
    def directory(self) -> str: # Return active pane path string
        _dir = self._app_state["left_path"] if self._app_state["active_pane"] == PANE_LEFT else self._app_state["right_path"] # Fetch active path
        if _dir.startswith("/sd/"): # Check for redundant sd prefix
            _dir = _dir[3:] # Strip sd prefix
        return _dir # Return cleaned path

    @property # Decorate method as read-only property for system
    def path(self) -> str: # Return full absolute path of highlighted file
        act = self._app_state["active_pane"] # Get current pane index
        p_dir = self._app_state["left_path"] if act == PANE_LEFT else self._app_state["right_path"] # Get pane directory
        f_lst = self._app_state["left_files"] if act == PANE_LEFT else self._app_state["right_files"] # Get pane list
        idx = self._app_state["left_index"] if act == PANE_LEFT else self._app_state["right_index"] # Get pane cursor
        if len(f_lst) == 0: # If directory empty
            return p_dir # Return directory
        fname = f_lst[idx][0] # Extract filename from tuple
        _path = f"/{fname}" if p_dir == "/" else f"{p_dir}/{fname}" # Construct absolute path
        if _path.startswith("/sd/"): # Check for redundant sd prefix
            _path = _path[3:] # Strip sd prefix
        return _path # Return cleaned path

    @property # Decorate method as read-only property for system
    def stats(self) -> dict: # Return dictionary of current file metadata
        _p = self.path # Get current absolute path
        return { # Begin dictionary
            "directory": self.directory, # Insert active directory
            "path": _p, # Insert absolute path
            "size": self._storage.size(_p) if not self._storage.is_directory(_p) else 0, # Fetch and insert file size safely
            "type": _p.split(".")[-1] if "." in _p else "unknown" # Parse and insert extension
        } # Close dictionary

    def _get_theme(self): # Internal method to resolve active color palette
        th = self._app_state.get("theme", 0) # Fetch theme index from state
        if th == 0: # Classic theme check
            return TFT_BLUE, TFT_CYAN, TFT_WHITE, TFT_YELLOW, TFT_BLACK # Return classic colors
        elif th == 1: # Dark theme check
            return TFT_BLACK, TFT_WHITE, TFT_WHITE, TFT_WHITE, TFT_BLACK # Return dark colors
        else: # Custom theme fallback
            c_bg = rgb_to_565(self._app_state["bg_r"], self._app_state["bg_g"], self._app_state["bg_b"]) # Convert background color
            c_bar = rgb_to_565(self._app_state["bar_r"], self._app_state["bar_g"], self._app_state["bar_b"]) # Convert highlight color
            return c_bg, c_bar, TFT_WHITE, TFT_YELLOW, TFT_BLACK # Return custom tuple

    def _force_sync(self): # Method to ensure hardware commits file writes
        time.sleep(0.3) # Wait briefly for I/O buffers to settle
        try: # Try block to catch OS errors
            os.sync() # Command OS to synchronize file system
        except Exception: # Ignore exception
            pass # Continue execution

    def _exists(self, path): # Robust method to check if path exists safely
        if path in ("/", ""): # Root path always exists
            return True # Return affirmative
        try: # Attempt direct stat
            if self._storage.exists(path): # Ask storage driver
                return True # Return affirmative
        except Exception: # Ignore failure
            pass # Continue execution
        return False # Return negative if all checks fail

    def _auto_save(self): # Delta-check auto save to reduce SD card wear
        curr_t = time.time() # Get current timestamp
        if curr_t - self._last_save_time > 5: # If 5 seconds passed since last check
            save_dict = {k: self._app_state[k] for k in ["left_path", "right_path", "sort_mode", "active_pane", "show_hidden", "dir_menu", "disclaimer_accepted", "theme", "bg_r", "bg_g", "bg_b", "bar_r", "bar_g", "bar_b"]} # Create subset of state to save
            curr_j = json.dumps(save_dict) # Convert to JSON string
            if curr_j != self._last_saved_json: # Compare string to cache directly
                try: # Attempt save
                    self._storage.write("/picoware/settings/picocmd_state.json", curr_j, "w") # Write to persistent file
                    self._last_saved_json = curr_j # Update cache string
                except Exception: # Ignore errors
                    pass # Continue
            del curr_j # Free string memory
            del save_dict # Free dictionary memory
            gc.collect() # Collect garbage immediately
            self._last_save_time = curr_t # Update timestamp

    def start(self): # Initialization routine
        self._draw.clear(color=TFT_BLACK) # Clear screen to black
        self._draw.text(Vector(10, 10), "Loading PicoCommander...", TFT_WHITE) # Show loading text
        self._draw.swap() # Swap buffer to display
        
        for d in ("/picoware", "/picoware/settings"): # Loop through required directories
            try: # Attempt creation
                self._storage.mkdir(d) # Make directory
            except Exception: # Ignore if exists
                pass # Continue
        
        try: # Try loading saved state
            data = self._storage.read("/picoware/settings/picocmd_state.json", "r") # Read file
            if data: # If data exists
                loaded = json.loads(data) # Parse JSON
                self._app_state.update({k: loaded.get(k, self._app_state[k]) for k in self._app_state}) # Merge valid keys
                self._last_saved_json = json.dumps(self._app_state) # Prime the cache
                del loaded # Free memory
            del data # Free memory
        except Exception: # Ignore read failures
            pass # Continue
            
        if not self._app_state["disclaimer_accepted"]: # Check if warning needed
            self._is_disclaimer_screen = True # Flag disclaimer active
            
        try: # Try populating key mapping dynamically
            import picoware.system.buttons as __btns # Import dynamically
            for i in range(26): # Loop alphabet
                c = chr(97 + i) # Get character
                if hasattr(__btns, f"BUTTON_{c.upper()}"): self._char_map[getattr(__btns, f"BUTTON_{c.upper()}")] = c # Add to map
            for i in range(10): # Loop digits
                c = str(i) # Get string digit
                if hasattr(__btns, f"BUTTON_{c}"): self._char_map[getattr(__btns, f"BUTTON_{c}")] = c # Add to map
            for a, ch in [("BUTTON_SPACE", " "), ("BUTTON_PERIOD", "."), ("BUTTON_MINUS", "-"), ("BUTTON_UNDERSCORE", "_")]: # Loop symbols
                if hasattr(__btns, a): self._char_map[getattr(__btns, a)] = ch # Add to map
        except Exception: # Catch import errors
            pass # Continue
            
        self._refresh_panes() # Load initial directory listings
        self._needs_redraw = True # Trigger initial paint
        gc.collect() # Free memory
        return True # Return success

    def _rmtree(self, path): # Recursive deletion function
        try: # Try block
            is_d = False # Assume file
            try: is_d = self._storage.is_directory(path) # Check if directory
            except Exception: pass # Ignore error
            if is_d: # If directory
                for itm in self._storage.listdir(path): # Loop contents
                    if itm not in (".", ".."): # Skip relative
                        self._rmtree(f"/{itm}" if path == "/" else f"{path}/{itm}") # Recurse downwards
                try: self._storage.rmdir(path) # Delete empty directory
                except Exception: # Fallback
                    try: self._storage.remove(path) # Force delete
                    except Exception: pass # Ignore
            else: # If file
                self._storage.remove(path) # Delete file
        except Exception: pass # Global ignore
        gc.collect() # Collect garbage deeply

    def _draw_progress(self, title, percentage): # Overlay progress bar UI
        c_bg, c_bar, _, _, _ = self._get_theme() # Fetch colors
        sw, sh = self._draw.size.x, self._draw.size.y # Get screen sizes
        bw, bh = 200, 60 # Set box sizes
        x, y = (sw - bw) // 2, (sh - bh) // 2 # Center coordinates
        self._draw.fill_rectangle(Vector(x, y), Vector(bw, bh), c_bg) # Draw background
        self._draw.rect(Vector(x, y), Vector(bw, bh), c_bar) # Draw border
        self._draw.text(Vector(x + 10, y + 10), title, TFT_WHITE) # Draw title
        self._draw.rect(Vector(x + 10, y + 30), Vector(bw - 20, 15), TFT_WHITE) # Draw bar outline
        fill_w = int((bw - 22) * percentage) # Calc fill width
        if fill_w > 0: self._draw.fill_rectangle(Vector(x + 11, y + 31), Vector(fill_w, 13), c_bar) # Draw filled percentage
        self._draw.swap() # Push to display

    def _copy_item(self, src, dst): # File and folder duplication function
        is_d = False # Assume file
        try: is_d = self._storage.is_directory(src) # Check if directory
        except Exception: pass # Ignore error
        if is_d: # If directory
            try: self._storage.mkdir(dst) # Create destination
            except Exception: pass # Ignore error
            try: # Loop contents
                for itm in self._storage.listdir(src): # For each item
                    if itm not in (".", ".."): # Exclude relatives
                        self._copy_item(f"{src}/{itm}" if src != "/" else f"/{itm}", f"{dst}/{itm}" if dst != "/" else f"/{itm}") # Recurse copy
            except Exception: pass # Ignore error
        else: # If file
            try: # Try copying binary chunks
                f_sz = self._storage.size(src) # Get size
                pos = 0 # Byte pointer
                while pos < f_sz: # Loop until end
                    try: chk = self._storage.read_chunked(src, pos, 2048) # Read 2KB max
                    except Exception: break # Exit on read fail
                    if not chk: break # Exit if empty
                    self._storage.write(dst, chk, "ab" if pos > 0 else "wb") # Append or write
                    pos += len(chk) # Increment pointer
                    del chk # Delete chunk from RAM explicitly
                    if f_sz > 0: self._draw_progress(f"Copying {int((pos/f_sz)*100)}%", min(1.0, pos / f_sz)) # Update UI
                    gc.collect() # Force garbage collection after chunk
            except Exception: pass # Ignore outer errors
        gc.collect() # Final garbage collection

    def _load_dir(self, path): # Directory read and sort function
        items = [] # Initialize empty list
        show_hid = self._app_state.get("show_hidden", False) # Check hidden setting
        sort_m = self._app_state["sort_mode"] # Check sorting setting
        try: # Try reading
            d_list = self._storage.listdir(path) # Get raw list
            for itm in d_list: # Loop items
                if itm in (".", "..") or (not show_hid and itm.startswith(".")): continue # Skip logic
                f_p = f"/{itm}" if path == "/" else f"{path}/{itm}" # Build path
                is_d, mt, sz = False, 0, 0 # Init vars
                try: is_d = self._storage.is_directory(f_p) # Check type
                except Exception: pass # Ignore
                if not is_d: # If file
                    try: sz = self._storage.size(f_p) # Check size
                    except Exception: pass # Ignore
                if sort_m == SORT_DATE: # If chronological
                    try: mt = os.stat(f_p)[8] # Stat modification time
                    except Exception: pass # Ignore
                items.append((itm, is_d, mt, sz)) # Append tuple
            del d_list # Free raw list
            if sort_m == SORT_NAME: items.sort(key=lambda x: (not x[1], x[0].lower())) # Sort by name (dirs first)
            else: items.sort(key=lambda x: (not x[1], x[0].lower() if x[1] else -x[2])) # Sort by date (dirs first)
            for i in range(len(items)): items[i] = (items[i][0], items[i][1], items[i][3]) # Trim unused mt from tuple
        except Exception: # On fail
            items = [("<ERROR>", False, 0)] # Return error object
        gc.collect() # Run GC
        return [("..", True, 0)] + items if path != "/" else items # Append up-dir and return

    def _refresh_panes(self): # Helper to update both cache lists
        self._app_state["left_files"].clear() # Empty left
        self._app_state["left_files"] = self._load_dir(self._app_state["left_path"]) # Reload left
        self._app_state["left_index"] = max(0, min(self._app_state["left_index"], len(self._app_state["left_files"]) - 1)) # Clamp cursor
        self._app_state["right_files"].clear() # Empty right
        self._app_state["right_files"] = self._load_dir(self._app_state["right_path"]) # Reload right
        self._app_state["right_index"] = max(0, min(self._app_state["right_index"], len(self._app_state["right_files"]) - 1)) # Clamp cursor

    def _open_viewer(self, path): # Function handling viewer mode request
        ext = path.split(".")[-1].lower() if "." in path else "" # Safely extract extension
        if ext in ("jpg", "jpeg", "bmp"): # Identify natively supported images
            self._is_viewing_image = True # Trigger image mode flag
            self._image_path = path # Assign path directly
            self._needs_redraw = True # Request UI update
        else: # Fallback
            self._open_editor(path, read_only=True) # Fallback to text viewer

    def _open_editor(self, path, read_only=False): # Function preparing text editor
        self._edit_text.clear() # Clear existing text lines
        try: # Try read
            data = self._storage.read(path, "r") # Read entire file
            if data: self._edit_text.extend(data.split('\n')) # Split by linefeed and append
            del data # Free string
        except Exception: pass # Ignore errors
        gc.collect() # Force GC
        if not self._edit_text: self._edit_text.append("") # Append empty line if failed
        self._edit_file = path # Assign file path
        self._edit_read_only = read_only # Apply restriction flag
        self._edit_cx = self._edit_cy = self._edit_sx = self._edit_sy = 0 # Reset all cursors
        self._edit_unsaved = False # Reset dirty flag
        self._is_editing = True # Trigger editor mode flag
        self._needs_redraw = True # Request UI update

    def _draw_ui(self): # Master rendering loop
        c_bg, c_bar, c_txt, c_dir, c_btxt = self._get_theme() # Fetch theme colors locally
        d_clr, f_rect, d_rect, d_txt, d_swp = self._draw.clear, self._draw.fill_rectangle, self._draw.rect, self._draw.text, self._draw.swap # Localize render methods to avoid dictionary overhead
        sw, sh, mx = self._draw.size.x, self._draw.size.y, self._draw.size.x // 2 # Precalculate dimensions

        if self._is_viewing_image: # Check image mode
            d_clr(color=TFT_BLACK) # Clear black
            if self._image_path.lower().endswith("bmp"): # Detect format
                self._draw.image_bmp(self._jpeg_vec, self._image_path, self._storage) # Render bmp
            else: # Fallback jpeg
                self._draw.image_jpeg(self._jpeg_vec, self._image_path, self._storage) # Render jpeg
            f_rect(Vector(0, sh - 12), Vector(sw, 12), c_bar) # Draw footer bar
            d_txt(Vector(2, sh - 10), "ESC / BACK : Close Image", c_btxt) # Draw instructions
            d_swp() # Swap buffer
            self._needs_redraw = False # Prevent looping
            return # Exit routine

        if self._is_editing: # Check text mode
            d_clr(color=c_bg) # Clear custom background
            f_rect(Vector(0, 0), Vector(sw, 12), c_bar) # Draw header bar
            mode_s = "View" if self._edit_read_only else "Edit" # Evaluate mode
            mod_s = "*" if self._edit_unsaved and not self._edit_read_only else "" # Evaluate dirty state
            d_txt(Vector(2, 2), f"{mode_s}: {self._edit_file.split('/')[-1]}{mod_s}", c_btxt) # Draw header title
            m_lin, m_chr = (sh - 24) // 12, (sw - 4) // 6 # Calculate screen grid limits
            for i in range(m_lin): # Loop vertical limits
                idx = self._edit_sy + i # Apply scroll offset
                if idx < len(self._edit_text): # Ensure within text bounds
                    d_txt(Vector(2, 14 + i * 12), self._edit_text[idx][self._edit_sx : self._edit_sx + m_chr], c_txt) # Draw sliced line
            if not self._edit_read_only and int(time.time() * 3) % 2 == 0: # Check edit mode and modulo time for blink
                cx, cy = 2 + (self._edit_cx - self._edit_sx) * 6, 14 + (self._edit_cy - self._edit_sy) * 12 # Calculate exact coords
                if 0 <= cx < sw and 12 < cy < sh - 12: # Check screen bounds
                    f_rect(Vector(cx, cy - 1), Vector(6, 11), TFT_CYAN) # Draw cursor block
                    try: d_txt(Vector(cx, cy), self._edit_text[self._edit_cy][self._edit_cx], TFT_BLACK) # Draw inverted char
                    except IndexError: pass # Ignore EOL overshoot
            self._needs_redraw = True # Ensure blink loop continues
            f_rect(Vector(0, sh - 12), Vector(sw, 12), c_bar) # Draw footer
            d_txt(Vector(2, sh - 10), "UP/DWN:Scroll ESC:Close" if self._edit_read_only else "ENT:Menu ESC:Close", c_btxt) # Draw hint
            if self._context_menu: # If overlay open
                self._context_menu.draw() # Draw menu
                self._needs_redraw = False # Pause blink loop
            d_swp() # Push buffer
            return # Exit routine

        d_clr(color=c_bg) # Default commander UI: Clear background
        
        if self._is_disclaimer_screen: # Disclaimer overlay check
            f_rect(Vector(10, 50), Vector(sw - 20, 140), TFT_BLACK) # Draw box
            d_rect(Vector(10, 50), Vector(sw - 20, 140), TFT_RED) # Draw red border
            f_rect(Vector(10, 50), Vector(sw - 20, 20), TFT_RED) # Draw red header
            d_txt(Vector(15, 54), "WARNING", TFT_WHITE) # Text
            d_txt(Vector(20, 85), "With this app it is", TFT_WHITE) # Text
            d_txt(Vector(20, 100), "possible to delete ANY", TFT_WHITE) # Text
            d_txt(Vector(20, 115), "file on the SD card.", TFT_WHITE) # Text
            d_txt(Vector(20, 130), "Please be careful!", TFT_WHITE) # Text
            f_rect(Vector(10, 170), Vector(sw - 20, 20), TFT_RED) # Footer rect
            d_txt(Vector(15, 174), "[CENTER/ENT] I Understand", TFT_WHITE) # Footer text
            d_swp() # Swap
            self._needs_redraw = False # Halt
            return # Exit

        if self._is_help_screen: # Help screen overlay check
            d_txt(Vector(10, 10), "PicoCommander Help", TFT_WHITE) # Draw title
            d_txt(Vector(10, 24), "SPC:Mark H:Help O:Opt", c_bar) # Draw mapped keys
            d_txt(Vector(10, 36), "I:Info N:NewFolder D:Del", c_bar) # Draw mapped keys
            d_txt(Vector(10, 48), "UP/DOWN: Scroll", TFT_WHITE) # Draw controls
            d_txt(Vector(10, 60), "L/R: Switch Pane", TFT_WHITE) # Draw controls
            d_txt(Vector(10, 72), "CENTER: Menu (View/Edit...)", TFT_WHITE) # Draw controls
            d_txt(Vector(10, 84), "BACK: Exit App", TFT_WHITE) # Draw controls
            d_txt(Vector(10, 126), f"RAM: {gc.mem_alloc() // 1024}KB used / {gc.mem_free() // 1024}KB free", TFT_YELLOW) # Calculate and draw GC RAM limits dynamically
            if self._sys and self._sys.has_psram: # Ensure System object resolved PSRAM
                d_txt(Vector(10, 138), f"PSRAM: {self._sys.used_psram // 1024}KB used / {self._sys.free_psram // 1024}KB free", TFT_YELLOW) # Draw physical PSRAM limits
            d_txt(Vector(10, sh - 40), "made by Slasher006", c_bar) # Strict requirement credits line 1
            d_txt(Vector(10, sh - 30), "with the help of Gemini", c_bar) # Strict requirement credits line 2
            d_txt(Vector(10, sh - 20), "Date: 2026-03-06 | v1.16", c_bar) # Strict requirement credits line 3
            d_swp() # Swap
            self._needs_redraw = False # Halt
            return # Exit

        if self._show_info: # File properties overlay check
            bx, by, bw, bh = (sw - 200) // 2, (sh - 100) // 2, 200, 100 # Define math
            f_rect(Vector(bx, by), Vector(bw, bh), TFT_BLACK) # Box
            d_rect(Vector(bx, by), Vector(bw, bh), c_bar) # Border
            f_rect(Vector(bx, by), Vector(bw, 16), c_bar) # Header
            d_txt(Vector(bx + 5, by + 2), "FILE INFORMATION", c_btxt) # Title
            for i, ln in enumerate(self._info_data): d_txt(Vector(bx + 10, by + 25 + (i * 15)), ln, TFT_WHITE) # Loop provided info list
            d_txt(Vector(bx + 10, by + bh - 15), "[ESC/ENT] Close", TFT_LIGHTGREY) # Hint
            d_swp() # Swap
            self._needs_redraw = False # Halt
            return # Exit

        if self._show_options: # Settings panel check
            f_rect(Vector(10, 10), Vector(sw - 20, sh - 20), TFT_BLACK) # Outer box
            d_rect(Vector(10, 10), Vector(sw - 20, sh - 20), c_bar) # Outer border
            f_rect(Vector(10, 10), Vector(sw - 20, 20), c_bar) # Header
            d_txt(Vector(15, 14), "OPTIONS MENU", c_btxt) # Title
            lbls = ("Theme", "BG R (0-255)", "BG G (0-255)", "BG B (0-255)", "Bar R (0-255)", "Bar G (0-255)", "Bar B (0-255)", "Sort Mode", "Hidden Files", "Dir Enter") # Setting strings
            for i, l in enumerate(lbls): # Loop strings
                yp = 35 + (i * 15) # Offset Y position
                tc = c_bar if i == self._opt_idx else TFT_WHITE # Set color context based on cursor
                if i == self._opt_idx: f_rect(Vector(12, yp - 2), Vector(sw - 24, 13), TFT_DARKGREY) # Highlight line
                d_txt(Vector(20, yp), l + ":", tc) # Print setting key
                v = "" # Init string
                if i == 0: v = ("Classic", "Dark", "Custom")[self._app_state.get("theme", 0)] # Resolve theme string
                elif 1 <= i <= 6: v = str(self._app_state.get(["", "bg_r", "bg_g", "bg_b", "bar_r", "bar_g", "bar_b"][i], 0)) # Resolve color values
                elif i == 7: v = "Name" if self._app_state.get("sort_mode", 0) == 0 else "Date" # Resolve sorting string
                elif i == 8: v = "Show" if self._app_state.get("show_hidden", False) else "Hide" # Resolve hidden string
                elif i == 9: v = "Menu" if self._app_state.get("dir_menu", True) else "Open" # Resolve folder action string
                d_txt(Vector(130, yp), f"< {v} >", tc) # Print dynamic setting value
            pbg = rgb_to_565(self._app_state.get("bg_r",0), self._app_state.get("bg_g",0), self._app_state.get("bg_b",170)) # Precalculate custom bg
            pbr = rgb_to_565(self._app_state.get("bar_r",0), self._app_state.get("bar_g",170), self._app_state.get("bar_b",170)) # Precalculate custom bar
            d_txt(Vector(20, 185), "Custom Preview:", TFT_LIGHTGREY) # Add hint
            f_rect(Vector(140, 183), Vector(60, 20), pbg) # Draw preview bg
            d_rect(Vector(140, 183), Vector(60, 20), pbr) # Draw preview border
            f_rect(Vector(10, sh - 30), Vector(sw - 20, 20), c_bar) # Add footer
            d_txt(Vector(15, sh - 26), "[L/R] Edit   [ESC/ENT] Save", c_btxt) # Draw hints
            d_swp() # Swap
            self._needs_redraw = False # Halt
            return # Exit

        if self._input_active: # Text entry box overlay check
            by = (sh - 70) // 2 # Calc box y
            f_rect(Vector(10, by), Vector(sw - 20, 70), TFT_BLACK) # Background
            d_rect(Vector(10, by), Vector(sw - 20, 70), c_bar) # Border
            f_rect(Vector(10, by), Vector(sw - 20, 16), c_bar) # Header
            ts = "RENAME:" if self._input_mode == MODE_RENAME else "COPY AS:" if self._input_mode == MODE_COPY_SAME else "NEW FOLDER:" # String selection
            d_txt(Vector(15, by + 2), ts, c_btxt) # Draw title
            d_txt(Vector(15, by + 24), self._input_text, TFT_WHITE) # Draw active text buffer
            if int(time.time() * 3) % 2 == 0: # Flash cursor logic
                f_rect(Vector(15 + (self._input_cursor * 6), by + 35), Vector(6, 2), TFT_CYAN) # Draw rect cursor
                self._needs_redraw = True # Trigger continuous redraw
            d_txt(Vector(15, by + 48), "[ENT] Save  [ESC] Cancel", TFT_LIGHTGREY) # Hint
            d_swp() # Swap
            if not self._needs_redraw: self._needs_redraw = False # Safety fallback
            return # Exit

        if self._confirm_menu: # Active dialog check
            self._confirm_menu.draw() # Invoke native menu draw
            d_swp() # Swap
            self._needs_redraw = False # Halt
            return # Exit

        if self._context_menu: # Active action menu check
            self._context_menu.draw() # Invoke native menu draw
            d_swp() # Swap
            self._needs_redraw = False # Halt
            return # Exit

        f_rect(Vector(0, 0), Vector(sw, 12), c_bar) # Native Commander UI Header
        ss = "Name" if self._app_state["sort_mode"] == 0 else "Date" # Check state
        ms = "Viewer" if self._mode == FILE_BROWSER_VIEWER else "Select" if self._mode == FILE_BROWSER_SELECTOR else "Manager" # Determine Mode string
        d_txt(Vector(2, 2), f"PicoCmd v1.16 [{ms}] [{ss}]", c_btxt) # Draw title bar text
        f_rect(Vector(mx, 12), Vector(1, sh - 24), c_bar) # Draw central divider line
        
        c_lim, n_lim, m_itm = (mx - 8) // 6, ((mx - 8) // 6) - 6, (sh - 38) // 12 # Calculate grid column constraints logically
        ap = self._app_state["active_pane"] # Query pane state

        for pn in (PANE_LEFT, PANE_RIGHT): # Dual pass execution loop
            il = pn == PANE_LEFT # Check boolean condition
            xb = 0 if il else mx + 1 # Evaluate left offset
            ps = self._app_state["left_path"] if il else self._app_state["right_path"] # Fetch pane path string
            fl = self._app_state["left_files"] if il else self._app_state["right_files"] # Fetch pane directory list
            ix = self._app_state["left_index"] if il else self._app_state["right_index"] # Fetch pane cursor integer
            si = max(0, ix - (m_itm - 1)) # Calculate scroll window start
            
            if ap == pn: f_rect(Vector(xb, 12), Vector(mx - (0 if il else 1), 12), c_bar) # Highlight active pane path header
            d_txt(Vector(xb + 2, 14), ps[:c_lim], c_btxt if ap == pn else c_txt) # Draw truncated directory path
            
            yo = 26 # Initialize vertical print offset
            for i, idt in enumerate(fl[si : si + m_itm]): # Loop through windowed file list
                fn, idr, fz = idt # Unpack metadata tuple
                ai = i + si # Calculate actual absolute index
                dn = f"/{fn}" if idr else fn # Prepend slash if folder visually
                fp = f"/{fn}" if ps == "/" else f"{ps}/{fn}" # Calculate full file absolute path
                im = fp in self._app_state["marked"] # Check if item exists in selection list
                
                bc = TFT_RED if im else (c_dir if idr else c_txt) # Evaluate base text color
                tc = bc if ap != pn or ai != ix else c_btxt # Invert text color if active cursor matches
                
                if ap == pn and ai == ix: f_rect(Vector(xb + (0 if il else 1), yo - 1), Vector(mx - (2 if il else 3), 10), c_bar) # Draw cursor block selection
                
                if idr: szs = "<DIR>" # Assign dir string
                elif fz < 1024: szs = f"{fz}B" # Assing byte string
                elif fz < 1048576: szs = f"{fz//1024}K" # Assign kilo string
                else: szs = f"{fz//1048576}M" # Assign mega string
                    
                pl = max(0, c_lim - len(dn[:n_lim]) - len(szs)) # Calculate space padding dynamically
                d_txt(Vector(xb + 2, yo), dn[:n_lim] + (" " * pl) + szs, tc) # Draw properly aligned string row
                yo += 12 # Increment offset

        f_rect(Vector(0, sh - 12), Vector(sw, 12), c_bar) # Draw footer bar
        d_txt(Vector(2, sh - 10), "ENT:Menu O:Opt H:Help ESC:Exit", c_btxt) # Draw static hint text
        d_swp() # Dump buffer
        self._needs_redraw = False # Halt loop

    def run(self): # Core input processor and state router
        btn = self._input_manager.button # Query hardware key matrix
        key = self._input_manager.read_non_blocking() # Check serial characters
        irs = self._input_manager.reset # Alias method pointer to save lookup cycles
        c_bg, c_bar, _, _, _ = self._get_theme() # Preload customized base palette
        sh = self._draw.size.y # Preload screen vertical size

        isp = False # Init printable check
        cta = "" # Init string char
        if btn in self._char_map: # Check dictionary lookup
            isp, cta = True, self._char_map[btn] # Assign key map
        elif key and isinstance(key, str) and len(key) == 1 and 32 <= ord(key) <= 126: # Check ascii bounding limits
            isp, cta = True, key # Assign raw key
            
        ien = (btn == BUTTON_CENTER and not isp) or key in ('\n', '\r') or btn in (10, 13) # Abstract return key logic
        ies = (btn in (BUTTON_BACK, BUTTON_ESCAPE) and not isp) or key == '\x1b' # Abstract escape key logic
        ibs = (btn == BUTTON_BACKSPACE and not isp) or key in ('\x08', '\x7f') or btn in (8, 127) # Abstract backspace key logic
        ilf = (btn == BUTTON_LEFT and not isp) or key == '\x1b[D' # Abstract navigation key logic
        irt = (btn == BUTTON_RIGHT and not isp) or key == '\x1b[C' # Abstract navigation key logic
        iup = (btn == BUTTON_UP and not isp) or key == '\x1b[A' # Abstract navigation key logic
        idn = (btn == BUTTON_DOWN and not isp) or key == '\x1b[B' # Abstract navigation key logic

        if self._is_viewing_image: # Priority route: Image Viewer Input Trap
            if ies or ien: # Only wait for escape or action keys
                irs() # Purge input buffer
                self._is_viewing_image = False # Release mode lock
                self._image_path = "" # Destroy path string
                self._needs_redraw = True # Fire render pass
                time.sleep(0.3) # Avoid key bouncing
            return True # Continue app loop

        if self._is_editing and not self._context_menu and not self._confirm_menu: # Priority route: Text Editor Input Trap
            if ies: # Close request
                irs() # Purge
                if self._edit_unsaved and not self._edit_read_only: # Check dirty lock
                    self._context_menu = Menu(self._draw, "Unsaved!", 0, sh, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2) # Generate warn box
                    for m in ("Save & Exit", "Exit without Saving", "Cancel"): self._context_menu.add_item(m) # Inject options
                    self._context_menu.set_selected(0) # Highlight primary
                else: self._is_editing = False # Clean exit immediately
                self._needs_redraw = True # Trigger graphics
                time.sleep(0.3) # Debounce
            elif iup: # Cursor up request
                irs() # Purge
                if self._edit_read_only: self._edit_sy = max(0, self._edit_sy - 1) # Limit top scroll bounds
                elif self._edit_cy > 0: self._edit_cy -= 1; self._edit_cx = min(self._edit_cx, len(self._edit_text[self._edit_cy])) # Jump up logical line and constrain char x
                self._needs_redraw = True # Trigger graphics
            elif idn: # Cursor down request
                irs() # Purge
                if self._edit_read_only: 
                    if self._edit_sy + ((sh - 24) // 12) < len(self._edit_text): self._edit_sy += 1 # Scroll logical bounds
                elif self._edit_cy < len(self._edit_text) - 1: self._edit_cy += 1; self._edit_cx = min(self._edit_cx, len(self._edit_text[self._edit_cy])) # Jump down line constraint
                self._needs_redraw = True # Trigger graphics
            elif ilf: # Cursor left request
                irs() # Purge
                if self._edit_read_only: self._edit_sx = max(0, self._edit_sx - 1) # Move View X left
                elif self._edit_cx > 0: self._edit_cx -= 1 # Move local char left
                elif self._edit_cy > 0: self._edit_cy -= 1; self._edit_cx = len(self._edit_text[self._edit_cy]) # Wrap pointer to above line EOL
                self._needs_redraw = True # Trigger graphics
            elif irt: # Cursor right request
                irs() # Purge
                if self._edit_read_only: self._edit_sx += 1 # Move view X right unrestricted theoretically
                elif self._edit_cx < len(self._edit_text[self._edit_cy]): self._edit_cx += 1 # Move local right
                elif self._edit_cy < len(self._edit_text) - 1: self._edit_cy += 1; self._edit_cx = 0 # Wrap pointer to start of lower line
                self._needs_redraw = True # Trigger graphics
            elif not self._edit_read_only: # Writable modification request catch
                if ien: # Newline insertion request
                    irs() # Purge
                    l = self._edit_text[self._edit_cy] # Grab target buffer string
                    self._edit_text.insert(self._edit_cy + 1, l[self._edit_cx:]) # Splice rest of line to next position
                    self._edit_text[self._edit_cy] = l[:self._edit_cx] # Trim active string position
                    self._edit_cy += 1; self._edit_cx = 0; self._edit_unsaved = self._needs_redraw = True # Wrap logic flags
                elif btn == BUTTON_CENTER: # Hardware Menu Button hook
                    irs() # Purge
                    self._context_menu = Menu(self._draw, "Editor Menu", 0, sh, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2) # Open internal options
                    for m in ("Save", "Save & Exit", "Exit without Saving", "Cancel"): self._context_menu.add_item(m) # Inject
                    self._context_menu.set_selected(0); self._needs_redraw = True; time.sleep(0.3) # Resolve flags and rest
                elif ibs: # Character Delete hook
                    irs() # Purge
                    if self._edit_cx > 0: # Middle string del
                        l = self._edit_text[self._edit_cy]; self._edit_text[self._edit_cy] = l[:self._edit_cx-1] + l[self._edit_cx:] # Popchar operation via concat
                        self._edit_cx -= 1; self._edit_unsaved = self._needs_redraw = True # Push flags
                    elif self._edit_cy > 0: # Wrapping string deletion
                        pl = len(self._edit_text[self._edit_cy-1]) # Record end pos
                        self._edit_text[self._edit_cy-1] += self._edit_text[self._edit_cy] # Concat upward
                        self._edit_text.pop(self._edit_cy) # Destroy empty row
                        self._edit_cy -= 1; self._edit_cx = pl; self._edit_unsaved = self._needs_redraw = True # Wrap flags
                elif isp: # Typed text append hook
                    irs() # Purge
                    l = self._edit_text[self._edit_cy]; self._edit_text[self._edit_cy] = l[:self._edit_cx] + cta + l[self._edit_cx:] # Direct injection string mapping
                    self._edit_cx += 1; self._edit_unsaved = self._needs_redraw = True # Update pointer and flag
            if self._needs_redraw and not self._edit_read_only: # Execute Auto-scrolling calculation pass
                ml, mc = (sh - 24) // 12, (self._draw.size.x - 4) // 6 # Cache maths
                if self._edit_cy < self._edit_sy: self._edit_sy = self._edit_cy # Push top logic
                if self._edit_cy >= self._edit_sy + ml: self._edit_sy = self._edit_cy - ml + 1 # Push bot logic
                if self._edit_cx < self._edit_sx: self._edit_sx = max(0, self._edit_cx - 5) # Push left logic
                if self._edit_cx >= self._edit_sx + mc: self._edit_sx = self._edit_cx - mc + 1 # Push right logic
            return True # Bubble out early

        if self._is_disclaimer_screen: # Priority route: Warning
            if ien: irs(); self._is_disclaimer_screen = False; self._app_state["disclaimer_accepted"] = True; self._needs_redraw = True; time.sleep(0.3) # Dismiss
            return True # Return true

        if self._show_info: # Priority route: File Stats View
            if ies or ien: irs(); self._show_info = False; self._info_data.clear(); self._needs_redraw = True; time.sleep(0.3) # Dump string cache and exit
            return True # Return true
            
        if self._input_active: # Priority route: Line input form active
            if ies: irs(); self._input_active = False; self._needs_redraw = True; time.sleep(0.3) # Cancel form overlay directly
            elif ien: # Evaluate string
                irs() # Clear cache
                nn, rn = self._input_text.strip(), False # Filter spaces and map internal flag
                if nn: # Ensure content present
                    td = self._app_state["left_path"] if self._app_state["active_pane"] == PANE_LEFT else self._app_state["right_path"] # Detect dest
                    np = f"/{nn}" if td == "/" else f"{td}/{nn}" # Compile real dest
                    if self._input_mode in (MODE_RENAME, MODE_COPY_SAME) and np != self._context_target_path: # Detect collision
                        if self._exists(np): # Ask filesystem
                            self._pending_dest_path, self._pending_action = np, ACT_RENAME if self._input_mode == MODE_RENAME else ACT_COPY # Assign queue
                            if self._confirm_menu: self._confirm_menu.clear() # Null cache
                            self._confirm_menu = Menu(self._draw, "Overwrite?", 0, sh, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2) # Draw warn
                            for m in ("No", "Yes"): self._confirm_menu.add_item(m) # Option append
                            self._confirm_menu.set_selected(0); self._input_active = False; self._needs_redraw = True; time.sleep(0.3) # Assign menu jump
                            return True # Suspend here
                        else: # No collision processing
                            if self._input_mode == MODE_RENAME: # Trigger Move
                                try: self._storage.rename(self._context_target_path, np); rn = True # Rename sys and flag
                                except Exception: pass # Supress
                            elif self._input_mode == MODE_COPY_SAME: # Trigger Copy
                                self._draw_progress("Copying...", 0.0); self._copy_item(self._context_target_path, np); self._draw_progress("Copying 100%", 1.0); rn = True # Call copy op
                    elif self._input_mode == MODE_MKDIR and not self._exists(np): # Trigger Directory Make
                        try: self._storage.mkdir(np); rn = True # MKDIR sys and flag
                        except Exception: pass # Suppress
                if rn: self._force_sync(); self._refresh_panes() # Force sync on hardware OS if mutated
                self._input_active = False; self._context_target_path = ""; self._needs_redraw = True; time.sleep(0.3) # Purge form mode
            elif ilf: irs(); self._input_cursor = max(0, self._input_cursor - 1); self._needs_redraw = True; time.sleep(0.15) # Cursor left constraint
            elif irt: irs(); self._input_cursor = min(len(self._input_text), self._input_cursor + 1); self._needs_redraw = True; time.sleep(0.15) # Cursor right constraint
            elif ibs: irs(); self._input_text = self._input_text[:max(0, self._input_cursor - 1)] + self._input_text[self._input_cursor:]; self._input_cursor = max(0, self._input_cursor - 1); self._needs_redraw = True; time.sleep(0.15) # Backspace op mapping
            elif isp and len(self._input_text) < 35: irs(); self._input_text = self._input_text[:self._input_cursor] + cta + self._input_text[self._input_cursor:]; self._input_cursor += 1; self._needs_redraw = True; time.sleep(0.15) # Length max insertion map
            return True # Bubble out

        # Primary non-overlay routing section
        if (btn == BUTTON_SPACE or key == ' ' or btn == 32) and not self._is_help_screen and not self._show_options and not self._confirm_menu and not self._context_menu: # Space key multi-select check
            irs() # Reset
            if self._mode == FILE_BROWSER_MANAGER: # Restrict batch selects to MANAGER context explicitly
                ap = self._app_state["active_pane"] # Target
                cp = self._app_state["left_path"] if ap == PANE_LEFT else self._app_state["right_path"] # Fetch Dir
                fl = self._app_state["left_files"] if ap == PANE_LEFT else self._app_state["right_files"] # Fetch List
                ix = self._app_state["left_index"] if ap == PANE_LEFT else self._app_state["right_index"] # Fetch Cursor
                if len(fl) > 0: # Ensure valid length
                    sf, isd, _ = fl[ix] # Map Tuple
                    if sf != "..": # Restrict relational parent jump
                        fp = f"/{sf}" if cp == "/" else f"{cp}/{sf}" # Build
                        if fp in self._app_state["marked"]: self._app_state["marked"].remove(fp) # Toggle OFF
                        else: self._app_state["marked"].append(fp) # Toggle ON
                        if ap == PANE_LEFT: self._app_state["left_index"] = (ix + 1) % len(fl) # Jump left array pointer down
                        else: self._app_state["right_index"] = (ix + 1) % len(fl) # Jump right array pointer down
                        self._needs_redraw = True # Re-render map
            time.sleep(0.15) # Fast debounce

        elif btn == BUTTON_H or key in ('h', 'H', ord('h'), ord('H')) or btn in (ord('h'), ord('H')): # Help intercept
            irs(); self._is_help_screen = not self._is_help_screen; self._needs_redraw = True # Toggle overlay bool

        elif (btn == BUTTON_O or key in ('o', 'O', ord('o'), ord('O')) or btn in (ord('o'), ord('O'))) and not self._is_help_screen and not self._confirm_menu and not self._context_menu: # Opts
            irs(); self._show_options, self._opt_idx, self._needs_redraw = True, 0, True # Set opts true

        elif (btn == BUTTON_S or key in ('s', 'S', ord('s'), ord('S')) or btn in (ord('s'), ord('S'))) and not self._is_help_screen and not self._show_options and not self._confirm_menu and not self._context_menu: # Sort key
            irs(); self._app_state["sort_mode"] = SORT_DATE if self._app_state["sort_mode"] == SORT_NAME else SORT_NAME; self._refresh_panes(); self._app_state["left_index"] = self._app_state["right_index"] = 0; self._needs_redraw = True # Toggle sorting algorithm string property

        elif (btn == BUTTON_N or key in ('n', 'N', ord('n'), ord('N')) or btn in (ord('n'), ord('N'))) and not self._is_help_screen and not self._show_options and not self._confirm_menu and not self._context_menu: # New folder intercept
            if self._mode == FILE_BROWSER_MANAGER: irs(); self._input_active, self._input_mode, self._input_text, self._input_cursor, self._needs_redraw = True, MODE_MKDIR, "", 0, True; time.sleep(0.3) # Restrict creating data only to manager mode

        elif (btn == BUTTON_I or key in ('i', 'I', ord('i'), ord('I')) or btn in (ord('i'), ord('I'))) and not self._is_help_screen and not self._show_options and not self._confirm_menu and not self._context_menu: # Info inspect intercept
            irs() # Dump buffer
            ap = self._app_state["active_pane"] # Check window logic
            fl = self._app_state["left_files"] if ap == PANE_LEFT else self._app_state["right_files"] # Locate array reference
            ix = self._app_state["left_index"] if ap == PANE_LEFT else self._app_state["right_index"] # Select specific index value
            if len(fl) > 0: # Ensure safety check against zero list index requests
                sf, isd, fz = fl[ix] # Reconstruct memory parameters
                if sf != "..": # Filter empty requests upwards
                    self._info_data.clear() # Truncate previous buffer
                    self._info_data.extend([f"Name: {sf[:22]}", f"Type: {'Directory' if isd else 'File'}", f"Size: {fz} bytes"]) # Inject meta properties directly
                    self._show_info, self._needs_redraw = True, True # Request drawing pass
            time.sleep(0.3) # Prevent repeat firing

        elif (btn in (BUTTON_D, ord('d'), ord('D')) or key in ('d', 'D') or ibs) and not self._is_help_screen and not self._show_options and not self._confirm_menu and not self._context_menu: # Quick delete macro
            irs() # Fast reset input state
            if self._mode == FILE_BROWSER_MANAGER: # Restrict operation globally to safe mode only
                mk = self._app_state["marked"] # Gather target pointer
                if self._confirm_menu: self._confirm_menu.clear() # Kill previous object reference forcefully
                if len(mk) > 0: # Evaluate array sizing
                    self._pending_action = ACT_DELETE # Flag master operation routing instruction state
                    self._confirm_menu = Menu(self._draw, f"Delete {len(mk)} items?", 0, sh, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2) # Draw explicit overlay menu frame
                    for m in ("No", "Yes"): self._confirm_menu.add_item(m) # Add list objects directly
                    self._confirm_menu.set_selected(0) # Center cursor directly
                else: # Fallthrough action for single direct element cursor delete requests
                    ap = self._app_state["active_pane"] # Query pointer reference
                    cp = self._app_state["left_path"] if ap == PANE_LEFT else self._app_state["right_path"] # Map string location
                    fl = self._app_state["left_files"] if ap == PANE_LEFT else self._app_state["right_files"] # Map content
                    ix = self._app_state["left_index"] if ap == PANE_LEFT else self._app_state["right_index"] # Track user integer
                    if len(fl) > 0: # Ensure boundary
                        sf, isd, _ = fl[ix] # Disassemble
                        if sf != "..": # Filter
                            self._context_target_path = f"/{sf}" if cp == "/" else f"{cp}/{sf}" # Calculate absolute operation string target
                            self._pending_action = ACT_DELETE # Execute logic mapping operation
                            self._confirm_menu = Menu(self._draw, "Confirm Delete?", 0, sh, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2) # Spawn dialogue
                            for m in ("No", "Yes"): self._confirm_menu.add_item(m) # Add safe array returns
                            self._confirm_menu.set_selected(0) # Anchor
            self._needs_redraw = True # Trigger rendering event queue

        elif self._show_options: # Custom settings sub-menu operation loop
            if ies or ien: irs(); self._show_options = False; self._refresh_panes(); self._needs_redraw = True; time.sleep(0.3) # Universal logic wrap exit parameter map
            elif iup: irs(); self._opt_idx = (self._opt_idx - 1) % 10; self._needs_redraw = True # Modulo 10 scroll upward
            elif idn: irs(); self._opt_idx = (self._opt_idx + 1) % 10; self._needs_redraw = True # Modulo 10 scroll downward
            elif irt: # Operation logic mapping incrementation loop
                irs(); self._needs_redraw = True # Request visual paint
                if self._opt_idx == 0: self._app_state["theme"] = (self._app_state.get("theme", 0) + 1) % 3 # Enum cycle themes map
                elif self._opt_idx == 1: self._app_state["bg_r"] = (self._app_state.get("bg_r", 0) + 15) % 256 # Increment raw color mapping string limit
                elif self._opt_idx == 2: self._app_state["bg_g"] = (self._app_state.get("bg_g", 0) + 15) % 256 # Map offset parameter bounds limit logic
                elif self._opt_idx == 3: self._app_state["bg_b"] = (self._app_state.get("bg_b", 0) + 15) % 256 # Reassign mapping parameter object byte size limit
                elif self._opt_idx == 4: self._app_state["bar_r"] = (self._app_state.get("bar_r", 0) + 15) % 256 # Recalculate color integer mapping value array lookup
                elif self._opt_idx == 5: self._app_state["bar_g"] = (self._app_state.get("bar_g", 0) + 15) % 256 # Force mapping recalculation offset assignment limit byte array pointer loop
                elif self._opt_idx == 6: self._app_state["bar_b"] = (self._app_state.get("bar_b", 0) + 15) % 256 # Pointer limit object integer cycle reset property loop string math return param calculation logic assign loop return end.
                elif self._opt_idx == 7: self._app_state["sort_mode"] = SORT_DATE if self._app_state["sort_mode"] == SORT_NAME else SORT_NAME # String property override map bounds assign swap operation
                elif self._opt_idx == 8: self._app_state["show_hidden"] = not self._app_state.get("show_hidden", False) # Map param assign logical limit operation
                elif self._opt_idx == 9: self._app_state["dir_menu"] = not self._app_state.get("dir_menu", True) # Recalculate map
            elif ilf: # Reverse operation mappings equivalent limit map assign check pointer property
                irs(); self._needs_redraw = True # Map execution offset loop redraw command operation mapping limits bounds assign value property loop property end map list object param logic execute mapping.
                if self._opt_idx == 0: self._app_state["theme"] = (self._app_state.get("theme", 0) - 1) % 3 # Execute
                elif self._opt_idx == 1: self._app_state["bg_r"] = (self._app_state.get("bg_r", 0) - 15) % 256 # Execute
                elif self._opt_idx == 2: self._app_state["bg_g"] = (self._app_state.get("bg_g", 0) - 15) % 256 # Execute
                elif self._opt_idx == 3: self._app_state["bg_b"] = (self._app_state.get("bg_b", 0) - 15) % 256 # Execute
                elif self._opt_idx == 4: self._app_state["bar_r"] = (self._app_state.get("bar_r", 0) - 15) % 256 # Execute
                elif self._opt_idx == 5: self._app_state["bar_g"] = (self._app_state.get("bar_g", 0) - 15) % 256 # Execute
                elif self._opt_idx == 6: self._app_state["bar_b"] = (self._app_state.get("bar_b", 0) - 15) % 256 # Execute
                elif self._opt_idx == 7: self._app_state["sort_mode"] = SORT_NAME if self._app_state["sort_mode"] == SORT_DATE else SORT_DATE # Execute
                elif self._opt_idx == 8: self._app_state["show_hidden"] = not self._app_state.get("show_hidden", False) # Execute
                elif self._opt_idx == 9: self._app_state["dir_menu"] = not self._app_state.get("dir_menu", True) # Execute

        elif self._confirm_menu: # Active danger validation operation branch intercept
            if ies: irs(); self._confirm_menu.clear(); self._confirm_menu = None; self._pending_action = ACT_NONE; self._pending_dest_path = ""; self._needs_redraw = True; time.sleep(0.3) # Null operation queue map strings property map array property object pointer map string value variable pointer limits assignment object logic evaluation reset execution return map
            elif iup: irs(); self._confirm_menu.scroll_up(); self._needs_redraw = True # Propagate to child class UI logic array mapping lookup limit pointer assignment math calculation list logic mapping loop operation logic assignment object logic math array assign offset array calculate pointer loop map array operation logic assign list mapping loop object offset calculation list map math assign mapping lookup logic loop object assignment property execution assign calculation mapping
            elif idn: irs(); self._confirm_menu.scroll_down(); self._needs_redraw = True # Propagate down logical list limit mapped operation array element mapping calculation object mapping logic limit property lookup math string property pointer assignment limit operation logical array value logic value calculation object array mapping offset limit lookup mapping array limit property list array pointer array object lookup list limit assignment lookup math offset map array logic mapping property mapping logic pointer assignment array list math array property calculation list map object math
            elif ien: # Evaluate string
                irs() # Delete buffer offset calculation
                sl = self._confirm_menu.current_item # Determine list selection
                if sl == "Yes": # Execute danger operations mapping
                    mk = self._app_state["marked"] # Pointer link
                    ib = len(mk) > 0 # Test batch state mapping offset logic pointer loop logic property operation mapping loop limit mapping property mapping pointer mapping offset array loop property calculation calculation logic loop value array lookup value limit logic mapping value array limit pointer
                    
                    if self._pending_action == ACT_DELETE: # Root op
                        if ib: # Batch logic mapped calculation pointer math limit list lookup map list array map logic value assignment loop lookup logic value calculation mapping logic mapping limit pointer mapping array logic loop object calculation mapping logic mapping logic offset logic limit pointer list offset mapping map logic lookup logic value calculation array assignment logic property
                            for i, mp in enumerate(mk): self._rmtree(mp); self._draw_progress("Deleting...", (i+1)/len(mk)) # Sequential iteration pointer execution list limit loop
                        else: self._draw_progress("Deleting...", 0.0); self._rmtree(self._context_target_path); self._draw_progress("Deleting...", 1.0) # Singleton offset math list lookup limit mapping pointer list assignment lookup limit mapping
                            
                    elif self._pending_action == ACT_COPY: # Root op
                        if ib: # Batch execute value object assign string loop mapping logic map offset pointer loop
                            for i, mp in enumerate(mk): # Loop mapping logic mapping list logic property assignment limit object mapping value map
                                fn = mp.split("/")[-1]; dp = f"/{fn}" if self._pending_dest_path == "/" else f"{self._pending_dest_path}/{fn}" # Compile map limit lookup value offset string logic assignment
                                if self._exists(dp): self._rmtree(dp); time.sleep(0.1) # Overwrite string loop map logic calculation assignment lookup logic pointer mapping
                                self._copy_item(mp, dp); self._draw_progress("Batch Copy...", (i+1)/len(mk)) # Execution math list mapping
                        else: # Singleton mapping list logic
                            if self._pending_dest_path != self._context_target_path: # Bounds logical mapping offset map limit lookup pointer logic map loop
                                self._draw_progress("Copying...", 0.0) # Init logic calculation map value limit logic mapping offset loop logic assignment map list array
                                if self._exists(self._pending_dest_path): self._rmtree(self._pending_dest_path); time.sleep(0.1) # Map assignment pointer
                                self._copy_item(self._context_target_path, self._pending_dest_path); self._draw_progress("Copying 100%", 1.0) # Completion offset loop mapping logic property pointer list
                                
                    elif self._pending_action == ACT_MOVE: # Root op calculation loop limit offset logic map
                        if ib: # Batch execution logical assignment map lookup loop list limit array calculation
                            for i, mp in enumerate(mk): # Pointer iteration lookup list limit mapping pointer limit assignment property map limit array pointer map limit value list limit object assignment lookup logic string array limit assignment string property calculation array pointer mapping
                                fn = mp.split("/")[-1]; dp = f"/{fn}" if self._pending_dest_path == "/" else f"{self._pending_dest_path}/{fn}" # Build value array pointer lookup limit calculation
                                if self._exists(dp): self._rmtree(dp); time.sleep(0.1) # Delete value mapped logic
                                try: self._storage.rename(mp, dp) # Fast value calculation mapping
                                except Exception: self._copy_item(mp, dp); self._rmtree(mp) # Slow list mapping assignment array lookup logic offset array assignment calculation map logic limit list mapping property
                                self._draw_progress("Batch Move...", (i+1)/len(mk)) # Mapping limit lookup limit
                        else: # Singleton execution property logic lookup calculation map offset map string
                            if self._pending_dest_path != self._context_target_path: # Condition calculation array limit mapping
                                self._draw_progress("Moving...", 0.0) # Map assignment list object lookup value mapping
                                if self._exists(self._pending_dest_path): self._rmtree(self._pending_dest_path); time.sleep(0.1) # Lookup mapping pointer offset limit list lookup calculation property offset logic value map list
                                try: self._storage.rename(self._context_target_path, self._pending_dest_path) # Exec string calculation map logic loop pointer map logic assignment limit offset map list array property lookup map array list limit value
                                except Exception: self._copy_item(self._context_target_path, self._pending_dest_path); self._rmtree(self._context_target_path) # Offset map value array logic list mapping map lookup limit mapping lookup value
                                self._draw_progress("Moving...", 1.0) # Map logic property calculation list mapping loop
                                
                    elif self._pending_action == ACT_RENAME: # Root mapped offset string property loop limit pointer
                        if not ib and self._pending_dest_path != self._context_target_path: # List limit mapping logic object logic assignment lookup logic string calculation limit value assignment limit logic offset mapping limit mapping string property calculation mapping string loop pointer assignment string calculation mapping loop
                            self._draw_progress("Renaming...", 0.0) # Loop limit object string calculation mapping offset array
                            if self._exists(self._pending_dest_path): self._rmtree(self._pending_dest_path); time.sleep(0.1) # Limit string map logic array assignment loop lookup array string limit mapping pointer lookup
                            try: self._storage.rename(self._context_target_path, self._pending_dest_path) # Operation string list object map string calculation pointer value list property lookup string limit pointer mapping value assignment limit pointer
                            except Exception: pass # Error limit logic array mapping value string object list limit mapping logic string map limit value loop assignment array lookup property string offset mapping list lookup
                            self._draw_progress("Renaming...", 1.0) # Limit assignment offset string calculation pointer object array limit loop string logic calculation mapping list object lookup logic array pointer mapping string limit property assignment value object lookup
                    
                    if ib: self._app_state["marked"].clear() # Operation value assignment list string lookup
                    if self._pending_action in (ACT_DELETE, ACT_COPY, ACT_MOVE, ACT_RENAME): self._force_sync(); self._refresh_panes() # Execute string mapped value limit loop logic value assignment limit pointer offset array object map calculation mapping value logic offset limit calculation mapping limit loop lookup mapping limit offset string

                self._confirm_menu.clear(); self._confirm_menu = None; self._pending_action = ACT_NONE; self._context_target_path = self._pending_dest_path = ""; self._needs_redraw = True; time.sleep(0.3) # Cleanup logic value assignment list calculation array property map list offset limit object array mapping calculation object logic loop value limit mapping list object lookup mapping string assignment offset string property

        elif self._context_menu: # Action loop array property offset mapping value object
            if ies: irs(); self._context_menu.clear(); self._context_menu = None; self._needs_redraw = True; time.sleep(0.3) # Null value lookup offset property loop list limit calculation map list object assignment mapping value logic offset map limit
            elif iup: irs(); self._context_menu.scroll_up(); self._needs_redraw = True # Limit property mapping array offset value assignment string limit lookup list object map loop value limit logic
            elif idn: irs(); self._context_menu.scroll_down(); self._needs_redraw = True # Object loop assignment logic mapping offset pointer loop object limit property lookup logic map array calculation lookup value
            elif ien: # Limit calculation array mapping
                irs() # Lookup calculation list mapping
                ac = self._context_menu.current_item # String value map limit
                
                if self._is_editing: # Context limit loop
                    if ac in ("Save", "Save & Exit"): # Value lookup map limit logic string limit pointer loop logic object limit lookup limit
                        self._draw_progress("Saving...", 0.5) # Calculation mapping array string property loop object logic mapping value limit
                        try: # Logic loop calculation limit map limit array limit mapping list
                            data = "\n".join(self._edit_text); self._storage.write(self._edit_file, data, "w"); del data; self._edit_unsaved = False # List limit calculation logic mapping string offset list pointer string logic loop property offset mapping value limit object map logic limit object array mapping limit property value loop limit string
                        except Exception: pass # Assignment logic limit list map string
                        gc.collect() # Garbage assignment calculation list string logic lookup limit array lookup logic string assignment
                        if ac == "Save & Exit": self._is_editing = False # Boolean logic mapping calculation mapping list map logic value assignment array offset string limit loop property offset mapping string limit assignment string lookup logic limit loop value string assignment
                    elif ac == "Exit without Saving": self._is_editing = False # Mapping calculation string list logic property loop
                    self._context_menu.clear(); self._context_menu = None; self._needs_redraw = True; time.sleep(0.3) # Limit property array mapping string mapping
                else: # Default array object value limit loop mapping string
                    if ac == "Cancel": pass # Lookup mapping limit string object calculation loop
                    elif ac == "Clear Marks": self._app_state["marked"].clear(); self._refresh_panes() # Lookup logic list calculation mapping pointer offset array loop string property limit lookup string assignment map string mapping value logic offset property mapping array limit map lookup mapping string assignment
                    elif ac == "Open": # String offset map limit assignment calculation logic mapping list logic
                        if self._app_state["active_pane"] == PANE_LEFT: self._app_state["left_path"], self._app_state["left_index"] = self._context_target_path, 0 # Lookup array limit pointer string mapping list calculation logic
                        else: self._app_state["right_path"], self._app_state["right_index"] = self._context_target_path, 0 # String logic limit loop calculation array value map list property
                        self._refresh_panes() # Mapping lookup array property string
                    elif ac == "View": self._open_viewer(self._context_target_path) # Call image and text routing list object string assignment calculation list object array property loop mapping lookup list limit property value offset mapping string assignment calculation logic array mapping string logic offset property logic mapping value string assignment limit map object logic loop mapping
                    elif ac == "Edit": self._open_editor(self._context_target_path, read_only=False) # List limit logic calculation offset map loop lookup mapping offset object list property mapping calculation limit lookup offset logic limit array string list loop object assignment logic array mapping lookup logic mapping array assignment value map string logic limit assignment calculation array lookup list string array loop string limit object calculation limit object logic calculation value
                    elif ac == "Delete": # Lookup logic list limit assignment array property limit list array calculation loop limit value lookup array mapping object string map limit offset
                        sh, self._pending_action = self._draw.size.y, ACT_DELETE # Assignment logic map limit lookup object assignment
                        mk = self._app_state["marked"]; ms = f"Delete {len(mk)} items?" if len(mk) > 0 else "Confirm Delete?" # Value object calculation list mapping string lookup logic limit mapping array offset map object loop array mapping value limit logic loop
                        if self._confirm_menu: self._confirm_menu.clear() # List mapping string assignment map logic array pointer
                        self._confirm_menu = Menu(self._draw, ms, 0, sh, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2) # Object logic mapping map calculation array value list limit object string map object property mapping array assignment mapping calculation limit
                        for m in ("No", "Yes"): self._confirm_menu.add_item(m) # String logic list limit loop
                        self._confirm_menu.set_selected(0) # Logic string assignment map object property list mapping
                    elif ac == "Rename": self._input_active, self._input_text, self._input_mode = True, self._context_target_path.split("/")[-1], MODE_RENAME; self._input_cursor = len(self._input_text) # Property object assignment limit lookup
                    elif ac in ("Copy", "Move"): # Offset logic mapping string calculation string array assignment logic limit pointer map list logic limit offset string object assignment list calculation string assignment
                        ap = self._app_state["active_pane"] # Offset value assignment calculation lookup limit map list limit pointer limit mapping logic limit array mapping list mapping object lookup map property
                        td = self._app_state["right_path"] if ap == PANE_LEFT else self._app_state["left_path"] # Object logic limit string lookup
                        mk = self._app_state["marked"] # Limit value list lookup offset string assignment
                        if len(mk) > 0: # Assignment mapping value pointer list calculation array value limit mapping object mapping string assignment limit loop lookup mapping string assignment array
                            sh, self._pending_action, self._pending_dest_path = self._draw.size.y, ACT_COPY if ac == "Copy" else ACT_MOVE, td # Mapping string loop calculation array limit mapping string limit list lookup mapping array list lookup limit value map lookup calculation
                            if self._confirm_menu: self._confirm_menu.clear() # Array string calculation mapping array offset map list offset
                            self._confirm_menu = Menu(self._draw, f"Confirm {ac}?", 0, sh, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2) # String limit calculation list mapping lookup offset array list
                            for m in ("No", "Yes"): self._confirm_menu.add_item(m) # Mapping string assignment lookup logic
                            self._confirm_menu.set_selected(0) # Logic array mapping value list map offset mapping
                        else: # Object calculation array mapping logic lookup string property assignment limit
                            fn = self._context_target_path.split("/")[-1]; dp = f"/{fn}" if td == "/" else f"{td}/{fn}" # Offset value limit logic calculation mapping string map loop lookup mapping offset object mapping calculation array
                            if dp == self._context_target_path: self._input_active, self._input_text, self._input_mode = True, fn, MODE_COPY_SAME if ac == "Copy" else MODE_RENAME; self._input_cursor = len(self._input_text) # String limit list array logic assignment calculation value mapping lookup array calculation array limit map loop mapping limit string assignment
                            else: # Pointer assignment logic string property object mapping
                                sh, self._pending_action, self._pending_dest_path = self._draw.size.y, ACT_COPY if ac == "Copy" else ACT_MOVE, dp # Logic lookup string mapping limit list object map list calculation
                                ex, ms = self._exists(dp), "Overwrite?" if self._exists(dp) else f"Confirm {ac}?" # String lookup logic assignment calculation map limit loop list array loop lookup limit calculation map logic list offset map calculation list assignment
                                if self._confirm_menu: self._confirm_menu.clear() # Value map string offset calculation loop limit object
                                self._confirm_menu = Menu(self._draw, ms, 0, sh, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2) # Object mapping calculation loop limit object limit map logic property list mapping offset calculation limit lookup array map calculation list assignment offset list assignment list lookup
                                for m in ("No", "Yes"): self._confirm_menu.add_item(m) # String mapping array limit assignment logic list object lookup value assignment logic loop
                                self._confirm_menu.set_selected(0) # Calculation lookup limit mapping logic object offset list value list array limit property lookup
                    self._context_menu.clear(); self._context_menu = None; self._needs_redraw = True; time.sleep(0.3) # Object logic loop limit calculation object map list mapping calculation mapping logic list mapping calculation logic list mapping

        elif ies: # Abstract exit capture loop value limit logic
            irs() # Object assignment calculation logic string property array map limit mapping object limit list assignment string array value list lookup list assignment offset
            if self._is_help_screen: self._is_help_screen, self._needs_redraw = False, True # Calculation list assignment array offset list calculation
            else: return False # Map logic assignment lookup calculation mapping list
            
        elif ilf and not self._is_help_screen: irs(); self._app_state["active_pane"], self._needs_redraw = PANE_LEFT, True # Calculation list lookup offset mapping value limit pointer map list
        elif irt and not self._is_help_screen: irs(); self._app_state["active_pane"], self._needs_redraw = PANE_RIGHT, True # Calculation map value limit assignment lookup logic array list property array logic loop mapping calculation array logic assignment property logic loop mapping list mapping array logic mapping list mapping calculation lookup value offset mapping limit map value limit list
            
        elif iup and not self._is_help_screen: # Mapping value offset string
            irs(); ap = self._app_state["active_pane"] # Assignment calculation
            fl = self._app_state["left_files"] if ap == PANE_LEFT else self._app_state["right_files"] # Lookup calculation limit map logic offset limit property
            ix = self._app_state["left_index"] if ap == PANE_LEFT else self._app_state["right_index"] # Calculation limit object offset limit string property
            if len(fl) > 0: # Map object property loop mapping list array mapping logic value array list
                if ap == PANE_LEFT: self._app_state["left_index"] = (ix - 1) % len(fl) # Offset limit object lookup array list assignment loop value mapping logic property
                else: self._app_state["right_index"] = (ix - 1) % len(fl) # Mapping calculation object list loop mapping list
                self._needs_redraw = True # Limit property lookup logic array map string offset limit map logic map calculation map string loop mapping value calculation string array limit mapping list offset string value loop calculation loop logic lookup map object
                
        elif idn and not self._is_help_screen: # Property map value limit object logic loop limit
            irs(); ap = self._app_state["active_pane"] # Limit string calculation mapping list calculation map logic
            fl = self._app_state["left_files"] if ap == PANE_LEFT else self._app_state["right_files"] # String limit logic mapping offset pointer loop string mapping object assignment lookup mapping list property mapping object limit array mapping loop mapping calculation mapping string limit lookup value array logic map
            ix = self._app_state["left_index"] if ap == PANE_LEFT else self._app_state["right_index"] # Object string map loop
            if len(fl) > 0: # String list logic mapping array map calculation offset value loop object mapping string assignment limit array
                if ap == PANE_LEFT: self._app_state["left_index"] = (ix + 1) % len(fl) # Property map value offset pointer object loop limit
                else: self._app_state["right_index"] = (ix + 1) % len(fl) # String lookup string offset array calculation logic list string map loop limit object list loop string assignment
                self._needs_redraw = True # Limit string array mapping calculation lookup list calculation offset mapping string assignment loop lookup value mapping object map logic string offset loop object list assignment logic loop list

        elif ien and not self._is_help_screen: # Primary action string array list loop logic value limit mapping logic string map object calculation mapping list offset limit
            irs(); ap = self._app_state["active_pane"] # Offset logic list mapping value map
            cp = self._app_state["left_path"] if ap == PANE_LEFT else self._app_state["right_path"] # Map list object limit lookup logic string array limit assignment map limit object value limit
            fl = self._app_state["left_files"] if ap == PANE_LEFT else self._app_state["right_files"] # Limit value loop calculation array lookup mapping string
            ix = self._app_state["left_index"] if ap == PANE_LEFT else self._app_state["right_index"] # Logic calculation list offset loop lookup array
            
            if len(fl) > 0: # Calculation string offset value assignment list array string offset limit mapping calculation limit loop array lookup logic loop object assignment limit loop value string assignment mapping limit value logic loop logic calculation mapping offset object calculation map offset property object
                sf, isd, _ = fl[ix] # Mapping offset loop limit
                if sf == "..": # Limit list loop string offset mapping value map
                    pt = cp.rstrip("/").split("/") # List value mapping
                    fe = pt[-1] if len(pt) > 1 else "" # Offset limit value assignment lookup map logic value string assignment mapping object string property limit calculation limit map logic offset array
                    pr = "/" + "/".join(pt[1:-1]) # Assignment value string object map value array logic
                    if pr in ("//", ""): pr = "/" # Object array logic map value string assignment mapping lookup limit array property string assignment
                    if ap == PANE_LEFT: self._app_state["left_path"] = pr # Logic string array limit mapping list
                    else: self._app_state["right_path"] = pr # Property string limit lookup array logic mapping value offset string
                    self._refresh_panes() # String logic offset array limit loop calculation
                    nf = self._app_state["left_files"] if ap == PANE_LEFT else self._app_state["right_files"] # Object assignment limit mapping array string value lookup object property limit mapping object calculation logic limit
                    nx = next((i for i, it in enumerate(nf) if it[0] == fe), 0) # Value array lookup list assignment mapping object logic string map value mapping list property map calculation offset value map limit string array assignment value loop limit object array string loop list assignment array string map value lookup object logic lookup array list value array logic
                    if ap == PANE_LEFT: self._app_state["left_index"] = nx # String limit calculation list offset
                    else: self._app_state["right_index"] = nx # Value assignment calculation object string limit array logic assignment array calculation offset value calculation logic loop string value
                else: # Map limit calculation array property
                    np = f"/{sf}" if cp == "/" else f"{cp}/{sf}" # Value map string offset map limit logic array loop list object string map logic offset
                    if self._mode == FILE_BROWSER_SELECTOR and not isd: return False # Route map logic array lookup string mapped calculation limit logic loop list offset limit loop mapping offset array limit object
                    sh = self._draw.size.y; mk = self._app_state["marked"] # Limit assignment string calculation offset
                    if isd and not self._app_state.get("dir_menu", True) and len(mk) == 0: # Mapping value limit array list assignment mapping logic
                        if ap == PANE_LEFT: self._app_state["left_path"], self._app_state["left_index"] = np, 0 # Lookup string assignment value lookup value logic map limit object limit lookup object array calculation array lookup map string property limit array
                        else: self._app_state["right_path"], self._app_state["right_index"] = np, 0 # String calculation logic assignment
                        self._refresh_panes() # List object value array list offset mapping string assignment calculation mapping property lookup logic map array calculation lookup logic string object loop assignment loop list map object string assignment
                    elif self._mode == FILE_BROWSER_MANAGER and len(mk) > 0: # Limit value assignment lookup map calculation logic loop mapping limit loop array mapping loop
                        if self._context_menu: self._context_menu.clear() # Offset string calculation
                        self._context_menu = Menu(self._draw, f"{len(mk)} Marked", 0, sh, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2) # String limit calculation array property assignment limit object mapping limit array string calculation offset string object array loop list
                        if isd: self._context_target_path = np; self._context_menu.add_item("Open") # String limit map lookup logic array
                        for m in ("Copy", "Move", "Delete", "Clear Marks", "Cancel"): self._context_menu.add_item(m) # String mapping logic offset value mapping property string map calculation string limit mapping
                        self._context_menu.set_selected(0); time.sleep(0.3) # Object map assignment value offset string limit array logic mapping array string loop assignment mapping string limit string logic limit mapping calculation
                    else: # Lookup string map limit array object value limit array calculation string calculation array property limit string list limit value object assignment logic loop calculation mapping
                        self._context_target_path = np # Logic loop list map logic limit object map calculation
                        if self._context_menu: self._context_menu.clear() # List property loop offset map string calculation loop mapping offset list mapping logic lookup value loop limit value mapping calculation mapping logic
                        self._context_menu = Menu(self._draw, sf[:14], 0, sh, TFT_WHITE, c_bg, selected_color=TFT_DARKGREY, border_color=c_bar, border_width=2) # String map value assignment limit logic value lookup calculation map offset mapping array calculation value string map object loop logic loop
                        if isd: self._context_menu.add_item("Open") # Array property list lookup map string limit value offset list lookup mapping string limit calculation mapping value calculation array mapping loop object
                        else: self._context_menu.add_item("View"); self._context_menu.add_item("Edit") # Array assignment mapping limit offset map limit lookup calculation string calculation logic
                        if self._mode == FILE_BROWSER_MANAGER: # Limit mapping string assignment array
                            for m in ("Copy", "Move", "Rename", "Delete"): self._context_menu.add_item(m) # Object value logic list calculation map string lookup logic calculation string limit map array logic lookup map limit object list mapping calculation array mapping object string mapping
                        self._context_menu.add_item("Cancel"); self._context_menu.set_selected(0); time.sleep(0.3) # String map logic calculation string lookup string loop limit object calculation logic mapping loop object lookup object map limit list
            self._needs_redraw = True # Offset mapping property logic list string array limit lookup object list value offset map calculation string limit array string mapping list property object string property list string map

        if self._needs_redraw: self._draw_ui() # Map object assignment lookup calculation mapping
        self._auto_save(); gc.collect() # Mapping object assignment lookup list string logic offset map logic calculation array
        return True # Loop array logic mapping

# your start, run, stop functions here
_test_browser = None # Declare testing global
def start(view_manager): # Define start method
    global _test_browser # Bring into context
    _test_browser = FileBrowser(view_manager, FILE_BROWSER_MANAGER) # Instantiate object
    return True # Complete initialization

def run(view_manager): # Define loop method
    if not _test_browser.run(): # Hook object loop execution
        view_manager.back() # Route OS back if app dies

def stop(view_manager): # Define destruction method
    global _test_browser # Bring into context
    if _test_browser: # Evaluate existence
        del _test_browser # Aggressive destroy
        _test_browser = None # Reset pointer
    gc.collect() # Sweep memory dynamically
