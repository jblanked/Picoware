import time # Import time for real-time clock and timer functions
import json # Import json for settings serialization
import gc # Import garbage collector to manage RAM
import os # Import OS for broad string checks

from picoware.system.vector import Vector # Import Vector for 2D coordinate handling
from picoware.system.colors import ( # Import standard system colors
    TFT_ORANGE, TFT_DARKGREY, TFT_LIGHTGREY, TFT_WHITE, # Import UI colors
    TFT_BLACK, TFT_BLUE, TFT_YELLOW, TFT_GREEN, TFT_RED # Import theme colors
) # End color imports

from picoware.system.buttons import ( # Import primary control buttons
    BUTTON_BACK, BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, # Nav buttons
    BUTTON_CENTER, BUTTON_BACKSPACE, BUTTON_H, BUTTON_ESCAPE, BUTTON_O # Action buttons
) # End primary button imports

from picoware.system.wifi import ( # Import WiFi constants for the diagnostic screen
    WIFI_STATE_CONNECTED, WIFI_STATE_CONNECTING, # Connection success and progress states
    WIFI_STATE_ISSUE, WIFI_STATE_TIMEOUT # Connection error and timeout states
) # End WiFi imports

try: # Attempt to import extended keyboard keys
    from picoware.system.buttons import BUTTON_A, BUTTON_Z, BUTTON_0, BUTTON_9, BUTTON_SPACE, BUTTON_N, BUTTON_T, BUTTON_S, BUTTON_C, BUTTON_M, BUTTON_R, BUTTON_D # Import alpha-numeric and shortcut keys
except ImportError: # Fallback if extended keys are not available
    BUTTON_A = BUTTON_Z = BUTTON_0 = BUTTON_9 = BUTTON_SPACE = BUTTON_N = BUTTON_T = BUTTON_S = BUTTON_C = BUTTON_M = BUTTON_R = BUTTON_D = -99 # Assign dummy values to avoid crashes

try: # Attempt to initialize hardware buzzers
    from machine import Pin, PWM # Import Pin and PWM for audio generation
    buzzer_l = PWM(Pin(28)) # Initialize left buzzer on Pin 28
    buzzer_r = PWM(Pin(27)) # Initialize right buzzer on Pin 27
    buzzer_l.duty_u16(0) # Silence left buzzer initially
    buzzer_r.duty_u16(0) # Silence right buzzer initially
    buzzer = (buzzer_l, buzzer_r) # Tuple storing both buzzers
except Exception: # Fallback if audio hardware is missing
    buzzer = None # Set buzzer reference to None

show_options = False # Global flag for options overlay visibility
help_scroll = 0 # Track scroll position for help screen
_last_saved_json = "" # Cache of last saved JSON to avoid redundant writes

_SETTINGS_FILE = "/picoware/settings/eggtimer_settings.json" # Define save path for configuration

_THEMES = ( # Tuple defining available UI themes to save PSRAM
    ("Green", TFT_GREEN), # Green theme option
    ("Red", TFT_RED), # Red theme option
    ("Blue", TFT_BLUE), # Blue theme option
    ("Yellow", TFT_YELLOW), # Yellow theme option
    ("Orange", TFT_ORANGE) # Orange theme option
) # End theme tuple

_EGG_PRESETS = ( # Tuple defining standard egg cooking times
    (0, "Off / Deactivate"), # Option to cancel egg timer
    (4, "Soft (4m)"), # 4-minute soft boil
    (6, "Medium (6m)"), # 6-minute medium boil
    (8, "Hard (8m)"), # 8-minute hard boil
    (10, "Hard+ (10m)") # 10-minute extra hard boil
) # End presets tuple

_VERSION = "0.10" # App version string updated

def get_help_lines(): # Function to dynamically generate help lines to save RAM
    global state # Access global state for the board name
    import gc # Import gc for memory info
    
    b_name = state.get("board_name", "Unknown Board")[:18] # Safely fetch and truncate board name
    
    try: # Safely attempt to get firmware info
        import os # Import os for firmware check
        hw_fw = os.uname().release # Fetch firmware version
    except Exception: # Fallback if os.uname() is missing
        hw_fw = "Unknown FW" # Default firmware string
        
    return [ # Return a list of lines
        f"EGGTIMER v{_VERSION}", # App title and version
        "--------------------", # Divider
        "Req: Wi-Fi Board", # Requirements
        "", # Empty line
        "DEBUG INFO:", # Debug header
        f"Board: {b_name}", # Display stripped board name
        f"FW: {hw_fw}", # Firmware version
        f"RAM Used: {gc.mem_alloc()} B", # Allocated RAM
        f"RAM Free: {gc.mem_free()} B", # Free RAM
        "", # Empty line
        "CREDITS:", # Credits header
        "made by Slasher006", # Author credit
        "with the help of Gemini", # AI credit
        "Date: 2026-02-27", # Current creation date
        "", # Empty line
        "SHORTCUTS:", # Shortcuts header
        "[L/R] Tgl ON/OFF", # Toggle alarm
        "[T] Tgl Audio", # Toggle sound
        "[C] Clear Past", # Clear history
        "[BS] Delete Alarm", # Delete specific alarm
        "[H] Help Overlay", # Show help
        "[O] Options Menu", # Show options
        "[N] New Alarm", # Create new alarm
        "[M] Alarm List", # View alarm list
        "[R] Reset Timers", # Reset timers
        "[D] Diagnostics", # Open diagnostic screen (if enabled)
        "[ESC] Exit App", # Exit application
        "", # Empty line
        "CONTROLS:", # Controls header
        "[UP/DN] Navigate", # Navigation keys
        "[ENTER] Select/Save" # Action keys
    ] # End help lines list

DEFAULT_STATE = { # Dictionary holding all default application variables
    "theme_idx": 0, # Default theme index (Green)
    "bg_r": 0, # Default background Red value
    "bg_g": 0, # Default background Green value
    "bg_b": 0, # Default background Blue value
    "use_12h": False, # Flag for 12-hour AM/PM format
    "snooze_min": 5, # Default snooze duration in minutes
    "show_diagnostics": False, # Toggle for boot diagnostic screen
    "alarms": [], # List holding user alarms
    "egg_preset": 1, # Default selected egg preset
    "egg_end": 0, # Timestamp for egg timer completion
    "sw_run": False, # Flag indicating if stopwatch is running
    "sw_start": 0, # Start time of the stopwatch
    "sw_accum": 0, # Accumulated stopwatch time
    "last_sw_ms": 0, # Last recorded stopwatch millisecond tick
    "cd_h": 0, # Countdown hours
    "cd_m": 0, # Countdown minutes
    "cd_s": 0, # Countdown seconds
    "cd_cursor": 0, # Cursor position for countdown setup
    "cd_end": 0, # Timestamp for countdown completion
    "mode": "main", # Current application screen/mode defaults to main
    "origin": "main", # Previous screen to return to
    "msg_origin": "main", # Previous screen specifically for error messages
    "cursor_idx": 0, # Cursor index for main menu and alarm list
    "options_cursor_idx": 0, # Cursor index for options menu
    "edit_idx": -1, # Index of alarm currently being edited
    "tmp_daily": False, # Temporary flag for daily alarm editing
    "tmp_y": 2026, # Temporary year for editing
    "tmp_mo": 1, # Temporary month for editing
    "tmp_d": 1, # Temporary day for editing
    "date_cursor": 0, # Cursor position in date editor
    "tmp_h": 12, # Temporary hour for editing
    "tmp_m": 0, # Temporary minute for editing
    "tmp_label": "", # Temporary label string for editing
    "tmp_audible": True, # Temporary flag for audio during alarm
    "ringing_idx": -1, # Index of the currently ringing alarm
    "snooze_epoch": 0, # Timestamp when snooze ends
    "snooze_idx": -1, # Index of the snoozed alarm
    "snooze_count": 0, # Number of times current alarm was snoozed
    "last_s": -1, # Last tracked second to reduce redraws
    "last_trig_m": -1, # Last triggered minute to prevent multi-fires
    "dirty_ui": True, # Flag indicating screen needs redraw
    "ring_flash": False, # Flag toggling alarm flashing colors
    "dirty_save": False, # Flag indicating settings need saving
    "save_timer": 0, # Countdown timer before committing save to disk
    "del_confirm_yes": False, # State of delete confirmation prompt
    "clear_confirm_yes": False, # State of clear all confirmation prompt
    "has_hardware": True, # Hardware capability flag
    "time_synced": True, # NTP sync flag
    "board_name": "Unknown" # Track the board name for diagnostics UI
} # End default state dictionary

state = None # Global reference to live state
storage = None # Global reference to system storage
show_help = False # Global flag for help overlay visibility
show_options = False # Global flag for options overlay visibility
help_box = None # Global reference to the TextBox UI element

def rgb_to_565(r, g, b): # Function to convert RGB888 to RGB565 format
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3) # Bitwise conversion for TFT display

def queue_save(): # Function to delay disk writes and save flash memory
    global state # Access global state
    if state: # Check if state exists safely
        state["dirty_save"] = True # Mark state as needing a save
        state["save_timer"] = 60 # Wait ~60 cycles before writing

def save_settings(): # Function to commit settings to disk
    global _last_saved_json, state, storage # Access globals
    if not storage or not state: return # Abort if storage or state is unavailable
    try: # Catch IO errors safely
        exclude_keys = ("dirty_ui", "mode", "cursor_idx", "options_cursor_idx", "tmp_y", "tmp_mo", "tmp_d", "date_cursor", "tmp_h", "tmp_m", "tmp_label", "tmp_audible", "edit_idx", "ringing_idx", "last_s", "ring_flash", "dirty_save", "save_timer", "origin", "del_confirm_yes", "clear_confirm_yes", "snooze_epoch", "snooze_idx", "last_trig_m", "snooze_count", "msg_origin", "tmp_daily", "egg_end", "sw_run", "sw_start", "sw_accum", "last_sw_ms", "cd_end", "cd_cursor", "has_hardware", "time_synced", "board_name") # Define volatile keys not to save
        save_data = {k: v for k, v in state.items() if k not in exclude_keys} # Filter state dict to only persistent data
        json_str = json.dumps(save_data) # Convert dict to JSON string
        if json_str == _last_saved_json: # Check if data actually changed
            state["dirty_save"] = False # Reset save flag
            gc.collect() # Sweep RAM used by JSON formatting
            return # Exit early to save flash wear
        storage.write(_SETTINGS_FILE, json_str, "w") # Write to persistent file
        _last_saved_json = json_str # Update JSON cache
        state["dirty_save"] = False # Reset save flag
        gc.collect() # Sweep RAM used by JSON formatting
    except Exception: pass # Ignore save errors silently

