# Waveshare ESP32-S3-Touch-AMOLED-2.06 MicroPython C modules.
# This file is copied to ports/esp32/modules/cardputer/ during the build.

# Identify Waveshare ESP32-S3-Touch-AMOLED-2.06 in shared modules (for board ID/capability flags).
add_compile_definitions(WAVESHARE_AMOLED_2_06_ESP32_S3)
# Ensure core ESP32 port sources (including shared TinyUSB).
list(APPEND MICROPY_DEF_BOARD WAVESHARE_AMOLED_2_06_ESP32_S3)

# Include Cardputer-specific C modules.
include(${CMAKE_CURRENT_LIST_DIR}/lcd/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/battery/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/sd/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/touch/micropython.cmake)

# Include JPEGDEC folder
include_directories(${CMAKE_CURRENT_LIST_DIR}/../JPEGDEC/src)

# Include Picoware modules
include(${CMAKE_CURRENT_LIST_DIR}/../auto_complete/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../engine/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../font/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../jpeg/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../jsmn/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../lcd/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../log/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../picoware_boards/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../response/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../textbox/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../vector/micropython.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/../vt/micropython.cmake)
