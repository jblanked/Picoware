# Import the const directive from MicroPython to optimize static variables at compile time mathematically
from micropython import const
# Import the Vector class to define precise X and Y display coordinates for UI elements securely
from picoware.system.vector import Vector
# Import UI color constants to colorize the application interface natively
from picoware.system.colors import (
    # Import orange color for the orange theme option logically
    TFT_ORANGE, 
    # Import dark grey color for panel backgrounds and inactive borders securely
    TFT_DARKGREY, 
    # Import light grey color for secondary text and disabled elements natively
    TFT_LIGHTGREY, 
    # Import white color for primary text explicitly
    TFT_WHITE, 
    # Import black color for deep backgrounds and initial screen clearing mathematically
    TFT_BLACK,
    # Import blue color for the blue theme option logically
    TFT_BLUE, 
    # Import yellow color for the yellow theme option logically
    TFT_YELLOW, 
    # Import cyan color for active inputs and shortcuts securely
    TFT_CYAN, 
    # Import green color for the default green theme option natively
    TFT_GREEN, 
    # Import red color for the red theme option logically
    TFT_RED,
)
# Import hardware button constants explicitly mapped to the Picocalc physical keypad securely
from picoware.system.buttons import (
    # Import standard navigational and control buttons mathematically
    BUTTON_BACK, BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_CENTER,
    # Import number keys required strictly for typing values into the fields inherently
    BUTTON_0, BUTTON_1, BUTTON_2, BUTTON_3, BUTTON_4, 
    BUTTON_5, BUTTON_6, BUTTON_7, BUTTON_8, BUTTON_9,
    # Import the period and backspace keys for numeric editing securely
    BUTTON_PERIOD, BUTTON_BACKSPACE,
    # Import explicitly mapped letter shortcut keys and the ESCAPE key for exiting logically
    BUTTON_C, BUTTON_F, BUTTON_T, BUTTON_V, BUTTON_H, BUTTON_ESCAPE,
    # Import the M and O keys specifically to act as dedicated application shortcuts natively
    BUTTON_M, BUTTON_O
)
# Import the TextBox GUI component to manage and render the scrollable help overlay securely
from picoware.gui.textbox import TextBox
# Import the json module to parse and serialize the application's configuration state natively
import json
# Import the garbage collection module to manually free unreferenced memory on the Pico structurally
import gc

# Define the absolute file path for saving the settings JSON on the physical SD card
_SETTINGS_FILE = "/picoware/apps/unit_converter_settings.json" 

# Define the dynamic themes array mapping literal string names to their physical hardware color constants natively
_THEMES = (
    # Define the Green theme mapping explicitly
    ("Green", TFT_GREEN),
    # Define the Red theme mapping explicitly
    ("Red", TFT_RED),
    # Define the Blue theme mapping explicitly
    ("Blue", TFT_BLUE),
    # Define the Yellow theme mapping explicitly
    ("Yellow", TFT_YELLOW),
    # Define the Orange theme mapping explicitly
    ("Orange", TFT_ORANGE)
)

# Define the expanded categories and their respective units with base conversion multipliers logically
_CONVERSIONS = (
    # Define the Length category with base unit as meters (m). Included microns and thou for machining securely.
    ("Length", (("um", 0.000001), ("thou", 0.0000254), ("mm", 0.001), ("cm", 0.01), ("m", 1.0), ("in", 0.0254), ("ft", 0.3048), ("yd", 0.9144))),
    # Define the Weight category with base unit as kilograms (kg) mathematically
    ("Weight", (("mg", 0.000001), ("g", 0.001), ("kg", 1.0), ("oz", 0.0283495), ("lb", 0.453592))),
    # Define the Volume category with base unit as Liters (L) mathematically
    ("Volume", (("ml", 0.001), ("L", 1.0), ("gal", 3.78541), ("fl oz", 0.0295735))),
    # Define the Kitchen category with base unit as milliliters (ml) for recipe and cooking conversions natively.
    ("Kitchen", (("ml", 1.0), ("tsp", 4.92892), ("tbsp", 14.7868), ("fl oz", 29.5735), ("cup", 236.588), ("pint", 473.176), ("L", 1000.0))),
    # Define the Area category with base unit as square meters (m2). Included sq in for shop materials securely.
    ("Area", (("cm2", 0.0001), ("m2", 1.0), ("sq in", 0.00064516), ("sq ft", 0.092903))),
    # Define the Speed category with base unit as meters per second (m/s). Included mm/s for 3D printing natively.
    ("Speed", (("mm/s", 0.001), ("m/s", 1.0), ("km/h", 0.277778), ("mph", 0.44704))),
    # Define the Pressure category with base unit as Pascals (Pa). Essential for air compressors and pneumatics logically.
    ("Press", (("Pa", 1.0), ("kPa", 1000.0), ("bar", 100000.0), ("psi", 6894.76))),
    # Define the Torque category with base unit as Newton-meters (Nm). Essential for fasteners and servos securely.
    ("Torque", (("Nmm", 0.001), ("Nm", 1.0), ("in-lb", 0.1129848), ("ft-lb", 1.355818))),
    # Define the Power category with base unit as Watts (W). Essential for spindles and electronics mathematically.
    ("Power", (("W", 1.0), ("kW", 1000.0), ("hp", 745.7))),
    # Define the Angle category with base unit as Degrees. Essential for setups and indexing natively.
    ("Angle", (("deg", 1.0), ("rad", 57.2957795))),
    # Define the Temperature category (multipliers not used directly, requires custom logic) logically
    ("Temp", (("C", 0), ("F", 0), ("K", 0)))
)

# Define the updated help text string maintaining the frozen version and describing the newly added Options shortcut explicitly
_HELP_TEXT = "UNIT CONVERTER\nVersion 1.93\n----------------\nCATEGORIES:\n- Len, Area, Vol\n- Kitch, Wgt, Spd\n- Press, Torq, Pwr\n- Ang, Temp\n\nSHORTCUTS:\n[C] Cycle Cat\n[F] Edit From\n[T] Edit To\n[V] Edit Value (Clears)\n[H] Open Help\n[O] Open Options\n[M] Toggle +/- (Contextual)\n[ESC] Exit App\n\nCONTROLS:\n[UP/DN]: Cursor Nav\n[L/R]: Select / Edit\n[ENTER]: Confirm\n[BACK]: Exit App"

# Define the baseline default configuration dictionary to ensure predictable behavior upon boot logically
DEFAULT_STATE = {
    # Set the default category index (0 = Length) securely
    "category_idx": 0,
    # Set the default From unit index securely
    "from_idx": 0,
    # Set the default To unit index securely
    "to_idx": 1,
    # Set the default input value string mathematically
    "input_val": "1.0",
    # Initialize the main UI cursor index strictly to 0 natively
    "cursor_idx": 0,
    # Initialize the dynamic theme index to 0 (Defaulting safely to Green) securely
    "theme_idx": 0,
    # Initialize the custom background red color channel securely
    "bg_r": 0,
    # Initialize the custom background green color channel securely
    "bg_g": 0,
    # Initialize the custom background blue color channel securely
    "bg_b": 0,
    # Initialize the options menu cursor index explicitly for independent navigation natively
    "options_cursor_idx": 0,
    # Initialize the dirty UI flag to force an initial render automatically securely
    "dirty_ui": True,
    # Initialize the blinking cursor frame counter to zero strictly for animation timing mathematically
    "blink_counter": 0,
    # Initialize the boolean flag determining if the cursor character is currently visible logically
    "cursor_visible": True,
    # Initialize the pending save flag to explicitly track deferred hardware writes securely
    "pending_save": False,
    # Initialize the countdown timer variable specifically to delay the SD card save explicitly
    "save_timer": 0
}