def validate_and_load_settings(): # Function to load and migrate settings
    global state, _last_saved_json, storage # Access globals
    if storage and storage.exists(_SETTINGS_FILE): # Check if config file exists
        try: # Catch parsing errors
            raw_data = storage.read(_SETTINGS_FILE, "r") # Read file content
            loaded = json.loads(raw_data) # Parse JSON into dict
            exclude_keys = ("dirty_ui", "mode", "cursor_idx", "options_cursor_idx", "tmp_y", "tmp_mo", "tmp_d", "date_cursor", "tmp_h", "tmp_m", "tmp_label", "tmp_audible", "edit_idx", "ringing_idx", "last_s", "ring_flash", "dirty_save", "save_timer", "origin", "del_confirm_yes", "clear_confirm_yes", "snooze_epoch", "snooze_idx", "last_trig_m", "snooze_count", "msg_origin", "tmp_daily", "egg_end", "sw_run", "sw_start", "sw_accum", "last_sw_ms", "cd_end", "cd_cursor", "has_hardware", "time_synced", "board_name") # Keys to ignore from file
            for key in loaded: # Iterate loaded data
                if key in state and key not in exclude_keys: state[key] = loaded[key] # Inject valid data into runtime state
            
            t = time.localtime() # Get current time for migration
            for i in range(len(state["alarms"])): # Iterate all loaded alarms
                a = state["alarms"][i] # Get individual alarm
                if len(a) == 3: state["alarms"][i] = [t[0], t[1], t[2], a[0], a[1], a[2], "ALARM", True, False] # Migrate v1 alarms
                elif len(a) == 4: state["alarms"][i] = [t[0], t[1], t[2], a[0], a[1], a[2], a[3], True, False] # Migrate v2 alarms
                elif len(a) == 7: state["alarms"][i] = [a[0], a[1], a[2], a[3], a[4], a[5], a[6], True, False] # Migrate v3 alarms
                elif len(a) == 8: state["alarms"][i] = [a[0], a[1], a[2], a[3], a[4], a[5], a[6], a[7], False] # Migrate v4 alarms
            
            save_data = {k: v for k, v in state.items() if k not in exclude_keys} # Prep sanitized data dict
            _last_saved_json = json.dumps(save_data) # Set initial JSON cache
        except Exception: pass # Ignore load errors, use defaults

def handle_audio_silence(): # Function to kill buzzer PWM output
    if buzzer: # Check if buzzer hardware exists
        try: # Catch hardware exceptions
            for b in buzzer: b.duty_u16(0) # Set duty cycle to 0 for both channels
        except Exception: pass # Ignore audio errors

def validate_hardware_and_time(view_manager): # Function to verify board capabilities gracefully
    global state # Access global state
    
    hw_flag = False # Initialize hardware flag to false
    board_str = "Unknown" # Initialize fallback string
    
    try: # Safely attempt to read hardware name natively
        import os # Import os
        board_str = os.uname().machine.replace("Raspberry Pi ", "") # Strip redundant prefix to save screen space
    except Exception: # Fallback
        pass # Ignore errors
        
    state["board_name"] = board_str # Store clean string in state dictionary for global access
    
    if hasattr(view_manager, "has_wifi") and view_manager.has_wifi: # Layer 1: Check native OS property
        hw_flag = True # Flag as capable
    else: # Layer 2: String detection fallback
        b_name = board_str.lower() # Convert to lowercase for reliable matching
        if "pico w" in b_name or "pico2 w" in b_name or "pico 2 w" in b_name or "pico 2w" in b_name: # Check substring patterns
            hw_flag = True # Flag as capable if physical hardware name matches
            
    state["has_hardware"] = hw_flag # Apply final computed hardware flag
    
    if time.localtime()[0] < 2024: # Check if NTP time is un-synced
        state["time_synced"] = False # Flag time as invalid
    else: # Time appears correct
        state["time_synced"] = True # Flag time as valid

def check_time_and_alarms(t, c_sec): # Core logic loop evaluating timers
    global state # Access global state
    cy, cmo, cd, ch, cm, cs = t[0], t[1], t[2], t[3], t[4], t[5] # Unpack local time tuple
    
    if state["mode"] == "stopwatch" and state["sw_run"]: # Check if stopwatch UI needs fast updates
        now_ms = time.ticks_ms() # Get current milliseconds
        if time.ticks_diff(now_ms, state["last_sw_ms"]) > 100: # Refresh screen every 100ms
            state["last_sw_ms"] = now_ms # Update tracker
            state["dirty_ui"] = True # Force UI redraw
            
    if cs != state["last_s"]: # Only evaluate logic once per second
        state["last_s"] = cs # Update second tracker
        state["dirty_ui"] = True # Force UI redraw
        if state["mode"] != "ring": # Only check triggers if not already ringing
            if state["egg_end"] > 0 and c_sec >= state["egg_end"]: # Check if eggtimer finished
                state["mode"] = "ring" # Switch to ring UI
                state["ringing_idx"] = -2 # Set special ID for eggtimer
                state["egg_end"] = 0 # Reset eggtimer
            elif state["cd_end"] > 0 and c_sec >= state["cd_end"]: # Check if countdown finished
                state["mode"] = "ring" # Switch to ring UI
                state["ringing_idx"] = -3 # Set special ID for countdown
                state["cd_end"] = 0 # Reset countdown
            elif state["snooze_epoch"] > 0 and c_sec >= state["snooze_epoch"]: # Check if snooze finished
                state["mode"] = "ring" # Switch to ring UI
                state["ringing_idx"] = state["snooze_idx"] # Re-trigger snoozed alarm
                state["snooze_epoch"] = 0 # Reset snooze timestamp
                state["last_trig_m"] = cm # Track trigger minute
            elif cs == 0 and state["last_trig_m"] != cm and state["time_synced"]: # Every new minute check standard alarms if time is valid
                for i in range(len(state["alarms"])): # Iterate alarm list
                    a = state["alarms"][i] # Extract individual alarm
                    if a[5] and a[3] == ch and a[4] == cm and (a[8] or (a[0] == cy and a[1] == cmo and a[2] == cd)): # Check if active and matching time/date
                        state["mode"] = "ring" # Switch to ring UI
                        state["ringing_idx"] = i # Track triggered alarm index
                        state["snooze_count"] = 0 # Reset snooze counter
                        state["last_trig_m"] = cm # Track trigger minute
                        break # Only trigger one alarm per minute

    if state["mode"] == "ring" and state["dirty_ui"]: # Handle visual/audio effects while ringing
        state["ring_flash"] = not state["ring_flash"] # Toggle visual flash state
        is_audible = True if state["ringing_idx"] in (-2, -3) else state["alarms"][state["ringing_idx"]][7] # Determine if alarm should make sound
        if buzzer and is_audible: # Check if hardware and setting allow sound
            try: # Catch PWM errors
                for b in buzzer: # Loop both buzzers
                    b.freq(1000) if state["ring_flash"] else None # Set tone frequency
                    b.duty_u16(32768 if state["ring_flash"] else 0) # Pulse audio volume
            except Exception: pass # Ignore audio errors

# --- INPUT HANDLER DISPATCH FUNCTIONS ---

def handle_input_diagnostic(button, input_mgr, view_manager, t, c_sec): # Handle inputs for the diagnostic screen
    global state # Access the global state dictionary
    if button in (BUTTON_BACK, BUTTON_ESCAPE): # Ensure users can back out of the app entirely
        state["dirty_ui"] = False # Stop rendering
        view_manager.back() # Natively pop the app and return control to Picoware OS
        return # Exit the function immediately
    elif button == BUTTON_CENTER: # Check if the center (enter) button was pressed to confirm
        state["mode"] = "main" # Switch the application mode to the main dashboard menu
        state["dirty_ui"] = True # Force a screen redraw to clear the diagnostic text
    elif button == BUTTON_RIGHT: # Check if the right button was pressed to manually retry sync
        if state.get("has_hardware", False): # Only attempt sync if WiFi hardware was successfully detected
            try: # Wrap the risky network/time operation in a try block
                import ntptime # Import the MicroPython standard NTP module
                ntptime.settime() # Attempt to fetch and apply the time from the NTP server
                state["time_synced"] = True # Update the state if the fetch was successful
            except Exception: pass # Ignore the error silently
        state["dirty_ui"] = True # Force a screen redraw to reflect any changes

def handle_input_modals(button, input_mgr, view_manager, t, c_sec): # Handle errors and confirmations
    global state # Access state
    if state["mode"] in ("invalid_time", "invalid_date_format", "hardware_warning"): # Transient errors
        if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_CENTER, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_UP, BUTTON_DOWN): # Dismiss keys
            state["mode"] = state.get("msg_origin", "main"); state["dirty_ui"] = True # Go back
    elif state["mode"] == "confirm_delete": # Delete prompt
        if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = "alarms"; state["dirty_ui"] = True # Cancel
        elif button in (BUTTON_LEFT, BUTTON_RIGHT): state["del_confirm_yes"] = not state["del_confirm_yes"]; state["dirty_ui"] = True # Toggle yes/no
        elif button == BUTTON_CENTER: # Confirm
            if state["del_confirm_yes"]: # If Yes
                if state["snooze_idx"] == state["cursor_idx"]: state["snooze_epoch"] = state["snooze_count"] = 0 # Cancel snooze
                elif state["snooze_idx"] > state["cursor_idx"]: state["snooze_idx"] -= 1 # Shift snooze
                state["alarms"].pop(state["cursor_idx"]); state["cursor_idx"] = max(0, state["cursor_idx"] - 1); queue_save() # Delete
            state["mode"] = "alarms"; state["dirty_ui"] = True # Exit
    elif state["mode"] == "confirm_clear": # Clear prompt
        if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = "alarms"; state["dirty_ui"] = True # Cancel
        elif button in (BUTTON_LEFT, BUTTON_RIGHT): state["clear_confirm_yes"] = not state["clear_confirm_yes"]; state["dirty_ui"] = True # Toggle yes/no
        elif button == BUTTON_CENTER: # Confirm
            if state["clear_confirm_yes"]: # If Yes
                for i in range(len(state["alarms"]) - 1, -1, -1): # Reverse iterate
                    a = state["alarms"][i] # Get alarm
                    if not a[8] and time.mktime((a[0], a[1], a[2], a[3], a[4], 0, 0, 0)) < c_sec: # Check if past
                        if state["snooze_idx"] == i: state["snooze_epoch"] = state["snooze_count"] = 0 # Cancel snooze
                        elif state["snooze_idx"] > i: state["snooze_idx"] -= 1 # Shift snooze
                        state["alarms"].pop(i) # Delete
                state["cursor_idx"] = 0; queue_save() # Save
            state["mode"] = "alarms"; state["dirty_ui"] = True # Exit

