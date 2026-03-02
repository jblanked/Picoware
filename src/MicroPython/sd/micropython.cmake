add_library(usermod_sd INTERFACE)

target_sources(usermod_sd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/fat32.c
    ${CMAKE_CURRENT_LIST_DIR}/sd_mp.c
    ${CMAKE_CURRENT_LIST_DIR}/sdcard.c
    ${CMAKE_CURRENT_LIST_DIR}/vfs_mp.c
)

target_include_directories(usermod_sd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_sd)
