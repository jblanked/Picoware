#include <stdio.h>
#include "pico/stdlib.h"
#include "hardware/clocks.h"
#include "src/applications/desktop/desktop.hpp"
#include "src/system/view_manager.hpp"

int main()
{
    stdio_init_all();

    set_sys_clock_khz(200000, true);
    ViewManager vm;
    vm.add(&desktopView);

    vm.switchTo("Desktop");

    while (true)
    {
        vm.run();
    }
}