def handle_input_ring(button, input_mgr, view_manager, t, c_sec): # Handle active alarms
    global state # Access state
    if state["ringing_idx"] in (-2, -3): # Eggtimer or Countdown
        if button in (BUTTON_CENTER, BUTTON_O, BUTTON_BACK, BUTTON_ESCAPE): # Dismiss
            state["mode"] = "egg_timer" if state["ringing_idx"] == -2 else "countdown"; state["ringing_idx"] = -1; state["dirty_ui"] = True; handle_audio_silence() # Stop
    else: # Standard alarm
        if button in (BUTTON_S, BUTTON_CENTER): # Snooze
            if state["snooze_count"] < 5: # Allowed snooze
                state["snooze_epoch"] = c_sec + (state["snooze_min"] * 60); state["snooze_idx"] = state["ringing_idx"]; state["snooze_count"] += 1; queue_save() # Schedule snooze
            else: # Max snooze
                if 0 <= state["ringing_idx"] < len(state["alarms"]) and not state["alarms"][state["ringing_idx"]][8]: state["alarms"][state["ringing_idx"]][5] = False; queue_save() # Disable
                state["snooze_epoch"] = state["snooze_count"] = 0 # Reset
            state["mode"] = "main"; state["ringing_idx"] = -1; state["dirty_ui"] = True; handle_audio_silence() # Stop
        elif button in (BUTTON_O, BUTTON_BACK, BUTTON_ESCAPE): # Dismiss
            state["mode"] = "main" # Change state
            if 0 <= state["ringing_idx"] < len(state["alarms"]) and not state["alarms"][state["ringing_idx"]][8]: state["alarms"][state["ringing_idx"]][5] = False; queue_save() # Disable
            state["ringing_idx"] = -1; state["snooze_epoch"] = state["snooze_count"] = 0; state["dirty_ui"] = True; handle_audio_silence() # Stop

def handle_input_main(button, input_mgr, view_manager, t, c_sec): # Handle dashboard
    global state, show_help, show_options # Access state
    cy, cmo, cd, ch, cm = t[0], t[1], t[2], t[3], t[4] # Unpack time
    if button in (BUTTON_BACK, BUTTON_ESCAPE): # Exit app handling
        state["dirty_ui"] = False # Stop rendering
        view_manager.back() # Natively pop the app and return control to Picoware OS
        return # Exit the function immediately
    elif button == BUTTON_H: show_help = True; state["dirty_ui"] = True # Show help
    elif button == BUTTON_O: show_options = True; state["dirty_ui"] = True # Show options
    elif button == BUTTON_D and state.get("show_diagnostics", False): state["mode"] = "diagnostic"; state["dirty_ui"] = True # Go to diagnostic screen if enabled
    elif button == BUTTON_M: 
        if not state["time_synced"]: state["mode"] = "hardware_warning"; state["msg_origin"] = "main"; state["dirty_ui"] = True # Block entry if NTP missing
        else: state["mode"] = "alarms"; state["cursor_idx"] = 0; state["dirty_ui"] = True # Jump alarms
    elif button == BUTTON_N: # Quick create
        if not state["time_synced"]: state["mode"] = "hardware_warning"; state["msg_origin"] = "main"; state["dirty_ui"] = True # Block entry if NTP missing
        else: state["mode"] = "edit_type"; state["origin"] = "main"; state["edit_idx"] = -1; state["tmp_daily"] = False; state["tmp_y"] = cy; state["tmp_mo"] = cmo; state["tmp_d"] = cd; state["date_cursor"] = 0; state["tmp_h"] = ch; state["tmp_m"] = cm; state["tmp_label"] = ""; state["tmp_audible"] = True; state["dirty_ui"] = True # Setup edit
    elif button == BUTTON_DOWN: state["cursor_idx"] = (state["cursor_idx"] + 1) % 6; state["dirty_ui"] = True # Nav down
    elif button == BUTTON_UP: state["cursor_idx"] = (state["cursor_idx"] - 1) % 6; state["dirty_ui"] = True # Nav up
    elif button == BUTTON_CENTER: # Enter
        if state["cursor_idx"] == 0: 
            if not state["time_synced"]: state["mode"] = "hardware_warning"; state["msg_origin"] = "main" # Block entry if NTP missing
            else: state["mode"] = "alarms"; state["cursor_idx"] = 0 # Go alarms
        elif state["cursor_idx"] == 1: state["mode"] = "egg_timer" # Go egg
        elif state["cursor_idx"] == 2: state["mode"] = "stopwatch" # Go sw
        elif state["cursor_idx"] == 3: state["mode"] = "countdown" # Go cd
        elif state["cursor_idx"] == 4: show_options = True # Go opt
        elif state["cursor_idx"] == 5: show_help = True # Go help
        state["dirty_ui"] = True # Redraw

def handle_input_egg_timer(button, input_mgr, view_manager, t, c_sec): # Handle egg timer inputs
    global state # Access the global state dictionary
    if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = "main"; state["dirty_ui"] = True # Return to main menu if back is pressed
    elif button == BUTTON_DOWN: state["egg_preset"] = (state["egg_preset"] + 1) % len(_EGG_PRESETS); state["dirty_ui"] = True # Cycle preset selection down
    elif button == BUTTON_UP: state["egg_preset"] = (state["egg_preset"] - 1) % len(_EGG_PRESETS); state["dirty_ui"] = True # Cycle preset selection up
    elif button == BUTTON_CENTER: # Apply the currently selected preset
        m = _EGG_PRESETS[state["egg_preset"]][0] # Extract the minute value from the preset tuple
        if m == 0: state["egg_end"] = 0 # If 0 minutes selected, disable the running timer entirely
        else: state["egg_end"] = c_sec + (m * 60) # Calculate the exact completion timestamp in seconds
        queue_save(); state["dirty_ui"] = True # Queue a flash save and force a screen redraw without changing the mode

def handle_input_stopwatch(button, input_mgr, view_manager, t, c_sec): # Handle stopwatch
    global state # Access state
    if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = "main"; state["dirty_ui"] = True # Back
    elif button == BUTTON_CENTER: # Toggle
        if state["sw_run"]: state["sw_accum"] += time.ticks_diff(time.ticks_ms(), state["sw_start"]); state["sw_run"] = False # Pause
        else: state["sw_start"] = time.ticks_ms(); state["sw_run"] = True # Resume
        state["dirty_ui"] = True # Redraw
    elif button == BUTTON_R: state["sw_accum"] = 0; state["sw_run"] = False; state["dirty_ui"] = True # Reset

def handle_input_countdown(button, input_mgr, view_manager, t, c_sec): # Handle countdown
    global state # Access state
    if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = "main"; state["dirty_ui"] = True # Back
    elif state["cd_end"] == 0: # Setup phase
        if button == BUTTON_LEFT: state["cd_cursor"] = (state["cd_cursor"] - 1) % 3; state["dirty_ui"] = True # Left
        elif button == BUTTON_RIGHT: state["cd_cursor"] = (state["cd_cursor"] + 1) % 3; state["dirty_ui"] = True # Right
        elif button == BUTTON_UP: # Inc
            if state["cd_cursor"] == 0: state["cd_h"] = (state["cd_h"] + 1) % 100 # Add H
            elif state["cd_cursor"] == 1: state["cd_m"] = (state["cd_m"] + 1) % 60 # Add M
            elif state["cd_cursor"] == 2: state["cd_s"] = (state["cd_s"] + 1) % 60 # Add S
            state["dirty_ui"] = True; queue_save() # Redraw
        elif button == BUTTON_DOWN: # Dec
            if state["cd_cursor"] == 0: state["cd_h"] = (state["cd_h"] - 1) % 100 # Sub H
            elif state["cd_cursor"] == 1: state["cd_m"] = (state["cd_m"] - 1) % 60 # Sub M
            elif state["cd_cursor"] == 2: state["cd_s"] = (state["cd_s"] - 1) % 60 # Sub S
            state["dirty_ui"] = True; queue_save() # Redraw
        elif button == BUTTON_CENTER: # Start
            total_s = state["cd_h"] * 3600 + state["cd_m"] * 60 + state["cd_s"] # Calc sec
            if total_s > 0: state["cd_end"] = c_sec + total_s; state["dirty_ui"] = True # Run
        elif button == BUTTON_R: state["cd_h"] = state["cd_m"] = state["cd_s"] = 0; state["dirty_ui"] = True; queue_save() # Reset
    else: # Run phase
        if button in (BUTTON_CENTER, BUTTON_R): state["cd_end"] = 0; state["dirty_ui"] = True # Cancel

