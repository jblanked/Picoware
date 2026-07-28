# Add the battery module for Pancake.

add_library(usermod_pancake_battery INTERFACE)

target_sources(usermod_pancake_battery INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/battery.c
    ${CMAKE_CURRENT_LIST_DIR}/battery_mp.c
)

target_include_directories(usermod_pancake_battery INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/..
)

target_link_libraries(usermod INTERFACE usermod_pancake_battery)
