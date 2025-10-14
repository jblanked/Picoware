// Animates white pixels to simulate flying through a star field
// Original from https://github.com/Bodmer/TFT_eSPI/tree/master/examples/320%20x%20240/TFT_Starfield

#pragma once
#include "../../../system/colors.hpp"
#include "../../../system/view.hpp"
#include "../../../system/view_manager.hpp"
#include "../../../system/psram.hpp"
#include "../../../system/helpers.hpp"

namespace Starfield
{
#define NSTARS 128

    static uint32_t psram_stars_addr = 0;
    static bool psram_data_valid = false;

    uint8_t za, zb, zc, zx;

    // Fast 0-255 random number generator from http://eternityforest.com/Projects/rng.php:
    inline uint8_t rng()
    {
        zx++;
        za = (za ^ zc ^ zx);
        zb = (zb + za);
        zc = ((zc + (zb >> 1)) ^ za);
        return zc;
    }

    void initializePSRAM()
    {
        psram_data_valid = false;

        PSRAM psram;

        if (psram_stars_addr == 0 && PSRAM::isReady())
        {
            // We need 3 arrays of 128 uint8_t values each (sx, sy, sz)
            // Total: 128 * 3 = 384 bytes
            uint32_t size_needed = NSTARS * 3 * sizeof(uint8_t);

            // Allocate PSRAM for star data
            psram_stars_addr = PSRAM::malloc(size_needed);
            if (psram_stars_addr != 0)
            {
                // Initialize all star data to 0
                uint8_t zero_data[NSTARS * 3] = {0}; // sx, sy, sz arrays
                PSRAM::writeUint8Array(psram_stars_addr, zero_data, NSTARS * 3);
                psram_data_valid = true;
            }
        }
    }

    void setStar(uint8_t index, uint8_t sx, uint8_t sy, uint8_t sz)
    {
        if (psram_data_valid && psram_stars_addr != 0 && index < NSTARS)
        {
            PSRAM::write8(psram_stars_addr + (index * 3) + 0, sx); // sx
            PSRAM::write8(psram_stars_addr + (index * 3) + 1, sy); // sy
            PSRAM::write8(psram_stars_addr + (index * 3) + 2, sz); // sz
        }
    }

    void getStar(uint8_t index, uint8_t &sx, uint8_t &sy, uint8_t &sz)
    {
        if (psram_data_valid && psram_stars_addr != 0 && index < NSTARS)
        {
            sx = PSRAM::read8(psram_stars_addr + (index * 3) + 0);
            sy = PSRAM::read8(psram_stars_addr + (index * 3) + 1);
            sz = PSRAM::read8(psram_stars_addr + (index * 3) + 2);
        }
        else
        {
            sx = sy = sz = 0;
        }
    }

    bool starfieldStart(ViewManager *viewManager)
    {
        za = rand() % 256;
        zb = rand() % 256;
        zc = rand() % 256;
        zx = rand() % 256;

        // Initialize PSRAM storage for star data
        initializePSRAM();

        viewManager->getDraw()->fillScreen(TFT_BLACK);
        viewManager->getDraw()->swap();
        return true;
    }

    void starfieldRun(ViewManager *viewManager)
    {
        if (!psram_data_valid)
            return;

        auto input = viewManager->getInputManager()->getLastButton();
        if (input == BUTTON_LEFT || input == BUTTON_BACK)
        {
            viewManager->back();
            viewManager->getInputManager()->reset();
            return;
        }

        auto tft = viewManager->getDraw();
        uint8_t spawnDepthVariation = 255;

        for (int i = 0; i < NSTARS; ++i)
        {
            uint8_t sx, sy, sz;
            getStar(i, sx, sy, sz);

            if (sz <= 1)
            {
                sx = 160 - 120 + rng();
                sy = rng();
                sz = (spawnDepthVariation > 10) ? spawnDepthVariation-- : 10;
                setStar(i, sx, sy, sz);
            }
            else
            {
                if (sz > 0)
                {
                    int old_screen_x = ((int)sx - 160) * 256 / sz + 160;
                    int old_screen_y = ((int)sy - 160) * 256 / sz + 160;

                    // Only draw black pixel if it's within screen bounds
                    if (old_screen_x >= 0 && old_screen_y >= 0 && old_screen_x < 320 && old_screen_y < 320)
                    {
                        tft->drawPixel(Vector(old_screen_x, old_screen_y), TFT_BLACK);
                    }

                    sz -= 2;
                    if (sz > 1)
                    {
                        int screen_x = ((int)sx - 160) * 256 / sz + 160;
                        int screen_y = ((int)sy - 160) * 256 / sz + 160;

                        if (screen_x >= 0 && screen_y >= 0 && screen_x < 320 && screen_y < 320)
                        {
                            uint16_t color = TFT_WHITE;
                            Vector pixel_pos(screen_x, screen_y);
                            tft->drawPixel(pixel_pos, color);
                        }
                        else
                        {
                            sz = 0; // Out of screen, die.
                        }
                    }
                    setStar(i, sx, sy, sz);
                }
            }
        }

        tft->swap();
    }

    void starfieldStop(ViewManager *viewManager)
    {
        auto draw = viewManager->getDraw();
        draw->fillScreen(TFT_BLACK);
        draw->swap();

        // Clean up PSRAM allocation
        if (psram_stars_addr != 0)
        {
            PSRAM::free(psram_stars_addr);
            psram_stars_addr = 0;
        }
        psram_data_valid = false;
    }
} // namespace Starfield

static const View starfieldView = View("Starfield", Starfield::starfieldRun, Starfield::starfieldStart, Starfield::starfieldStop);