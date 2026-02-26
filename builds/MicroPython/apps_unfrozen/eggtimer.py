from micropython import const # Import const for memory optimization
import time # Import time for real-time clock and timer functions
import os # Import os to check the hardware board ID for Pico 2 W
from picoware.system.vector import Vector # Import Vector for 2D coordinate handling
from picoware.system.colors import ( # Import standard system colors
    TFT_ORANGE, TFT_DARKGREY, TFT_LIGHTGREY, TFT_WHITE, # Import UI colors
    TFT_BLACK, TFT_BLUE, TFT_YELLOW, TFT_CYAN, TFT_GREEN, TFT_RED # Import theme colors
) # End color imports
from picoware.system.buttons import ( # Import primary control buttons
    BUTTON_BACK, BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, # Nav buttons
    BUTTON_CENTER, BUTTON_BACKSPACE, BUTTON_H, BUTTON_ESCAPE, BUTTON_O # Action buttons
) # End primary button imports

try: # Attempt to import extended keyboard keys
    from picoware.system.buttons import BUTTON_A, BUTTON_Z, BUTTON_0, BUTTON_9, BUTTON_SPACE, BUTTON_N, BUTTON_T, BUTTON_S, BUTTON_C, BUTTON_M, BUTTON_R # Import alpha-numeric and shortcut keys
except ImportError: # Fallback if extended keys are not available
    BUTTON_A = BUTTON_Z = BUTTON_0 = BUTTON_9 = BUTTON_SPACE = BUTTON_N = BUTTON_T = BUTTON_S = BUTTON_C = BUTTON_M = BUTTON_R = -99 # Assign dummy values to avoid crashes

try: # Attempt to initialize hardware buzzers
    from machine import Pin, PWM # Import Pin and PWM for audio generation
    buzzer_l = PWM(Pin(28)) # Initialize left buzzer on Pin 28
    buzzer_r = PWM(Pin(27)) # Initialize right buzzer on Pin 27
    buzzer_l.duty_u16(0) # Silence left buzzer initially
    buzzer_r.duty_u16(0) # Silence right buzzer initially
    buzzer = (buzzer_l, buzzer_r) # Tuple storing both buzzers
except: # Fallback if audio hardware is missing
    buzzer = None # Set buzzer reference to None

from picoware.gui.textbox import TextBox # Import TextBox for the help overlay
import json # Import json for settings serialization
import gc # Import garbage collector to manage RAM

_SETTINGS_FILE = "/picoware/apps/eggtimer_settings.json" # Define save path for configuration

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

_VERSION = "0.06" # App version string

# Extended help text with updated hardware requirements, credits, and date
_HELP_TEXT = f"EGGTIMER\nVersion {_VERSION}\n----------------\nAlarms, egg timer,\nstopwatch & countdown.\nReq: Pico 2 W (Wi-Fi)\n\nCREDITS:\nmade by Slasher006\nwith the help of Gemini\nDate: 2026-02-26\n\nSHORTCUTS:\n[L/R] Toggle ON/OFF\n[T] Toggle Audio\n[C] Clear Past\n[BS] Delete Alarm\n[H] Help Overlay\n[O] Options Menu\n[N] New Alarm\n[M] Alarm List\n[R] Reset Timers\n[ESC] Exit App\n\nCONTROLS:\n[UP/DN] Navigate\n[ENTER] Select/Save" # Help screen content

DEFAULT_STATE = { # Dictionary holding all default application variables
    "theme_idx": 0, # Default theme index (Green)
    "bg_r": 0, # Default background Red value
    "bg_g": 0, # Default background Green value
    "bg_b": 0, # Default background Blue value
    "use_12h": False, # Flag for 12-hour AM/PM format
    "snooze_min": 5, # Default snooze duration in minutes
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
    "mode": "main", # Current application screen/mode
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
    "clear_confirm_yes": False # State of clear all confirmation prompt
} # End default state dictionary

state = DEFAULT_STATE.copy() # Initialize live state from defaults
storage = None # Global reference to system storage
show_help = False # Global flag for help overlay visibility
show_options = False # Global flag for options overlay visibility
help_box = None # Global reference to the TextBox UI element
_last_saved_json = "" # Cache of last saved JSON to avoid redundant writes

def rgb_to_565(r, g, b): # Function to convert RGB888 to RGB565 format
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3) # Bitwise conversion for TFT display

def queue_save(): # Function to delay disk writes and save flash memory
    global state # Access global state
    state["dirty_save"] = True # Mark state as needing a save
    state["save_timer"] = 60 # Wait ~60 cycles before writing

def save_settings(): # Function to commit settings to disk
    global _last_saved_json, state # Access globals
    if not storage: return # Abort if storage is unavailable
    try: # Catch IO errors safely
        exclude_keys = ("dirty_ui", "mode", "cursor_idx", "options_cursor_idx", "tmp_y", "tmp_mo", "tmp_d", "date_cursor", "tmp_h", "tmp_m", "tmp_label", "tmp_audible", "edit_idx", "ringing_idx", "last_s", "ring_flash", "dirty_save", "save_timer", "origin", "del_confirm_yes", "clear_confirm_yes", "snooze_epoch", "snooze_idx", "last_trig_m", "snooze_count", "msg_origin", "tmp_daily", "egg_end", "sw_run", "sw_start", "sw_accum", "last_sw_ms", "cd_end", "cd_cursor") # Define volatile keys not to save
        save_data = {k: v for k, v in state.items() if k not in exclude_keys} # Filter state dict to only persistent data
        json_str = json.dumps(save_data) # Convert dict to JSON string
        if json_str == _last_saved_json: # Check if data actually changed
            state["dirty_save"] = False # Reset save flag
            return # Exit early to save flash wear
        storage.write(_SETTINGS_FILE, json_str, "w") # Write to persistent file
        _last_saved_json = json_str # Update JSON cache
        state["dirty_save"] = False # Reset save flag
    except Exception: pass # Ignore save errors silently

def validate_and_load_settings(): # Function to load and migrate settings
    global state, _last_saved_json # Access globals
    if storage.exists(_SETTINGS_FILE): # Check if config file exists
        try: # Catch parsing errors
            raw_data = storage.read(_SETTINGS_FILE, "r") # Read file content
            loaded = json.loads(raw_data) # Parse JSON into dict
            exclude_keys = ("dirty_ui", "mode", "cursor_idx", "options_cursor_idx", "tmp_y", "tmp_mo", "tmp_d", "date_cursor", "tmp_h", "tmp_m", "tmp_label", "tmp_audible", "edit_idx", "ringing_idx", "last_s", "ring_flash", "dirty_save", "save_timer", "origin", "del_confirm_yes", "clear_confirm_yes", "snooze_epoch", "snooze_idx", "last_trig_m", "snooze_count", "msg_origin", "tmp_daily", "egg_end", "sw_run", "sw_start", "sw_accum", "last_sw_ms", "cd_end", "cd_cursor") # Keys to ignore from file
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
        except: pass # Ignore audio errors

def check_time_and_alarms(t, c_sec): # Core logic loop evaluating timers
    global state # Access global state
    cy, cmo, cd, ch, cm, cs = t[0], t[1], t[2], t[3], t[4], t[5] # Unpack local time tuple
    
    if state["mode"] == "stopwatch" and state["sw_run"]: # Check if stopwatch UI needs fast updates
        now_ms = time.ticks_ms() # Get current milliseconds
        if time.ticks_diff(now_ms, state["last_sw_ms"]) > 100: # Refresh screen every 100ms
            state["last_sw_ms"] = now_ms # Update tracker
            state["dirty_ui"] = True # Force UI redraw
            
    if state["mode"] not in ("error_time", "error_hw"): # Skip checks if in critical error states
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
                elif cs == 0 and state["last_trig_m"] != cm: # Every new minute check standard alarms
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
                except: pass # Ignore audio errors

