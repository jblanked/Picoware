# Include mjs module
add_library(usermod_mjs INTERFACE)

target_sources(usermod_mjs INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/mjs_module.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/color.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/lcd.c
    ${CMAKE_CURRENT_LIST_DIR}/lib/log.c
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