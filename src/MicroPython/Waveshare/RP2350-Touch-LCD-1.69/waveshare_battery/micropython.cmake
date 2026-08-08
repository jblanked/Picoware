# Create a C module for Waveshare battery extension
add_library(usermod_waveshare_battery INTERFACE)

target_sources(usermod_waveshare_battery INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/waveshare_battery.c
    ${CMAKE_CURRENT_LIST_DIR}/battery.c
)

target_include_directories(usermod_waveshare_battery INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_compile_definitions(usermod_waveshare_battery INTERFACE
    MODULE_WAVESHARE_BATTERY_ENABLED=1
)

target_link_libraries(usermod INTERFACE usermod_waveshare_battery)
