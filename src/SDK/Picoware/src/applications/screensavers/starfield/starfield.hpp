// Animates white pixels to simulate flying through a star field
// Original from https://github.com/Bodmer/TFT_eSPI/tree/master/examples/320%20x%20240/TFT_Starfield

#pragma once
#include "../../../system/colors.hpp"
#include "../../../system/view.hpp"
#include "../../../system/view_manager.hpp"

#define NSTARS 128
uint8_t sf_sx[NSTARS] = {};
uint8_t sf_sy[NSTARS] = {};
uint8_t sf_sz[NSTARS] = {};

uint8_t za, zb, zc, zx;

// Fast 0-255 random number generator from http://eternityforest.com/Projects/rng.php:
inline uint8_t __attribute__((always_inline)) rng()
{
    zx++;
    za = (za ^ zc ^ zx);
    zb = (zb + za);
    zc = ((zc + (zb >> 1)) ^ za);
    return zc;
}

bool starfieldStart(ViewManager *viewManager)
{
    za = randomMax(256);
    zb = randomMax(256);
    zc = randomMax(256);
    zx = randomMax(256);
    viewManager->getDraw()->fillScreen(TFT_BLACK);
    viewManager->getDraw()->swap();
    return true;
}

void starfieldRun(ViewManager *viewManager)
{
    unsigned long t0 = micros();
    uint8_t spawnDepthVariation = 255;
    auto tft = viewManager->getDraw();
    auto input = viewManager->getInputManager()->getLastButton();
    if (input == BUTTON_LEFT || input == BUTTON_BACK)
    {
        viewManager->back();
        viewManager->getInputManager()->reset(true);
        return;
    }
    for (int i = 0; i < NSTARS; ++i)
    {
        if (sf_sz[i] <= 1)
        {
            sf_sx[i] = 160 - 120 + rng();
            sf_sy[i] = rng();
            sf_sz[i] = spawnDepthVariation--;
        }
        else
        {
            int old_screen_x = ((int)sf_sx[i] - 160) * 256 / sf_sz[i] + 160;
            int old_screen_y = ((int)sf_sy[i] - 120) * 256 / sf_sz[i] + 120;

            // This is a faster pixel drawing function for occasions where many single pixels must be drawn
            tft->drawPixel(Vector(old_screen_x, old_screen_y), TFT_BLACK);

            sf_sz[i] -= 2;
            if (sf_sz[i] > 1)
            {
                int screen_x = ((int)sf_sx[i] - 160) * 256 / sf_sz[i] + 160;
                int screen_y = ((int)sf_sy[i] - 120) * 256 / sf_sz[i] + 120;

                if (screen_x >= 0 && screen_y >= 0 && screen_x < 320 && screen_y < 240)
                {
                    uint8_t r, g, b;
                    r = g = b = 255 - sf_sz[i];
                    tft->drawPixel(Vector(screen_x, screen_y), tft->color565(r, g, b));
                }
                else
                    sf_sz[i] = 0; // Out of screen, die.
            }
        }
    }
    unsigned long t1 = micros();
    tft->swap();
}

void starfieldStop(ViewManager *viewManager)
{
    auto draw = viewManager->getDraw();
    draw->fillScreen(TFT_BLACK);
    draw->swap();
}

static const View starfieldView = View("Starfield", starfieldRun, starfieldStart, starfieldStop);