def handle_input_alarms(button, input_mgr, view_manager, t, c_sec): # Handle alarms list
    global state # Access state
    cy, cmo, cd, ch, cm = t[0], t[1], t[2], t[3], t[4] # Unpack time
    list_len = len(state["alarms"]) + 1 # Dynamic len
    if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = "main"; state["cursor_idx"] = 0; state["dirty_ui"] = True # Back
    elif button == BUTTON_DOWN and state["cursor_idx"] < list_len - 1: state["cursor_idx"] += 1; state["dirty_ui"] = True # Down
    elif button == BUTTON_UP and state["cursor_idx"] > 0: state["cursor_idx"] -= 1; state["dirty_ui"] = True # Up
    elif button in (BUTTON_LEFT, BUTTON_RIGHT) and state["cursor_idx"] < len(state["alarms"]): # Toggle on/off
        a = state["alarms"][state["cursor_idx"]] # Ref alarm
        if not a[5]: # Turn on
            if not a[8] and time.mktime((a[0], a[1], a[2], a[3], a[4], 0, 0, 0)) <= c_sec: state["mode"] = "invalid_time"; state["msg_origin"] = "alarms"; state["dirty_ui"] = True # Invalid past
            else: a[5] = True; queue_save(); state["dirty_ui"] = True # Turn on
        else: # Turn off
            a[5] = False # Turn off
            if state["snooze_idx"] == state["cursor_idx"]: state["snooze_epoch"] = state["snooze_count"] = 0 # Cancel snooze
            queue_save(); state["dirty_ui"] = True # Save
    elif button == BUTTON_T and state["cursor_idx"] < len(state["alarms"]): state["alarms"][state["cursor_idx"]][7] = not state["alarms"][state["cursor_idx"]][7]; queue_save(); state["dirty_ui"] = True # Toggle audio
    elif button == BUTTON_C: # Clear past
        has_past = any(not a[8] and time.mktime((a[0], a[1], a[2], a[3], a[4], 0, 0, 0)) < c_sec for a in state["alarms"]) # Check
        if has_past: state["mode"] = "confirm_clear"; state["clear_confirm_yes"] = False; state["dirty_ui"] = True # Prompt
    elif button == BUTTON_BACKSPACE and state["cursor_idx"] < len(state["alarms"]): state["mode"] = "confirm_delete"; state["del_confirm_yes"] = False; state["dirty_ui"] = True # Delete prompt
    elif button == BUTTON_CENTER: # Select
        state["mode"] = "edit_type"; state["origin"] = "alarms"; state["date_cursor"] = 0; state["dirty_ui"] = True # Setup edit
        if state["cursor_idx"] == len(state["alarms"]): # New
            state["edit_idx"] = -1; state["tmp_daily"] = False; state["tmp_y"] = cy; state["tmp_mo"] = cmo; state["tmp_d"] = cd; state["tmp_h"] = ch; state["tmp_m"] = cm; state["tmp_label"] = ""; state["tmp_audible"] = True # Defaults
        else: # Edit existing
            a = state["alarms"][state["cursor_idx"]]; state["edit_idx"] = state["cursor_idx"] # Ref
            state["tmp_y"] = a[0]; state["tmp_mo"] = a[1]; state["tmp_d"] = a[2]; state["tmp_h"] = a[3]; state["tmp_m"] = a[4]; state["tmp_label"] = a[6]; state["tmp_audible"] = a[7]; state["tmp_daily"] = a[8] # Load values

def handle_input_editor(button, input_mgr, view_manager, t, c_sec): # Handle editor states
    global state # Access state
    cy, cmo, cd, ch, cm = t[0], t[1], t[2], t[3], t[4] # Unpack time
    if state["mode"] == "edit_type": # Step 1
        if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = state.get("origin", "main"); state["dirty_ui"] = True # Back
        elif button in (BUTTON_LEFT, BUTTON_RIGHT, BUTTON_UP, BUTTON_DOWN): state["tmp_daily"] = not state["tmp_daily"]; state["dirty_ui"] = True # Toggle
        elif button == BUTTON_CENTER: state["mode"] = "edit_h" if state["tmp_daily"] else "edit_date"; state["dirty_ui"] = True # Proceed
    elif state["mode"] == "edit_date": # Step 2
        if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = "edit_type"; state["dirty_ui"] = True # Back
        elif button == BUTTON_LEFT: state["date_cursor"] = (state["date_cursor"] - 1) % 3; state["dirty_ui"] = True # Left
        elif button == BUTTON_RIGHT: state["date_cursor"] = (state["date_cursor"] + 1) % 3; state["dirty_ui"] = True # Right
        elif button == BUTTON_UP: # Inc
            if state["date_cursor"] == 0: state["tmp_y"] += 1 if state["use_12h"] else 0; state["tmp_d"] = state["tmp_d"] + 1 if state["tmp_d"] < 31 and not state["use_12h"] else (1 if not state["use_12h"] else state["tmp_d"]) # EU vs US logic
            elif state["date_cursor"] == 1: state["tmp_mo"] = state["tmp_mo"] + 1 if state["tmp_mo"] < 12 else 1 # Month
            elif state["date_cursor"] == 2: state["tmp_d"] = state["tmp_d"] + 1 if state["tmp_d"] < 31 and state["use_12h"] else (1 if state["use_12h"] else state["tmp_d"]); state["tmp_y"] += 1 if not state["use_12h"] else 0 # EU vs US logic
            state["dirty_ui"] = True # Redraw
        elif button == BUTTON_DOWN: # Dec
            if state["date_cursor"] == 0: state["tmp_y"] = max(2024, state["tmp_y"] - 1) if state["use_12h"] else state["tmp_y"]; state["tmp_d"] = state["tmp_d"] - 1 if state["tmp_d"] > 1 and not state["use_12h"] else (31 if not state["use_12h"] else state["tmp_d"]) # EU vs US logic
            elif state["date_cursor"] == 1: state["tmp_mo"] = state["tmp_mo"] - 1 if state["tmp_mo"] > 1 else 12 # Month
            elif state["date_cursor"] == 2: state["tmp_d"] = state["tmp_d"] - 1 if state["tmp_d"] > 1 and state["use_12h"] else (31 if state["use_12h"] else state["tmp_d"]); state["tmp_y"] = max(2024, state["tmp_y"] - 1) if not state["use_12h"] else state["tmp_y"] # EU vs US logic
            state["dirty_ui"] = True # Redraw
        elif button == BUTTON_CENTER: # Val and proceed
            leap = 1 if (state["tmp_y"] % 4 == 0 and (state["tmp_y"] % 100 != 0 or state["tmp_y"] % 400 == 0)) else 0 # Leap
            dim = [31, 28 + leap, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][state["tmp_mo"] - 1] # Days in month
            if state["tmp_d"] > dim: state["mode"] = "invalid_date_format"; state["msg_origin"] = "edit_date"; state["dirty_ui"] = True; return # Check format
            if state["tmp_y"] < cy or (state["tmp_y"] == cy and state["tmp_mo"] < cmo) or (state["tmp_y"] == cy and state["tmp_mo"] == cmo and state["tmp_d"] < cd): state["mode"] = "invalid_time"; state["msg_origin"] = "edit_date"; state["dirty_ui"] = True; return # Check past
            state["mode"] = "edit_h"; state["dirty_ui"] = True # Proceed
    elif state["mode"] == "edit_h": # Step 3
        if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = "edit_type" if state["tmp_daily"] else "edit_date"; state["dirty_ui"] = True # Back
        elif button == BUTTON_DOWN: state["tmp_h"] = (state["tmp_h"] - 1) % 24; state["dirty_ui"] = True # Dec
        elif button == BUTTON_UP: state["tmp_h"] = (state["tmp_h"] + 1) % 24; state["dirty_ui"] = True # Inc
        elif button == BUTTON_CENTER: # Val
            if not state["tmp_daily"] and state["tmp_y"] == cy and state["tmp_mo"] == cmo and state["tmp_d"] == cd and state["tmp_h"] < ch: state["mode"] = "invalid_time"; state["msg_origin"] = "edit_h"; state["dirty_ui"] = True; return # Check past
            state["mode"] = "edit_m"; state["dirty_ui"] = True # Proceed
    elif state["mode"] == "edit_m": # Step 4
        if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = "edit_h"; state["dirty_ui"] = True # Back
        elif button == BUTTON_DOWN: state["tmp_m"] = (state["tmp_m"] - 1) % 60; state["dirty_ui"] = True # Dec
        elif button == BUTTON_UP: state["tmp_m"] = (state["tmp_m"] + 1) % 60; state["dirty_ui"] = True # Inc
        elif button == BUTTON_CENTER: # Val
            if not state["tmp_daily"] and state["tmp_y"] == cy and state["tmp_mo"] == cmo and state["tmp_d"] == cd and state["tmp_h"] == ch and state["tmp_m"] <= cm: state["mode"] = "invalid_time"; state["msg_origin"] = "edit_m"; state["dirty_ui"] = True; return # Check past
            state["mode"] = "edit_l"; state["dirty_ui"] = True # Proceed
    elif state["mode"] == "edit_l": # Step 5
        if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = "edit_m"; state["dirty_ui"] = True # Back
        elif button == BUTTON_CENTER: state["mode"] = "edit_aud"; state["dirty_ui"] = True # Proceed
        elif button == BUTTON_BACKSPACE and len(state["tmp_label"]) > 0: state["tmp_label"] = state["tmp_label"][:-1]; state["dirty_ui"] = True # Backspace
        elif button == BUTTON_SPACE and len(state["tmp_label"]) < 50: state["tmp_label"] += " "; state["dirty_ui"] = True # Space
        elif button >= BUTTON_A and button <= BUTTON_Z and len(state["tmp_label"]) < 50: state["tmp_label"] += chr(button - BUTTON_A + ord('A')); state["dirty_ui"] = True # Letters
        elif button >= BUTTON_0 and button <= BUTTON_9 and len(state["tmp_label"]) < 50: state["tmp_label"] += chr(button - BUTTON_0 + ord('0')); state["dirty_ui"] = True # Numbers
    elif state["mode"] == "edit_aud": # Step 6
        if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = "edit_l"; state["dirty_ui"] = True # Back
        elif button in (BUTTON_LEFT, BUTTON_RIGHT, BUTTON_UP, BUTTON_DOWN): state["tmp_audible"] = not state["tmp_audible"]; state["dirty_ui"] = True # Toggle
        elif button == BUTTON_CENTER: # Save
            final_lbl = state["tmp_label"].strip() or "ALARM" # Clean label
            if not state["tmp_daily"] and time.mktime((state["tmp_y"], state["tmp_mo"], state["tmp_d"], state["tmp_h"], state["tmp_m"], 0, 0, 0)) <= c_sec: state["mode"] = "invalid_time"; state["msg_origin"] = "edit_aud"; state["dirty_ui"] = True; return # Final val
            new_a = [state["tmp_y"], state["tmp_mo"], state["tmp_d"], state["tmp_h"], state["tmp_m"], True, final_lbl, state["tmp_audible"], state["tmp_daily"]] # Make tuple
            if state["edit_idx"] == -1: state["alarms"].append(new_a) # Add
            else: state["alarms"][state["edit_idx"]] = new_a # Update
            queue_save(); state["mode"] = state.get("origin", "main"); state["dirty_ui"] = True # Save and exit
            if state["origin"] == "main": state["cursor_idx"] = 0 # Reset main cursor

