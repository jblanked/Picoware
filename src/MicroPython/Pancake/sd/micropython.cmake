# Add the sd modules for Pancake.

add_library(usermod_pancake_sd INTERFACE)

target_sources(usermod_pancake_sd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/sdcard.c
    ${CMAKE_CURRENT_LIST_DIR}/sdcard_vfs_bridge.c
    ${CMAKE_CURRENT_LIST_DIR}/storage.c
    ${CMAKE_CURRENT_LIST_DIR}/sd_mp.c
)

target_include_directories(usermod_pancake_sd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/..
)

target_link_libraries(usermod INTERFACE usermod_pancake_sd)
