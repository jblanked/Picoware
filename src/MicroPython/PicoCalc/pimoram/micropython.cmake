add_library(usermod_pimoram INTERFACE)

target_sources(usermod_pimoram INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/pimoram.c
)

target_include_directories(usermod_pimoram INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod_pimoram INTERFACE
    hardware_psram
)

target_link_libraries(usermod INTERFACE
    usermod_pimoram
)
