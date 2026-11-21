add_library(usermod_input INTERFACE)

target_sources(usermod_input INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/input_mp.c
    ${CMAKE_CURRENT_LIST_DIR}/input.c
)

target_include_directories(usermod_input INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(usermod INTERFACE usermod_input)