INPUT_DISPATCH = { # Map string states to specific input handlers
    "diagnostic": handle_input_diagnostic, # Route diagnostic screen
    "main": handle_input_main, # Route main
    "egg_timer": handle_input_egg_timer, # Route egg timer
    "stopwatch": handle_input_stopwatch, # Route stopwatch
    "countdown": handle_input_countdown, # Route countdown
    "alarms": handle_input_alarms, # Route alarms list
    "ring": handle_input_ring, # Route active ring
    "edit_type": handle_input_editor, # Route editor type
    "edit_date": handle_input_editor, # Route editor date
    "edit_h": handle_input_editor, # Route editor hour
    "edit_m": handle_input_editor, # Route editor minute
    "edit_l": handle_input_editor, # Route editor label
    "edit_aud": handle_input_editor, # Route editor audio
    "confirm_delete": handle_input_modals, # Route delete modal
    "confirm_clear": handle_input_modals, # Route clear modal
    "invalid_time": handle_input_modals, # Route time error
    "invalid_date_format": handle_input_modals, # Route date error
    "hardware_warning": handle_input_modals # Route hardware error
} # End input map

# --- DRAWING DISPATCH FUNCTIONS ---

def draw_diagnostic(view_manager, draw, screen_w, screen_h, theme_color, bg_color): # Render the diagnostic screen
    global state # Access the global state dictionary
    import gc # Import garbage collector to calculate live memory stats
    wifi = view_manager.wifi # Get the WiFi manager instance from the view manager
    
    draw.text(Vector(10, 10), "SYSTEM DIAGNOSTICS", TFT_WHITE) # Draw the header text at the top left
    draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), TFT_WHITE) # Draw a horizontal separator line
    
    validate_hardware_and_time(view_manager) # Update the hardware logic natively
    
    try: # Safely attempt to read OS firmware info natively
        import os # Import OS bindings
        fw_ver = os.uname().release[:16] # Truncate to fit safely on the screen
    except Exception:
        fw_ver = "Unknown" # Fallback if firmware info is inaccessible
        
    b_name = state.get("board_name", "Unknown")[:16] # Get hardware string safely and limit length
    
    # --- RENDER SYSTEM INFORMATION ---
    draw.text(Vector(10, 40), f"App Ver : v{_VERSION}", TFT_LIGHTGREY) # Draw the current application version
    draw.text(Vector(10, 56), f"Firmware: {fw_ver}", TFT_LIGHTGREY) # Draw the Picoware OS version
    
    ram_u = gc.mem_alloc() // 1024 # Calculate currently used RAM in KB
    ram_f = gc.mem_free() // 1024 # Calculate remaining free RAM in KB
    draw.text(Vector(10, 72), f"RAM: {ram_u}KB Used / {ram_f}KB Free", TFT_LIGHTGREY) # Draw live RAM stats
    
    # --- RENDER HARDWARE & NETWORK STATUS ---
    hw_col = TFT_GREEN if state["has_hardware"] else TFT_RED # Choose green if hardware exists, else red
    hw_txt = f"HW: OK ({b_name})" if state["has_hardware"] else f"HW: MISSING ({b_name})" # Set the hardware status text
    draw.text(Vector(10, 96), hw_txt, hw_col) # Draw the hardware status on the screen
    
    if state["has_hardware"]: # Protect against crashing un-supported dummy modules
        ws = wifi.status() # Fetch the current WiFi connection status
        if ws == WIFI_STATE_CONNECTED: # Check if WiFi is actively connected
            ip_str = wifi.device_ip if wifi.device_ip else "Unknown IP" # Safely fetch the IP address
            draw.text(Vector(10, 112), f"WiFi: Connected ({ip_str})", TFT_GREEN) # Draw the connected status and IP
        elif ws == WIFI_STATE_CONNECTING: # Check if WiFi is currently trying to connect
            draw.text(Vector(10, 112), "WiFi: Connecting...", TFT_YELLOW) # Draw the connecting progress status
        elif ws in (WIFI_STATE_ISSUE, WIFI_STATE_TIMEOUT): # Check if WiFi encountered an error
            draw.text(Vector(10, 112), "WiFi: Connection Error", TFT_RED) # Draw the connection error status
        else: # Handle any other WiFi states like idle or disconnected
            draw.text(Vector(10, 112), "WiFi: Idle/Disconnected", TFT_WHITE) # Draw the idle status
    else:
        draw.text(Vector(10, 112), "WiFi: Not Available", TFT_RED) # Display failure if hardware is missing
        
    sync_col = TFT_GREEN if state["time_synced"] else TFT_RED # Choose green if time is synced, else red
    sync_txt = "NTP Time: SYNCED" if state["time_synced"] else "NTP Time: NOT SET" # Set the NTP status text
    draw.text(Vector(10, 128), sync_txt, sync_col) # Draw the NTP status on the screen
    
    # --- RENDER FOOTER HINTS ---
    draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color) # Draw a horizontal footer line
    draw.text(Vector(5, screen_h - 32), "[ENT] Start  [RHT] Sync NTP", TFT_WHITE) # Draw the footer instruction hints for the user
    draw.text(Vector(5, screen_h - 15), "[ESC/BCK] Exit App", TFT_LIGHTGREY) # Provide exit visual hint

def draw_modals(view_manager, draw, screen_w, screen_h, theme_color, bg_color): # Render errors and popups
    global state # Access state
    if state["mode"] in ("invalid_date_format", "invalid_time", "hardware_warning"): # Draw errors
        draw.text(Vector(10, 10), "ERROR", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), TFT_RED) # Header setup
        draw.fill_rectangle(Vector(15, 60), Vector(screen_w - 30, 80), TFT_DARKGREY); draw.rect(Vector(15, 60), Vector(screen_w - 30, 80), TFT_RED) # Error box
        if state["mode"] == "invalid_date_format": draw.text(Vector(25, 75), "INVALID DATE", TFT_RED); draw.text(Vector(25, 100), "This date does not", TFT_WHITE); draw.text(Vector(25, 115), "exist in calendar.", TFT_WHITE) # Date error
        elif state["mode"] == "invalid_time": draw.text(Vector(25, 75), "INVALID DATE/TIME", TFT_RED); draw.text(Vector(25, 100), "Alarm must be set", TFT_WHITE); draw.text(Vector(25, 115), "in the future.", TFT_WHITE) # Time error
        else: draw.text(Vector(25, 75), "FEATURE DISABLED", TFT_RED); draw.text(Vector(25, 100), "Real-time alarms", TFT_WHITE); draw.text(Vector(25, 115), "need Wi-Fi & NTP.", TFT_WHITE) # HW error
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), TFT_RED); draw.text(Vector(5, screen_h - 32), "[Any Key] Go Back", TFT_RED) # Hints
    else: # Draw confirmations
        draw.text(Vector(10, 10), f"MODE: {'DELETE' if state['mode'] == 'confirm_delete' else 'CLEAR'} ALARM(S)", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color) # Header
        draw.fill_rectangle(Vector(15, 60), Vector(screen_w - 30, 80), TFT_DARKGREY); draw.rect(Vector(15, 60), Vector(screen_w - 30, 80), theme_color) # Box
        draw.text(Vector(25, 70), "Delete this alarm?" if state["mode"] == "confirm_delete" else "Clear past alarms?", TFT_WHITE) # Text
        if state["mode"] == "confirm_delete": # Specific logic
            a = state["alarms"][state["cursor_idx"]]; lbl = a[6][:10]; adh = a[3] % 12 if state["use_12h"] else a[3]; adh = 12 if state["use_12h"] and adh == 0 else adh # Unpack
            aampm = ("AM" if a[3] < 12 else "PM") if state["use_12h"] else ""; dt_str = "DAILY" if a[8] else (f"{a[1]:02d}/{a[2]:02d}" if state["use_12h"] else f"{a[2]:02d}.{a[1]:02d}.{a[0]:04d}") # Formatting
            draw.text(Vector(25, 90), f"{dt_str} {adh:02d}:{a[4]:02d} {aampm} [{lbl}]", theme_color) # Draw target
        else: draw.text(Vector(25, 90), "This cannot be undone.", TFT_LIGHTGREY) # Warning text
        is_yes = state["del_confirm_yes"] if state["mode"] == "confirm_delete" else state["clear_confirm_yes"] # Track selected
        draw.fill_rectangle(Vector(30, 115), Vector(60, 20), TFT_BLACK if is_yes else TFT_DARKGREY); draw.text(Vector(45, 118), "YES", theme_color if is_yes else TFT_LIGHTGREY) # YES
        draw.fill_rectangle(Vector(140, 115), Vector(60, 20), TFT_BLACK if not is_yes else TFT_DARKGREY); draw.text(Vector(160, 118), "NO", theme_color if not is_yes else TFT_LIGHTGREY) # NO
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color); draw.text(Vector(5, screen_h - 32), "[L/R] Select [ENT] Confirm", theme_color); draw.text(Vector(5, screen_h - 15), "[ESC] Cancel", TFT_LIGHTGREY) # Hints

