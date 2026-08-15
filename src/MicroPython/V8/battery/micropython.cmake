# Add the battery module for V8.

add_library(usermod_v8_battery INTERFACE)

target_sources(usermod_v8_battery INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/battery.c
    ${CMAKE_CURRENT_LIST_DIR}/battery_mp.c
)

target_include_directories(usermod_v8_battery INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/..
)

target_link_libraries(usermod INTERFACE usermod_v8_battery)
