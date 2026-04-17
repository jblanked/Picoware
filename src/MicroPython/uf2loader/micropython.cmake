# MicroPython C module for UF2 firmware flashing

add_library(usermod_uf2loader INTERFACE)

target_sources(usermod_uf2loader INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/uf2loader_mp.c
)

target_include_directories(usermod_uf2loader INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod_uf2loader INTERFACE
    hardware_flash
    hardware_watchdog
    hardware_sync
)

target_link_libraries(usermod INTERFACE usermod_uf2loader)
