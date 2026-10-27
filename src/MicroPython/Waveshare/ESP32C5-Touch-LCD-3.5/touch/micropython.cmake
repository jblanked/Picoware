# Add the touch C module for the WS C5-3.5.

add_library(usermod_ws_c5_35_touch INTERFACE)

target_sources(usermod_ws_c5_35_touch INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/touch.c
    ${CMAKE_CURRENT_LIST_DIR}/touch_mp.c
)

target_include_directories(usermod_ws_c5_35_touch INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/..
)

target_link_libraries(usermod INTERFACE usermod_ws_c5_35_touch)
