# Add the battery module for the WS C5-3.5.

add_library(usermod_ws_c5_35_battery INTERFACE)

target_sources(usermod_ws_c5_35_battery INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/battery.c
    ${CMAKE_CURRENT_LIST_DIR}/battery_mp.c
)

target_include_directories(usermod_ws_c5_35_battery INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/..
)

target_link_libraries(usermod INTERFACE usermod_ws_c5_35_battery)
