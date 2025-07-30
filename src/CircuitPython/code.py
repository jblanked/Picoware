"""
Picoware
Author: JBlanked
Github: https://github.com/jblanked/Picoware
Info: A custom firmware for the PicoCalc, Video Game Module, and other Raspberry Pi Pico devices.
Created: 2025-05-14
Updated: 2025-07-30
"""

from picoware.system.view import View
from picoware.system.view_manager import ViewManager
from picoware.system.boards import (
    VGM_BOARD_CONFIG,
    JBLANKED_BOARD_CONFIG,
    PICO_CALC_BOARD_CONFIG_PICO,
    PICO_CALC_BOARD_CONFIG_PICO_W,
    PICO_CALC_BOARD_CONFIG_PICO_2,
    PICO_CALC_BOARD_CONFIG_PICO_2W,
)
from picoware.applications.desktop import main as desktop
from picoware.applications.loading import main as loading


# run the main function
if __name__ == "__main__":
    """
    Main function to run the application
    """
    # Initialize the view manager
    vm: ViewManager = None
    tries = 0
    while not vm and tries < 3:
        try:
            vm: ViewManager = ViewManager(VGM_BOARD_CONFIG, debug=True)
        except Exception:
            print("Failed to initialize ViewManager, retrying...")
            tries += 1
            if tries >= 3:
                raise

    # Add views to the view manager
    vm.add(View("loading_view", loading))
    vm.add(View("desktop_view", desktop))

    # Switch views
    vm.switch("desktop_view")
    # Main loop
    while True:
        vm.run()
