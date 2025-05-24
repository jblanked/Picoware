#include "Picoware.h"

/*
- Board Manager: Raspberry Pi Pico
- Flash Size: 2MB (Sketch: 1984KB, FS: 64KB)
- CPU Speed: 200MHz
*/

ViewManager *vm;

void setup()
{
  vm = new ViewManager(VGMConfig);
  vm->add(&desktopView);
  vm->switchTo("Desktop");
}

void loop()
{
  vm->run();
}