# Clone the default state dictionary into the active runtime variable to isolate defaults securely
state = DEFAULT_STATE.copy()
# Initialize the active input tracker to None to signify the typing mode is currently closed natively
state["active_input"] = None

# Initialize the global conversion result string to zero mathematically
conv_result = "0.0"
# Initialize the global storage manager reference to None natively
storage = None
# Initialize the boolean flag determining if the help screen overlay is actively rendered logically
show_help = False
# Initialize the boolean flag determining if the options screen overlay is actively rendered logically
show_options = False
# Initialize the global help box UI instance to None to save memory until formally requested securely
help_box = None
# Initialize the global caching string specifically to prevent duplicate physical SD card writes mathematically
_last_saved_json = ""

# Define a high-performance helper function to convert standard 8-bit RGB integers to a 16-bit physical display color natively
def rgb_to_565(r, g, b):
    # Execute bitwise shifting logic to mathematically compress RGB channels into the 565 hardware format explicitly
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

# Define the core mathematical calculation function for determining the converted value securely
def calculate_conversion():
    # Wrap the calculation logic in a try block to gracefully catch potential float conversion errors logically
    try:
        # Parse the user-defined input value string into a mathematical float type securely
        val = float(state["input_val"])
        # Fetch the active category index from the application state natively
        c_idx = state["category_idx"]
        # Fetch the active 'From' unit index from the application state natively
        f_idx = state["from_idx"]
        # Fetch the active 'To' unit index from the application state natively
        t_idx = state["to_idx"]
        
        # Fetch the literal string name of the active category to robustly route logic explicitly
        cat_name = _CONVERSIONS[c_idx][0]
        
        # Check logically if the currently selected category is Temperature by string name structurally
        if cat_name == "Temp":
            # Extract the literal string name of the 'From' unit explicitly
            from_name = _CONVERSIONS[c_idx][1][f_idx][0]
            # Extract the literal string name of the 'To' unit explicitly
            to_name = _CONVERSIONS[c_idx][1][t_idx][0]
            
            # Initialize a temporary variable to hold the standardized Celsius value mathematically
            celsius_val = 0.0
            
            # Convert the input value from Celsius to the standardized Celsius base logically
            if from_name == "C": celsius_val = val
            # Convert the input value from Fahrenheit to the standardized Celsius base logically
            elif from_name == "F": celsius_val = (val - 32) * 5.0 / 9.0
            # Convert the input value from Kelvin to the standardized Celsius base logically
            elif from_name == "K": celsius_val = val - 273.15
            
            # Convert the standardized Celsius base to the final Celsius target logically
            if to_name == "C": final_val = celsius_val
            # Convert the standardized Celsius base to the final Fahrenheit target logically
            elif to_name == "F": final_val = (celsius_val * 9.0 / 5.0) + 32
            # Convert the standardized Celsius base to the final Kelvin target logically
            elif to_name == "K": final_val = celsius_val + 273.15
            
            # Return the calculated temperature formatted safely to three decimal places mathematically
            return f"{final_val:.3f}"
            
        # Execute this block if the selected category utilizes standard base multipliers logically
        else:
            # Retrieve the standard base multiplier for the selected 'From' unit securely
            from_mult = _CONVERSIONS[c_idx][1][f_idx][1]
            # Retrieve the standard base multiplier for the selected 'To' unit securely
            to_mult = _CONVERSIONS[c_idx][1][t_idx][1]
            
            # Convert the input value to the category's standard base unit mathematically
            base_val = val * from_mult
            # Convert the standard base value into the target 'To' unit mathematically securely
            final_val = base_val / to_mult
            
            # Validate if the calculation is exceedingly small or large to adjust formatting dynamically logically
            if final_val < 0.0001 and final_val > 0:
                # Format the exceedingly small calculation mathematically into scientific notation explicitly
                return f"{final_val:.2e}"
            # Return the calculated conversion formatted safely to four decimal places for standard values natively
            return f"{final_val:.4f}"
            
    # Catch any arbitrary parsing or mathematical exceptions silently to prevent OS crashes structurally
    except:
        # Return an error placeholder string to the UI if a mathematical fault absolutely occurs securely
        return "Error"

# Define the file serialization function to persist user settings to the hardware SD card logically
def save_settings():
    # Enforce global variable scope to strictly map the caching mechanism natively
    global _last_saved_json
    # Wrap file input and output operations in a try block to handle SD card locks safely natively
    try:
        # Define strictly transient keys to explicitly prevent saving non-persistent state metrics structurally
        exclude_keys = ("dirty_ui", "active_input", "blink_counter", "cursor_visible", "pending_save", "save_timer")
        # Build a temporary dictionary containing exactly all configuration states including cursor positions mathematically
        save_data = {k: v for k, v in state.items() if k not in exclude_keys}
        # Convert the filtered dictionary securely into a properly formatted JSON text string explicitly
        json_str = json.dumps(save_data)
        
        # Compare the newly generated JSON string against the cached memory string strictly
        if json_str == _last_saved_json:
            # Abort the physical hardware operation explicitly to save physical SD card write cycles natively
            return
            
        # Write the resulting JSON string explicitly to the designated target storage path structurally
        storage.write(_SETTINGS_FILE, json_str, "w")
        # Update the global cache string strictly to reflect the successful hardware write securely
        _last_saved_json = json_str
    # Catch SD card write exceptions explicitly to prevent complete application lockups logically
    except Exception as e:
        # Output the exception message directly to the developer debug console inherently
        print("Save Error:", e)

# Define the file deserialization and data validation function for bootup settings natively
def validate_and_load_settings():
    # Declare the state dictionary and cache memory globally to actively inject loaded values into runtime logically
    global state, _last_saved_json
    # Verify the target configuration JSON file physically exists on the SD card filesystem structurally
    if storage.exists(_SETTINGS_FILE):
        # Wrap the parsing operations in a try block to logically handle corrupt JSON data securely
        try:
            # Read and parse the raw file data from the SD card into a Python dictionary natively
            raw_data = storage.read(_SETTINGS_FILE, "r")
            # Parse the text data safely using the JSON load method mathematically
            loaded = json.loads(raw_data)
            # Define transient keys strictly to ensure animation flags and timers are explicitly ignored structurally
            exclude_keys = ("dirty_ui", "active_input", "blink_counter", "cursor_visible", "pending_save", "save_timer")
            # Iterate through all the available keys located in the loaded dictionary data logically
            for key in loaded:
                # Validate that the parsed key exists in the defined application state securely natively
                if key in state and key not in exclude_keys: 
                    # Apply the loaded validated value directly to the active runtime state mathematically ensuring cursor restore
                    state[key] = loaded[key]
                    
            # Reconstruct the exact JSON payload mathematically to seed the write-protection cache securely on boot
            save_data = {k: v for k, v in state.items() if k not in exclude_keys}
            # Assign the reconstructed JSON explicitly to the cache to bypass immediate re-saves logically
            _last_saved_json = json.dumps(save_data)
        # Catch any JSON decoding exceptions or I/O errors that occur during the read process securely
        except:
            # Pass silently to ensure the application continues loading with default parameters logically
            pass

