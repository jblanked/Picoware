# POOM ESP32-C5 MicroPython C modules.
# This file is copied to ports/esp32/modules/poom/ during the build.

# Identify POOM in shared modules (for board ID/capability flags).
add_compile_definitions(POOM)
# Ensure core ESP32 port sources (including shared TinyUSB) also see POOM.
list(APPEND MICROPY_DEF_BOARD POOM)

# Include POOM-specific C modules.
include(${CMAKE_CURRENT_LIST_DIR}/input/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/lcd/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/sd/micropython.cmake)

# usb_video is present but compiles to a stub: it needs TinyUSB (tusb.h), which
# is only built for chips with a USB-OTG peripheral. The C5 has only USB
# Serial/JTAG.

# Include JPEGDEC folder
include_directories(${CMAKE_CURRENT_LIST_DIR}/../JPEGDEC/src)

# Include Picoware modules
include(${CMAKE_CURRENT_LIST_DIR}/../auto_complete/micropython.cmake)
set(ESP32 TRUE)
include(${CMAKE_CURRENT_LIST_DIR}/../c/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../engine/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../font/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../jpeg/micropython.cmake)
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
include(${CMAKE_CURRENT_LIST_DIR}/../video/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../vt/micropython.cmake)

# Network modules (HTTP, WebSocket)
include(${CMAKE_CURRENT_LIST_DIR}/../http/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../websocket/micropython.cmake)

# Game modules
include(${CMAKE_CURRENT_LIST_DIR}/../ghouls/micropython.cmake)
