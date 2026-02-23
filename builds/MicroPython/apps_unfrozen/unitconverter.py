# Import the const directive from MicroPython to optimize static variables at compile time
from micropython import const
# Import the Vector class to define precise X and Y display coordinates for UI elements
from picoware.system.vector import Vector
# Import UI color constants to colorize the application interface
from picoware.system.colors import (
    # Import orange color for highlights
    TFT_ORANGE, 
    # Import dark grey color for backgrounds
    TFT_DARKGREY, 
    # Import light grey color for secondary text
    TFT_LIGHTGREY, 
    # Import white color for primary text
    TFT_WHITE, 
    # Import black color for deep backgrounds
    TFT_BLACK,
    # Import blue color for material accents
    TFT_BLUE, 
    # Import yellow color for active cursors
    TFT_YELLOW, 
    # Import cyan color for active inputs and shortcuts
    TFT_CYAN, 
    # Import green color for standard modes
    TFT_GREEN, 
    # Import red color for warnings
    TFT_RED,
)
# Import hardware button constants explicitly mapped to the Picocalc physical keypad
from picoware.system.buttons import (
    # Import standard navigational and control buttons
    BUTTON_BACK, BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, BUTTON_CENTER,
    # Import number keys required strictly for typing values into the fields
    BUTTON_0, BUTTON_1, BUTTON_2, BUTTON_3, BUTTON_4, 
    BUTTON_5, BUTTON_6, BUTTON_7, BUTTON_8, BUTTON_9,
    # Import the period and backspace keys for numeric editing
    BUTTON_PERIOD, BUTTON_BACKSPACE,
    # Import explicitly mapped letter shortcut keys and the ESCAPE key for exiting
    BUTTON_C, BUTTON_F, BUTTON_T, BUTTON_V, BUTTON_H, BUTTON_ESCAPE
)
# Import the TextBox GUI component to manage and render the scrollable help overlay
from picoware.gui.textbox import TextBox
# Import the json module to parse and serialize the application's configuration state
import json
# Import the garbage collection module to manually free unreferenced memory on the Pico
import gc

# Define the absolute file path for saving the settings JSON on the SD card
_SETTINGS_FILE = "/picoware/apps/unit_converter_settings.json" 

# Define the expanded categories and their respective units with base conversion multipliers
_CONVERSIONS = (
    # Define the Length category with base unit as meters (m). Included microns and thou for machining.
    ("Length", (("um", 0.000001), ("thou", 0.0000254), ("mm", 0.001), ("cm", 0.01), ("m", 1.0), ("in", 0.0254), ("ft", 0.3048), ("yd", 0.9144))),
    # Define the Weight category with base unit as kilograms (kg)
    ("Weight", (("mg", 0.000001), ("g", 0.001), ("kg", 1.0), ("oz", 0.0283495), ("lb", 0.453592))),
    # Define the Volume category with base unit as Liters (L)
    ("Volume", (("ml", 0.001), ("L", 1.0), ("gal", 3.78541), ("fl oz", 0.0295735))),
    # Define the Area category with base unit as square meters (m2). Included sq in for shop materials.
    ("Area", (("cm2", 0.0001), ("m2", 1.0), ("sq in", 0.00064516), ("sq ft", 0.092903))),
    # Define the Speed category with base unit as meters per second (m/s). Included mm/s for 3D printing.
    ("Speed", (("mm/s", 0.001), ("m/s", 1.0), ("km/h", 0.277778), ("mph", 0.44704))),
    # Define the Pressure category with base unit as Pascals (Pa). Essential for air compressors and pneumatics.
    ("Press", (("Pa", 1.0), ("kPa", 1000.0), ("bar", 100000.0), ("psi", 6894.76))),
    # Define the Torque category with base unit as Newton-meters (Nm). Essential for fasteners and servos.
    ("Torque", (("Nmm", 0.001), ("Nm", 1.0), ("in-lb", 0.1129848), ("ft-lb", 1.355818))),
    # Define the Power category with base unit as Watts (W). Essential for spindles and electronics.
    ("Power", (("W", 1.0), ("kW", 1000.0), ("hp", 745.7))),
    # Define the Angle category with base unit as Degrees. Essential for setups and indexing.
    ("Angle", (("deg", 1.0), ("rad", 57.2957795))),
    # Define the Temperature category (multipliers not used directly, requires custom logic)
    ("Temp", (("C", 0), ("F", 0), ("K", 0)))
)

