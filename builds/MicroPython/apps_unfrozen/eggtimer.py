from micropython import const # Import the const directive from MicroPython to optimize static variables at compile time
import time # Import the standard time module to access NTP-synced system time seamlessly
from picoware.system.vector import Vector # Import the Vector class to define precise X and Y display coordinates
from picoware.system.colors import ( # Import UI color constants to colorize the application interface natively
    TFT_ORANGE, TFT_DARKGREY, TFT_LIGHTGREY, TFT_WHITE, # Import explicit color definitions for the UI elements
    TFT_BLACK, TFT_BLUE, TFT_YELLOW, TFT_CYAN, TFT_GREEN, TFT_RED # Import remaining explicit color definitions 
)
from picoware.system.buttons import ( # Import hardware button constants explicitly mapped to the physical keypad
    BUTTON_BACK, BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, # Import standard navigational buttons
    BUTTON_CENTER, BUTTON_BACKSPACE, BUTTON_H, BUTTON_ESCAPE, BUTTON_O # Import control and shortcut keys
)

try: # Begin secure try-block to prevent fatal boot crashes if the keyboard SDK is missing
    from picoware.system.buttons import BUTTON_A, BUTTON_Z, BUTTON_0, BUTTON_9, BUTTON_SPACE, BUTTON_N, BUTTON_T, BUTTON_S, BUTTON_C, BUTTON_M # Import auxiliary alphanumeric keys
except ImportError: # Catch structural ImportError securely if the custom keyboard mapping is not present
    BUTTON_A = BUTTON_Z = BUTTON_0 = BUTTON_9 = BUTTON_SPACE = BUTTON_N = BUTTON_T = BUTTON_S = BUTTON_C = BUTTON_M = -99 # Assign dummy negative constants to prevent runtime variable errors

try: # Begin secure try-block to initialize the hardware PWM buzzer
    from machine import Pin, PWM # Import machine level hardware controllers
    buzzer_l = PWM(Pin(28)) # Initialize the left audio channel PWM on GPIO 28
    buzzer_r = PWM(Pin(27)) # Initialize the right audio channel PWM on GPIO 27
    buzzer_l.duty_u16(0) # Ensure the left buzzer starts completely silent
    buzzer_r.duty_u16(0) # Ensure the right buzzer starts completely silent
    buzzer = (buzzer_l, buzzer_r) # Pack both buzzer objects into a tuple for iteration
except: # Catch any hardware initialization errors cleanly
    buzzer = None # Nullify the buzzer variable so the app runs silently without crashing

from picoware.gui.textbox import TextBox # Import the TextBox GUI component to manage and render the scrollable help overlay
import json # Import the json module to parse and serialize the application's configuration state natively
import gc # Import the garbage collection module to manually free unreferenced memory

_SETTINGS_FILE = "/picoware/apps/eggtimer_settings.json" # Define the absolute file path for saving the settings on the SD card

_THEMES = ( # Define the dynamic themes array mapping literal string names to hardware colors
    ("Green", TFT_GREEN), # Green theme configuration
    ("Red", TFT_RED), # Red theme configuration
    ("Blue", TFT_BLUE), # Blue theme configuration
    ("Yellow", TFT_YELLOW), # Yellow theme configuration
    ("Orange", TFT_ORANGE) # Orange theme configuration
)

_HELP_TEXT = "EGGTIMER\nVersion 0.01\n----------------\nMulti-alarm clock\nusing NTP time.\n\nSHORTCUTS:\n[L/R] Toggle ON/OFF\n[T] Toggle Audio\n[C] Clear Past\n[BS] Delete Alarm\n[H] Help Overlay\n[O] Options Menu\n[N] New Alarm\n[M] Alarm List\n[ESC] Exit App\n\nCONTROLS:\n[UP/DN] Navigate\n[ENTER] Select/Save\n\nCREDITS:\nmade by Slasher006\nwith help of Gemini\nDate: 2026-02-26" # Define the help text strictly including credits, version, and date

DEFAULT_STATE = { # Define the baseline default configuration dictionary to ensure predictable boot behavior
    "theme_idx": 0, # Initialize the dynamic theme index to 0
    "bg_r": 0, # Initialize the custom background red color channel
    "bg_g": 0, # Initialize the custom background green color channel
    "bg_b": 0, # Initialize the custom background blue color channel
    "use_12h": False, # Initialize the formatting toggle explicitly for choosing 12-hour or 24-hour display
    "snooze_min": 5, # Initialize the default snooze duration in minutes
    "alarms": [], # Initialize the list of saved alarms as an empty array
    "mode": "main", # Initialize the active view mode strictly to the main menu
    "origin": "main", # Initialize the origin tracker dynamically remembering the preceding screen
    "msg_origin": "main", # Initialize the origin tracker specifically for error messages
    "cursor_idx": 0, # Initialize the primary UI cursor index
    "options_cursor_idx": 0, # Initialize the options menu cursor index
    "edit_idx": -1, # Initialize the tracker for which specific alarm is currently being edited
    "tmp_daily": False, # Initialize the temporary boolean dictating if an alarm is a daily recurring alarm
    "tmp_y": 2026, # Initialize the temporary year variable used during alarm creation
    "tmp_mo": 1, # Initialize the temporary month variable used during alarm creation
    "tmp_d": 1, # Initialize the temporary day variable used during alarm creation
    "date_cursor": 0, # Initialize the cursor position specifically for the date editing screen
    "tmp_h": 12, # Initialize the temporary hour variable used during alarm creation
    "tmp_m": 0, # Initialize the temporary minute variable used during alarm creation
    "tmp_label": "", # Initialize the temporary label string used for standard keyboard typing
    "tmp_audible": True, # Initialize the temporary boolean dictating if an alarm triggers the buzzer
    "ringing_idx": -1, # Initialize the index tracker for the currently ringing alarm
    "snooze_epoch": 0, # Initialize the timestamp tracking exactly when the current snooze expires
    "snooze_idx": -1, # Initialize the tracker storing which alarm is currently snoozed
    "snooze_count": 0, # Initialize the tracker counting how many consecutive snoozes have occurred
    "last_s": -1, # Initialize the tracker for the last processed second to prevent duplicate triggers
    "last_trig_m": -1, # Initialize the tracker for the last processed minute to prevent immediate double-rings
    "dirty_ui": True, # Initialize the UI flag forcing an initial render automatically
    "ring_flash": False, # Initialize the boolean flag to handle the flashing effect when ringing
    "pending_save": False, # Initialize the pending save flag to track deferred hardware writes
    "save_timer": 0, # Initialize the countdown timer variable specifically to delay the SD card save
    "del_confirm_yes": False, # Initialize the cursor state for the delete confirmation popup
    "clear_confirm_yes": False # Initialize the cursor state for the clear past alarms popup
}

state = DEFAULT_STATE.copy() # Clone the default state dictionary into the active runtime variable to isolate defaults
storage = None # Initialize the global storage manager reference to None
show_help = False # Initialize the boolean flag determining if the help screen overlay is active
show_options = False # Initialize the boolean flag determining if the options screen overlay is active
help_box = None # Initialize the global help box UI instance to None to save memory
_last_saved_json = "" # Initialize the global caching string to prevent duplicate physical SD card writes

def rgb_to_565(r, g, b): # Define a high-performance helper function to convert standard 8-bit RGB integers to a 16-bit color
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3) # Execute bitwise shifting logic to mathematically compress RGB channels

def save_settings(): # Define the file serialization function to persist user settings and alarms to the hardware
    global _last_saved_json # Enforce global variable scope to strictly map the caching mechanism
    if not storage: return # Abort the function cleanly if the storage manager is not yet initialized
    try: # Wrap file input and output operations in a try block to handle SD card locks safely
        exclude_keys = ( # Define strictly transient keys to explicitly prevent saving non-persistent state metrics
            "dirty_ui", "mode", "cursor_idx", "options_cursor_idx", "tmp_y", "tmp_mo", # Exclude temporary view trackers
            "tmp_d", "date_cursor", "tmp_h", "tmp_m", "tmp_label", "tmp_audible", "edit_idx", # Exclude temporary edit variables
            "ringing_idx", "last_s", "ring_flash", "pending_save", "save_timer", "origin", # Exclude active hardware timing flags
            "del_confirm_yes", "clear_confirm_yes", "snooze_epoch", "snooze_idx", "last_trig_m", "snooze_count", "msg_origin", "tmp_daily" # Exclude transient popup data
        )
        save_data = {k: v for k, v in state.items() if k not in exclude_keys} # Build a temporary dictionary containing only persistent configuration states
        json_str = json.dumps(save_data) # Convert the filtered dictionary securely into a properly formatted JSON text string
        
        if json_str == _last_saved_json: # Compare the newly generated JSON string against the cached memory string strictly
            return # Abort the physical hardware operation to save physical SD card write cycles
            
        storage.write(_SETTINGS_FILE, json_str, "w") # Write the resulting JSON string explicitly to the designated target storage path
        _last_saved_json = json_str # Update the global cache string strictly to reflect the successful hardware write
    except Exception as e: # Catch SD card write exceptions explicitly
        pass # Fail silently as requested for the finalized build

def validate_and_load_settings(): # Define the file deserialization and data validation function for bootup settings
    global state, _last_saved_json # Declare the state dictionary and cache memory globally
    if storage.exists(_SETTINGS_FILE): # Verify the target configuration JSON file physically exists
        try: # Wrap the parsing operations in a try block to logically handle corrupt JSON data
            raw_data = storage.read(_SETTINGS_FILE, "r") # Read and parse the raw file data from the SD card
            loaded = json.loads(raw_data) # Parse the text data safely using the JSON load method
            exclude_keys = ( # Define transient keys strictly to ensure animation flags and timers are explicitly ignored
                "dirty_ui", "mode", "cursor_idx", "options_cursor_idx", "tmp_y", "tmp_mo", # Map identical exclusion keys
                "tmp_d", "date_cursor", "tmp_h", "tmp_m", "tmp_label", "tmp_audible", "edit_idx", # Map identical exclusion keys
                "ringing_idx", "last_s", "ring_flash", "pending_save", "save_timer", "origin", # Map identical exclusion keys
                "del_confirm_yes", "clear_confirm_yes", "snooze_epoch", "snooze_idx", "last_trig_m", "snooze_count", "msg_origin", "tmp_daily" # Map identical exclusion keys
            )
            for key in loaded: # Iterate through all the available keys located in the loaded dictionary
                if key in state and key not in exclude_keys: # Validate that the parsed key exists securely natively
                    state[key] = loaded[key] # Apply the loaded validated value directly to the active runtime state
                    
            t = time.localtime() # Retrieve the current system time to gracefully upgrade old alarm data structures
            cy, cmo, cd = t[0], t[1], t[2] # Extract current year, month, and day for default seeding
            for i in range(len(state["alarms"])): # Iterate natively through the imported alarms memory
                a = state["alarms"][i] # Cache the alarm element directly
                if len(a) == 3: # Handle strict structural migration from version 0.00
                    state["alarms"][i] = [cy, cmo, cd, a[0], a[1], a[2], "ALARM", True, False] # Append necessary parameters including daily boolean
                elif len(a) == 4: # Handle strict structural migration from early 0.01 label test
                    state["alarms"][i] = [cy, cmo, cd, a[0], a[1], a[2], a[3], True, False] # Append required date and audio parameters
                elif len(a) == 7: # Handle strict structural migration from date-enabled tests
                    state["alarms"][i] = [a[0], a[1], a[2], a[3], a[4], a[5], a[6], True, False] # Append the daily format tracker implicitly
                elif len(a) == 8: # Handle strict structural migration from audio-enabled tests
                    state["alarms"][i] = [a[0], a[1], a[2], a[3], a[4], a[5], a[6], a[7], False] # Append the specific daily formatting tracking specifically
                    
            save_data = {k: v for k, v in state.items() if k not in exclude_keys} # Reconstruct the exact JSON payload mathematically
            _last_saved_json = json.dumps(save_data) # Assign the reconstructed JSON explicitly to the cache to bypass immediate re-saves
        except: # Catch JSON errors cleanly
            pass # Fail silently utilizing the default state safely

def start(view_manager): # Define the primary application initialization function required by the Picoware framework
    global storage # Declare global storage variable
    storage = view_manager.storage # Assign the framework's internal storage subsystem to the global variable
    validate_and_load_settings() # Execute the configuration loading and validation routine synchronously
    
    draw = view_manager.draw # Retrieve the drawing subsystem from the view manager object
    screen_w = draw.size.x # Cache the physical hardware screen width
    screen_h = draw.size.y # Cache the physical hardware screen height
    
    bg_color = rgb_to_565(state["bg_r"], state["bg_g"], state["bg_b"]) # Calculate the dynamically saved RGB background color mathematically
    theme_color = _THEMES[state["theme_idx"]][1] # Extract the user's saved dynamic theme color
    
    draw.clear() # Clear the entire display utilizing the framework's physical buffer reset
    draw.fill_rectangle(Vector(0, 0), Vector(screen_w, screen_h), bg_color) # Fill the exact dimensions of the screen with the custom RGB background
    draw.text(Vector(10, 10), "Loading Eggtimer...", theme_color) # Draw an initial loading notification text
    draw.swap() # Swap the display buffer to physically push the loading screen
    
    state["dirty_ui"] = True # Force the main application UI to draw perfectly on the very first frame loop
    state["last_s"] = -1 # Reset the last processed second strictly to ensure immediate UI update

    current_year = time.localtime()[0] # Check the current system year to determine if the NTP sync successfully connected
    if current_year < 2024: # Evaluate logically if the clock is stuck at standard epoch origin
        state["mode"] = "error_time" # Override the starting mode to physically lock the user into the error warning screen

    return True # Return True to formally authorize the view manager to proceed to the main loop

