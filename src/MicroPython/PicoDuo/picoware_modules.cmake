# Combined Picoware Modules for MicroPython

# Define PICO_DUO for all modules compiled via this file
add_compile_definitions(PICO_DUO)

# Include lcd module
include(${CMAKE_CURRENT_LIST_DIR}/lcd/micropython.cmake)

include(${CMAKE_CURRENT_LIST_DIR}/../auto_complete/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../c/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../engine/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../font/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../jpeg/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../jsmn/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../ghouls/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../http/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../lcd/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../log/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../mjs/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../mmbasic/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../picoware_boards/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../response/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../textbox/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../usb_video/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../websocket/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../vector/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../video/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../vt/micropython.cmake)