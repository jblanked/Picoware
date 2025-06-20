#include "game.hpp"

namespace Picoware
{
    static const PROGMEM uint16_t vgm_engine_palette[256] = {0x0000, 0x0008, 0x0010, 0x0018, 0x0100, 0x0108, 0x0110, 0x0118, 0x0200, 0x0208, 0x0210, 0x0218, 0x0300, 0x0308, 0x0310, 0x0318, 0x0400, 0x0408, 0x0410, 0x0418, 0x0500, 0x0508, 0x0510, 0x0518, 0x0600, 0x0608, 0x0610, 0x0618, 0x0700, 0x0708, 0x0710, 0x0718, 0x2000, 0x2008, 0x2010, 0x2018, 0x2100, 0x2108, 0x2110, 0x2118, 0x2200, 0x2208, 0x2210, 0x2218, 0x2300, 0x2308, 0x2310, 0x2318, 0x2400, 0x2408, 0x2410, 0x2418, 0x2500, 0x2508, 0x2510, 0x2518, 0x2600, 0x2608, 0x2610, 0x2618, 0x2700, 0x2708, 0x2710, 0x2718, 0x4000, 0x4008, 0x4010, 0x4018, 0x4100, 0x4108, 0x4110, 0x4118, 0x4200, 0x4208, 0x4210, 0x4218, 0x4300, 0x4308, 0x4310, 0x4318, 0x4400, 0x4408, 0x4410, 0x4418, 0x4500, 0x4508, 0x4510, 0x4518, 0x4600, 0x4608, 0x4610, 0x4618, 0x4700, 0x4708, 0x4710, 0x4718, 0x6000, 0x6008, 0x6010, 0x6018, 0x6100, 0x6108, 0x6110, 0x6118, 0x6200, 0x6208, 0x6210, 0x6218, 0x6300, 0x6308, 0x6310, 0x6318, 0x6400, 0x6408, 0x6410, 0x6418, 0x6500, 0x6508, 0x6510, 0x6518, 0x6600, 0x6608, 0x6610, 0x6618, 0x6700, 0x6708, 0x6710, 0x6718, 0x8000, 0x8008, 0x8010, 0x8018, 0x8100, 0x8108, 0x8110, 0x8118, 0x8200, 0x8208, 0x8210, 0x8218, 0x8300, 0x8308, 0x8310, 0x8318, 0x8400, 0x8408, 0x8410, 0x8418, 0x8500, 0x8508, 0x8510, 0x8518, 0x8600, 0x8608, 0x8610, 0x8618, 0x8700, 0x8708, 0x8710, 0x8718, 0xa000, 0xa008, 0xa010, 0xa018, 0xa100, 0xa108, 0xa110, 0xa118, 0xa200, 0xa208, 0xa210, 0xa218, 0xa300, 0xa308, 0xa310, 0xa318, 0xa400, 0xa408, 0xa410, 0xa418, 0xa500, 0xa508, 0xa510, 0xa518, 0xa600, 0xa608, 0xa610, 0xa618, 0xa700, 0xa708, 0xa710, 0xa718, 0xc000, 0xc008, 0xc010, 0xc018, 0xc100, 0xc108, 0xc110, 0xc118, 0xc200, 0xc208, 0xc210, 0xc218, 0xc300, 0xc308, 0xc310, 0xc318, 0xc400, 0xc408, 0xc410, 0xc418, 0xc500, 0xc508, 0xc510, 0xc518, 0xc600, 0xc608, 0xc610, 0xc618, 0xc700, 0xc708, 0xc710, 0xc718, 0xe000, 0xe008, 0xe010, 0xe018, 0xe100, 0xe108, 0xe110, 0xe118, 0xe200, 0xe208, 0xe210, 0xe218, 0xe300, 0xe308, 0xe310, 0xe318, 0xe400, 0xe408, 0xe410, 0xe418, 0xe500, 0xe508, 0xe510, 0xe518, 0xe600, 0xe608, 0xe610, 0xe618, 0xe700, 0xe708, 0xe710, 0xffff};

