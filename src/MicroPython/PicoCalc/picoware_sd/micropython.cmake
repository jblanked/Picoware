# Create a C module for Picoware sd extension
add_library(usermod_picoware_sd INTERFACE)

target_sources(usermod_picoware_sd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/picoware_sd.c
    ${CMAKE_CURRENT_LIST_DIR}/picoware_vfs.c
    ${CMAKE_CURRENT_LIST_DIR}/sdcard.c
    ${CMAKE_CURRENT_LIST_DIR}/fat32.c
)

target_include_directories(usermod_picoware_sd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_compile_definitions(usermod_picoware_sd INTERFACE
    MODULE_WAVESHARE_SD_ENABLED=1
)

target_link_libraries(usermod INTERFACE usermod_picoware_sd)
