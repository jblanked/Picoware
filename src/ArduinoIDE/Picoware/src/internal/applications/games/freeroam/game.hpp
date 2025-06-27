#pragma once
#include "../../../../internal/system/colors.hpp"
#include "../../../../internal/system/view.hpp"
#include "../../../../internal/system/view_manager.hpp"
#include "../../../../internal/applications/games/freeroam/general.hpp"
#include "../../../../internal/applications/games/freeroam/player.hpp"
#include "../../../../internal/engine/engine.hpp"
using namespace Picoware;
class FreeRoamGame
{
private:
    int currentLevelIndex = 0;                                   // Current level index
    std::unique_ptr<GameEngine> engine;                          // Engine instance
    bool inputHeld = false;                                      // Flag to check if input is held
    bool isGameRunning = false;                                  // Flag to check if the game is running
    uint8_t lastInput = -1;                                      // Last input key pressed
    const char *levelNames[3] = {"Tutorial", "First", "Second"}; // Level names for display
    std::unique_ptr<Player> player;                              // Player instance
    ToggleState soundToggle = ToggleOn;                          // sound toggle state
    const int totalLevels = 3;                                   // Total number of levels available
    ToggleState vibrationToggle = ToggleOn;                      // vibration toggle state
    //
    int atoi(const char *nptr) { return (int)strtol(nptr, NULL, 10); } // convert string to integer
    void debounceInput();                                              // debounce input to prevent multiple actions from a single press
    void inputManager();                                               // manage input for the game, called from updateInput
    void switchToNextLevel();                                          // switch to the next level in the game
    void switchToLevel(int levelIndex);                                // switch to a specific level by index

public:
    FreeRoamGame(ViewManager *viewManager);
    ~FreeRoamGame();

    void *appContext = nullptr;            // Pointer to the application context for accessing app-specific functionality
    bool shouldReturnToMenu = false;       // Flag to signal return to menu
    bool shouldDebounce = false;           // Make shouldDebounce public for Player access
    ViewManager *viewManagerRef = nullptr; // Reference to the view dispatcher for navigation
    //
    void endGame();                                               // end the game and return to the submenu
    Board getBoard() const { return viewManagerRef->getBoard(); } // Get the board configuration
    uint8_t getCurrentInput() const { return lastInput; }         // Get the last input key pressed
    GameEngine *getEngine() const { return engine.get(); }        // Get the game engine instance
    Draw *getDraw() const { return viewManagerRef->getDraw(); }   // Get the Draw instance
    bool isActive() const { return shouldReturnToMenu == false; } // Check if the game is active
    bool isRunning() const { return isGameRunning; }              // Check if the game engine is running
    void resetInput() { lastInput = -1; }                         // Reset input after processing
    bool startGame();                                             // start the actual game
    void updateDraw();                                            // update and draw the game
    void updateInput(uint8_t key);                                // update input for the game
    void updateSoundToggle();                                     // update sound toggle state
    void updateVibrationToggle();                                 // update vibration toggle state
};
