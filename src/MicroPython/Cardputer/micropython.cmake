# Cardputer ESP32-S3 MicroPython C modules.
# This file is copied to ports/esp32/modules/cardputer/ during the build.

# Identify Cardputer in shared modules (for board ID/capability flags).
add_compile_definitions(CARDPUTER)

# Include Cardputer-specific C modules.
include(${CMAKE_CURRENT_LIST_DIR}/lcd/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/keyboard/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/battery/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/sd/micropython.cmake)

# Include Picoware modules
include(${CMAKE_CURRENT_LIST_DIR}/../auto_complete/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../font/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../lcd/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../log/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../picoware_boards/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../response/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../textbox/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../vector/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../vt/micropython.cmake)