def process_input(button, input_mgr, view_manager, t, c_sec): # Core input handling function
    global show_help, show_options, help_box, state # Access global states
    cy, cmo, cd, ch, cm = t[0], t[1], t[2], t[3], t[4] # Unpack current time

    if state["mode"] in ("error_time", "error_hw"): # Handle critical startup errors
        if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_CENTER): # Check for exit buttons
            view_manager.back() # Exit app back to OS
            
    elif state["mode"] in ("invalid_time", "invalid_date_format"): # Handle transient user errors
        if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_CENTER, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_UP, BUTTON_DOWN): # Any key dismisses error
            state["mode"] = state.get("msg_origin", "main") # Return to previous screen
            state["dirty_ui"] = True # Force redraw

    elif state["mode"] == "ring": # Input handling while ringing
        if state["ringing_idx"] in (-2, -3): # Special handling for eggtimer and countdown
            if button in (BUTTON_CENTER, BUTTON_O, BUTTON_BACK, BUTTON_ESCAPE): # Dismiss buttons
                state["mode"] = "egg_timer" if state["ringing_idx"] == -2 else "countdown" # Return to origin screen
                state["ringing_idx"] = -1 # Clear ringing state
                state["dirty_ui"] = True # Force redraw
                handle_audio_silence() # Stop buzzing
        else: # Standard alarm handling
            if button in (BUTTON_S, BUTTON_CENTER): # Snooze buttons
                if state["snooze_count"] < 5: # Limit max snoozes
                    state["snooze_epoch"] = c_sec + (state["snooze_min"] * 60) # Calculate next snooze time
                    state["snooze_idx"] = state["ringing_idx"] # Track which alarm is snoozed
                    state["snooze_count"] += 1 # Increment snooze counter
                    queue_save() # Save state
                else: # Max snoozes reached
                    if 0 <= state["ringing_idx"] < len(state["alarms"]) and not state["alarms"][state["ringing_idx"]][8]: # Check if non-daily alarm
                        state["alarms"][state["ringing_idx"]][5] = False # Auto-disable one-time alarms
                        queue_save() # Save changes
                    state["snooze_epoch"] = state["snooze_count"] = 0 # Reset snooze trackers
                state["mode"] = "main" # Return to main screen
                state["ringing_idx"] = -1 # Clear ringing state
                state["dirty_ui"] = True # Force redraw
                handle_audio_silence() # Stop buzzing
            elif button in (BUTTON_O, BUTTON_BACK, BUTTON_ESCAPE): # Dismiss buttons
                state["mode"] = "main" # Return to main screen
                if 0 <= state["ringing_idx"] < len(state["alarms"]) and not state["alarms"][state["ringing_idx"]][8]: # Check if non-daily alarm
                    state["alarms"][state["ringing_idx"]][5] = False # Auto-disable one-time alarms
                    queue_save() # Save changes
                state["ringing_idx"] = -1 # Clear ringing state
                state["snooze_epoch"] = state["snooze_count"] = 0 # Reset snooze data
                state["dirty_ui"] = True # Force redraw
                handle_audio_silence() # Stop buzzing

    elif show_options: # Input handling for options menu
        if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_CENTER): # Exit options menu
            show_options = False # Hide options
            state["dirty_ui"] = True # Force redraw
            queue_save() # Save settings
        elif button == BUTTON_DOWN: state["options_cursor_idx"] = (state["options_cursor_idx"] + 1) % 6; state["dirty_ui"] = True # Move cursor down
        elif button == BUTTON_UP: state["options_cursor_idx"] = (state["options_cursor_idx"] - 1) % 6; state["dirty_ui"] = True # Move cursor up
        elif button == BUTTON_RIGHT: # Increment selected setting
            if state["options_cursor_idx"] == 0: state["theme_idx"] = (state["theme_idx"] + 1) % len(_THEMES) # Next theme
            elif state["options_cursor_idx"] == 1: state["bg_r"] = (state["bg_r"] + 5) % 256 # Increase background Red
            elif state["options_cursor_idx"] == 2: state["bg_g"] = (state["bg_g"] + 5) % 256 # Increase background Green
            elif state["options_cursor_idx"] == 3: state["bg_b"] = (state["bg_b"] + 5) % 256 # Increase background Blue
            elif state["options_cursor_idx"] == 4: state["use_12h"] = not state["use_12h"] # Toggle time format
            elif state["options_cursor_idx"] == 5: state["snooze_min"] = state["snooze_min"] + 1 if state["snooze_min"] < 60 else 1 # Increase snooze time
            state["dirty_ui"] = True; queue_save() # Redraw and save
        elif button == BUTTON_LEFT: # Decrement selected setting
            if state["options_cursor_idx"] == 0: state["theme_idx"] = (state["theme_idx"] - 1) % len(_THEMES) # Prev theme
            elif state["options_cursor_idx"] == 1: state["bg_r"] = (state["bg_r"] - 5) % 256 # Decrease background Red
            elif state["options_cursor_idx"] == 2: state["bg_g"] = (state["bg_g"] - 5) % 256 # Decrease background Green
            elif state["options_cursor_idx"] == 3: state["bg_b"] = (state["bg_b"] - 5) % 256 # Decrease background Blue
            elif state["options_cursor_idx"] == 4: state["use_12h"] = not state["use_12h"] # Toggle time format
            elif state["options_cursor_idx"] == 5: state["snooze_min"] = state["snooze_min"] - 1 if state["snooze_min"] > 1 else 60 # Decrease snooze time
            state["dirty_ui"] = True; queue_save() # Redraw and save
            
    elif show_help: # Input handling for help overlay
        if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_H): # Dismiss help
            show_help = False # Hide help flag
            if help_box is not None: # Check if text box exists
                del help_box # Destroy object to free RAM
                help_box = None # Clear reference
                gc.collect() # Force garbage collection immediately
            state["dirty_ui"] = True # Force redraw
        elif button == BUTTON_DOWN and help_box: help_box.scroll_down(); state["dirty_ui"] = True # Scroll text down
        elif button == BUTTON_UP and help_box: help_box.scroll_up(); state["dirty_ui"] = True # Scroll text up

    elif state["mode"] == "main": # Input handling for main menu
        if button in (BUTTON_BACK, BUTTON_ESCAPE): # Exit app command
            save_settings(); view_manager.back() # Save and return to OS
        elif button == BUTTON_H: show_help = True; state["dirty_ui"] = True # Show help overlay
        elif button == BUTTON_O: show_options = True; state["dirty_ui"] = True # Show options menu
        elif button == BUTTON_M: state["mode"] = "alarms"; state["cursor_idx"] = 0; state["dirty_ui"] = True # Jump to alarms
        elif button == BUTTON_N: # Quick create new alarm
            state["mode"] = "edit_type"; state["origin"] = "main"; state["edit_idx"] = -1; state["tmp_daily"] = False # Setup edit variables
            state["tmp_y"] = cy; state["tmp_mo"] = cmo; state["tmp_d"] = cd; state["date_cursor"] = 0 # Pre-fill current date
            state["tmp_h"] = ch; state["tmp_m"] = cm; state["tmp_label"] = ""; state["tmp_audible"] = True; state["dirty_ui"] = True # Pre-fill current time
        elif button == BUTTON_DOWN: state["cursor_idx"] = (state["cursor_idx"] + 1) % 6; state["dirty_ui"] = True # Move cursor down
        elif button == BUTTON_UP: state["cursor_idx"] = (state["cursor_idx"] - 1) % 6; state["dirty_ui"] = True # Move cursor up
        elif button == BUTTON_CENTER: # Enter selected menu item
            if state["cursor_idx"] == 0: state["mode"] = "alarms"; state["cursor_idx"] = 0 # Open Alarms list
            elif state["cursor_idx"] == 1: state["mode"] = "egg_timer" # Open Egg timer
            elif state["cursor_idx"] == 2: state["mode"] = "stopwatch" # Open Stopwatch
            elif state["cursor_idx"] == 3: state["mode"] = "countdown" # Open Countdown
            elif state["cursor_idx"] == 4: show_options = True # Open Options
            elif state["cursor_idx"] == 5: show_help = True # Open Help
            state["dirty_ui"] = True # Force redraw

    elif state["mode"] == "egg_timer": # Input handling for egg timer
        if button in (BUTTON_BACK, BUTTON_ESCAPE): # Return to main menu
            state["mode"] = "main" # Change state
            state["dirty_ui"] = True # Redraw screen
        elif button == BUTTON_DOWN: # Cycle presets down
            state["egg_preset"] = (state["egg_preset"] + 1) % len(_EGG_PRESETS) # Wrap around index
            state["dirty_ui"] = True # Redraw screen
        elif button == BUTTON_UP: # Cycle presets up
            state["egg_preset"] = (state["egg_preset"] - 1) % len(_EGG_PRESETS) # Wrap around index
            state["dirty_ui"] = True # Redraw screen
        elif button == BUTTON_CENTER: # Apply selected preset
            m = _EGG_PRESETS[state["egg_preset"]][0] # Fetch minute value from tuple
            if m == 0: # Check if "Off" is selected
                state["egg_end"] = 0 # Disable timer
            else: # Valid timer selected
                state["egg_end"] = c_sec + (m * 60) # Calculate completion epoch
            queue_save() # Save timer state
            state["mode"] = "main" # Return to main menu
            state["dirty_ui"] = True # Redraw screen

    elif state["mode"] == "stopwatch": # Input handling for stopwatch
        if button in (BUTTON_BACK, BUTTON_ESCAPE): # Return to main menu
            state["mode"] = "main" # Change state
            state["dirty_ui"] = True # Redraw screen
        elif button == BUTTON_CENTER: # Start/Pause toggle
            if state["sw_run"]: # If running
                state["sw_accum"] += time.ticks_diff(time.ticks_ms(), state["sw_start"]) # Save passed milliseconds
                state["sw_run"] = False # Pause timer
            else: # If paused
                state["sw_start"] = time.ticks_ms() # Set new start point
                state["sw_run"] = True # Resume timer
            state["dirty_ui"] = True # Redraw screen
        elif button == BUTTON_R: # Reset stopwatch
            state["sw_accum"] = 0 # Clear accumulated time
            state["sw_run"] = False # Stop running
            state["dirty_ui"] = True # Redraw screen
            
    elif state["mode"] == "countdown": # Input handling for countdown
        if button in (BUTTON_BACK, BUTTON_ESCAPE): # Return to main menu
            state["mode"] = "main" # Change state
            state["dirty_ui"] = True # Redraw screen
        elif state["cd_end"] == 0: # If countdown is not active
            if button == BUTTON_LEFT: # Move cursor left
                state["cd_cursor"] = (state["cd_cursor"] - 1) % 3 # Update cursor
                state["dirty_ui"] = True # Redraw screen
            elif button == BUTTON_RIGHT: # Move cursor right
                state["cd_cursor"] = (state["cd_cursor"] + 1) % 3 # Update cursor
                state["dirty_ui"] = True # Redraw screen
            elif button == BUTTON_UP: # Increment selected field
                if state["cd_cursor"] == 0: state["cd_h"] = (state["cd_h"] + 1) % 100 # Add hour
                elif state["cd_cursor"] == 1: state["cd_m"] = (state["cd_m"] + 1) % 60 # Add minute
                elif state["cd_cursor"] == 2: state["cd_s"] = (state["cd_s"] + 1) % 60 # Add second
                state["dirty_ui"] = True; queue_save() # Redraw and save
            elif button == BUTTON_DOWN: # Decrement selected field
                if state["cd_cursor"] == 0: state["cd_h"] = (state["cd_h"] - 1) % 100 # Sub hour
                elif state["cd_cursor"] == 1: state["cd_m"] = (state["cd_m"] - 1) % 60 # Sub minute
                elif state["cd_cursor"] == 2: state["cd_s"] = (state["cd_s"] - 1) % 60 # Sub second
                state["dirty_ui"] = True; queue_save() # Redraw and save
            elif button == BUTTON_CENTER: # Start countdown
                total_s = state["cd_h"] * 3600 + state["cd_m"] * 60 + state["cd_s"] # Calculate total seconds
                if total_s > 0: # Ensure > 0 duration
                    state["cd_end"] = c_sec + total_s # Calculate completion epoch
                    state["dirty_ui"] = True # Redraw screen
            elif button == BUTTON_R: # Reset input fields
                state["cd_h"] = state["cd_m"] = state["cd_s"] = 0 # Clear variables
                state["dirty_ui"] = True; queue_save() # Redraw and save
        else: # If countdown is active
            if button in (BUTTON_CENTER, BUTTON_R): # Cancel running countdown
                state["cd_end"] = 0 # Disable timer
                state["dirty_ui"] = True # Redraw screen

    elif state["mode"] == "alarms": # Input handling for alarm list
        list_len = len(state["alarms"]) + 1 # Dynamic list length including 'Create New'
        if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = "main"; state["cursor_idx"] = 0; state["dirty_ui"] = True # Return to main menu
        elif button == BUTTON_DOWN and state["cursor_idx"] < list_len - 1: state["cursor_idx"] += 1; state["dirty_ui"] = True # Move cursor down list
        elif button == BUTTON_UP and state["cursor_idx"] > 0: state["cursor_idx"] -= 1; state["dirty_ui"] = True # Move cursor up list
        elif button in (BUTTON_LEFT, BUTTON_RIGHT) and state["cursor_idx"] < len(state["alarms"]): # Toggle alarm active state
            a = state["alarms"][state["cursor_idx"]] # Reference selected alarm
            if not a[5]: # If currently inactive
                if not a[8] and time.mktime((a[0], a[1], a[2], a[3], a[4], 0, 0, 0)) <= c_sec: # Prevent turning on a past alarm
                    state["mode"] = "invalid_time"; state["msg_origin"] = "alarms"; state["dirty_ui"] = True # Show error
                else: 
                    a[5] = True; queue_save(); state["dirty_ui"] = True # Turn on and save
            else: # If currently active
                a[5] = False # Turn off
                if state["snooze_idx"] == state["cursor_idx"]: state["snooze_epoch"] = state["snooze_count"] = 0 # Cancel related snooze
                queue_save(); state["dirty_ui"] = True # Save and redraw
        elif button == BUTTON_T and state["cursor_idx"] < len(state["alarms"]):  # Toggle audio parameter
            state["alarms"][state["cursor_idx"]][7] = not state["alarms"][state["cursor_idx"]][7]; queue_save(); state["dirty_ui"] = True # Flip bool and save
        elif button == BUTTON_C: # Clear all past alarms shortcut
            has_past = any(not a[8] and time.mktime((a[0], a[1], a[2], a[3], a[4], 0, 0, 0)) < c_sec for a in state["alarms"]) # Check if any exist
            if has_past: state["mode"] = "confirm_clear"; state["clear_confirm_yes"] = False; state["dirty_ui"] = True # Trigger confirmation
        elif button == BUTTON_BACKSPACE and state["cursor_idx"] < len(state["alarms"]): # Delete selected alarm shortcut
            state["mode"] = "confirm_delete"; state["del_confirm_yes"] = False; state["dirty_ui"] = True # Trigger confirmation
        elif button == BUTTON_CENTER: # Select item
            state["mode"] = "edit_type"; state["origin"] = "alarms"; state["date_cursor"] = 0; state["dirty_ui"] = True # Setup edit mode
            if state["cursor_idx"] == len(state["alarms"]): # If "Create New" selected
                state["edit_idx"] = -1; state["tmp_daily"] = False; state["tmp_y"] = cy; state["tmp_mo"] = cmo; state["tmp_d"] = cd # Setup new defaults
                state["tmp_h"] = ch; state["tmp_m"] = cm; state["tmp_label"] = ""; state["tmp_audible"] = True # Setup new defaults
            else: # If existing alarm selected
                a = state["alarms"][state["cursor_idx"]]; state["edit_idx"] = state["cursor_idx"] # Track index
                state["tmp_y"] = a[0]; state["tmp_mo"] = a[1]; state["tmp_d"] = a[2]; state["tmp_h"] = a[3]; state["tmp_m"] = a[4] # Load specific data
                state["tmp_label"] = a[6]; state["tmp_audible"] = a[7]; state["tmp_daily"] = a[8] # Load specific parameters

    elif state["mode"] == "confirm_delete": # Input handling for delete prompt
        if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = "alarms"; state["dirty_ui"] = True # Cancel
        elif button in (BUTTON_LEFT, BUTTON_RIGHT): state["del_confirm_yes"] = not state["del_confirm_yes"]; state["dirty_ui"] = True # Toggle yes/no
        elif button == BUTTON_CENTER: # Confirm selection
            if state["del_confirm_yes"]: # If Yes selected
                if state["snooze_idx"] == state["cursor_idx"]: state["snooze_epoch"] = state["snooze_count"] = 0 # Cancel snooze if targeting this alarm
                elif state["snooze_idx"] > state["cursor_idx"]: state["snooze_idx"] -= 1 # Shift snooze index if needed
                state["alarms"].pop(state["cursor_idx"]); state["cursor_idx"] = max(0, state["cursor_idx"] - 1); queue_save() # Remove alarm and correct cursor
            state["mode"] = "alarms"; state["dirty_ui"] = True # Return to list
            
    elif state["mode"] == "confirm_clear": # Input handling for clear past prompt
        if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = "alarms"; state["dirty_ui"] = True # Cancel
        elif button in (BUTTON_LEFT, BUTTON_RIGHT): state["clear_confirm_yes"] = not state["clear_confirm_yes"]; state["dirty_ui"] = True # Toggle yes/no
        elif button == BUTTON_CENTER: # Confirm selection
            if state["clear_confirm_yes"]: # If Yes selected
                for i in range(len(state["alarms"]) - 1, -1, -1): # Iterate backwards to safely delete
                    a = state["alarms"][i] # Get alarm
                    if not a[8] and time.mktime((a[0], a[1], a[2], a[3], a[4], 0, 0, 0)) < c_sec: # Identify past non-daily alarm
                        if state["snooze_idx"] == i: state["snooze_epoch"] = state["snooze_count"] = 0 # Cancel related snooze
                        elif state["snooze_idx"] > i: state["snooze_idx"] -= 1 # Shift snooze index
                        state["alarms"].pop(i) # Delete from array
                state["cursor_idx"] = 0; queue_save() # Reset cursor and save changes
            state["mode"] = "alarms"; state["dirty_ui"] = True # Return to list

    elif state["mode"] == "edit_type": # Editor step 1: Select Type
        if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = state.get("origin", "main"); state["dirty_ui"] = True # Cancel editor
        elif button in (BUTTON_LEFT, BUTTON_RIGHT, BUTTON_UP, BUTTON_DOWN): state["tmp_daily"] = not state["tmp_daily"]; state["dirty_ui"] = True # Toggle Daily/Specific
        elif button == BUTTON_CENTER: state["mode"] = "edit_h" if state["tmp_daily"] else "edit_date"; state["dirty_ui"] = True # Proceed to appropriate next step
        
    elif state["mode"] == "edit_date": # Editor step 2a: Set Date
        if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = "edit_type"; state["dirty_ui"] = True # Go back a step
        elif button == BUTTON_LEFT: state["date_cursor"] = (state["date_cursor"] - 1) % 3; state["dirty_ui"] = True # Move cursor left
        elif button == BUTTON_RIGHT: state["date_cursor"] = (state["date_cursor"] + 1) % 3; state["dirty_ui"] = True # Move cursor right
        elif button == BUTTON_UP: # Increment selected date field safely
            if state["date_cursor"] == 0: state["tmp_y"] += 1 if state["use_12h"] else 0; state["tmp_d"] = state["tmp_d"] + 1 if state["tmp_d"] < 31 and not state["use_12h"] else (1 if not state["use_12h"] else state["tmp_d"]) # EU vs US format logic
            elif state["date_cursor"] == 1: state["tmp_mo"] = state["tmp_mo"] + 1 if state["tmp_mo"] < 12 else 1 # Increment month
            elif state["date_cursor"] == 2: state["tmp_d"] = state["tmp_d"] + 1 if state["tmp_d"] < 31 and state["use_12h"] else (1 if state["use_12h"] else state["tmp_d"]); state["tmp_y"] += 1 if not state["use_12h"] else 0 # EU vs US format logic
            state["dirty_ui"] = True # Redraw screen
        elif button == BUTTON_DOWN: # Decrement selected date field safely
            if state["date_cursor"] == 0: state["tmp_y"] = max(2024, state["tmp_y"] - 1) if state["use_12h"] else state["tmp_y"]; state["tmp_d"] = state["tmp_d"] - 1 if state["tmp_d"] > 1 and not state["use_12h"] else (31 if not state["use_12h"] else state["tmp_d"]) # EU vs US format logic
            elif state["date_cursor"] == 1: state["tmp_mo"] = state["tmp_mo"] - 1 if state["tmp_mo"] > 1 else 12 # Decrement month
            elif state["date_cursor"] == 2: state["tmp_d"] = state["tmp_d"] - 1 if state["tmp_d"] > 1 and state["use_12h"] else (31 if state["use_12h"] else state["tmp_d"]); state["tmp_y"] = max(2024, state["tmp_y"] - 1) if not state["use_12h"] else state["tmp_y"] # EU vs US format logic
            state["dirty_ui"] = True # Redraw screen
        elif button == BUTTON_CENTER: # Validate and proceed
            leap = 1 if (state["tmp_y"] % 4 == 0 and (state["tmp_y"] % 100 != 0 or state["tmp_y"] % 400 == 0)) else 0 # Calculate leap year
            dim = [31, 28 + leap, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][state["tmp_mo"] - 1] # Find days in selected month
            if state["tmp_d"] > dim: state["mode"] = "invalid_date_format"; state["msg_origin"] = "edit_date"; state["dirty_ui"] = True; input_mgr.reset(); return # Catch invalid calendar dates like Feb 30
            if state["tmp_y"] < cy or (state["tmp_y"] == cy and state["tmp_mo"] < cmo) or (state["tmp_y"] == cy and state["tmp_mo"] == cmo and state["tmp_d"] < cd): state["mode"] = "invalid_time"; state["msg_origin"] = "edit_date"; state["dirty_ui"] = True; input_mgr.reset(); return # Catch dates in the past
            state["mode"] = "edit_h"; state["dirty_ui"] = True # Proceed to time step

    elif state["mode"] == "edit_h": # Editor step 3: Set Hour
        if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = "edit_type" if state["tmp_daily"] else "edit_date"; state["dirty_ui"] = True # Go back
        elif button == BUTTON_DOWN: state["tmp_h"] = (state["tmp_h"] - 1) % 24; state["dirty_ui"] = True # Decrement hour
        elif button == BUTTON_UP: state["tmp_h"] = (state["tmp_h"] + 1) % 24; state["dirty_ui"] = True # Increment hour
        elif button == BUTTON_CENTER: # Validate and proceed
            if not state["tmp_daily"] and state["tmp_y"] == cy and state["tmp_mo"] == cmo and state["tmp_d"] == cd and state["tmp_h"] < ch: state["mode"] = "invalid_time"; state["msg_origin"] = "edit_h"; state["dirty_ui"] = True; input_mgr.reset(); return # Prevent setting past hour on today's date
            state["mode"] = "edit_m"; state["dirty_ui"] = True # Proceed to minute step

    elif state["mode"] == "edit_m": # Editor step 4: Set Minute
        if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = "edit_h"; state["dirty_ui"] = True # Go back
        elif button == BUTTON_DOWN: state["tmp_m"] = (state["tmp_m"] - 1) % 60; state["dirty_ui"] = True # Decrement minute
        elif button == BUTTON_UP: state["tmp_m"] = (state["tmp_m"] + 1) % 60; state["dirty_ui"] = True # Increment minute
        elif button == BUTTON_CENTER: # Validate and proceed
            if not state["tmp_daily"] and state["tmp_y"] == cy and state["tmp_mo"] == cmo and state["tmp_d"] == cd and state["tmp_h"] == ch and state["tmp_m"] <= cm: state["mode"] = "invalid_time"; state["msg_origin"] = "edit_m"; state["dirty_ui"] = True; input_mgr.reset(); return # Prevent setting past minute on today's date
            state["mode"] = "edit_l"; state["dirty_ui"] = True # Proceed to label step

    elif state["mode"] == "edit_l": # Editor step 5: Set Label (Text Input)
        if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = "edit_m"; state["dirty_ui"] = True # Go back
        elif button == BUTTON_CENTER: state["mode"] = "edit_aud"; state["dirty_ui"] = True # Proceed to audio step
        elif button == BUTTON_BACKSPACE and len(state["tmp_label"]) > 0: state["tmp_label"] = state["tmp_label"][:-1]; state["dirty_ui"] = True # Handle backspace key
        elif button == BUTTON_SPACE and len(state["tmp_label"]) < 50: state["tmp_label"] += " "; state["dirty_ui"] = True # Handle space key
        elif button >= BUTTON_A and button <= BUTTON_Z and len(state["tmp_label"]) < 50: state["tmp_label"] += chr(button - BUTTON_A + ord('A')); state["dirty_ui"] = True # Append letter keys safely
        elif button >= BUTTON_0 and button <= BUTTON_9 and len(state["tmp_label"]) < 50: state["tmp_label"] += chr(button - BUTTON_0 + ord('0')); state["dirty_ui"] = True # Append number keys safely

    elif state["mode"] == "edit_aud": # Editor step 6: Set Audio bool
        if button in (BUTTON_BACK, BUTTON_ESCAPE): state["mode"] = "edit_l"; state["dirty_ui"] = True # Go back
        elif button in (BUTTON_LEFT, BUTTON_RIGHT, BUTTON_UP, BUTTON_DOWN): state["tmp_audible"] = not state["tmp_audible"]; state["dirty_ui"] = True # Toggle yes/no
        elif button == BUTTON_CENTER: # Finalize and Save
            final_lbl = state["tmp_label"].strip() or "ALARM" # Clean label or set default string
            if not state["tmp_daily"] and time.mktime((state["tmp_y"], state["tmp_mo"], state["tmp_d"], state["tmp_h"], state["tmp_m"], 0, 0, 0)) <= c_sec: state["mode"] = "invalid_time"; state["msg_origin"] = "edit_aud"; state["dirty_ui"] = True; input_mgr.reset(); return # Final validation pass
            new_a = [state["tmp_y"], state["tmp_mo"], state["tmp_d"], state["tmp_h"], state["tmp_m"], True, final_lbl, state["tmp_audible"], state["tmp_daily"]] # Construct new data tuple
            if state["edit_idx"] == -1: state["alarms"].append(new_a) # Append if new
            else: state["alarms"][state["edit_idx"]] = new_a # Overwrite if editing
            queue_save(); state["mode"] = state.get("origin", "main"); state["dirty_ui"] = True # Queue disk save and exit to origin screen
            if state["origin"] == "main": state["cursor_idx"] = 0 # Reset cursor if returning to main menu

    input_mgr.reset() # Clear input buffer