def draw_ring(view_manager, draw, screen_w, screen_h, theme_color, bg_color): # Render active ringing
    global state # Access state
    if state["ringing_idx"] == -2: display_lbl = "EGG READY!"; hint_str = "[ENT/O] Dismiss" # Egg
    elif state["ringing_idx"] == -3: display_lbl = "TIME'S UP!"; hint_str = "[ENT/O] Dismiss" # CD
    else: display_lbl = state["alarms"][state["ringing_idx"]][6][:15] + "..." if len(state["alarms"][state["ringing_idx"]][6]) > 15 else state["alarms"][state["ringing_idx"]][6]; hint_str = f"[S/ENT]Snooze({5-state['snooze_count']}) [O]Off" if state["snooze_count"] < 5 else "[O]Off (Max Snooze)" # Standard alarm string
    draw.fill_rectangle(Vector(0, 0), Vector(screen_w, screen_h), TFT_WHITE if state["ring_flash"] else TFT_BLACK) # Flash bg
    draw.text(Vector(30, 60), "ALARM!", TFT_BLACK if state["ring_flash"] else theme_color, 3) # Title
    draw.text(Vector(10, 100), display_lbl, TFT_BLACK if state["ring_flash"] else theme_color, 2) # Label
    draw.text(Vector(10, 150), hint_str, TFT_BLACK if state["ring_flash"] else theme_color) # Hint

def draw_egg_timer(view_manager, draw, screen_w, screen_h, theme_color, bg_color): # Render egg timer
    global state # Access state
    draw.text(Vector(10, 10), "MODE: EGG TIMER", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color) # Header
    if state["egg_end"] > 0: # Running
        rem = max(0, state["egg_end"] - int(time.time())); m, s = divmod(rem, 60) # Calc
        draw.text(Vector(15, 40), f"Run: {m:02d}:{s:02d}", TFT_GREEN, 2) # Live timer
    else: draw.text(Vector(15, 45), "Status: Inactive", TFT_LIGHTGREY) # Inactive
    draw.text(Vector(15, 70), "Select Preset:", TFT_LIGHTGREY) # Header
    for i, (_, lbl) in enumerate(_EGG_PRESETS): # Iterate presets
        c = theme_color if state["egg_preset"] == i else TFT_LIGHTGREY # Highlight color
        if state["egg_preset"] == i: draw.text(Vector(10, 90 + i*20), ">", theme_color) # Cursor
        draw.text(Vector(25, 90 + i*20), lbl, c) # Text
    draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color) # Footer line
    draw.text(Vector(5, screen_h - 32), "[UP/DN] Nav [ENT] Apply", theme_color) # Hint

