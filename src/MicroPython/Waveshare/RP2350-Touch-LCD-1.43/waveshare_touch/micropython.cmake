# Create a C module for Waveshare touch extension
add_library(usermod_waveshare_touch INTERFACE)

target_sources(usermod_waveshare_touch INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/waveshare_touch.c
    ${CMAKE_CURRENT_LIST_DIR}/touch.c
)

target_include_directories(usermod_waveshare_touch INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_compile_definitions(usermod_waveshare_touch INTERFACE
    MODULE_WAVESHARE_TOUCH_ENABLED=1
)

target_link_libraries(usermod INTERFACE usermod_waveshare_touch)
