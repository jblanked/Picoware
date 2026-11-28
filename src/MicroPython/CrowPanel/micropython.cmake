# CrowPanel 10.1 ESP32-P4 MicroPython C modules.
# This is copied to ports/esp32/modules/crowpanel/ during the build.

# Include CrowPanel-specific C modules.
include(${CMAKE_CURRENT_LIST_DIR}/lcd/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/touch/micropython.cmake)

# Include Picoware core modules that are portable to ESP32.
include(${CMAKE_CURRENT_LIST_DIR}/../engine/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../PicoGTA/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../picoware_boards/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../http/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../jsmn/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../vector/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../view/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../view_manager/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../response/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../font/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../input/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../log/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../websocket/micropython.cmake)