# Define the updated help text string containing the new shop categories and adjusted layout
_HELP_TEXT = "UNIT CONVERTER\nVersion 1.2\n----------------\nCATEGORIES:\n- Len, Area, Vol\n- Wgt, Spd, Press\n- Torq, Pwr, Ang\n- Temp\n\nSHORTCUTS:\n[C] Cycle Cat\n[F] Edit From\n[T] Edit To\n[V] Edit Value\n[H] Open Help\n[ESC] Exit App\n\nCONTROLS:\n[UP/DN]: Cursor\n[L/R]: Select\n[CENTER]: Confirm\n[BACK]: Exit"

# Define the baseline default configuration dictionary to ensure predictable behavior upon boot
DEFAULT_STATE = {
    # Set the default category index (0 = Length)
    "category_idx": 0,
    # Set the default From unit index
    "from_idx": 0,
    # Set the default To unit index
    "to_idx": 1,
    # Set the default input value string
    "input_val": "1.0",
    # Initialize the cursor index to 0 (Category Selection)
    "cursor_idx": 0,
    # Initialize the dirty UI flag to force an initial render
    "dirty_ui": True
}

# Clone the default state dictionary into the active runtime variable to isolate defaults
state = DEFAULT_STATE.copy()
# Initialize the active input tracker to None to signify the typing mode is currently closed
state["active_input"] = None

# Initialize the global conversion result string to zero
conv_result = "0.0"
# Initialize the global storage manager reference to None
storage = None
# Initialize the boolean flag determining if the help screen overlay is actively rendered
show_help = False
# Initialize the global help box UI instance to None to save memory until requested
help_box = None

# Define the core mathematical calculation function for determining the converted value
def calculate_conversion():
    # Wrap the calculation logic in a try block to gracefully catch potential float conversion errors
    try:
        # Parse the user-defined input value string into a mathematical float type
        val = float(state["input_val"])
        # Fetch the active category index from the application state
        c_idx = state["category_idx"]
        # Fetch the active 'From' unit index from the application state
        f_idx = state["from_idx"]
        # Fetch the active 'To' unit index from the application state
        t_idx = state["to_idx"]
        
        # Fetch the literal string name of the active category to robustly route logic
        cat_name = _CONVERSIONS[c_idx][0]
        
        # Check logically if the currently selected category is Temperature by string name
        if cat_name == "Temp":
            # Extract the literal string name of the 'From' unit
            from_name = _CONVERSIONS[c_idx][1][f_idx][0]
            # Extract the literal string name of the 'To' unit
            to_name = _CONVERSIONS[c_idx][1][t_idx][0]
            
            # Initialize a temporary variable to hold the standardized Celsius value
            celsius_val = 0.0
            
            # Convert the input value from Celsius to the standardized Celsius base
            if from_name == "C": celsius_val = val
            # Convert the input value from Fahrenheit to the standardized Celsius base
            elif from_name == "F": celsius_val = (val - 32) * 5.0 / 9.0
            # Convert the input value from Kelvin to the standardized Celsius base
            elif from_name == "K": celsius_val = val - 273.15
            
            # Convert the standardized Celsius base to the final Celsius target
            if to_name == "C": final_val = celsius_val
            # Convert the standardized Celsius base to the final Fahrenheit target
            elif to_name == "F": final_val = (celsius_val * 9.0 / 5.0) + 32
            # Convert the standardized Celsius base to the final Kelvin target
            elif to_name == "K": final_val = celsius_val + 273.15
            
            # Return the calculated temperature formatted safely to three decimal places
            return f"{final_val:.3f}"
            
        # Execute this block if the selected category utilizes standard base multipliers
        else:
            # Retrieve the standard base multiplier for the selected 'From' unit
            from_mult = _CONVERSIONS[c_idx][1][f_idx][1]
            # Retrieve the standard base multiplier for the selected 'To' unit
            to_mult = _CONVERSIONS[c_idx][1][t_idx][1]
            
            # Convert the input value to the category's standard base unit
            base_val = val * from_mult
            # Convert the standard base value into the target 'To' unit mathematically
            final_val = base_val / to_mult
            
            # Validate if the calculation is exceedingly small or large to adjust formatting dynamically
            if final_val < 0.0001 and final_val > 0:
                # Format the exceedingly small calculation mathematically into scientific notation
                return f"{final_val:.2e}"
            # Return the calculated conversion formatted safely to four decimal places for standard values
            return f"{final_val:.4f}"
            
    # Catch any arbitrary parsing or mathematical exceptions silently to prevent OS crashes
    except:
        # Return an error placeholder string to the UI if a mathematical fault absolutely occurs
        return "Error"

