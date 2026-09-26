# Add the input C module for POOM.

add_library(usermod_poom_input INTERFACE)

target_sources(usermod_poom_input INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/input.c
    ${CMAKE_CURRENT_LIST_DIR}/input_mp.c
)

target_include_directories(usermod_poom_input INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_LIST_DIR}/..
)

target_compile_definitions(usermod_poom_input INTERFACE
    POOM
)

target_link_libraries(usermod INTERFACE usermod_poom_input)
