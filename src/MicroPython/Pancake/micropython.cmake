# Pancake ESP32-C5 MicroPython C modules.
# This file is copied to ports/esp32/modules/pancake/ during the build.

# Identify Pancake in shared modules (for board ID/capability flags).
add_compile_definitions(PANCAKE)
# Ensure core ESP32 port sources (including shared TinyUSB) also see PANCAKE.
list(APPEND MICROPY_DEF_BOARD PANCAKE)

# Include Pancake-specific C modules.
include(${CMAKE_CURRENT_LIST_DIR}/i2c/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/lcd/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/touch/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/battery/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/sd/micropython.cmake)

# usb_video is absent: it needs TinyUSB (tusb.h), which is only built for chips
# with a USB-OTG peripheral. The C5 has only USB Serial/JTAG.

# Include JPEGDEC folder
include_directories(${CMAKE_CURRENT_LIST_DIR}/../JPEGDEC/src)

# Include Picoware modules
include(${CMAKE_CURRENT_LIST_DIR}/../auto_complete/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../engine/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../font/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../jpeg/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../video/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../jsmn/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../lcd/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../log/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../mjs/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../mmbasic/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../picoware_boards/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../response/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../textbox/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../usb_video/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../vector/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../vt/micropython.cmake)

# Network modules (HTTP, WebSocket)
include(${CMAKE_CURRENT_LIST_DIR}/../http/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../websocket/micropython.cmake)

# Game modules
include(${CMAKE_CURRENT_LIST_DIR}/../ghouls/micropython.cmake)
