
#pragma once
#include <functional>
#include <stdint.h>
#include <string>
#include <Arduino.h>
#include "../../internal/gui/draw.hpp"
#include "../../internal/gui/vector.hpp"
#include "../../internal/system/buttons.hpp"
#include "../../internal/system/colors.hpp"
#include "../../internal/system/input_manager.hpp"

namespace Picoware
{
    class Keyboard
    {
    public:
        Keyboard(
            Draw *draw,
            InputManager *inputManager,
            uint16_t textColor = TFT_BLACK,
            uint16_t backgroundColor = TFT_WHITE,
            uint16_t selectedColor = TFT_BLUE,
            std::function<void(const String &)> onSaveCallback = nullptr);
        ~Keyboard();

        // Getters
        uint16_t getBackgroundColor() const noexcept { return backgroundColor; }   // Returns the background color
        uint8_t getCurrentKey() const noexcept { return currentKey; }              // Returns the currently pressed key
        uint16_t getSelectedColor() const noexcept { return selectedColor; }       // Returns the selected color
        uint16_t getTextColor() const noexcept { return textColor; }               // Returns the text color
        String getResponse() const noexcept { return response; }                   // Returns the response string
        uint8_t getKeyboardWidth() const noexcept { return display->getSize().x; } // Returns the keyboard width/width of the display

        // Setters
        void setSaveCallback(std::function<void(const String &)> callback)
        {
            onSaveCallback = callback;
        } // Sets the save callback function

        // Main functions
        void reset();                                             // Resets the keyboard state
        void run();                                               // Runs the input manager, handles input, and draws the keyboard
        void setResponse(const String &text) { response = text; } // Sets the response string

    private:
        void drawKey(uint8_t row, uint8_t col, bool isSelected); // Draws a specific key on the keyboard
        void drawKeyboard();                                     // Draws the entire keyboard
        void drawTextbox();                                      // Draws the text box that displays the current saved response
        void handleInput();                                      // Handles directional input and key selection
        void processKeyPress();                                  // Processes the currently selected key press
        std::function<void(const String &)> onSaveCallback;      // Callback function for saving the response
        bool justStopped;                                        // Flag to indicate if the keyboard was just stopped

        // Core components
        Draw *display;              // Pointer to the Draw class for rendering the keyboard
        InputManager *inputManager; // Pointer to the InputManager class for handling input events

        // Input state
        int dpadInput;      // Input from the directional pad
        uint8_t currentKey; // Currently pressed key (BUTTON_A, BUTTON_B, etc.)

        // Keyboard state
        bool isShiftPressed; // Flag to indicate if the Shift key is pressed
        bool isCapsLockOn;   // Flag to indicate if Caps Lock is on
        uint8_t cursorRow;   // Current row position of the cursor
        uint8_t cursorCol;   // Current column position of the cursor

        // Timing
        unsigned long lastInputTime; // Last time input was processed
        unsigned long inputDelay;    // Delay between input processing

        // Visual properties
        uint16_t textColor;       // Text color for the keyboard
        uint16_t backgroundColor; // Background color for the keyboard
        uint16_t selectedColor;   // Color for the selected key

        // Data
        String response; // Response string for the keyboard input

        /* Keyboard layout
         * 1 2 3 4 5 6 7 8 9 0 - = BCK
         * Q W E R T Y U I O P [ ] \ CLR
         * Caps A S D F G H J K L ; ' Enter
         * Shift Z X C V B N M , . / Shift
         *        Space              Save
         */
    };
}