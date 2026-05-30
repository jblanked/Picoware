# Add the battery/southbridge compatibility modules for Cardputer.

add_library(usermod_cardputer_battery INTERFACE)

target_sources(usermod_cardputer_battery INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/battery.c
    ${CMAKE_CURRENT_LIST_DIR}/battery_mp.c
)

target_include_directories(usermod_cardputer_battery INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/..
)

target_link_libraries(usermod INTERFACE usermod_cardputer_battery)