def draw_view(view_manager): # Core rendering function
    global help_box # Access help textbox reference
    draw = view_manager.draw; screen_w = draw.size.x; screen_h = draw.size.y # Access screen API and dimensions
    bg_color = rgb_to_565(state["bg_r"], state["bg_g"], state["bg_b"]) # Calculate background 565 color
    theme_color = _THEMES[state["theme_idx"]][1] # Get current theme color code
    draw.clear(); draw.fill_rectangle(Vector(0, 0), Vector(screen_w, screen_h), bg_color) # Wipe screen and fill background
    
    if state["mode"] == "error_time": # Draw Time error screen
        draw.text(Vector(30, 40), "NTP ERROR", theme_color, 2) # Draw Error title
        draw.text(Vector(15, 90), "Cannot verify time.", TFT_LIGHTGREY) # Draw reason text
        draw.text(Vector(15, 110), "Please connect Wi-Fi", TFT_WHITE) # Draw instruction text
        draw.text(Vector(15, 130), "and restart app.", TFT_WHITE) # Draw instruction text 2
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color) # Draw footer line
        draw.text(Vector(5, screen_h - 25), "[ESC] Exit App", theme_color) # Draw exit hint
    elif state["mode"] == "error_hw": # Draw Hardware error screen (Pico 2 W check)
        draw.text(Vector(30, 40), "HW ERROR", TFT_RED, 2) # Draw red Error title
        draw.text(Vector(15, 90), "Pico 2 W required.", TFT_LIGHTGREY) # Explain board requirement
        draw.text(Vector(15, 110), "Wi-Fi needed for app.", TFT_WHITE) # Explain why it is required
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), TFT_RED) # Draw red footer line
        draw.text(Vector(5, screen_h - 25), "[ESC] Exit App", TFT_RED) # Draw exit hint
    elif state["mode"] == "invalid_date_format": # Draw bad date screen
        draw.text(Vector(10, 10), "ERROR", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), TFT_RED) # Header setup
        draw.fill_rectangle(Vector(15, 60), Vector(screen_w - 30, 80), TFT_DARKGREY); draw.rect(Vector(15, 60), Vector(screen_w - 30, 80), TFT_RED) # Draw error box
        draw.text(Vector(25, 75), "INVALID DATE", TFT_RED); draw.text(Vector(25, 100), "This date does not", TFT_WHITE); draw.text(Vector(25, 115), "exist in calendar.", TFT_WHITE) # Draw box text
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), TFT_RED); draw.text(Vector(5, screen_h - 32), "[Any Key] Go Back", TFT_RED) # Draw footer hints
    elif state["mode"] == "invalid_time": # Draw past-time error screen
        draw.text(Vector(10, 10), "ERROR", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), TFT_RED) # Header setup
        draw.fill_rectangle(Vector(15, 60), Vector(screen_w - 30, 80), TFT_DARKGREY); draw.rect(Vector(15, 60), Vector(screen_w - 30, 80), TFT_RED) # Draw error box
        draw.text(Vector(25, 75), "INVALID DATE/TIME", TFT_RED); draw.text(Vector(25, 100), "Alarm must be set", TFT_WHITE); draw.text(Vector(25, 115), "in the future.", TFT_WHITE) # Draw box text
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), TFT_RED); draw.text(Vector(5, screen_h - 32), "[Any Key] Go Back", TFT_RED) # Draw footer hints
    elif state["mode"] == "ring": # Draw active ringing screen
        if state["ringing_idx"] == -2: # Check if it's the egg timer ringing
            display_lbl = "EGG READY!" # Setup egg text
            hint_str = "[ENT/O] Dismiss" # Setup egg hints
        elif state["ringing_idx"] == -3: # Check if it's countdown ringing
            display_lbl = "TIME'S UP!" # Setup cd text
            hint_str = "[ENT/O] Dismiss" # Setup cd hints
        else: # Standard alarm ringing
            display_lbl = state["alarms"][state["ringing_idx"]][6][:15] + "..." if len(state["alarms"][state["ringing_idx"]][6]) > 15 else state["alarms"][state["ringing_idx"]][6] # Fetch and truncate label
            hint_str = f"[S/ENT]Snooze({5-state['snooze_count']}) [O]Off" if state["snooze_count"] < 5 else "[O]Off (Max Snooze)" # Construct snooze hint string
        draw.fill_rectangle(Vector(0, 0), Vector(screen_w, screen_h), TFT_WHITE if state["ring_flash"] else TFT_BLACK) # Flash background color rapidly
        draw.text(Vector(30, 60), "ALARM!", TFT_BLACK if state["ring_flash"] else theme_color, 3) # Flash title text color rapidly
        draw.text(Vector(10, 100), display_lbl, TFT_BLACK if state["ring_flash"] else theme_color, 2) # Flash main text color rapidly
        draw.text(Vector(10, 150), hint_str, TFT_BLACK if state["ring_flash"] else theme_color) # Flash hint text color rapidly
    elif state["mode"] == "egg_timer": # Draw egg timer menu
        draw.text(Vector(10, 10), "MODE: EGG TIMER", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color) # Header setup
        if state["egg_end"] > 0: # Check if timer is running
            rem = max(0, state["egg_end"] - int(time.time())) # Calculate remaining seconds safely
            m, s = divmod(rem, 60) # Convert to minutes/seconds
            draw.text(Vector(15, 40), f"Run: {m:02d}:{s:02d}", TFT_GREEN, 2) # Display live timer
        else: # Timer is idle
            draw.text(Vector(15, 45), "Status: Inactive", TFT_LIGHTGREY) # Display inactive status
        
        draw.text(Vector(15, 70), "Select Preset:", TFT_LIGHTGREY) # Draw preset list header
        for i, (m, lbl) in enumerate(_EGG_PRESETS): # Iterate through hardcoded presets
            c = theme_color if state["egg_preset"] == i else TFT_LIGHTGREY # Highlight color for selected item
            if state["egg_preset"] == i: draw.text(Vector(10, 90 + i*20), ">", theme_color) # Draw selection cursor
            draw.text(Vector(25, 90 + i*20), lbl, c) # Draw preset text
            
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color) # Draw footer line
        draw.text(Vector(5, screen_h - 32), "[UP/DN] Nav [ENT] Apply", theme_color) # Draw footer hint
    elif state["mode"] == "stopwatch": # Draw stopwatch screen
        draw.text(Vector(10, 10), "MODE: STOPWATCH", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color) # Header setup
        
        current_ms = state["sw_accum"] # Fetch saved milliseconds
        if state["sw_run"]: # If stopwatch is running
            current_ms += time.ticks_diff(time.ticks_ms(), state["sw_start"]) # Add live milliseconds
            
        ms = (current_ms % 1000) // 100 # Calculate fractional tenth seconds
        sec = (current_ms // 1000) % 60 # Calculate total seconds
        mins = (current_ms // 60000) % 60 # Calculate total minutes
        hrs = (current_ms // 3600000) # Calculate total hours
        
        if hrs > 0: # Switch display formatting if past 1 hour
            sw_text = f"{hrs:02d}:{mins:02d}:{sec:02d}" # Format HH:MM:SS
        else: # Standard formatting under 1 hour
            sw_text = f"{mins:02d}:{sec:02d}.{ms:01d}" # Format MM:SS.t
            
        draw.text(Vector((screen_w // 2) - 85, 70), sw_text, theme_color, 4) # Draw big center text
        
        stat_str = "RUNNING" if state["sw_run"] else "STOPPED" # Get status string
        draw.text(Vector((screen_w // 2) - 30, 130), stat_str, TFT_GREEN if state["sw_run"] else TFT_LIGHTGREY) # Draw status indicator
        
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color) # Draw footer line
        draw.text(Vector(5, screen_h - 32), "[ENT] Start/Stop [R] Reset", theme_color) # Draw footer hints
    elif state["mode"] == "countdown": # Draw countdown screen
        draw.text(Vector(10, 10), "MODE: COUNTDOWN", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color) # Header setup
        
        if state["cd_end"] > 0: # If countdown is actively running
            rem = max(0, state["cd_end"] - int(time.time())) # Calculate remaining seconds safely
            h = rem // 3600; m = (rem % 3600) // 60; s = rem % 60 # Convert to H, M, S
            draw.text(Vector((screen_w // 2) - 85, 70), f"{h:02d}:{m:02d}:{s:02d}", theme_color, 4) # Draw big time string
            draw.text(Vector((screen_w // 2) - 30, 130), "RUNNING", TFT_GREEN) # Draw active status
            draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color) # Draw footer line
            draw.text(Vector(5, screen_h - 32), "[ENT] Cancel", theme_color) # Draw cancel hint
        else: # If setting up countdown
            draw.text(Vector(15, 45), "Set Duration:", TFT_LIGHTGREY) # Setup text
            c0 = theme_color if state["cd_cursor"] == 0 else TFT_WHITE # Cursor color logic for Hours
            c1 = theme_color if state["cd_cursor"] == 1 else TFT_WHITE # Cursor color logic for Minutes
            c2 = theme_color if state["cd_cursor"] == 2 else TFT_WHITE # Cursor color logic for Seconds
            
            st_x = (screen_w // 2) - 85 # Calculate center alignment x-offset
            draw.text(Vector(st_x, 70), f"{state['cd_h']:02d}", c0, 4) # Draw Hour field
            draw.text(Vector(st_x + 50, 70), ":", TFT_LIGHTGREY, 4) # Draw separator
            draw.text(Vector(st_x + 70, 70), f"{state['cd_m']:02d}", c1, 4) # Draw Minute field
            draw.text(Vector(st_x + 120, 70), ":", TFT_LIGHTGREY, 4) # Draw separator
            draw.text(Vector(st_x + 140, 70), f"{state['cd_s']:02d}", c2, 4) # Draw Second field
            
            draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color) # Draw footer line
            draw.text(Vector(5, screen_h - 32), "[L/R]Sel [U/D]Adj [ENT]Go [R]Rst", theme_color) # Draw complex control hints
            
    elif show_options: # Draw Options overlay menu
        draw.fill_rectangle(Vector(0, 0), Vector(screen_w, screen_h), TFT_DARKGREY); draw.fill_rectangle(Vector(0, 0), Vector(screen_w, 30), theme_color); draw.text(Vector(10, 10), "OPTIONS MENU", TFT_WHITE) # Setup dark overlay bg and header
        opt_r_height = 22; o_idx = state["options_cursor_idx"] # Define row height and fetch cursor index
        
        c0 = theme_color if o_idx == 0 else TFT_LIGHTGREY; draw.fill_rectangle(Vector(0, 36), Vector(screen_w, opt_r_height), TFT_BLACK) if o_idx == 0 else None; draw.text(Vector(15, 40), "Theme Color:", c0); draw.text(Vector(140, 40), f"< {_THEMES[state['theme_idx']][0]} >", c0) # Draw Theme Color row
        c1 = theme_color if o_idx == 1 else TFT_LIGHTGREY; draw.fill_rectangle(Vector(0, 60), Vector(screen_w, opt_r_height), TFT_BLACK) if o_idx == 1 else None; draw.text(Vector(15, 64), "Back R (0-255):", c1); draw.text(Vector(140, 64), f"< {state['bg_r']} >", c1) # Draw BG Red row
        c2 = theme_color if o_idx == 2 else TFT_LIGHTGREY; draw.fill_rectangle(Vector(0, 84), Vector(screen_w, opt_r_height), TFT_BLACK) if o_idx == 2 else None; draw.text(Vector(15, 88), "Back G (0-255):", c2); draw.text(Vector(140, 88), f"< {state['bg_g']} >", c2) # Draw BG Green row
        c3 = theme_color if o_idx == 3 else TFT_LIGHTGREY; draw.fill_rectangle(Vector(0, 108), Vector(screen_w, opt_r_height), TFT_BLACK) if o_idx == 3 else None; draw.text(Vector(15, 112), "Back B (0-255):", c3); draw.text(Vector(140, 112), f"< {state['bg_b']} >", c3) # Draw BG Blue row
        c4 = theme_color if o_idx == 4 else TFT_LIGHTGREY; draw.fill_rectangle(Vector(0, 132), Vector(screen_w, opt_r_height), TFT_BLACK) if o_idx == 4 else None; draw.text(Vector(15, 136), "Time Format:", c4); draw.text(Vector(140, 136), f"< {'12 Hour' if state['use_12h'] else '24 Hour'} >", c4) # Draw 12/24H format row
        c5 = theme_color if o_idx == 5 else TFT_LIGHTGREY; draw.fill_rectangle(Vector(0, 156), Vector(screen_w, opt_r_height), TFT_BLACK) if o_idx == 5 else None; draw.text(Vector(15, 160), "Snooze (Min):", c5); draw.text(Vector(140, 160), f"< {state['snooze_min']} >", c5) # Draw Snooze time row
        
        draw.text(Vector(15, 184), "Preview:", TFT_LIGHTGREY); draw.rect(Vector(90, 182), Vector(135, 14), theme_color); draw.fill_rectangle(Vector(91, 183), Vector(133, 12), bg_color) # Draw live color preview box
        draw.text(Vector(5, screen_h - 20), "[L/R] Edit  [ENT] Close", TFT_WHITE) # Draw footer hints
    elif show_help: # Draw Help text overlay
        if help_box is None: help_box = TextBox(draw, 0, 240, theme_color, bg_color, True); help_box.set_text(_HELP_TEXT) # Instantiate text box if missing and apply text
        help_box.refresh() # Trigger text box redraw method
    elif state["mode"] == "main": # Draw Main menu/dashboard
        c_idx = state["cursor_idx"] # Get cursor location
        draw.text(Vector(10, 10), f"Eggtimer {_VERSION}", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color) # Header setup
        
        draw.text(Vector(15, 42), "CURRENT TIME:", TFT_LIGHTGREY); draw.fill_rectangle(Vector(15, 55), Vector(screen_w - 30, 43), TFT_DARKGREY); draw.rect(Vector(15, 55), Vector(screen_w - 30, 43), theme_color) # Clock box styling
        
        t = time.localtime() # Get current time
        dh = t[3] % 12 if state["use_12h"] else t[3] # Handle 12/24 logic
        dh = 12 if state["use_12h"] and dh == 0 else dh # Fix 0 o'clock logic in 12h
        time_str = "{:02d}:{:02d}:{:02d} {}".format(dh, t[4], t[5], "AM" if t[3] < 12 else "PM") if state["use_12h"] else "{:02d}:{:02d}:{:02d}".format(t[3], t[4], t[5]) # Format main clock string
        draw.text(Vector(40 if not state["use_12h"] else 20, 58), time_str, theme_color, 2) # Draw main clock text
        
        n_str = "Next: None Active" # Default string for next alarm tracker
        min_d = 9999999999; c_sec = time.time(); next_a = None; is_snooze_next = False # Setup calculation variables
        for a in state["alarms"]: # Iterate alarms to find the next active one
            if a[5]: # If active
                a_sec = time.mktime((t[0], t[1], t[2], a[3], a[4], 0, 0, 0)) + (86400 if a[8] and (a[3] < t[3] or (a[3] == t[3] and a[4] <= t[4])) else 0) if a[8] else time.mktime((a[0], a[1], a[2], a[3], a[4], 0, 0, 0)) # Calculate absolute epoch of alarm
                d = a_sec - c_sec # Calculate seconds from now
                if 0 < d < min_d: min_d = d; next_a = a; is_snooze_next = False # Update nearest alarm data
        if state["snooze_epoch"] > 0 and 0 < state["snooze_epoch"] - c_sec < min_d: next_a = state["alarms"][state["snooze_idx"]]; is_snooze_next = True # Override if a snooze is coming up sooner
        
        if next_a: # Construct text if a next alarm was found
            lbl = next_a[6][:4] + "Zz" if is_snooze_next else next_a[6][:6] # Abbreviate label
            nh, nm = (time.localtime(state["snooze_epoch"])[3:5] if is_snooze_next else next_a[3:5]) # Extract hour/min
            nmo, nd = (time.localtime(state["snooze_epoch"])[1:3] if is_snooze_next else (next_a[1:3] if not next_a[8] else (t[1], t[2]))) # Extract month/day
            ny = time.localtime(state["snooze_epoch"])[0] if is_snooze_next else (next_a[0] if not next_a[8] else t[0]) # Extract year
            ndh = nh % 12 if state["use_12h"] else nh; ndh = 12 if state["use_12h"] and ndh == 0 else ndh # 12/24 format handling
            nampm = ("A" if nh < 12 else "P") if state["use_12h"] else "" # AM/PM string handling
            n_str = ("Next: DAILY " if next_a[8] and not is_snooze_next else f"Next: {nmo:02d}/{nd:02d} " if state["use_12h"] else f"Next: {nd:02d}.{nmo:02d}.{ny:04d} ") + f"{ndh:02d}:{nm:02d}{nampm} [{lbl}]" # Assemble final UI string
            
        draw.text(Vector(20, 80), n_str, TFT_WHITE) # Draw next alarm preview text
        
        in_y = 102; r_height = 16 # Menu list layout variables
        egg_str = "RUN" if state["egg_end"] > 0 else "" # Check eggtimer state for badge
        sw_str = "RUN" if state.get("sw_run", False) else "" # Check stopwatch state for badge
        cd_str = "RUN" if state.get("cd_end", 0) > 0 else "" # Check countdown state for badge
        
        for i, (txt, cnt) in enumerate([("Manage Alarms", f"[{len(state['alarms'])}]"), ("Egg Timer", egg_str), ("Stopwatch", sw_str), ("Countdown", cd_str), ("Options Menu", ""), ("View Help", "")]): # Iterate menu items
            r_y = in_y + (i * 16); col = theme_color if c_idx == i else TFT_LIGHTGREY; b_col = theme_color if c_idx == i else TFT_DARKGREY # Styling calculations per row
            if c_idx == i: draw.fill_rectangle(Vector(0, r_y - 2), Vector(screen_w, r_height), TFT_DARKGREY); draw.text(Vector(screen_w - 20, r_y + 1), "<", theme_color) # Draw cursor highlight
            draw.text(Vector(15, r_y + 1), txt, col) # Draw list item text
            if cnt: draw.rect(Vector(160, r_y - 2), Vector(60, r_height), b_col); draw.text(Vector(170, r_y + 1), cnt, theme_color if c_idx == i else TFT_WHITE) # Draw item info badge
            
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color); draw.text(Vector(5, screen_h - 32), "[M]List [N]New [O]Opt [ESC]Exit", theme_color); draw.text(Vector(5, screen_h - 15), "[UP/DN]Nav [ENT]Select", TFT_LIGHTGREY) # Footer hints
    elif state["mode"] == "alarms": # Draw Alarms management list
        c_idx = state["cursor_idx"]; list_len = len(state["alarms"]) + 1 # Variables for view list logic
        draw.text(Vector(10, 10), "MODE: ALARMS LIST", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color) # Header setup
        
        c_sec = time.time(); has_past = False # Tracker variables for rendering
        for i in range(min(4, list_len)): # Max list render limit is 4 items visible
            idx = c_idx - (c_idx % 4) + i # Paginated index calculation
            if idx < list_len: # Check bounds
                r_y = 50 + (i * 35) # Y spacing offset
                if idx == c_idx: draw.fill_rectangle(Vector(0, r_y - 4), Vector(screen_w, 30), TFT_DARKGREY) # Draw cursor block highlight
                if idx < len(state["alarms"]): # Render actual alarm data
                    a = state["alarms"][idx]; is_past = not a[8] and time.mktime((a[0], a[1], a[2], a[3], a[4], 0, 0, 0)) < c_sec # Check if expired date
                    if is_past: has_past = True # Set flag if at least one is past due
                    t_col = theme_color if idx == c_idx else TFT_LIGHTGREY; label_color = TFT_RED if is_past else t_col # Set color coding based on status
                    draw.text(Vector(5, r_y + 1), f"{a[6][:6]}:", label_color); draw.rect(Vector(65, r_y - 4), Vector(250, 30), theme_color if idx == c_idx else TFT_DARKGREY) # Draw label and box
                    stat_str = ("ON*" if a[7] else "ON ") if a[5] else ("OFF*" if a[7] else "OFF ") # Active/Audible status indicator string
                    adh = a[3] % 12 if state["use_12h"] else a[3]; adh = 12 if state["use_12h"] and adh == 0 else adh # 12h/24h convert logic
                    aampm = ("A" if a[3] < 12 else "P") if state["use_12h"] else "" # AM/PM symbol logic
                    a_str = f"DAILY {adh:02d}:{a[4]:02d}{aampm} [{stat_str}]" if a[8] else (f"{a[1]:02d}/{a[2]:02d} " if state["use_12h"] else f"{a[2]:02d}.{a[1]:02d}.{a[0]:04d} ") + f"{adh:02d}:{a[4]:02d}{aampm} [{stat_str}]" # Formatted final list string
                    draw.text(Vector(70, r_y + 1), a_str, TFT_RED if is_past else (theme_color if idx == c_idx else TFT_WHITE)) # Draw main item text
                else: draw.text(Vector(15, r_y + 1), "+ Create New Alarm", theme_color if idx == c_idx else TFT_LIGHTGREY) # Draw new item placeholder text
        
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color); draw.text(Vector(5, screen_h - 32), "[L/R]Tgl " + ("[C]Clr " if has_past else "") + "[N]New [ESC]Back", theme_color); draw.text(Vector(5, screen_h - 15), "[UP/DN]Nav [T]Snd [BS]Del [ENT]Edit", TFT_LIGHTGREY) # Draw complex dynamic footer hints
    elif state["mode"] in ("confirm_delete", "confirm_clear"): # Draw confirmation modal screen
        draw.text(Vector(10, 10), f"MODE: {'DELETE' if state['mode'] == 'confirm_delete' else 'CLEAR'} ALARM(S)", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color) # Header setup
        draw.fill_rectangle(Vector(15, 60), Vector(screen_w - 30, 80), TFT_DARKGREY); draw.rect(Vector(15, 60), Vector(screen_w - 30, 80), theme_color) # Box setup
        draw.text(Vector(25, 70), "Delete this alarm?" if state["mode"] == "confirm_delete" else "Clear past alarms?", TFT_WHITE) # Main question
        if state["mode"] == "confirm_delete": # Specific logic for single alarm delete
            a = state["alarms"][state["cursor_idx"]]; lbl = a[6][:10] # Unpack alarm values
            adh = a[3] % 12 if state["use_12h"] else a[3]; adh = 12 if state["use_12h"] and adh == 0 else adh # 12h/24h logic
            aampm = ("AM" if a[3] < 12 else "PM") if state["use_12h"] else "" # AM/PM string
            dt_str = "DAILY" if a[8] else (f"{a[1]:02d}/{a[2]:02d}" if state["use_12h"] else f"{a[2]:02d}.{a[1]:02d}.{a[0]:04d}") # Prefix date string format
            draw.text(Vector(25, 90), f"{dt_str} {adh:02d}:{a[4]:02d} {aampm} [{lbl}]", theme_color) # Draw target alarm summary
        else: draw.text(Vector(25, 90), "This cannot be undone.", TFT_LIGHTGREY) # Warning text for clear all
        is_yes = state["del_confirm_yes"] if state["mode"] == "confirm_delete" else state["clear_confirm_yes"] # Track selected option
        draw.fill_rectangle(Vector(30, 115), Vector(60, 20), TFT_BLACK if is_yes else TFT_DARKGREY); draw.text(Vector(45, 118), "YES", theme_color if is_yes else TFT_LIGHTGREY) # Draw YES button UI
        draw.fill_rectangle(Vector(140, 115), Vector(60, 20), TFT_BLACK if not is_yes else TFT_DARKGREY); draw.text(Vector(160, 118), "NO", theme_color if not is_yes else TFT_LIGHTGREY) # Draw NO button UI
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color); draw.text(Vector(5, screen_h - 32), "[L/R] Select [ENT] Confirm", theme_color); draw.text(Vector(5, screen_h - 15), "[ESC] Cancel", TFT_LIGHTGREY) # Footer hint setup
    elif state["mode"] in ("edit_type", "edit_date", "edit_h", "edit_m", "edit_l", "edit_aud"): # Draw unified Editor views
        draw.text(Vector(10, 10), "MODE: EDIT ALARM" if state.get("edit_idx", -1) != -1 else "MODE: ADD ALARM", TFT_WHITE); draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color) # Header setup
        out_y = 45; draw.fill_rectangle(Vector(15, out_y + 25), Vector(screen_w - 30, 80 if state["mode"] == "edit_l" else 35), TFT_DARKGREY); draw.rect(Vector(15, out_y + 25), Vector(screen_w - 30, 80 if state["mode"] == "edit_l" else 35), theme_color) # Editor box setup
        if state["mode"] == "edit_type": # Step 1 draw
            draw.text(Vector(15, out_y + 5), "ALARM TYPE:", TFT_LIGHTGREY); draw.text(Vector(40, out_y + 33), f"< {'DAILY' if state['tmp_daily'] else 'SPECIFIC DATE'} >", theme_color, 2) # Toggle UI text
        elif state["mode"] == "edit_date": # Step 2a draw
            draw.text(Vector(15, out_y + 5), "SET DATE:", TFT_LIGHTGREY) # Title setup
            cy, cm, cd = (state["tmp_y"], state["tmp_mo"], state["tmp_d"]) if state["use_12h"] else (state["tmp_d"], state["tmp_mo"], state["tmp_y"]) # Fetch date based on format
            c0, c1, c2 = (theme_color if state["date_cursor"] == i else TFT_WHITE for i in range(3)) # Cursor color mapping logic
            if state["use_12h"]: draw.text(Vector(30, out_y+33), f"{cy:04d}", c0, 2); draw.text(Vector(100, out_y+33), "-", TFT_LIGHTGREY, 2); draw.text(Vector(120, out_y+33), f"{cm:02d}", c1, 2); draw.text(Vector(160, out_y+33), "-", TFT_LIGHTGREY, 2); draw.text(Vector(180, out_y+33), f"{cd:02d}", c2, 2) # Draw US format YYYY-MM-DD
            else: draw.text(Vector(30, out_y+33), f"{cy:02d}", c0, 2); draw.text(Vector(70, out_y+33), ".", TFT_LIGHTGREY, 2); draw.text(Vector(90, out_y+33), f"{cm:02d}", c1, 2); draw.text(Vector(130, out_y+33), ".", TFT_LIGHTGREY, 2); draw.text(Vector(150, out_y+33), f"{cd:04d}", c2, 2) # Draw EU format DD.MM.YYYY
        elif state["mode"] in ("edit_h", "edit_m"): # Step 3 & 4 draw
            draw.text(Vector(15, out_y + 5), "SET TIME:", TFT_LIGHTGREY) # Title setup
            th = state["tmp_h"] % 12 if state["use_12h"] else state["tmp_h"]; th = 12 if state["use_12h"] and th == 0 else th # Format logic
            draw.text(Vector(60, out_y + 33), f"{th:02d}", theme_color if state["mode"] == "edit_h" else TFT_WHITE, 2); draw.text(Vector(100, out_y + 33), ":", TFT_LIGHTGREY, 2); draw.text(Vector(120, out_y + 33), f"{state['tmp_m']:02d}", theme_color if state["mode"] == "edit_m" else TFT_WHITE, 2) # Draw separated Hour and Min fields
            if state["use_12h"]: draw.text(Vector(150, out_y + 33), "AM" if state["tmp_h"] < 12 else "PM", TFT_LIGHTGREY, 2) # Draw AM/PM flag
        elif state["mode"] == "edit_l": # Step 5 draw
            draw.text(Vector(15, out_y + 5), f"SET LABEL ({len(state['tmp_label'])}/50):", TFT_LIGHTGREY) # Title with character count
            v_str = state["tmp_label"] + ("_" if (int(time.time()) % 2 == 0) else "") # Add blinking cursor underscore to end
            for i in range(0, len(v_str), 18): draw.text(Vector(20, out_y + 30 + (i // 18) * 20), v_str[i:i+18], TFT_WHITE, 2) # Wordwrap rendering logic
        elif state["mode"] == "edit_aud": # Step 6 draw
            draw.text(Vector(15, out_y + 5), "AUDIBLE SOUND:", TFT_LIGHTGREY); draw.text(Vector(80, out_y + 33), f"< {'YES' if state['tmp_audible'] else 'NO '} >", theme_color, 2) # Toggle UI text
        draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color); draw.text(Vector(5, screen_h - 32), "[ESC] Cancel / Back", theme_color); draw.text(Vector(5, screen_h - 15), "[ENT] Next / Save", TFT_LIGHTGREY) # Shared footer hints for all edit views

    draw.swap(); state["dirty_ui"] = False # Push frame buffer to hardware screen and reset flag

def start(view_manager): # App initialize hook
    global storage # Get globals
    storage = view_manager.storage # Hook into system storage API
    validate_and_load_settings() # Process saved data
    
    draw = view_manager.draw; screen_w = draw.size.x; screen_h = draw.size.y # Screen layout
    draw.clear(); draw.fill_rectangle(Vector(0, 0), Vector(screen_w, screen_h), rgb_to_565(state["bg_r"], state["bg_g"], state["bg_b"])) # Prep background
    draw.text(Vector(10, 10), f"Eggtimer {_VERSION}", _THEMES[state["theme_idx"]][1]); draw.swap() # Draw logo text
    
    state["dirty_ui"] = True; state["last_s"] = -1 # Setup start state
    
    board_info = os.uname().machine # Fetch the OS machine string to identify the board
    if "Pico 2 W" not in board_info: state["mode"] = "error_hw" # Require hardware with Wi-Fi capability
    elif time.localtime()[0] < 2024: state["mode"] = "error_time" # Trigger time sync warning if offline
    return True # Complete initialization

def run(view_manager): # App main event loop
    draw = view_manager.draw; input_mgr = view_manager.input_manager; button = input_mgr.button # Process context
    t = time.localtime(); c_sec = time.time() # Pull latest timing metrics
    
    check_time_and_alarms(t, c_sec) # Process alarm triggers in background
    
    if button == -1 and not state["dirty_ui"] and not state["dirty_save"]: return # Optimize tick rate out if inactive
    if button != -1: process_input(button, input_mgr, view_manager, t, c_sec) # Pass inputs to handler
    
    if state["dirty_save"] and button == -1: # Execute background saving during idle times
        if state["save_timer"] > 0: state["save_timer"] -= 1 # Countdown before save tick
        else: save_settings() # Trigger flash disk write
        
    if state["dirty_ui"]: draw_view(view_manager) # Trigger screen render if view changed

def stop(view_manager): # App shutdown hook
    save_settings(); handle_audio_silence(); gc.collect() # Safe cleanup and exit