# Define the file serialization function to persist user settings to the hardware SD card
def save_settings():
    # Wrap file input and output operations in a try block to handle SD card locks safely
    try:
        # Build a temporary dictionary containing only persistable keys, removing transient runtime flags
        save_data = {k: v for k, v in state.items() if k not in ("dirty_ui", "active_input", "cursor_idx")}
        # Convert the filtered dictionary securely into a properly formatted JSON text string
        json_str = json.dumps(save_data)
        # Write the resulting JSON string explicitly to the designated target storage path
        storage.write(_SETTINGS_FILE, json_str, "w")
    # Catch SD card write exceptions explicitly to prevent complete application lockups
    except Exception as e:
        # Output the exception message directly to the developer debug console
        print("Save Error:", e)

# Define the file deserialization and data validation function for bootup settings
def validate_and_load_settings():
    # Declare the state dictionary as global to actively inject loaded values into runtime
    global state
    # Verify the target configuration JSON file physically exists on the SD card filesystem
    if storage.exists(_SETTINGS_FILE):
        # Wrap the parsing operations in a try block to logically handle corrupt JSON data
        try:
            # Read and parse the raw file data from the SD card into a Python dictionary
            loaded = json.loads(storage.read(_SETTINGS_FILE, "r"))
            # Iterate through all the available keys located in the loaded dictionary data
            for key in loaded:
                # Validate that the parsed key exists in the defined application state
                if key in state and key not in ("dirty_ui", "active_input", "cursor_idx"): 
                    # Apply the loaded validated value directly to the active runtime state
                    state[key] = loaded[key]
        # Catch any JSON decoding exceptions or I/O errors that occur during the read process
        except:
            # Pass silently to ensure the application continues loading with default parameters
            pass

# Define the primary application initialization function required by the Picoware framework
def start(view_manager):
    # Declare global variables requiring immediate initialization on boot
    global conv_result, storage
    # Assign the framework's internal storage subsystem to the global variable
    storage = view_manager.storage
    # Execute the configuration loading and validation routine synchronously
    validate_and_load_settings()
    # Ensure the unit indices fit the currently loaded category correctly to prevent boot crashes
    clamp_unit_indices()
    # Perform the initial mathematical conversion calculation to populate the startup UI
    conv_result = calculate_conversion()
    
    # Retrieve the drawing subsystem from the view manager object
    draw = view_manager.draw
    # Clear the entire display to a pure black background to prevent artifacting
    draw.clear()
    # Draw an initial loading notification text to confirm the display driver is responsive
    draw.text(Vector(10, 10), "Loading Converter...", TFT_GREEN)
    # Swap the display buffer to physically push the loading screen to the TFT panel
    draw.swap()
    
    # Force the main application UI to draw perfectly on the very first frame loop
    state["dirty_ui"] = True
    # Return True to formally authorize the view manager to proceed to the main run loop
    return True