    Game::Game(
        const char *name,
        Vector size,
        Draw *draw,
        InputManager *input_manager,
        uint16_t fg_color,
        uint16_t bg_color,
        CameraPerspective perspective,
        void (*start)(),
        void (*stop)())
        : name(name), size(size), _start(start), _stop(stop),
          fg_color(fg_color), bg_color(bg_color),
          camera_perspective(perspective),
          current_level(nullptr),
          camera(0, 0), pos(0, 0), old_pos(0, 0),
          is_active(false), input(-1)
    {
        for (int i = 0; i < MAX_LEVELS; i++)
        {
            levels[i] = nullptr;
        }
        this->draw = draw;
        this->draw->background(bg_color);
        this->draw->display->setFont();
        this->draw->color(fg_color);

        if (this->draw->is8bit())
        {
            memcpy(draw->getPalette(), vgm_engine_palette, sizeof(vgm_engine_palette));
            this->draw->swap(false, true); // Duplicate same palette into front & back buffers
        }

        // Initialize the input manager
        this->input_manager = input_manager;
    }

    // Destructor: clean up dynamically allocated memory
    Game::~Game()
    {

        for (int i = 0; i < MAX_LEVELS; i++)
        {
            if (levels[i] != nullptr)
            {
                delete levels[i];
                levels[i] = nullptr;
            }
        }
    }

    void Game::clamp(float &value, float min, float max)
    {
        if (value < min)
            value = min;
        if (value > max)
            value = max;
    }

    void Game::level_add(Level *level)
    {
        for (int i = 0; i < MAX_LEVELS; i++)
        {
            if (this->levels[i] == nullptr)
            {
                this->levels[i] = level;
                return;
            }
        }
    }

    void Game::level_remove(Level *level)
    {
        for (int i = 0; i < MAX_LEVELS; i++)
        {
            if (this->levels[i] == level)
            {
                this->levels[i] = nullptr;
                delete level;
                return;
            }
        }
    }

    void Game::level_switch(const char *name)
    {
        for (int i = 0; i < MAX_LEVELS; i++)
        {
            if (this->levels[i] && strcmp(this->levels[i]->name, name) == 0)
            {
                // Stop the current level before switching
                if (this->current_level != nullptr)
                {
                    this->current_level->stop();
                }

                this->current_level = this->levels[i];
                this->current_level->start();
                return;
            }
        }
    }

    void Game::level_switch(int index)
    {
        if (index < MAX_LEVELS && this->levels[index] != nullptr)
        {
            // Stop the current level before switching
            if (this->current_level != nullptr)
            {
                this->current_level->stop();
            }

            this->current_level = this->levels[index];
            this->current_level->start();
        }
    }

    void Game::render()
    {
        if (this->current_level == nullptr)
        {
            return;
        }

        // render the level with the configured perspective
        this->current_level->render(this, camera_perspective);
    }

    void Game::start()
    {
        if (this->levels[0] == nullptr)
        {
            return;
        }
        this->current_level = this->levels[0];

        // Call the game’s start callback (if any)
        if (this->_start != nullptr)
        {
            this->_start();
        }

        // Start the level
        this->current_level->start();

        // Mark the game as active
        this->is_active = true;
    }

    void Game::stop()
    {
        if (!this->is_active)
            return;

        if (this->_stop != nullptr)
            this->_stop();

        if (this->current_level != nullptr)
            this->current_level->stop();

        this->is_active = false;

        // Clear all levels.
        for (int i = 0; i < MAX_LEVELS; i++)
        {
            delete this->levels[i];
            this->levels[i] = nullptr;
        }

        // Clear the screen.
        this->draw->clear(Vector(0, 0), size, bg_color);
    }

    void Game::update()
    {
        if (!this->is_active || this->current_level == nullptr)
            return;

        // Update input states (view manager runs the input)
        this->input = this->input_manager->getInput();

        // Update the level
        this->current_level->update(this);
    }

    void Game::setPerspective(CameraPerspective perspective)
    {
        camera_perspective = perspective;
    }

    CameraPerspective Game::getPerspective() const
    {
        return camera_perspective;
    }

}