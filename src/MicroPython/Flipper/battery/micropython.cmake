add_library(usermod_battery INTERFACE)

target_sources(usermod_battery INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/battery.c
    ${CMAKE_CURRENT_LIST_DIR}/battery_mp.c
)

target_include_directories(usermod_battery INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/..
)

target_compile_definitions(usermod_battery INTERFACE
    FLIPPER_ZERO
)

target_link_libraries(usermod INTERFACE usermod_battery)
