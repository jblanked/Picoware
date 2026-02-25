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
    # Import explicitly requested letter shortcut keys and the ESCAPE key for exiting
    BUTTON_S, BUTTON_M, BUTTON_D, BUTTON_V, BUTTON_R, BUTTON_H, BUTTON_ESCAPE
)
# Import the TextBox GUI component to manage and render the scrollable help overlay
from picoware.gui.textbox import TextBox
# Import the math module to access the Pi constant required for the cutting speed formulas
import math
# Import the json module to parse and serialize the application's configuration state
import json
# Import the garbage collection module to manually free unreferenced memory on the Pico
import gc

# Define the absolute file path for saving the settings JSON on the SD card
_SETTINGS_FILE = "/picoware/apps/drill_pro_settings.json" 

# Define the material database as a tuple of tuples to drastically reduce heap memory usage
_MATERIALS = (
    # Define Aluminium configuration (Name, Vc, Color)
    ("Aluminium", 45, TFT_WHITE),
    # Define Brass configuration (Name, Vc, Color)
    ("Brass",     35, TFT_YELLOW),
    # Define Wood configuration (Name, Vc, Color)
    ("Wood",      28, TFT_ORANGE),
    # Define Steel St37 configuration (Name, Vc, Color)
    ("Steel St37", 22, TFT_GREEN),
    # Define Plastic configuration (Name, Vc, Color)
    ("Plastic",   18, TFT_CYAN),
    # Define Stainless configuration (Name, Vc, Color)
    ("Stainless", 12, TFT_BLUE),
    # Define Custom configuration (Name, Vc, Color)
    ("Custom",    0,  TFT_RED)
)

# Define the detailed help text string containing the updated independent row layout and ESC instruction
_HELP_TEXT = "DRILL SPEED PRO\nVersion 1.7\n----------------\nABOUT:\nCalculates safe spindle RPM.\n\nMODES:\n- DRILL: Standard calc.\n- SINK: Forces Dia to 20mm.\n\nSHORTCUTS:\n[S] Key: Toggle Mode\n[M] Key: Cycle Material\n[D] Key: Edit Diameter\n[V] Key: Edit Custom Vc\n[R] Key: Edit Max RPM\n[H] Key: Open Help\n[ESC] Key: Exit App\n\nCONTROLS:\n[UP/DN]: Move Cursor\n[L/R]: Change Mode/Material\n[CENTER]: Select / Confirm\n[BACK]/[ESC]: Cancel / Exit\n\nMade by Slasher006"

# Define the baseline default configuration dictionary to ensure predictable behavior upon boot
DEFAULT_STATE = {
    # Set the default material index
    "mat_index": 3,
    # Set the default custom cutting speed
    "custom_vc": "30",
    # Set the default drill diameter
    "diameter_mm": "5.0",
    # Set the default maximum machine RPM limit
    "max_rpm": "3500",
    # Set the default operational mode boolean to False
    "mode_sink": False,
    # Initialize the cursor index to 0 (Mode Selection)
    "cursor_idx": 0,
    # Initialize the dirty UI flag to force an initial render
    "dirty_ui": True
}

# Clone the default state dictionary into the active runtime variable to isolate defaults
state = DEFAULT_STATE.copy()
# Initialize the active input tracker to None to signify the typing mode is currently closed
state["active_input"] = None

# Initialize the global RPM result calculation string to zero
rpm_result = "0"
# Initialize the boolean flag tracking if the calculated RPM exceeds the user limit
is_capped = False
# Initialize the global storage manager reference to None
storage = None
# Initialize the boolean flag determining if the help screen overlay is actively rendered
show_help = False
# Initialize the global help box UI instance to None to save memory until requested
help_box = None