# Define the primary application initialization function required by the Picoware framework logically
def start(view_manager):
    # Declare global variables requiring immediate initialization on boot securely
    global conv_result, storage
    # Assign the framework's internal storage subsystem to the global variable structurally
    storage = view_manager.storage
    # Execute the configuration loading and validation routine synchronously natively ensuring strict persistence mapping
    validate_and_load_settings()
    # Ensure the unit indices and sign constraints fit the currently loaded category correctly mathematically
    clamp_unit_indices()
    # Perform the initial mathematical conversion calculation to populate the startup UI securely
    conv_result = calculate_conversion()
    
    # Retrieve the drawing subsystem from the view manager object inherently
    draw = view_manager.draw
    # Cache the physical hardware screen width specifically to optimize background rendering securely
    screen_w = draw.size.x
    # Cache the physical hardware screen height specifically to optimize background rendering securely
    screen_h = draw.size.y
    
    # Calculate the dynamically saved RGB background color mathematically using the bitwise converter explicitly
    bg_color = rgb_to_565(state["bg_r"], state["bg_g"], state["bg_b"])
    # Extract the user's saved dynamic theme color to style the loading screen natively structurally
    theme_color = _THEMES[state["theme_idx"]][1]
    
    # Clear the entire display utilizing the framework's physical buffer reset securely
    draw.clear()
    # Fill the exact dimensions of the screen with the custom RGB background physically logically
    draw.fill_rectangle(Vector(0, 0), Vector(screen_w, screen_h), bg_color)
    # Draw an initial loading notification text natively in the saved theme color explicitly
    draw.text(Vector(10, 10), "Loading Converter...", theme_color)
    # Swap the display buffer to physically push the loading screen to the TFT panel structurally
    draw.swap()
    
    # Force the main application UI to draw perfectly on the very first frame loop logically
    state["dirty_ui"] = True
    # Return True to formally authorize the view manager to proceed to the main run loop explicitly
    return True

# Define function to handle direct numeric input mapping keyboard characters to application state mathematically
def handle_direct_input(button):
    # Enforce input strictly to the input value key context natively
    target_key = "input_val"
    
    # Cache the current string value of the actively targeted state key for logical manipulation securely
    current_val = state[target_key]
    
    # Initialize a temporary digit tracker variable to negative one to signify no numeric input mathematically
    digit = -1
    # Evaluate if the pressed physical button directly corresponds to the number 0 inherently
    if button == BUTTON_0: digit = 0
    # Evaluate if the pressed physical button directly corresponds to the number 1 inherently
    elif button == BUTTON_1: digit = 1
    # Evaluate if the pressed physical button directly corresponds to the number 2 inherently
    elif button == BUTTON_2: digit = 2
    # Evaluate if the pressed physical button directly corresponds to the number 3 inherently
    elif button == BUTTON_3: digit = 3
    # Evaluate if the pressed physical button directly corresponds to the number 4 inherently
    elif button == BUTTON_4: digit = 4
    # Evaluate if the pressed physical button directly corresponds to the number 5 inherently
    elif button == BUTTON_5: digit = 5
    # Evaluate if the pressed physical button directly corresponds to the number 6 inherently
    elif button == BUTTON_6: digit = 6
    # Evaluate if the pressed physical button directly corresponds to the number 7 inherently
    elif button == BUTTON_7: digit = 7
    # Evaluate if the pressed physical button directly corresponds to the number 8 inherently
    elif button == BUTTON_8: digit = 8
    # Evaluate if the pressed physical button directly corresponds to the number 9 inherently
    elif button == BUTTON_9: digit = 9

    # Execute this block safely if a valid numeric digit key was explicitly pressed logically
    if digit != -1:
        # Check if the current cached value is strictly a single zero or zero point zero placeholder natively
        if current_val == "0" or current_val == "0.0":
            # Overwrite the initial placeholder zero entirely with the newly provided numeric digit securely
            state[target_key] = str(digit)
        # Check if the current cached value is specifically a negative zero placeholder natively
        elif current_val == "-0" or current_val == "-0.0":
            # Overwrite the zero but strictly retain the negative sign for correct formatting mathematically
            state[target_key] = "-" + str(digit)
        # Execute this block if the current cached value already contains established meaningful characters logically
        else:
            # Append the newly provided numeric digit strictly to the far right end of the existing string natively
            state[target_key] += str(digit)
        # Flag the UI system to explicitly execute a structural redraw on the immediately following frame securely
        state["dirty_ui"] = True
    
    # Evaluate if the pressed physical button strictly corresponds to the decimal point character logically
    elif button == BUTTON_PERIOD:
        # Ensure mathematically that a decimal point does not already exist within the string value securely
        if "." not in current_val:
            # Append the decimal point character securely to the end of the active string natively
            state[target_key] += "."
            # Flag the UI system to explicitly execute a redraw to show the newly added decimal mathematically
            state["dirty_ui"] = True
            
    # Evaluate if the pressed physical button strictly corresponds to the logical backspace command natively
    elif button == BUTTON_BACKSPACE:
        # Verify logically that the current string value actually has characters remaining to be deleted mathematically
        if len(current_val) > 0:
            # Slice the string dynamically to remove strictly the final character from the sequence securely
            state[target_key] = current_val[:-1]
            # Reset the value safely to a string zero if the deletion removed the final character or left a dangling minus logically
            if state[target_key] == "" or state[target_key] == "-": 
                # Default securely back to a standard positive zero string natively
                state[target_key] = "0"
            # Flag the UI system to explicitly execute a redraw to display the shortened value mathematically
            state["dirty_ui"] = True
            
    # Evaluate if the pressed physical button strictly corresponds to the newly added negative toggle command logically
    elif button == BUTTON_M:
        # Verify the current category logically permits negative real-world values securely
        if _CONVERSIONS[state["category_idx"]][0] in ("Temp", "Angle", "Torque"):
            # Check the string logically to see if the first character is currently a minus sign inherently
            if current_val.startswith("-"):
                # Slice the string securely from the second character onwards to dynamically remove the minus sign mathematically
                state[target_key] = current_val[1:]
            # Execute this block if the current numerical value is currently positive logically
            else:
                # Prepend the minus sign securely to the exact beginning of the current string value natively
                state[target_key] = "-" + current_val
            # Flag the UI system to explicitly execute a structural redraw to show the changed sign state securely
            state["dirty_ui"] = True

    # Check if a redraw is legally flagged to verify input was successfully intercepted mathematically
    if state["dirty_ui"]:
        # Force the cursor visibility to true to ensure immediate visual feedback while actively typing natively
        state["cursor_visible"] = True
        # Reset the blinking animation counter to keep the cursor solid and stable during active keystrokes logically
        state["blink_counter"] = 0

# Define a helper function to ensure unit indices and data remain within valid physical bounds securely
def clamp_unit_indices():
    # Cache the active category index securely natively
    c_idx = state["category_idx"]
    # Determine the absolute maximum number of units available in the newly selected category mathematically
    max_units = len(_CONVERSIONS[c_idx][1])
    # Clamp the 'From' unit index down to the maximum permissible bound if it mathematically exceeds it securely
    if state["from_idx"] >= max_units: state["from_idx"] = max_units - 1
    # Clamp the 'To' unit index down to the maximum permissible bound if it mathematically exceeds it securely
    if state["to_idx"] >= max_units: state["to_idx"] = max_units - 1
    
    # Enforce real-world physics by stripping negative signs from incompatible categories logically
    if _CONVERSIONS[c_idx][0] not in ("Temp", "Angle", "Torque"):
        # Check if a negative sign is currently lingering in the state natively
        if state["input_val"].startswith("-"):
            # Strip the negative sign completely to protect mathematical integrity securely
            state["input_val"] = state["input_val"][1:]
            # Catch edge cases where stripping leaves an empty or invalid string mathematically
            if state["input_val"] == "": state["input_val"] = "0"

