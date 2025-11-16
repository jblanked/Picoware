# Create a C module for Waveshare sd extension
add_library(usermod_waveshare_sd INTERFACE)

target_sources(usermod_waveshare_sd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/waveshare_sd.c
    ${CMAKE_CURRENT_LIST_DIR}/sdcard.c
    ${CMAKE_CURRENT_LIST_DIR}/fat32.c
)

target_include_directories(usermod_waveshare_sd INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_compile_definitions(usermod_waveshare_sd INTERFACE
    MODULE_WAVESHARE_SD_ENABLED=1
)

target_link_libraries(usermod INTERFACE usermod_waveshare_sd)