# Define the core mathematical calculation function for determining the target RPM
def calculate_rpm_metric():
    # Declare the is_capped variable as global to modify the UI warning state from within the function
    global is_capped
    # Wrap the calculation logic in a try block to gracefully catch potential float conversion errors
    try:
        # Check if the countersink mode flag is currently active in the application state
        if state["mode_sink"]:
            # Override the operational diameter strictly to 20.0mm for countersink safety
            d = 20.0
        # Execute this block if standard standard drilling mode is currently active
        else:
            # Parse the user-defined diameter state string into a mathematical float type
            d = float(state["diameter_mm"])

        # Fetch the active material tuple from the optimized memory database using the current index
        mat = _MATERIALS[state["mat_index"]]
        # Parse custom Vc if the Custom material is active, otherwise utilize the preset Vc
        vc = float(state["custom_vc"]) if mat[0] == "Custom" else mat[1]
        # Parse the user-defined maximum machine RPM string safely into a mathematical float type
        limit = float(state["max_rpm"])
        
        # Abort the mathematical calculation and return zero if any physical parameters are invalid
        if d <= 0 or vc <= 0: return "0"
        
        # Execute the standard metric machining RPM formula: (Cutting Speed * 1000) / (Pi * Diameter)
        rpm = (vc * 1000) / (math.pi * d)
        
        # Evaluate if the newly calculated RPM mathematically exceeds the user-defined physical limit
        if rpm > limit:
            # Enable the limit warning flag to trigger the red GUI text warning
            is_capped = True
            # Return the limit cast as an integer and subsequently converted to a display string
            return str(int(limit))
        # Execute this block if the calculated RPM falls securely within the defined safe bounds
        else:
            # Disable the limit warning flag for the GUI rendering
            is_capped = False
            # Return the dynamically calculated RPM cast as an integer and converted to a string
            return str(int(rpm))
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
    global rpm_result, storage
    # Assign the framework's internal storage subsystem to the global variable
    storage = view_manager.storage
    # Execute the configuration loading and validation routine synchronously
    validate_and_load_settings()
    # Perform the initial mathematical RPM calculation to populate the startup UI
    rpm_result = calculate_rpm_metric()
    
    # Retrieve the drawing subsystem from the view manager object
    draw = view_manager.draw
    # Clear the entire display to a pure black background to prevent artifacting
    draw.clear()
    # Draw an initial loading notification text to confirm the display driver is responsive
    draw.text(Vector(10, 10), "Loading Drill Pro...", TFT_GREEN)
    # Swap the display buffer to physically push the loading screen to the TFT panel
    draw.swap()
    
    # Force the main application UI to draw perfectly on the very first frame loop
    state["dirty_ui"] = True
    # Return True to formally authorize the view manager to proceed to the main run loop
    return True

# Define function to handle direct numeric input mapping keyboard characters to application state
def handle_direct_input(button):
    # Default the target state key to diameter modification
    target_key = "diameter_mm"
    # Reassign the target key to custom cutting speed if the virtual VC mode is actively selected
    if state["active_input"] == "vc": target_key = "custom_vc"
    # Reassign the target key to maximum machine RPM if the virtual RPM mode is actively selected
    if state["active_input"] == "rpm": target_key = "max_rpm"
    
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