# Define function to handle direct numeric input mapping keyboard characters to application state
def handle_direct_input(button):
    # Enforce input strictly to the input value key context
    target_key = "input_val"
    
    # Cache the current string value of the actively targeted state key for logical manipulation
    current_val = state[target_key]
    
    # Initialize a temporary digit tracker variable to negative one to signify no numeric input
    digit = -1
    # Evaluate if the pressed physical button directly corresponds to the number 0
    if button == BUTTON_0: digit = 0
    # Evaluate if the pressed physical button directly corresponds to the number 1
    elif button == BUTTON_1: digit = 1
    # Evaluate if the pressed physical button directly corresponds to the number 2
    elif button == BUTTON_2: digit = 2
    # Evaluate if the pressed physical button directly corresponds to the number 3
    elif button == BUTTON_3: digit = 3
    # Evaluate if the pressed physical button directly corresponds to the number 4
    elif button == BUTTON_4: digit = 4
    # Evaluate if the pressed physical button directly corresponds to the number 5
    elif button == BUTTON_5: digit = 5
    # Evaluate if the pressed physical button directly corresponds to the number 6
    elif button == BUTTON_6: digit = 6
    # Evaluate if the pressed physical button directly corresponds to the number 7
    elif button == BUTTON_7: digit = 7
    # Evaluate if the pressed physical button directly corresponds to the number 8
    elif button == BUTTON_8: digit = 8
    # Evaluate if the pressed physical button directly corresponds to the number 9
    elif button == BUTTON_9: digit = 9

    # Execute this block safely if a valid numeric digit key was explicitly pressed
    if digit != -1:
        # Check if the current cached value is strictly a single zero or zero point zero placeholder
        if current_val == "0" or current_val == "0.0":
            # Overwrite the initial placeholder zero entirely with the newly provided numeric digit
            state[target_key] = str(digit)
        # Execute this block if the current cached value already contains established meaningful characters
        else:
            # Append the newly provided numeric digit strictly to the far right end of the existing string
            state[target_key] += str(digit)
        # Flag the UI system to explicitly execute a structural redraw on the immediately following frame
        state["dirty_ui"] = True
    
    # Evaluate if the pressed physical button strictly corresponds to the decimal point character
    elif button == BUTTON_PERIOD:
        # Ensure mathematically that a decimal point does not already exist within the string value
        if "." not in current_val:
            # Append the decimal point character securely to the end of the active string
            state[target_key] += "."
            # Flag the UI system to explicitly execute a redraw to show the newly added decimal
            state["dirty_ui"] = True
            
    # Evaluate if the pressed physical button strictly corresponds to the logical backspace command
    elif button == BUTTON_BACKSPACE:
        # Verify logically that the current string value actually has characters remaining to be deleted
        if len(current_val) > 0:
            # Slice the string dynamically to remove strictly the final character from the sequence
            state[target_key] = current_val[:-1]
            # Reset the value safely to a string zero if the deletion removed the absolute final character
            if state[target_key] == "": state[target_key] = "0"
            # Flag the UI system to explicitly execute a redraw to display the shortened value
            state["dirty_ui"] = True

# Define a helper function to ensure unit indices remain within valid bounds when categories change
def clamp_unit_indices():
    # Cache the active category index securely
    c_idx = state["category_idx"]
    # Determine the absolute maximum number of units available in the newly selected category
    max_units = len(_CONVERSIONS[c_idx][1])
    # Clamp the 'From' unit index down to the maximum permissible bound if it mathematically exceeds it
    if state["from_idx"] >= max_units: state["from_idx"] = max_units - 1
    # Clamp the 'To' unit index down to the maximum permissible bound if it mathematically exceeds it
    if state["to_idx"] >= max_units: state["to_idx"] = max_units - 1

