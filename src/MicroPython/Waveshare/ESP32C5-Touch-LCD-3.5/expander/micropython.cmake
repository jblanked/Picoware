# Add the I/O expander helper for the WS C5-3.5 (LCD/touch reset, backlight).
# Not a MicroPython module itself; the LCD and touch drivers call into it.

add_library(usermod_ws_c5_35_expander INTERFACE)

target_sources(usermod_ws_c5_35_expander INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/expander.c
)

target_include_directories(usermod_ws_c5_35_expander INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/..
)

target_link_libraries(usermod INTERFACE usermod_ws_c5_35_expander)
