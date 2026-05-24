# Add the sd/southbridge compatibility modules for Cardputer.

add_library(usermod_sd INTERFACE)

target_sources(usermod_sd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/sdcard.c
    ${CMAKE_CURRENT_LIST_DIR}/storage.c
    ${CMAKE_CURRENT_LIST_DIR}/sd_mp.c
)

target_include_directories(usermod_sd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/..
)

target_link_libraries(usermod INTERFACE usermod_sd)