def draw_stopwatch(view_manager, draw, screen_w, screen_h, theme_color, bg_color): # Render stopwatch
    global state # Access state
    draw.text(Vector(10, 10), "MODE: STOPWATCH", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color) # Header
    current_ms = state["sw_accum"] # Fetch ms
    if state["sw_run"]: current_ms += time.ticks_diff(time.ticks_ms(), state["sw_start"]) # Add live ms
    ms = (current_ms % 1000) // 100; sec = (current_ms // 1000) % 60; mins = (current_ms // 60000) % 60; hrs = (current_ms // 3600000) # Calc
    sw_text = f"{hrs:02d}:{mins:02d}:{sec:02d}" if hrs > 0 else f"{mins:02d}:{sec:02d}.{ms:01d}" # Format string
    draw.text(Vector((screen_w // 2) - 85, 70), sw_text, theme_color, 4) # Big text
    stat_str = "RUNNING" if state["sw_run"] else "STOPPED" # Status
    draw.text(Vector((screen_w // 2) - 30, 130), stat_str, TFT_GREEN if state["sw_run"] else TFT_LIGHTGREY) # Status indicator
    draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color) # Footer line
    draw.text(Vector(5, screen_h - 32), "[ENT] Start/Stop [R] Reset", theme_color) # Hints

def draw_countdown(view_manager, draw, screen_w, screen_h, theme_color, bg_color): # Render countdown
    global state # Access state
    draw.text(Vector(10, 10), "MODE: COUNTDOWN", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color) # Header
    if state["cd_end"] > 0: # Running
        rem = max(0, state["cd_end"] - int(time.time())); h = rem // 3600; m = (rem % 3600) // 60; s = rem % 60 # Calc
        draw.text(Vector((screen_w // 2) - 85, 70), f"{h:02d}:{m:02d}:{s:02d}", theme_color, 4) # Draw big time
        draw.text(Vector((screen_w // 2) - 30, 130), "RUNNING", TFT_GREEN) # Status
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color); draw.text(Vector(5, screen_h - 32), "[ENT] Cancel", theme_color) # Hint
    else: # Setup
        draw.text(Vector(15, 45), "Set Duration:", TFT_LIGHTGREY) # Title
        c0 = theme_color if state["cd_cursor"] == 0 else TFT_WHITE; c1 = theme_color if state["cd_cursor"] == 1 else TFT_WHITE; c2 = theme_color if state["cd_cursor"] == 2 else TFT_WHITE # Cursor colors
        st_x = (screen_w // 2) - 85 # X-offset
        draw.text(Vector(st_x, 70), f"{state['cd_h']:02d}", c0, 4); draw.text(Vector(st_x + 50, 70), ":", TFT_LIGHTGREY, 4) # Hours
        draw.text(Vector(st_x + 70, 70), f"{state['cd_m']:02d}", c1, 4); draw.text(Vector(st_x + 120, 70), ":", TFT_LIGHTGREY, 4) # Mins
        draw.text(Vector(st_x + 140, 70), f"{state['cd_s']:02d}", c2, 4) # Secs
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color); draw.text(Vector(5, screen_h - 32), "[L/R]Sel [U/D]Adj [ENT]Go [R]Rst", theme_color) # Hints

def draw_main(view_manager, draw, screen_w, screen_h, theme_color, bg_color): # Render main dashboard
    global state # Access state
    c_idx = state["cursor_idx"] # Cursor pos
    draw.text(Vector(10, 10), f"Eggtimer {_VERSION}", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color) # Header
    draw.text(Vector(15, 42), "CURRENT TIME:", TFT_LIGHTGREY); draw.fill_rectangle(Vector(15, 55), Vector(screen_w - 30, 43), TFT_DARKGREY); draw.rect(Vector(15, 55), Vector(screen_w - 30, 43), theme_color) # Clock box
    t = time.localtime(); dh = t[3] % 12 if state["use_12h"] else t[3]; dh = 12 if state["use_12h"] and dh == 0 else dh # 12/24 clock logic
    time_str = "{:02d}:{:02d}:{:02d} {}".format(dh, t[4], t[5], "AM" if t[3] < 12 else "PM") if state["use_12h"] else "{:02d}:{:02d}:{:02d}".format(t[3], t[4], t[5]) # Format time
    draw.text(Vector(40 if not state["use_12h"] else 20, 58), time_str, theme_color, 2) # Draw clock
    
    is_rto_ok = state.get("time_synced", False) # Flag confirming NTP real-time clock is available
    
    n_str = "Next: None Active"; min_d = 9999999999; c_sec = time.time(); next_a = None; is_snooze_next = False # Next calc logic setup
    if not is_rto_ok: # Catch missing real-time sync
        n_str = "Next: NTP Not Synced" # Override text if clock invalid
    else: # Only search for next alarm if NTP is synced
        for a in state["alarms"]: # Find next active alarm
            if a[5]: # Active
                a_sec = time.mktime((t[0], t[1], t[2], a[3], a[4], 0, 0, 0)) + (86400 if a[8] and (a[3] < t[3] or (a[3] == t[3] and a[4] <= t[4])) else 0) if a[8] else time.mktime((a[0], a[1], a[2], a[3], a[4], 0, 0, 0)) # Calc epoch
                d = a_sec - c_sec # Compare difference
                if 0 < d < min_d: min_d = d; next_a = a; is_snooze_next = False # Update nearest
        if state["snooze_epoch"] > 0 and 0 < state["snooze_epoch"] - c_sec < min_d: next_a = state["alarms"][state["snooze_idx"]]; is_snooze_next = True # Snooze override
        if next_a: # Form string if found
            lbl = next_a[6][:4] + "Zz" if is_snooze_next else next_a[6][:6]; nh, nm = (time.localtime(state["snooze_epoch"])[3:5] if is_snooze_next else next_a[3:5]) # Unpack string
            nmo, nd = (time.localtime(state["snooze_epoch"])[1:3] if is_snooze_next else (next_a[1:3] if not next_a[8] else (t[1], t[2]))) # Unpack month
            ny = time.localtime(state["snooze_epoch"])[0] if is_snooze_next else (next_a[0] if not next_a[8] else t[0]) # Unpack year
            ndh = nh % 12 if state["use_12h"] else nh; ndh = 12 if state["use_12h"] and ndh == 0 else ndh; nampm = ("A" if nh < 12 else "P") if state["use_12h"] else "" # Format AM/PM
            n_str = ("Next: DAILY " if next_a[8] and not is_snooze_next else f"Next: {nmo:02d}/{nd:02d} " if state["use_12h"] else f"Next: {nd:02d}.{nmo:02d}.{ny:04d} ") + f"{ndh:02d}:{nm:02d}{nampm} [{lbl}]" # Assemble string
    
    draw.text(Vector(20, 80), n_str, TFT_WHITE) # Draw next summary
    
    in_y = 102; r_height = 16; egg_str = "RUN" if state["egg_end"] > 0 else ""; sw_str = "RUN" if state.get("sw_run", False) else ""; cd_str = "RUN" if state.get("cd_end", 0) > 0 else "" # Status badges
    for i, (txt, cnt) in enumerate([("Manage Alarms", f"[{len(state['alarms'])}]"), ("Egg Timer", egg_str), ("Stopwatch", sw_str), ("Countdown", cd_str), ("Options Menu", ""), ("View Help", "")]): # List items
        r_y = in_y + (i * 16) # Y-offset for row
        is_disabled = (i == 0 and not is_rto_ok) # Identify if the specific item is disabled (Manage Alarms)
        
        # Color resolution mapping
        if is_disabled: # Handling for grayed-out items
            col = TFT_DARKGREY # Main text gets dark grey
            b_col = TFT_DARKGREY # Badge box gets dark grey
            badge_col = TFT_DARKGREY # Badge text gets dark grey
        else: # Standard item rendering
            col = theme_color if c_idx == i else TFT_LIGHTGREY # Main text gets theme color if selected
            b_col = theme_color if c_idx == i else TFT_DARKGREY # Badge box gets theme color if selected
            badge_col = theme_color if c_idx == i else TFT_WHITE # Badge text logic
            
        if c_idx == i: # Selection cursor drawing
            draw.fill_rectangle(Vector(0, r_y - 2), Vector(screen_w, r_height), TFT_DARKGREY) # Background highlight bar
            draw.text(Vector(screen_w - 20, r_y + 1), "<", TFT_DARKGREY if is_disabled else theme_color) # Cursor arrow
            
        draw.text(Vector(15, r_y + 1), txt, col) # Render the main row text
        
        if cnt: # Badge rendering
            draw.rect(Vector(160, r_y - 2), Vector(60, r_height), b_col) # Draw badge box outline
            draw.text(Vector(170, r_y + 1), cnt, badge_col) # Draw badge text internally
            
    draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color) # Footer line
    draw.text(Vector(5, screen_h - 32), "[M]List [N]New [O]Opt [ESC]Exit", theme_color) # Top hint row
    
    hint_row_2 = "[UP/DN]Nav [ENT]Select" + ("  [D]Diag" if state.get("show_diagnostics", False) else "") # Conditionally append D shortcut
    draw.text(Vector(5, screen_h - 15), hint_row_2, TFT_LIGHTGREY) # Bottom hint row

def draw_alarms(view_manager, draw, screen_w, screen_h, theme_color, bg_color): # Render alarms list
    global state # Access state
    c_idx = state["cursor_idx"]; list_len = len(state["alarms"]) + 1 # Setup vars
    draw.text(Vector(10, 10), "MODE: ALARMS LIST", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color) # Header
    c_sec = time.time(); has_past = False # Calc state
    for i in range(min(4, list_len)): # Max 4 items shown
        idx = c_idx - (c_idx % 4) + i # Paginate logic
        if idx < list_len: # Bounds check
            r_y = 50 + (i * 35) # Y offset
            if idx == c_idx: draw.fill_rectangle(Vector(0, r_y - 4), Vector(screen_w, 30), TFT_DARKGREY) # Cursor bar
            if idx < len(state["alarms"]): # Alarm items
                a = state["alarms"][idx]; is_past = not a[8] and time.mktime((a[0], a[1], a[2], a[3], a[4], 0, 0, 0)) < c_sec # Calc past due
                if is_past: has_past = True # Flag past exist
                t_col = theme_color if idx == c_idx else TFT_LIGHTGREY; label_color = TFT_RED if is_past else t_col # Set color
                draw.text(Vector(5, r_y + 1), f"{a[6][:6]}:", label_color); draw.rect(Vector(65, r_y - 4), Vector(250, 30), theme_color if idx == c_idx else TFT_DARKGREY) # Draw label/box
                stat_str = ("ON*" if a[7] else "ON ") if a[5] else ("OFF*" if a[7] else "OFF "); adh = a[3] % 12 if state["use_12h"] else a[3]; adh = 12 if state["use_12h"] and adh == 0 else adh # Unpack data
                aampm = ("A" if a[3] < 12 else "P") if state["use_12h"] else ""; a_str = f"DAILY {adh:02d}:{a[4]:02d}{aampm} [{stat_str}]" if a[8] else (f"{a[1]:02d}/{a[2]:02d} " if state["use_12h"] else f"{a[2]:02d}.{a[1]:02d}.{a[0]:04d} ") + f"{adh:02d}:{a[4]:02d}{aampm} [{stat_str}]" # Format text
                draw.text(Vector(70, r_y + 1), a_str, TFT_RED if is_past else (theme_color if idx == c_idx else TFT_WHITE)) # Draw text
            else: draw.text(Vector(15, r_y + 1), "+ Create New Alarm", theme_color if idx == c_idx else TFT_LIGHTGREY) # Create New item
    draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color); draw.text(Vector(5, screen_h - 32), "[L/R]Tgl " + ("[C]Clr " if has_past else "") + "[N]New [ESC]Back", theme_color); draw.text(Vector(5, screen_h - 15), "[UP/DN]Nav [T]Snd [BS]Del [ENT]Edit", TFT_LIGHTGREY) # Footers

def draw_editor(view_manager, draw, screen_w, screen_h, theme_color, bg_color): # Render unified editor views
    global state # Access state
    draw.text(Vector(10, 10), "MODE: EDIT ALARM" if state.get("edit_idx", -1) != -1 else "MODE: ADD ALARM", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color) # Header
    out_y = 45; draw.fill_rectangle(Vector(15, out_y + 25), Vector(screen_w - 30, 80 if state["mode"] == "edit_l" else 35), TFT_DARKGREY); draw.rect(Vector(15, out_y + 25), Vector(screen_w - 30, 80 if state["mode"] == "edit_l" else 35), theme_color) # Editor box
    if state["mode"] == "edit_type": draw.text(Vector(15, out_y + 5), "ALARM TYPE:", TFT_LIGHTGREY); draw.text(Vector(40, out_y + 33), f"< {'DAILY' if state['tmp_daily'] else 'SPECIFIC DATE'} >", theme_color, 2) # Type switch
    elif state["mode"] == "edit_date": # Date editor
        draw.text(Vector(15, out_y + 5), "SET DATE:", TFT_LIGHTGREY) # Title
        cy, cm, cd = (state["tmp_y"], state["tmp_mo"], state["tmp_d"]) if state["use_12h"] else (state["tmp_d"], state["tmp_mo"], state["tmp_y"]); c0, c1, c2 = (theme_color if state["date_cursor"] == i else TFT_WHITE for i in range(3)) # Cursor color mapping logic
        if state["use_12h"]: draw.text(Vector(30, out_y+33), f"{cy:04d}", c0, 2); draw.text(Vector(100, out_y+33), "-", TFT_LIGHTGREY, 2); draw.text(Vector(120, out_y+33), f"{cm:02d}", c1, 2); draw.text(Vector(160, out_y+33), "-", TFT_LIGHTGREY, 2); draw.text(Vector(180, out_y+33), f"{cd:02d}", c2, 2) # Format US YYYY-MM-DD
        else: draw.text(Vector(30, out_y+33), f"{cy:02d}", c0, 2); draw.text(Vector(70, out_y+33), ".", TFT_LIGHTGREY, 2); draw.text(Vector(90, out_y+33), f"{cm:02d}", c1, 2); draw.text(Vector(130, out_y+33), ".", TFT_LIGHTGREY, 2); draw.text(Vector(150, out_y+33), f"{cd:04d}", c2, 2) # Format EU DD.MM.YYYY
    elif state["mode"] in ("edit_h", "edit_m"): # Time editor
        draw.text(Vector(15, out_y + 5), "SET TIME:", TFT_LIGHTGREY); th = state["tmp_h"] % 12 if state["use_12h"] else state["tmp_h"]; th = 12 if state["use_12h"] and th == 0 else th # Title
        draw.text(Vector(60, out_y + 33), f"{th:02d}", theme_color if state["mode"] == "edit_h" else TFT_WHITE, 2); draw.text(Vector(100, out_y + 33), ":", TFT_LIGHTGREY, 2); draw.text(Vector(120, out_y + 33), f"{state['tmp_m']:02d}", theme_color if state["mode"] == "edit_m" else TFT_WHITE, 2) # H M text
        if state["use_12h"]: draw.text(Vector(150, out_y + 33), "AM" if state["tmp_h"] < 12 else "PM", TFT_LIGHTGREY, 2) # Draw AM/PM flag
    elif state["mode"] == "edit_l": # Label editor
        draw.text(Vector(15, out_y + 5), f"SET LABEL ({len(state['tmp_label'])}/50):", TFT_LIGHTGREY); v_str = state["tmp_label"] + ("_" if (int(time.time()) % 2 == 0) else "") # Label with blinker
        for i in range(0, len(v_str), 18): draw.text(Vector(20, out_y + 30 + (i // 18) * 20), v_str[i:i+18], TFT_WHITE, 2) # Wordwrap render
    elif state["mode"] == "edit_aud": draw.text(Vector(15, out_y + 5), "AUDIBLE SOUND:", TFT_LIGHTGREY); draw.text(Vector(80, out_y + 33), f"< {'YES' if state['tmp_audible'] else 'NO '} >", theme_color, 2) # Audio editor
    draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color); draw.text(Vector(5, screen_h - 32), "[ESC] Cancel / Back", theme_color); draw.text(Vector(5, screen_h - 15), "[ENT] Next / Save", TFT_LIGHTGREY) # Footer hints

VIEW_DISPATCH = { # Map string states to specific view handlers
    "diagnostic": draw_diagnostic, # Route diagnostic screen
    "main": draw_main, # Route main
    "alarms": draw_alarms, # Route alarms
    "stopwatch": draw_stopwatch, # Route stopwatch
    "countdown": draw_countdown, # Route countdown
    "egg_timer": draw_egg_timer, # Route egg_timer
    "ring": draw_ring, # Route ringing
    "edit_type": draw_editor, # Route editor type
    "edit_date": draw_editor, # Route editor date
    "edit_h": draw_editor, # Route editor hour
    "edit_m": draw_editor, # Route editor min
    "edit_l": draw_editor, # Route editor label
    "edit_aud": draw_editor, # Route editor audio
    "confirm_delete": draw_modals, # Route delete modal
    "confirm_clear": draw_modals, # Route clear modal
    "invalid_time": draw_modals, # Route time error
    "invalid_date_format": draw_modals, # Route date error
    "hardware_warning": draw_modals # Route hardware warning
} # End view map

def process_input(button, input_mgr, view_manager, t, c_sec): # Core lightweight input dispatcher
    global show_help, show_options, help_scroll, state # Access global states
    if show_help: # Overlay logic layer takes priority
        if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_H): # Dismiss help
            show_help = False; help_scroll = 0; state["dirty_ui"] = True # Reset scroll and close
            gc.collect() # Instantly sweep RAM after closing the massive text list
        elif button == BUTTON_DOWN: help_scroll += 1; state["dirty_ui"] = True # Scroll down
        elif button == BUTTON_UP: help_scroll = max(0, help_scroll - 1); state["dirty_ui"] = True # Scroll up
        input_mgr.reset(); return # Exit out of standard handlers
    elif show_options: # Overlay logic layer takes priority
        if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_CENTER): 
            show_options = False; state["dirty_ui"] = True; queue_save() # Dismiss
            gc.collect() # Instantly sweep RAM after destroying the heavy options UI
        elif button == BUTTON_DOWN: state["options_cursor_idx"] = (state["options_cursor_idx"] + 1) % 7; state["dirty_ui"] = True # Down
        elif button == BUTTON_UP: state["options_cursor_idx"] = (state["options_cursor_idx"] - 1) % 7; state["dirty_ui"] = True # Up
        elif button == BUTTON_RIGHT: # Increment value
            if state["options_cursor_idx"] == 0: state["theme_idx"] = (state["theme_idx"] + 1) % len(_THEMES) # Next theme
            elif state["options_cursor_idx"] == 1: state["bg_r"] = (state["bg_r"] + 5) % 256 # Red
            elif state["options_cursor_idx"] == 2: state["bg_g"] = (state["bg_g"] + 5) % 256 # Green
            elif state["options_cursor_idx"] == 3: state["bg_b"] = (state["bg_b"] + 5) % 256 # Blue
            elif state["options_cursor_idx"] == 4: state["use_12h"] = not state["use_12h"] # 12h/24h toggle
            elif state["options_cursor_idx"] == 5: state["snooze_min"] = state["snooze_min"] + 1 if state["snooze_min"] < 60 else 1 # Snooze
            elif state["options_cursor_idx"] == 6: state["show_diagnostics"] = not state.get("show_diagnostics", False) # Toggle Boot Diag
            state["dirty_ui"] = True; queue_save() # Save
        elif button == BUTTON_LEFT: # Decrement value
            if state["options_cursor_idx"] == 0: state["theme_idx"] = (state["theme_idx"] - 1) % len(_THEMES) # Prev theme
            elif state["options_cursor_idx"] == 1: state["bg_r"] = (state["bg_r"] - 5) % 256 # Red
            elif state["options_cursor_idx"] == 2: state["bg_g"] = (state["bg_g"] - 5) % 256 # Green
            elif state["options_cursor_idx"] == 3: state["bg_b"] = (state["bg_b"] - 5) % 256 # Blue
            elif state["options_cursor_idx"] == 4: state["use_12h"] = not state["use_12h"] # 12h/24h toggle
            elif state["options_cursor_idx"] == 5: state["snooze_min"] = state["snooze_min"] - 1 if state["snooze_min"] > 1 else 60 # Snooze
            elif state["options_cursor_idx"] == 6: state["show_diagnostics"] = not state.get("show_diagnostics", False) # Toggle Boot Diag
            state["dirty_ui"] = True; queue_save() # Save
        input_mgr.reset(); return # Exit out of standard handlers

    handler = INPUT_DISPATCH.get(state["mode"]) # Fetch function based on current string state
    if handler: handler(button, input_mgr, view_manager, t, c_sec) # Trigger specific function cleanly
    input_mgr.reset() # Clear input buffer globally

def draw_view(view_manager): # Core lightweight rendering dispatcher
    global help_scroll # Access references
    draw = view_manager.draw; screen_w = draw.size.x; screen_h = draw.size.y # Dimensions
    bg_color = rgb_to_565(state["bg_r"], state["bg_g"], state["bg_b"]); theme_color = _THEMES[state["theme_idx"]][1] # Colors
    
    if not (show_options or state["mode"] == "ring"): # Wipes background cleanly
        draw.clear(); draw.fill_rectangle(Vector(0, 0), Vector(screen_w, screen_h), bg_color) # Base fill
        
    if show_help: # Overlay render logic
        lines = get_help_lines() # Fetch dynamic text lines
        max_scroll = max(0, len(lines) - 12) # Calculate maximum scroll depth to leave room for footer
        help_scroll = min(help_scroll, max_scroll) # Clamp scroll position to prevent scrolling out of bounds
        
        for i in range(12): # Render up to 12 visible lines
            if help_scroll + i < len(lines): # Ensure we don't exceed list bounds
                draw.text(Vector(10, 10 + i * 20), lines[help_scroll + i], TFT_WHITE) # Draw line text
                
        # Draw solid footer over the bottom text to ensure UI separation
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 40), bg_color) # Solid masking block
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color) # Divider line
        draw.text(Vector(5, screen_h - 32), "[UP/DN] Scroll  [ESC/H] Close", theme_color) # Navigation hints

    elif show_options: # Overlay render logic
        draw.fill_rectangle(Vector(0, 0), Vector(screen_w, screen_h), TFT_DARKGREY); draw.fill_rectangle(Vector(0, 0), Vector(screen_w, 30), theme_color); draw.text(Vector(10, 10), "OPTIONS MENU", TFT_WHITE) # Setup bg
        o_idx = state["options_cursor_idx"] # Unpack cursor
        c0 = theme_color if o_idx == 0 else TFT_LIGHTGREY; draw.fill_rectangle(Vector(0, 36), Vector(screen_w, 22), TFT_BLACK) if o_idx == 0 else None; draw.text(Vector(15, 40), "Theme Color:", c0); draw.text(Vector(140, 40), f"< {_THEMES[state['theme_idx']][0]} >", c0) # Draw Row
        c1 = theme_color if o_idx == 1 else TFT_LIGHTGREY; draw.fill_rectangle(Vector(0, 60), Vector(screen_w, 22), TFT_BLACK) if o_idx == 1 else None; draw.text(Vector(15, 64), "Back R (0-255):", c1); draw.text(Vector(140, 64), f"< {state['bg_r']} >", c1) # Draw Row
        c2 = theme_color if o_idx == 2 else TFT_LIGHTGREY; draw.fill_rectangle(Vector(0, 84), Vector(screen_w, 22), TFT_BLACK) if o_idx == 2 else None; draw.text(Vector(15, 88), "Back G (0-255):", c2); draw.text(Vector(140, 88), f"< {state['bg_g']} >", c2) # Draw Row
        c3 = theme_color if o_idx == 3 else TFT_LIGHTGREY; draw.fill_rectangle(Vector(0, 108), Vector(screen_w, 22), TFT_BLACK) if o_idx == 3 else None; draw.text(Vector(15, 112), "Back B (0-255):", c3); draw.text(Vector(140, 112), f"< {state['bg_b']} >", c3) # Draw Row
        c4 = theme_color if o_idx == 4 else TFT_LIGHTGREY; draw.fill_rectangle(Vector(0, 132), Vector(screen_w, 22), TFT_BLACK) if o_idx == 4 else None; draw.text(Vector(15, 136), "Time Format:", c4); draw.text(Vector(140, 136), f"< {'12 Hour' if state['use_12h'] else '24 Hour'} >", c4) # Draw Row
        c5 = theme_color if o_idx == 5 else TFT_LIGHTGREY; draw.fill_rectangle(Vector(0, 156), Vector(screen_w, 22), TFT_BLACK) if o_idx == 5 else None; draw.text(Vector(15, 160), "Snooze (Min):", c5); draw.text(Vector(140, 160), f"< {state['snooze_min']} >", c5) # Draw Row
        c6 = theme_color if o_idx == 6 else TFT_LIGHTGREY; draw.fill_rectangle(Vector(0, 180), Vector(screen_w, 22), TFT_BLACK) if o_idx == 6 else None; draw.text(Vector(15, 184), "Boot Diag:", c6); draw.text(Vector(140, 184), f"< {'ON ' if state.get('show_diagnostics', False) else 'OFF'} >", c6) # Draw Row
        draw.text(Vector(15, 204), "Preview:", TFT_LIGHTGREY); draw.rect(Vector(90, 202), Vector(135, 14), theme_color); draw.fill_rectangle(Vector(91, 203), Vector(133, 12), bg_color) # Draw box
        draw.text(Vector(5, screen_h - 20), "[L/R] Edit  [ENT] Close", TFT_WHITE) # Footer hints
    else: # View dispatcher layer
        handler = VIEW_DISPATCH.get(state["mode"]) # Fetch function based on current string state
        if handler: handler(view_manager, draw, screen_w, screen_h, theme_color, bg_color) # Inject context into correct function

    draw.swap(); state["dirty_ui"] = False # Push frame buffer to hardware screen and reset flag

def start(view_manager): # App initialize hook
    global storage, state, show_help, show_options, help_box, _last_saved_json # Access globals
    
    state = DEFAULT_STATE.copy() # Guarantee pure clean state on app start
    show_help = False # Reset help overlay
    show_options = False # Reset options overlay
    help_box = None # Reset UI elements
    _last_saved_json = "" # Reset caching
    storage = view_manager.storage # Hook into system storage API
    
    validate_hardware_and_time(view_manager) # Run the hardware module check safely using the OS-provided property
    validate_and_load_settings() # Process saved data and apply user settings
    
    # Check the user preference toggle before showing the diagnostic screen
    if state.get("show_diagnostics", False): 
        state["mode"] = "diagnostic" # Show diagnostics if enabled
    else:
        state["mode"] = "main" # Boot straight to the main menu if disabled
    
    state["dirty_ui"] = True # Force a screen render on the first app tick
    state["last_s"] = -1 # Setup seconds tracking logic
    return True # Complete initialization seamlessly

def run(view_manager): # App main event loop
    global state # Access globals
    draw = view_manager.draw; input_mgr = view_manager.input_manager; button = input_mgr.button # Process context
    t = time.localtime(); c_sec = time.time() # Pull latest timing metrics
    
    check_time_and_alarms(t, c_sec) # Process alarm triggers in background
    
    if button == -1 and not state["dirty_ui"] and not state["dirty_save"]: return # Optimize tick rate out if inactive
    if button != -1: process_input(button, input_mgr, view_manager, t, c_sec) # Pass inputs to handler
    
    # FIX: Stop executing immediately if view_manager.back() destroyed the app state
    if state is None: return 
    
    if state["dirty_save"] and button == -1: # Execute background saving during idle times
        if state["save_timer"] > 0: state["save_timer"] -= 1 # Countdown before save tick
        else: save_settings() # Trigger flash disk write
        
    if state["dirty_ui"]: draw_view(view_manager) # Trigger screen render if view changed

def stop(view_manager): # App shutdown hook
    global state, storage, help_box, _last_saved_json # Access globals
    save_settings() # Commit anything remaining
    handle_audio_silence() # Safe cleanup
    if state is not None: state.clear() # Nullify dictionaries
    state = None # Destroy reference
    storage = None # Destroy reference
    if help_box is not None: # Catch and safely destroy UI element
        help_box = None # Clear reference
    _last_saved_json = "" # Reset variable memory
    gc.collect() # Safe cleanup and exit