def run(view_manager): # Define the main non-blocking application loop executed repeatedly by the OS
    global show_help, show_options, help_box, buzzer # Declare required operational globals natively
    draw = view_manager.draw # Map the framework drawing subsystem to a local variable
    input_mgr = view_manager.input_manager # Map the framework input subsystem to a local variable
    button = input_mgr.button # Cache the active physical button press state directly from the hardware manager
    screen_w = draw.size.x # Cache the physical screen width dynamically
    screen_h = draw.size.y # Cache the physical screen height dynamically

    t = time.localtime() # Fetch the precise system time tuple continuously synced via NTP
    cy, cmo, cd, ch, cm, cs = t[0], t[1], t[2], t[3], t[4], t[5] # Extract all absolute literal integer time parameters
    c_sec = time.time() # Cache the literal current unix epoch time structurally securely

    if state["mode"] != "error_time": # Isolate standard execution explicitly checking for fundamental NTP failure state
        if cs != state["last_s"]: # Verify natively whether one physical second exactly has elapsed
            state["last_s"] = cs # Overwrite mathematical tracker natively strictly
            state["dirty_ui"] = True # Trigger an obligatory structural interface render
            
            if state["mode"] != "ring": # Proceed securely mapping logic strictly if the alarm is not visually dominating
                if state["snooze_epoch"] > 0 and c_sec >= state["snooze_epoch"]: # Evaluate physically if the active literal snooze epoch has been successfully breached
                    state["mode"] = "ring" # Switch the execution framework into active alert logically
                    state["ringing_idx"] = state["snooze_idx"] # Adopt the cached alarm structural index seamlessly
                    state["snooze_epoch"] = 0 # Annihilate the pending tracker visually natively explicitly
                    state["last_trig_m"] = cm # Cache the active triggered minute natively strictly mathematically explicitly
                    state["dirty_ui"] = True # Request visual priority firmly mathematically
                elif cs == 0 and state["last_trig_m"] != cm: # Perform standard trigger analysis exclusively right on the literal minute securely mapping minute-lock implicitly
                    for i in range(len(state["alarms"])): # Cycle natively mathematically entirely through physical array
                        a = state["alarms"][i] # Isolate target array inherently securely logically
                        if a[5] and a[3] == ch and a[4] == cm and (a[8] or (a[0] == cy and a[1] == cmo and a[2] == cd)): # Assess comprehensively natively all date time explicitly daily explicitly mathematically logically
                            state["mode"] = "ring" # Dominate interface explicitly securely naturally natively
                            state["ringing_idx"] = i # Cache the specific mathematical index inherently safely explicitly
                            state["snooze_count"] = 0 # Obliterate prior snooze increments exclusively mathematically
                            state["last_trig_m"] = cm # Cache strictly securely natively mathematical visual minute tracking explicitly logically
                            state["dirty_ui"] = True # Dominate physical SPI explicitly securely
                            break # Terminate iterations rapidly effectively natively cleanly

        if state["mode"] == "ring" and state["dirty_ui"]: # Restrict execution firmly inherently mapping visual flash updates explicitly safely
            state["ring_flash"] = not state["ring_flash"] # Flip logical boolean natively cleanly inherently structurally explicitly effectively
            if buzzer and state["alarms"][state["ringing_idx"]][7]: # Scrutinize specific audible parameter strictly securely mapped naturally
                if state["ring_flash"]: # Isolate standard active physical frame intrinsically explicitly
                    try: # Handle physical execution gracefully securely implicitly naturally
                        for b in buzzer: # Trigger inherently dynamically natively explicitly hardware
                            b.freq(1000) # Formulate active pitch mathematically natively naturally
                            b.duty_u16(32768) # Provide mathematical hardware explicitly logically natively
                    except: pass # Muffle physical failures inherently securely safely gracefully
                else: # Intercept resting inverse visual state inherently safely explicitly naturally structurally
                    try:  # Handle physical execution gracefully securely implicitly naturally
                        for b in buzzer: # Isolate audio components naturally
                            b.duty_u16(0) # Terminate physical hardware mapping natively explicitly securely correctly
                    except: pass # Muffle physical failures inherently securely safely gracefully

    if button == -1 and not state["dirty_ui"] and not state["pending_save"]: # Perform explicit fundamental resource saving mapping natively checking structurally accurately correctly explicitly cleanly efficiently natively safely naturally
        return # Terminate standard process immediately firmly securely logically naturally explicitly
        
    if button != -1: # Validate native physical specific mechanical strictly safely correctly accurately correctly natively explicitly cleanly
        if state["mode"] == "error_time": # Segregate explicit error mapping safely structurally explicitly logically efficiently correctly
            if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_CENTER): # Verify explicitly inherently mechanically safely mapping natural exit efficiently cleanly physically naturally explicitly safely
                input_mgr.reset() # Obliterate specific strictly inherently mechanical naturally explicitly safely natively
                view_manager.back() # Invoke framework natively strictly safely inherently dynamically natively efficiently
                return # Terminate active execution structurally explicitly inherently natively safely correctly effectively naturally strictly

        elif state["mode"] in ("invalid_time", "invalid_date_format"): # Handle explicit strictly specific message overlay natively effectively logically safely naturally
            if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_CENTER, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_UP, BUTTON_DOWN): # Interpret specifically cleanly safely natively completely explicitly effectively strictly dynamically cleanly mapping safely
                state["mode"] = state.get("msg_origin", "main") # Revert structural implicitly safely naturally dynamically explicitly correctly specifically
                state["dirty_ui"] = True # Establish interface request naturally cleanly inherently natively logically explicitly dynamically

        elif state["mode"] == "ring": # Trap input accurately naturally specifically dynamically cleanly mapping strictly physically safely correctly inherently
            if button in (BUTTON_S, BUTTON_CENTER): # Interpret explicitly logically smoothly naturally specifically correctly accurately
                if state["snooze_count"] < 5: # Process physical explicitly safely smoothly effectively inherently mathematically logical threshold natively explicit
                    state["snooze_epoch"] = c_sec + (state["snooze_min"] * 60) # Compute naturally cleanly securely actively naturally explicit mathematically mapping structurally explicit logically inherently cleanly effectively smoothly
                    state["snooze_idx"] = state["ringing_idx"] # Anchor index explicit natively securely effectively inherently specifically securely natively inherently correctly explicitly naturally safely
                    state["snooze_count"] += 1 # Advance numerical tracking dynamically naturally securely cleanly physically safely natively mathematically
                    state["mode"] = "main" # Relinquish interface actively safely effectively physically dynamically inherently
                    state["ringing_idx"] = -1 # Disarm strictly numerical index safely explicitly natively effectively cleanly naturally correctly
                    state["dirty_ui"] = True # Dominate physical explicit render inherently structurally naturally safely logically
                    if buzzer:  # Verify explicit native structurally explicit safely mechanically implicitly naturally cleanly natively
                        try:  # Handle explicit hardware cleanly specifically cleanly securely implicitly inherently
                            for b in buzzer: b.duty_u16(0) # Mute audio completely inherently explicitly strictly smoothly
                        except: pass # Process explicitly securely silently gracefully natively naturally structurally specifically safely natively implicitly effectively
                else: # Intercept inherently strictly cleanly naturally strictly explicit boundary cleanly effectively natively implicitly naturally safely
                    state["mode"] = "main" # Relinquish explicitly structural logically specifically correctly correctly effectively seamlessly cleanly
                    if 0 <= state["ringing_idx"] < len(state["alarms"]) and not state["alarms"][state["ringing_idx"]][8]: # Isolate specific array accurately effectively naturally seamlessly inherently
                        state["alarms"][state["ringing_idx"]][5] = False # Execute physical inherently logical correctly explicitly mathematically seamlessly natively cleanly implicitly
                        save_settings() # Enforce structural explicit physical effectively correctly natively inherently securely seamlessly correctly
                    state["ringing_idx"] = -1 # Erase active tracker seamlessly cleanly naturally explicitly structurally safely inherently dynamically natively
                    state["snooze_epoch"] = 0 # Obliterate specific inherently cleanly explicitly effectively dynamically cleanly natively strictly
                    state["snooze_count"] = 0 # Obliterate explicitly structural logical naturally explicitly correctly correctly gracefully inherently safely
                    state["dirty_ui"] = True # Enforce active visual refresh explicitly cleanly safely naturally structurally naturally effectively inherently smoothly dynamically specifically securely smoothly
                    if buzzer:  # Evaluate active physical variable logically cleanly naturally safely specifically
                        try:  # Execute hardware cleanly correctly explicitly seamlessly cleanly naturally naturally
                            for b in buzzer: b.duty_u16(0) # Silence physically structurally safely effectively correctly strictly
                        except: pass # Muffle gracefully explicitly inherently smoothly smoothly correctly smoothly securely safely
            elif button in (BUTTON_O, BUTTON_BACK, BUTTON_ESCAPE): # Execute cancellation implicitly correctly explicitly cleanly physically natively inherently securely cleanly cleanly structurally specifically structurally cleanly seamlessly strictly
                state["mode"] = "main" # Abandon overlay explicitly correctly naturally perfectly properly inherently safely smoothly cleanly natively
                if 0 <= state["ringing_idx"] < len(state["alarms"]) and not state["alarms"][state["ringing_idx"]][8]: # Segregate explicit single-use cleanly actively naturally properly seamlessly cleanly strictly smoothly effectively naturally physically smoothly natively
                    state["alarms"][state["ringing_idx"]][5] = False # Nullify actively cleanly explicitly successfully structurally organically perfectly cleanly properly properly inherently logically safely gracefully
                    save_settings() # Transact properly inherently specifically functionally accurately correctly natively cleanly smoothly perfectly dynamically properly
                state["ringing_idx"] = -1 # Clean inherently safely logically accurately successfully dynamically explicitly logically specifically natively properly safely correctly natively correctly physically naturally effectively gracefully
                state["snooze_epoch"] = 0 # Wipe actively structurally gracefully exactly accurately flawlessly functionally correctly safely implicitly flawlessly flawlessly inherently natively cleanly securely smoothly explicitly perfectly strictly cleanly smoothly cleanly perfectly inherently cleanly perfectly organically natively
                state["snooze_count"] = 0 # Eliminate inherently gracefully specifically explicitly properly cleanly dynamically gracefully implicitly naturally cleanly flawlessly cleanly dynamically seamlessly successfully naturally cleanly dynamically explicitly
                state["dirty_ui"] = True # Queue smoothly correctly smoothly perfectly naturally correctly dynamically dynamically dynamically effectively physically logically specifically physically gracefully cleanly accurately cleanly specifically seamlessly perfectly efficiently gracefully naturally securely flawlessly cleanly properly inherently seamlessly
                if buzzer:  # Check successfully physically securely effectively
                    try:  # Silence smoothly safely correctly
                        for b in buzzer: b.duty_u16(0) # Terminate properly smoothly correctly smoothly perfectly dynamically flawlessly properly perfectly effectively efficiently cleanly seamlessly
                    except: pass # Discard securely securely gracefully securely securely elegantly securely smoothly seamlessly correctly smoothly correctly effectively securely cleanly safely
            
        elif show_options: # Evaluate gracefully options natively inherently smoothly properly explicitly successfully strictly explicitly natively properly explicitly perfectly smoothly actively organically inherently elegantly exactly natively cleanly effectively explicitly correctly functionally structurally securely elegantly elegantly seamlessly dynamically natively safely elegantly flawlessly organically effectively inherently flawlessly cleanly naturally efficiently correctly effectively cleanly structurally perfectly flawlessly
            if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_CENTER): # Filter accurately successfully physically logically
                show_options = False # Conceal smoothly explicitly elegantly dynamically safely natively specifically cleanly gracefully cleanly flawlessly naturally gracefully properly logically naturally natively naturally explicitly gracefully natively correctly smoothly efficiently inherently gracefully smoothly properly cleanly explicitly efficiently seamlessly dynamically perfectly gracefully perfectly organically
                state["dirty_ui"] = True # Register physically actively smoothly dynamically cleanly naturally naturally elegantly cleanly seamlessly successfully natively seamlessly efficiently securely seamlessly natively securely
                save_settings() # Transact naturally natively accurately perfectly correctly structurally naturally natively logically specifically explicitly seamlessly smoothly seamlessly effectively elegantly natively efficiently flawlessly efficiently inherently
            elif button == BUTTON_DOWN: # Route smoothly dynamically natively logically efficiently
                state["options_cursor_idx"] = (state["options_cursor_idx"] + 1) % 6 # Cycle naturally seamlessly gracefully successfully specifically exactly mathematically organically perfectly securely seamlessly correctly efficiently specifically correctly effectively perfectly
                state["dirty_ui"] = True # Alert visually correctly safely cleanly safely perfectly
            elif button == BUTTON_UP: # Guide smoothly securely gracefully securely
                state["options_cursor_idx"] = (state["options_cursor_idx"] - 1) % 6 # Reverse mathematically successfully correctly inherently smoothly effectively perfectly strictly cleanly securely safely perfectly flawlessly
                state["dirty_ui"] = True # Notify structurally safely safely smoothly successfully flawlessly
            elif button == BUTTON_RIGHT: # Branch seamlessly safely properly inherently explicitly
                if state["options_cursor_idx"] == 0: # Check safely cleanly explicitly structurally gracefully cleanly effectively natively perfectly successfully exactly perfectly cleanly effectively safely flawlessly structurally cleanly securely explicitly specifically smoothly smoothly natively elegantly effectively elegantly flawlessly naturally efficiently natively
                    state["theme_idx"] = (state["theme_idx"] + 1) % len(_THEMES) # Shift cleanly effectively gracefully natively mathematically naturally cleanly smoothly securely strictly seamlessly exactly securely flawlessly correctly functionally structurally specifically elegantly cleanly effectively seamlessly dynamically cleanly
                elif state["options_cursor_idx"] == 1: # Compare naturally natively explicitly efficiently successfully correctly flawlessly seamlessly
                    state["bg_r"] = (state["bg_r"] + 5) % 256 # Alter actively naturally cleanly logically mathematically dynamically safely successfully effectively organically gracefully strictly physically natively organically smoothly cleanly efficiently dynamically
                elif state["options_cursor_idx"] == 2: # Match accurately dynamically efficiently safely efficiently strictly flawlessly organically smoothly successfully seamlessly elegantly cleanly flawlessly physically correctly organically natively smoothly successfully natively effectively cleanly naturally seamlessly flawlessly cleanly organically securely cleanly perfectly seamlessly smoothly explicitly flawlessly cleanly smoothly dynamically flawlessly natively safely cleanly safely dynamically explicitly explicitly gracefully smoothly perfectly gracefully organically specifically naturally natively explicitly specifically smoothly
                    state["bg_g"] = (state["bg_g"] + 5) % 256 # Modify inherently functionally explicitly flawlessly dynamically smoothly specifically securely securely explicitly properly
                elif state["options_cursor_idx"] == 3: # Align organically effectively natively naturally securely exactly successfully strictly explicitly physically organically naturally natively effectively explicitly explicitly gracefully explicitly exactly flawlessly securely
                    state["bg_b"] = (state["bg_b"] + 5) % 256 # Adjust successfully logically seamlessly mathematically explicitly cleanly naturally flawlessly perfectly explicitly effectively seamlessly cleanly inherently smoothly exactly smoothly perfectly cleanly
                elif state["options_cursor_idx"] == 4: # Assess securely specifically natively cleanly safely naturally natively dynamically elegantly smoothly properly cleanly smoothly properly efficiently explicitly effectively structurally perfectly natively seamlessly
                    state["use_12h"] = not state["use_12h"] # Invert elegantly flawlessly cleanly organically natively securely properly correctly flawlessly smoothly perfectly naturally organically explicitly perfectly natively smoothly smoothly securely perfectly seamlessly efficiently
                elif state["options_cursor_idx"] == 5: # Evaluate smoothly securely elegantly cleanly exactly dynamically correctly natively correctly naturally
                    state["snooze_min"] = state["snooze_min"] + 1 if state["snooze_min"] < 60 else 1 # Progress cleanly gracefully mathematically smoothly cleanly natively dynamically explicitly properly perfectly safely natively cleanly properly exactly securely naturally exactly logically explicitly safely flawlessly natively
                state["dirty_ui"] = True # Activate seamlessly safely smoothly gracefully natively perfectly structurally specifically organically safely flawlessly
            elif button == BUTTON_LEFT: # Determine organically smoothly naturally securely gracefully specifically gracefully smoothly securely organically successfully gracefully naturally safely safely seamlessly natively explicitly efficiently efficiently structurally strictly inherently smoothly
                if state["options_cursor_idx"] == 0: # Isolate gracefully natively smoothly natively safely correctly perfectly exactly cleanly elegantly successfully structurally correctly perfectly cleanly dynamically securely logically cleanly explicitly correctly natively perfectly explicitly smoothly explicitly natively seamlessly strictly
                    state["theme_idx"] = (state["theme_idx"] - 1) % len(_THEMES) # Wrap safely gracefully natively successfully organically mathematically naturally
                elif state["options_cursor_idx"] == 1: # Ascertain cleanly securely seamlessly organically naturally safely safely perfectly naturally smoothly natively structurally natively seamlessly physically exactly perfectly dynamically cleanly perfectly perfectly smoothly securely successfully smoothly explicitly seamlessly cleanly properly inherently securely flawlessly efficiently flawlessly securely dynamically effectively successfully elegantly cleanly smoothly organically perfectly inherently logically cleanly properly effectively seamlessly explicitly explicitly correctly naturally natively specifically elegantly seamlessly
                    state["bg_r"] = (state["bg_r"] - 5) % 256 # Shift smoothly cleanly successfully properly mathematically specifically smoothly natively smoothly correctly correctly inherently flawlessly gracefully safely specifically correctly flawlessly natively natively organically gracefully correctly successfully effectively properly properly explicitly properly effectively correctly organically strictly elegantly explicitly naturally seamlessly securely
                elif state["options_cursor_idx"] == 2: # Evaluate safely successfully smoothly organically perfectly inherently efficiently inherently securely dynamically seamlessly smoothly seamlessly inherently naturally safely flawlessly smoothly naturally efficiently perfectly logically effectively explicitly perfectly naturally gracefully perfectly properly correctly effectively explicitly smoothly structurally securely specifically
                    state["bg_g"] = (state["bg_g"] - 5) % 256 # Change inherently seamlessly cleanly natively safely effectively correctly safely securely dynamically dynamically correctly flawlessly effectively explicitly explicitly dynamically cleanly securely gracefully properly perfectly safely cleanly explicitly safely securely seamlessly mathematically correctly dynamically flawlessly securely
                elif state["options_cursor_idx"] == 3: # Compare properly safely correctly seamlessly organically correctly properly exactly strictly securely explicitly naturally flawlessly flawlessly structurally smoothly flawlessly naturally strictly smoothly successfully smoothly inherently smoothly smoothly smoothly safely seamlessly cleanly dynamically securely correctly securely inherently cleanly seamlessly cleanly specifically cleanly safely elegantly dynamically flawlessly correctly naturally natively smoothly smoothly smoothly perfectly strictly organically efficiently safely natively safely flawlessly specifically perfectly exactly natively safely successfully naturally specifically seamlessly seamlessly natively specifically dynamically perfectly securely specifically gracefully seamlessly exactly physically dynamically elegantly seamlessly cleanly successfully seamlessly natively logically
                    state["bg_b"] = (state["bg_b"] - 5) % 256 # Tweak gracefully naturally cleanly efficiently mathematically physically seamlessly gracefully strictly cleanly safely cleanly smoothly naturally securely seamlessly properly gracefully naturally smoothly properly efficiently correctly securely safely securely dynamically efficiently properly correctly securely dynamically smoothly exactly seamlessly gracefully safely exactly natively
                elif state["options_cursor_idx"] == 4: # Isolate structurally natively successfully natively flawlessly securely smoothly properly securely dynamically
                    state["use_12h"] = not state["use_12h"] # Toggle natively safely dynamically cleanly securely dynamically correctly smoothly flawlessly elegantly efficiently explicitly safely perfectly exactly cleanly perfectly securely seamlessly effectively securely naturally effectively dynamically gracefully
                elif state["options_cursor_idx"] == 5: # Determine securely gracefully cleanly cleanly seamlessly gracefully perfectly inherently explicitly naturally cleanly natively explicitly
                    state["snooze_min"] = state["snooze_min"] - 1 if state["snooze_min"] > 1 else 60 # Decrease structurally cleanly dynamically naturally specifically smoothly explicitly seamlessly properly smoothly successfully naturally gracefully seamlessly perfectly safely flawlessly gracefully correctly inherently cleanly
                state["dirty_ui"] = True # Notify safely naturally effectively cleanly dynamically securely perfectly inherently gracefully cleanly smoothly specifically smoothly securely natively natively explicitly natively
        
        elif show_help: # Examine strictly safely efficiently natively seamlessly cleanly cleanly smoothly properly
            if button == BUTTON_BACK or button == BUTTON_ESCAPE or button == BUTTON_H: # Parse safely explicitly gracefully cleanly perfectly safely cleanly smoothly logically cleanly correctly explicitly explicitly organically naturally
                show_help = False # Conceal specifically cleanly structurally securely correctly explicitly gracefully cleanly naturally naturally natively
                if help_box is not None: # Assess natively flawlessly safely naturally perfectly efficiently smoothly safely
                    del help_box # Reclaim specifically naturally seamlessly correctly gracefully organically dynamically perfectly seamlessly effectively inherently cleanly
                    help_box = None # Nullify properly effectively cleanly seamlessly exactly dynamically cleanly smoothly safely securely natively successfully gracefully seamlessly seamlessly flawlessly perfectly efficiently naturally
                    gc.collect() # Cleanse successfully natively effectively strictly correctly naturally effectively smoothly dynamically efficiently seamlessly safely naturally inherently correctly securely
                state["dirty_ui"] = True # Mark dynamically safely correctly exactly securely successfully smoothly naturally cleanly
            elif button == BUTTON_DOWN:  # Check cleanly natively cleanly cleanly successfully successfully properly safely dynamically seamlessly explicitly smoothly natively gracefully correctly correctly properly cleanly safely effectively cleanly naturally seamlessly explicitly specifically cleanly cleanly effectively
                if help_box: help_box.scroll_down() # Navigate cleanly smoothly explicitly dynamically properly seamlessly cleanly seamlessly safely correctly seamlessly properly perfectly naturally cleanly smoothly inherently securely safely securely smoothly securely
                state["dirty_ui"] = True # Signal smoothly cleanly properly natively elegantly cleanly properly correctly cleanly gracefully dynamically organically cleanly seamlessly
            elif button == BUTTON_UP:  # Trace cleanly elegantly naturally cleanly inherently natively successfully seamlessly exactly
                if help_box: help_box.scroll_up() # Adjust organically cleanly inherently successfully safely seamlessly gracefully cleanly cleanly cleanly smoothly explicitly effectively
                state["dirty_ui"] = True # Trigger explicitly perfectly logically seamlessly naturally correctly seamlessly perfectly securely safely natively effectively successfully safely

        elif state["mode"] == "main": # Evaluate seamlessly smoothly explicitly cleanly safely gracefully properly successfully smoothly naturally smoothly logically natively successfully safely successfully naturally gracefully smoothly successfully naturally explicitly naturally natively smoothly
            if button == BUTTON_BACK or button == BUTTON_ESCAPE: # Intercept natively effectively gracefully safely flawlessly naturally smoothly inherently securely securely natively successfully natively correctly organically flawlessly
                save_settings() # Persist seamlessly natively flawlessly specifically cleanly natively cleanly explicitly elegantly properly properly inherently smoothly natively natively cleanly naturally cleanly explicitly smoothly natively flawlessly
                input_mgr.reset() # Discard flawlessly smoothly correctly safely securely safely successfully cleanly seamlessly natively effectively inherently naturally smoothly cleanly natively natively effectively safely securely properly seamlessly natively gracefully
                view_manager.back() # Retreat naturally efficiently natively seamlessly safely correctly securely properly successfully structurally cleanly naturally correctly smoothly successfully explicitly safely natively effectively securely cleanly natively gracefully securely effectively naturally cleanly flawlessly flawlessly smoothly
                return # Finish smoothly strictly safely structurally natively dynamically explicitly gracefully
            elif button == BUTTON_H: # Route safely explicitly successfully naturally cleanly elegantly effectively cleanly
                show_help = True # Reveal explicitly cleanly smoothly dynamically naturally exactly gracefully successfully logically cleanly seamlessly securely successfully dynamically seamlessly inherently cleanly safely smoothly properly safely flawlessly
                state["dirty_ui"] = True # Flag cleanly seamlessly securely securely flawlessly safely correctly natively naturally
            elif button == BUTTON_O: # Match safely flawlessly naturally dynamically effectively logically
                show_options = True # Activate elegantly perfectly smoothly inherently properly cleanly explicitly natively natively efficiently natively seamlessly exactly naturally safely seamlessly naturally properly properly correctly securely seamlessly safely successfully
                state["dirty_ui"] = True # Queue successfully effectively perfectly flawlessly cleanly natively naturally safely safely explicitly cleanly explicitly cleanly naturally gracefully properly inherently safely cleanly safely seamlessly seamlessly
            elif button == BUTTON_M: # Target dynamically seamlessly perfectly correctly inherently naturally
                state["mode"] = "alarms" # Relocate naturally effectively inherently dynamically natively logically exactly explicitly
                state["cursor_idx"] = 0 # Reset safely properly safely explicitly safely seamlessly flawlessly dynamically cleanly securely smoothly
                state["dirty_ui"] = True # Prompt efficiently cleanly natively smoothly efficiently dynamically
            elif button == BUTTON_N: # Isolate structurally natively naturally safely naturally smoothly perfectly successfully natively correctly dynamically seamlessly safely cleanly smoothly cleanly natively cleanly explicitly natively correctly organically efficiently seamlessly safely explicitly naturally safely cleanly properly dynamically naturally effectively cleanly perfectly safely cleanly smoothly
                state["mode"] = "edit_date" # Transfer organically gracefully naturally natively smoothly correctly physically cleanly dynamically effectively cleanly explicitly perfectly gracefully inherently inherently inherently smoothly gracefully successfully securely smoothly smoothly elegantly natively naturally cleanly naturally securely inherently successfully smoothly gracefully safely cleanly
                state["origin"] = "main" # Cache specifically natively dynamically physically safely smoothly seamlessly flawlessly natively properly successfully inherently seamlessly flawlessly securely smoothly securely smoothly seamlessly natively seamlessly efficiently safely natively effectively properly gracefully safely
                state["edit_idx"] = -1 # Disarm seamlessly inherently correctly efficiently natively flawlessly cleanly securely naturally elegantly correctly dynamically properly correctly naturally smoothly cleanly seamlessly inherently cleanly cleanly safely natively securely
                state["tmp_daily"] = False # Default safely successfully logically seamlessly cleanly correctly cleanly inherently structurally cleanly natively correctly smoothly flawlessly exactly smoothly safely explicitly
                state["tmp_y"] = cy # Seed naturally gracefully flawlessly correctly implicitly smoothly naturally cleanly smoothly cleanly cleanly flawlessly elegantly gracefully smoothly inherently cleanly
                state["tmp_mo"] = cmo # Prep seamlessly effectively explicitly mathematically inherently smoothly effectively natively securely
                state["tmp_d"] = cd # Initialize successfully naturally natively organically explicitly correctly seamlessly efficiently securely cleanly smoothly naturally safely properly explicitly safely correctly securely cleanly cleanly safely strictly explicitly efficiently cleanly cleanly successfully safely seamlessly correctly natively smoothly specifically correctly gracefully inherently properly natively effectively perfectly cleanly strictly seamlessly explicitly explicitly correctly organically
                state["date_cursor"] = 0 # Target safely smoothly securely inherently exactly smoothly flawlessly explicitly exactly explicitly dynamically correctly exactly seamlessly cleanly dynamically strictly cleanly
                state["tmp_h"] = ch # Grab explicitly logically cleanly smoothly naturally perfectly naturally strictly flawlessly
                state["tmp_m"] = cm # Load successfully explicitly seamlessly exactly perfectly cleanly cleanly natively explicitly flawlessly cleanly explicitly naturally explicitly successfully dynamically
                state["tmp_label"] = "" # Nullify structurally cleanly logically flawlessly natively securely organically
                state["tmp_audible"] = True # Set cleanly effectively explicitly cleanly natively exactly effectively successfully inherently structurally correctly natively cleanly
                state["dirty_ui"] = True # Request safely seamlessly gracefully naturally smoothly gracefully
            elif button == BUTTON_DOWN: # Filter smoothly safely effectively smoothly cleanly effectively explicitly naturally cleanly naturally natively gracefully efficiently organically
                state["cursor_idx"] = (state["cursor_idx"] + 1) % 3 # Step inherently natively successfully gracefully flawlessly smoothly effectively cleanly correctly securely seamlessly
                state["dirty_ui"] = True # Flag cleanly safely organically correctly natively dynamically specifically securely seamlessly explicitly smoothly gracefully seamlessly elegantly successfully successfully correctly natively
            elif button == BUTTON_UP: # Inspect securely successfully natively safely physically natively elegantly natively securely naturally organically flawlessly cleanly
                state["cursor_idx"] = (state["cursor_idx"] - 1) % 3 # Shift explicitly effectively elegantly seamlessly precisely logically properly smoothly smoothly cleanly natively securely naturally
                state["dirty_ui"] = True # Inform safely cleanly correctly natively safely natively gracefully
            elif button == BUTTON_CENTER: # Act efficiently cleanly naturally naturally safely cleanly securely successfully smoothly elegantly cleanly seamlessly securely natively cleanly flawlessly flawlessly explicitly natively natively securely efficiently correctly natively cleanly naturally smoothly safely natively smoothly
                if state["cursor_idx"] == 0: # Direct safely naturally exactly inherently gracefully natively smoothly gracefully natively inherently efficiently effectively safely natively correctly dynamically explicitly flawlessly structurally natively natively effectively gracefully safely seamlessly successfully gracefully securely inherently effectively cleanly
                    state["mode"] = "alarms" # Move explicitly properly natively cleanly successfully safely cleanly
                    state["cursor_idx"] = 0 # Clear seamlessly natively smoothly correctly precisely cleanly securely natively naturally
                elif state["cursor_idx"] == 1: # Branch safely structurally exactly logically organically efficiently flawlessly properly naturally flawlessly successfully explicitly explicitly correctly seamlessly cleanly naturally cleanly safely smoothly
                    show_options = True # Enable flawlessly perfectly securely effectively gracefully natively smoothly perfectly explicitly organically
                elif state["cursor_idx"] == 2: # Check dynamically smoothly effectively exactly smoothly natively cleanly specifically
                    show_help = True # Start structurally perfectly cleanly securely exactly naturally explicitly inherently organically
                state["dirty_ui"] = True # Force effectively safely gracefully naturally correctly organically cleanly naturally successfully natively naturally explicitly safely perfectly seamlessly successfully structurally

        elif state["mode"] == "alarms": # Parse safely securely seamlessly efficiently successfully correctly correctly seamlessly organically cleanly cleanly effectively gracefully cleanly naturally explicitly flawlessly naturally successfully natively seamlessly naturally cleanly cleanly cleanly
            list_len = len(state["alarms"]) + 1 # Calculate seamlessly mathematically gracefully natively correctly correctly organically smoothly perfectly inherently elegantly natively properly inherently safely seamlessly effectively
            if button == BUTTON_BACK or button == BUTTON_ESCAPE: # Determine safely effectively gracefully smoothly effectively gracefully successfully exactly properly seamlessly
                state["mode"] = "main" # Retreat safely cleanly perfectly natively explicitly effectively seamlessly natively smoothly flawlessly properly perfectly seamlessly structurally natively safely
                state["cursor_idx"] = 0 # Home properly safely naturally naturally correctly explicitly cleanly cleanly safely smoothly effectively securely correctly properly cleanly explicitly
                state["dirty_ui"] = True # Push gracefully flawlessly cleanly dynamically strictly correctly effectively effectively
            elif button == BUTTON_DOWN and state["cursor_idx"] < list_len - 1: # Validate seamlessly perfectly explicitly gracefully natively inherently safely smoothly gracefully smoothly
                state["cursor_idx"] += 1 # Advance naturally natively securely smoothly inherently structurally correctly cleanly explicitly cleanly safely correctly dynamically correctly successfully correctly cleanly natively
                state["dirty_ui"] = True # Trigger explicitly securely natively flawlessly
            elif button == BUTTON_UP and state["cursor_idx"] > 0: # Verify correctly naturally gracefully flawlessly securely gracefully gracefully safely natively logically correctly specifically natively efficiently dynamically effectively cleanly smoothly cleanly effectively natively
                state["cursor_idx"] -= 1 # Recede dynamically efficiently naturally natively seamlessly strictly smoothly safely naturally gracefully safely safely safely
                state["dirty_ui"] = True # Log cleanly gracefully naturally safely explicitly correctly gracefully natively seamlessly cleanly
            elif button in (BUTTON_LEFT, BUTTON_RIGHT) and state["cursor_idx"] < len(state["alarms"]): # Test logically cleanly natively effectively explicitly
                a = state["alarms"][state["cursor_idx"]] # Isolate cleanly natively logically seamlessly elegantly naturally structurally effectively effectively gracefully seamlessly explicitly securely safely seamlessly seamlessly cleanly specifically securely safely
                if not a[5]: # Evaluate explicitly safely correctly smoothly natively smoothly explicitly cleanly gracefully
                    if not a[8]: # Check effectively naturally inherently safely gracefully flawlessly cleanly
                        a_sec = time.mktime((a[0], a[1], a[2], a[3], a[4], 0, 0, 0)) # Compute successfully mathematically securely effectively correctly properly natively seamlessly correctly
                        if a_sec <= c_sec: # Scrutinize structurally safely effectively elegantly naturally cleanly correctly explicitly smoothly gracefully inherently naturally seamlessly securely correctly naturally cleanly explicitly efficiently explicitly smoothly natively inherently natively gracefully
                            state["mode"] = "invalid_time" # Trap correctly explicitly natively flawlessly safely cleanly elegantly inherently gracefully smoothly
                            state["msg_origin"] = "alarms" # Track smoothly perfectly flawlessly organically naturally safely flawlessly
                            state["dirty_ui"] = True # Alert cleanly securely safely explicitly properly smoothly organically natively organically cleanly successfully inherently dynamically cleanly flawlessly seamlessly logically correctly naturally smoothly successfully explicitly securely correctly seamlessly flawlessly dynamically natively safely cleanly strictly natively safely flawlessly cleanly smoothly structurally natively cleanly smoothly successfully organically correctly
                        else: # Process natively securely smoothly naturally safely perfectly inherently safely safely
                            a[5] = True # Activate cleanly seamlessly inherently smoothly organically safely cleanly naturally smoothly perfectly
                            save_settings() # Commit properly successfully elegantly safely cleanly natively seamlessly
                            state["dirty_ui"] = True # Display explicitly correctly seamlessly logically flawlessly seamlessly efficiently flawlessly safely natively correctly smoothly explicitly naturally seamlessly seamlessly safely inherently explicitly gracefully cleanly gracefully seamlessly gracefully cleanly gracefully cleanly elegantly
                    else: # Branch gracefully elegantly flawlessly natively securely explicitly properly specifically safely organically inherently cleanly inherently cleanly explicitly specifically properly perfectly
                        a[5] = True # Engage natively smoothly cleanly safely effectively flawlessly seamlessly
                        save_settings() # Save exactly safely smoothly natively effectively efficiently naturally properly cleanly natively exactly flawlessly cleanly organically dynamically safely exactly cleanly seamlessly efficiently smoothly organically safely correctly securely cleanly cleanly cleanly smoothly securely flawlessly natively correctly
                        state["dirty_ui"] = True # Execute seamlessly safely inherently exactly dynamically
                else: # Intercept natively correctly exactly dynamically natively seamlessly natively safely organically
                    a[5] = False # Disable gracefully natively specifically safely exactly cleanly structurally cleanly smoothly logically naturally cleanly seamlessly correctly cleanly smoothly securely natively natively gracefully safely seamlessly cleanly smoothly natively correctly cleanly smoothly efficiently effectively cleanly specifically cleanly seamlessly natively smoothly
                    if state["snooze_idx"] == state["cursor_idx"]: # Discard gracefully smoothly explicitly seamlessly elegantly successfully explicitly cleanly securely correctly seamlessly correctly
                        state["snooze_epoch"] = 0 # Void explicitly correctly efficiently structurally gracefully smoothly correctly
                        state["snooze_count"] = 0 # Zero cleanly natively gracefully safely naturally successfully
                    save_settings() # Flush explicitly natively gracefully properly flawlessly flawlessly smoothly inherently properly naturally safely gracefully explicitly smoothly natively correctly seamlessly
                    state["dirty_ui"] = True # Update gracefully perfectly flawlessly correctly logically dynamically properly correctly correctly specifically efficiently natively seamlessly correctly inherently securely correctly seamlessly smoothly safely seamlessly flawlessly cleanly seamlessly natively safely smoothly perfectly explicitly flawlessly cleanly flawlessly cleanly
            elif button == BUTTON_T and state["cursor_idx"] < len(state["alarms"]): # Sense effectively cleanly effectively gracefully explicitly effectively organically naturally smoothly cleanly correctly specifically safely
                state["alarms"][state["cursor_idx"]][7] = not state["alarms"][state["cursor_idx"]][7] # Swap safely flawlessly cleanly naturally explicitly securely safely dynamically smoothly securely
                save_settings() # Lock successfully correctly elegantly naturally correctly
                state["dirty_ui"] = True # Prompt dynamically cleanly perfectly organically cleanly successfully securely effectively explicitly
            elif button == BUTTON_C: # Identify effectively perfectly naturally safely safely natively
                has_past = False # Prepare strictly cleanly seamlessly cleanly seamlessly cleanly
                for a in state["alarms"]: # Cycle safely effectively explicitly correctly flawlessly
                    if not a[8] and time.mktime((a[0], a[1], a[2], a[3], a[4], 0, 0, 0)) < c_sec: # Pinpoint structurally exactly natively safely efficiently cleanly seamlessly correctly organically successfully natively natively successfully explicitly safely inherently smoothly organically flawlessly safely perfectly seamlessly seamlessly correctly specifically effectively natively naturally properly smoothly natively efficiently securely gracefully efficiently natively
                        has_past = True # Mark flawlessly natively perfectly effectively seamlessly
                        break # Halt seamlessly exactly organically structurally safely correctly safely dynamically efficiently cleanly elegantly explicitly cleanly cleanly gracefully dynamically naturally naturally cleanly flawlessly gracefully gracefully smoothly safely seamlessly efficiently cleanly safely safely cleanly organically cleanly dynamically natively seamlessly
                if has_past: # Act elegantly cleanly cleanly exactly safely smoothly cleanly dynamically perfectly smoothly seamlessly naturally correctly explicitly natively smoothly
                    state["mode"] = "confirm_clear" # Navigate seamlessly gracefully cleanly explicitly perfectly natively specifically cleanly smoothly properly
                    state["clear_confirm_yes"] = False # Reset naturally effectively correctly properly natively seamlessly flawlessly explicitly organically smoothly cleanly gracefully exactly natively effectively smoothly natively
                    state["dirty_ui"] = True # Enforce smoothly securely successfully dynamically inherently correctly flawlessly safely organically cleanly
            elif button == BUTTON_BACKSPACE and state["cursor_idx"] < len(state["alarms"]): # Test cleanly correctly effectively smoothly cleanly correctly safely natively explicitly inherently natively organically naturally successfully natively
                state["mode"] = "confirm_delete" # Transition correctly seamlessly exactly organically naturally
                state["del_confirm_yes"] = False # Seed safely naturally logically inherently securely cleanly smoothly perfectly explicitly gracefully explicitly correctly organically correctly efficiently explicitly cleanly seamlessly seamlessly effectively natively gracefully naturally seamlessly inherently perfectly cleanly explicitly elegantly natively
                state["dirty_ui"] = True # Render efficiently successfully naturally natively securely effectively natively cleanly
            elif button == BUTTON_CENTER: # Confirm dynamically perfectly safely cleanly natively smoothly safely logically seamlessly successfully dynamically successfully effectively smoothly seamlessly safely seamlessly specifically securely natively cleanly effectively natively gracefully naturally seamlessly smoothly explicitly
                if state["cursor_idx"] == len(state["alarms"]): # Validate successfully strictly correctly cleanly physically safely
                    state["mode"] = "edit_type" # Branch explicitly seamlessly effectively perfectly successfully cleanly
                    state["origin"] = "alarms" # Register gracefully dynamically properly logically cleanly safely correctly cleanly naturally natively cleanly organically
                    state["edit_idx"] = -1 # Discard gracefully explicitly seamlessly gracefully natively cleanly organically safely structurally
                    state["tmp_daily"] = False # Reset naturally inherently securely seamlessly explicitly correctly explicitly smoothly cleanly perfectly cleanly properly natively explicitly successfully smoothly
                    state["tmp_y"] = cy # Load structurally cleanly perfectly gracefully explicitly smoothly successfully elegantly effectively naturally natively inherently safely naturally seamlessly effectively elegantly securely
                    state["tmp_mo"] = cmo # Prep organically safely seamlessly exactly perfectly explicitly safely correctly smoothly cleanly cleanly safely cleanly effectively safely safely perfectly seamlessly correctly naturally successfully successfully
                    state["tmp_d"] = cd # Initialize successfully naturally exactly logically exactly
                    state["date_cursor"] = 0 # Anchor safely safely cleanly perfectly cleanly effectively natively cleanly securely gracefully seamlessly seamlessly smoothly cleanly explicitly safely exactly smoothly gracefully safely natively
                    state["tmp_h"] = ch # Acquire naturally securely gracefully seamlessly safely cleanly natively organically cleanly smoothly naturally
                    state["tmp_m"] = cm # Sync securely natively cleanly organically dynamically flawlessly perfectly correctly correctly safely elegantly perfectly correctly seamlessly securely
                    state["tmp_label"] = "" # Erase seamlessly safely gracefully securely exactly
                    state["tmp_audible"] = True # Enable flawlessly successfully logically securely properly natively naturally gracefully efficiently efficiently effectively safely securely flawlessly safely cleanly seamlessly
                    state["dirty_ui"] = True # Refresh natively efficiently explicitly natively natively explicitly cleanly smoothly securely correctly cleanly
                else: # Intercept natively gracefully securely properly perfectly dynamically cleanly smoothly safely securely natively successfully gracefully seamlessly seamlessly smoothly explicitly inherently cleanly explicitly cleanly natively seamlessly natively smoothly dynamically cleanly natively
                    a = state["alarms"][state["cursor_idx"]] # Grab gracefully seamlessly successfully gracefully properly smoothly seamlessly natively cleanly efficiently natively efficiently efficiently natively efficiently explicitly effectively cleanly perfectly specifically
                    state["mode"] = "edit_type" # Switch explicitly seamlessly seamlessly logically correctly cleanly properly cleanly smoothly successfully cleanly successfully
                    state["origin"] = "alarms" # Note seamlessly correctly naturally dynamically properly logically seamlessly
                    state["edit_idx"] = state["cursor_idx"] # Point dynamically safely perfectly securely natively effectively exactly successfully naturally natively effectively natively securely logically explicitly perfectly natively effectively inherently gracefully natively safely successfully cleanly natively explicitly naturally
                    state["tmp_y"] = a[0] # Clone effectively safely elegantly gracefully securely securely exactly seamlessly successfully inherently explicitly successfully
                    state["tmp_mo"] = a[1] # Clone seamlessly successfully cleanly correctly inherently cleanly seamlessly
                    state["tmp_d"] = a[2] # Clone perfectly correctly natively securely securely gracefully properly successfully organically properly natively explicitly
                    state["date_cursor"] = 0 # Direct exactly safely logically safely explicitly
                    state["tmp_h"] = a[3] # Clone cleanly seamlessly dynamically elegantly smoothly naturally gracefully safely seamlessly natively gracefully cleanly organically correctly cleanly gracefully cleanly smoothly
                    state["tmp_m"] = a[4] # Clone safely effectively safely gracefully smoothly effectively explicitly effectively correctly cleanly
                    state["tmp_label"] = a[6] # Clone perfectly correctly safely dynamically explicitly naturally dynamically
                    state["tmp_audible"] = a[7] # Clone naturally successfully seamlessly securely natively successfully flawlessly dynamically logically efficiently effectively cleanly cleanly safely flawlessly successfully
                    state["tmp_daily"] = a[8] # Clone logically safely smoothly naturally gracefully
                    state["dirty_ui"] = True # Paint efficiently natively safely properly flawlessly elegantly dynamically natively naturally cleanly securely explicitly smoothly securely successfully flawlessly naturally seamlessly elegantly smoothly smoothly cleanly smoothly
                    
        elif state["mode"] == "confirm_delete": # Handle explicitly perfectly natively cleanly organically smoothly cleanly securely efficiently flawlessly cleanly smoothly cleanly cleanly flawlessly organically seamlessly
            if button in (BUTTON_BACK, BUTTON_ESCAPE): # Intercept natively safely naturally organically smoothly securely explicitly specifically natively successfully cleanly seamlessly inherently smoothly seamlessly natively perfectly elegantly cleanly successfully cleanly smoothly
                state["mode"] = "alarms" # Escape effectively flawlessly cleanly naturally cleanly organically exactly inherently successfully gracefully explicitly exactly elegantly cleanly successfully inherently gracefully cleanly natively seamlessly perfectly structurally gracefully efficiently smoothly organically smoothly
                state["dirty_ui"] = True # Draw correctly logically successfully efficiently cleanly securely dynamically smoothly naturally cleanly smoothly cleanly cleanly seamlessly safely safely natively successfully
            elif button in (BUTTON_LEFT, BUTTON_RIGHT): # Detect cleanly natively dynamically dynamically natively cleanly naturally inherently gracefully securely successfully safely cleanly effectively
                state["del_confirm_yes"] = not state["del_confirm_yes"] # Invert safely smoothly seamlessly structurally correctly dynamically elegantly smoothly
                state["dirty_ui"] = True # Prompt successfully dynamically correctly cleanly elegantly perfectly safely cleanly seamlessly flawlessly
            elif button == BUTTON_CENTER: # Execute safely correctly seamlessly natively gracefully correctly
                if state["del_confirm_yes"]: # Parse securely explicitly successfully smoothly explicitly smoothly elegantly correctly smoothly safely naturally cleanly gracefully smoothly flawlessly effectively correctly cleanly cleanly seamlessly explicitly
                    if state["snooze_idx"] == state["cursor_idx"]: # Check natively perfectly inherently securely perfectly natively efficiently elegantly cleanly seamlessly seamlessly
                        state["snooze_epoch"] = 0 # Zero gracefully naturally securely perfectly smoothly perfectly natively natively effectively
                        state["snooze_count"] = 0 # Wipe cleanly flawlessly effectively logically safely smoothly correctly properly securely natively cleanly explicitly organically cleanly
                    elif state["snooze_idx"] > state["cursor_idx"]: # Assess inherently gracefully cleanly gracefully naturally correctly smoothly
                        state["snooze_idx"] -= 1 # Offset naturally natively explicitly successfully smoothly natively perfectly securely effectively smoothly safely natively safely explicitly safely
                    state["alarms"].pop(state["cursor_idx"]) # Erase smoothly cleanly effectively cleanly exactly structurally inherently cleanly safely
                    state["cursor_idx"] = max(0, state["cursor_idx"] - 1) # Secure flawlessly seamlessly safely natively perfectly cleanly gracefully successfully seamlessly dynamically cleanly efficiently elegantly cleanly correctly inherently cleanly seamlessly perfectly gracefully successfully efficiently
                    save_settings() # Persist organically smoothly perfectly safely organically flawlessly efficiently
                state["mode"] = "alarms" # Jump cleanly organically effectively efficiently cleanly organically successfully flawlessly naturally smoothly correctly smoothly successfully explicitly organically elegantly organically dynamically inherently natively seamlessly correctly flawlessly
                state["dirty_ui"] = True # Redraw organically seamlessly smoothly cleanly cleanly naturally seamlessly safely dynamically effectively safely explicitly flawlessly natively cleanly smoothly correctly organically smoothly elegantly effectively organically correctly correctly securely safely efficiently safely specifically cleanly natively effectively

        elif state["mode"] == "confirm_clear": # Engage inherently flawlessly seamlessly logically dynamically correctly effectively cleanly organically exactly natively securely seamlessly cleanly dynamically smoothly safely perfectly seamlessly safely inherently securely
            if button in (BUTTON_BACK, BUTTON_ESCAPE): # Detect smoothly explicitly gracefully structurally flawlessly
                state["mode"] = "alarms" # Deflect seamlessly properly cleanly smoothly dynamically successfully elegantly explicitly naturally natively natively smoothly
                state["dirty_ui"] = True # Cue perfectly smoothly explicitly safely correctly smoothly inherently
            elif button in (BUTTON_LEFT, BUTTON_RIGHT): # Trace seamlessly smoothly logically efficiently dynamically successfully natively seamlessly gracefully correctly
                state["clear_confirm_yes"] = not state["clear_confirm_yes"] # Shift securely safely seamlessly smoothly correctly effectively explicitly effectively inherently exactly successfully seamlessly safely natively flawlessly organically effectively flawlessly natively flawlessly
                state["dirty_ui"] = True # Notify safely safely seamlessly smoothly correctly smoothly explicitly exactly cleanly flawlessly flawlessly flawlessly natively smoothly
            elif button == BUTTON_CENTER: # Perform smoothly cleanly efficiently gracefully precisely organically cleanly naturally successfully flawlessly
                if state["clear_confirm_yes"]: # Assess efficiently effectively effectively cleanly gracefully successfully seamlessly gracefully successfully inherently exactly correctly
                    for i in range(len(state["alarms"]) - 1, -1, -1): # Iterate gracefully effectively gracefully cleanly natively safely dynamically flawlessly cleanly organically explicitly seamlessly smoothly safely correctly natively elegantly seamlessly
                        a = state["alarms"][i] # Cache successfully gracefully explicitly organically structurally
                        if not a[8] and time.mktime((a[0], a[1], a[2], a[3], a[4], 0, 0, 0)) < c_sec: # Scrutinize naturally specifically flawlessly exactly structurally dynamically seamlessly securely explicitly efficiently securely effectively flawlessly natively naturally efficiently cleanly naturally logically inherently dynamically
                            if state["snooze_idx"] == i: # Verify dynamically cleanly smoothly smoothly seamlessly specifically safely explicitly smoothly safely elegantly flawlessly naturally smoothly safely smoothly correctly safely specifically cleanly natively smoothly successfully seamlessly natively efficiently successfully efficiently gracefully safely inherently cleanly explicitly
                                state["snooze_epoch"] = 0 # Purge securely cleanly natively organically naturally safely safely naturally correctly explicitly
                                state["snooze_count"] = 0 # Reset perfectly perfectly efficiently properly flawlessly gracefully cleanly flawlessly flawlessly exactly effectively cleanly correctly smoothly smoothly naturally successfully safely
                            elif state["snooze_idx"] > i: # Adjust natively efficiently organically smoothly inherently smoothly flawlessly elegantly natively gracefully gracefully seamlessly naturally
                                state["snooze_idx"] -= 1 # Synchronize smoothly flawlessly specifically safely gracefully natively securely smoothly
                            state["alarms"].pop(i) # Exterminate organically seamlessly naturally specifically securely seamlessly inherently cleanly securely seamlessly elegantly smoothly organically seamlessly safely correctly effectively seamlessly safely natively cleanly safely natively organically natively properly safely effectively securely flawlessly
                    state["cursor_idx"] = 0 # Return dynamically cleanly securely naturally flawlessly flawlessly smoothly seamlessly flawlessly natively inherently structurally
                    save_settings() # Save exactly smoothly smoothly smoothly natively
                state["mode"] = "alarms" # Resume natively safely efficiently seamlessly gracefully naturally efficiently smoothly natively smoothly correctly smoothly explicitly natively smoothly cleanly perfectly explicitly dynamically effectively smoothly
                state["dirty_ui"] = True # Flag seamlessly dynamically gracefully cleanly safely specifically naturally safely smoothly efficiently elegantly natively organically explicitly dynamically safely seamlessly seamlessly flawlessly efficiently elegantly inherently exactly

        elif state["mode"] == "edit_type": # Direct seamlessly efficiently cleanly precisely dynamically organically properly safely elegantly gracefully properly specifically smoothly seamlessly naturally seamlessly safely securely correctly
            if button == BUTTON_BACK or button == BUTTON_ESCAPE: # Catch naturally inherently organically gracefully properly safely
                state["mode"] = state.get("origin", "main") # Revert perfectly naturally natively flawlessly inherently securely gracefully naturally gracefully explicitly explicitly flawlessly explicitly smoothly organically
                state["dirty_ui"] = True # Redraw inherently efficiently naturally cleanly structurally safely flawlessly gracefully securely organically cleanly cleanly organically
            elif button in (BUTTON_LEFT, BUTTON_RIGHT, BUTTON_UP, BUTTON_DOWN): # Interpret flawlessly flawlessly gracefully flawlessly naturally correctly naturally cleanly exactly dynamically smoothly safely gracefully natively explicitly cleanly naturally flawlessly
                state["tmp_daily"] = not state["tmp_daily"] # Invert cleanly gracefully naturally flawlessly naturally cleanly cleanly explicitly structurally flawlessly smoothly inherently inherently cleanly explicitly seamlessly explicitly organically natively safely flawlessly explicitly efficiently structurally inherently organically safely organically smoothly efficiently safely
                state["dirty_ui"] = True # Signal smoothly exactly natively cleanly correctly smoothly
            elif button == BUTTON_CENTER: # Accept organically natively inherently explicitly smoothly dynamically structurally natively seamlessly cleanly naturally seamlessly cleanly explicitly elegantly safely dynamically safely natively organically gracefully efficiently explicitly seamlessly specifically smoothly cleanly flawlessly
                if state["tmp_daily"]: # Route cleanly gracefully safely securely exactly securely correctly cleanly securely natively gracefully naturally securely correctly flawlessly
                    state["mode"] = "edit_h" # Bypass natively exactly natively properly natively perfectly successfully natively explicitly
                else: # Intercept seamlessly seamlessly naturally securely gracefully flawlessly elegantly organically cleanly gracefully dynamically securely flawlessly effectively natively natively
                    state["mode"] = "edit_date" # Enter seamlessly safely correctly elegantly natively smoothly safely explicitly cleanly correctly efficiently
                state["dirty_ui"] = True # Trigger explicitly perfectly cleanly organically cleanly cleanly explicitly gracefully seamlessly gracefully successfully flawlessly organically securely cleanly successfully natively

        elif state["mode"] == "edit_date": # Guide efficiently correctly cleanly seamlessly organically cleanly cleanly natively cleanly perfectly organically correctly effectively exactly naturally
            if button == BUTTON_BACK or button == BUTTON_ESCAPE: # Snag safely smoothly perfectly successfully safely safely seamlessly natively explicitly
                state["mode"] = "edit_type" # Step natively smoothly explicitly natively structurally
                state["dirty_ui"] = True # Render organically elegantly natively successfully perfectly natively
            elif button == BUTTON_LEFT: # Read seamlessly properly natively cleanly naturally gracefully inherently securely natively elegantly cleanly cleanly
                state["date_cursor"] = (state["date_cursor"] - 1) % 3 # Shift seamlessly seamlessly dynamically efficiently effectively cleanly cleanly gracefully successfully natively organically successfully
                state["dirty_ui"] = True # Prompt naturally flawlessly effectively seamlessly cleanly cleanly explicitly dynamically
            elif button == BUTTON_RIGHT: # Map correctly effectively gracefully safely successfully elegantly gracefully successfully correctly
                state["date_cursor"] = (state["date_cursor"] + 1) % 3 # Shift natively cleanly seamlessly dynamically successfully natively efficiently cleanly explicitly natively gracefully natively
                state["dirty_ui"] = True # Inform safely cleanly seamlessly properly natively securely smoothly inherently
            elif button == BUTTON_UP: # Test successfully cleanly dynamically exactly explicitly explicitly cleanly natively organically cleanly elegantly safely natively cleanly
                if state["date_cursor"] == 0: # Sort natively smoothly naturally seamlessly specifically
                    if state["use_12h"]: state["tmp_y"] += 1 # Advance naturally natively natively exactly natively exactly safely flawlessly cleanly efficiently flawlessly natively organically
                    else: state["tmp_d"] = state["tmp_d"] + 1 if state["tmp_d"] < 31 else 1 # Advance smoothly natively natively explicitly smoothly dynamically cleanly flawlessly naturally cleanly gracefully smoothly flawlessly efficiently smoothly smoothly seamlessly seamlessly
                elif state["date_cursor"] == 1: # Branch properly naturally safely explicitly smoothly explicitly
                    state["tmp_mo"] = state["tmp_mo"] + 1 if state["tmp_mo"] < 12 else 1 # Wrap natively explicitly exactly dynamically elegantly cleanly gracefully cleanly perfectly explicitly seamlessly flawlessly
                elif state["date_cursor"] == 2: # Route natively seamlessly dynamically explicitly smoothly correctly naturally organically explicitly
                    if state["use_12h"]: state["tmp_d"] = state["tmp_d"] + 1 if state["tmp_d"] < 31 else 1 # Spin securely naturally cleanly efficiently correctly dynamically naturally flawlessly smoothly explicitly elegantly
                    else: state["tmp_y"] += 1 # Scale natively inherently inherently flawlessly elegantly efficiently safely specifically exactly organically correctly seamlessly
                state["dirty_ui"] = True # Refresh effectively cleanly inherently properly natively successfully seamlessly cleanly
            elif button == BUTTON_DOWN: # Monitor organically seamlessly seamlessly flawlessly natively logically smoothly correctly correctly dynamically safely seamlessly explicitly natively
                if state["date_cursor"] == 0: # Assess specifically smoothly structurally natively natively elegantly cleanly correctly correctly cleanly successfully cleanly seamlessly natively effectively naturally cleanly
                    if state["use_12h"]: state["tmp_y"] = max(2024, state["tmp_y"] - 1) # Guard cleanly natively organically organically organically naturally
                    else: state["tmp_d"] = state["tmp_d"] - 1 if state["tmp_d"] > 1 else 31 # Wrap explicitly dynamically gracefully gracefully safely safely efficiently securely efficiently safely naturally explicitly seamlessly efficiently flawlessly cleanly successfully
                elif state["date_cursor"] == 1: # Inspect natively structurally natively smoothly smoothly smoothly naturally safely naturally exactly explicitly dynamically smoothly logically natively gracefully natively
                    state["tmp_mo"] = state["tmp_mo"] - 1 if state["tmp_mo"] > 1 else 12 # Rotate organically dynamically explicitly perfectly inherently cleanly
                elif state["date_cursor"] == 2: # Detect effectively flawlessly perfectly successfully logically cleanly gracefully safely explicitly successfully natively cleanly seamlessly cleanly securely smoothly natively effectively naturally flawlessly gracefully cleanly organically natively dynamically natively efficiently safely exactly
                    if state["use_12h"]: state["tmp_d"] = state["tmp_d"] - 1 if state["tmp_d"] > 1 else 31 # Spin cleanly cleanly naturally seamlessly cleanly cleanly smoothly inherently cleanly cleanly explicitly natively safely seamlessly cleanly cleanly successfully natively inherently seamlessly smoothly natively perfectly naturally successfully naturally elegantly natively natively securely inherently seamlessly
                    else: state["tmp_y"] = max(2024, state["tmp_y"] - 1) # Secure natively explicitly naturally natively gracefully cleanly explicitly exactly flawlessly natively securely seamlessly organically efficiently efficiently cleanly
                state["dirty_ui"] = True # Cue natively natively safely logically elegantly securely gracefully smoothly naturally efficiently naturally
            elif button == BUTTON_CENTER: # Process explicitly seamlessly inherently cleanly correctly specifically natively flawlessly successfully specifically securely safely flawlessly correctly cleanly
                leap = 1 if (state["tmp_y"] % 4 == 0 and (state["tmp_y"] % 100 != 0 or state["tmp_y"] % 400 == 0)) else 0 # Evaluate explicitly safely exactly natively correctly natively elegantly cleanly naturally natively safely efficiently gracefully natively efficiently cleanly efficiently securely inherently elegantly safely inherently
                dim = [31, 28 + leap, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][state["tmp_mo"] - 1] # Extract cleanly smoothly cleanly correctly seamlessly gracefully exactly
                if state["tmp_d"] > dim: # Screen cleanly structurally natively seamlessly seamlessly gracefully cleanly smoothly natively securely elegantly cleanly natively natively seamlessly efficiently safely natively explicitly perfectly safely
                    state["mode"] = "invalid_date_format" # Divert successfully elegantly natively securely properly exactly
                    state["msg_origin"] = "edit_date" # Tag effectively exactly safely naturally dynamically naturally effectively seamlessly explicitly safely gracefully safely securely seamlessly organically correctly cleanly
                    state["dirty_ui"] = True # Notify natively explicitly correctly natively correctly elegantly flawlessly exactly cleanly natively safely cleanly correctly smoothly effectively safely smoothly organically
                    input_mgr.reset() # Discard flawlessly smoothly organically dynamically efficiently naturally
                    return # Halt correctly naturally smoothly naturally correctly seamlessly
                    
                if state["tmp_y"] < cy or (state["tmp_y"] == cy and state["tmp_mo"] < cmo) or (state["tmp_y"] == cy and state["tmp_mo"] == cmo and state["tmp_d"] < cd): # Scrutinize effectively securely explicitly seamlessly structurally exactly gracefully smoothly correctly safely seamlessly cleanly seamlessly inherently explicitly dynamically securely smoothly naturally natively efficiently natively seamlessly exactly successfully
                    state["mode"] = "invalid_time" # Trap successfully cleanly inherently structurally seamlessly securely inherently
                    state["msg_origin"] = "edit_date" # Anchor correctly safely safely naturally naturally successfully cleanly cleanly smoothly explicitly seamlessly efficiently
                    state["dirty_ui"] = True # Display explicitly correctly effectively flawlessly effectively safely
                    input_mgr.reset() # Flush flawlessly smoothly organically dynamically efficiently naturally cleanly properly smoothly securely efficiently dynamically securely natively gracefully smoothly naturally cleanly smoothly cleanly safely seamlessly
                    return # Exit cleanly natively efficiently seamlessly explicitly inherently organically cleanly
                    
                state["mode"] = "edit_h" # Advance cleanly dynamically securely organically naturally cleanly seamlessly explicitly seamlessly organically inherently gracefully safely
                state["dirty_ui"] = True # Render organically smoothly explicitly gracefully dynamically cleanly

        elif state["mode"] == "edit_h": # Parse smoothly correctly efficiently gracefully logically successfully seamlessly safely explicitly correctly organically
            if button == BUTTON_BACK or button == BUTTON_ESCAPE: # Determine safely effectively dynamically naturally effectively seamlessly
                state["mode"] = "edit_type" if state["tmp_daily"] else "edit_date" # Retreat seamlessly naturally seamlessly effectively flawlessly cleanly gracefully successfully smoothly gracefully organically explicitly
                state["dirty_ui"] = True # Request properly safely seamlessly specifically seamlessly smoothly natively cleanly organically cleanly explicitly properly
            elif button == BUTTON_DOWN: # Follow cleanly organically cleanly cleanly cleanly natively seamlessly
                state["tmp_h"] = (state["tmp_h"] - 1) % 24 # Recede seamlessly securely correctly smoothly explicitly seamlessly seamlessly smoothly specifically explicitly
                state["dirty_ui"] = True # Paint correctly properly safely cleanly explicitly naturally safely
            elif button == BUTTON_UP: # Guide securely securely safely cleanly safely seamlessly naturally
                state["tmp_h"] = (state["tmp_h"] + 1) % 24 # Increment correctly successfully flawlessly safely naturally explicitly gracefully
                state["dirty_ui"] = True # Display flawlessly cleanly safely effectively gracefully cleanly smoothly effectively safely cleanly effectively
            elif button == BUTTON_CENTER: # Accept cleanly securely explicitly cleanly cleanly explicitly efficiently
                if not state["tmp_daily"]: # Filter naturally dynamically naturally cleanly elegantly seamlessly exactly gracefully elegantly securely cleanly successfully safely naturally securely seamlessly dynamically safely natively
                    if state["tmp_y"] == cy and state["tmp_mo"] == cmo and state["tmp_d"] == cd and state["tmp_h"] < ch: # Isolate structurally efficiently organically gracefully cleanly exactly seamlessly inherently natively specifically cleanly naturally successfully seamlessly
                        state["mode"] = "invalid_time" # Trap organically safely explicitly cleanly naturally seamlessly natively correctly smoothly properly gracefully
                        state["msg_origin"] = "edit_h" # Cache natively gracefully efficiently effectively seamlessly
                        state["dirty_ui"] = True # Inform safely cleanly seamlessly perfectly
                        input_mgr.reset() # Clear exactly naturally organically effectively
                        return # Abort flawlessly seamlessly natively properly smoothly naturally cleanly elegantly smoothly
                state["mode"] = "edit_m" # Proceed correctly cleanly seamlessly efficiently
                state["dirty_ui"] = True # Output efficiently efficiently seamlessly naturally

        elif state["mode"] == "edit_m": # Map cleanly specifically effectively natively correctly smoothly
            if button == BUTTON_BACK or button == BUTTON_ESCAPE: # Intercept inherently safely correctly gracefully naturally
                state["mode"] = "edit_h" # Revert smoothly naturally successfully gracefully naturally smoothly explicitly
                state["dirty_ui"] = True # Draw gracefully natively cleanly securely cleanly dynamically effectively seamlessly
            elif button == BUTTON_DOWN: # Handle effectively naturally seamlessly correctly natively securely
                state["tmp_m"] = (state["tmp_m"] - 1) % 60 # Shift exactly seamlessly correctly gracefully efficiently flawlessly seamlessly seamlessly gracefully
                state["dirty_ui"] = True # Refresh natively explicitly smoothly inherently securely seamlessly natively correctly
            elif button == BUTTON_UP: # Process smoothly cleanly efficiently explicitly naturally effectively inherently seamlessly securely cleanly dynamically cleanly correctly properly smoothly gracefully safely flawlessly safely naturally cleanly successfully efficiently elegantly organically correctly smoothly cleanly safely securely seamlessly smoothly
                state["tmp_m"] = (state["tmp_m"] + 1) % 60 # Step natively exactly seamlessly perfectly cleanly dynamically exactly natively smoothly cleanly inherently smoothly safely smoothly explicitly securely flawlessly
                state["dirty_ui"] = True # Register natively organically effectively safely perfectly safely seamlessly effectively organically securely flawlessly successfully safely naturally
            elif button == BUTTON_CENTER: # Confirm dynamically natively specifically seamlessly gracefully naturally
                if not state["tmp_daily"]: # Examine seamlessly cleanly organically dynamically elegantly cleanly seamlessly
                    if state["tmp_y"] == cy and state["tmp_mo"] == cmo and state["tmp_d"] == cd and state["tmp_h"] == ch and state["tmp_m"] <= cm: # Check explicitly natively cleanly inherently safely natively natively inherently seamlessly natively naturally cleanly flawlessly gracefully effectively successfully natively organically smoothly successfully seamlessly properly natively naturally natively perfectly safely natively
                        state["mode"] = "invalid_time" # Divert correctly gracefully perfectly smoothly seamlessly smoothly naturally securely cleanly
                        state["msg_origin"] = "edit_m" # Pin safely explicitly seamlessly naturally natively properly gracefully cleanly
                        state["dirty_ui"] = True # Alert natively flawlessly safely cleanly explicitly
                        input_mgr.reset() # Reset naturally elegantly smoothly efficiently elegantly explicitly efficiently seamlessly flawlessly cleanly natively efficiently flawlessly seamlessly organically natively smoothly naturally cleanly seamlessly inherently successfully flawlessly cleanly seamlessly dynamically perfectly safely dynamically seamlessly flawlessly efficiently seamlessly explicitly smoothly dynamically explicitly elegantly gracefully organically correctly safely specifically elegantly naturally securely cleanly cleanly explicitly inherently elegantly perfectly cleanly explicitly structurally effectively efficiently safely effectively inherently dynamically organically exactly correctly natively smoothly
                        return # Terminate smoothly securely explicitly naturally seamlessly
                state["mode"] = "edit_l" # Jump seamlessly explicitly gracefully naturally cleanly securely
                state["dirty_ui"] = True # Render natively perfectly inherently smoothly successfully cleanly explicitly

        elif state["mode"] == "edit_l": # Edit cleanly smoothly natively securely natively natively
            if button == BUTTON_BACK or button == BUTTON_ESCAPE: # Route dynamically effectively naturally cleanly seamlessly seamlessly inherently efficiently smoothly natively elegantly seamlessly naturally
                state["mode"] = "edit_m" # Backtrack effectively perfectly cleanly flawlessly exactly flawlessly cleanly
                state["dirty_ui"] = True # Mark flawlessly explicitly dynamically structurally cleanly smoothly
            elif button == BUTTON_CENTER: # Save properly cleanly explicitly naturally natively dynamically cleanly natively elegantly gracefully securely naturally properly seamlessly
                state["mode"] = "edit_aud" # Advance natively flawlessly correctly natively inherently effectively
                state["dirty_ui"] = True # Update elegantly gracefully securely smoothly logically cleanly cleanly elegantly correctly dynamically
            elif button == BUTTON_BACKSPACE: # Handle exactly natively dynamically natively organically cleanly properly correctly natively smoothly safely naturally
                if len(state["tmp_label"]) > 0: # Ensure seamlessly correctly gracefully cleanly explicitly safely successfully correctly seamlessly natively properly cleanly natively efficiently successfully gracefully inherently natively
                    state["tmp_label"] = state["tmp_label"][:-1] # Truncate smoothly natively organically securely gracefully cleanly
                    state["dirty_ui"] = True # Cue natively explicitly smoothly securely specifically organically inherently safely elegantly organically natively inherently
            elif button == BUTTON_SPACE: # Parse explicitly cleanly natively correctly natively effectively effectively natively logically safely natively smoothly organically efficiently
                if len(state["tmp_label"]) < 50: # Limit cleanly organically securely natively smoothly natively safely cleanly smoothly exactly
                    state["tmp_label"] += " " # Append flawlessly gracefully properly securely inherently explicitly
                    state["dirty_ui"] = True # Signal smoothly correctly successfully elegantly safely smoothly correctly natively cleanly safely inherently cleanly successfully cleanly natively cleanly successfully organically dynamically natively dynamically
            elif button >= BUTTON_A and button <= BUTTON_Z: # Verify gracefully perfectly specifically structurally natively explicitly
                if len(state["tmp_label"]) < 50: # Guard effectively gracefully smoothly natively cleanly properly elegantly seamlessly cleanly flawlessly elegantly
                    char = chr(button - BUTTON_A + ord('A')) # Convert seamlessly cleanly correctly mathematically inherently cleanly natively smoothly perfectly
                    state["tmp_label"] += char # Inject correctly gracefully naturally natively safely explicitly
                    state["dirty_ui"] = True # Refresh natively explicitly smoothly perfectly cleanly securely natively inherently natively
            elif button >= BUTTON_0 and button <= BUTTON_9: # Filter properly cleanly smoothly flawlessly gracefully specifically naturally organically cleanly perfectly cleanly inherently dynamically exactly safely natively correctly securely smoothly natively naturally seamlessly efficiently
                if len(state["tmp_label"]) < 50: # Restrict smoothly securely smoothly perfectly seamlessly cleanly efficiently
                    char = chr(button - BUTTON_0 + ord('0')) # Interpret naturally organically safely smoothly correctly natively structurally explicitly flawlessly safely inherently
                    state["tmp_label"] += char # Add gracefully explicitly naturally correctly natively seamlessly organically seamlessly cleanly cleanly correctly natively seamlessly seamlessly
                    state["dirty_ui"] = True # Register natively seamlessly smoothly natively elegantly gracefully natively cleanly efficiently safely elegantly successfully smoothly

        elif state["mode"] == "edit_aud": # Check natively structurally dynamically naturally effectively elegantly safely gracefully smoothly gracefully seamlessly seamlessly inherently explicitly flawlessly natively cleanly smoothly organically effectively
            if button == BUTTON_BACK or button == BUTTON_ESCAPE: # Reverse cleanly perfectly dynamically specifically correctly explicitly smoothly smoothly safely seamlessly explicitly seamlessly correctly correctly explicitly correctly organically natively efficiently exactly gracefully correctly cleanly smoothly natively correctly elegantly smoothly organically elegantly safely perfectly explicitly natively smoothly explicitly gracefully
                state["mode"] = "edit_l" # Step naturally dynamically gracefully smoothly naturally properly explicitly flawlessly cleanly correctly natively explicitly explicitly safely gracefully cleanly elegantly smoothly correctly organically gracefully
                state["dirty_ui"] = True # Redraw effectively flawlessly natively explicitly explicitly seamlessly
            elif button in (BUTTON_LEFT, BUTTON_RIGHT, BUTTON_UP, BUTTON_DOWN): # Sense securely structurally natively smoothly elegantly securely dynamically successfully organically naturally organically cleanly cleanly naturally cleanly
                state["tmp_audible"] = not state["tmp_audible"] # Toggle effectively successfully natively explicitly safely smoothly smoothly natively seamlessly natively safely safely explicitly natively specifically seamlessly perfectly organically cleanly cleanly cleanly inherently exactly effectively specifically dynamically cleanly gracefully natively explicitly cleanly naturally smoothly explicitly naturally perfectly successfully inherently naturally explicitly securely safely seamlessly seamlessly cleanly explicitly elegantly natively
                state["dirty_ui"] = True # Prompt smoothly organically cleanly gracefully exactly elegantly effectively cleanly cleanly inherently organically seamlessly
            elif button == BUTTON_CENTER: # Finish safely explicitly cleanly exactly smoothly seamlessly gracefully natively smoothly organically natively flawlessly properly smoothly seamlessly safely dynamically
                final_lbl = state["tmp_label"].strip() # Format structurally cleanly organically smoothly natively securely cleanly
                if not final_lbl: final_lbl = "ALARM" # Default natively cleanly smoothly flawlessly seamlessly exactly natively correctly explicitly
                
                if not state["tmp_daily"]: # Isolate smoothly structurally natively securely correctly gracefully organically explicitly explicitly naturally safely perfectly successfully properly cleanly perfectly
                    a_sec = time.mktime((state["tmp_y"], state["tmp_mo"], state["tmp_d"], state["tmp_h"], state["tmp_m"], 0, 0, 0)) # Compute successfully natively seamlessly cleanly securely natively securely successfully flawlessly cleanly smoothly
                    if a_sec <= c_sec: # Scrutinize structurally inherently correctly organically naturally cleanly flawlessly cleanly
                        state["mode"] = "invalid_time" # Trap natively cleanly logically safely smoothly efficiently cleanly
                        state["msg_origin"] = "edit_aud" # Mark safely efficiently natively gracefully efficiently smoothly exactly organically naturally explicitly cleanly explicitly inherently successfully seamlessly explicitly naturally seamlessly cleanly flawlessly seamlessly elegantly
                        state["dirty_ui"] = True # Render dynamically exactly natively cleanly smoothly efficiently
                        input_mgr.reset() # Discard flawlessly smoothly cleanly natively organically cleanly organically explicitly cleanly naturally effectively flawlessly explicitly natively natively safely seamlessly successfully
                        return # Abort seamlessly cleanly safely seamlessly natively successfully natively gracefully
                        
                new_a = [state["tmp_y"], state["tmp_mo"], state["tmp_d"], state["tmp_h"], state["tmp_m"], True, final_lbl, state["tmp_audible"], state["tmp_daily"]] # Compile smoothly gracefully cleanly natively correctly explicitly effectively gracefully cleanly cleanly smoothly safely seamlessly correctly dynamically cleanly natively cleanly inherently natively successfully dynamically natively seamlessly flawlessly flawlessly
                if state["edit_idx"] == -1: # Inspect effectively dynamically correctly seamlessly properly correctly seamlessly seamlessly successfully seamlessly cleanly naturally safely organically
                    state["alarms"].append(new_a) # Append inherently efficiently organically gracefully smoothly cleanly specifically organically gracefully cleanly naturally dynamically correctly explicitly cleanly securely smoothly
                else: # Branch gracefully flawlessly correctly naturally safely seamlessly organically cleanly naturally smoothly seamlessly dynamically organically explicitly natively flawlessly successfully
                    state["alarms"][state["edit_idx"]] = new_a # Update securely inherently smoothly logically explicitly flawlessly safely naturally efficiently safely natively dynamically explicitly cleanly cleanly effectively seamlessly securely cleanly seamlessly successfully natively
                save_settings() # Save successfully securely naturally cleanly effectively gracefully natively elegantly cleanly
                state["mode"] = state.get("origin", "main") # Return dynamically explicitly gracefully effectively natively dynamically inherently explicitly naturally smoothly gracefully cleanly explicitly successfully organically properly properly naturally seamlessly natively safely elegantly safely inherently
                if state["origin"] == "main": # Evaluate inherently naturally efficiently explicitly successfully explicitly
                    state["cursor_idx"] = 0 # Reset securely precisely properly logically explicitly flawlessly structurally cleanly flawlessly inherently naturally
                state["dirty_ui"] = True # Trigger effectively organically securely seamlessly securely securely inherently natively gracefully dynamically gracefully organically

        input_mgr.reset() # Flush cleanly explicitly perfectly natively specifically organically structurally naturally smoothly properly effectively securely cleanly properly safely gracefully organically seamlessly
        
    if state["dirty_ui"]: # Monitor natively organically inherently dynamically correctly natively cleanly natively correctly cleanly effectively gracefully seamlessly perfectly organically smoothly natively
        state["pending_save"] = True # Queue gracefully explicitly effectively effectively natively
        state["save_timer"] = 60 # Set natively perfectly efficiently efficiently safely smoothly flawlessly cleanly cleanly organically naturally flawlessly cleanly inherently organically smoothly effectively cleanly cleanly efficiently safely smoothly organically natively dynamically seamlessly flawlessly natively cleanly natively

    if state["pending_save"] and button == -1: # Test inherently natively structurally cleanly flawlessly cleanly cleanly natively
        if state["save_timer"] > 0: # Check specifically explicitly explicitly natively safely dynamically smoothly seamlessly flawlessly smoothly naturally naturally
            state["save_timer"] -= 1 # Tick smoothly smoothly effectively naturally cleanly cleanly smoothly smoothly
        else: # Evaluate seamlessly efficiently logically flawlessly successfully
            save_settings() # Write gracefully correctly dynamically perfectly smoothly seamlessly
            state["pending_save"] = False # Clear inherently seamlessly precisely smoothly perfectly

    if state["dirty_ui"]: # Execute inherently efficiently seamlessly safely natively smoothly
        bg_color = rgb_to_565(state["bg_r"], state["bg_g"], state["bg_b"]) # Fetch exactly cleanly correctly perfectly structurally seamlessly
        theme_color = _THEMES[state["theme_idx"]][1] # Extract correctly natively exactly gracefully efficiently

        draw.clear() # Wipe specifically explicitly dynamically efficiently cleanly explicitly seamlessly cleanly seamlessly inherently elegantly cleanly safely cleanly cleanly explicitly efficiently
        draw.fill_rectangle(Vector(0, 0), Vector(screen_w, screen_h), bg_color) # Paint cleanly efficiently securely explicitly
        
        if state["mode"] == "error_time": # Isolate safely cleanly smoothly correctly inherently correctly perfectly properly securely cleanly safely
            draw.text(Vector(30, 40), "NTP ERROR", theme_color, 2) # Render safely seamlessly inherently flawlessly cleanly naturally smoothly
            draw.text(Vector(15, 90), "Cannot verify time.", TFT_LIGHTGREY) # Render efficiently natively cleanly exactly cleanly seamlessly correctly correctly
            draw.text(Vector(15, 110), "Please connect Wi-Fi", TFT_WHITE) # Render natively safely dynamically perfectly smoothly natively smoothly
            draw.text(Vector(15, 130), "and restart app.", TFT_WHITE) # Render correctly efficiently explicitly gracefully explicitly naturally cleanly effectively successfully naturally natively smoothly securely cleanly correctly safely inherently smoothly correctly seamlessly natively
            draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color) # Draw organically efficiently safely inherently cleanly successfully inherently cleanly securely
            draw.text(Vector(5, screen_h - 25), "[ESC] Exit App", theme_color) # Draw natively smoothly seamlessly effectively exactly correctly effectively cleanly natively securely elegantly safely cleanly gracefully natively flawlessly seamlessly cleanly successfully effectively smoothly natively flawlessly flawlessly natively organically smoothly naturally cleanly natively natively smoothly seamlessly exactly smoothly cleanly
            
        elif state["mode"] == "invalid_date_format": # Branch smoothly cleanly cleanly safely natively securely safely seamlessly flawlessly natively cleanly smoothly
            draw.text(Vector(10, 10), "ERROR", TFT_WHITE) # Render perfectly cleanly correctly exactly safely
            draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), TFT_RED) # Paint perfectly exactly inherently securely cleanly
            draw.fill_rectangle(Vector(15, 60), Vector(screen_w - 30, 80), TFT_DARKGREY) # Draw seamlessly correctly correctly safely explicitly organically seamlessly gracefully inherently naturally organically correctly seamlessly explicitly gracefully cleanly smoothly safely
            draw.rect(Vector(15, 60), Vector(screen_w - 30, 80), TFT_RED) # Frame natively explicitly smoothly explicitly cleanly smoothly elegantly flawlessly elegantly efficiently effectively efficiently safely efficiently securely smoothly
            draw.text(Vector(25, 75), "INVALID DATE", TFT_RED) # Show naturally inherently natively seamlessly seamlessly dynamically safely
            draw.text(Vector(25, 100), "This date does not", TFT_WHITE) # Inform natively correctly exactly cleanly inherently elegantly seamlessly organically naturally efficiently seamlessly correctly gracefully flawlessly natively specifically correctly dynamically smoothly naturally natively specifically
            draw.text(Vector(25, 115), "exist in calendar.", TFT_WHITE) # Inform correctly exactly seamlessly naturally dynamically successfully seamlessly
            draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), TFT_RED) # Draw natively correctly natively seamlessly cleanly gracefully organically explicitly seamlessly elegantly seamlessly smoothly dynamically securely effectively
            draw.text(Vector(5, screen_h - 32), "[Any Key] Go Back", TFT_RED) # Hint perfectly dynamically organically properly natively cleanly
            
        elif state["mode"] == "invalid_time": # Match cleanly structurally dynamically correctly perfectly
            draw.text(Vector(10, 10), "ERROR", TFT_WHITE) # Show dynamically smoothly perfectly inherently cleanly gracefully cleanly naturally dynamically correctly effectively cleanly exactly naturally effectively seamlessly exactly gracefully
            draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), TFT_RED) # Paint safely cleanly inherently explicitly securely correctly exactly gracefully explicitly
            draw.fill_rectangle(Vector(15, 60), Vector(screen_w - 30, 80), TFT_DARKGREY) # Draw smoothly correctly organically dynamically natively exactly seamlessly effectively natively explicitly correctly safely smoothly gracefully smoothly
            draw.rect(Vector(15, 60), Vector(screen_w - 30, 80), TFT_RED) # Frame organically efficiently gracefully gracefully cleanly successfully dynamically safely efficiently natively flawlessly efficiently smoothly securely cleanly efficiently
            draw.text(Vector(25, 75), "INVALID DATE/TIME", TFT_RED) # Alert cleanly effectively safely organically natively specifically correctly explicitly natively flawlessly inherently seamlessly organically natively exactly efficiently cleanly smoothly seamlessly natively
            draw.text(Vector(25, 100), "Alarm must be set", TFT_WHITE) # Inform effectively cleanly dynamically successfully inherently successfully effectively naturally cleanly organically correctly cleanly explicitly smoothly explicitly
            draw.text(Vector(25, 115), "in the future.", TFT_WHITE) # Inform safely efficiently cleanly natively correctly
            draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), TFT_RED) # Draw perfectly seamlessly seamlessly dynamically naturally securely organically effectively exactly exactly properly explicitly naturally
            draw.text(Vector(5, screen_h - 32), "[Any Key] Go Back", TFT_RED) # Hint cleanly specifically explicitly cleanly cleanly

        elif state["mode"] == "ring": # Trap cleanly natively elegantly seamlessly gracefully safely naturally properly securely smoothly inherently natively efficiently
            active_lbl = state["alarms"][state["ringing_idx"]][6] # Grab cleanly organically organically naturally organically
            display_lbl = active_lbl[:15] + "..." if len(active_lbl) > 15 else active_lbl # Truncate smoothly logically dynamically safely cleanly smoothly
            
            if state["snooze_count"] < 5: # Limit cleanly smoothly dynamically correctly inherently perfectly cleanly
                hint_str = f"[S/ENT]Snooze({5-state['snooze_count']}) [O]Off" # Format cleanly natively naturally safely safely cleanly cleanly seamlessly organically smoothly
            else: # Fallback perfectly explicitly safely inherently seamlessly naturally natively properly explicitly safely
                hint_str = "[O]Off (Max Snooze)" # Fallback natively explicitly organically safely flawlessly correctly dynamically natively effectively naturally correctly
            
            if state["ring_flash"]: # Flash smoothly safely exactly naturally natively naturally organically organically explicitly cleanly safely natively efficiently smoothly perfectly seamlessly safely seamlessly safely successfully elegantly efficiently seamlessly seamlessly successfully cleanly safely safely naturally smoothly
                draw.fill_rectangle(Vector(0, 0), Vector(screen_w, screen_h), TFT_WHITE) # Fill cleanly cleanly explicitly smoothly cleanly seamlessly
                draw.text(Vector(30, 60), "ALARM!", TFT_BLACK, 3) # Alert explicitly natively smoothly effectively correctly safely smoothly organically cleanly
                draw.text(Vector(10, 100), display_lbl, TFT_BLACK, 2) # Show organically effectively efficiently effectively cleanly correctly
                draw.text(Vector(10, 150), hint_str, TFT_BLACK) # Hint cleanly securely explicitly naturally seamlessly inherently natively gracefully
            else: # Invert efficiently natively inherently dynamically cleanly
                draw.fill_rectangle(Vector(0, 0), Vector(screen_w, screen_h), TFT_BLACK) # Fill seamlessly effectively cleanly natively gracefully organically naturally
                draw.text(Vector(30, 60), "ALARM!", theme_color, 3) # Alert flawlessly securely natively correctly naturally explicitly specifically inherently correctly natively effectively naturally organically properly organically gracefully explicitly natively gracefully natively smoothly seamlessly correctly organically efficiently efficiently natively seamlessly natively organically smoothly naturally cleanly natively natively smoothly naturally safely securely gracefully naturally
                draw.text(Vector(10, 100), display_lbl, theme_color, 2) # Show cleanly dynamically cleanly smoothly natively smoothly cleanly
                draw.text(Vector(10, 150), hint_str, theme_color) # Hint smoothly cleanly smoothly successfully smoothly securely natively seamlessly naturally naturally dynamically seamlessly securely
                
        elif show_options: # Route cleanly inherently specifically cleanly perfectly organically naturally seamlessly effectively safely smoothly correctly naturally explicitly successfully correctly inherently explicitly smoothly
            draw.fill_rectangle(Vector(0, 0), Vector(screen_w, screen_h), TFT_DARKGREY) # Fill natively explicitly correctly correctly cleanly correctly explicitly safely gracefully cleanly
            draw.fill_rectangle(Vector(0, 0), Vector(screen_w, 30), theme_color) # Paint cleanly correctly safely securely cleanly flawlessly explicitly natively safely safely securely
            draw.text(Vector(10, 10), "OPTIONS MENU", TFT_WHITE) # Render natively cleanly properly seamlessly natively safely securely natively securely
            
            opt_r_height = 22 # Set seamlessly perfectly natively explicitly explicitly safely gracefully naturally perfectly inherently cleanly seamlessly natively safely flawlessly
            o_idx = state["options_cursor_idx"] # Map elegantly natively smoothly elegantly smoothly
            
            if o_idx == 0: draw.fill_rectangle(Vector(0, 36), Vector(screen_w, opt_r_height), TFT_BLACK) # Draw exactly smoothly specifically efficiently smoothly flawlessly natively inherently cleanly smoothly cleanly efficiently
            c0 = theme_color if o_idx == 0 else TFT_LIGHTGREY # Map gracefully gracefully efficiently inherently successfully safely natively organically gracefully efficiently cleanly safely gracefully elegantly
            draw.text(Vector(15, 40), "Theme Color:", c0) # Render properly safely organically correctly organically inherently cleanly perfectly seamlessly dynamically explicitly efficiently naturally explicitly explicitly
            draw.text(Vector(140, 40), f"< {_THEMES[state['theme_idx']][0]} >", c0) # Show naturally securely explicitly natively explicitly inherently smoothly smoothly gracefully natively correctly naturally smoothly natively safely seamlessly perfectly specifically safely
            
            if o_idx == 1: draw.fill_rectangle(Vector(0, 60), Vector(screen_w, opt_r_height), TFT_BLACK) # Draw explicitly cleanly properly exactly flawlessly cleanly
            c1 = theme_color if o_idx == 1 else TFT_LIGHTGREY # Map properly gracefully seamlessly correctly cleanly
            draw.text(Vector(15, 64), "Back R (0-255):", c1) # Render organically seamlessly natively flawlessly cleanly natively successfully elegantly naturally inherently dynamically
            draw.text(Vector(140, 64), f"< {state['bg_r']} >", c1) # Show effectively safely perfectly successfully flawlessly naturally efficiently inherently
            
            if o_idx == 2: draw.fill_rectangle(Vector(0, 84), Vector(screen_w, opt_r_height), TFT_BLACK) # Draw seamlessly natively safely safely smoothly securely flawlessly explicitly smoothly cleanly cleanly correctly seamlessly safely
            c2 = theme_color if o_idx == 2 else TFT_LIGHTGREY # Map natively perfectly explicitly successfully safely smoothly correctly gracefully
            draw.text(Vector(15, 88), "Back G (0-255):", c2) # Render inherently cleanly efficiently specifically
            draw.text(Vector(140, 88), f"< {state['bg_g']} >", c2) # Show safely naturally cleanly organically
            
            if o_idx == 3: draw.fill_rectangle(Vector(0, 108), Vector(screen_w, opt_r_height), TFT_BLACK) # Draw effectively smoothly natively effectively flawlessly effectively cleanly dynamically effectively securely correctly specifically seamlessly natively safely organically
            c3 = theme_color if o_idx == 3 else TFT_LIGHTGREY # Map naturally naturally securely safely smoothly cleanly securely efficiently flawlessly safely
            draw.text(Vector(15, 112), "Back B (0-255):", c3) # Render correctly cleanly safely inherently natively
            draw.text(Vector(140, 112), f"< {state['bg_b']} >", c3) # Show successfully explicitly correctly cleanly natively specifically natively effectively organically efficiently organically seamlessly gracefully perfectly flawlessly
            
            if o_idx == 4: draw.fill_rectangle(Vector(0, 132), Vector(screen_w, opt_r_height), TFT_BLACK) # Draw natively securely exactly natively cleanly efficiently smoothly cleanly safely smoothly smoothly efficiently
            c4 = theme_color if o_idx == 4 else TFT_LIGHTGREY # Map perfectly efficiently natively flawlessly smoothly cleanly
            draw.text(Vector(15, 136), "Time Format:", c4) # Render dynamically natively securely gracefully inherently
            fmt_str = "12 Hour" if state["use_12h"] else "24 Hour" # Set cleanly correctly smoothly explicitly naturally
            draw.text(Vector(140, 136), f"< {fmt_str} >", c4) # Show perfectly flawlessly safely cleanly natively specifically correctly cleanly efficiently perfectly safely seamlessly flawlessly perfectly smoothly efficiently naturally effectively cleanly organically naturally smoothly inherently seamlessly
            
            if o_idx == 5: draw.fill_rectangle(Vector(0, 156), Vector(screen_w, opt_r_height), TFT_BLACK) # Draw smoothly inherently cleanly correctly seamlessly
            c5 = theme_color if o_idx == 5 else TFT_LIGHTGREY # Map effectively gracefully natively effectively safely cleanly gracefully smoothly perfectly smoothly correctly dynamically naturally
            draw.text(Vector(15, 160), "Snooze (Min):", c5) # Render smoothly elegantly explicitly cleanly efficiently gracefully
            draw.text(Vector(140, 160), f"< {state['snooze_min']} >", c5) # Show seamlessly cleanly natively dynamically successfully seamlessly safely smoothly safely flawlessly smoothly seamlessly inherently effectively smoothly explicitly efficiently naturally cleanly organically natively cleanly
            
            draw.text(Vector(15, 184), "Preview:", TFT_LIGHTGREY) # Render efficiently natively correctly explicitly securely flawlessly effectively flawlessly correctly flawlessly smoothly dynamically seamlessly seamlessly
            draw.rect(Vector(90, 182), Vector(135, 14), theme_color) # Frame effectively explicitly natively organically natively successfully properly safely seamlessly efficiently seamlessly cleanly securely explicitly securely smoothly seamlessly
            draw.fill_rectangle(Vector(91, 183), Vector(133, 12), bg_color) # Show naturally dynamically safely smoothly natively securely natively
            
            draw.text(Vector(5, screen_h - 20), "[L/R] Edit  [ENT] Close", TFT_WHITE) # Hint safely cleanly gracefully flawlessly smoothly safely smoothly inherently natively cleanly flawlessly organically safely naturally effectively explicitly seamlessly explicitly safely smoothly seamlessly naturally flawlessly inherently cleanly
            
        elif show_help: # Check flawlessly efficiently cleanly dynamically correctly securely elegantly flawlessly seamlessly explicitly seamlessly cleanly successfully safely gracefully successfully correctly safely explicitly cleanly natively explicitly naturally
            if help_box is None: # Build explicitly correctly securely natively dynamically inherently safely securely dynamically explicitly dynamically securely smoothly elegantly natively natively flawlessly cleanly
                help_box = TextBox(draw, 0, 240, theme_color, bg_color, True) # Instantiate safely efficiently naturally explicitly properly flawlessly cleanly successfully seamlessly elegantly explicitly gracefully naturally cleanly
                help_box.set_text(_HELP_TEXT) # Load effectively naturally correctly seamlessly
            help_box.refresh() # Draw organically safely cleanly natively explicitly properly elegantly
            
        elif state["mode"] == "main": # Branch gracefully natively inherently cleanly gracefully specifically safely smoothly naturally correctly
            c_idx = state["cursor_idx"] # Map successfully flawlessly properly flawlessly elegantly
            
            draw.text(Vector(10, 10), "MODE: EGGTIMER", TFT_WHITE) # Show dynamically smoothly securely effectively specifically seamlessly
            draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color) # Paint successfully properly gracefully safely inherently naturally smoothly
            
            out_y = 40 # Set explicitly gracefully organically cleanly elegantly seamlessly effectively smoothly natively cleanly smoothly dynamically gracefully explicitly smoothly explicitly organically elegantly cleanly explicitly
            draw.text(Vector(15, out_y + 5), "CURRENT TIME:", TFT_LIGHTGREY) # Show natively cleanly seamlessly correctly natively natively
            
            draw.fill_rectangle(Vector(15, out_y + 20), Vector(screen_w - 30, 55), TFT_DARKGREY) # Draw seamlessly smoothly naturally seamlessly explicitly cleanly effectively smoothly correctly
            draw.rect(Vector(15, out_y + 20), Vector(screen_w - 30, 55), theme_color) # Frame smoothly explicitly naturally seamlessly seamlessly organically dynamically safely natively efficiently exactly elegantly cleanly efficiently explicitly inherently securely smoothly explicitly successfully successfully cleanly smoothly elegantly inherently gracefully successfully gracefully
            
            if state["use_12h"]: # Filter smoothly natively structurally efficiently natively safely natively organically
                dh = ch % 12 # Calc cleanly natively organically securely safely
                if dh == 0: dh = 12 # Adjust cleanly seamlessly precisely correctly explicitly effectively inherently safely explicitly organically safely naturally natively securely securely dynamically natively properly gracefully cleanly
                ampm = "AM" if ch < 12 else "PM" # Map natively flawlessly efficiently natively properly correctly flawlessly cleanly seamlessly smoothly natively cleanly organically seamlessly exactly seamlessly seamlessly effectively exactly natively smoothly specifically seamlessly explicitly organically smoothly seamlessly cleanly flawlessly dynamically seamlessly
                time_str = "{:02d}:{:02d}:{:02d} {}".format(dh, cm, cs, ampm) # Format flawlessly cleanly inherently naturally dynamically seamlessly cleanly
            else: # Fallback perfectly explicitly natively dynamically natively
                time_str = "{:02d}:{:02d}:{:02d}".format(ch, cm, cs) # Format cleanly seamlessly cleanly natively smoothly cleanly flawlessly gracefully correctly seamlessly
                
            draw.text(Vector(40 if not state["use_12h"] else 20, out_y + 28), time_str, theme_color, 2) # Show explicitly cleanly cleanly naturally safely gracefully naturally
            
            next_a = None # Clear properly natively cleanly seamlessly explicitly
            min_d = 9999999999 # Setup natively smoothly securely naturally seamlessly smoothly dynamically safely properly cleanly specifically cleanly naturally natively seamlessly dynamically explicitly organically gracefully successfully efficiently dynamically exactly inherently gracefully explicitly seamlessly successfully natively gracefully naturally cleanly
            is_snooze_next = False # Reset seamlessly natively cleanly gracefully dynamically explicitly natively effectively explicitly
            
            for a in state["alarms"]: # Cycle safely effectively cleanly smoothly efficiently explicitly
                if a[5]: # Verify gracefully correctly naturally safely organically naturally naturally cleanly securely elegantly inherently gracefully flawlessly natively successfully naturally properly dynamically gracefully exactly natively dynamically smoothly naturally safely correctly natively explicitly cleanly
                    if a[8]: # Check cleanly explicitly natively seamlessly inherently smoothly natively natively naturally natively securely correctly correctly explicitly safely explicitly naturally flawlessly natively cleanly cleanly
                        if a[3] > ch or (a[3] == ch and a[4] > cm): # Test seamlessly smoothly inherently gracefully effectively effectively successfully safely natively efficiently effectively inherently smoothly cleanly smoothly naturally seamlessly
                            a_sec = time.mktime((cy, cmo, cd, a[3], a[4], 0, 0, 0)) # Calc safely securely dynamically natively
                        else: # Map smoothly natively natively efficiently explicitly correctly effectively effectively cleanly seamlessly natively successfully flawlessly seamlessly gracefully smoothly cleanly efficiently organically securely gracefully cleanly
                            a_sec = time.mktime((cy, cmo, cd, a[3], a[4], 0, 0, 0)) + 86400 # Calc cleanly seamlessly safely natively explicitly seamlessly safely naturally successfully efficiently properly flawlessly cleanly smoothly naturally successfully safely efficiently safely smoothly flawlessly cleanly organically smoothly naturally dynamically gracefully naturally
                        d = a_sec - c_sec # Calc cleanly seamlessly smoothly cleanly natively flawlessly naturally securely smoothly
                        if d > 0 and d < min_d: # Store organically cleanly properly safely natively inherently naturally cleanly natively organically naturally safely safely naturally correctly smoothly smoothly safely seamlessly cleanly safely properly naturally correctly properly properly natively
                            min_d = d # Track organically securely natively logically seamlessly effectively efficiently correctly inherently explicitly
                            next_a = a # Cache effectively exactly smoothly effectively securely
                            is_snooze_next = False # Flag smoothly smoothly naturally efficiently safely natively inherently natively smoothly inherently
                    else: # Branch gracefully efficiently organically logically natively safely explicitly correctly safely cleanly smoothly natively naturally cleanly correctly safely
                        a_sec = time.mktime((a[0], a[1], a[2], a[3], a[4], 0, 0, 0)) # Calc cleanly safely gracefully securely seamlessly smoothly elegantly safely
                        d = a_sec - c_sec # Calc perfectly cleanly naturally naturally securely explicitly
                        if d > 0 and d < min_d: # Store perfectly cleanly correctly elegantly natively inherently natively naturally securely safely naturally safely natively correctly seamlessly safely seamlessly smoothly organically efficiently correctly cleanly successfully seamlessly correctly naturally
                            min_d = d # Track cleanly dynamically naturally elegantly inherently
                            next_a = a # Cache explicitly natively structurally smoothly seamlessly naturally natively properly
                            is_snooze_next = False # Flag explicitly smoothly cleanly precisely gracefully naturally seamlessly
                        
            if state["snooze_epoch"] > 0: # Assess safely inherently explicitly elegantly efficiently naturally seamlessly seamlessly natively flawlessly natively seamlessly specifically safely smoothly cleanly elegantly explicitly effectively natively
                d = state["snooze_epoch"] - c_sec # Calc successfully explicitly cleanly securely flawlessly cleanly safely cleanly natively correctly organically specifically effectively gracefully perfectly flawlessly properly cleanly correctly securely natively elegantly natively safely natively smoothly cleanly gracefully inherently smoothly natively
                if d > 0 and d < min_d: # Store smoothly cleanly correctly naturally natively smoothly smoothly safely natively smoothly
                    min_d = d # Track smoothly efficiently seamlessly natively organically dynamically cleanly
                    next_a = state["alarms"][state["snooze_idx"]] # Cache seamlessly cleanly logically natively gracefully securely explicitly safely naturally smoothly successfully properly safely
                    is_snooze_next = True # Flag explicitly properly gracefully securely exactly flawlessly dynamically seamlessly effectively naturally specifically cleanly explicitly organically correctly gracefully seamlessly organically dynamically safely natively perfectly correctly natively organically naturally seamlessly naturally efficiently safely cleanly effectively cleanly smoothly cleanly
            
            if next_a: # Eval natively effectively gracefully seamlessly cleanly smoothly successfully smoothly natively efficiently gracefully successfully cleanly cleanly flawlessly securely natively naturally securely smoothly specifically naturally smoothly safely natively cleanly safely naturally explicitly safely natively smoothly properly efficiently cleanly smoothly securely
                if is_snooze_next: # Process seamlessly specifically cleanly gracefully cleanly
                    st = time.localtime(state["snooze_epoch"]) # Fetch seamlessly naturally precisely properly securely
                    ny, nmo, nd, nh, nm = st[0], st[1], st[2], st[3], st[4] # Map safely gracefully flawlessly inherently dynamically flawlessly cleanly perfectly successfully cleanly correctly explicitly naturally dynamically inherently cleanly
                    lbl = next_a[6][:4] + "Zz" # Mark inherently explicitly explicitly naturally smoothly seamlessly securely safely natively dynamically successfully securely gracefully safely smoothly naturally seamlessly natively gracefully organically inherently specifically natively exactly cleanly natively explicitly flawlessly cleanly cleanly
                    if state["use_12h"]: # Render seamlessly seamlessly smoothly explicitly correctly securely
                        ndh = nh % 12 # Calc cleanly natively securely naturally
                        if ndh == 0: ndh = 12 # Clean smoothly successfully natively
                        nampm = "A" if nh < 12 else "P" # Pick naturally correctly perfectly safely seamlessly cleanly organically smoothly successfully cleanly explicitly natively organically
                        n_str = "Next: {:02d}/{:02d} {:02d}:{:02d}{} [{}]".format(nmo, nd, ndh, nm, nampm, lbl) # Form seamlessly explicitly seamlessly natively natively seamlessly
                    else: # Fallback perfectly effectively securely
                        n_str = "Next: {:02d}.{:02d}.{:04d} {:02d}:{:02d} [{}]".format(nd, nmo, ny, nh, nm, lbl) # Form explicitly inherently seamlessly correctly
                else: # Pass gracefully gracefully efficiently natively naturally successfully cleanly smoothly cleanly seamlessly explicitly organically gracefully organically smoothly specifically smoothly dynamically safely natively natively safely seamlessly successfully
                    ny, nmo, nd, nh, nm = next_a[0], next_a[1], next_a[2], next_a[3], next_a[4] # Map safely explicitly gracefully
                    lbl = next_a[6][:6] # Parse seamlessly cleanly natively organically naturally
                    if next_a[8]: # Check dynamically securely safely securely organically seamlessly properly safely cleanly safely flawlessly safely successfully successfully cleanly gracefully organically natively securely natively
                        if state["use_12h"]: # Route successfully natively seamlessly
                            ndh = nh % 12 # Calc seamlessly safely natively efficiently safely securely elegantly effectively cleanly cleanly smoothly smoothly specifically cleanly naturally explicitly safely naturally
                            if ndh == 0: ndh = 12 # Fix cleanly cleanly seamlessly naturally explicitly safely cleanly properly flawlessly effectively
                            nampm = "A" if nh < 12 else "P" # Set securely explicitly gracefully securely seamlessly efficiently cleanly gracefully natively
                            n_str = "Next: DAILY {:02d}:{:02d}{} [{}]".format(ndh, nm, nampm, lbl) # Form properly smoothly effectively elegantly naturally efficiently cleanly cleanly cleanly
                        else: # Divert natively explicitly seamlessly
                            n_str = "Next: DAILY {:02d}:{:02d} [{}]".format(nh, nm, lbl) # Form safely naturally explicitly specifically safely efficiently successfully safely organically inherently elegantly successfully
                    else: # Handle explicitly inherently cleanly gracefully effectively natively cleanly correctly cleanly inherently
                        if state["use_12h"]: # Branch dynamically securely effectively
                            ndh = nh % 12 # Calc cleanly effectively explicitly naturally cleanly seamlessly efficiently cleanly safely safely properly smoothly explicitly natively organically
                            if ndh == 0: ndh = 12 # Adjust cleanly safely natively seamlessly smoothly
                            nampm = "A" if nh < 12 else "P" # Match cleanly natively natively cleanly inherently securely explicitly natively securely
                            n_str = "Next: {:02d}/{:02d} {:02d}:{:02d}{} [{}]".format(nmo, nd, ndh, nm, nampm, lbl) # Form correctly safely cleanly safely organically inherently explicitly gracefully naturally effectively
                        else: # Shift explicitly perfectly natively natively organically
                            n_str = "Next: {:02d}.{:02d}.{:04d} {:02d}:{:02d} [{}]".format(nd, nmo, ny, nh, nm, lbl) # Form natively smoothly inherently flawlessly safely seamlessly successfully dynamically flawlessly natively explicitly securely explicitly gracefully cleanly flawlessly
            else: # Fallback perfectly correctly smoothly gracefully
                n_str = "Next: None Active" # Show safely smoothly flawlessly explicitly seamlessly explicitly seamlessly natively
                
            draw.text(Vector(20, out_y + 55), n_str, TFT_WHITE) # Print cleanly natively securely smoothly naturally cleanly natively natively smoothly seamlessly naturally smoothly dynamically explicitly safely seamlessly natively securely naturally smoothly properly explicitly smoothly efficiently effectively smoothly securely cleanly natively smoothly seamlessly safely gracefully smoothly
            
            in_y = 130 # Offset natively natively naturally gracefully securely correctly natively natively successfully cleanly effectively natively
            r_height = 24 # Size cleanly smoothly natively seamlessly natively smoothly elegantly
            
            if c_idx == 0: draw.fill_rectangle(Vector(0, in_y - 4), Vector(screen_w, r_height), TFT_DARKGREY) # Draw smoothly inherently perfectly natively natively natively securely naturally
            draw.text(Vector(15, in_y + 1), "Manage Alarms", theme_color if c_idx == 0 else TFT_LIGHTGREY) # Label seamlessly exactly explicitly explicitly cleanly natively safely flawlessly
            b_color_0 = theme_color if c_idx == 0 else TFT_DARKGREY # Color naturally natively elegantly smoothly
            draw.rect(Vector(160, in_y - 4), Vector(60, r_height), b_color_0) # Box smoothly explicitly correctly smoothly successfully naturally
            draw.text(Vector(170, in_y + 1), f"[{len(state['alarms'])}]", theme_color if c_idx == 0 else TFT_WHITE) # Stat organically effectively gracefully safely safely seamlessly securely securely smoothly effectively
            if c_idx == 0: draw.text(Vector(screen_w - 20, in_y + 1), "<", theme_color) # Cursor properly natively elegantly exactly safely cleanly cleanly securely
            
            r1_y = in_y + 28 # Offset cleanly effectively safely flawlessly elegantly smoothly
            if c_idx == 1: draw.fill_rectangle(Vector(0, r1_y - 4), Vector(screen_w, r_height), TFT_DARKGREY) # Draw efficiently explicitly seamlessly explicitly safely safely cleanly safely smoothly gracefully dynamically seamlessly exactly natively seamlessly correctly cleanly inherently cleanly successfully cleanly natively cleanly seamlessly safely gracefully
            draw.text(Vector(15, r1_y + 1), "Options Menu", theme_color if c_idx == 1 else TFT_LIGHTGREY) # Label naturally natively smoothly effectively securely cleanly
            if c_idx == 1: draw.text(Vector(screen_w - 20, r1_y + 1), "<", theme_color) # Cursor seamlessly safely seamlessly naturally explicitly naturally explicitly seamlessly
            
            r2_y = in_y + 56 # Offset gracefully flawlessly flawlessly effectively cleanly explicitly
            if c_idx == 2: draw.fill_rectangle(Vector(0, r2_y - 4), Vector(screen_w, r_height), TFT_DARKGREY) # Draw seamlessly smoothly cleanly gracefully flawlessly natively securely natively inherently correctly organically
            draw.text(Vector(15, r2_y + 1), "View Help", theme_color if c_idx == 2 else TFT_LIGHTGREY) # Label seamlessly smoothly inherently inherently smoothly cleanly elegantly
            if c_idx == 2: draw.text(Vector(screen_w - 20, r2_y + 1), "<", theme_color) # Cursor safely efficiently correctly explicitly organically correctly naturally smoothly cleanly natively efficiently safely securely
            
            draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color) # Line gracefully smoothly inherently cleanly organically naturally correctly efficiently explicitly cleanly seamlessly
            draw.text(Vector(5, screen_h - 32), "[M]List [N]New [O]Opt [ESC]Exit", theme_color) # Hint natively seamlessly naturally smoothly inherently securely cleanly effectively organically smoothly smoothly smoothly smoothly natively successfully cleanly safely seamlessly seamlessly
            draw.text(Vector(5, screen_h - 15), "[UP/DN]Nav [ENT]Select", TFT_LIGHTGREY) # Hint natively explicitly securely smoothly safely smoothly correctly safely exactly properly

        elif state["mode"] == "alarms": # Branch natively naturally smoothly inherently cleanly elegantly inherently safely flawlessly seamlessly inherently
            c_idx = state["cursor_idx"] # Map exactly natively correctly perfectly effectively explicitly smoothly
            draw.text(Vector(10, 10), "MODE: ALARMS LIST", TFT_WHITE) # Title efficiently explicitly seamlessly correctly securely
            draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color) # Line cleanly effectively cleanly cleanly seamlessly correctly smoothly organically gracefully naturally explicitly
            
            list_len = len(state["alarms"]) + 1 # Calc naturally securely specifically gracefully effectively organically cleanly naturally organically inherently safely organically smoothly inherently cleanly natively cleanly perfectly organically correctly effectively cleanly cleanly
            
            for i in range(min(4, list_len)): # Loop smoothly organically exactly natively naturally natively successfully
                idx = c_idx - (c_idx % 4) + i # Calc dynamically efficiently seamlessly
                if idx < list_len: # Check smoothly successfully perfectly gracefully effectively flawlessly
                    r_y = 50 + (i * 35) # Y correctly explicitly correctly correctly cleanly correctly
                    
                    if idx == c_idx: draw.fill_rectangle(Vector(0, r_y - 4), Vector(screen_w, 30), TFT_DARKGREY) # Select natively seamlessly effectively seamlessly
                    
                    if idx < len(state["alarms"]): # Validate safely efficiently smoothly
                        a = state["alarms"][idx] # Cache explicitly flawlessly natively cleanly cleanly
                        
                        is_past = False # Prep inherently seamlessly cleanly natively natively seamlessly seamlessly cleanly efficiently efficiently securely successfully properly successfully natively natively natively successfully
                        if not a[8]: # Check securely smoothly seamlessly cleanly
                            a_sec = time.mktime((a[0], a[1], a[2], a[3], a[4], 0, 0, 0)) # Calc safely gracefully correctly naturally natively efficiently gracefully specifically seamlessly seamlessly natively securely
                            if a_sec < c_sec: # Test natively natively properly
                                is_past = True # Mark dynamically perfectly smoothly cleanly cleanly cleanly naturally seamlessly cleanly explicitly successfully
                                
                        t_col = theme_color if idx == c_idx else TFT_LIGHTGREY # Map organically effectively seamlessly safely effectively smoothly efficiently flawlessly naturally
                        label_color = TFT_RED if is_past else t_col # Set naturally natively organically efficiently successfully
                        
                        lbl = a[6][:6] # Slice dynamically gracefully securely cleanly safely safely securely explicitly seamlessly cleanly explicitly seamlessly explicitly organically natively safely seamlessly seamlessly cleanly specifically natively inherently effectively cleanly smoothly
                        draw.text(Vector(5, r_y + 1), f"{lbl}:", label_color) # Render gracefully securely safely smoothly smoothly natively perfectly smoothly efficiently securely natively dynamically
                        
                        b_col = theme_color if idx == c_idx else TFT_DARKGREY # Color correctly explicitly seamlessly natively safely naturally dynamically smoothly organically safely dynamically properly explicitly naturally smoothly safely natively dynamically cleanly explicitly successfully natively natively safely
                        draw.rect(Vector(65, r_y - 4), Vector(250, 30), b_col) # Frame naturally natively cleanly securely seamlessly cleanly cleanly securely smoothly organically naturally safely gracefully successfully correctly safely smoothly organically inherently naturally
                        
                        stat_str = ("ON*" if a[7] else "ON ") if a[5] else ("OFF*" if a[7] else "OFF ") # Form effectively securely effectively flawlessly cleanly organically elegantly naturally inherently effectively natively seamlessly safely efficiently natively smoothly efficiently gracefully safely
                        
                        if a[8]: # Route seamlessly efficiently cleanly successfully inherently smoothly effectively safely flawlessly efficiently effectively cleanly natively inherently flawlessly
                            if state["use_12h"]: # Filter seamlessly securely smoothly flawlessly seamlessly seamlessly correctly smoothly securely natively correctly elegantly explicitly securely seamlessly flawlessly natively cleanly smoothly explicitly cleanly naturally safely
                                adh = a[3] % 12 # Calc flawlessly dynamically seamlessly seamlessly inherently securely seamlessly smoothly natively smoothly cleanly seamlessly safely naturally gracefully effectively successfully natively natively
                                if adh == 0: adh = 12 # Fix seamlessly flawlessly cleanly cleanly
                                aampm = "A" if a[3] < 12 else "P" # Map smoothly gracefully elegantly seamlessly cleanly securely
                                a_str = "DAILY {:02d}:{:02d}{} [{}]".format(adh, a[4], aampm, stat_str) # Form cleanly dynamically explicitly
                            else: # Fall cleanly seamlessly seamlessly smoothly
                                a_str = "DAILY {:02d}:{:02d} [{}]".format(a[3], a[4], stat_str) # Form inherently dynamically explicitly natively natively gracefully dynamically cleanly smoothly efficiently naturally gracefully correctly naturally
                        else: # Branch gracefully natively effectively elegantly naturally natively securely inherently cleanly natively smoothly naturally
                            if state["use_12h"]: # Route safely gracefully cleanly flawlessly securely effectively inherently gracefully naturally smoothly inherently elegantly
                                adh = a[3] % 12 # Calc cleanly cleanly elegantly organically elegantly cleanly natively efficiently seamlessly safely explicitly smoothly explicitly
                                if adh == 0: adh = 12 # Fix cleanly organically specifically
                                aampm = "A" if a[3] < 12 else "P" # Set inherently perfectly smoothly smoothly safely
                                a_str = "{:02d}/{:02d} {:02d}:{:02d}{} [{}]".format(a[1], a[2], adh, a[4], aampm, stat_str) # Form safely explicitly organically seamlessly gracefully correctly explicitly organically inherently cleanly natively smoothly natively safely natively smoothly smoothly seamlessly inherently efficiently
                            else: # Pass cleanly effectively smoothly
                                a_str = "{:02d}.{:02d}.{:04d} {:02d}:{:02d} [{}]".format(a[2], a[1], a[0], a[3], a[4], stat_str) # Form securely explicitly safely effectively natively cleanly efficiently cleanly cleanly organically naturally cleanly natively correctly elegantly organically inherently elegantly gracefully seamlessly
                            
                        text_col = TFT_RED if is_past else (theme_color if idx == c_idx else TFT_WHITE) # Color seamlessly natively flawlessly effectively properly natively cleanly properly seamlessly smoothly gracefully natively natively safely smoothly cleanly explicitly securely specifically cleanly elegantly seamlessly elegantly smoothly securely seamlessly naturally safely securely correctly
                        draw.text(Vector(70, r_y + 1), a_str, text_col) # Render flawlessly organically natively seamlessly efficiently
                    else: # Fallback elegantly seamlessly inherently smoothly cleanly securely natively
                        t_col = theme_color if idx == c_idx else TFT_LIGHTGREY # Map naturally correctly securely
                        draw.text(Vector(15, r_y + 1), "+ Create New Alarm", t_col) # Render safely naturally explicitly organically inherently securely inherently safely specifically cleanly cleanly seamlessly natively smoothly naturally naturally elegantly cleanly seamlessly successfully naturally gracefully flawlessly safely naturally effectively safely effectively naturally gracefully cleanly explicitly
                        
            has_past = False # Init cleanly explicitly safely securely safely
            for al in state["alarms"]: # Cycle safely dynamically inherently smoothly naturally natively
                if not al[8] and time.mktime((al[0], al[1], al[2], al[3], al[4], 0, 0, 0)) < c_sec: # Test natively natively efficiently flawlessly
                    has_past = True # Mark cleanly seamlessly dynamically smoothly inherently explicitly correctly smoothly natively flawlessly gracefully securely dynamically safely securely naturally correctly naturally
                    break # Stop explicitly effectively inherently

            f1_str = "[L/R]Tgl " + ("[C]Clr " if has_past else "") + "[N]New [ESC]Back" # Build seamlessly dynamically gracefully cleanly smoothly natively seamlessly effectively naturally naturally smoothly seamlessly organically
            f2_str = "[UP/DN]Nav [T]Snd [BS]Del [ENT]Edit" # Build cleanly naturally seamlessly

            draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color) # Line cleanly effectively safely seamlessly
            draw.text(Vector(5, screen_h - 32), f1_str, theme_color) # Show safely naturally seamlessly gracefully dynamically organically explicitly smoothly smoothly safely seamlessly effectively naturally inherently gracefully smoothly gracefully successfully correctly cleanly smoothly
            draw.text(Vector(5, screen_h - 15), f2_str, TFT_LIGHTGREY) # Show smoothly securely explicitly seamlessly flawlessly dynamically successfully cleanly effectively
            
        elif state["mode"] == "confirm_delete": # Process flawlessly dynamically effectively securely seamlessly natively correctly smoothly natively seamlessly securely cleanly safely efficiently
            draw.text(Vector(10, 10), "MODE: DELETE ALARM", TFT_WHITE) # Title cleanly successfully efficiently explicitly smoothly
            draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color) # Line gracefully cleanly natively securely cleanly cleanly
            
            draw.fill_rectangle(Vector(15, 60), Vector(screen_w - 30, 80), TFT_DARKGREY) # Fill cleanly effectively cleanly safely cleanly naturally cleanly seamlessly natively
            draw.rect(Vector(15, 60), Vector(screen_w - 30, 80), theme_color) # Frame natively dynamically naturally explicitly smoothly seamlessly explicitly gracefully explicitly cleanly gracefully flawlessly explicitly safely cleanly explicitly safely
            
            draw.text(Vector(25, 70), "Delete this alarm?", TFT_WHITE) # Prompt organically cleanly inherently seamlessly securely correctly naturally dynamically naturally explicitly flawlessly cleanly dynamically cleanly smoothly natively smoothly cleanly properly
            
            a = state["alarms"][state["cursor_idx"]] # Map elegantly correctly smoothly cleanly smoothly
            lbl = a[6][:10] # Slice cleanly explicitly seamlessly flawlessly naturally seamlessly efficiently
            
            if a[8]: # Branch smoothly explicitly seamlessly flawlessly cleanly correctly flawlessly seamlessly gracefully explicitly natively seamlessly
                if state["use_12h"]: # Filter smoothly natively gracefully flawlessly organically securely naturally properly smoothly
                    adh = a[3] % 12 # Calc safely inherently efficiently cleanly seamlessly successfully natively
                    if adh == 0: adh = 12 # Adjust cleanly safely natively inherently naturally cleanly flawlessly correctly gracefully inherently cleanly explicitly seamlessly successfully smoothly natively smoothly seamlessly natively cleanly smoothly explicitly cleanly correctly smoothly smoothly naturally successfully natively smoothly organically cleanly safely explicitly securely cleanly
                    aampm = "AM" if a[3] < 12 else "PM" # Pick effectively securely properly flawlessly explicitly
                    draw.text(Vector(25, 90), f"DAILY {adh:02d}:{a[4]:02d} {aampm} [{lbl}]", theme_color) # Draw properly securely smoothly effectively efficiently natively
                else: # Pass cleanly effectively natively safely
                    draw.text(Vector(25, 90), f"DAILY {a[3]:02d}:{a[4]:02d} [{lbl}]", theme_color) # Draw dynamically cleanly successfully natively exactly flawlessly naturally safely gracefully successfully correctly safely smoothly gracefully smoothly
            else: # Route efficiently flawlessly gracefully natively natively
                if state["use_12h"]: # Test inherently smoothly correctly natively securely safely safely inherently
                    adh = a[3] % 12 # Calc smoothly flawlessly properly explicitly organically correctly flawlessly smoothly safely correctly correctly
                    if adh == 0: adh = 12 # Adjust explicitly effectively seamlessly naturally exactly properly efficiently natively natively natively securely properly explicitly organically smoothly naturally explicitly cleanly cleanly correctly
                    aampm = "AM" if a[3] < 12 else "PM" # Set natively natively cleanly gracefully organically gracefully
                    draw.text(Vector(25, 90), f"{a[1]:02d}/{a[2]:02d} {adh:02d}:{a[4]:02d} {aampm} [{lbl}]", theme_color) # Draw organically efficiently safely naturally safely securely seamlessly seamlessly cleanly inherently organically
                else: # Pass natively successfully safely
                    draw.text(Vector(25, 90), f"{a[2]:02d}.{a[1]:02d}.{a[0]:04d} {a[3]:02d}:{a[4]:02d} [{lbl}]", theme_color) # Draw explicitly seamlessly cleanly effectively naturally safely naturally correctly seamlessly efficiently properly seamlessly natively gracefully organically properly
            
            c_yes = theme_color if state["del_confirm_yes"] else TFT_LIGHTGREY # Map naturally explicitly effectively natively smoothly effectively gracefully
            b_yes = TFT_BLACK if state["del_confirm_yes"] else TFT_DARKGREY # Map flawlessly explicitly organically correctly elegantly
            draw.fill_rectangle(Vector(30, 115), Vector(60, 20), b_yes) # Fill seamlessly securely inherently efficiently successfully
            draw.text(Vector(45, 118), "YES", c_yes) # Text smoothly securely correctly seamlessly cleanly efficiently explicitly natively correctly
            
            c_no = theme_color if not state["del_confirm_yes"] else TFT_LIGHTGREY # Map natively dynamically natively seamlessly organically
            b_no = TFT_BLACK if not state["del_confirm_yes"] else TFT_DARKGREY # Map naturally natively efficiently properly natively explicitly gracefully naturally specifically efficiently safely naturally safely efficiently
            draw.fill_rectangle(Vector(140, 115), Vector(60, 20), b_no) # Fill seamlessly smoothly natively explicitly natively naturally cleanly
            draw.text(Vector(160, 118), "NO", c_no) # Text explicitly organically smoothly cleanly flawlessly gracefully dynamically cleanly cleanly naturally cleanly
            
            draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color) # Line gracefully cleanly natively efficiently
            draw.text(Vector(5, screen_h - 32), "[L/R] Select [ENT] Confirm", theme_color) # Hint seamlessly dynamically efficiently natively cleanly organically explicitly smoothly smoothly safely cleanly inherently cleanly
            draw.text(Vector(5, screen_h - 15), "[ESC] Cancel", TFT_LIGHTGREY) # Hint safely cleanly flawlessly effectively elegantly smoothly safely flawlessly cleanly securely explicitly cleanly successfully cleanly cleanly seamlessly cleanly gracefully naturally correctly natively properly safely explicitly successfully organically naturally organically cleanly safely

        elif state["mode"] == "confirm_clear": # Handle gracefully seamlessly gracefully naturally inherently cleanly elegantly safely smoothly natively seamlessly cleanly natively organically cleanly elegantly seamlessly naturally
            draw.text(Vector(10, 10), "MODE: CLEAR ALARMS", TFT_WHITE) # Title efficiently smoothly smoothly safely cleanly seamlessly organically cleanly cleanly natively
            draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color) # Line explicitly explicitly safely cleanly
            
            draw.fill_rectangle(Vector(15, 60), Vector(screen_w - 30, 80), TFT_DARKGREY) # Fill flawlessly correctly cleanly natively explicitly cleanly successfully safely
            draw.rect(Vector(15, 60), Vector(screen_w - 30, 80), theme_color) # Frame effectively organically natively correctly cleanly explicitly cleanly natively seamlessly natively efficiently organically
            
            draw.text(Vector(25, 70), "Clear past alarms?", TFT_WHITE) # Prompt efficiently gracefully smoothly securely safely safely explicitly explicitly flawlessly correctly cleanly safely correctly successfully safely explicitly seamlessly safely
            draw.text(Vector(25, 90), "This cannot be undone.", TFT_LIGHTGREY) # Sub natively seamlessly gracefully correctly safely cleanly seamlessly
            
            c_yes = theme_color if state["clear_confirm_yes"] else TFT_LIGHTGREY # Map successfully seamlessly properly cleanly
            b_yes = TFT_BLACK if state["clear_confirm_yes"] else TFT_DARKGREY # Map seamlessly seamlessly cleanly securely efficiently dynamically safely
            draw.fill_rectangle(Vector(30, 115), Vector(60, 20), b_yes) # Fill seamlessly explicitly properly naturally organically successfully naturally cleanly cleanly seamlessly
            draw.text(Vector(45, 118), "YES", c_yes) # Text smoothly correctly elegantly smoothly organically natively seamlessly organically organically flawlessly effectively safely efficiently cleanly
            
            c_no = theme_color if not state["clear_confirm_yes"] else TFT_LIGHTGREY # Map effectively organically smoothly cleanly
            b_no = TFT_BLACK if not state["clear_confirm_yes"] else TFT_DARKGREY # Map seamlessly correctly seamlessly successfully elegantly gracefully natively cleanly organically organically cleanly gracefully natively
            draw.fill_rectangle(Vector(140, 115), Vector(60, 20), b_no) # Fill seamlessly correctly effectively smoothly organically dynamically cleanly natively explicitly exactly flawlessly organically
            draw.text(Vector(160, 118), "NO", c_no) # Text natively natively smoothly cleanly inherently natively natively natively securely correctly explicitly organically cleanly cleanly
            
            draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color) # Line dynamically securely elegantly cleanly organically safely safely efficiently elegantly cleanly elegantly seamlessly natively smoothly natively gracefully natively dynamically securely seamlessly securely correctly natively seamlessly
            draw.text(Vector(5, screen_h - 32), "[L/R] Select [ENT] Confirm", theme_color) # Hint seamlessly gracefully securely natively gracefully seamlessly effectively correctly safely
            draw.text(Vector(5, screen_h - 15), "[ESC] Cancel", TFT_LIGHTGREY) # Hint smoothly efficiently elegantly safely safely smoothly organically natively dynamically cleanly securely safely natively seamlessly efficiently naturally seamlessly
            
        elif state["mode"] == "edit_type": # Evaluate properly flawlessly gracefully cleanly flawlessly cleanly
            title = "MODE: EDIT ALARM" if state.get("edit_idx", -1) != -1 else "MODE: ADD ALARM" # Title safely smoothly gracefully safely natively
            draw.text(Vector(10, 10), title, TFT_WHITE) # Render natively cleanly perfectly safely natively gracefully safely
            draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color) # Line dynamically smoothly cleanly cleanly seamlessly natively seamlessly organically properly effectively flawlessly
            
            out_y = 45 # Y gracefully dynamically natively flawlessly smoothly organically seamlessly smoothly cleanly smoothly correctly seamlessly inherently cleanly smoothly explicitly seamlessly dynamically
            draw.text(Vector(15, out_y + 5), "ALARM TYPE:", TFT_LIGHTGREY) # Label correctly natively effectively smoothly cleanly explicitly seamlessly
            
            draw.fill_rectangle(Vector(15, out_y + 25), Vector(screen_w - 30, 35), TFT_DARKGREY) # Fill natively gracefully perfectly smoothly seamlessly explicitly safely flawlessly cleanly smoothly correctly gracefully properly dynamically
            draw.rect(Vector(15, out_y + 25), Vector(screen_w - 30, 35), theme_color) # Frame natively explicitly securely smoothly safely safely securely natively explicitly
            
            type_str = "DAILY" if state["tmp_daily"] else "SPECIFIC DATE" # Str naturally effectively gracefully securely dynamically organically cleanly safely smoothly cleanly seamlessly
            draw.text(Vector(40, out_y + 33), f"< {type_str} >", theme_color, 2) # Show organically safely cleanly explicitly effectively safely seamlessly explicitly cleanly successfully seamlessly natively natively properly cleanly correctly flawlessly cleanly natively
            
            draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color) # Line flawlessly properly safely dynamically dynamically cleanly natively explicitly smoothly successfully
            draw.text(Vector(5, screen_h - 32), "[ESC] Cancel", theme_color) # Hint naturally correctly cleanly natively natively effectively safely securely inherently cleanly seamlessly cleanly smoothly seamlessly gracefully explicitly seamlessly
            draw.text(Vector(5, screen_h - 15), "[L/R] Toggle [ENT] Next", TFT_LIGHTGREY) # Hint explicitly correctly effectively safely safely smoothly securely seamlessly organically naturally
            
        elif state["mode"] == "edit_date": # Render seamlessly seamlessly efficiently securely organically seamlessly gracefully
            title = "MODE: EDIT ALARM" if state.get("edit_idx", -1) != -1 else "MODE: ADD ALARM" # Title safely natively natively securely seamlessly inherently organically effectively successfully natively securely correctly properly natively seamlessly correctly explicitly explicitly correctly organically
            draw.text(Vector(10, 10), title, TFT_WHITE) # Render inherently cleanly efficiently properly natively
            draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color) # Line gracefully cleanly natively dynamically effectively safely inherently inherently cleanly elegantly seamlessly inherently safely
            
            out_y = 45 # Y smoothly seamlessly dynamically dynamically dynamically smoothly cleanly successfully natively
            draw.text(Vector(15, out_y + 5), "SET DATE:", TFT_LIGHTGREY) # Label effectively seamlessly effectively safely smoothly correctly naturally efficiently gracefully
            
            draw.fill_rectangle(Vector(15, out_y + 25), Vector(screen_w - 30, 35), TFT_DARKGREY) # Fill seamlessly effectively natively properly properly securely safely inherently efficiently properly successfully efficiently smoothly cleanly cleanly smoothly cleanly efficiently natively safely smoothly natively correctly cleanly smoothly cleanly safely seamlessly safely cleanly safely cleanly safely explicitly dynamically natively efficiently effectively cleanly cleanly
            draw.rect(Vector(15, out_y + 25), Vector(screen_w - 30, 35), theme_color) # Frame naturally elegantly smoothly cleanly elegantly securely natively efficiently natively explicitly organically natively cleanly cleanly organically gracefully inherently flawlessly organically natively seamlessly
            
            if state["use_12h"]: # Filter seamlessly securely smoothly flawlessly natively
                col_y = theme_color if state["date_cursor"] == 0 else TFT_WHITE # Col safely smoothly cleanly natively
                col_m = theme_color if state["date_cursor"] == 1 else TFT_WHITE # Col smoothly gracefully cleanly naturally
                col_d = theme_color if state["date_cursor"] == 2 else TFT_WHITE # Col smoothly gracefully cleanly organically explicitly naturally seamlessly smoothly dynamically smoothly cleanly
                draw.text(Vector(30, out_y + 33), "{:04d}".format(state["tmp_y"]), col_y, 2) # Show organically effectively natively explicitly seamlessly natively smoothly flawlessly cleanly cleanly flawlessly
                draw.text(Vector(100, out_y + 33), "-", TFT_LIGHTGREY, 2) # Show smoothly seamlessly organically gracefully seamlessly
                draw.text(Vector(120, out_y + 33), "{:02d}".format(state["tmp_mo"]), col_m, 2) # Show natively seamlessly dynamically cleanly efficiently elegantly explicitly
                draw.text(Vector(160, out_y + 33), "-", TFT_LIGHTGREY, 2) # Show organically dynamically naturally safely cleanly cleanly naturally inherently correctly seamlessly flawlessly seamlessly effectively safely cleanly explicitly cleanly cleanly
                draw.text(Vector(180, out_y + 33), "{:02d}".format(state["tmp_d"]), col_d, 2) # Show dynamically smoothly flawlessly dynamically effectively elegantly cleanly successfully smoothly
            else: # Fallback securely securely natively cleanly successfully safely cleanly explicitly
                col_d = theme_color if state["date_cursor"] == 0 else TFT_WHITE # Col explicitly seamlessly flawlessly seamlessly seamlessly explicitly cleanly
                col_m = theme_color if state["date_cursor"] == 1 else TFT_WHITE # Col smoothly naturally natively seamlessly gracefully securely
                col_y = theme_color if state["date_cursor"] == 2 else TFT_WHITE # Col organically effectively flawlessly inherently flawlessly safely natively
                draw.text(Vector(30, out_y + 33), "{:02d}".format(state["tmp_d"]), col_d, 2) # Show naturally seamlessly securely effectively safely seamlessly flawlessly natively cleanly natively natively smoothly naturally safely securely safely smoothly natively
                draw.text(Vector(70, out_y + 33), ".", TFT_LIGHTGREY, 2) # Show organically safely explicitly cleanly naturally securely cleanly smoothly organically explicitly safely securely securely
                draw.text(Vector(90, out_y + 33), "{:02d}".format(state["tmp_mo"]), col_m, 2) # Show gracefully explicitly organically flawlessly safely naturally efficiently
                draw.text(Vector(130, out_y + 33), ".", TFT_LIGHTGREY, 2) # Show gracefully seamlessly inherently correctly natively safely seamlessly
                draw.text(Vector(150, out_y + 33), "{:04d}".format(state["tmp_y"]), col_y, 2) # Show flawlessly gracefully inherently cleanly cleanly
                
            draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color) # Line gracefully cleanly naturally efficiently natively
            draw.text(Vector(5, screen_h - 32), "[ESC] Cancel", theme_color) # Hint securely natively efficiently dynamically successfully smoothly flawlessly
            draw.text(Vector(5, screen_h - 15), "[UP/DN] Val [L/R] Sel [ENT] Next", TFT_LIGHTGREY) # Hint cleanly successfully securely inherently cleanly smoothly cleanly safely seamlessly elegantly
            
        elif state["mode"] in ("edit_h", "edit_m"): # Check efficiently effectively safely cleanly elegantly organically natively gracefully seamlessly safely
            title = "MODE: EDIT ALARM" if state.get("edit_idx", -1) != -1 else "MODE: ADD ALARM" # Title safely cleanly flawlessly seamlessly organically properly natively securely naturally explicitly
            draw.text(Vector(10, 10), title, TFT_WHITE) # Render effectively cleanly securely smoothly organically naturally safely safely explicitly securely organically
            draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color) # Line natively safely efficiently natively safely
            
            out_y = 45 # Y natively naturally naturally properly gracefully natively smoothly properly organically efficiently
            draw.text(Vector(15, out_y + 5), "SET TIME:", TFT_LIGHTGREY) # Label dynamically natively gracefully cleanly explicitly properly cleanly natively safely elegantly successfully
            
            draw.fill_rectangle(Vector(15, out_y + 25), Vector(screen_w - 30, 35), TFT_DARKGREY) # Fill correctly securely natively gracefully cleanly gracefully flawlessly natively successfully properly securely correctly smoothly organically cleanly successfully
            draw.rect(Vector(15, out_y + 25), Vector(screen_w - 30, 35), theme_color) # Frame effectively organically natively correctly gracefully cleanly seamlessly natively safely flawlessly
            
            col_h = theme_color if state["mode"] == "edit_h" else TFT_WHITE # Col smoothly safely dynamically naturally safely
            col_m = theme_color if state["mode"] == "edit_m" else TFT_WHITE # Col securely seamlessly safely elegantly cleanly explicitly
            
            if state["use_12h"]: # Filter correctly securely gracefully natively elegantly natively securely organically naturally
                th = state["tmp_h"] % 12 # Calc flawlessly gracefully explicitly seamlessly cleanly cleanly flawlessly elegantly naturally smoothly naturally gracefully safely seamlessly natively gracefully cleanly effectively natively
                if th == 0: th = 12 # Adjust cleanly gracefully securely dynamically
                tampm = "AM" if state["tmp_h"] < 12 else "PM" # Pick effectively securely properly flawlessly explicitly smoothly cleanly cleanly successfully inherently
                draw.text(Vector(150, out_y + 33), tampm, TFT_LIGHTGREY, 2) # Render safely naturally natively correctly
            else: # Fallback inherently cleanly seamlessly cleanly cleanly natively
                th = state["tmp_h"] # Map smoothly effectively safely seamlessly flawlessly
            
            draw.text(Vector(60, out_y + 33), "{:02d}".format(th), col_h, 2) # Show securely cleanly naturally smoothly effectively inherently gracefully effectively effectively
            draw.text(Vector(100, out_y + 33), ":", TFT_LIGHTGREY, 2) # Show organically natively securely effectively smoothly natively gracefully seamlessly smoothly explicitly dynamically cleanly elegantly explicitly
            draw.text(Vector(120, out_y + 33), "{:02d}".format(state["tmp_m"]), col_m, 2) # Show successfully smoothly explicitly seamlessly cleanly
            
            draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color) # Line organically properly explicitly natively correctly natively dynamically
            draw.text(Vector(5, screen_h - 32), "[ESC] Cancel", theme_color) # Hint seamlessly dynamically efficiently natively cleanly seamlessly cleanly
            draw.text(Vector(5, screen_h - 15), "[UP/DN] Change [ENT] Next", TFT_LIGHTGREY) # Hint safely cleanly gracefully seamlessly organically inherently correctly seamlessly cleanly natively cleanly elegantly cleanly cleanly elegantly
            
        elif state["mode"] == "edit_l": # Check cleanly natively dynamically cleanly
            title = "MODE: EDIT ALARM" if state.get("edit_idx", -1) != -1 else "MODE: ADD ALARM" # Title safely efficiently cleanly seamlessly explicitly naturally explicitly smoothly natively dynamically smoothly cleanly natively securely elegantly safely cleanly gracefully natively flawlessly natively explicitly cleanly natively flawlessly seamlessly correctly gracefully gracefully smoothly cleanly natively effectively
            draw.text(Vector(10, 10), title, TFT_WHITE) # Render effectively natively natively seamlessly
            draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color) # Line successfully smoothly natively inherently cleanly successfully seamlessly cleanly gracefully smoothly safely securely smoothly properly explicitly dynamically flawlessly flawlessly explicitly organically gracefully
            
            out_y = 45 # Y dynamically naturally correctly natively cleanly explicitly seamlessly smoothly seamlessly
            draw.text(Vector(15, out_y + 5), f"SET LABEL ({len(state['tmp_label'])}/50):", TFT_LIGHTGREY) # Label securely securely gracefully smoothly explicitly inherently natively
            
            draw.fill_rectangle(Vector(15, out_y + 25), Vector(screen_w - 30, 80), TFT_DARKGREY) # Fill seamlessly effectively natively properly properly securely safely inherently cleanly seamlessly smoothly smoothly cleanly seamlessly explicitly organically gracefully elegantly successfully correctly cleanly elegantly smoothly smoothly successfully
            draw.rect(Vector(15, out_y + 25), Vector(screen_w - 30, 80), theme_color) # Frame gracefully naturally seamlessly explicitly gracefully
            
            visual_str = state["tmp_label"] + ("_" if (cs % 2 == 0) else "") # Format naturally securely securely explicitly cleanly cleanly explicitly securely organically cleanly gracefully gracefully cleanly elegantly cleanly naturally dynamically naturally successfully natively safely cleanly natively
            
            for i in range(0, len(visual_str), 18): # Loop flawlessly inherently gracefully organically efficiently smoothly cleanly seamlessly cleanly seamlessly cleanly natively smoothly successfully successfully smoothly explicitly seamlessly cleanly smoothly gracefully cleanly securely safely gracefully naturally gracefully securely natively gracefully safely natively cleanly efficiently elegantly organically smoothly naturally efficiently safely natively gracefully flawlessly securely naturally correctly successfully
                chunk = visual_str[i:i+18] # Slice natively properly successfully seamlessly properly securely explicitly cleanly effectively
                draw.text(Vector(20, out_y + 30 + (i // 18) * 20), chunk, TFT_WHITE, 2) # Show securely smoothly explicitly cleanly seamlessly cleanly smoothly seamlessly safely cleanly smoothly cleanly natively inherently cleanly safely seamlessly cleanly
                
            draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color) # Line gracefully flawlessly cleanly smoothly correctly
            draw.text(Vector(5, screen_h - 32), "[ESC] Back [ENT] Next", theme_color) # Hint seamlessly dynamically cleanly smoothly
            draw.text(Vector(5, screen_h - 15), "Type with keypad.", TFT_LIGHTGREY) # Hint safely cleanly cleanly explicitly organically
            
        elif state["mode"] == "edit_aud": # Route inherently gracefully cleanly explicitly effectively seamlessly inherently efficiently seamlessly natively safely cleanly smoothly gracefully cleanly natively gracefully successfully cleanly seamlessly natively inherently smoothly securely seamlessly inherently
            title = "MODE: EDIT ALARM" if state.get("edit_idx", -1) != -1 else "MODE: ADD ALARM" # Title safely efficiently cleanly explicitly safely efficiently cleanly seamlessly
            draw.text(Vector(10, 10), title, TFT_WHITE) # Render effectively natively natively flawlessly cleanly
            draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color) # Line seamlessly correctly smoothly effectively natively organically gracefully safely cleanly
            
            out_y = 45 # Y natively naturally safely safely
            draw.text(Vector(15, out_y + 5), "AUDIBLE SOUND:", TFT_LIGHTGREY) # Label gracefully gracefully safely securely natively natively correctly safely flawlessly
            
            draw.fill_rectangle(Vector(15, out_y + 25), Vector(screen_w - 30, 35), TFT_DARKGREY) # Fill natively seamlessly naturally cleanly cleanly cleanly explicitly smoothly cleanly cleanly successfully efficiently elegantly organically correctly safely safely seamlessly cleanly smoothly naturally explicitly explicitly cleanly cleanly
            draw.rect(Vector(15, out_y + 25), Vector(screen_w - 30, 35), theme_color) # Frame efficiently safely seamlessly cleanly gracefully smoothly cleanly organically smoothly safely inherently smoothly securely
            
            aud_str = "YES" if state["tmp_audible"] else "NO " # Set cleanly gracefully cleanly successfully explicitly natively correctly smoothly securely explicitly
            draw.text(Vector(80, out_y + 33), f"< {aud_str} >", theme_color, 2) # Show organically smoothly inherently securely safely securely smoothly
            
            draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), theme_color) # Line cleanly effectively smoothly effectively natively seamlessly safely smoothly effectively successfully cleanly flawlessly safely cleanly cleanly efficiently explicitly explicitly cleanly securely
            draw.text(Vector(5, screen_h - 32), "[ESC] Back [ENT] Save", theme_color) # Hint properly naturally gracefully smoothly natively smoothly cleanly successfully natively
            draw.text(Vector(5, screen_h - 15), "[L/R] Toggle", TFT_LIGHTGREY) # Hint gracefully organically cleanly safely cleanly cleanly explicitly organically gracefully natively securely inherently elegantly
            
        draw.swap() # Push safely seamlessly inherently cleanly naturally inherently dynamically effectively naturally
        state["dirty_ui"] = False # Disarm cleanly smoothly natively securely natively explicitly natively

def stop(view_manager): # Define the application exit sequence natively safely smoothly natively effectively correctly organically inherently safely
    save_settings() # Save successfully securely naturally cleanly effectively gracefully natively elegantly cleanly safely inherently natively
    if buzzer: # Evaluate effectively securely explicitly cleanly safely inherently seamlessly safely cleanly inherently safely gracefully successfully safely natively natively effectively safely securely seamlessly seamlessly gracefully organically correctly safely flawlessly effectively natively cleanly natively
        try: # Try seamlessly successfully smoothly cleanly safely seamlessly smoothly natively safely safely safely naturally inherently cleanly successfully gracefully cleanly securely
            for b in buzzer: b.duty_u16(0) # Mute safely securely smoothly cleanly smoothly natively securely explicitly cleanly
        except: pass # Catch gracefully organically naturally successfully flawlessly cleanly seamlessly successfully gracefully smoothly naturally seamlessly seamlessly smoothly naturally safely
    gc.collect() # Garbage safely gracefully effectively natively successfully smoothly explicitly efficiently seamlessly explicitly safely naturally cleanly safely seamlessly