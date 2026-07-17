# Add the touch C module for Pancake.

add_library(usermod_pancake_touch INTERFACE)

target_sources(usermod_pancake_touch INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/touch.c
    ${CMAKE_CURRENT_LIST_DIR}/touch_mp.c
)

target_include_directories(usermod_pancake_touch INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/..
)

target_link_libraries(usermod INTERFACE usermod_pancake_touch)
