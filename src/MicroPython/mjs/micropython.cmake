# Include mjs module
add_library(usermod_mjs INTERFACE)

target_sources(usermod_mjs INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/mjs_module.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/array_buf.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/bluetooth.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/buttons.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/color.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/http.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/input.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/lib.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/lcd.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/log.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/math.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/mjs.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/pin.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/settings.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/storage.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/system.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/time.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/wifi.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/uart.c
)

target_include_directories(usermod_mjs INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/mjs
    ${CMAKE_CURRENT_LIST_DIR}/mjs/src
    ${CMAKE_CURRENT_LIST_DIR}/mjs/src/frozen
    ${CMAKE_CURRENT_LIST_DIR}/mjs/src/common
    ${CMAKE_CURRENT_LIST_DIR}/mjs/src/ffi
    ${CMAKE_CURRENT_LIST_DIR}/mjs/lib
)

target_compile_definitions(usermod_mjs INTERFACE
    MJS_EXPOSE_PRIVATE
)

target_link_libraries(usermod INTERFACE usermod_mjs)