# Add the touch C module for V8.

add_library(usermod_v8_touch INTERFACE)

target_sources(usermod_v8_touch INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/touch.c
    ${CMAKE_CURRENT_LIST_DIR}/touch_mp.c
)

target_include_directories(usermod_v8_touch INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/..
)

target_link_libraries(usermod INTERFACE usermod_v8_touch)