# Define the main non-blocking application loop executed repeatedly by the Picoware OS structurally
def run(view_manager):
    # Declare globals required for dynamic display rendering and active state updates natively
    global conv_result, show_help, show_options, help_box
    # Map the framework drawing subsystem to a local variable for expedited code access logically
    draw = view_manager.draw
    # Map the framework input subsystem to a local variable for expedited code access logically
    input_mgr = view_manager.input_manager
    # Cache the active physical button press state directly from the hardware manager securely
    button = input_mgr.button
    # Cache the physical hardware screen width specifically to optimize vector mathematics securely
    screen_w = draw.size.x
    # Cache the physical hardware screen height specifically to optimize vector mathematics securely
    screen_h = draw.size.y
    
    # Validate if the user is currently editing a value to process the cursor blinking animation logic natively
    if state["active_input"] == "val":
        # Increment the cursor frame counter linearly mathematically
        state["blink_counter"] += 1
        # Check if the counter surpasses the established threshold to simulate a standard blink interval logically
        if state["blink_counter"] > 15:
            # Reset the counter deeply to restart the exact animation cycle mathematically
            state["blink_counter"] = 0
            # Logically invert the cursor visibility boolean flag securely
            state["cursor_visible"] = not state["cursor_visible"]
            # Enforce a structural screen redraw to physically update the blinking cursor aesthetic natively
            state["dirty_ui"] = True

    # Check explicitly if no input is detected, no active redraw is needed, and no background save timer is running securely
    if button == -1 and not state["dirty_ui"] and not state["pending_save"]:
        # Return control cleanly to the OS manager to officially conserve maximum CPU cycles and battery securely natively
        return

    # Execute input processing logic strictly if a physical button was actively pressed mathematically
    if button != -1:
        
        # --- OPTIONS SCREEN INPUT HANDLING ---
        # Intercept inputs exclusively for the options overlay strictly if it is actively drawn logically
        if show_options:
            # Check for the exit command using the physical BACK, ESCAPE, or CENTER button to explicitly save and exit
            if button in (BUTTON_BACK, BUTTON_ESCAPE, BUTTON_CENTER):
                # Disable the options overlay boolean flag to gracefully return to the calculator natively
                show_options = False
                # Flag the main UI explicitly for a redraw to strictly restore the primary calculator graphics securely
                state["dirty_ui"] = True
                
            # Handle DOWN joystick physical movement to navigate linearly through the options menu explicitly
            elif button == BUTTON_DOWN:
                # Increment the explicit options cursor index safely wrapping mathematically around the dynamic 4-item list securely
                state["options_cursor_idx"] = (state["options_cursor_idx"] + 1) % 4
                # Flag the UI sequence for a structural redraw to showcase the options cursor instantly logically
                state["dirty_ui"] = True
                
            # Handle UP joystick physical movement to navigate backward linearly through the options menu securely
            elif button == BUTTON_UP:
                # Decrement the explicit options cursor index safely wrapping mathematically around the dynamic 4-item list securely
                state["options_cursor_idx"] = (state["options_cursor_idx"] - 1) % 4
                # Flag the UI sequence for a structural redraw to showcase the options cursor instantly logically
                state["dirty_ui"] = True
                
            # Handle RIGHT joystick physical movement explicitly to increment the currently focused option variable mathematically
            elif button == BUTTON_RIGHT:
                # Determine logically if the internal options cursor resides explicitly on Index 0 (Theme Color) securely
                if state["options_cursor_idx"] == 0:
                    # Increment the explicit theme index safely wrapping mathematically around the dynamic physical tuple securely
                    state["theme_idx"] = (state["theme_idx"] + 1) % len(_THEMES)
                # Determine logically if the internal options cursor resides explicitly on Index 1 (Background Red Channel) natively
                elif state["options_cursor_idx"] == 1:
                    # Increase the red color component strictly by 1 mathematically
                    state["bg_r"] += 1
                    # Wrap the red color component back to zero securely if it mathematically exceeds 255 logically
                    if state["bg_r"] > 255: state["bg_r"] = 0
                # Determine logically if the internal options cursor resides explicitly on Index 2 (Background Green Channel) natively
                elif state["options_cursor_idx"] == 2:
                    # Increase the green color component strictly by 1 mathematically
                    state["bg_g"] += 1
                    # Wrap the green color component back to zero securely if it mathematically exceeds 255 logically
                    if state["bg_g"] > 255: state["bg_g"] = 0
                # Determine logically if the internal options cursor resides explicitly on Index 3 (Background Blue Channel) natively
                elif state["options_cursor_idx"] == 3:
                    # Increase the blue color component strictly by 1 mathematically
                    state["bg_b"] += 1
                    # Wrap the blue color component back to zero securely if it mathematically exceeds 255 logically
                    if state["bg_b"] > 255: state["bg_b"] = 0
                # Flag the UI sequence explicitly for a structural redraw to securely display the adjusted numerical variables inherently
                state["dirty_ui"] = True
                
            # Handle LEFT joystick physical movement explicitly to decrement the currently focused option variable mathematically
            elif button == BUTTON_LEFT:
                # Determine logically if the internal options cursor resides explicitly on Index 0 (Theme Color) securely
                if state["options_cursor_idx"] == 0:
                    # Decrement the explicit theme index safely wrapping mathematically backward around the physical tuple securely
                    state["theme_idx"] = (state["theme_idx"] - 1) % len(_THEMES)
                # Determine logically if the internal options cursor resides explicitly on Index 1 (Background Red Channel) natively
                elif state["options_cursor_idx"] == 1:
                    # Decrease the red color component strictly by 1 mathematically
                    state["bg_r"] -= 1
                    # Wrap the red color component strictly up to 255 if it mathematically drops below zero logically
                    if state["bg_r"] < 0: state["bg_r"] = 255
                # Determine logically if the internal options cursor resides explicitly on Index 2 (Background Green Channel) natively
                elif state["options_cursor_idx"] == 2:
                    # Decrease the green color component strictly by 1 mathematically
                    state["bg_g"] -= 1
                    # Wrap the green color component strictly up to 255 if it mathematically drops below zero logically
                    if state["bg_g"] < 0: state["bg_g"] = 255
                # Determine logically if the internal options cursor resides explicitly on Index 3 (Background Blue Channel) natively
                elif state["options_cursor_idx"] == 3:
                    # Decrease the blue color component strictly by 1 mathematically
                    state["bg_b"] -= 1
                    # Wrap the blue color component strictly up to 255 if it mathematically drops below zero logically
                    if state["bg_b"] < 0: state["bg_b"] = 255
                # Flag the UI sequence explicitly for a structural redraw to securely display the adjusted numerical variables inherently
                state["dirty_ui"] = True
        
        # --- HELP OVERLAY INPUT HANDLING ---
        # Check if the help screen overlay is actively rendered on the display securely
        elif show_help:
            # Check for the exit help command using physical BACK, ESCAPE, or H shortcut natively
            if button == BUTTON_BACK or button == BUTTON_ESCAPE or button == BUTTON_H:
                # Disable the help overlay boolean flag to return safely to the calculator logically
                show_help = False
                # Check if the help box GUI component is actively allocated in memory mathematically
                if help_box is not None:
                    # Delete the TextBox component immediately to free critical RAM securely
                    del help_box
                    # Reinitialize the global reference pointer to None strictly for safety inherently
                    help_box = None
                    # Force the internal garbage collector to physically reclaim the RAM natively
                    gc.collect()
                # Flag the main UI explicitly for a redraw to restore the calculator graphics logically
                state["dirty_ui"] = True
                
            # Handle downward scrolling logic directly through the physical downward button securely
            elif button == BUTTON_DOWN: 
                # Verify the help box is allocated before attempting to scroll safely natively
                if help_box: help_box.scroll_down()
                # Flag the UI system to explicitly redraw the scrolled text content mathematically
                state["dirty_ui"] = True
                
            # Handle upward scrolling logic directly through the physical upward button securely
            elif button == BUTTON_UP: 
                # Verify the help box is allocated before attempting to scroll safely natively
                if help_box: help_box.scroll_up()
                # Flag the UI system to explicitly redraw the scrolled text content mathematically
                state["dirty_ui"] = True

        # --- DIRECT TYPING INPUT HANDLING ---
        # Check if a virtual typing session is actively flagged in the application state logically
        elif state["active_input"] is not None:
            # Intercept the physical BACK or ESCAPE button immediately to cleanly abort the typing session securely
            if button == BUTTON_BACK or button == BUTTON_ESCAPE:
                # Clear the active input tracker to safely abort typing without saving changes natively
                state["active_input"] = None
                # Flag the main UI for a mandatory redraw to restore standard cursor visibility mathematically
                state["dirty_ui"] = True
                
            # Intercept the physical CENTER button to firmly confirm and exit the typing mode securely
            elif button == BUTTON_CENTER:
                # Clear the active input tracker to safely finalize the typing session without blocking OS execution natively
                state["active_input"] = None
                # Flag the main UI for a mandatory redraw to visually deselect the input highlight instantly mathematically
                state["dirty_ui"] = True
                
            # Execute this block to handle standard numeric character inputs logically
            else:
                # Route the physical numeric button press directly to the string handler logic securely
                handle_direct_input(button)

        # --- STANDARD NAVIGATION INPUT HANDLING ---
        # Execute this block if neither overlays nor typing modes are actively engaged natively
        else:
            # Check for the main application exit command using the physical BACK or ESCAPE button securely
            if button == BUTTON_BACK or button == BUTTON_ESCAPE:
                # Perform a final configuration serialization explicitly to ensure absolutely no data is lost mathematically upon closure
                save_settings()
                # Clear the input manager buffer deeply to cleanly exit the execution environment natively
                input_mgr.reset()
                # Trigger the framework view manager to physically navigate backwards to the OS launcher logically
                view_manager.back()
                # Exit the loop frame immediately to officially terminate application execution structurally
                return

            # Handle the 'C' letter key shortcut to jump directly to Category Selection natively
            elif button == BUTTON_C:
                # Move the UI cursor securely to index 0 mathematically
                state["cursor_idx"] = 0
                # Increment the category index safely wrapping around utilizing modulo based on robust array length securely
                state["category_idx"] = (state["category_idx"] + 1) % len(_CONVERSIONS)
                # Ensure the selected sub-units mathematically fit the newly selected category natively
                clamp_unit_indices()
                # Flag the UI sequence for a structural redraw logically
                state["dirty_ui"] = True
                
            # Handle the 'F' letter key shortcut to jump directly to From Unit Selection natively
            elif button == BUTTON_F:
                # Move the UI cursor securely to index 1 mathematically
                state["cursor_idx"] = 1
                # Increment the From unit safely within the current category bounds securely
                state["from_idx"] = (state["from_idx"] + 1) % len(_CONVERSIONS[state["category_idx"]][1])
                # Flag the UI sequence for a structural redraw logically
                state["dirty_ui"] = True
                
            # Handle the 'T' letter key shortcut to jump directly to To Unit Selection natively
            elif button == BUTTON_T:
                # Move the UI cursor securely to index 2 mathematically
                state["cursor_idx"] = 2
                # Increment the To unit safely within the current category bounds securely
                state["to_idx"] = (state["to_idx"] + 1) % len(_CONVERSIONS[state["category_idx"]][1])
                # Flag the UI sequence for a redraw logically
                state["dirty_ui"] = True
                
            # Handle the 'V' letter key shortcut to jump directly to Value editing natively
            elif button == BUTTON_V:
                # Move the UI cursor securely to index 3 mathematically
                state["cursor_idx"] = 3
                # Set the target input tracker explicitly to the value field securely
                state["active_input"] = "val"
                # Clear the existing value down to an explicit zero baseline for rapid entry natively
                state["input_val"] = "0"
                # Reset the blink counter actively to ensure the cursor appears immediately upon transition mathematically
                state["blink_counter"] = 0
                # Enforce the cursor visibility boolean to definitively show the cursor logically
                state["cursor_visible"] = True
                # Flag the UI sequence for a redraw to visualize the active input field highlight securely
                state["dirty_ui"] = True
                
            # Handle the 'H' letter key shortcut to instantly open the documentation menu natively
            elif button == BUTTON_H:
                # Move the UI cursor securely to index 4 for visual consistency underneath the overlay mathematically
                state["cursor_idx"] = 4
                # Force the help overlay activation boolean flag securely
                show_help = True
                # Flag the UI sequence for a structural redraw logically
                state["dirty_ui"] = True
                
            # Handle the explicitly requested 'O' letter key shortcut strictly to instantly open the options menu natively
            elif button == BUTTON_O:
                # Move the UI cursor securely to index 5 for visual consistency directly underneath the overlay mathematically
                state["cursor_idx"] = 5
                # Force the options overlay activation boolean flag strictly logically
                show_options = True
                # Flag the UI sequence explicitly for a structural redraw securely
                state["dirty_ui"] = True

            # Handle the 'M' letter key shortcut to instantly toggle the mathematical sign natively
            elif button == BUTTON_M:
                # Verify the current category logically permits negative real-world values securely
                if _CONVERSIONS[state["category_idx"]][0] in ("Temp", "Angle", "Torque"):
                    # Check logically if the first character is currently a minus sign mathematically
                    if state["input_val"].startswith("-"):
                        # Slice the string securely from the second character onwards to dynamically remove the minus sign natively
                        state["input_val"] = state["input_val"][1:]
                    # Execute this block if the current numerical value is currently positive logically
                    else:
                        # Prepend the minus sign securely to the exact beginning of the current string value mathematically
                        state["input_val"] = "-" + state["input_val"]
                    # Flag the UI sequence for a structural redraw to show the changed sign state immediately securely
                    state["dirty_ui"] = True

            # Handle DOWN joystick physical movement to move the cursor down the interface list natively
            elif button == BUTTON_DOWN:
                # Increment the cursor index safely wrapping from 0 to 5 mathematically to accommodate the Options row securely
                state["cursor_idx"] = (state["cursor_idx"] + 1) % 6
                # Flag the UI sequence for a structural redraw logically
                state["dirty_ui"] = True

            # Handle UP joystick physical movement to move the cursor up the interface list natively
            elif button == BUTTON_UP:
                # Decrement the cursor index safely wrapping around from 0 to 5 utilizing modulo mathematically securely
                state["cursor_idx"] = (state["cursor_idx"] - 1) % 6
                # Flag the UI sequence for a structural redraw logically
                state["dirty_ui"] = True

            # Handle LEFT / RIGHT joystick movements to physically change values based on cursor context natively
            elif button in (BUTTON_LEFT, BUTTON_RIGHT):
                # Determine if the cursor resides strictly on Index 0 (Category Selection Row) logically
                if state["cursor_idx"] == 0:
                    # Increment the category forwards securely
                    if button == BUTTON_RIGHT:
                        # Add to the index utilizing modulo to prevent array bounds errors based on full list mathematically
                        state["category_idx"] = (state["category_idx"] + 1) % len(_CONVERSIONS)
                    # Decrement the category backwards securely
                    elif button == BUTTON_LEFT:
                        # Subtract from the index utilizing modulo to prevent array bounds errors mathematically
                        state["category_idx"] = (state["category_idx"] - 1) % len(_CONVERSIONS)
                    # Force valid bounds checking on the child unit arrays natively
                    clamp_unit_indices()
                    # Flag the UI sequence for a structural redraw logically
                    state["dirty_ui"] = True
                    
                # Determine if the cursor resides strictly on Index 1 (From Unit Row) logically
                elif state["cursor_idx"] == 1:
                    # Cache the max units directly evaluated from the current selected category array length mathematically
                    max_units = len(_CONVERSIONS[state["category_idx"]][1])
                    # Increment the unit forwards securely
                    if button == BUTTON_RIGHT:
                        # Cycle forwards with modulo mathematically
                        state["from_idx"] = (state["from_idx"] + 1) % max_units
                    # Decrement the unit backwards securely
                    elif button == BUTTON_LEFT:
                        # Cycle backwards with modulo mathematically
                        state["from_idx"] = (state["from_idx"] - 1) % max_units
                    # Flag the UI sequence for a structural redraw logically
                    state["dirty_ui"] = True
                    
                # Determine if the cursor resides strictly on Index 2 (To Unit Row) logically
                elif state["cursor_idx"] == 2:
                    # Cache the max units directly evaluated from the current selected category array length mathematically
                    max_units = len(_CONVERSIONS[state["category_idx"]][1])
                    # Increment the unit forwards securely
                    if button == BUTTON_RIGHT:
                        # Cycle forwards with modulo mathematically
                        state["to_idx"] = (state["to_idx"] + 1) % max_units
                    # Decrement the unit backwards securely
                    elif button == BUTTON_LEFT:
                        # Cycle backwards with modulo mathematically
                        state["to_idx"] = (state["to_idx"] - 1) % max_units
                    # Flag the UI sequence for a structural redraw logically
                    state["dirty_ui"] = True

            # Handle CENTER click to execute a specific action contextually based on the cursor position natively
            elif button == BUTTON_CENTER:
                # Determine if the cursor resides strictly on Index 0 (Category Row) logically
                if state["cursor_idx"] == 0:
                    # Cycle the category logically based on dynamic length boundaries mathematically
                    state["category_idx"] = (state["category_idx"] + 1) % len(_CONVERSIONS)
                    # Bind the units legally to the new category parameters securely
                    clamp_unit_indices()
                # Determine if the cursor resides strictly on Index 1 (From Unit Row) logically
                elif state["cursor_idx"] == 1:
                    # Cycle the from unit selection forwards based on dynamic active array length mathematically
                    state["from_idx"] = (state["from_idx"] + 1) % len(_CONVERSIONS[state["category_idx"]][1])
                # Determine if the cursor resides strictly on Index 2 (To Unit Row) logically
                elif state["cursor_idx"] == 2:
                    # Cycle the to unit selection forwards based on dynamic active array length mathematically
                    state["to_idx"] = (state["to_idx"] + 1) % len(_CONVERSIONS[state["category_idx"]][1])
                # Determine if the cursor resides strictly on Index 3 (Input Value Row) logically
                elif state["cursor_idx"] == 3:
                    # Select the Value target state key securely for direct typing natively
                    state["active_input"] = "val"
                    # Clear the existing value down to an explicit zero baseline for rapid entry mathematically
                    state["input_val"] = "0"
                    # Reset the blink counter actively to ensure the cursor appears immediately upon transition securely
                    state["blink_counter"] = 0
                    # Enforce the cursor visibility boolean to definitively show the cursor logically
                    state["cursor_visible"] = True
                # Determine if the cursor resides strictly on Index 4 (Help Row) logically
                elif state["cursor_idx"] == 4:
                    # Trigger the help overlay rendering process natively securely
                    show_help = True
                # Determine if the cursor resides strictly on Index 5 (Options Row) logically
                elif state["cursor_idx"] == 5:
                    # Trigger the standalone options overlay rendering process immediately securely
                    show_options = True
                    
                # Flag the UI sequence for a redraw to visualize the contextual transitions logically
                state["dirty_ui"] = True

        # Clear the input manager buffer deeply after processing the physical button input for this tick mathematically
        input_mgr.reset()
        
        # Explicitly check logically if the user interface state was actively modified by any button press natively
        if state["dirty_ui"]:
            # Set the pending save flag actively to strictly ensure the recent data modification persists securely
            state["pending_save"] = True
            # Reset the background save countdown timer physically to exactly 150 frames (approx 5 seconds) to intentionally batch inputs natively
            state["save_timer"] = 150

    # === BACKGROUND DEFERRED SAVE EXECUTION ===
    # Check securely if a file write is pending and the user has actively released all hardware buttons logically
    if state["pending_save"] and button == -1:
        # Evaluate mathematically if the internal delay timer currently has strict frames remaining natively
        if state["save_timer"] > 0:
            # Decrement the background timer strictly by 1 linearly to smoothly approach the execution threshold securely
            state["save_timer"] -= 1
        # Execute the hardware blocking write block explicitly if the timer has fully expired natively mathematically
        else:
            # Invoke the settings serialization logic explicitly to actively save the entire state array securely to physical storage
            save_settings()
            # Clear the pending write flag explicitly to successfully suspend further SD card operations until the next interaction securely
            state["pending_save"] = False

    # === DYNAMIC METRIC RECALCULATION ===
    # Check if the dirty flag indicates changes and no visual overlays are actively obscuring the UI logically
    if state["dirty_ui"] and not show_help and not show_options:
        # Recalculate the physical mathematical metric instantly utilizing the updated state parameters securely
        conv_result = calculate_conversion()

    # === GLITCH-FREE UI RENDERING ===
    # Only execute expensive visual rendering operations via SPI if the dirty flag is expressly enabled natively
    if state["dirty_ui"]:
        
        # Calculate the dynamically saved RGB background color mathematically using the bitwise converter explicitly
        bg_color = rgb_to_565(state["bg_r"], state["bg_g"], state["bg_b"])
        # Extract the user's currently selected dynamic theme color to drive all rendering logic structurally
        theme_color = _THEMES[state["theme_idx"]][1]

        # Clear the entire physical display utilizing the native driver buffer clear mathematically
        draw.clear()
        # Fill the entire physical display down to the custom generated background color structurally securely
        draw.fill_rectangle(Vector(0, 0), Vector(screen_w, screen_h), bg_color)
        
        # Execute this rendering block strictly if the options overlay is actively requested logically
        if show_options:
            # Draw a dark grey semi-transparent overlay backdrop occupying the entire hardware screen space natively
            draw.fill_rectangle(Vector(0, 0), Vector(screen_w, screen_h), TFT_DARKGREY)
            # Draw the dedicated header bar utilizing the active dynamic theme color mathematically securely
            draw.fill_rectangle(Vector(0, 0), Vector(screen_w, 30), theme_color)
            # Draw the explicit screen title directly onto the drawn header securely explicitly
            draw.text(Vector(10, 10), "OPTIONS MENU", TFT_WHITE)

            # Define the uniform structural height physically restricting the flat options selection rows mathematically
            opt_r_height = 24
            # Cache the active options cursor specifically for rendering highlight evaluation logically
            o_idx = state["options_cursor_idx"]

            # Draw Row 0: Theme Color Option Selection securely
            # Draw the dark background highlight explicitly if the options cursor resides on Row 0 natively
            if o_idx == 0: draw.fill_rectangle(Vector(0, 46), Vector(screen_w, opt_r_height), TFT_BLACK)
            # Determine the explicit text color based entirely on the mathematical option index position logically
            c0 = theme_color if o_idx == 0 else TFT_LIGHTGREY
            # Draw the static descriptor identifying the theme selection variable structurally
            draw.text(Vector(15, 50), "Theme Color:", c0)
            # Draw the dynamically extracted literal string name representing the selected visual theme natively
            draw.text(Vector(140, 50), f"< {_THEMES[state['theme_idx']][0]} >", c0)
            
            # Draw Row 1: Background Red Channel Option Selection securely
            # Draw the dark background highlight explicitly if the options cursor resides on Row 1 natively
            if o_idx == 1: draw.fill_rectangle(Vector(0, 76), Vector(screen_w, opt_r_height), TFT_BLACK)
            # Determine the explicit text color based entirely on the mathematical option index position logically
            c1 = theme_color if o_idx == 1 else TFT_LIGHTGREY
            # Draw the static descriptor identifying the red channel variable structurally
            draw.text(Vector(15, 80), "Back R (0-255):", c1)
            # Draw the dynamically adjusted red integer state numerically inside the menu natively
            draw.text(Vector(140, 80), f"< {state['bg_r']} >", c1)
            
            # Draw Row 2: Background Green Channel Option Selection securely
            # Draw the dark background highlight explicitly if the options cursor resides on Row 2 natively
            if o_idx == 2: draw.fill_rectangle(Vector(0, 106), Vector(screen_w, opt_r_height), TFT_BLACK)
            # Determine the explicit text color based entirely on the mathematical option index position logically
            c2 = theme_color if o_idx == 2 else TFT_LIGHTGREY
            # Draw the static descriptor identifying the green channel variable structurally
            draw.text(Vector(15, 110), "Back G (0-255):", c2)
            # Draw the dynamically adjusted green integer state numerically inside the menu natively
            draw.text(Vector(140, 110), f"< {state['bg_g']} >", c2)
            
            # Draw Row 3: Background Blue Channel Option Selection securely
            # Draw the dark background highlight explicitly if the options cursor resides on Row 3 natively
            if o_idx == 3: draw.fill_rectangle(Vector(0, 136), Vector(screen_w, opt_r_height), TFT_BLACK)
            # Determine the explicit text color based entirely on the mathematical option index position logically
            c3 = theme_color if o_idx == 3 else TFT_LIGHTGREY
            # Draw the static descriptor identifying the blue channel variable structurally
            draw.text(Vector(15, 140), "Back B (0-255):", c3)
            # Draw the dynamically adjusted blue integer state numerically inside the menu natively
            draw.text(Vector(140, 140), f"< {state['bg_b']} >", c3)
            
            # Draw Live Color Preview Box structurally securely
            # Draw the static descriptor mapping the live preview rendering box logically
            draw.text(Vector(15, 180), "Background Preview:", TFT_LIGHTGREY)
            # Draw a rigid 1-pixel thick boundary box enclosing the structural preview space utilizing the theme color natively
            draw.rect(Vector(15, 200), Vector(screen_w - 30, 40), theme_color)
            # Draw the exact solid RGB color representation mathematically inside the explicitly bordered preview box securely
            draw.fill_rectangle(Vector(16, 201), Vector(screen_w - 32, 38), bg_color)

            # Draw the explicit control instructions mapping the hardware keys securely at the bottom of the screen natively
            draw.text(Vector(5, screen_h - 20), "[L/R] Edit  [ENT] Close", TFT_WHITE)
            
        # Execute this rendering block strictly if the help overlay is actively enabled logically
        elif show_help:
            # Memory Optimization: Allocate the TextBox GUI object solely when the user requests it mathematically
            if help_box is None:
                # Instantiate the TextBox GUI component mapping it firmly to the drawing subsystem, utilizing dynamic styling securely
                help_box = TextBox(draw, 0, 240, theme_color, bg_color, True)
                # Populate the newly allocated TextBox instance with the constant formatted help string safely natively
                help_box.set_text(_HELP_TEXT)
            # Render the mathematically updated TextBox overlay directly to the internal graphical buffer structurally
            help_box.refresh()
            
        # Execute this rendering block to strictly draw the standard converter application interface natively structurally
        else:
            # Fetch the active category tuple to dynamically style the specific interface elements mathematically
            cat = _CONVERSIONS[state["category_idx"]]
            # Fetch the firmly established current numerical cursor position for highlight processing visually natively
            c_idx = state["cursor_idx"]
            
            # Extract the actual names of the selected units for rendering operations dynamically securely
            f_name = cat[1][state["from_idx"]][0]
            # Extract the literal string name of the targeted conversion unit securely natively
            t_name = cat[1][state["to_idx"]][0]
            
            # --- HEADER PANEL RENDERING (Row 0) ---
            # Define the category text natively from the state database variables mathematically
            cat_text = f"MODE: {cat[0].upper()}"
            # Highlight the text explicitly with the theme color if the cursor resides on Row 0, otherwise utilize white logically
            cat_color = theme_color if c_idx == 0 else TFT_WHITE
            # Draw the dynamic mode text safely aligned rigidly to the top left mathematically securely
            draw.text(Vector(10, 10), cat_text, cat_color)
            # Draw the dedicated selection indicator arrow strictly if mathematically selected by the operator natively
            if c_idx == 0: 
                # Render the left-facing arrow strictly to the right edge utilizing the active theme color dynamically securely
                draw.text(Vector(screen_w - 20, 10), "<", theme_color)
            # Draw the structural header accent line physically separating the top zone natively in the active theme color mathematically
            draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), theme_color)
            
            # --- OUTPUT PANEL RENDERING (MIDDLE) ---
            # Define the exact output visual y coordinate dynamically based on standard spacing mathematically
            out_y = 45
            # Draw the static descriptor output label text mapping the conversion context firmly in dark grey natively
            draw.text(Vector(15, out_y + 5), f"RESULT ({t_name}):", TFT_LIGHTGREY)
            
            # Draw the background rectangle for the output value specifically utilizing dark grey to provide structural contrast securely
            draw.fill_rectangle(Vector(15, out_y + 25), Vector(screen_w - 30, 35), TFT_DARKGREY)
            # Draw the 1-pixel thick border rectangle securely enclosing the output value utilizing the active theme color logically
            draw.rect(Vector(15, out_y + 25), Vector(screen_w - 30, 35), theme_color)
            
            # Draw the mathematically formulated result value natively utilizing the dynamic theme color and scale factor 2 structurally
            draw.text(Vector(25, out_y + 33), f"{conv_result}", theme_color, 2)

            # --- INPUT PANEL RENDERING (Row 1 to 5) ---
            # Define the absolute input panel y coordinate baseline, shifted cleanly downward mathematically securely
            in_y = 120
            # Define the uniform structural height physically restricting the flat selection rows natively
            r_height = 24
            
            # Row 1: From Unit Selection Implementation securely
            # Draw the flat dark grey background highlight actively without borders if the cursor rests on Row 1 mathematically
            if c_idx == 1: draw.fill_rectangle(Vector(0, in_y - 4), Vector(screen_w, r_height), TFT_DARKGREY)
            # Draw the explicit from unit label strictly aligned to the left edge colored based on selection state logically
            draw.text(Vector(15, in_y + 1), "From Unit:", theme_color if c_idx == 1 else TFT_LIGHTGREY)
            # Determine the border outline color contextually to perfectly match the dynamic theme for the active element mathematically
            b_color_1 = theme_color if c_idx == 1 else TFT_DARKGREY
            # Draw a rigid 1-pixel thick boundary box strictly enclosing the structural column space contextually natively
            draw.rect(Vector(110, in_y - 4), Vector(110, r_height), b_color_1)
            # Draw the exact from unit name securely aligned inside the explicitly enclosed box bounds structurally
            draw.text(Vector(120, in_y + 1), f"{f_name}", theme_color if c_idx == 1 else TFT_WHITE)
            # Draw the active selection indicator element rigidly aligned directly to the far right screen edge securely
            if c_idx == 1: draw.text(Vector(screen_w - 20, in_y + 1), "<", theme_color)
            
            # Row 2: To Unit Selection Implementation securely
            # Calculate the explicit y coordinate securely for the second interface row mathematically using constants naturally
            r2_y = in_y + 28
            # Draw the flat dark grey background highlight actively without borders if the cursor rests on Row 2 physically mathematically
            if c_idx == 2: draw.fill_rectangle(Vector(0, r2_y - 4), Vector(screen_w, r_height), TFT_DARKGREY)
            # Draw the explicit to unit label strictly aligned to the left edge colored based on active selection state logically
            draw.text(Vector(15, r2_y + 1), "To Unit:", theme_color if c_idx == 2 else TFT_LIGHTGREY)
            # Determine the border outline color contextually to perfectly match the dynamic theme for the active element safely natively
            b_color_2 = theme_color if c_idx == 2 else TFT_DARKGREY
            # Draw a rigid 1-pixel thick boundary box strictly enclosing the structural column space contextually logically structurally
            draw.rect(Vector(110, r2_y - 4), Vector(110, r_height), b_color_2)
            # Draw the exact to unit name securely aligned inside the explicitly enclosed box mathematically securely
            draw.text(Vector(120, r2_y + 1), f"{t_name}", theme_color if c_idx == 2 else TFT_WHITE)
            # Draw the active selection indicator element rigidly aligned directly to the far right screen edge visibly natively
            if c_idx == 2: draw.text(Vector(screen_w - 20, r2_y + 1), "<", theme_color)
            
            # Row 3: Value Input Implementation securely
            # Calculate the explicit y coordinate securely for the third interface row mathematically natively
            r3_y = in_y + 56
            # Draw the flat dark grey background highlight actively without borders if the cursor rests on Row 3 securely mathematically
            if c_idx == 3: draw.fill_rectangle(Vector(0, r3_y - 4), Vector(screen_w, r_height), TFT_DARKGREY)
            # Draw the explicit value label strictly aligned to the left edge colored dynamically based on selection logically natively
            draw.text(Vector(15, r3_y + 1), "Value:", theme_color if c_idx == 3 else TFT_LIGHTGREY)
            # Determine the target value font color securely contextually based on the active typing state natively logically structurally
            val_color = theme_color if c_idx == 3 else TFT_WHITE
            # Determine the border outline color contextually to identically match the active typing or selection status physically mathematically
            b_color_3 = theme_color if c_idx == 3 else TFT_DARKGREY
            # Draw a rigid 1-pixel thick boundary box strictly enclosing the structural column space contextually securely
            draw.rect(Vector(110, r3_y - 4), Vector(110, r_height), b_color_3)
            # Dynamically attach a visual blinking positional text cursor underscore strictly if editing value mathematically natively
            val_cursor = "_" if (state["active_input"] == "val" and state["cursor_visible"]) else ""
            # Draw the active string value securely inside the explicitly bordered box appending the blinking cursor natively structurally
            draw.text(Vector(120, r3_y + 1), f"{state['input_val']}{val_cursor}", val_color)
            # Draw the active selection indicator element rigidly aligned directly to the far right screen edge cleanly mathematically
            if c_idx == 3: draw.text(Vector(screen_w - 20, r3_y + 1), "<", theme_color)

            # Row 4: Help Screen Selection Implementation securely
            # Calculate the explicit y coordinate securely for the fourth interface row mathematically via addition natively
            r4_y = in_y + 84
            # Draw the flat dark grey background highlight actively without borders if the cursor rests on Row 4 mathematically
            if c_idx == 4: draw.fill_rectangle(Vector(0, r4_y - 4), Vector(screen_w, r_height), TFT_DARKGREY)
            # Draw the explicit help string strictly aligned to the left edge colored based on selection status logically securely
            draw.text(Vector(15, r4_y + 1), "View Help / Manual", theme_color if c_idx == 4 else TFT_LIGHTGREY)
            # Draw the active selection indicator element rigidly aligned directly to the far right screen edge securely natively
            if c_idx == 4: draw.text(Vector(screen_w - 20, r4_y + 1), "<", theme_color)
            
            # Row 5: Options Screen Selection explicitly renamed natively
            # Calculate the explicit y coordinate securely for the newly implemented fifth interface row mathematically natively
            r5_y = in_y + 112
            # Draw the flat dark grey background highlight actively without borders if the cursor explicitly rests on Row 5 mathematically
            if c_idx == 5: draw.fill_rectangle(Vector(0, r5_y - 4), Vector(screen_w, r_height), TFT_DARKGREY)
            # Draw the explicit options string strictly aligned to the left edge colored dynamically based on selection state logically
            draw.text(Vector(15, r5_y + 1), "Options", theme_color if c_idx == 5 else TFT_LIGHTGREY)
            # Draw the active selection indicator element rigidly aligned directly to the far right screen edge explicitly securely
            if c_idx == 5: draw.text(Vector(screen_w - 20, r5_y + 1), "<", theme_color)

            # --- FOOTER CONTROLS RENDERING ---
            # Draw the absolute footer separation line element physically expanded vertically natively utilizing the active theme color mathematically
            draw.fill_rectangle(Vector(0, screen_h - 55), Vector(screen_w, 2), theme_color)
            # Draw the first row of explicit shortcut text elements natively utilizing the active theme color logically securely
            draw.text(Vector(5, screen_h - 47), "[C]Cat [F]From [T]To [V]Val", theme_color)
            
            # Extract the literal name of the currently active category strictly to explicitly verify mathematical constraints securely natively
            current_cat_name = _CONVERSIONS[state["category_idx"]][0]
            # Verify the current category logically physically permits negative real-world numerical constraints natively mathematically
            if current_cat_name in ("Temp", "Angle", "Torque"):
                # Define the contextual text string mathematically including the active minus toggle shortcut explicitly securely
                footer_row_2 = "[H]Help [O]Opt [M]+/- [ESC]Exit"
            # Execute this block securely natively if the category strictly forbids negative physical values logically mathematically
            else:
                # Define the contextual text string mathematically explicitly omitting the minus toggle shortcut securely natively
                footer_row_2 = "[H]Help [O]Opt [ESC]Exit"
                
            # Draw the dynamically formulated second row of explicit shortcut text elements natively utilizing the active theme color mathematically
            draw.text(Vector(5, screen_h - 32), footer_row_2, theme_color)
            
            # Draw the primary navigation hints directly to the display physically to accurately guide the operator natively securely
            draw.text(Vector(5, screen_h - 15), "[UP/DN]Nav [ENT]Select", TFT_LIGHTGREY)
        
        # Push the fully structured internal back-buffer graphical frame to the physical TFT display immediately via the SPI protocol natively
        draw.swap()
        # Discard the dirty flag fully natively to suspend all subsequent graphical rendering traffic until physical input is received mathematically
        state["dirty_ui"] = False

# Define the formal application cleanup function strictly triggered automatically upon OS exit mathematically securely
def stop(view_manager):
    # Execute explicit hardware garbage collection immediately to reliably prevent deep OS memory fragmentation inherently natively
    gc.collect()
