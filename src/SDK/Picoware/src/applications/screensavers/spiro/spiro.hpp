// Original from https://github.com/Bodmer/TFT_eSPI/blob/master/examples/320%20x%20240/TFT_Spiro/TFT_Spiro.ino

#pragma once
#include "../../../system/colors.hpp"
#include "../../../system/view.hpp"
#include "../../../system/view_manager.hpp"

#define DEG2RAD 0.0174532925 // Convert angles in degrees to radians
float sp_sx = 0, sp_sy = 0;
uint16_t x0 = 0, x1 = 0, yy0 = 0, yy1 = 0;

static unsigned int rainbow(int value)
{
  // Value is expected to be in range 0-127
  // The value is converted to a spectrum colour from 0 = blue through to red = blue
  // int value = random (128);
  uint8_t red = 0;   // Red is the top 5 bits of a 16-bit colour value
  uint8_t green = 0; // Green is the middle 6 bits
  uint8_t blue = 0;  // Blue is the bottom 5 bits

  uint8_t quadrant = value / 32;

  if (quadrant == 0)
  {
    blue = 31;
    green = 2 * (value % 32);
    red = 0;
  }
  if (quadrant == 1)
  {
    blue = 31 - (value % 32);
    green = 63;
    red = 0;
  }
  if (quadrant == 2)
  {
    blue = 0;
    green = 63;
    red = value % 32;
  }
  if (quadrant == 3)
  {
    blue = 0;
    green = 63 - 2 * (value % 32);
    red = 31;
  }
  return (red << 11) + (green << 5) + blue;
}

bool spiroStart(ViewManager *viewManager)
{
  viewManager->getDraw()->fillScreen(TFT_BLACK);
  viewManager->getDraw()->swap();
  return true;
}

void spiroRun(ViewManager *viewManager)
{
  auto input = viewManager->getInputManager()->getLastButton();
  static int spiro_elapsed = 0;
  if (input == BUTTON_LEFT || input == BUTTON_BACK)
  {
    viewManager->back();
    spiro_elapsed = 0;
    viewManager->getInputManager()->reset();
    return;
  }
  if (spiro_elapsed > 200000)
  {
    spiro_elapsed = 0;
    auto tft = viewManager->getDraw();

    tft->fillScreen(TFT_BLACK);
    int n = randomRange(2, 23), r = randomRange(20, 100), colour = 0; // rainbow();

    for (long i = 0; i < (360 * n); i++)
    {
      sp_sx = cos((i / n - 90) * DEG2RAD);
      sp_sy = sin((i / n - 90) * DEG2RAD);
      x0 = sp_sx * (120 - r) + 159;
      yy0 = sp_sy * (120 - r) + 119;

      sp_sy = cos(((i % 360) - 90) * DEG2RAD);
      sp_sx = sin(((i % 360) - 90) * DEG2RAD);
      x1 = sp_sx * r + x0;
      yy1 = sp_sy * r + yy0;
      tft->drawPixel(Vector(x1, yy1), rainbow(mapValue(i % 360, 0, 360, 0, 127))); // colour);
    }

    r = randomRange(20, 100); // r = r / random(2,4);
    for (long i = 0; i < (360 * n); i++)
    {
      sp_sx = cos((i / n - 90) * DEG2RAD);
      sp_sy = sin((i / n - 90) * DEG2RAD);
      x0 = sp_sx * (120 - r) + 159;
      yy0 = sp_sy * (120 - r) + 119;

      sp_sy = cos(((i % 360) - 90) * DEG2RAD);
      sp_sx = sin(((i % 360) - 90) * DEG2RAD);
      x1 = sp_sx * r + x0;
      yy1 = sp_sy * r + yy0;
      tft->drawPixel(Vector(x1, yy1), rainbow(mapValue(i % 360, 0, 360, 0, 127))); // colour);
    }
    tft->swap();
  }
  spiro_elapsed++;
}

void spiroStop(ViewManager *viewManager)
{
  auto draw = viewManager->getDraw();
  draw->fillScreen(viewManager->getBackgroundColor());
  draw->swap();
}

static const View spiroView = View("Spiro", spiroRun, spiroStart, spiroStop);