# Define the main non-blocking application loop executed repeatedly by the Picoware OS
def run(view_manager):
    # Declare globals required for dynamic display rendering and active state updates
    global rpm_result, is_capped, show_help, help_box
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

            # Handle the 'S' letter key shortcut to jump directly to Mode Selection
            elif button == BUTTON_S:
                # Move the UI cursor securely to index 0
                state["cursor_idx"] = 0
                # Immediately toggle the sink mode status boolean for rapid user workflow
                state["mode_sink"] = not state["mode_sink"]
                # Flag the UI sequence for a structural redraw
                state["dirty_ui"] = True
                
            # Handle the 'M' letter key shortcut to jump directly to Material Selection
            elif button == BUTTON_M:
                # Move the UI cursor securely to index 1
                state["cursor_idx"] = 1
                # Increment the material structure forwards
                state["mat_index"] = (state["mat_index"] + 1) % len(_MATERIALS)
                # Flag the UI sequence for a structural redraw
                state["dirty_ui"] = True
                
            # Handle the 'D' letter key shortcut to jump directly to Diameter editing
            elif button == BUTTON_D:
                # Move the UI cursor securely to index 2
                state["cursor_idx"] = 2
                # Set the target input tracker to the Diameter field explicitly
                state["active_input"] = "dia"
                # Flag the UI sequence for a redraw to visualize the active input field highlight
                state["dirty_ui"] = True
                
            # Handle the 'V' letter key shortcut to jump directly to Vc editing
            elif button == BUTTON_V:
                # Move the UI cursor securely to index 3
                state["cursor_idx"] = 3
                # Auto-switch the material to Custom mode to ensure validity
                state["mat_index"] = 6
                # Set the target input tracker to the Custom VC field explicitly
                state["active_input"] = "vc"
                # Flag the UI sequence for a redraw to visualize the active input field highlight
                state["dirty_ui"] = True
                
            # Handle the 'R' letter key shortcut to jump directly to Max RPM editing
            elif button == BUTTON_R:
                # Move the UI cursor securely to index 4
                state["cursor_idx"] = 4
                # Set the target input tracker specifically to the Maximum RPM field
                state["active_input"] = "rpm"
                # Flag the UI sequence for a redraw to visualize the active input field highlight
                state["dirty_ui"] = True
                
            # Handle the 'H' letter key shortcut to instantly open the documentation menu
            elif button == BUTTON_H:
                # Move the UI cursor securely to index 5 for visual consistency underneath the overlay
                state["cursor_idx"] = 5
                # Force the help overlay activation boolean flag
                show_help = True
                # Flag the UI sequence for a structural redraw
                state["dirty_ui"] = True

            # Handle DOWN joystick physical movement to move the cursor down the interface list
            elif button == BUTTON_DOWN:
                # Increment the cursor index safely wrapping from 0 to 5 utilizing modulo arithmetic
                state["cursor_idx"] = (state["cursor_idx"] + 1) % 6
                # Flag the UI sequence for a structural redraw
                state["dirty_ui"] = True

            # Handle UP joystick physical movement to move the cursor up the interface list
            elif button == BUTTON_UP:
                # Decrement the cursor index safely wrapping around from 0 to 5 utilizing modulo
                state["cursor_idx"] = (state["cursor_idx"] - 1) % 6
                # Flag the UI sequence for a structural redraw
                state["dirty_ui"] = True

            # Handle LEFT / RIGHT joystick movements to physically change values based on cursor context
            elif button in (BUTTON_LEFT, BUTTON_RIGHT):
                # Determine if the cursor resides strictly on Index 0 (Mode Selection Row)
                if state["cursor_idx"] == 0:
                    # Toggle the boolean operational mode logically
                    state["mode_sink"] = not state["mode_sink"]
                    # Flag the UI sequence for a structural redraw
                    state["dirty_ui"] = True
                # Determine if the cursor resides strictly on Index 1 (Material Selection Row)
                elif state["cursor_idx"] == 1:
                    # Increment the material structure forwards
                    if button == BUTTON_RIGHT:
                        # Add to the index utilizing modulo to prevent array bounds errors
                        state["mat_index"] = (state["mat_index"] + 1) % len(_MATERIALS)
                    # Decrement the material structure backwards
                    elif button == BUTTON_LEFT:
                        # Subtract from the index utilizing modulo to prevent array bounds errors
                        state["mat_index"] = (state["mat_index"] - 1) % len(_MATERIALS)
                    # Flag the UI sequence for a structural redraw
                    state["dirty_ui"] = True

            # Handle CENTER click to execute a specific action contextually based on the cursor position
            elif button == BUTTON_CENTER:
                # Determine if the cursor resides strictly on Index 0 (Mode Row)
                if state["cursor_idx"] == 0:
                    # Toggle the boolean operational mode logically
                    state["mode_sink"] = not state["mode_sink"]
                # Determine if the cursor resides strictly on Index 1 (Material Row)
                elif state["cursor_idx"] == 1:
                    # Cycle the material selection forwards
                    state["mat_index"] = (state["mat_index"] + 1) % len(_MATERIALS)
                # Determine if the cursor resides strictly on Index 2 (Diameter Row)
                elif state["cursor_idx"] == 2:
                    # Select the standard Diameter target state key securely
                    state["active_input"] = "dia"
                # Determine if the cursor resides strictly on Index 3 (Vc Row)
                elif state["cursor_idx"] == 3:
                    # Auto-switch the material to Custom mode to ensure validity
                    state["mat_index"] = 6
                    # Select the Custom VC target state key securely
                    state["active_input"] = "vc"
                # Determine if the cursor resides strictly on Index 4 (Max RPM Row)
                elif state["cursor_idx"] == 4:
                    # Select the Maximum RPM target state key securely
                    state["active_input"] = "rpm"
                # Determine if the cursor resides strictly on Index 5 (Help Row)
                elif state["cursor_idx"] == 5:
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
        rpm_result = calculate_rpm_metric()

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
            
        # Execute this rendering block to strictly draw the standard calculator application interface
        else:
            # Fill the entire background with pure dark grey to construct the segmented panel aesthetic
            draw.fill_rectangle(Vector(0, 0), Vector(screen_w, screen_h), TFT_DARKGREY)
            # Fetch the active material configuration tuple to dynamically style the specific interface colors
            mat = _MATERIALS[state["mat_index"]]
            # Fetch the firmly established current numerical cursor position for highlight processing
            c_idx = state["cursor_idx"]
            
            # --- HEADER PANEL RENDERING (Row 0) ---
            # Draw the header background utilizing pure black
            draw.fill_rectangle(Vector(0, 0), Vector(screen_w, 30), TFT_BLACK)
            # Define the mode text utilizing ternary logical string evaluation
            mode_text = "MODE: COUNTERSINK" if state["mode_sink"] else "MODE: DRILLING"
            # Highlight the text yellow explicitly if the cursor resides on Row 0, otherwise utilize mode colors
            mode_color = TFT_YELLOW if c_idx == 0 else (TFT_ORANGE if state["mode_sink"] else TFT_GREEN)
            # Draw the dynamic mode text safely aligned to the top left
            draw.text(Vector(10, 10), mode_text, mode_color)
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
            # Draw the static descriptor output label text
            draw.text(Vector(20, out_y + 10), "TARGET RPM:", TFT_LIGHTGREY)
            # Determine the exact result color utilizing the physical cap safety boolean
            res_color = TFT_RED if is_capped else TFT_GREEN
            # Draw the mathematically formulated result value integer
            draw.text(Vector(20, out_y + 35), f"{rpm_result}", res_color)
            # Check the active limit cap status continuously
            if is_capped: 
                # Draw the physical limit warning to safely alert the human operator
                draw.text(Vector(120, out_y + 35), "(LIMIT)", TFT_RED)

            # --- INPUT PANEL RENDERING (Row 1 to 5) ---
            # Define the absolute input panel y coordinate baseline
            in_y = 120
            
            # Row 1: Material Selection Implementation
            # Draw the explicit material label colored dynamically
            draw.text(Vector(15, in_y), "Material:", TFT_YELLOW if c_idx == 1 else TFT_LIGHTGREY)
            # Determine the targeted material color contextually
            mat_color = TFT_YELLOW if c_idx == 1 else mat[2]
            # Draw the exact material name utilizing conditional color rules
            draw.text(Vector(100, in_y), f"< {mat[0]} >", mat_color)
            # Draw the active selection indicator element
            if c_idx == 1: 
                # Render the left-facing arrow
                draw.text(Vector(screen_w - 20, in_y), "<", TFT_YELLOW)
            
            # Row 2: Diameter Selection Implementation
            # Draw the explicit diameter label colored dynamically
            draw.text(Vector(15, in_y + 30), "Diameter:", TFT_YELLOW if c_idx == 2 else TFT_LIGHTGREY)
            # Determine the target diameter color contextually based on the mode override
            dia_color = TFT_YELLOW if c_idx == 2 else TFT_WHITE
            # Dim the diameter element completely if visually inactive
            if state["mode_sink"]: 
                # Apply the dimmed color hex
                dia_color = TFT_LIGHTGREY 
            # Highlight utilizing cyan securely if actively typing
            if state["active_input"] == "dia": dia_color = TFT_CYAN
            # Dynamically attach a visual positional text cursor underscore strictly if editing diameter
            dia_cursor = "_" if state["active_input"] == "dia" else ""
            # Draw the active diameter value appending cursor and unit strings
            draw.text(Vector(100, in_y + 30), f"{state['diameter_mm']}{dia_cursor} mm", dia_color)
            # Draw the active selection indicator element
            if c_idx == 2: 
                # Render the left-facing arrow
                draw.text(Vector(screen_w - 20, in_y + 30), "<", TFT_YELLOW)
            
            # Row 3: VC Selection Implementation
            # Draw the explicit VC label colored dynamically
            draw.text(Vector(15, in_y + 60), "Vc (m/min):", TFT_YELLOW if c_idx == 3 else TFT_LIGHTGREY)
            # Determine the accurate custom VC color logic
            vc_color = TFT_YELLOW if c_idx == 3 else TFT_WHITE
            # Dim the VC element completely if it is not Custom
            if mat[0] != "Custom": 
                # Apply the dimmed color hex
                vc_color = TFT_LIGHTGREY
            # Highlight utilizing cyan securely if actively typing
            if state["active_input"] == "vc": vc_color = TFT_CYAN
            # Extract the mathematically active VC value
            vc_val = state["custom_vc"] if mat[0] == "Custom" else mat[1]
            # Dynamically attach a visual positional text cursor underscore strictly if editing VC
            vc_cursor = "_" if state["active_input"] == "vc" else ""
            # Draw the specific VC value conditionally appending the positional cursor
            draw.text(Vector(100, in_y + 60), f"{vc_val}{vc_cursor}", vc_color)
            # Draw the active selection indicator element
            if c_idx == 3: 
                # Render the left-facing arrow
                draw.text(Vector(screen_w - 20, in_y + 60), "<", TFT_YELLOW)

            # Row 4: Max RPM Selection Implementation
            # Draw the explicit RPM label colored dynamically
            draw.text(Vector(15, in_y + 90), "Max Spindle:", TFT_YELLOW if c_idx == 4 else TFT_LIGHTGREY)
            # Determine the target RPM color contextually
            rpm_color = TFT_YELLOW if c_idx == 4 else TFT_WHITE
            # Highlight utilizing cyan securely if actively typing
            if state["active_input"] == "rpm": rpm_color = TFT_CYAN
            # Dynamically attach a visual positional text cursor underscore strictly if editing RPM
            rpm_cursor = "_" if state["active_input"] == "rpm" else ""
            # Draw the accurate RPM value string conditionally appending the positional cursor
            draw.text(Vector(100, in_y + 90), f"{state['max_rpm']}{rpm_cursor}", rpm_color)
            # Draw the active selection indicator element
            if c_idx == 4: 
                # Render the left-facing arrow
                draw.text(Vector(screen_w - 20, in_y + 90), "<", TFT_YELLOW)
            
            # Row 5: Help Screen Selection Implementation
            # Draw the explicit help string colored dynamically
            draw.text(Vector(15, in_y + 120), "View Help / Manual", TFT_YELLOW if c_idx == 5 else TFT_LIGHTGREY)
            # Draw the active selection indicator element
            if c_idx == 5: 
                # Render the left-facing arrow
                draw.text(Vector(screen_w - 20, in_y + 120), "<", TFT_YELLOW)

            # --- FOOTER CONTROLS RENDERING ---
            # Draw the absolute footer separation line element
            draw.fill_rectangle(Vector(0, screen_h - 40), Vector(screen_w, 2), TFT_LIGHTGREY)
            # Draw the explicit shortcut text elements utilizing letters securely
            draw.text(Vector(5, screen_h - 32), "[S]Mode [M]Mat [D]Dia [R]RPM", TFT_CYAN)
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
