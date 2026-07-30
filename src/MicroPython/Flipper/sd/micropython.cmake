add_library(usermod_sd INTERFACE)

target_sources(usermod_sd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/sd.c
    ${CMAKE_CURRENT_LIST_DIR}/storage.c
    ${CMAKE_CURRENT_LIST_DIR}/sd_mp.c
    ${CMAKE_CURRENT_LIST_DIR}/flipper_sd_blockdev.c
)

target_include_directories(usermod_sd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/..
)

target_compile_definitions(usermod_sd INTERFACE
    FLIPPER_ZERO
)

target_link_libraries(usermod INTERFACE usermod_sd)
