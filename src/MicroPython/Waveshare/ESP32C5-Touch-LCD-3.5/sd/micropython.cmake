# Add the sd modules for the WS C5-3.5.

add_library(usermod_ws_c5_35_sd INTERFACE)

target_sources(usermod_ws_c5_35_sd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/sdcard.c
    ${CMAKE_CURRENT_LIST_DIR}/sdcard_vfs_bridge.c
    ${CMAKE_CURRENT_LIST_DIR}/storage.c
    ${CMAKE_CURRENT_LIST_DIR}/sd_mp.c
)

target_include_directories(usermod_ws_c5_35_sd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/..
)

target_link_libraries(usermod INTERFACE usermod_ws_c5_35_sd)
