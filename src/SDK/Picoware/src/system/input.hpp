#pragma once
#include <cstdint>

class Input
{
public:
    Input();  // Constructor initializes the input system
    ~Input(); // Destructor
    //
    // Singleton access
    static Input *getInstance() { return instance; }
    //
    int getLastButton() const noexcept { return this->lastButton; } // Get the last button pressed
    //
    bool isHeld(uint8_t duration = 3); // Check if a button is held for a specified duration
    bool isPressed();                  // Check if a button is currently pressed
    void reset();                      // Reset the input state
    char read();                       // Read a key (blocking - waits for key if none available)
    char readNonBlocking();            // Read a key (non-blocking - returns 0 if no key available)

private:
    float debounce;    // Debounce time for button presses
    float elapsedTime; // Time elapsed that a button has been pressed
    int lastButton;    // Last button pressed
    bool wasPressed;   // Flag to indicate if a button was pressed
    //
    static Input *instance; // Singleton instance
    //
    int charToButton(char key) const noexcept; // Convert character to button definition
    static void onKeyAvailableCallback();      // Static callback function for C interface
    void processInput();                       // Process input when callback is triggered
};