# Define the main non-blocking application loop executed repeatedly by the Picoware OS
def run(view_manager):
    # Declare globals required for dynamic display rendering and active state updates
    global conv_result, show_help, help_box
    # Map the framework drawing subsystem to a local variable for expedited code access
    draw = view_manager.draw
    # Map the framework input subsystem to a local variable for expedited code access
    input_mgr = view_manager.input_manager
    # Cache the active physical button press state directly from the hardware manager
    button = input_mgr.button
    # Cache the physical hardware screen width specifically to optimize vector mathematics
    screen_w = draw.size.x
    # Cache the physical hardware screen height specifically to optimize vector mathematics
    screen_h = draw.size.y
    
    # Check if no input is detected and no UI redraw is currently pending
    if button == -1 and not state["dirty_ui"]:
        # Return control cleanly to the OS manager to conserve CPU cycles
        return

    # Execute input processing logic strictly if a physical button was actively pressed
    if button != -1:
        
        # --- HELP OVERLAY INPUT HANDLING ---
        # Check if the help screen overlay is actively rendered on the display
        if show_help:
            # Check for the exit help command using physical BACK, ESCAPE, or H shortcut
            if button == BUTTON_BACK or button == BUTTON_ESCAPE or button == BUTTON_H:
                # Disable the help overlay boolean flag to return safely to the calculator
                show_help = False
                # Check if the help box GUI component is actively allocated in memory
                if help_box is not None:
                    # Delete the TextBox component immediately to free critical RAM
                    del help_box
                    # Reinitialize the global reference pointer to None strictly for safety
                    help_box = None
                    # Force the internal garbage collector to physically reclaim the RAM
                    gc.collect()
                # Flag the main UI explicitly for a redraw to restore the calculator graphics
                state["dirty_ui"] = True
                
            # Handle downward scrolling logic directly through the physical downward button
            elif button == BUTTON_DOWN: 
                # Verify the help box is allocated before attempting to scroll safely
                if help_box: help_box.scroll_down()
                # Flag the UI system to explicitly redraw the scrolled text content
                state["dirty_ui"] = True
                
            # Handle upward scrolling logic directly through the physical upward button
            elif button == BUTTON_UP: 
                # Verify the help box is allocated before attempting to scroll safely
                if help_box: help_box.scroll_up()
                # Flag the UI system to explicitly redraw the scrolled text content
                state["dirty_ui"] = True

        # --- DIRECT TYPING INPUT HANDLING ---
        # Check if a virtual typing session is actively flagged in the application state
        elif state["active_input"] is not None:
            # Intercept the physical BACK or ESCAPE button immediately to cleanly abort the typing session
            if button == BUTTON_BACK or button == BUTTON_ESCAPE:
                # Clear the active input tracker to safely abort typing without saving changes
                state["active_input"] = None
                # Flag the main UI for a mandatory redraw to restore standard cursor visibility
                state["dirty_ui"] = True
                
            # Intercept the physical CENTER button to firmly confirm and exit the typing mode
            elif button == BUTTON_CENTER:
                # Clear the active input tracker to safely finalize the typing session
                state["active_input"] = None
                # Serialize the explicitly confirmed numeric parameters safely to the SD card
                save_settings()
                # Flag the main UI for a mandatory redraw to visually deselect the input highlight
                state["dirty_ui"] = True
                
            # Execute this block to handle standard numeric character inputs
            else:
                # Route the physical numeric button press directly to the string handler logic
                handle_direct_input(button)

        # --- STANDARD NAVIGATION INPUT HANDLING ---
        # Execute this block if neither the help screen nor typing modes are actively engaged
        else:
            # Check for the main application exit command using the physical BACK or ESCAPE button
            if button == BUTTON_BACK or button == BUTTON_ESCAPE:
                # Perform a final configuration serialization to ensure absolutely no data is lost
                save_settings()
                # Clear the input manager buffer deeply to cleanly exit the execution environment
                input_mgr.reset()
                # Trigger the framework view manager to physically navigate backwards to the OS launcher
                view_manager.back()
                # Exit the loop frame immediately to officially terminate application execution
                return

            # Handle the 'C' letter key shortcut to jump directly to Category Selection
            elif button == BUTTON_C:
                # Move the UI cursor securely to index 0
                state["cursor_idx"] = 0
                # Increment the category index safely wrapping around utilizing modulo based on robust array length
                state["category_idx"] = (state["category_idx"] + 1) % len(_CONVERSIONS)
                # Ensure the selected sub-units mathematically fit the newly selected category
                clamp_unit_indices()
                # Flag the UI sequence for a structural redraw
                state["dirty_ui"] = True
                
            # Handle the 'F' letter key shortcut to jump directly to From Unit Selection
            elif button == BUTTON_F:
                # Move the UI cursor securely to index 1
                state["cursor_idx"] = 1
                # Increment the From unit safely within the current category bounds
                state["from_idx"] = (state["from_idx"] + 1) % len(_CONVERSIONS[state["category_idx"]][1])
                # Flag the UI sequence for a structural redraw
                state["dirty_ui"] = True
                
            # Handle the 'T' letter key shortcut to jump directly to To Unit Selection
            elif button == BUTTON_T:
                # Move the UI cursor securely to index 2
                state["cursor_idx"] = 2
                # Increment the To unit safely within the current category bounds
                state["to_idx"] = (state["to_idx"] + 1) % len(_CONVERSIONS[state["category_idx"]][1])
                # Flag the UI sequence for a redraw
                state["dirty_ui"] = True
                
            # Handle the 'V' letter key shortcut to jump directly to Value editing
            elif button == BUTTON_V:
                # Move the UI cursor securely to index 3
                state["cursor_idx"] = 3
                # Set the target input tracker explicitly to the value field
                state["active_input"] = "val"
                # Flag the UI sequence for a redraw to visualize the active input field highlight
                state["dirty_ui"] = True
                
            # Handle the 'H' letter key shortcut to instantly open the documentation menu
            elif button == BUTTON_H:
                # Move the UI cursor securely to index 4 for visual consistency underneath the overlay
                state["cursor_idx"] = 4
                # Force the help overlay activation boolean flag
                show_help = True
                # Flag the UI sequence for a structural redraw
                state["dirty_ui"] = True

            # Handle DOWN joystick physical movement to move the cursor down the interface list
            elif button == BUTTON_DOWN:
                # Increment the cursor index safely wrapping from 0 to 4 utilizing modulo arithmetic
                state["cursor_idx"] = (state["cursor_idx"] + 1) % 5
                # Flag the UI sequence for a structural redraw
                state["dirty_ui"] = True

            # Handle UP joystick physical movement to move the cursor up the interface list
            elif button == BUTTON_UP:
                # Decrement the cursor index safely wrapping around from 0 to 4 utilizing modulo
                state["cursor_idx"] = (state["cursor_idx"] - 1) % 5
                # Flag the UI sequence for a structural redraw
                state["dirty_ui"] = True

            # Handle LEFT / RIGHT joystick movements to physically change values based on cursor context
            elif button in (BUTTON_LEFT, BUTTON_RIGHT):
                # Determine if the cursor resides strictly on Index 0 (Category Selection Row)
                if state["cursor_idx"] == 0:
                    # Increment the category forwards
                    if button == BUTTON_RIGHT:
                        # Add to the index utilizing modulo to prevent array bounds errors based on full list
                        state["category_idx"] = (state["category_idx"] + 1) % len(_CONVERSIONS)
                    # Decrement the category backwards
                    elif button == BUTTON_LEFT:
                        # Subtract from the index utilizing modulo to prevent array bounds errors
                        state["category_idx"] = (state["category_idx"] - 1) % len(_CONVERSIONS)
                    # Force valid bounds checking on the child unit arrays
                    clamp_unit_indices()
                    # Flag the UI sequence for a structural redraw
                    state["dirty_ui"] = True
                    
                # Determine if the cursor resides strictly on Index 1 (From Unit Row)
                elif state["cursor_idx"] == 1:
                    # Cache the max units directly evaluated from the current selected category array length
                    max_units = len(_CONVERSIONS[state["category_idx"]][1])
                    # Increment the unit forwards
                    if button == BUTTON_RIGHT:
                        # Cycle forwards with modulo
                        state["from_idx"] = (state["from_idx"] + 1) % max_units
                    # Decrement the unit backwards
                    elif button == BUTTON_LEFT:
                        # Cycle backwards with modulo
                        state["from_idx"] = (state["from_idx"] - 1) % max_units
                    # Flag the UI sequence for a structural redraw
                    state["dirty_ui"] = True
                    
                # Determine if the cursor resides strictly on Index 2 (To Unit Row)
                elif state["cursor_idx"] == 2:
                    # Cache the max units directly evaluated from the current selected category array length
                    max_units = len(_CONVERSIONS[state["category_idx"]][1])
                    # Increment the unit forwards
                    if button == BUTTON_RIGHT:
                        # Cycle forwards with modulo
                        state["to_idx"] = (state["to_idx"] + 1) % max_units
                    # Decrement the unit backwards
                    elif button == BUTTON_LEFT:
                        # Cycle backwards with modulo
                        state["to_idx"] = (state["to_idx"] - 1) % max_units
                    # Flag the UI sequence for a structural redraw
                    state["dirty_ui"] = True

            # Handle CENTER click to execute a specific action contextually based on the cursor position
            elif button == BUTTON_CENTER:
                # Determine if the cursor resides strictly on Index 0 (Category Row)
                if state["cursor_idx"] == 0:
                    # Cycle the category logically based on dynamic length boundaries
                    state["category_idx"] = (state["category_idx"] + 1) % len(_CONVERSIONS)
                    # Bind the units legally to the new category parameters
                    clamp_unit_indices()
                # Determine if the cursor resides strictly on Index 1 (From Unit Row)
                elif state["cursor_idx"] == 1:
                    # Cycle the from unit selection forwards based on dynamic active array length
                    state["from_idx"] = (state["from_idx"] + 1) % len(_CONVERSIONS[state["category_idx"]][1])
                # Determine if the cursor resides strictly on Index 2 (To Unit Row)
                elif state["cursor_idx"] == 2:
                    # Cycle the to unit selection forwards based on dynamic active array length
                    state["to_idx"] = (state["to_idx"] + 1) % len(_CONVERSIONS[state["category_idx"]][1])
                # Determine if the cursor resides strictly on Index 3 (Input Value Row)
                elif state["cursor_idx"] == 3:
                    # Select the Value target state key securely for direct typing
                    state["active_input"] = "val"
                # Determine if the cursor resides strictly on Index 4 (Help Row)
                elif state["cursor_idx"] == 4:
                    # Trigger the help overlay rendering process
                    show_help = True
                    
                # Flag the UI sequence for a redraw to visualize the contextual transitions
                state["dirty_ui"] = True

        # Clear the input manager buffer deeply after processing the physical button input for this tick
        input_mgr.reset()

    # === DYNAMIC METRIC RECALCULATION ===
    # Check if the dirty flag indicates changes and the help screen is not currently obscuring the UI
    if state["dirty_ui"] and not show_help:
        # Recalculate the physical mathematical metric instantly utilizing the updated state parameters
        conv_result = calculate_conversion()

    # === GLITCH-FREE UI RENDERING ===
    # Only execute expensive visual rendering operations via SPI if the dirty flag is expressly enabled
    if state["dirty_ui"]:
        # Clear the entire physical display using the validated clear method to prevent graphic corruption
        draw.clear()
        
        # Execute this rendering block strictly if the help overlay is actively enabled
        if show_help:
            # Memory Optimization: Allocate the TextBox GUI object solely when the user requests it
            if help_box is None:
                # Instantiate the TextBox GUI component mapping it firmly to the drawing subsystem
                help_box = TextBox(draw, 0, 240, TFT_WHITE, TFT_BLACK, True)
                # Populate the newly allocated TextBox instance with the constant formatted help string
                help_box.set_text(_HELP_TEXT)
            # Render the mathematically updated TextBox overlay directly to the internal graphical buffer
            help_box.refresh()
            
        # Execute this rendering block to strictly draw the standard converter application interface
        else:
            # Fill the entire background with pure dark grey to construct the segmented panel aesthetic
            draw.fill_rectangle(Vector(0, 0), Vector(screen_w, screen_h), TFT_DARKGREY)
            
            # Fetch the active category tuple to dynamically style the specific interface elements
            cat = _CONVERSIONS[state["category_idx"]]
            # Fetch the firmly established current numerical cursor position for highlight processing
            c_idx = state["cursor_idx"]
            
            # Extract the actual names of the selected units for drawing
            f_name = cat[1][state["from_idx"]][0]
            # Extract the literal string name of the target unit
            t_name = cat[1][state["to_idx"]][0]
            
            # --- HEADER PANEL RENDERING (Row 0) ---
            # Draw the header background utilizing pure black
            draw.fill_rectangle(Vector(0, 0), Vector(screen_w, 30), TFT_BLACK)
            # Define the category text natively from the state database
            cat_text = f"MODE: {cat[0].upper()}"
            # Highlight the text yellow explicitly if the cursor resides on Row 0, otherwise utilize green
            cat_color = TFT_YELLOW if c_idx == 0 else TFT_GREEN
            # Draw the dynamic mode text safely aligned to the top left
            draw.text(Vector(10, 10), cat_text, cat_color)
            # Draw the dedicated selection indicator arrow if mathematically selected
            if c_idx == 0: 
                # Render the left-facing arrow utilizing bright yellow
                draw.text(Vector(screen_w - 20, 10), "<", TFT_YELLOW)
            # Draw the structural header accent line separating the top zone
            draw.fill_rectangle(Vector(0, 30), Vector(screen_w, 2), TFT_LIGHTGREY)
            
            # --- OUTPUT PANEL RENDERING (MIDDLE) ---
            # Define the exact output visual y coordinate
            out_y = 45
            # Draw the output background box utilizing pure black to completely eliminate pixel noise
            draw.fill_round_rectangle(Vector(10, out_y), Vector(screen_w - 20, 60), 5, TFT_BLACK)
            # Draw the contrasting white output border around the calculation result
            draw.rect(Vector(10, out_y), Vector(screen_w - 20, 60), TFT_WHITE)
            # Draw the static descriptor output label text mapping the conversion context
            draw.text(Vector(20, out_y + 10), f"RESULT ({t_name}):", TFT_LIGHTGREY)
            # Draw the mathematically formulated result value natively in bright green
            draw.text(Vector(20, out_y + 35), f"{conv_result}", TFT_GREEN)

            # --- INPUT PANEL RENDERING (Row 1 to 4) ---
            # Define the absolute input panel y coordinate baseline
            in_y = 120
            
            # Row 1: From Unit Selection Implementation
            # Draw the explicit from unit label colored dynamically
            draw.text(Vector(15, in_y), "From Unit:", TFT_YELLOW if c_idx == 1 else TFT_LIGHTGREY)
            # Determine the targeted element color contextually
            f_color = TFT_YELLOW if c_idx == 1 else TFT_WHITE
            # Draw the exact from unit name utilizing conditional color rules
            draw.text(Vector(120, in_y), f"< {f_name} >", f_color)
            # Draw the active selection indicator element
            if c_idx == 1: 
                # Render the left-facing arrow
                draw.text(Vector(screen_w - 20, in_y), "<", TFT_YELLOW)
            
            # Row 2: To Unit Selection Implementation
            # Draw the explicit to unit label colored dynamically
            draw.text(Vector(15, in_y + 30), "To Unit:", TFT_YELLOW if c_idx == 2 else TFT_LIGHTGREY)
            # Determine the targeted element color contextually
            t_color = TFT_YELLOW if c_idx == 2 else TFT_WHITE
            # Draw the exact to unit name utilizing conditional color rules
            draw.text(Vector(120, in_y + 30), f"< {t_name} >", t_color)
            # Draw the active selection indicator element
            if c_idx == 2: 
                # Render the left-facing arrow
                draw.text(Vector(screen_w - 20, in_y + 30), "<", TFT_YELLOW)
            
            # Row 3: Value Input Implementation
            # Draw the explicit value label colored dynamically
            draw.text(Vector(15, in_y + 60), "Value:", TFT_YELLOW if c_idx == 3 else TFT_LIGHTGREY)
            # Determine the target value color contextually
            val_color = TFT_YELLOW if c_idx == 3 else TFT_WHITE
            # Highlight utilizing cyan securely if actively typing
            if state["active_input"] == "val": val_color = TFT_CYAN
            # Dynamically attach a visual positional text cursor underscore strictly if editing value
            val_cursor = "_" if state["active_input"] == "val" else ""
            # Draw the active string value appending cursor seamlessly
            draw.text(Vector(120, in_y + 60), f"{state['input_val']}{val_cursor}", val_color)
            # Draw the active selection indicator element
            if c_idx == 3: 
                # Render the left-facing arrow
                draw.text(Vector(screen_w - 20, in_y + 60), "<", TFT_YELLOW)

            # Row 4: Help Screen Selection Implementation
            # Draw the explicit help string colored dynamically
            draw.text(Vector(15, in_y + 90), "View Help / Manual", TFT_YELLOW if c_idx == 4 else TFT_LIGHTGREY)
            # Draw the active selection indicator element
            if c_idx == 4: 
                # Render the left-facing arrow
                draw.text(Vector(screen_w - 20, in_y + 90), "<", TFT_YELLOW)

            # --- FOOTER CONTROLS RENDERING ---
            # Draw the absolute footer separation line element
            draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), TFT_LIGHTGREY)
            # Draw the explicit shortcut text elements utilizing letters securely mapped to the UI
            draw.text(Vector(5, screen_h - 32), "[C]Cat [F]From [T]To [V]Val", TFT_CYAN)
            # Draw the primary navigation hints to guide the operator accurately
            draw.text(Vector(5, screen_h - 15), "[UP/DN] Move Cursor | [ENT] Edit", TFT_WHITE)
        
        # Push the fully structured internal back-buffer frame to the physical TFT display immediately via SPI
        draw.swap()
        # Discard the dirty flag fully to suspend all subsequent rendering traffic until input is specifically received
        state["dirty_ui"] = False

# Define the formal application cleanup function triggered automatically upon OS exit
def stop(view_manager):
    # Execute explicit garbage collection immediately to prevent deep OS memory fragmentation
    gc.collect()
