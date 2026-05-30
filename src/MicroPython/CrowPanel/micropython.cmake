# CrowPanel 10.1 ESP32-P4 MicroPython C modules.
# This is copied to ports/esp32/modules/crowpanel/ during the build.

# Identify CrowPanel in shared modules (for board ID/capability flags).
add_compile_definitions(CROWPANEL_10_1)

# Include CrowPanel-specific C modules.
include(${CMAKE_CURRENT_LIST_DIR}/lcd/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/touch/micropython.cmake)

# Include Picoware core modules that are portable to ESP32.
include(${CMAKE_CURRENT_LIST_DIR}/../picoware_boards/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../vector/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../response/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../font/micropython.cmake)

