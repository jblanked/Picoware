#include "../../../../internal/applications/games/freeroam/game.hpp"
#include "../../../../internal/applications/games/freeroam/sprite.hpp"

FreeRoamGame::FreeRoamGame(ViewManager *viewManager)
{
    this->viewManagerRef = viewManager;
}

FreeRoamGame::~FreeRoamGame()
{
    // also nothing to do anymore since I moved the view/timer to the app
}

void FreeRoamGame::debounceInput()
{
    static uint8_t debounceCounter = 0;
    if (shouldDebounce)
    {
        lastInput = -1;
        debounceCounter++;
        if (debounceCounter < 2) // Reduced from 4 to 2 for faster menu response
        {
            return;
        }
        debounceCounter = 0;
        shouldDebounce = false;
        inputHeld = false;
    }
}

void FreeRoamGame::endGame()
{
    shouldReturnToMenu = true;
    isGameRunning = false;

    this->updateSoundToggle();
    this->updateVibrationToggle();

    if (engine)
    {
        engine->stop();
    }
}

void FreeRoamGame::inputManager()
{
    static int inputHeldCounter = 0;

    // Track input held state
    if (lastInput != -1)
    {
        inputHeldCounter++;
        if (inputHeldCounter > 10)
        {
            this->inputHeld = true;
        }
    }
    else
    {
        inputHeldCounter = 0;
        this->inputHeld = false;
    }

    // Handle input for all views, but don't debounce when game engine is running
    if (player && (player->getCurrentMainView() == GameViewGameLocal || player->getCurrentMainView() == GameViewGameOnline))
    {
        // When game is running, completely skip debouncing to avoid interference
        if (!isGameRunning)
        {
            // Only debounce if game is not actually running (e.g., during startup)
            if (lastInput == InputKeyBack)
            {
                debounceInput();
            }
        }
        // When game is running, let all inputs pass through without any debouncing
    }
    else
    {
        // For menu views, use fast debouncing (much faster than original but prevents menu skipping)
        // Only debounce when shouldDebounce is explicitly set, skip the inputHeld check for speed
        if (shouldDebounce)
        {
            debounceInput();
        }
    }

    // Pass input to player for processing
    if (player)
    {
        player->setInputKey(lastInput);
        player->processInput();
    }
}

bool FreeRoamGame::startGame()
{
    auto draw = getDraw();

    draw->fillScreen(ColorWhite);
    draw->text(Vector(0, 10), "Initializing game...", ColorBlack);

    if (isGameRunning || engine)
    {
        // Game already running, skipping start
        return true;
    }

    auto board = getBoard();

    // Create the game instance with 3rd person perspective
    auto game = std::make_unique<Game>("Free Roam", Vector(128, 64), draw, viewManagerRef->getInputManager(), ColorBlack, ColorWhite, CAMERA_THIRD_PERSON);
    if (!game)
    {
        // Failed to create Game object
        return false;
    }

    // Create the player instance if it doesn't exist
    if (!player)
    {
        player = std::make_unique<Player>(board);
        if (!player)
        {
            // Failed to create Player object
            return false;
        }
    }

    // set sound/vibration toggle states
    player->setSoundToggle(soundToggle);
    player->setVibrationToggle(vibrationToggle);

    draw->fillScreen(ColorWhite);
    draw->text(Vector(0, 10), "Adding levels and player...", ColorBlack);

    // add levels and player to the game
    std::unique_ptr<Level> level1 = std::make_unique<Level>("Tutorial", Vector(128, 64), game.get());
    std::unique_ptr<Level> level2 = std::make_unique<Level>("First", Vector(128, 64), game.get());
    std::unique_ptr<Level> level3 = std::make_unique<Level>("Second", Vector(128, 64), game.get());

    // we'll clear ourselves and swap afterwards too
    level1->setClearAllowed(false);
    level2->setClearAllowed(false);
    level3->setClearAllowed(false);

    level1->entity_add(player.get());
    level2->entity_add(player.get());
    level3->entity_add(player.get());

    // add some 3D sprites
    std::unique_ptr<Entity> tutorialGuard1 = std::make_unique<Sprite>(board, "Tutorial Guard 1", Vector(3, 7), SPRITE_3D_HUMANOID, 1.7f, 1.0f, M_PI / 4, Vector(9, 7));
    std::unique_ptr<Entity> tutorialGuard2 = std::make_unique<Sprite>(board, "Tutorial Guard 2", Vector(6, 2), SPRITE_3D_HUMANOID, 1.7f, 1.0f, M_PI / 4, Vector(1, 2));
    level1->entity_add(tutorialGuard1.release());
    level1->entity_add(tutorialGuard2.release());

    game->level_add(level1.release());
    game->level_add(level2.release());
    game->level_add(level3.release());

    this->engine = std::make_unique<GameEngine>(game.release(), 240);
    if (!this->engine)
    {
        // Failed to create GameEngine
        return false;
    }

    draw->fillScreen(ColorWhite);
    draw->text(Vector(0, 10), "Starting game engine...", ColorBlack);

    isGameRunning = true; // Set the flag to indicate game is running
    return true;
}

void FreeRoamGame::switchToLevel(int levelIndex)
{
    if (!isGameRunning || !engine || !engine->getGame())
        return;

    // Ensure the level index is within bounds
    if (levelIndex < 0 || levelIndex >= totalLevels)
    {
        return;
    }

    currentLevelIndex = levelIndex;

    // Switch to the specified level using the engine's game instance
    engine->getGame()->level_switch(currentLevelIndex);

    // Force the Player to update its currentDynamicMap on next render
    if (player)
    {
        player->forceMapReload();
    }
}

void FreeRoamGame::switchToNextLevel()
{
    if (!isGameRunning || !engine || !engine->getGame())
    {
        return;
    }

    // Cycle to next level
    currentLevelIndex = (currentLevelIndex + 1) % totalLevels;

    // Switch to the new level using the engine's game instance
    engine->getGame()->level_switch(currentLevelIndex);

    // Force the Player to update its currentDynamicMap on next render
    if (player)
    {
        player->forceMapReload();
    }
}

void FreeRoamGame::updateDraw()
{
    // Initialize player if not already done
    if (!player)
    {
        player = std::make_unique<Player>(getBoard());
        if (player)
        {
            player->setFreeRoamGame(this);
            player->setSoundToggle(soundToggle);
            player->setVibrationToggle(vibrationToggle);
        }
    }

    // Let the player handle all drawing
    if (player)
    {
        player->drawCurrentView(getDraw());

        if (player->shouldLeaveGame())
        {
            this->soundToggle = player->getSoundToggle();
            this->vibrationToggle = player->getVibrationToggle();
            this->endGame(); // End the game if the player wants to leave
        }
    }
}

void FreeRoamGame::updateInput(uint8_t key)
{
    this->lastInput = key;

    // Only run inputManager when not in an active game to avoid input conflicts
    if (!(player && player->getCurrentMainView() == GameViewGameLocal && this->isGameRunning))
    {
        this->inputManager();
    }
}

void FreeRoamGame::updateSoundToggle()
{
    // there is sound for the PicoCalc but I haven't implemented it yet
}

void FreeRoamGame::updateVibrationToggle()
{
    // no vibration in Picoware systems yet
}