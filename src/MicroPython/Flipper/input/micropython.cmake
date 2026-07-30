add_library(usermod_input INTERFACE)

target_sources(usermod_input INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/input.c
    ${CMAKE_CURRENT_LIST_DIR}/input_mp.c
)

target_include_directories(usermod_input INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/..
)

target_compile_definitions(usermod_input INTERFACE
    FLIPPER_ZERO
)

target_link_libraries(usermod INTERFACE usermod_input)
