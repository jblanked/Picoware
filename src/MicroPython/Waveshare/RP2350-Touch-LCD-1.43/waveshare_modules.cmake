add_compile_definitions(WAVESHARE_1_43)
list(APPEND MICROPY_DEF_BOARD WAVESHARE_1_43)

# Include Waveshare 1.43 board-specific C modules.
include(${CMAKE_CURRENT_LIST_DIR}/waveshare_battery/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/waveshare_lcd/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/waveshare_touch/micropython.cmake)

# Include JPEGDEC folder
include_directories(${CMAKE_CURRENT_LIST_DIR}/../../JPEGDEC/src)

# Include Picoware modules
include(${CMAKE_CURRENT_LIST_DIR}/../../audio/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../../auto_complete/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../../c/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../../engine/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../../font/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../../jpeg/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../../jsmn/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../../lcd/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../../log/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../../mjs/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../../mmbasic/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../../picoware_boards/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../../response/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../../sd/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../../textbox/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../../usb_video/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../../vector/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../../video/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../../vt/micropython.cmake)

# Network modules (HTTP, WebSocket)
include(${CMAKE_CURRENT_LIST_DIR}/../../http/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../../websocket/micropython.cmake)

# Game modules
include(${CMAKE_CURRENT_LIST_DIR}/../../ghouls/micropython.cmake)
